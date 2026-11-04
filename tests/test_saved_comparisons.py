"""Stored evidence, atomic creation, retry identity and calculation-free retrieval."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from application import saved_comparisons as saved
from domain.comparison import replay_comparison
from domain.consortium.replay_v1 import canonical_json
from domain.values import DomainFailure
from infrastructure.sqlite_comparisons import SqliteComparisonRepository, migrate_comparisons
from tests.test_monthly_resources_comparison import raw_request, request


ID = "00000000-0000-4000-8000-000000000001"
NOW = "2026-11-04T12:00:00Z"


@pytest.fixture
def repository(tmp_path: Path) -> SqliteComparisonRepository:
    path = tmp_path / "synthetic.sqlite3"
    migrate_comparisons(path)
    return SqliteComparisonRepository(path)


def prepare(value: dict[str, object]) -> bytes:
    return canonical_json(value).encode()


def save(repository: SqliteComparisonRepository, raw: dict[str, object] | None = None, operation_id: str = ID) -> saved.PreparedSave:
    return saved.save_comparison(repository, operation_id, raw if raw is not None else raw_request(), prepare, clock=lambda: NOW, snapshot_factory=lambda: "synthetic-stored")


def test_complete_envelope_survives_reopen_and_replays_exactly(repository: SqliteComparisonRepository) -> None:
    created = save(repository)
    assert created.created
    reopened = SqliteComparisonRepository(repository.path)
    assert prepare(saved.read_comparison(reopened, ID)) == created.body
    with reopened.transaction() as transaction:
        _, record = transaction.find(ID)
    assert record is not None
    envelope = saved.decode_record(record, ID)
    verified = replay_comparison(envelope)
    assert not isinstance(verified, DomainFailure)
    assert asdict(verified.envelope) == asdict(envelope)
    wrapper = json.loads(record.record_jcs)
    assert wrapper["envelope"] == asdict(envelope)
    assert "result" not in wrapper
    assert verified.ranking_groups == (("sac", "price"), ("consortium",), ("rent",))


@pytest.mark.parametrize("case", ["no_eligible", "local_admission", "local_execution"])
def test_normal_aggregate_results_and_failed_child_evidence_are_saved(repository: SqliteComparisonRepository, case: str) -> None:
    raw = raw_request(request("0.00", "1.00", "0.00")) if case == "local_execution" else raw_request()
    if case == "no_eligible":
        cast(dict[str, object], raw["constraints"])["maximum_monthly_housing_outflow"] = "0.00"
    if case == "local_admission":
        raw["financing"] = None
    value = json.loads(save(repository, raw).body)["result"]
    assert value["status"] == "no_eligible" if case != "local_admission" else value["alternatives"][0]["status"] == "domain_failure"
    with repository.transaction() as tx:
        _, record = tx.find(ID)
    assert record is not None
    assert not isinstance(replay_comparison(saved.decode_record(record, ID)), DomainFailure)


def test_retry_and_read_never_run_factory_normalization_evaluation_or_replay(repository: SqliteComparisonRepository, monkeypatch: pytest.MonkeyPatch) -> None:
    first = save(repository)
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("financial execution on historical retrieval")
    from domain import comparison, comparison_v2, monthly_resources_v1
    monkeypatch.setattr(saved, "create_comparison_v2_envelope", forbidden)
    monkeypatch.setattr(comparison, "replay_comparison", forbidden)
    monkeypatch.setattr(comparison_v2, "evaluate", forbidden)
    monkeypatch.setattr(monthly_resources_v1, "normalize", forbidden)
    assert save(repository) == saved.PreparedSave(False, first.body)
    assert prepare(saved.read_comparison(repository, ID)) == first.body
    assert saved.list_comparisons(repository)["items"] == [{"simulation_id": ID, "saved_at": NOW}]
    with pytest.raises(saved.SavedComparisonError, match="operation_id_conflict"):
        save(repository, raw_request(request("4.00")))


def test_concurrent_retries_execute_factory_once(repository: SqliteComparisonRepository, monkeypatch: pytest.MonkeyPatch) -> None:
    actual = saved.create_comparison_v2_envelope
    calls: list[None] = []
    def factory(**kwargs: str):
        calls.append(None)
        return actual(**kwargs)
    monkeypatch.setattr(saved, "create_comparison_v2_envelope", factory)
    def execute(_: int) -> saved.PreparedSave:
        return save(repository)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, range(2)))
    assert len(calls) == 1
    assert sorted(result.created for result in results) == [False, True]
    assert results[0].body == results[1].body


@pytest.mark.parametrize("failure", ["global", "presenter", "evidence_limit", "insert"])
def test_failures_roll_back_payload_and_operation_id(repository: SqliteComparisonRepository, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    raw = raw_request()
    presenter = prepare
    if failure == "global":
        raw["monthly_resources"] = None
    elif failure == "presenter":
        def broken(_: dict[str, object]) -> bytes:
            raise ValueError("synthetic presenter failure")
        presenter = broken
    elif failure == "evidence_limit":
        monkeypatch.setattr(saved, "MAX_RECORD_BYTES", 1)
    else:
        from infrastructure import sqlite_comparisons
        actual = sqlite_comparisons._Transaction.insert  # pyright: ignore[reportPrivateUsage]
        def broken_insert(self: object, record: saved.StoredComparison) -> None:
            actual(self, record)  # type: ignore[arg-type]
            raise RuntimeError("synthetic insert failure")
        monkeypatch.setattr(sqlite_comparisons._Transaction, "insert", broken_insert)  # pyright: ignore[reportPrivateUsage]
    with pytest.raises((saved.SavedComparisonError, ValueError, RuntimeError)):
        saved.save_comparison(repository, ID, raw, presenter)
    with repository.transaction() as transaction:
        assert transaction.find(ID) == (False, None)


def test_delete_keeps_only_id_and_late_retry_cannot_resurrect(repository: SqliteComparisonRepository) -> None:
    save(repository)
    saved.delete_comparison(repository, ID)
    saved.delete_comparison(repository, ID)
    assert saved.list_comparisons(repository)["items"] == []
    with repository.transaction() as transaction:
        assert transaction.find(ID) == (True, None)
    with pytest.raises(saved.SavedComparisonError, match="simulation_deleted"):
        save(repository)
    with pytest.raises(saved.SavedComparisonError, match="simulation_deleted"):
        saved.read_comparison(repository, ID)
    with pytest.raises(saved.SavedComparisonError, match="simulation_not_found"):
        saved.delete_comparison(repository, "00000000-0000-4000-8000-000000000002")


@pytest.mark.parametrize("mutation", ["digest", "noncanonical", "id", "indexed_date", "wrapper_id", "wrapper_date", "record_version", "engine", "metadata", "child_request", "child_seal", "child_version", "empty_child", "missing_postings", "missing_normalized"])
def test_corruption_or_incompatibility_never_becomes_a_result(repository: SqliteComparisonRepository, mutation: str) -> None:
    save(repository)
    with repository.transaction() as transaction:
        _, original = transaction.find(ID)
    assert original is not None
    wrapper = json.loads(original.record_jcs)
    if mutation == "digest":
        record = replace(original, sha256="0" * 64)
    elif mutation == "noncanonical":
        text = original.record_jcs + " "
        record = replace(original, record_jcs=text, sha256=hashlib.sha256(text.encode()).hexdigest())
    elif mutation in {"id", "indexed_date"}:
        record = replace(original, **({"simulation_id": "00000000-0000-4000-8000-000000000002"} if mutation == "id" else {"saved_at": "2026-11-05T12:00:00Z"}))
    else:
        if mutation == "wrapper_id":
            wrapper["simulation_id"] = "00000000-0000-4000-8000-000000000002"
        elif mutation == "wrapper_date":
            wrapper["saved_at"] = "2026-11-05T12:00:00Z"
        elif mutation == "record_version":
            wrapper["record_schema_version"] = "unknown"
        elif mutation == "engine":
            wrapper["envelope"]["engine_version"] = "unknown"
            wrapper["envelope"]["raw_request_jcs"] = "not-json"
        elif mutation == "metadata":
            wrapper["envelope"]["data_snapshot_id"] = "other-synthetic"
        else:
            outcome = json.loads(wrapper["envelope"]["sealed_outcome_jcs"])
            child = outcome["trace"]["child_evidence"][0]
            if mutation == "child_request":
                child["raw_request_jcs"] = "{}"
            elif mutation == "child_seal":
                child["sealed_outcome_jcs"] = "not-json"
            elif mutation == "child_version":
                child["versions"]["engine_version"] = "unknown"
            else:
                sealed = json.loads(child["sealed_outcome_jcs"])
                if mutation == "empty_child":
                    sealed = json.loads('{"kind":"success","normalized_input":{},"trace":{}}')
                elif mutation == "missing_postings":
                    sealed["trace"]["resource_postings"] = []
                else:
                    sealed["normalized_input"]["strategy_input"] = {}
                child["sealed_outcome_jcs"] = canonical_json(sealed)
            wrapper["envelope"]["sealed_outcome_jcs"] = canonical_json(outcome)
        text = canonical_json(wrapper)
        record = replace(original, record_jcs=text, sha256=hashlib.sha256(text.encode()).hexdigest())
    with pytest.raises(saved.SavedComparisonError) as error:
        saved.decode_record(record, ID)
    expected = "incompatible_storage_version" if mutation == "record_version" else "incompatible_contract_version" if mutation in {"engine", "child_version"} else "stored_simulation_corrupt"
    assert error.value.code == expected


def test_pagination_is_bounded_and_ties_have_stable_id_order(repository: SqliteComparisonRepository) -> None:
    second = "00000000-0000-4000-8000-000000000002"
    save(repository)
    save(repository, operation_id=second)
    assert saved.list_comparisons(repository, 1)["items"] == [{"simulation_id": second, "saved_at": NOW}]
    assert saved.list_comparisons(repository, 1)["next_offset"] == 1
    assert saved.list_comparisons(repository, 1, 1)["items"] == [{"simulation_id": ID, "saved_at": NOW}]
    with pytest.raises(saved.SavedComparisonError, match="invalid_input"):
        saved.list_comparisons(repository, 51)
