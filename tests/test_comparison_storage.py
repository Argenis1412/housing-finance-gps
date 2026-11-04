"""SQLite lifecycle, migration, permissions boundaries and failure atomicity."""

import ast
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from application.saved_comparisons import SavedComparisonError
from infrastructure import sqlite_comparisons as sqlite
from infrastructure.sqlite_comparisons import SqliteComparisonRepository, migrate_comparisons
from tests.test_saved_comparisons import ID, save


@pytest.mark.parametrize("case", ["missing_config", "relative", "checkout", "symlink_checkout", "missing_file", "uninitialized"])
def test_runtime_refuses_unsafe_or_uninitialized_storage_without_creating_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    path: str | Path | None = tmp_path / "absent.sqlite3"
    expected = "storage_unavailable"
    monkeypatch.delenv("HFGPS_DB_PATH", raising=False)
    if case == "missing_config":
        path = None
        expected = "storage_not_configured"
    elif case == "relative":
        path = "synthetic.sqlite3"
    elif case == "checkout":
        path = Path.cwd() / "synthetic.sqlite3"
    elif case == "symlink_checkout":
        (tmp_path / "linked").symlink_to(Path.cwd(), target_is_directory=True)
        path = tmp_path / "linked" / "synthetic.sqlite3"
    else:
        expected = "storage_not_initialized"
        if case == "uninitialized":
            path.touch()
    with pytest.raises(SavedComparisonError, match=expected):
        with SqliteComparisonRepository(path).transaction():
            pytest.fail("invalid storage admitted")
    assert not (Path.cwd() / "synthetic.sqlite3").exists()
    assert (tmp_path / "absent.sqlite3").exists() == (case == "uninitialized")


def test_explicit_migration_is_repeatable_and_preserves_all_evidence(tmp_path: Path) -> None:
    path = tmp_path / "space # ?" / "synthetic.sqlite3"
    migrate_comparisons(path)
    repository = SqliteComparisonRepository(path)
    save(repository)
    before = path.read_bytes()
    migrate_comparisons(path)
    assert path.read_bytes() == before
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        for table in ("saved_comparisons", "comparison_operations"):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(f"UPDATE {table} SET simulation_id=?", (ID,))
        with pytest.raises(sqlite3.IntegrityError, match="retained"):
            connection.execute("DELETE FROM comparison_operations")


@pytest.mark.parametrize("case", ["unrelated", "future", "wrong_application"])
def test_migration_refuses_unknown_databases_without_writing(tmp_path: Path, case: str) -> None:
    path = tmp_path / "unknown.sqlite3"
    if case == "unrelated":
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE unrelated(value TEXT)")
    else:
        migrate_comparisons(path)
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA user_version=2" if case == "future" else "PRAGMA application_id=123")
    before = path.read_bytes()
    with pytest.raises(SavedComparisonError, match="incompatible_storage_version"):
        migrate_comparisons(path)
    assert before == path.read_bytes()


def test_failed_migration_rolls_back_schema_and_versions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "migration.sqlite3"
    monkeypatch.setattr(sqlite, "_SCHEMA", ("CREATE TABLE partial(value TEXT)", "INVALID SQL"))
    with pytest.raises(SavedComparisonError, match="storage_unavailable"):
        migrate_comparisons(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (0,)
        assert connection.execute("SELECT name FROM sqlite_master").fetchall() == []


def test_busy_failure_is_safe_and_does_not_reserve_operation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "busy.sqlite3"
    migrate_comparisons(path)
    actual = sqlite3.connect
    def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        # Exercise the actual lock failure without spending five seconds in QA.
        kwargs["timeout"] = 0.01
        return actual(*args, **kwargs)  # type: ignore[arg-type]
    with actual(path, autocommit=True) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        monkeypatch.setattr(sqlite.sqlite3, "connect", connect)
        with pytest.raises(SavedComparisonError, match="storage_busy"):
            save(SqliteComparisonRepository(path))
        blocker.execute("ROLLBACK")
    with SqliteComparisonRepository(path).transaction() as transaction:
        assert transaction.find(ID) == (False, None)


def test_commit_failure_rolls_back_inserted_artifact_and_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commit.sqlite3"
    migrate_comparisons(path)
    actual = sqlite3.connect
    class Connection(sqlite3.Connection):
        def execute(self, sql: str, parameters: object = (), /) -> sqlite3.Cursor:
            if sql == "COMMIT":
                raise sqlite3.OperationalError("synthetic commit fault")
            return super().execute(sql, parameters)  # type: ignore[arg-type]
    def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        return actual(*args, **kwargs, factory=Connection)  # type: ignore[arg-type]
    monkeypatch.setattr(sqlite.sqlite3, "connect", connect)
    with pytest.raises(SavedComparisonError, match="storage_unavailable"):
        save(SqliteComparisonRepository(path))
    with actual(path) as connection:
        assert connection.execute("SELECT * FROM comparison_operations").fetchall() == []
        assert connection.execute("SELECT * FROM saved_comparisons").fetchall() == []


def test_import_app_creation_and_openapi_never_create_configured_database(tmp_path: Path) -> None:
    path = tmp_path / "never-create.sqlite3"
    result = subprocess.run([sys.executable, "-c", "from api.main import create_app; create_app().openapi(); import scripts.migrate_comparisons"], env={**os.environ, "HFGPS_DB_PATH": str(path)}, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr.decode()
    assert not path.exists()


def test_application_and_domain_dependency_boundaries() -> None:
    forbidden = {"api", "fastapi", "pydantic", "infrastructure"}
    for path in Path("application").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            assert all(name.split(".")[0] not in forbidden for name in names), path
    for path in Path("domain").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            assert all(name.split(".")[0] not in {"infrastructure", "sqlite3"} for name in names), path


@pytest.mark.parametrize("method", ["resolve", "is_file"])
def test_path_filesystem_failures_are_safe_unavailable_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str) -> None:
    path = tmp_path / "inspection.sqlite3"
    actual = getattr(Path, method)
    def broken(self: Path, *args: object, **kwargs: object) -> object:
        if self == path:
            raise PermissionError("synthetic private path diagnostic")
        return actual(self, *args, **kwargs)
    monkeypatch.setattr(Path, method, broken)
    with pytest.raises(SavedComparisonError, match="storage_unavailable") as error:
        with SqliteComparisonRepository(path).transaction():
            pytest.fail("filesystem failure was admitted")
    assert error.value.status == 503
    assert "diagnostic" not in str(error.value)
