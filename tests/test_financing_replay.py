"""Guarantees for the retained, executable financing replay v1 contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
import unittest

from domain.financing import replay_v1
from domain.financing.price import calculate_price, normalize_price_request
from domain.financing.replay import (
    ReplayVerification,
    SimulationReplayEnvelope,
    create_v1_envelope,
    replay_financing,
)
from domain.financing.sac import calculate_sac, normalize_sac_request
from domain.financing.contracts import FinancingRequest
from domain.values import DomainFailure


def _raw_request(**changes: object) -> str:
    request: dict[str, object] = {
        "comparison_opening_cash": "20000.00",
        "property_price": "1500.00",
        "cash_down_payment": "300.00",
        "principal": "1200.00",
        "term_months": 12,
        "rate_value": "0.01",
        "rate_convention": "effective_monthly",
        "fgts_amount": None,
        "subsidy_amount": None,
        "tax_amount": None,
        "transaction_cost_amount": None,
        "fee_amount": None,
        "insurance_amount": None,
        "indexation": "not_requested",
        "extraordinary_amortization_amount": None,
    }
    request.update(changes)
    return replay_v1.canonical_json(request)


def _envelope(strategy: str = "sac", **changes: object) -> SimulationReplayEnvelope:
    return create_v1_envelope(
        strategy=strategy,  # type: ignore[arg-type]
        raw_request_jcs=_raw_request(**changes),
        data_snapshot_id="synthetic-regression-v1",
    )


def _incompatible(value: object) -> DomainFailure:
    result = replay_financing(value)  # type: ignore[arg-type]
    assert isinstance(result, DomainFailure)
    assert result.code == "incompatible_contract_version"
    return result


def test_sac_and_price_envelopes_replay_complete_traces() -> None:
    for strategy in ("sac", "price"):
        envelope = _envelope(strategy)
        verified = replay_financing(envelope)
        assert isinstance(verified, ReplayVerification)
        outcome = json.loads(envelope.sealed_outcome_jcs)
        assert outcome["kind"] == "success"
        assert len(outcome["trace"]["contractual_schedule"]) == 12
        assert len(outcome["trace"]["comparison_ledger"]) == 61
        assert outcome["trace"]["comparison_ledger"][0]["month"] == 0
        assert outcome["trace"]["comparison_ledger"][-1]["month"] == 60


def test_v1_initially_captures_the_existing_prefee_sac_and_price_outputs() -> None:
    raw = _raw_request()
    values = json.loads(raw)
    request = FinancingRequest(**values)
    for strategy, normalizer, calculator in (
        ("sac", normalize_sac_request, calculate_sac),
        ("price", normalize_price_request, calculate_price),
    ):
        normalized = normalizer(request)
        assert not isinstance(normalized, DomainFailure)
        result = calculator(normalized)
        expected = {
            "contractual_schedule": [
                {
                    "amortization": row.amortization.as_string,
                    "closing_principal_balance": row.closing_principal_balance.as_string,
                    "interest": row.interest.as_string,
                    "month": row.month,
                    "opening_principal_balance": row.opening_principal_balance.as_string,
                    "payment": row.payment.as_string,
                }
                for row in result.contractual_schedule
            ],
            "comparison_ledger": [
                {
                    name: value.as_string if hasattr(value := getattr(row, name), "as_string") else value
                    for name in row.__dataclass_fields__
                }
                for row in result.comparison_ledger
            ],
        }
        outcome = json.loads(_envelope(strategy).sealed_outcome_jcs)
        assert outcome["trace"] == expected


def test_positive_fee_replays_the_historical_typed_failure() -> None:
    envelope = _envelope(fee_amount="1.00")
    outcome = json.loads(envelope.sealed_outcome_jcs)
    assert outcome == {
        "code": "unsupported_contract_clause",
        "detail": "fee_amount is not supported",
        "kind": "failure",
    }
    assert isinstance(replay_financing(envelope), ReplayVerification)


def test_replay_rejects_normalized_trace_and_failure_mismatches() -> None:
    success = _envelope()
    success_outcome = json.loads(success.sealed_outcome_jcs)
    success_outcome["normalized_input"]["principal"] = "1200.01"
    normalized_mismatch = replace(success, sealed_outcome_jcs=replay_v1.canonical_json(success_outcome))
    _incompatible(normalized_mismatch)

    success_outcome = json.loads(success.sealed_outcome_jcs)
    success_outcome["trace"]["contractual_schedule"][0]["payment"] = "0.00"
    trace_mismatch = replace(success, sealed_outcome_jcs=replay_v1.canonical_json(success_outcome))
    _incompatible(trace_mismatch)

    failure = _envelope(fee_amount="1.00")
    failure_outcome = json.loads(failure.sealed_outcome_jcs)
    failure_outcome["detail"] = "different safe detail"
    failure_mismatch = replace(failure, sealed_outcome_jcs=replay_v1.canonical_json(failure_outcome))
    _incompatible(failure_mismatch)

    failure_outcome = json.loads(failure.sealed_outcome_jcs)
    failure_outcome["code"] = "invalid_input"
    code_mismatch = replace(failure, sealed_outcome_jcs=replay_v1.canonical_json(failure_outcome))
    _incompatible(code_mismatch)


def test_replay_fails_closed_for_unknown_versions_and_invalid_evidence() -> None:
    envelope = _envelope()
    _incompatible(replace(envelope, contract_schema_version="financing-replay-v2"))
    _incompatible(replace(envelope, engine_version="financing-fixed-principal-v2"))
    _incompatible(replace(envelope, ruleset_version="financing-ruleset-v2"))
    _incompatible(replace(envelope, strategy="price"))

    object.__setattr__(envelope, "sealed_outcome_jcs", "{}")
    _incompatible(envelope)


def test_raw_request_must_be_complete_canonical_and_duplicate_free() -> None:
    canonical = _raw_request()
    noncanonical = json.dumps(json.loads(canonical), ensure_ascii=False, indent=2)
    try:
        create_v1_envelope(strategy="sac", raw_request_jcs=noncanonical, data_snapshot_id="synthetic-regression-v1")
    except ValueError:
        pass
    else:
        raise AssertionError("noncanonical raw request must be rejected")

    duplicate = canonical[:-1] + ',"principal":"1200.00"}'
    try:
        create_v1_envelope(strategy="sac", raw_request_jcs=duplicate, data_snapshot_id="synthetic-regression-v1")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate raw request keys must be rejected")

    try:
        _envelope(term_months=9_007_199_254_740_992)
    except ValueError:
        pass
    else:
        raise AssertionError("non-JCS-safe terms must be rejected")


def test_term_boundary_is_semantic_and_complete() -> None:
    maximum = _envelope(term_months=600)
    maximum_outcome = json.loads(maximum.sealed_outcome_jcs)
    assert maximum_outcome["kind"] == "success"
    assert len(maximum_outcome["trace"]["contractual_schedule"]) == 600
    assert isinstance(replay_financing(maximum), ReplayVerification)

    oversized = _envelope(term_months=601)
    assert json.loads(oversized.sealed_outcome_jcs) == {
        "code": "invalid_input",
        "detail": "term_months exceeds v1 maximum of 600",
        "kind": "failure",
    }
    assert isinstance(replay_financing(oversized), ReplayVerification)


def test_envelope_is_immutable_and_only_an_envelope_is_replayable() -> None:
    envelope = _envelope()
    try:
        envelope.engine_version = "changed"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("replay envelope must be immutable")
    _incompatible({"sealed_outcome_jcs": envelope.sealed_outcome_jcs})


def load_tests(
    loader: unittest.TestLoader,
    standard_tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    """Expose function tests without a test-only implementation class."""
    tests = (
        test_sac_and_price_envelopes_replay_complete_traces,
        test_v1_initially_captures_the_existing_prefee_sac_and_price_outputs,
        test_positive_fee_replays_the_historical_typed_failure,
        test_replay_rejects_normalized_trace_and_failure_mismatches,
        test_replay_fails_closed_for_unknown_versions_and_invalid_evidence,
        test_raw_request_must_be_complete_canonical_and_duplicate_free,
        test_term_boundary_is_semantic_and_complete,
        test_envelope_is_immutable_and_only_an_envelope_is_replayable,
    )
    return unittest.TestSuite(unittest.FunctionTestCase(test) for test in tests)
