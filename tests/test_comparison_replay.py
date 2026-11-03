"""Exact retained simulation evidence, version admission and failure replay."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from decimal import ROUND_DOWN, localcontext
from pathlib import Path
from typing import cast

import pytest

from domain import comparison_v1, rent_replay_v1
from domain.comparison import (
    ComparisonSimulationEnvelope, create_comparison_v1_envelope, replay_comparison,
)
from domain.consortium import replay_v1 as codec
from domain.financing import replay_v3
from domain.values import DomainFailure
from tests.test_comparison_domain import raw_outcome, raw_request, result, synthetic_request


def envelope(raw: dict[str, object] | None = None) -> ComparisonSimulationEnvelope:
    return create_comparison_v1_envelope(
        raw_request_jcs=codec.canonical_json(raw if raw is not None else raw_request()),
        data_snapshot_id="synthetic-comparison-reference-v1", calculated_at="2026-11-03T12:00:00Z",
    )


def test_complete_evidence_versions_classifications_and_explicit_creation() -> None:
    value = result()
    assert replay_comparison(value.envelope) == value
    bound = codec.parse_canonical_object(value.envelope.raw_request_jcs)
    outcome = codec.parse_canonical_object(value.envelope.sealed_outcome_jcs)
    assert bound["metadata"] == outcome["metadata"]
    assert bound["comparison"] == raw_request()
    normalized = cast(dict[str, object], outcome["normalized_input"])
    assert cast(dict[str, object], normalized["rule_conventions"])["reference_basis"] == "synthetic_contract_reference"
    evidence = cast(list[dict[str, object]], cast(dict[str, object], outcome["trace"])["child_evidence"])
    assert [entry["strategy"] for entry in evidence] == ["sac", "price", "rent", "consortium"]
    for entry in evidence:
        raw = codec.parse_canonical_object(entry["raw_request_jcs"])
        assert raw["comparison_opening_cash"] == "200.00"
        assert cast(dict[str, object], entry["input_classification"])["comparison_opening_cash"] == "observed_data"
        assert "sealed_outcome_jcs" in entry and "admission_failure" not in entry
    assert cast(dict[str, object], evidence[2]["versions"])["engine_version"] == "rent-plus-fixed-cash-v1"
    assert value.envelope.engine_version == "comparison-minimum-v1"
    assert value.envelope.ruleset_version == "comparison-ruleset-v1"
    with pytest.raises(FrozenInstanceError):
        setattr(value.envelope, "sealed_outcome_jcs", "{}")


@pytest.mark.parametrize("raw", ["{}", '{"shared":null}'])
def test_canonical_global_failures_are_sealed_and_replayed(raw: str) -> None:
    value = create_comparison_v1_envelope(raw_request_jcs=raw, data_snapshot_id="synthetic", calculated_at="2026-11-03T12:00:00Z")
    replay = replay_comparison(value)
    assert isinstance(replay, DomainFailure) and replay.code == "invalid_input"
    assert codec.parse_canonical_object(value.sealed_outcome_jcs)["kind"] == "failure"


@pytest.mark.parametrize("raw", ["", "[]", "null", '{"x":1,"x":1}', '{ "x": 1 }', '{"x":1.0}', '{"x":NaN}'])
def test_noncanonical_representation_never_creates_evidence(raw: str) -> None:
    with pytest.raises(ValueError):
        create_comparison_v1_envelope(raw_request_jcs=raw, data_snapshot_id="synthetic", calculated_at="2026-11-03T12:00:00Z")


@pytest.mark.parametrize(("snapshot", "timestamp"), [
    ("", "2026-11-03T12:00:00Z"), ("private value", "2026-11-03T12:00:00Z"),
    ("synthetic", "2026-11-03T12:00:00+00:00"), ("synthetic", "2026-02-30T12:00:00Z"),
    ("synthetic", "2026-11-03T12:00:00.0Z"), ("synthetic", "2026-11-03"),
])
def test_invalid_supplied_metadata_is_rejected(snapshot: str, timestamp: str) -> None:
    with pytest.raises(ValueError):
        create_comparison_v1_envelope(raw_request_jcs="{}", data_snapshot_id=snapshot, calculated_at=timestamp)


@pytest.mark.parametrize("field", ["contract_schema_version", "engine_version", "ruleset_version"])
def test_unknown_versions_are_rejected_before_interpreting_raw(field: str) -> None:
    value = replace(envelope(), **{field: "unavailable"}, raw_request_jcs="not-json")
    failed = replay_comparison(value)
    assert isinstance(failed, DomainFailure) and failed.code == "incompatible_contract_version"


@pytest.mark.parametrize("mutation", ["request", "normalized", "metric", "group", "constraint", "child", "metadata", "failure", "raw_noncanonical", "sealed_noncanonical"])
def test_tampered_inputs_outcomes_and_trace_fail_exact_reexecution(mutation: str) -> None:
    original = envelope()
    bound = codec.parse_canonical_object(original.raw_request_jcs)
    outcome = codec.parse_canonical_object(original.sealed_outcome_jcs)
    if mutation == "request":
        cast(dict[str, object], cast(dict[str, object], bound["comparison"])["constraints"])["minimum_liquidity"] = "1.00"
    elif mutation == "normalized":
        cast(dict[str, object], cast(dict[str, object], outcome["normalized_input"])["shared"])["comparison_opening_cash"] = "200.01"
    elif mutation == "metric":
        metrics = cast(dict[str, object], cast(list[dict[str, object]], outcome["alternatives"])[0]["metrics"])
        cast(dict[str, object], metrics["final_ledger_row"])["net_worth"] = "200.01"
    elif mutation == "group":
        cast(dict[str, object], outcome["result"])["ranking_groups"] = [["rent"]]
    elif mutation == "constraint":
        cast(list[dict[str, object]], outcome["alternatives"])[0]["violations"] = [{"month": 1}]
    elif mutation == "child":
        cast(list[dict[str, object]], cast(dict[str, object], outcome["trace"])["child_evidence"])[0]["sealed_outcome_jcs"] = "{}"
    elif mutation == "metadata":
        cast(dict[str, object], bound["metadata"])["calculated_at"] = "2026-11-03T12:00:01Z"
    elif mutation == "failure":
        outcome = {"kind": "failure", "code": "invalid_input", "detail": "changed", "metadata": bound["metadata"]}
    raw = codec.canonical_json(bound)
    sealed = codec.canonical_json(outcome)
    if mutation == "raw_noncanonical":
        raw += " "
    if mutation == "sealed_noncanonical":
        sealed += " "
    failed = replay_comparison(replace(original, raw_request_jcs=raw, sealed_outcome_jcs=sealed))
    assert isinstance(failed, DomainFailure) and failed.code == "incompatible_contract_version"


@pytest.mark.parametrize(("field", "value"), [
    ("data_snapshot_id", "different-synthetic"), ("calculated_at", "2026-11-03T12:00:01Z"),
])
def test_header_metadata_must_equal_bound_request(field: str, value: str) -> None:
    failed = replay_comparison(replace(envelope(), **{field: value}))
    assert isinstance(failed, DomainFailure) and failed.code == "incompatible_contract_version"


def test_admission_failure_has_parent_evidence_without_fabricated_child_outcome() -> None:
    raw = raw_request()
    del cast(dict[str, object], raw["financing"])["principal"]
    value = envelope(raw)
    outcome = codec.parse_canonical_object(value.sealed_outcome_jcs)
    evidence = cast(list[dict[str, object]], cast(dict[str, object], outcome["trace"])["child_evidence"])
    assert "admission_failure" in evidence[0] and "sealed_outcome_jcs" not in evidence[0]
    assert codec.parse_canonical_object(evidence[0]["raw_request_jcs"]) == raw["financing"]
    replay = replay_comparison(value)
    assert not isinstance(replay, DomainFailure)
    assert replay.alternatives[0].failure is not None
    assert replay.alternatives[0].failure.code == "invalid_input"


@pytest.mark.parametrize("exception", [ValueError, RuntimeError, ArithmeticError])
def test_unexpected_execution_error_is_never_admission_failure(
    monkeypatch: pytest.MonkeyPatch, exception: type[Exception],
) -> None:
    value = envelope()
    def broken(*args: object) -> str:
        raise exception("injected engine execution error")
    monkeypatch.setattr(replay_v3, "evaluate", broken)
    with pytest.raises(exception, match="injected engine"):
        envelope()
    failed = replay_comparison(value)
    assert isinstance(failed, DomainFailure) and failed.code == "incompatible_contract_version"
    raw = raw_request()
    del cast(dict[str, object], raw["financing"])["principal"]
    # Preflight still seals known invalid structure without calling evaluate.
    assert raw_outcome(raw)["kind"] == "success"


def test_retained_evaluators_ignore_live_calculators_and_pin_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    from domain import rent_plus_investment
    from domain.financing import v3
    value = envelope()
    def broken(*args: object) -> None:
        raise AssertionError("mutable live calculator used")
    monkeypatch.setattr(rent_plus_investment, "calculate_rent_plus_investment", broken)
    monkeypatch.setattr(v3, "calculate_sac_v3", broken)
    assert not isinstance(replay_comparison(value), DomainFailure)
    expected = {
        "domain/rent_replay_v1.py": {("domain.consortium", "replay_v1")},
        "domain/comparison_v1.py": {("domain.consortium", "replay_v1"), ("domain.financing", "replay_v3"), ("domain", "rent_replay_v1")},
    }
    for path, permitted in expected.items():
        tree = ast.parse(Path(path).read_text())
        found: set[tuple[str, str]] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("domain"):
                found.update((node.module, alias.name) for alias in node.names)
            elif isinstance(node, ast.Import):
                assert all(not alias.name.startswith("domain") for alias in node.names)
        assert found == permitted


def test_bound_input_precision_does_not_inherit_decimal_context() -> None:
    raw = raw_request()
    # Relationship sums exceed caller precision, but stay in the admitted envelope.
    cast(dict[str, object], raw["financing"]).update(property_price="60.00", cash_down_payment="1.01", principal="58.99")
    baseline = envelope(raw)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert envelope(raw) == baseline
        assert not isinstance(replay_comparison(baseline), DomainFailure)


@pytest.mark.parametrize("mutation", ["shared_type", "constraints_type", "shared_extra", "constraints_extra", "child_type", "schedule_type", "row_type", "row_missing", "row_month", "row_amount", "term", "waiting_type"])
def test_closed_structure_and_nested_admission(mutation: str) -> None:
    raw = raw_request()
    child = cast(dict[str, object], raw["consortium"])
    if mutation == "shared_type":
        raw["shared"] = None
    elif mutation == "constraints_type":
        raw["constraints"] = []
    elif mutation == "shared_extra":
        cast(dict[str, object], raw["shared"])["income"] = "1.00"
    elif mutation == "constraints_extra":
        cast(dict[str, object], raw["constraints"])["weight"] = "1"
    elif mutation == "child_type":
        raw["consortium"] = []
    elif mutation == "schedule_type":
        child["monthly_schedule"] = None
    elif mutation == "row_type":
        cast(list[object], child["monthly_schedule"])[0] = None
    elif mutation == "row_missing":
        del cast(list[dict[str, object]], child["monthly_schedule"])[0]["credit_component"]
    elif mutation == "row_month":
        cast(list[dict[str, object]], child["monthly_schedule"])[0]["month"] = True
    elif mutation == "row_amount":
        cast(list[dict[str, object]], child["monthly_schedule"])[0]["insurance"] = "1e2"
    elif mutation == "term":
        child["term_months"] = 601
    elif mutation == "waiting_type":
        child["waiting_housing_costs"] = None
    outcome = raw_outcome(raw)
    if mutation.startswith(("shared", "constraints")):
        assert outcome["kind"] == "failure"
    else:
        assert outcome["kind"] == "success"
        assert cast(list[dict[str, object]], outcome["alternatives"])[3]["status"] == "domain_failure"


def test_retained_rent_rejects_noncanonical_or_unclosed_evidence() -> None:
    with pytest.raises(ValueError):
        rent_replay_v1.evaluate("[]")
    assert codec.parse_canonical_object(rent_replay_v1.evaluate("{}"))["kind"] == "failure"
    raw = raw_request(synthetic_request())
    rent = cast(dict[str, object], raw["rent"])
    assert codec.parse_canonical_object(rent_replay_v1.evaluate(codec.canonical_json(rent)))["kind"] == "success"
    rent["tax_amount"] = "1.00"
    assert codec.parse_canonical_object(rent_replay_v1.evaluate(codec.canonical_json(rent)))["code"] == "unsupported_rule"


@pytest.mark.parametrize("metadata", [None, {}, {"data_snapshot_id": "synthetic", "calculated_at": "2026-11-03T12:00:00Z", "timezone": "UTC"}])
def test_retained_metadata_rejects_unbound_shapes(metadata: object) -> None:
    with pytest.raises(ValueError):
        comparison_v1.validate_metadata(metadata)
    with pytest.raises(ValueError):
        comparison_v1.evaluate("{}")
