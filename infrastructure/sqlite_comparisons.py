"""SQLite adapter and explicit schema migration for local synthetic evidence."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3

from application.saved_comparisons import MAX_RECORD_BYTES, ComparisonTransaction, SavedComparisonError, StoredComparison


_APPLICATION_ID = 0x48464750
_SCHEMA_VERSION = 1
_SCHEMA = (
    "CREATE TABLE comparison_operations (simulation_id TEXT PRIMARY KEY NOT NULL)",
    "CREATE TABLE saved_comparisons (simulation_id TEXT PRIMARY KEY NOT NULL REFERENCES comparison_operations(simulation_id), saved_at TEXT NOT NULL, record_jcs TEXT NOT NULL, sha256 TEXT NOT NULL)",
    "CREATE INDEX saved_comparisons_order ON saved_comparisons(saved_at DESC, simulation_id DESC)",
    "CREATE TRIGGER immutable_comparison_operations BEFORE UPDATE ON comparison_operations BEGIN SELECT RAISE(ABORT, 'immutable operation'); END",
    "CREATE TRIGGER retained_comparison_operations BEFORE DELETE ON comparison_operations BEGIN SELECT RAISE(ABORT, 'retained operation'); END",
    "CREATE TRIGGER immutable_saved_comparisons BEFORE UPDATE ON saved_comparisons BEGIN SELECT RAISE(ABORT, 'immutable comparison'); END",
)


def _path(value: str | Path | None) -> Path:
    supplied = str(value) if value is not None else os.environ.get("HFGPS_DB_PATH", "")
    if not supplied:
        raise SavedComparisonError("storage_not_configured", 503)
    try:
        candidate = Path(supplied)
        if not candidate.is_absolute():
            raise SavedComparisonError("storage_unavailable", 503)
        root = Path(__file__).resolve().parents[1]
        lexical = Path(os.path.abspath(candidate))
        resolved = candidate.resolve()
        if lexical.is_relative_to(root) or resolved.is_relative_to(root):
            raise SavedComparisonError("storage_unavailable", 503)
        return resolved
    except (OSError, ValueError, RuntimeError):
        raise SavedComparisonError("storage_unavailable", 503) from None


def _sql_error(error: sqlite3.Error) -> SavedComparisonError:
    code = getattr(error, "sqlite_errorcode", 0)
    return SavedComparisonError("storage_busy" if code & 0xFF in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED} else "storage_unavailable", 503)


def _verify_schema(connection: sqlite3.Connection) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    application = connection.execute("PRAGMA application_id").fetchone()[0]
    if version == 0 and application == 0:
        raise SavedComparisonError("storage_not_initialized", 503)
    if version != _SCHEMA_VERSION or application != _APPLICATION_ID:
        raise SavedComparisonError("incompatible_storage_version", 409)
    objects = set(connection.execute("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall())
    if objects != {
        ("table", "comparison_operations"), ("table", "saved_comparisons"),
        ("index", "saved_comparisons_order"),
        ("trigger", "immutable_comparison_operations"), ("trigger", "retained_comparison_operations"),
        ("trigger", "immutable_saved_comparisons"),
    }:
        raise SavedComparisonError("incompatible_storage_version", 409)


class _Transaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def find(self, simulation_id: str) -> tuple[bool, StoredComparison | None]:
        known = self.connection.execute("SELECT 1 FROM comparison_operations WHERE simulation_id=?", (simulation_id,)).fetchone() is not None
        # SQLite TEXT substr stops at NUL. Keep the row deletable but pass an
        # invalid record to the decoder instead of a potentially valid prefix.
        row = self.connection.execute(
            """SELECT simulation_id, saved_at,
                      CASE WHEN instr(record_jcs, char(0)) > 0 THEN ''
                           ELSE substr(record_jcs, 1, ?) END,
                      sha256
               FROM saved_comparisons WHERE simulation_id=?""",
            (MAX_RECORD_BYTES + 1, simulation_id),
        ).fetchone()
        return known, StoredComparison(*row) if row is not None else None

    def insert(self, record: StoredComparison) -> None:
        self.connection.execute("INSERT INTO comparison_operations(simulation_id) VALUES (?)", (record.simulation_id,))
        self.connection.execute("INSERT INTO saved_comparisons VALUES (?, ?, ?, ?)", (record.simulation_id, record.saved_at, record.record_jcs, record.sha256))

    def summaries(self, limit: int, offset: int) -> list[tuple[str, str]]:
        return self.connection.execute("SELECT simulation_id, saved_at FROM saved_comparisons ORDER BY saved_at DESC, simulation_id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()

    def delete(self, simulation_id: str) -> None:
        self.connection.execute("DELETE FROM saved_comparisons WHERE simulation_id=?", (simulation_id,))


class SqliteComparisonRepository:
    """Open per-operation connections; construction has no filesystem side effects."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = path

    @contextmanager
    def transaction(self, *, write: bool = False) -> Generator[ComparisonTransaction]:
        connection: sqlite3.Connection | None = None
        try:
            path = _path(self.path)
            try:
                if not path.is_file():
                    raise SavedComparisonError("storage_not_initialized", 503)
                connection = sqlite3.connect(path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=5.0, autocommit=True)
            except (OSError, ValueError):
                raise SavedComparisonError("storage_unavailable", 503) from None
            connection.execute("PRAGMA foreign_keys=ON")
            if write:
                connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            _verify_schema(connection)
            yield _Transaction(connection)
            connection.execute("COMMIT")
        except sqlite3.Error as error:
            raise _sql_error(error) from None
        finally:
            if connection is not None:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                connection.close()


def migrate_comparisons(path: str | Path | None = None) -> None:
    """Explicitly initialize v1; never rewrite stored envelopes or downgrade."""
    connection: sqlite3.Connection | None = None
    try:
        target = _path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(target.as_uri() + "?mode=rwc", uri=True, timeout=5.0, autocommit=True)
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        application = connection.execute("PRAGMA application_id").fetchone()[0]
        if version == 0 and application == 0:
            if connection.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone() is not None:
                raise SavedComparisonError("incompatible_storage_version", 409)
            for statement in _SCHEMA:
                connection.execute(statement)
            connection.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
        _verify_schema(connection)
        connection.execute("COMMIT")
    except sqlite3.Error as error:
        raise _sql_error(error) from None
    except (OSError, ValueError):
        raise SavedComparisonError("storage_unavailable", 503) from None
    finally:
        if connection is not None:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            connection.close()
