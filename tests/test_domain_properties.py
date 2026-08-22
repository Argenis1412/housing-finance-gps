"""Deterministic synthetic properties for the supported domain contracts."""

from __future__ import annotations

from dataclasses import asdict, replace
from decimal import Decimal
from fractions import Fraction
import json
from typing import Callable, Literal, cast

import pytest
from hypothesis import given, settings, strategies as st

from domain.financing import replay_v1, replay_v2, replay_v3
from domain.financing.contracts import FinancingRequest
from domain.financing.price import calculate_price_v3, normalize_price_request_v3
from domain.financing.replay import (
    ReplayVerification,
    SimulationReplayEnvelope,
    create_v1_envelope,
    create_v2_envelope,
    create_v3_envelope,
    replay_financing,
)
from domain.financing.sac import calculate_sac_v3, normalize_sac_request_v3
from domain.financing.v3 import FinancingV3Result, NormalizedV3FinancingInput
from domain.ledger import ComparisonLedgerRow, post_nonnegative_fraction
from domain.rent_plus_investment import (
    RentPlusInvestmentRequest,
    calculate_rent_plus_investment,
    normalize_rent_plus_investment_request,
)
from domain.values import BRLMoney, DeclaredRate, DomainFailure, EffectiveMonthlyRate, FailureCode


Strategy = Literal["sac", "price"]
_PROPERTY_SETTINGS = settings(
    derandomize=True,
    database=None,
    deadline=None,
    max_examples=24,
)


def _brl(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _financing_request(
    *,
    principal_cents: int = 120_000,
    term_months: int = 12,
    rate_basis_points: int = 100,
    fee_cents: int = 0,
) -> FinancingRequest:
    principal = _brl(principal_cents)
    return FinancingRequest(
        comparison_opening_cash="1000000.00",
        property_price=principal,
        cash_down_payment="0.00",
        principal=principal,
        term_months=term_months,
        rate_value=f"{rate_basis_points / 10_000:.4f}",
        rate_convention="effective_monthly",
        fee_amount=_brl(fee_cents),
    )


def _raw_request(**changes: object) -> str:
    payload = asdict(_financing_request())
    payload.update(changes)
    return replay_v3.canonical_json(payload)


def _raw_financing_request(
    *, principal_cents: int, term_months: int, rate_basis_points: int
) -> str:
    return replay_v3.canonical_json(
        asdict(
            _financing_request(
                principal_cents=principal_cents,
                term_months=term_months,
                rate_basis_points=rate_basis_points,
            )
        )
    )


def _v1_evaluate(raw_request_jcs: str, strategy: Strategy) -> str:
    return replay_v1.evaluate(raw_request_jcs, strategy).outcome_jcs


_VERSIONED_EVALUATORS: tuple[
    tuple[Callable[[object], str], Callable[[str, Strategy], str]],
    ...,
] = (
    (replay_v1.canonical_json, _v1_evaluate),
    (replay_v2.canonical_json, replay_v2.evaluate),
    (replay_v3.canonical_json, replay_v3.evaluate),
)


def _assert_ledger_identities(rows: tuple[ComparisonLedgerRow, ...]) -> None:
    for row in rows:
        assert row.total_liabilities.amount == (
            row.financing_principal_balance.amount + row.consortium_credit_obligation_balance.amount
        )
        assert row.home_equity.amount == row.property_value.amount - row.total_liabilities.amount
        assert row.liquidity.amount == row.cash.amount + row.liquid_financial_assets.amount
        assert row.net_worth.amount == (
            row.cash.amount
            + row.liquid_financial_assets.amount
            + row.consortium_credit_right_balance.amount
            + row.property_value.amount
            - row.total_liabilities.amount
        )


@pytest.mark.parametrize(
    ("strategy", "normalize", "calculate"),
    [
        ("sac", normalize_sac_request_v3, calculate_sac_v3),
        ("price", normalize_price_request_v3, calculate_price_v3),
    ],
)
@_PROPERTY_SETTINGS
@given(
    principal_cents=st.integers(min_value=1, max_value=500_000),
    term_months=st.integers(min_value=1, max_value=60),
    rate_basis_points=st.integers(min_value=0, max_value=2_000),
    fee_cents=st.integers(min_value=0, max_value=1_000),
)
def test_v3_financing_properties_preserve_schedule_and_ledger_contracts(
    strategy: Strategy,
    normalize: Callable[[FinancingRequest], NormalizedV3FinancingInput | DomainFailure],
    calculate: Callable[[NormalizedV3FinancingInput], FinancingV3Result],
    principal_cents: int,
    term_months: int,
    rate_basis_points: int,
    fee_cents: int,
) -> None:
    request = _financing_request(
        principal_cents=principal_cents,
        term_months=term_months,
        rate_basis_points=rate_basis_points,
        fee_cents=fee_cents,
    )
    normalized = normalize(request)
    assert not isinstance(normalized, DomainFailure)
    result = calculate(normalized)
    schedule = result.contractual_schedule
    ledger = result.comparison_ledger

    assert len(schedule) == term_months
    assert [row.month for row in schedule] == list(range(1, term_months + 1))
    assert len(ledger) == 61
    assert [row.month for row in ledger] == list(range(61))
    assert schedule[-1].closing_principal_balance.amount == Decimal("0.00")

    previous_balance = Decimal(_brl(principal_cents))
    previous_cost = Decimal("0.00")
    for row in schedule:
        assert row.opening_principal_balance.amount == previous_balance
        assert row.payment.amount == row.interest.amount + row.amortization.amount + row.fee.amount
        assert row.closing_principal_balance.amount == (
            row.opening_principal_balance.amount - row.amortization.amount
        )
        assert row.closing_principal_balance.amount >= Decimal("0.00")
        previous_balance = row.closing_principal_balance.amount

    for month, row in enumerate(ledger):
        if month == 0:
            assert row.financing_principal_balance.amount == Decimal(_brl(principal_cents))
            continue
        if month <= term_months:
            posting = schedule[month - 1]
            assert row.financing_principal_balance.amount == posting.closing_principal_balance.amount
            assert row.recoverable_transfer.amount == posting.amortization.amount
            assert row.nonrecoverable_housing_cost.amount == posting.interest.amount + posting.fee.amount
        else:
            assert row.financing_principal_balance.amount == Decimal("0.00")
            assert row.recoverable_transfer.amount == Decimal("0.00")
            assert row.nonrecoverable_housing_cost.amount == Decimal("0.00")
        assert row.cumulative_housing_cost.amount == previous_cost + row.nonrecoverable_housing_cost.amount
        previous_cost = row.cumulative_housing_cost.amount
    _assert_ledger_identities(ledger)
    assert strategy in ("sac", "price")


@_PROPERTY_SETTINGS
@given(
    strategy=st.sampled_from(("sac", "price")),
    principal_cents=st.integers(min_value=1, max_value=50_000),
    term_months=st.integers(min_value=1, max_value=60),
    rate_basis_points=st.integers(min_value=0, max_value=1_000),
)
def test_versioned_replay_properties_are_repeatable_and_explicit(
    strategy: Strategy,
    principal_cents: int,
    term_months: int,
    rate_basis_points: int,
) -> None:
    raw_request_jcs = _raw_financing_request(
        principal_cents=principal_cents,
        term_months=term_months,
        rate_basis_points=rate_basis_points,
    )
    factories: tuple[
        tuple[
            Callable[..., SimulationReplayEnvelope],
            tuple[str, str, str],
        ],
        ...,
    ] = (
        (
            create_v1_envelope,
            (replay_v1.CONTRACT_SCHEMA_VERSION, replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION),
        ),
        (
            create_v2_envelope,
            (replay_v2.CONTRACT_SCHEMA_VERSION, replay_v2.ENGINE_VERSION, replay_v2.RULESET_VERSION),
        ),
        (
            create_v3_envelope,
            (replay_v3.CONTRACT_SCHEMA_VERSION, replay_v3.ENGINE_VERSION, replay_v3.RULESET_VERSION),
        ),
    )
    for factory, versions in factories:
        envelope = factory(
            strategy=strategy,
            raw_request_jcs=raw_request_jcs,
            data_snapshot_id="synthetic-property-v1",
        )
        repeated = factory(
            strategy=strategy,
            raw_request_jcs=raw_request_jcs,
            data_snapshot_id="synthetic-property-v1",
        )
        assert envelope == repeated
        assert (
            envelope.contract_schema_version,
            envelope.engine_version,
            envelope.ruleset_version,
        ) == versions
        assert isinstance(replay_financing(envelope), ReplayVerification)

@_PROPERTY_SETTINGS
@given(
    opening_cash_cents=st.integers(min_value=1_500_000, max_value=5_000_000),
    initial_capital_cents=st.integers(min_value=0, max_value=50_000),
    monthly_contribution_cents=st.integers(min_value=0, max_value=1_000),
    rent_cents=st.integers(min_value=1, max_value=5_000),
    annual_rate_basis_points=st.integers(min_value=0, max_value=2_000),
    monthly_return_basis_points=st.integers(min_value=0, max_value=1_000),
    first_adjustment_month=st.integers(min_value=2, max_value=61),
)
def test_rent_plus_properties_preserve_allocation_ledger_and_determinism(
    opening_cash_cents: int,
    initial_capital_cents: int,
    monthly_contribution_cents: int,
    rent_cents: int,
    annual_rate_basis_points: int,
    monthly_return_basis_points: int,
    first_adjustment_month: int,
) -> None:
    request = RentPlusInvestmentRequest(
        comparison_opening_cash=_brl(opening_cash_cents),
        starting_monthly_rent=_brl(rent_cents),
        initial_invested_capital=_brl(initial_capital_cents),
        monthly_contribution=_brl(monthly_contribution_cents),
        rent_adjustment_rate_value=f"{annual_rate_basis_points / 10_000:.4f}",
        rent_adjustment_rate_convention="effective_annual",
        return_rate_value=f"{monthly_return_basis_points / 10_000:.4f}",
        return_rate_convention="effective_monthly",
        first_rent_adjustment_month=first_adjustment_month,
    )
    normalized = normalize_rent_plus_investment_request(request)
    assert not isinstance(normalized, DomainFailure)
    result = calculate_rent_plus_investment(normalized)
    assert not isinstance(result, DomainFailure)
    assert calculate_rent_plus_investment(normalized) == result
    assert len(result.monthly_postings) == 60
    assert len(result.comparison_ledger) == 61
    assert result.comparison_ledger[0].cash.amount == (
        Decimal(_brl(opening_cash_cents)) - Decimal(_brl(initial_capital_cents))
    )
    assert result.comparison_ledger[0].liquid_financial_assets.amount == Decimal(_brl(initial_capital_cents))

    previous = result.comparison_ledger[0]
    for posting, ledger in zip(result.monthly_postings, result.comparison_ledger[1:], strict=True):
        assert posting.month == ledger.month
        assert posting.opening_liquid_financial_assets.amount == previous.liquid_financial_assets.amount
        assert posting.closing_liquid_financial_assets.amount == (
            posting.opening_liquid_financial_assets.amount
            + posting.investment_return.amount
            + posting.monthly_contribution.amount
        )
        assert ledger.cash.amount == previous.cash.amount - posting.rent.amount - posting.monthly_contribution.amount
        assert ledger.liquid_financial_assets.amount == posting.closing_liquid_financial_assets.amount
        assert ledger.cumulative_housing_cost.amount == previous.cumulative_housing_cost.amount + posting.rent.amount
        previous = ledger
    _assert_ledger_identities(result.comparison_ledger)


def test_replay_and_v3_validation_fail_closed_without_cross_version_fallback() -> None:
    raw_request_jcs = _raw_request()
    envelope = create_v3_envelope(
        strategy="sac", raw_request_jcs=raw_request_jcs, data_snapshot_id="synthetic-validation-v1"
    )
    noncanonical = raw_request_jcs.replace(",", ", ", 1)
    for factory in (create_v1_envelope, create_v2_envelope, create_v3_envelope):
        with pytest.raises(ValueError):
            factory(strategy="sac", raw_request_jcs=noncanonical, data_snapshot_id="synthetic-validation-v1")
        with pytest.raises(ValueError):
            factory(strategy=cast(Strategy, "invalid"), raw_request_jcs=raw_request_jcs, data_snapshot_id="synthetic-validation-v1")

    object.__setattr__(envelope, "sealed_outcome_jcs", "{}")
    outcome = replay_financing(envelope)
    assert isinstance(outcome, DomainFailure)
    assert outcome.code == "incompatible_contract_version"


@pytest.mark.parametrize("strategy", ("sac", "price"))
def test_low_centavo_historical_envelopes_cannot_be_reinterpreted_as_v3(strategy: Strategy) -> None:
    raw_request_jcs = _raw_financing_request(principal_cents=100, term_months=18, rate_basis_points=0)
    for factory in (create_v1_envelope, create_v2_envelope):
        historical = factory(
            strategy=strategy,
            raw_request_jcs=raw_request_jcs,
            data_snapshot_id="synthetic-historical-v1",
        )
        reinterpreted = replace(
            historical,
            contract_schema_version=replay_v3.CONTRACT_SCHEMA_VERSION,
            engine_version=replay_v3.ENGINE_VERSION,
            ruleset_version=replay_v3.RULESET_VERSION,
        )
        outcome = replay_financing(reinterpreted)
        assert isinstance(outcome, DomainFailure)
        assert outcome.code == "incompatible_contract_version"


def test_value_boundaries_and_negative_posting_fail_explicitly() -> None:
    for raw_money in ("1.0", "NaN", "Infinity"):
        with pytest.raises(ValueError):
            BRLMoney(raw_money)
    for raw_rate, convention in ((cast(str, 1), "effective_monthly"), ("not-a-rate", "effective_monthly"), ("NaN", "effective_monthly")):
        with pytest.raises(ValueError):
            DeclaredRate(raw_rate, convention)
    for declared in (
        cast(DeclaredRate, "not-a-rate"),
        DeclaredRate("0.01", "effective_annual"),
        DeclaredRate("-0.01", "effective_monthly"),
    ):
        with pytest.raises(ValueError):
            EffectiveMonthlyRate(declared)
    with pytest.raises(ValueError):
        DomainFailure(cast(FailureCode, "unknown"), "detail")
    with pytest.raises(ValueError):
        DomainFailure("invalid_input", cast(str, 1))
    with pytest.raises(ValueError):
        post_nonnegative_fraction(Fraction(-1, 100))


def test_canonical_json_parsers_reject_alternative_evidence_forms() -> None:
    parsers = (
        replay_v1.parse_canonical_object,
        replay_v2.parse_canonical_object,
        replay_v3.parse_canonical_object,
    )
    for parser in parsers:
        for value in (None, "[]", '{"value":NaN}', '{"value":1,"value":2}', '{ "value":1 }'):
            with pytest.raises(ValueError):
                parser(value)
    for value in (Decimal("1"), 9_007_199_254_740_992, {1: "value"}):
        with pytest.raises(ValueError):
            replay_v1.canonical_json(value)


@pytest.mark.parametrize("canonical_json, evaluate", _VERSIONED_EVALUATORS)
@pytest.mark.parametrize(
    ("changes", "expected_code"),
    (
        ({"term_months": 0}, "invalid_input"),
        ({"term_months": 601}, "invalid_input"),
        ({"property_price": "0.00", "principal": "0.00"}, "invalid_input"),
        ({"principal": "0.00", "property_price": "0.00"}, "invalid_input"),
        ({"cash_down_payment": "-0.01"}, "invalid_input"),
        ({"property_price": "1200.01"}, "invalid_input"),
        ({"fgts_amount": "1.00"}, "unsupported_rule"),
        ({"transaction_cost_amount": "1.00"}, "unsupported_contract_clause"),
        ({"indexation": "requested_nonzero"}, "unsupported_contract_clause"),
        ({"indexation": "unknown"}, "invalid_input"),
        ({"rate_value": "-0.01"}, "invalid_input"),
        ({"rate_value": "0.0000000000001"}, "invalid_input"),
        ({"rate_convention": "effective_annual", "rate_value": "0.01"}, "unsupported_rate_convention"),
    ),
)
def test_versioned_evaluators_preserve_common_typed_failures(
    canonical_json: Callable[[object], str],
    evaluate: Callable[[str, Strategy], str],
    changes: dict[str, object],
    expected_code: str,
) -> None:
    payload = asdict(_financing_request())
    payload.update(changes)
    outcome = json.loads(evaluate(canonical_json(payload), "sac"))
    assert outcome["kind"] == "failure"
    assert outcome["code"] == expected_code


@pytest.mark.parametrize("strategy", ("sac", "price"))
def test_v3_fee_validation_and_settlement_paths_are_closed(strategy: Strategy) -> None:
    for fee_amount, expected_code in (("-0.01", "invalid_input"), ("1.0", "invalid_input")):
        outcome = json.loads(replay_v3.evaluate(_raw_request().replace('"fee_amount":"0.00"', f'"fee_amount":"{fee_amount}"'), strategy))
        assert outcome["kind"] == "failure"
        assert outcome["code"] == expected_code
    explicit_zero = replay_v3.evaluate(_raw_request(), strategy)
    absent_payload = asdict(_financing_request())
    absent_payload["fee_amount"] = None
    assert replay_v3.evaluate(replay_v3.canonical_json(absent_payload), strategy) == explicit_zero


def test_versioned_outcome_validators_reject_tampered_shapes_and_values() -> None:
    raw_request_jcs = _raw_request()
    v1_success = _v1_evaluate(raw_request_jcs, "sac")
    v2_success = replay_v2.evaluate(raw_request_jcs, "sac")
    v3_success = replay_v3.evaluate(raw_request_jcs, "sac")
    for validator, canonical_json, success in (
        (replay_v1.validate_outcome, replay_v1.canonical_json, v1_success),
        (replay_v2.validate_outcome, replay_v2.canonical_json, v2_success),
        (replay_v3.validate_outcome, replay_v3.canonical_json, v3_success),
    ):
        validator(success)
        with pytest.raises(ValueError):
            validator(canonical_json({"kind": "unknown"}))
        with pytest.raises(ValueError):
            validator(canonical_json({"kind": "failure", "code": 1, "detail": "detail"}))

    v2_value = json.loads(v2_success)
    v2_value["trace"]["contractual_schedule"][0].pop("fee")
    with pytest.raises(ValueError):
        replay_v2.validate_outcome(replay_v2.canonical_json(v2_value))

    v3_value = cast(dict[str, object], json.loads(v3_success))
    cast(dict[str, object], v3_value["normalized_input"])["term_months"] = 0
    with pytest.raises(ValueError):
        replay_v3.validate_outcome(replay_v3.canonical_json(v3_value))

    v3_value = cast(dict[str, object], json.loads(v3_success))
    cast(dict[str, object], v3_value["normalized_input"])["effective_monthly_rate"] = "NaN"
    with pytest.raises(ValueError):
        replay_v3.validate_outcome(replay_v3.canonical_json(v3_value))

    v3_value = cast(dict[str, object], json.loads(v3_success))
    cast(dict[str, object], v3_value["trace"])["comparison_ledger"] = []
    with pytest.raises(ValueError):
        replay_v3.validate_outcome(replay_v3.canonical_json(v3_value))

    v3_value = cast(dict[str, object], json.loads(v3_success))
    schedule = cast(list[object], cast(dict[str, object], v3_value["trace"])["contractual_schedule"])
    cast(dict[str, object], schedule[0])["month"] = 2
    with pytest.raises(ValueError):
        replay_v3.validate_outcome(replay_v3.canonical_json(v3_value))

    v3_value = cast(dict[str, object], json.loads(v3_success))
    ledger = cast(list[object], cast(dict[str, object], v3_value["trace"])["comparison_ledger"])
    cast(dict[str, object], ledger[0])["financing_principal_balance"] = "-0.01"
    with pytest.raises(ValueError):
        replay_v3.validate_outcome(replay_v3.canonical_json(v3_value))


def test_v1_and_v3_codecs_reject_incomplete_and_invalid_raw_contracts() -> None:
    for canonical_json, evaluate in (
        (replay_v1.canonical_json, _v1_evaluate),
        (replay_v3.canonical_json, replay_v3.evaluate),
    ):
        with pytest.raises(ValueError):
            evaluate(canonical_json({}), "sac")
        for changes in (
            {"principal": 1},
            {"fee_amount": 1},
            {"rate_value": 1},
            {"term_months": True},
            {"term_months": 9_007_199_254_740_992},
        ):
            payload = asdict(_financing_request())
            payload.update(changes)
            with pytest.raises(ValueError):
                evaluate(canonical_json(payload), "sac")

    for changes, expected_code in (
        ({"principal": "1.0"}, "invalid_input"),
        ({"principal": "0.00", "property_price": "1200.00"}, "invalid_input"),
        ({"fgts_amount": "1.0"}, "invalid_input"),
        ({"fgts_amount": "0.00"}, None),
        ({"rate_value": "not-a-rate"}, "invalid_input"),
    ):
        payload = asdict(_financing_request())
        payload.update(changes)
        outcome = json.loads(replay_v3.evaluate(replay_v3.canonical_json(payload), "sac"))
        if expected_code is None:
            assert outcome["kind"] == "success"
        else:
            assert outcome["code"] == expected_code


def test_v2_validator_rejects_each_structural_boundary() -> None:
    success = json.loads(replay_v2.evaluate(_raw_request(), "sac"))
    mutations: tuple[tuple[str, object], ...] = (
        ("normalized_input", None),
        ("normalized_input", {}),
        ("trace", None),
        ("trace", {}),
    )
    for field, replacement in mutations:
        value = json.loads(replay_v2.canonical_json(success))
        value[field] = replacement
        with pytest.raises(ValueError):
            replay_v2.validate_outcome(replay_v2.canonical_json(value))

    for trace_field, replacement in cast(tuple[tuple[str, object], ...], (
        ("contractual_schedule", None),
        ("contractual_schedule", [None]),
        ("comparison_ledger", None),
        ("comparison_ledger", [None]),
        ("comparison_ledger", [{}]),
    )):
        value = json.loads(replay_v2.canonical_json(success))
        trace = cast(dict[str, object], value["trace"])
        trace[trace_field] = replacement
        with pytest.raises(ValueError):
            replay_v2.validate_outcome(replay_v2.canonical_json(value))


def test_v3_validator_rejects_trace_containers_rows_and_sealed_money() -> None:
    success = json.loads(replay_v3.evaluate(_raw_request(), "sac"))
    valid_failure = replay_v3.canonical_json(
        {"code": "invalid_input", "detail": "synthetic failure", "kind": "failure"}
    )
    replay_v3.validate_outcome(valid_failure)

    value = json.loads(replay_v3.canonical_json(success))
    value["trace"] = []
    with pytest.raises(ValueError):
        replay_v3.validate_outcome(replay_v3.canonical_json(value))

    for trace_field, replacement in (("contractual_schedule", {}), ("comparison_ledger", {})):
        value = json.loads(replay_v3.canonical_json(success))
        cast(dict[str, object], value["trace"])[trace_field] = replacement
        with pytest.raises(ValueError):
            replay_v3.validate_outcome(replay_v3.canonical_json(value))

    value = json.loads(replay_v3.canonical_json(success))
    ledger = cast(list[object], cast(dict[str, object], value["trace"])["comparison_ledger"])
    cast(dict[str, object], ledger[0]).pop("cash")
    with pytest.raises(ValueError):
        replay_v3.validate_outcome(replay_v3.canonical_json(value))

    value = json.loads(replay_v3.canonical_json(success))
    schedule = cast(list[object], cast(dict[str, object], value["trace"])["contractual_schedule"])
    cast(dict[str, object], schedule[0])["payment"] = "1.0"
    with pytest.raises(ValueError):
        replay_v3.validate_outcome(replay_v3.canonical_json(value))


def test_live_versioned_adapters_reject_unvalidated_inputs_without_fallback() -> None:
    from domain.financing.v2 import (
        NormalizedV2FinancingInput,
        calculate_sac_v2,
        normalize_sac_request_v2,
    )
    from domain.financing.v3 import NormalizedV3FinancingInput, calculate_sac_v3

    invalid_request = cast(FinancingRequest, object())
    assert isinstance(normalize_sac_request_v2(invalid_request), DomainFailure)
    assert isinstance(normalize_sac_request_v3(invalid_request), DomainFailure)
    failed_v2 = NormalizedV2FinancingInput(_raw_request(principal="0.00"), "sac")
    failed_v3 = NormalizedV3FinancingInput(_raw_request(principal="0.00"), "sac")
    with pytest.raises(ValueError):
        calculate_sac_v2(failed_v2)
    with pytest.raises(ValueError):
        calculate_sac_v3(failed_v3)
    with pytest.raises(ValueError):
        calculate_sac_v3(cast(NormalizedV3FinancingInput, object()))
