"""Regression guarantees for centavo-safe versioned financing settlement."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
from decimal import Decimal, ROUND_DOWN, localcontext
import hashlib
import json
from typing import Callable, cast

import pytest

from domain.financing import replay_v1, replay_v3
from domain.financing.price import (
    PriceRequest,
    calculate_price_v2,
    calculate_price_v3,
    normalize_price_request_v2,
    normalize_price_request_v3,
)
from domain.financing.replay import (
    ReplayVerification,
    SimulationReplayEnvelope,
    create_v1_envelope,
    create_v2_envelope,
    create_v3_envelope,
    replay_financing,
)
from domain.financing.replay import Strategy
from domain.financing.sac import (
    SACRequest,
    calculate_sac_v2,
    calculate_sac_v3,
    normalize_sac_request_v2,
    normalize_sac_request_v3,
)
from domain.financing.v3 import NormalizedV3FinancingInput
from domain.values import DomainFailure


_BASE_REQUEST: dict[str, object] = {
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
_MINIMAL_REQUEST: dict[str, object] = {
    **_BASE_REQUEST,
    "comparison_opening_cash": "0.00",
    "property_price": "1.00",
    "cash_down_payment": "0.00",
    "principal": "1.00",
    "term_months": 18,
}
_HISTORICAL_HASHES = {
    "v1_price_baseline": "0783a2982f937e8748ca69b3cb7172adf4b0d0557564549ddfa0c038996365d5",
    "v1_price_minimal_nonzero": "ef1f7d23f91f505227d2efb2a5aa22ff5319b1853f7d8927b8714ad191274f9c",
    "v1_sac_baseline": "4c339708f0b1277b98477c941bd57ac37c18fe07b351dc65dd5580c9ee32be16",
    "v1_sac_fee_failure": "1ad9a2f74fc43e90b9e139b1db9e862f33bf22cacd778f522232ba6847c96e38",
    "v1_sac_minimal_nonzero": "f2c2eb7181ced88b9f5885b93456f9d16684e184a90400f50044fff45f6933d5",
    "v1_sac_minimal_zero": "fb7e1b4602ce8a079d7dd3a4cd50bfd2e3665dcd19355c7c8a290df187b87863",
    "v1_price_minimal_zero": "1cdaa57dd03cb7ff192db1c4d177706f14624ff91c5d3f9e988d09469d4b5cd2",
    "v2_price_baseline_fee": "0e3bde71279c05a59d65ca1c17ae5c85ec3015b9cf7c417606ca2c9091f71066",
    "v2_price_minimal_fee": "0e21e83ba8f06b157840765fc0c658b6641982faa1e6da9995de361492ce44ef",
    "v2_price_minimal_nonzero": "599cc2620272827d2082f0424b65b80dd52223aef298c3761ba180b1b3cd83c2",
    "v2_price_minimal_zero": "5ddaa8d3b6faab59ec4a1f23e225b1acf98557e84ecfa3ab8615d28eead4aa3f",
    "v2_sac_baseline_fee": "edd8ff68c2524cbc8c16e659cd3703172ce254652fb5d85726e79dafc67e2d3f",
    "v2_sac_minimal_fee": "4718e16b71b9e17dada96631c155c1a835a0fc91830d591db9664c83a1e57736",
    "v2_sac_minimal_nonzero": "f5f32954f1e9a2120296c790bd0a8fbc7feaadc1f9529275bb4fa743deee180b",
    "v2_sac_minimal_zero": "26eb6e1447094f386276fdb4fb2f66582e867ac7d4a8b25d89e9253f7ca48cae",
}


def _request(**changes: object) -> dict[str, object]:
    return {**_BASE_REQUEST, **changes}


def _raw_request(**changes: object) -> str:
    return replay_v3.canonical_json(_request(**changes))


def _envelope(strategy: Strategy = "sac", **changes: object) -> SimulationReplayEnvelope:
    return create_v3_envelope(
        strategy=strategy,
        raw_request_jcs=_raw_request(**changes),
        data_snapshot_id="synthetic-regression-v3",
    )


def _outcome(strategy: Strategy = "sac", **changes: object) -> dict[str, object]:
    return json.loads(replay_v3.evaluate(_raw_request(**changes), strategy))


def _sac_request(**changes: object) -> SACRequest:
    return cast(Callable[..., SACRequest], SACRequest)(**_request(**changes))


def _price_request(**changes: object) -> PriceRequest:
    return cast(Callable[..., PriceRequest], PriceRequest)(**_request(**changes))


def _hash(envelope: SimulationReplayEnvelope) -> str:
    canonical = replay_v1.canonical_json(asdict(envelope))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(detail)


def _cents(value: object) -> int:
    _require(isinstance(value, str), "centavo amount must be a string")
    text = cast(str, value)
    whole, fraction = text.removeprefix("-").split(".")
    _require(
        len(fraction) == 2 and fraction.isdigit(),
        "centavo amount must have an exact two-digit fraction",
    )
    sign = -1 if text.startswith("-") else 1
    return sign * (int(whole) * 100 + int(fraction))


def _detail(detail: str, case: str) -> str:
    return f"{detail}: {case}" if case else detail


def _assert_trace_identities(outcome: dict[str, object], case: str = "") -> None:
    _require(outcome["kind"] == "success", _detail("outcome must succeed", case))
    trace = cast(dict[str, list[dict[str, object]]], outcome["trace"])
    schedule = trace["contractual_schedule"]
    ledger = trace["comparison_ledger"]
    previous_closing: int | None = None
    for position, row in enumerate(schedule, start=1):
        opening = _cents(row["opening_principal_balance"])
        interest = _cents(row["interest"])
        amortization = _cents(row["amortization"])
        fee = _cents(row["fee"])
        payment = _cents(row["payment"])
        closing = _cents(row["closing_principal_balance"])
        if previous_closing is not None:
            _require(
                opening == previous_closing,
                _detail("schedule balances must be continuous", case),
            )
        _require(
            opening >= 0
            and interest >= 0
            and amortization >= 0
            and fee >= 0
            and closing >= 0
            and payment == interest + amortization + fee
            and closing == opening - amortization,
            _detail("schedule identity is invalid", case),
        )
        if position < len(schedule):
            _require(
                closing >= 1,
                _detail("non-final schedule rows must retain at least R$0.01", case),
            )
        else:
            _require(closing == 0, _detail("final schedule row must settle", case))
        previous_closing = closing
    _require(previous_closing == 0, _detail("schedule must settle", case))

    previous_ledger: dict[str, object] | None = None
    for row in ledger:
        month = cast(int, row["month"])
        principal = _cents(row["financing_principal_balance"])
        cost = _cents(row["nonrecoverable_housing_cost"])
        cash = _cents(row["cash"])
        cumulative = _cents(row["cumulative_housing_cost"])
        _require(principal >= 0, _detail("ledger principal cannot be negative", case))
        if 1 <= month <= len(schedule):
            posting = schedule[month - 1]
            expected_cost = _cents(posting["interest"]) + _cents(posting["fee"])
            if previous_ledger is None:
                raise AssertionError(_detail("schedule ledger must have an opening row", case))
            _require(
                principal == _cents(posting["closing_principal_balance"])
                and cost == expected_cost
                and cash == _cents(previous_ledger["cash"]) - _cents(posting["payment"]),
                _detail("posted schedule and ledger diverge", case),
            )
        elif previous_ledger is not None:
            _require(
                principal == 0 and cost == 0 and cash == _cents(previous_ledger["cash"]),
                _detail("ledger must remain settled after the schedule", case),
            )
        total_liabilities = _cents(row["total_liabilities"])
        _require(
            total_liabilities == principal + _cents(row["consortium_credit_obligation_balance"])
            and _cents(row["home_equity"]) == _cents(row["property_value"]) - total_liabilities
            and _cents(row["liquidity"]) == cash + _cents(row["liquid_financial_assets"])
            and _cents(row["net_worth"])
            == (
                cash
                + _cents(row["liquid_financial_assets"])
                + _cents(row["consortium_credit_right_balance"])
                + _cents(row["property_value"])
                - total_liabilities
            ),
            _detail("ledger accounting identity is invalid", case),
        )
        expected_cumulative = cost
        if previous_ledger is not None:
            expected_cumulative += _cents(previous_ledger["cumulative_housing_cost"])
        _require(cumulative == expected_cumulative, _detail("cumulative cost is invalid", case))
        previous_ledger = row


def test_v1_and_v2_canonical_envelopes_are_byte_stable() -> None:
    cases = {
        "v1_sac_baseline": create_v1_envelope(
            strategy="sac",
            raw_request_jcs=replay_v1.canonical_json(_request()),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v1_price_baseline": create_v1_envelope(
            strategy="price",
            raw_request_jcs=replay_v1.canonical_json(_request()),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v1_sac_fee_failure": create_v1_envelope(
            strategy="sac",
            raw_request_jcs=replay_v1.canonical_json(_request(fee_amount="0.01")),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v1_sac_minimal_zero": create_v1_envelope(
            strategy="sac",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "rate_value": "0.0000"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v1_sac_minimal_nonzero": create_v1_envelope(
            strategy="sac",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "rate_value": "0.0001"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v1_price_minimal_zero": create_v1_envelope(
            strategy="price",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "rate_value": "0.0000"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v1_price_minimal_nonzero": create_v1_envelope(
            strategy="price",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "rate_value": "0.0001"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v2_sac_baseline_fee": create_v2_envelope(
            strategy="sac",
            raw_request_jcs=replay_v1.canonical_json(_request(fee_amount="0.01")),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v2_price_baseline_fee": create_v2_envelope(
            strategy="price",
            raw_request_jcs=replay_v1.canonical_json(_request(fee_amount="0.01")),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v2_sac_minimal_zero": create_v2_envelope(
            strategy="sac",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "rate_value": "0.0000"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v2_sac_minimal_nonzero": create_v2_envelope(
            strategy="sac",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "rate_value": "0.0001"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v2_price_minimal_zero": create_v2_envelope(
            strategy="price",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "rate_value": "0.0000"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v2_price_minimal_nonzero": create_v2_envelope(
            strategy="price",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "rate_value": "0.0001"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v2_sac_minimal_fee": create_v2_envelope(
            strategy="sac",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "fee_amount": "0.01"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
        "v2_price_minimal_fee": create_v2_envelope(
            strategy="price",
            raw_request_jcs=replay_v1.canonical_json({**_MINIMAL_REQUEST, "fee_amount": "0.01"}),
            data_snapshot_id="synthetic-hash-v1-v2",
        ),
    }
    assert {name: _hash(envelope) for name, envelope in cases.items()} == _HISTORICAL_HASHES


@pytest.mark.parametrize("strategy", ("sac", "price"))
@pytest.mark.parametrize("rate", ("0.0000", "0.0001"))
@pytest.mark.parametrize("fee", (None, "0.01"), ids=("fee-absent", "fee-0.01"))
def test_v3_minimal_counterexamples_have_exact_centavo_safe_settlement(
    strategy: Strategy, rate: str, fee: str | None
) -> None:
    expected_amortization = ["0.06"] * 16 + ["0.03", "0.01"]
    case = f"strategy={strategy}, principal=1.00, term=18, rate={rate}, fee={fee}"
    outcome = _outcome(
        strategy,
        **{
            **_MINIMAL_REQUEST,
            "rate_value": rate,
            "fee_amount": fee,
        },
    )
    schedule = cast(dict[str, list[dict[str, object]]], outcome["trace"])["contractual_schedule"]
    assert [row["interest"] for row in schedule] == ["0.00"] * 18, case
    assert [row["amortization"] for row in schedule] == expected_amortization, case
    assert [row["fee"] for row in schedule] == ["0.00" if fee is None else fee] * 18, case
    expected_payment = [
        format(Decimal(amortization) + Decimal("0.00" if fee is None else fee), ".2f")
        for amortization in expected_amortization
    ]
    assert [row["payment"] for row in schedule] == expected_payment, case
    _assert_trace_identities(outcome, case)
    if fee is None:
        assert outcome == _outcome(
            strategy,
            **{
                **_MINIMAL_REQUEST,
                "rate_value": rate,
                "fee_amount": "0.00",
            },
        ), case
    assert isinstance(
        replay_financing(
            _envelope(
                strategy,
                **{**_MINIMAL_REQUEST, "rate_value": rate, "fee_amount": fee},
            )
        ),
        ReplayVerification,
    ), case


@pytest.mark.parametrize("strategy", ("sac", "price"))
@pytest.mark.parametrize("rate", ("0.0000", "0.0001"))
def test_v3_exhaustive_small_principals_preserve_schedule_and_ledger_invariants(
    strategy: Strategy, rate: str
) -> None:
    for cents in range(1, 51):
        principal = f"{cents // 100}.{cents % 100:02d}"
        for term in range(1, 61):
            common = {
                "comparison_opening_cash": "100.00",
                "property_price": principal,
                "cash_down_payment": "0.00",
                "principal": principal,
                "term_months": term,
                "rate_value": rate,
            }
            for fee in (None, "0.01"):
                case = (
                    f"strategy={strategy}, principal={principal}, term={term}, rate={rate}, fee={fee}"
                )
                _assert_trace_identities(_outcome(strategy, **{**common, "fee_amount": fee}), case)


def test_v3_live_entry_points_replay_and_preserve_ordinary_v2_values() -> None:
    for fee in (None, "0.00", "0.01"):
        sac_v2 = normalize_sac_request_v2(_sac_request(fee_amount=fee))
        sac_v3 = normalize_sac_request_v3(_sac_request(fee_amount=fee))
        price_v2 = normalize_price_request_v2(_price_request(fee_amount=fee))
        price_v3 = normalize_price_request_v3(_price_request(fee_amount=fee))
        assert not isinstance(sac_v2, DomainFailure)
        assert not isinstance(sac_v3, DomainFailure)
        assert not isinstance(price_v2, DomainFailure)
        assert not isinstance(price_v3, DomainFailure)
        assert asdict(calculate_sac_v2(sac_v2)) == asdict(calculate_sac_v3(sac_v3))
        assert asdict(calculate_price_v2(price_v2)) == asdict(calculate_price_v3(price_v3))

    envelope = _envelope("price", fee_amount="0.01")
    assert envelope.contract_schema_version == replay_v3.CONTRACT_SCHEMA_VERSION
    assert envelope.engine_version == replay_v3.ENGINE_VERSION
    assert envelope.ruleset_version == replay_v3.RULESET_VERSION
    assert isinstance(replay_financing(envelope), ReplayVerification)


def test_v3_boundaries_validation_and_version_isolation_are_explicit() -> None:
    term_one = _outcome(
        "sac",
        comparison_opening_cash="0.01",
        property_price="0.01",
        cash_down_payment="0.00",
        principal="0.01",
        term_months=1,
        rate_value="0",
        fee_amount="0.01",
    )
    schedule = cast(dict[str, list[dict[str, object]]], term_one["trace"])["contractual_schedule"]
    assert schedule == [
        {
            "amortization": "0.01",
            "closing_principal_balance": "0.00",
            "fee": "0.01",
            "interest": "0.00",
            "month": 1,
            "opening_principal_balance": "0.01",
            "payment": "0.02",
        }
    ]

    long_term = _outcome("price", term_months=600, fee_amount="0.01")
    trace = cast(dict[str, list[dict[str, object]]], long_term["trace"])
    assert len(trace["contractual_schedule"]) == 600
    assert len(trace["comparison_ledger"]) == 61
    assert trace["contractual_schedule"][-1]["fee"] == "0.01"
    _assert_trace_identities(long_term)

    invalid_fee = normalize_sac_request_v3(_sac_request(fee_amount="-1.00"))
    assert isinstance(invalid_fee, DomainFailure)
    assert invalid_fee.code == "invalid_input"
    unsupported = normalize_price_request_v3(_price_request(insurance_amount="1.00"))
    assert isinstance(unsupported, DomainFailure)
    assert unsupported.code == "unsupported_contract_clause"

    v2_input = normalize_sac_request_v2(_sac_request(fee_amount="0.01"))
    v3_price = normalize_price_request_v3(_price_request(fee_amount="0.01"))
    assert not isinstance(v2_input, DomainFailure)
    assert not isinstance(v3_price, DomainFailure)
    with pytest.raises(ValueError):
        calculate_sac_v3(cast(NormalizedV3FinancingInput, v2_input))
    with pytest.raises(ValueError):
        calculate_sac_v3(v3_price)


def test_v3_codec_tampering_context_independence_and_immutability_fail_safely() -> None:
    envelope = _envelope("sac", fee_amount="0.01")
    outcome = json.loads(envelope.sealed_outcome_jcs)
    del outcome["trace"]["contractual_schedule"][0]["fee"]
    malformed = replace(envelope, sealed_outcome_jcs=replay_v3.canonical_json(outcome))
    result = replay_financing(malformed)
    assert isinstance(result, DomainFailure)
    assert result.code == "incompatible_contract_version"

    semantic_tamper = json.loads(envelope.sealed_outcome_jcs)
    semantic_tamper["trace"]["contractual_schedule"][0]["payment"] = "112.02"
    altered = replace(envelope, sealed_outcome_jcs=replay_v3.canonical_json(semantic_tamper))
    result = replay_financing(altered)
    assert isinstance(result, DomainFailure)
    assert result.code == "incompatible_contract_version"

    mismatched = replace(envelope, ruleset_version="financing-ruleset-v1")
    result = replay_financing(mismatched)
    assert isinstance(result, DomainFailure)
    assert result.code == "incompatible_contract_version"

    normalized = normalize_price_request_v3(_price_request(fee_amount="0.01"))
    assert not isinstance(normalized, DomainFailure)
    expected = calculate_price_v3(normalized)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert calculate_price_v3(normalized) == expected
    with pytest.raises(FrozenInstanceError):
        setattr(expected.contractual_schedule[0], "fee", expected.contractual_schedule[0].fee)

    with pytest.raises(ValueError):
        create_v3_envelope(
            strategy="sac",
            raw_request_jcs=replay_v3.canonical_json({"principal": "1.00"}),
            data_snapshot_id="synthetic-regression-v3",
        )
