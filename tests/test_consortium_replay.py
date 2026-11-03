"""Version, canonical evidence and exact historical consortium reexecution."""

import ast
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
from typing import cast

import pytest

from domain.consortium import replay_v1
from domain.consortium.replay import (
    ConsortiumReplayEnvelope, ConsortiumReplayVerification,
    create_consortium_v1_envelope, replay_consortium,
)
from domain.consortium.v1 import calculate_consortium_v1, normalize_consortium_request_v1
from domain.values import DomainFailure
from tests.test_consortium_domain import synthetic_request, raw_request


def _envelope(raw: dict[str, object] | None = None) -> ConsortiumReplayEnvelope:
    return create_consortium_v1_envelope(
        raw_request_jcs=replay_v1.canonical_json(raw_request() if raw is None else raw),
        data_snapshot_id="synthetic-consortium-v1",
    )


def _incompatible(envelope: object) -> None:
    result = replay_consortium(cast(ConsortiumReplayEnvelope, envelope))
    assert isinstance(result, DomainFailure) and result.code == "incompatible_contract_version"


def test_replay_envelope_contains_complete_normalized_evidence_and_typed_projection() -> None:
    envelope = _envelope()
    assert envelope.contract_schema_version == "consortium-replay-v1"
    assert envelope.engine_version == "consortium-explicit-schedule-v1"
    assert envelope.ruleset_version == "consortium-ruleset-v1"
    assert envelope.strategy == "consortium" and envelope.data_snapshot_id == "synthetic-consortium-v1"
    outcome = json.loads(envelope.sealed_outcome_jcs)
    trace = outcome["trace"]
    assert len(trace["contractual_schedule"]) == 10
    assert len(trace["monthly_postings"]) == 60
    assert len(trace["comparison_ledger"]) == 61
    assert outcome["normalized_input"]["rule_conventions"]["ruleset_version"] == envelope.ruleset_version
    assert isinstance(replay_consortium(envelope), ConsortiumReplayVerification)
    assert _envelope() == envelope
    normalized = normalize_consortium_request_v1(synthetic_request())
    assert not isinstance(normalized, DomainFailure)
    result = calculate_consortium_v1(normalized)
    for projected, canonical in zip(result.comparison_ledger, trace["comparison_ledger"], strict=True):
        assert projected.month == canonical["month"]
        for key, expected in canonical.items():
            if key != "month":
                assert getattr(projected, key).as_string == expected
    with pytest.raises(FrozenInstanceError):
        setattr(envelope, "engine_version", "changed")


@pytest.mark.parametrize(("changes", "code"), [
    ({"term_months": True}, "invalid_input"), ({"correction": "requested_nonzero"}, "unsupported_contract_clause"),
    ({"requested_features": ["tax"]}, "unsupported_rule"),
    ({"comparison_opening_cash": "0.00"}, "infeasible_scenario"),
])
def test_canonical_domain_failures_are_sealed_and_reexecuted(changes: dict[str, object], code: str) -> None:
    raw = raw_request()
    raw.update(changes)
    envelope = _envelope(raw)
    outcome = json.loads(envelope.sealed_outcome_jcs)
    assert set(outcome) == {"kind", "code", "detail"}
    assert outcome["kind"] == "failure" and outcome["code"] == code
    assert isinstance(replay_consortium(envelope), ConsortiumReplayVerification)
    outcome["detail"] = "different safe detail"
    _incompatible(replace(envelope, sealed_outcome_jcs=replay_v1.canonical_json(outcome)))


def test_empty_canonical_request_can_record_invalid_input() -> None:
    envelope = _envelope({})
    assert json.loads(envelope.sealed_outcome_jcs)["code"] == "invalid_input"
    assert isinstance(replay_consortium(envelope), ConsortiumReplayVerification)


@pytest.mark.parametrize("raw", [
    "{", "[]", "null", " {}", '{"a":1,"a":1}', '{"a":NaN}', '{"a":Infinity}',
    '{"a":1.0}', '{"a":1e0}', '{"a":9007199254740992}', '{"b":0,"a":0}',
    '{"a":"\\ud800"}',
])
def test_factory_rejects_malformed_or_noncanonical_evidence(raw: str) -> None:
    with pytest.raises(ValueError):
        create_consortium_v1_envelope(raw_request_jcs=raw, data_snapshot_id="synthetic-v1")
    _incompatible(replace(_envelope(), raw_request_jcs=raw))


@pytest.mark.parametrize("field", ["contract_schema_version", "engine_version", "ruleset_version"])
def test_unknown_version_is_rejected_before_interpreting_raw_evidence(field: str) -> None:
    envelope = replace(_envelope(), **{field: "unknown-version"}, raw_request_jcs="not JSON")
    _incompatible(envelope)


@pytest.mark.parametrize("mutation", ["request", "normalized", "cash", "noncash", "schedule", "missing", "extra", "kind", "failure"])
def test_any_changed_evidence_fails_exact_reexecution(mutation: str) -> None:
    envelope = _envelope()
    outcome = json.loads(envelope.sealed_outcome_jcs)
    if mutation == "request":
        raw = raw_request()
        raw["comparison_opening_cash"] = "20000.01"
        _incompatible(replace(envelope, raw_request_jcs=replay_v1.canonical_json(raw)))
        return
    if mutation == "normalized":
        outcome["normalized_input"]["input_classification"]["credit_letter"] = "projected_assumption"
    elif mutation == "cash":
        outcome["trace"]["comparison_ledger"][4]["cash"] = "19560.01"
    elif mutation == "noncash":
        outcome["trace"]["monthly_postings"][3]["credit_letter_applied"] = "0.00"
    elif mutation == "schedule":
        outcome["trace"]["contractual_schedule"][-1]["credit_component"] = "99.99"
    elif mutation == "missing":
        outcome["trace"]["comparison_ledger"].pop()
    elif mutation == "extra":
        outcome["trace"]["probability"] = "0.5"
    elif mutation == "kind":
        outcome["kind"] = "unknown"
    else:
        outcome = {"kind": "failure", "code": "invalid_input", "detail": "forged failure"}
    _incompatible(replace(envelope, sealed_outcome_jcs=replay_v1.canonical_json(outcome)))


@pytest.mark.parametrize("outcome", ["[]", "{}", " { }", "not JSON", '{"kind":"success","kind":"failure"}'])
def test_invalid_sealed_outcome_never_becomes_a_stored_result_fallback(outcome: str) -> None:
    _incompatible(replace(_envelope(), sealed_outcome_jcs=outcome))


def test_container_validation_rejects_missing_snapshot_cross_strategy_and_runtime_types() -> None:
    envelope = _envelope()
    for field, value in (("data_snapshot_id", ""), ("engine_version", None), ("raw_request_jcs", 1), ("sealed_outcome_jcs", None), ("strategy", "sac")):
        with pytest.raises(ValueError):
            replace(envelope, **{field: value})
    _incompatible(None)
    _incompatible({})
    # Even bypassing a frozen dataclass does not bypass replay admission.
    object.__setattr__(envelope, "data_snapshot_id", None)
    _incompatible(envelope)


@pytest.mark.parametrize("value", [1.0, float("nan"), 9_007_199_254_740_992, {1: "invalid"}, (1, 2), "\ud800"])
def test_codec_rejects_values_outside_the_closed_jcs_domain(value: object) -> None:
    with pytest.raises(ValueError):
        replay_v1.canonical_json(value)


def test_codec_orders_utf16_keys_and_supports_nested_safe_values() -> None:
    value = {"\U0001f600": [None, True, False, -1], "\ue000": "value"}
    canonical = replay_v1.canonical_json(value)
    assert canonical.startswith('{"\U0001f600":')
    assert replay_v1.parse_canonical_object(canonical) == value
    with pytest.raises(ValueError):
        replay_v1.parse_canonical_object(None)
    invalid = replace(synthetic_request(), cash_top_up=cast(str, 1.0))
    result = normalize_consortium_request_v1(invalid)
    assert isinstance(result, DomainFailure) and result.code == "invalid_input"


def test_retained_evaluator_has_no_live_domain_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    path = Path("domain/consortium/replay_v1.py")
    tree = ast.parse(path.read_text())
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    imports.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
    assert all(module is not None and not module.startswith(("domain", "api", "application")) for module in imports)
    envelope = _envelope()
    from domain import ledger
    monkeypatch.setattr(ledger, "COMPARISON_MONTHS", 1)
    assert _envelope() == envelope
    assert isinstance(replay_consortium(envelope), ConsortiumReplayVerification)


def test_integer_string_guard_cannot_change_a_valid_historical_outcome() -> None:
    raw = raw_request()
    raw["comparison_opening_cash"] = "1" + "0" * 700 + ".00"
    original_limit = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        baseline = _envelope(raw)
        assert json.loads(baseline.sealed_outcome_jcs)["kind"] == "success"
        sys.set_int_max_str_digits(640)
        assert _envelope(raw) == baseline
        assert isinstance(replay_consortium(baseline), ConsortiumReplayVerification)
    finally:
        sys.set_int_max_str_digits(original_limit)
