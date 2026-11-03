"""Synthetic independent references and invariants for consortium v1."""

from dataclasses import FrozenInstanceError, asdict, replace
from decimal import Decimal, ROUND_DOWN, localcontext
import json
from pathlib import Path
from typing import cast

from hypothesis import given, settings, strategies as st
import pytest

from domain.consortium import replay_v1
from domain.consortium.contracts import (
    ConsortiumRequest, ConsortiumScenarioKind, ConsortiumScheduleInput, ConsortiumWaitingCostInput,
    NormalizedConsortiumV1Input,
)
from domain.consortium.v1 import calculate_consortium_v1, normalize_consortium_request_v1
from domain.ledger import ComparisonLedgerRow
from domain.values import DomainFailure


def synthetic_request(*, term: int = 10, contemplation: int = 4) -> ConsortiumRequest:
    return ConsortiumRequest(
        comparison_opening_cash="20000.00", credit_letter=f"{term * 100}.00", term_months=term,
        monthly_schedule=tuple(ConsortiumScheduleInput(month, "100.00", "10.00", "0.00", "0.00") for month in range(1, term + 1)),
        credit_components_apply_to_credit_letter=True, correction="documented_zero",
        reserve_fund_treatment="nonrecoverable_no_refund",
        installment_schedule_treatment="fixed_independent_of_contemplation",
        scenario_kind="intermediate", contemplation_month=contemplation, property_purchase_event=True,
        property_price=f"{term * 100}.00", cash_top_up="0.00",
        waiting_housing_costs=tuple(ConsortiumWaitingCostInput(month, "0.00") for month in range(1, min(contemplation, 60) + 1)),
    )


def raw_request(request: ConsortiumRequest | None = None) -> dict[str, object]:
    return json.loads(json.dumps(asdict(request or synthetic_request())))


def _evaluate(raw: dict[str, object]) -> dict[str, object]:
    return json.loads(replay_v1.evaluate(replay_v1.canonical_json(raw)))


def _result(request: ConsortiumRequest | None = None):
    normalized = normalize_consortium_request_v1(request or synthetic_request())
    assert not isinstance(normalized, DomainFailure), normalized
    return calculate_consortium_v1(normalized)


def _assert_failure(raw: dict[str, object], code: str) -> None:
    result = _evaluate(raw)
    assert result["kind"] == "failure"
    assert result["code"] == code
    assert set(result) == {"kind", "code", "detail"}


def test_original_m0_consortium_checkpoints_are_exact() -> None:
    fixture = json.loads(Path("docs/fixtures/milestone-0-synthetic-regression.json").read_text())
    reference = fixture["fixtures"]["consortium_credit_right"]
    inputs = reference["inputs"]
    # M0 explicitly documents no reserve, insurance, correction, bid or waiting
    # cost; this adapter supplies those exclusions, not request defaults.
    request = replace(
        synthetic_request(), credit_letter=inputs["credit_letter"], term_months=inputs["term_months"],
        comparison_opening_cash=fixture["shared_conventions"]["comparison_opening_cash"],
        contemplation_month=inputs["contemplation_month"], property_price=inputs["credit_letter"],
        property_purchase_event=inputs["property_purchase_event"],
        monthly_schedule=tuple(ConsortiumScheduleInput(
            row["month"], row["credit_component"], row["administration_fee"], "0.00", "0.00",
        ) for row in inputs["monthly_schedule"]),
    )
    result = _result(request)
    for checkpoint in reference["checkpoints"]:
        row = result.comparison_ledger[cast(int, checkpoint["month"])]
        for name, expected in checkpoint["expected"].items():
            assert getattr(row, name).as_string == expected, (row.month, name)


@pytest.mark.parametrize(("kind", "month", "cash_at_purchase", "obligation", "final_cash", "final_cost"), [
    ("early", 1, "298.00", "20.00", "272.00", "13.00"),
    ("intermediate", 2, "281.00", "10.00", "268.00", "17.00"),
    ("late", 3, "264.00", "0.00", "264.00", "21.00"),
])
def test_independent_three_month_references_include_waiting_costs_and_top_up(
    kind: ConsortiumScenarioKind, month: int, cash_at_purchase: str, obligation: str,
    final_cash: str, final_cost: str,
) -> None:
    # Hand reference: credit=30, property=47, topup=17, opening=332;
    # each installment=10+1+1+1=13, waiting=4 per month including purchase.
    request = replace(
        synthetic_request(term=3, contemplation=month), scenario_kind=kind, comparison_opening_cash="332.00",
        credit_letter="30.00", property_price="47.00", cash_top_up="17.00",
        monthly_schedule=tuple(ConsortiumScheduleInput(m, "10.00", "1.00", "1.00", "1.00") for m in range(1, 4)),
        waiting_housing_costs=tuple(ConsortiumWaitingCostInput(m, "4.00") for m in range(1, month + 1)),
    )
    result = _result(request)
    assert result.scenario_kind == kind and result.contemplation_month == month
    purchase = result.comparison_ledger[month]
    assert purchase.cash.as_string == cash_at_purchase
    assert purchase.property_value.as_string == "47.00"
    assert purchase.consortium_credit_obligation_balance.as_string == obligation
    assert purchase.consortium_credit_right_balance.as_string == "0.00"
    assert purchase.recoverable_transfer.as_string == "27.00"
    assert purchase.nonrecoverable_housing_cost.as_string == "7.00"
    assert result.monthly_postings[month - 1].transferred_credit_right.as_string == f"{month * 10}.00"
    assert result.monthly_postings[month - 1].credit_letter_applied.as_string == "30.00"
    final = result.comparison_ledger[60]
    assert final.cash.as_string == final_cash
    assert final.cumulative_housing_cost.as_string == final_cost
    assert final.net_worth.amount == Decimal("332.00") - Decimal(final_cost)


def _assert_identities(request: ConsortiumRequest) -> None:
    result = _result(request)
    assert len(result.contractual_schedule) == request.term_months
    assert len(result.monthly_postings) == 60 and len(result.comparison_ledger) == 61
    assert sum(row.credit_component.amount for row in result.contractual_schedule) == Decimal(request.credit_letter)
    assert [row.month for row in result.comparison_ledger] == list(range(61))
    previous = result.comparison_ledger[0]
    assert previous.net_worth.amount == Decimal(request.comparison_opening_cash)
    for posting, row in zip(result.monthly_postings, result.comparison_ledger[1:], strict=True):
        assert isinstance(row, ComparisonLedgerRow)
        assert row.cash.amount == previous.cash.amount - posting.cash_outflow.amount >= 0
        assert posting.cash_outflow.amount == row.recoverable_transfer.amount + row.nonrecoverable_housing_cost.amount
        assert row.financing_principal_balance.as_string == "0.00"
        assert row.liquid_financial_assets.as_string == "0.00"
        assert row.total_liabilities.amount == row.consortium_credit_obligation_balance.amount >= 0
        assert row.home_equity.amount == row.property_value.amount - row.total_liabilities.amount
        assert row.liquidity.amount == row.cash.amount
        assert row.net_worth.amount == row.cash.amount + row.consortium_credit_right_balance.amount + row.property_value.amount - row.total_liabilities.amount
        assert row.cumulative_housing_cost.amount == previous.cumulative_housing_cost.amount + row.nonrecoverable_housing_cost.amount
        assert row.net_worth.amount == previous.net_worth.amount - row.nonrecoverable_housing_cost.amount
        if row.month < request.contemplation_month:
            assert row.consortium_credit_right_balance.amount == previous.consortium_credit_right_balance.amount + row.recoverable_transfer.amount
            assert row.property_value.amount == row.total_liabilities.amount == 0
        elif row.month > request.contemplation_month:
            assert row.consortium_credit_right_balance.amount == 0
            assert row.total_liabilities.amount == previous.total_liabilities.amount - row.recoverable_transfer.amount
            assert posting.transferred_credit_right.amount == posting.credit_letter_applied.amount == 0
        previous = row
    if request.term_months <= 60:
        assert result.comparison_ledger[request.term_months].total_liabilities.amount == 0


@pytest.mark.parametrize(("term", "contemplation"), [(1, 1), (60, 1), (60, 60), (61, 60), (61, 61), (600, 600)])
def test_horizon_and_term_boundaries_reconcile_without_future_balance_claims(term: int, contemplation: int) -> None:
    request = synthetic_request(term=term, contemplation=contemplation)
    request = replace(request, cash_top_up="10.00", property_price=f"{term * 100 + 10}.00")
    _assert_identities(request)
    result = _result(request)
    if contemplation > 60:
        last = result.comparison_ledger[-1]
        assert last.cash.as_string == "13400.00"
        assert last.consortium_credit_right_balance.as_string == "6000.00"
        assert last.property_value.amount == last.total_liabilities.amount == 0
        assert all(row.cash_top_up.amount == row.credit_letter_applied.amount == 0 for row in result.monthly_postings)


@pytest.mark.parametrize(("changes", "code"), [
    ({"credit_letter": "0.00"}, "invalid_input"), ({"credit_letter": "1.0"}, "invalid_input"),
    ({"cash_top_up": "-0.01"}, "invalid_input"), ({"comparison_opening_cash": "-0.01"}, "invalid_input"),
    ({"credit_letter": None}, "invalid_input"), ({"term_months": True}, "invalid_input"),
    ({"term_months": 601}, "invalid_input"), ({"term_months": 0}, "invalid_input"),
    ({"contemplation_month": 0}, "invalid_input"), ({"contemplation_month": 11}, "invalid_input"),
    ({"scenario_kind": "expected"}, "invalid_input"), ({"scenario_kind": {}}, "invalid_input"),
    ({"correction": "unknown"}, "invalid_input"), ({"property_purchase_event": 1}, "invalid_input"),
    ({"credit_components_apply_to_credit_letter": "yes"}, "invalid_input"),
    ({"reserve_fund_treatment": None}, "invalid_input"),
    ({"monthly_schedule": {}}, "invalid_input"), ({"monthly_schedule": []}, "invalid_input"),
    ({"waiting_housing_costs": []}, "invalid_input"),
    ({"credit_letter": "999.00"}, "invalid_input"), ({"property_price": "1000.01"}, "invalid_input"),
    ({"credit_components_apply_to_credit_letter": False}, "unsupported_contract_clause"),
    ({"property_purchase_event": False}, "unsupported_contract_clause"),
    ({"correction": "requested_nonzero"}, "unsupported_contract_clause"),
    ({"reserve_fund_treatment": "refundable"}, "unsupported_contract_clause"),
    ({"installment_schedule_treatment": "changes_on_contemplation"}, "unsupported_contract_clause"),
    ({"cash_bid": "1.00"}, "unsupported_contract_clause"), ({"probability": "0.5"}, "unsupported_contract_clause"),
    ({"requested_features": ["embedded_bid"]}, "unsupported_contract_clause"),
    ({"requested_features": ["unknown_clause"]}, "unsupported_contract_clause"),
    ({"requested_features": ["tax"]}, "unsupported_rule"), ({"requested_features": ["fgts"]}, "unsupported_rule"),
    ({"requested_features": ["subsidy", "cash_bid"]}, "unsupported_rule"),
    ({"requested_features": ["eligibility"]}, "unsupported_rule"),
    ({"requested_features": [None]}, "invalid_input"), ({"requested_features": [""]}, "invalid_input"),
    ({"requested_features": "tax"}, "invalid_input"),
])
def test_invalid_and_unsupported_inputs_fail_closed(changes: dict[str, object], code: str) -> None:
    raw = raw_request()
    raw.update(changes)
    _assert_failure(raw, code)


@pytest.mark.parametrize("mutation", ["missing", "row_object", "missing_component", "duplicate", "order", "negative", "unknown", "waiting_object", "waiting_month", "waiting_amount", "waiting_unknown"])
def test_required_rows_and_every_nested_object_are_closed(mutation: str) -> None:
    raw = raw_request()
    schedule = cast(list[dict[str, object]], raw["monthly_schedule"])
    waiting = cast(list[dict[str, object]], raw["waiting_housing_costs"])
    code = "invalid_input"
    if mutation == "missing":
        del raw["correction"]
    elif mutation == "row_object":
        cast(list[object], schedule)[0] = None
    elif mutation == "missing_component":
        del schedule[0]["insurance"]
    elif mutation == "duplicate":
        schedule[1]["month"] = 1
    elif mutation == "order":
        schedule.reverse()
    elif mutation == "negative":
        schedule[0]["insurance"] = "-0.01"
    elif mutation == "unknown":
        schedule[0]["recalculation"] = "private clause text"
        code = "unsupported_contract_clause"
    elif mutation == "waiting_object":
        cast(list[object], waiting)[0] = []
    elif mutation == "waiting_month":
        waiting[0]["month"] = True
    elif mutation == "waiting_amount":
        del waiting[0]["amount"]
    else:
        waiting[0]["probability"] = "0.50"
        code = "unsupported_contract_clause"
    _assert_failure(raw, code)


def test_support_validation_precedes_reconciliation_but_follows_known_shape() -> None:
    raw = raw_request()
    raw.update(credit_letter="999.00", requested_features=["tax"], probability="private")
    _assert_failure(raw, "unsupported_rule")
    raw["term_months"] = True
    _assert_failure(raw, "invalid_input")
    raw["term_months"] = 10
    raw["requested_features"] = []
    _assert_failure(raw, "unsupported_contract_clause")
    assert "private" not in str(_evaluate(raw))


def test_zero_cash_and_cent_shortfalls_return_no_partial_output() -> None:
    request = replace(synthetic_request(term=1, contemplation=1), comparison_opening_cash="115.00", cash_top_up="5.00", property_price="105.00")
    assert _result(request).comparison_ledger[-1].cash.as_string == "0.00"
    for cash in ("114.99", "109.99"):
        result = normalize_consortium_request_v1(replace(request, comparison_opening_cash=cash))
        assert isinstance(result, DomainFailure) and result.code == "infeasible_scenario"
    raw = raw_request(replace(synthetic_request(term=61, contemplation=61), comparison_opening_cash="6600.00"))
    assert _evaluate(raw)["kind"] == "success"  # No claim about payment in month61.


def test_input_classification_and_signed_zero_normalization_are_recorded() -> None:
    raw = raw_request()
    raw["cash_top_up"] = "-0.00"
    raw.pop("requested_features")
    normalized = cast(dict[str, object], _evaluate(raw)["normalized_input"])
    assert normalized["cash_top_up"] == "0.00"
    assert normalized["requested_features"] == []
    classification = cast(dict[str, str], normalized["input_classification"])
    assert classification["comparison_opening_cash"] == "observed_data"
    assert classification["monthly_schedule"] == "contractual_data"
    assert classification["contemplation_month"] == "projected_assumption"
    assert normalized["reference_basis"] == "synthetic_contract_reference"


def test_live_boundary_is_context_independent_immutable_and_defensive() -> None:
    request = synthetic_request()
    baseline = _result(request)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert _result(request) == baseline
    for target in (request, request.monthly_schedule[0], baseline, baseline.monthly_postings[0], baseline.comparison_ledger[0]):
        with pytest.raises((FrozenInstanceError, TypeError)):
            setattr(target, "month", 2)
    with pytest.raises(ValueError):
        calculate_consortium_v1(cast(NormalizedConsortiumV1Input, request))
    invalid = normalize_consortium_request_v1(cast(ConsortiumRequest, "invalid"))
    assert isinstance(invalid, DomainFailure) and invalid.code == "invalid_input"
    with pytest.raises(ValueError):
        calculate_consortium_v1(NormalizedConsortiumV1Input("{}"))


@settings(max_examples=35, derandomize=True, database=None, deadline=None)
@given(term=st.integers(1, 90), fraction=st.integers(1, 100), fee=st.integers(0, 9))
def test_bounded_properties_protect_nonuniform_schedules_and_conservation(term: int, fraction: int, fee: int) -> None:
    # Alternate 1/2 BRL credit components; independently sum supplied components.
    rows = tuple(ConsortiumScheduleInput(m, "1.00" if m % 2 else "2.00", f"0.0{fee}", "0.00", "0.00") for m in range(1, term + 1))
    letter = sum(Decimal(row.credit_component) for row in rows)
    contemplation = 1 + (term - 1) * fraction // 100
    request = replace(synthetic_request(term=term, contemplation=contemplation), monthly_schedule=rows, credit_letter=f"{letter:.2f}", property_price=f"{letter:.2f}")
    _assert_identities(request)
    assert _result(request) == _result(request)
