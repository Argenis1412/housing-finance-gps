"""Independent funded comparison references, failure phases and conservation."""

from __future__ import annotations

from dataclasses import asdict, replace
from decimal import Decimal
import json
from typing import cast

import pytest
from hypothesis import given, settings, strategies as st

from domain.comparison import (
    ComparisonRequestV2,
    ComparisonResult,
    ComparisonSimulationEnvelope,
    calculate_comparison_v2,
    create_comparison_v2_envelope,
)
from domain.consortium import replay_v1 as codec
from domain.consortium.contracts import (
    ConsortiumScheduleInput,
    ConsortiumWaitingCostInput,
)
from domain.financing import replay_v3
from domain.values import DomainFailure
from tests.test_comparison_domain import synthetic_request
from tests.test_monthly_resources_domain import component, profile


def request(
    income: str = "3.00", expense: str = "1.00", opening: str = "200.00"
) -> ComparisonRequestV2:
    base = synthetic_request()
    return ComparisonRequestV2(
        replace(base.shared, comparison_opening_cash=opening),
        base.constraints,
        replace(base.financing, comparison_opening_cash=opening),
        replace(base.rent, comparison_opening_cash=opening),
        replace(base.consortium, comparison_opening_cash=opening),
        profile(income, expense),
    )


def raw_request(value: ComparisonRequestV2 | None = None) -> dict[str, object]:
    return json.loads(json.dumps(asdict(value or request())))


def envelope(raw: dict[str, object] | None = None) -> ComparisonSimulationEnvelope:
    return create_comparison_v2_envelope(
        raw_request_jcs=codec.canonical_json(raw if raw is not None else raw_request()),
        data_snapshot_id="synthetic-monthly-resources",
        calculated_at="2026-11-03T12:00:00Z",
    )


def outcome(raw: dict[str, object] | None = None) -> dict[str, object]:
    return codec.parse_canonical_object(envelope(raw).sealed_outcome_jcs)


def result(value: ComparisonRequestV2 | None = None) -> ComparisonResult:
    calculated = calculate_comparison_v2(
        value or request(),
        data_snapshot_id="synthetic-monthly-resources",
        calculated_at="2026-11-03T12:00:00Z",
    )
    assert isinstance(calculated, ComparisonResult)
    return calculated


def children(value: dict[str, object]) -> list[dict[str, object]]:
    return cast(
        list[dict[str, object]],
        cast(dict[str, object], value["trace"])["child_evidence"],
    )


def test_independent_variable_monthly_reference_and_common_composition() -> None:
    value = request()
    months = value.monthly_resources.months
    value = replace(
        value,
        monthly_resources=replace(
            value.monthly_resources,
            months=(
                replace(months[0], income_components=(component("income-a", "0.00"),)),
                replace(months[1], income_components=(component("income-a", "5.00"),)),
                *months[2:],
            ),
        ),
    )
    actual = result(value)
    # Independent resource sum: -1 +4 +58*2 =119. Finance preserves worth;
    # rent loses60; consortium loses only its purchase-month waiting rent.
    assert actual.ranking_groups == (("sac", "price"), ("consortium",), ("rent",))
    assert [
        a.metrics.final_ledger_row.net_worth.as_string
        for a in actual.alternatives
        if a.metrics
    ] == ["319.00", "319.00", "259.00", "318.00"]
    first = actual.alternatives[0].comparison_ledger
    assert [first[m].cash.as_string for m in (0, 1, 2, 60)] == [
        "200.00",
        "198.00",
        "201.00",
        "259.00",
    ]
    sealed = codec.parse_canonical_object(actual.envelope.sealed_outcome_jcs)
    common = cast(
        dict[str, object],
        cast(dict[str, object], sealed["normalized_input"])["monthly_resources"],
    )
    for entry in children(sealed):
        raw = codec.parse_canonical_object(entry["raw_request_jcs"])
        assert raw["monthly_resources"] == raw_request(value)["monthly_resources"]
        child = codec.parse_canonical_object(entry["sealed_outcome_jcs"])
        assert (
            cast(dict[str, object], child["normalized_input"])["monthly_resources"]
            == common
        )
        rows = cast(
            list[dict[str, object]],
            cast(dict[str, object], child["trace"])["resource_postings"],
        )
        assert len(rows) == 60 and rows[0]["available_resources"] == "-1.00"
    assert actual.alternatives[2].metrics is not None
    assert (
        actual.alternatives[
            2
        ].metrics.final_ledger_row.cumulative_housing_cost.as_string
        == "60.00"
    )


def test_monthly_funding_works_before_obligations_and_cash_exactly_zero_passes() -> (
    None
):
    actual = result(request("2.00", "0.00", "0.00"))
    assert all(a.status == "eligible" for a in actual.alternatives)
    assert actual.alternatives[3].comparison_ledger[1].cash.as_string == "0.00"
    assert actual.alternatives[0].comparison_ledger[60].cash.as_string == "60.00"
    assert result(request("0.00", "0.00", "0.00")).status == "no_eligible"


@pytest.mark.parametrize(
    ("kind", "strategy", "phase", "month"),
    [
        ("finance_opening", "sac", "opening_allocation", 0),
        ("rent_opening", "rent", "opening_allocation", 0),
        ("negative_resources", "price", "external_expenses", 1),
        ("obligation", "consortium", "strategy_obligations", 1),
        ("contribution", "rent", "investment_contribution", 1),
    ],
)
def test_shortfalls_have_fixed_phases_and_no_fabricated_partial_outputs(
    kind: str, strategy: str, phase: str, month: int
) -> None:
    value = request("100.00", "0.00", "0.00")
    if kind == "finance_opening":
        value = replace(
            value,
            financing=replace(
                value.financing, cash_down_payment="0.01", principal="59.99"
            ),
        )
    elif kind == "rent_opening":
        value = replace(
            value, rent=replace(value.rent, initial_invested_capital="0.01")
        )
    elif kind == "negative_resources":
        value = request("0.00", "0.01", "0.00")
    elif kind == "obligation":
        value = request("1.99", "0.00", "0.00")
    elif kind == "contribution":
        value = replace(
            request("2.00", "0.00", "0.00"),
            rent=replace(value.rent, monthly_contribution="1.01"),
        )
    actual = result(value)
    alternative = next(a for a in actual.alternatives if a.strategy == strategy)
    assert alternative.failure == DomainFailure(
        "infeasible_scenario", f"cash is insufficient in month {month} during {phase}"
    )
    assert (
        alternative.metrics is None
        and alternative.comparison_ledger == ()
        and alternative.violations == ()
    )
    assert strategy not in [s for group in actual.ranking_groups for s in group]
    sealed = codec.parse_canonical_object(actual.envelope.sealed_outcome_jcs)
    entry = next(e for e in children(sealed) if e["strategy"] == strategy)
    assert (
        len(
            cast(
                list[object],
                cast(
                    dict[str, object],
                    codec.parse_canonical_object(entry["raw_request_jcs"])[
                        "monthly_resources"
                    ],
                )["months"],
            )
        )
        == 60
    )
    failure = codec.parse_canonical_object(entry["sealed_outcome_jcs"])
    assert failure.keys() == {"kind", "code", "detail"}


def test_investment_assets_and_current_return_cannot_rescue_cash() -> None:
    value = request("1.00", "0.00", "200.00")
    value = replace(
        value,
        rent=replace(
            value.rent,
            initial_invested_capital="200.00",
            monthly_contribution="0.01",
            return_rate_value="1",
        ),
    )
    actual = result(value).alternatives[2]
    assert actual.failure is not None and actual.failure.detail.endswith(
        "investment_contribution"
    )
    value = replace(value, monthly_resources=profile("0.00", "0.01"))
    failed = result(value).alternatives[2]
    assert failed.failure is not None and failed.failure.detail.endswith(
        "external_expenses"
    )


def test_opening_returns_and_explicit_contributions_stay_invested_while_surplus_stays_cash() -> (
    None
):
    value = request("4.00", "1.00", "200.00")
    value = replace(
        value,
        rent=replace(
            value.rent,
            initial_invested_capital="1.00",
            monthly_contribution="1.00",
            return_rate_value="1",
        ),
    )
    actual = result(value)
    rent = actual.alternatives[2].comparison_ledger
    assert [
        (r.cash.as_string, r.liquid_financial_assets.as_string) for r in rent[:3]
    ] == [("199.00", "1.00"), ("200.00", "3.00"), ("201.00", "7.00")]
    assert rent[-1].liquid_financial_assets.amount == 2**61 - 1
    assert rent[-1].cash.as_string == "259.00"
    assert (
        actual.alternatives[0].comparison_ledger[-1].liquid_financial_assets.as_string
        == "0.00"
    )


@settings(max_examples=16, derandomize=True, database=None, deadline=None)
@given(
    income=st.integers(0, 10), expense=st.integers(0, 3), contribution=st.integers(0, 2)
)
def test_independent_cash_and_networth_conservation(
    income: int, expense: int, contribution: int
) -> None:
    value = request(f"{income}.00", f"{expense}.00", "999.00")
    value = replace(
        value,
        financing=replace(value.financing, rate_value="0.01", fee_amount="0.05"),
        rent=replace(
            value.rent,
            initial_invested_capital="2.00",
            monthly_contribution=f"{contribution}.00",
            return_rate_value="0.01",
        ),
    )
    actual = result(value)
    sealed = codec.parse_canonical_object(actual.envelope.sealed_outcome_jcs)
    for alternative, entry in zip(actual.alternatives, children(sealed), strict=True):
        assert alternative.metrics is not None
        child = codec.parse_canonical_object(entry["sealed_outcome_jcs"])
        trace = cast(dict[str, object], child["trace"])
        for m in range(1, 61):
            opening, closing = alternative.comparison_ledger[m - 1 : m + 1]
            transfer = (
                Decimal(contribution) if alternative.strategy == "rent" else Decimal(0)
            )
            investment_return = Decimal(0)
            if alternative.strategy == "rent":
                posting = cast(list[dict[str, object]], trace["monthly_postings"])[
                    m - 1
                ]
                investment_return = Decimal(cast(str, posting["investment_return"]))
            assert (
                closing.cash.amount - opening.cash.amount
                == income
                - expense
                - alternative.monthly_housing_outflows[m - 1].amount
                - transfer
            )
            assert (
                closing.net_worth.amount - opening.net_worth.amount
                == income
                - expense
                + investment_return
                - closing.nonrecoverable_housing_cost.amount
            )
            assert (
                closing.cumulative_housing_cost.amount
                - opening.cumulative_housing_cost.amount
                == closing.nonrecoverable_housing_cost.amount
            )


def test_constraints_are_separate_inclusive_and_complete_without_double_counting() -> (
    None
):
    value = request()
    value = replace(
        value,
        constraints=replace(
            value.constraints,
            minimum_liquidity="200.00",
            maximum_monthly_housing_outflow="1.00",
        ),
    )
    actual = result(value)
    assert actual.alternatives[0].status == "eligible"
    consortium = actual.alternatives[3]
    assert [(v.constraint, v.month) for v in consortium.violations] == [
        ("maximum_monthly_housing_outflow", 1)
    ]
    assert (
        consortium.metrics is not None
        and consortium.metrics.maximum_monthly_housing_outflow.as_string == "2.00"
    )
    value = replace(
        value,
        constraints=replace(
            value.constraints,
            minimum_liquidity="999.00",
            maximum_monthly_housing_outflow="0.00",
        ),
    )
    actual = result(value)
    assert actual.status == "no_eligible"
    assert [(v.constraint, v.month) for v in actual.alternatives[0].violations] == [
        ("minimum_liquidity", m) for m in range(61)
    ] + [("maximum_monthly_housing_outflow", m) for m in range(1, 61)]
    value = replace(
        value,
        financing=replace(value.financing, insurance_amount="1.00"),
        rent=replace(value.rent, future_purchase="requested"),
        constraints=replace(
            value.constraints,
            minimum_liquidity="0.00",
            maximum_monthly_housing_outflow="2.00",
        ),
    )
    assert result(value).status == "single_eligible"


@pytest.mark.parametrize("contemplation", [1, 60, 61])
def test_consortium_keeps_classified_costs_transitions_and_horizon(
    contemplation: int,
) -> None:
    value = request("4.00", "1.00")
    term = max(60, contemplation)
    consortium = replace(
        value.consortium,
        credit_letter=f"{term}.00",
        property_price=f"{term + 1}.00",
        cash_top_up="1.00",
        term_months=term,
        contemplation_month=contemplation,
        monthly_schedule=tuple(
            ConsortiumScheduleInput(m, "1.00", "0.10", "0.20", "0.30")
            for m in range(1, term + 1)
        ),
        waiting_housing_costs=tuple(
            ConsortiumWaitingCostInput(m, "1.00")
            for m in range(1, min(contemplation, 60) + 1)
        ),
    )
    value = replace(
        value,
        shared=replace(value.shared, property_price=f"{term + 1}.00"),
        financing=replace(
            value.financing, property_price=f"{term + 1}.00", principal=f"{term + 1}.00"
        ),
        consortium=consortium,
    )
    actual = result(value).alternatives[3]
    assert actual.metrics is not None
    final = actual.metrics.final_ledger_row
    assert final.cumulative_housing_cost.amount == Decimal(36 + min(contemplation, 60))
    assert final.net_worth.amount == Decimal(200 + 180 - 36 - min(contemplation, 60))
    assert final.property_value.as_string == (
        f"{term + 1}.00" if contemplation <= 60 else "0.00"
    )
    assert final.consortium_credit_right_balance.as_string == (
        "0.00" if contemplation <= 60 else "60.00"
    )
    if contemplation <= 60:
        assert actual.monthly_housing_outflows[contemplation - 1].as_string == "3.60"
        sealed = outcome(raw_request(value))
        child = codec.parse_canonical_object(children(sealed)[3]["sealed_outcome_jcs"])
        posting = cast(
            list[dict[str, object]],
            cast(dict[str, object], child["trace"])["monthly_postings"],
        )[contemplation - 1]
        assert posting["transferred_credit_right"] == f"{contemplation}.00"
        assert posting["credit_letter_applied"] == f"{term}.00"


@pytest.mark.parametrize("strategy", ["sac", "price"])
def test_financing_preserves_v3_settlement_without_closed_cash_ledger(
    strategy: str,
) -> None:
    value = request("100.00", "0.00", "0.00")
    value = replace(
        value,
        shared=replace(value.shared, property_price="0.02"),
        financing=replace(
            value.financing,
            property_price="0.02",
            principal="0.02",
            term_months=5,
            fee_amount="0.01",
        ),
    )
    # Isolate the changed financing price from the common-basis consortium check.
    raw = raw_request(value)
    cast(dict[str, object], raw["consortium"]).update(
        property_price="0.02", credit_letter="0.02"
    )
    sealed = outcome(raw)
    child = codec.parse_canonical_object(
        children(sealed)[0 if strategy == "sac" else 1]["sealed_outcome_jcs"]
    )
    old = codec.parse_canonical_object(
        replay_v3.evaluate(
            codec.canonical_json(raw["financing"]), cast(replay_v3.Strategy, strategy)
        )
    )
    assert (
        cast(dict[str, object], child["trace"])["contractual_schedule"]
        == cast(dict[str, object], old["trace"])["contractual_schedule"]
    )
    assert (
        cast(
            list[dict[str, object]],
            cast(dict[str, object], child["trace"])["comparison_ledger"],
        )[-1]["financing_principal_balance"]
        == "0.00"
    )


@pytest.mark.parametrize(
    ("key", "field", "value"),
    [
        ("financing", "principal", None),
        ("financing", "term_months", True),
        ("financing", "term_months", 601),
        ("financing", "rate_value", "1e-2"),
        ("financing", "indexation", None),
        ("financing", "fee_amount", "-0.01"),
        ("financing", "insurance_amount", "1.00"),
        ("rent", "return_rate_value", "1.0000000000001"),
        ("rent", "return_rate_convention", "effective_annual"),
        ("rent", "monthly_contribution", "-0.01"),
        ("rent", "tax_amount", "1.00"),
        ("rent", "future_purchase", "requested"),
        ("consortium", "term_months", 601),
        ("consortium", "monthly_schedule", None),
        ("consortium", "monthly_schedule", [None]),
        ("consortium", "monthly_schedule", [{"month": True}]),
        ("consortium", "waiting_housing_costs", []),
        ("consortium", "correction", "requested_nonzero"),
        ("consortium", "requested_features", ["tax"]),
        ("consortium", "unknown", "clause"),
    ],
)
def test_new_child_admission_and_support_failures_remain_isolated(
    key: str, field: str, value: object
) -> None:
    raw = raw_request()
    cast(dict[str, object], raw[key])[field] = value
    sealed = outcome(raw)
    assert sealed["kind"] == "success"
    alternatives = cast(list[dict[str, object]], sealed["alternatives"])
    index = {"financing": 0, "rent": 2, "consortium": 3}[key]
    assert (
        alternatives[index]["status"] == "domain_failure"
        and "metrics" not in alternatives[index]
    )


def test_whole_profile_validation_and_shared_mismatches_precede_cash_execution() -> (
    None
):
    raw = raw_request(request("0.00", "1.00", "0.00"))
    months = cast(
        list[dict[str, object]],
        cast(dict[str, object], raw["monthly_resources"])["months"],
    )
    months[-1]["income_components"] = None
    sealed = outcome(raw)
    assert sealed["kind"] == "failure" and sealed["code"] == "invalid_input"
    raw = raw_request()
    cast(dict[str, object], raw["financing"])["insurance_amount"] = "1.00"
    cast(dict[str, object], raw["rent"])["starting_monthly_rent"] = "1.01"
    assert outcome(raw)["kind"] == "failure"
    raw = raw_request()
    raw["income"] = "3.00"
    assert outcome(raw)["kind"] == "failure"


def test_signed_zero_normalizes_in_successor_contracts_without_narrowing_admission() -> (
    None
):
    raw = raw_request(request("2.00", "0.00", "0.00"))
    for key in ("shared", "financing", "rent", "consortium"):
        cast(dict[str, object], raw[key])["comparison_opening_cash"] = "-0.00"
    cast(dict[str, object], raw["financing"]).update(
        cash_down_payment="-0.00", fee_amount="-0.00"
    )
    cast(dict[str, object], raw["rent"]).update(
        initial_invested_capital="-0.00", monthly_contribution="-0.00"
    )
    sealed = outcome(raw)
    for entry in children(sealed):
        child = codec.parse_canonical_object(entry["sealed_outcome_jcs"])
        assert child["kind"] == "success"
        assert "-0.00" not in codec.canonical_json(child["normalized_input"])
        assert "-0.00" in cast(str, entry["raw_request_jcs"])
