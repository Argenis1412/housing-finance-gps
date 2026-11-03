"""Independent small synthetic references and comparison admission guarantees."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
from decimal import ROUND_DOWN, localcontext
import json
from typing import cast

import pytest
from hypothesis import given, settings, strategies as st

from domain.comparison import (
    ComparisonConstraints, ComparisonRequest, ComparisonResult, SharedComparisonInput,
    calculate_comparison_v1, create_comparison_v1_envelope, replay_comparison,
)
from domain.consortium import replay_v1 as codec
from domain.consortium.contracts import ConsortiumRequest, ConsortiumScheduleInput, ConsortiumWaitingCostInput
from domain.financing.contracts import FinancingRequest
from domain.rent_plus_investment import RentPlusInvestmentRequest
from domain.values import DomainFailure


def synthetic_request() -> ComparisonRequest:
    return ComparisonRequest(
        shared=SharedComparisonInput("200.00", "60.00", "1.00", "0", "effective_annual", 13),
        constraints=ComparisonConstraints("0.00", "200.00"),
        financing=FinancingRequest(
            comparison_opening_cash="200.00", property_price="60.00",
            cash_down_payment="0.00", principal="60.00", term_months=60,
            rate_value="0", rate_convention="effective_monthly",
        ),
        rent=RentPlusInvestmentRequest(
            comparison_opening_cash="200.00", starting_monthly_rent="1.00",
            initial_invested_capital="0.00", monthly_contribution="0.00",
            rent_adjustment_rate_value="0", rent_adjustment_rate_convention="effective_annual",
            return_rate_value="0", return_rate_convention="effective_monthly", first_rent_adjustment_month=13,
        ),
        consortium=ConsortiumRequest(
            comparison_opening_cash="200.00", credit_letter="60.00", term_months=60,
            monthly_schedule=tuple(ConsortiumScheduleInput(month, "1.00", "0.00", "0.00", "0.00") for month in range(1, 61)),
            credit_components_apply_to_credit_letter=True, correction="documented_zero",
            reserve_fund_treatment="nonrecoverable_no_refund",
            installment_schedule_treatment="fixed_independent_of_contemplation",
            scenario_kind="early", contemplation_month=1, property_purchase_event=True,
            property_price="60.00", cash_top_up="0.00",
            waiting_housing_costs=(ConsortiumWaitingCostInput(1, "1.00"),),
        ),
    )


def raw_request(request: ComparisonRequest | None = None) -> dict[str, object]:
    return json.loads(json.dumps(asdict(request or synthetic_request())))


def result(request: ComparisonRequest | None = None) -> ComparisonResult:
    value = calculate_comparison_v1(
        request or synthetic_request(), data_snapshot_id="synthetic-comparison-reference-v1",
        calculated_at="2026-11-03T12:00:00Z",
    )
    assert isinstance(value, ComparisonResult)
    return value


def raw_outcome(raw: dict[str, object]) -> dict[str, object]:
    envelope = create_comparison_v1_envelope(
        raw_request_jcs=codec.canonical_json(raw),
        data_snapshot_id="synthetic-comparison-reference-v1", calculated_at="2026-11-03T12:00:00Z",
    )
    return codec.parse_canonical_object(envelope.sealed_outcome_jcs)


def test_independent_closed_cash_reference_and_metric_operands() -> None:
    # No interest/fees: finance converts 60 cash into property, losing no worth.
    # Consortium loses one waiting rent; renting loses 60 rents, with no return.
    value = result()
    assert value.ranking_groups == (("sac", "price"), ("consortium",), ("rent",))
    assert value.status == "compared"
    expected = {
        "sac": ("200.00", "140.00", "0.00", "1.00"),
        "price": ("200.00", "140.00", "0.00", "1.00"),
        "rent": ("140.00", "140.00", "60.00", "1.00"),
        "consortium": ("199.00", "139.00", "1.00", "2.00"),
    }
    for alternative in value.alternatives:
        metrics = alternative.metrics
        assert metrics is not None
        final = metrics.final_ledger_row
        assert (
            final.net_worth.as_string, metrics.minimum_liquidity.as_string,
            final.cumulative_housing_cost.as_string, metrics.maximum_monthly_housing_outflow.as_string,
        ) == expected[alternative.strategy]
        assert final.total_liabilities.as_string == "0.00"
        assert final.net_worth.amount == (
            final.cash.amount + final.liquid_financial_assets.amount
            + final.consortium_credit_right_balance.amount + final.property_value.amount
            - final.total_liabilities.amount
        )
        assert metrics.minimum_liquidity_months == (60,)
        assert len(alternative.comparison_ledger) == 61
    assert value.alternatives[0].metrics is not None
    assert value.alternatives[0].metrics.maximum_monthly_housing_outflow_months == tuple(range(1, 61))
    assert value.alternatives[-1].metrics is not None
    assert value.alternatives[-1].metrics.maximum_monthly_housing_outflow_months == (1,)
    assert "only_rent_invests_and_receives_returns" in value.limitations


def test_four_way_exact_tie_has_no_secondary_financial_order() -> None:
    request = synthetic_request()
    request = replace(
        request, financing=replace(request.financing, fee_amount="1.00"),
        consortium=replace(request.consortium, contemplation_month=60, scenario_kind="late",
            waiting_housing_costs=tuple(ConsortiumWaitingCostInput(month, "1.00") for month in range(1, 61))),
    )
    value = result(request)
    assert value.ranking_groups == (("sac", "price", "rent", "consortium"),)
    assert all(item.metrics is not None and item.metrics.final_ledger_row.net_worth.as_string == "140.00" for item in value.alternatives)


def test_threshold_equality_and_one_cent_violations_include_every_month() -> None:
    request = synthetic_request()
    equal = result(replace(request, constraints=ComparisonConstraints("140.00", "1.00")))
    assert [item.status for item in equal.alternatives] == ["eligible", "eligible", "eligible", "constraint_infeasible"]
    consortium = equal.alternatives[-1]
    assert {(row.constraint, row.month) for row in consortium.violations} == {
        ("minimum_liquidity", 60), ("maximum_monthly_housing_outflow", 1),
    }
    failed = result(replace(request, constraints=ComparisonConstraints("0.00", "0.99")))
    assert failed.status == "no_eligible" and failed.ranking_groups == ()
    for alternative in failed.alternatives:
        assert [v.month for v in alternative.violations] == list(range(1, 61))
    reserve = result(replace(request, constraints=ComparisonConstraints("140.01", "200.00")))
    assert reserve.status == "no_eligible"
    assert reserve.alternatives[0].violations[0].actual.as_string == "140.00"


def test_single_eligible_and_domain_failures_remain_visible_without_metrics() -> None:
    request = synthetic_request()
    single = result(replace(request, constraints=ComparisonConstraints("0.00", "1.00"), financing=replace(request.financing, fee_amount="1.00")))
    assert single.status == "single_eligible" and single.ranking_groups == (("rent",),)
    failed = result(replace(request, rent=replace(request.rent, initial_invested_capital="200.01")))
    alternative = failed.alternatives[2]
    assert alternative.status == "domain_failure" and alternative.failure is not None
    assert alternative.failure.code == "infeasible_scenario"
    assert alternative.metrics is None and not alternative.comparison_ledger and not alternative.violations


def test_successful_financing_with_negative_cash_is_ineligible_without_repair() -> None:
    raw = raw_request()
    for key in ("shared", "financing", "rent", "consortium"):
        cast(dict[str, object], raw[key])["comparison_opening_cash"] = "0.00"
    outcome = raw_outcome(raw)
    alternatives = cast(list[dict[str, object]], outcome["alternatives"])
    assert alternatives[0]["status"] == alternatives[1]["status"] == "constraint_infeasible"
    assert alternatives[2]["status"] == alternatives[3]["status"] == "domain_failure"
    assert cast(dict[str, object], outcome["result"])["status"] == "no_eligible"
    assert cast(list[dict[str, object]], alternatives[0]["violations"])[0]["month"] == 1


def test_month_zero_allocation_and_topup_are_classified_separately() -> None:
    request = synthetic_request()
    # The financed down payment is month zero: it has no monthly cap.
    value = result(replace(request,
        financing=replace(request.financing, cash_down_payment="59.00", principal="1.00", term_months=1),
        constraints=ComparisonConstraints("0.00", "1.00"),
    ))
    assert value.alternatives[0].status == "eligible"
    assert value.alternatives[0].metrics is not None
    assert value.alternatives[0].metrics.minimum_liquidity_months == tuple(range(1, 61))
    reserve = result(replace(request,
        financing=replace(request.financing, cash_down_payment="59.00", principal="1.00", term_months=1),
        constraints=ComparisonConstraints("142.00", "200.00"),
    ))
    assert reserve.alternatives[0].violations[0].month == 0
    # A consortium top-up is a housing cash outflow in the purchase month.
    consortium = replace(request.consortium, credit_letter="59.00", cash_top_up="1.00",
        monthly_schedule=tuple(replace(row, credit_component="0.00" if row.month == 60 else "1.00") for row in request.consortium.monthly_schedule))
    value = result(replace(request, consortium=consortium, constraints=ComparisonConstraints("0.00", "2.00")))
    assert value.alternatives[-1].monthly_housing_outflows[0].as_string == "3.00"
    assert value.alternatives[-1].violations[0].month == 1
    # Financial contributions reduce cash, but are not housing outflows.
    value = result(replace(request, rent=replace(request.rent, initial_invested_capital="1.00", monthly_contribution="1.00")))
    rent = value.alternatives[2]
    assert rent.metrics is not None
    assert rent.metrics.maximum_monthly_housing_outflow.as_string == "1.00"
    assert rent.comparison_ledger[0].liquidity.as_string == "200.00"


@pytest.mark.parametrize(("term", "contemplation"), [(1, 1), (60, 60), (61, 61), (600, 600)])
def test_contemplation_horizon_does_not_anticipate_future_property(term: int, contemplation: int) -> None:
    request = synthetic_request()
    consortium = replace(request.consortium, term_months=term, contemplation_month=contemplation,
        monthly_schedule=tuple(ConsortiumScheduleInput(month, "60.00" if month == 1 else "0.00", "0.00", "0.00", "0.00") for month in range(1, term + 1)),
        waiting_housing_costs=tuple(ConsortiumWaitingCostInput(month, "1.00") for month in range(1, min(contemplation, 60) + 1)))
    value = result(replace(request, consortium=consortium))
    metrics = value.alternatives[-1].metrics
    assert metrics is not None
    assert metrics.final_ledger_row.property_value.as_string == ("60.00" if contemplation <= 60 else "0.00")
    assert metrics.final_ledger_row.consortium_credit_right_balance.as_string == ("0.00" if contemplation <= 60 else "60.00")


def test_shared_mismatches_precede_child_failures_and_preserve_other_checks() -> None:
    raw = raw_request()
    cast(dict[str, object], raw["rent"])["initial_invested_capital"] = "200.01"
    waiting = cast(list[dict[str, object]], cast(dict[str, object], raw["consortium"])["waiting_housing_costs"])
    waiting[0]["amount"] = "1.01"
    outcome = raw_outcome(raw)
    assert outcome["kind"] == "failure" and outcome["code"] == "invalid_input"
    raw = raw_request()
    del cast(dict[str, object], raw["rent"])["comparison_opening_cash"]
    cast(dict[str, object], raw["financing"])["property_price"] = "61.00"
    cast(dict[str, object], raw["financing"])["insurance_amount"] = "1.00"
    assert raw_outcome(raw)["kind"] == "failure"


@pytest.mark.parametrize(("key", "field", "value"), [
    ("rent", "comparison_opening_cash", None),
    ("financing", "rate_value", "1e-2"),
    ("rent", "return_rate_value", "1.0000000000001"),
    ("consortium", "credit_letter", "1000000000000000000.00"),
    ("financing", "term_months", True),
    ("financing", "term_months", 601),
    ("rent", "return_rate_convention", "effective_annual"),
    ("financing", "insurance_amount", "1.00"),
    ("consortium", "correction", "requested_nonzero"),
])
def test_alternative_admission_and_support_failures_are_isolated(key: str, field: str, value: object) -> None:
    raw = raw_request()
    cast(dict[str, object], raw[key])[field] = value
    outcome = raw_outcome(raw)
    assert outcome["kind"] == "success"
    alternatives = cast(list[dict[str, object]], outcome["alternatives"])
    index = {"rent": 2, "financing": 0, "consortium": 3}[key]
    assert alternatives[index]["status"] == "domain_failure"
    assert "metrics" not in alternatives[index]


@pytest.mark.parametrize(("key", "field", "value"), [
    ("shared", "comparison_opening_cash", "-0.01"),
    ("shared", "property_price", "0.00"),
    ("shared", "starting_monthly_rent", "0.00"),
    ("shared", "rent_adjustment_rate_value", "1e-2"),
    ("shared", "rent_adjustment_rate_convention", "effective_monthly"),
    ("shared", "first_rent_adjustment_month", True),
    ("constraints", "minimum_liquidity", "-0.01"),
])
def test_invalid_common_basis_fails_globally(key: str, field: str, value: object) -> None:
    raw = raw_request()
    cast(dict[str, object], raw[key])[field] = value
    outcome = raw_outcome(raw)
    assert outcome["kind"] == "failure" and "alternatives" not in outcome


def test_shared_equality_is_numeric_and_unrelated_month_is_not_term_capped() -> None:
    request = synthetic_request()
    raw = raw_request(replace(request,
        shared=replace(request.shared, first_rent_adjustment_month=601),
        rent=replace(request.rent, first_rent_adjustment_month=601)))
    cast(dict[str, object], raw["financing"])["comparison_opening_cash"] = "+000200.00"
    cast(dict[str, object], raw["rent"])["rent_adjustment_rate_value"] = "0.000"
    assert raw_outcome(raw)["kind"] == "success"


def test_return_can_change_objective_and_calculated_amounts_exceed_input_digits() -> None:
    request = synthetic_request()
    value = result(replace(request, rent=replace(request.rent, initial_invested_capital="1.00", return_rate_value="1")))
    assert value.ranking_groups[0] == ("rent",)
    metrics = value.alternatives[2].metrics
    assert metrics is not None
    # Opening capital doubles each month, before zero contribution.
    assert metrics.final_ledger_row.liquid_financial_assets.amount == 2 ** 60


@settings(max_examples=12, derandomize=True, database=None, deadline=None)
@given(floor=st.integers(0, 205), cap=st.integers(0, 3))
def test_constraints_never_promote_excluded_alternatives(floor: int, cap: int) -> None:
    request = synthetic_request()
    value = result(replace(request, constraints=ComparisonConstraints(f"{floor}.00", f"{cap}.00")))
    eligible = {item.strategy for item in value.alternatives if item.status == "eligible"}
    assert {name for group in value.ranking_groups for name in group} == eligible
    assert len(value.alternatives) == 4


def test_result_is_immutable_and_context_independent() -> None:
    baseline = result()
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert result() == baseline
        assert replay_comparison(baseline.envelope) == baseline
    with pytest.raises(FrozenInstanceError):
        setattr(baseline.alternatives[0], "status", "eligible")
    assert isinstance(baseline.ranking_groups, tuple)
    assert isinstance(calculate_comparison_v1(
        replace(synthetic_request(), shared=replace(synthetic_request().shared, property_price="61.00")),
        data_snapshot_id="synthetic", calculated_at="2026-11-03T12:00:00Z",
    ), DomainFailure)
