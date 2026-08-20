"""Guarantee-focused tests for exact deterministic Price financing."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal, ROUND_DOWN, localcontext
import json
from pathlib import Path
from typing import Callable, cast

from domain.financing.contracts import (
    ComparisonLedgerRow,
    FinancingContractualRow,
    FinancingRequest,
)
from domain.financing.price import (
    PriceRequest,
    calculate_price,
    calculate_price_v2,
    normalize_price_request,
    normalize_price_request_v2,
)
from domain.financing.sac import SACRequest, normalize_sac_request, normalize_sac_request_v2
from domain.values import DomainFailure


FIXTURE_PATH = Path("docs/fixtures/milestone-0-synthetic-regression.json")


def _base_request(**changes: object) -> PriceRequest:
    values: dict[str, object] = {
        "comparison_opening_cash": "20000.00",
        "property_price": "1500.00",
        "cash_down_payment": "300.00",
        "principal": "1200.00",
        "term_months": 12,
        "rate_value": "0.01",
        "rate_convention": "effective_monthly",
    }
    values.update(changes)
    return cast(Callable[..., PriceRequest], PriceRequest)(**values)


def _normalized(**changes: object):
    result = normalize_price_request(_base_request(**changes))
    assert not isinstance(result, DomainFailure)
    return result


def _failure(**changes: object) -> DomainFailure:
    result = normalize_price_request(_base_request(**changes))
    assert isinstance(result, DomainFailure)
    return result


def _normalized_v2(**changes: object):
    result = normalize_price_request_v2(_base_request(**changes))
    assert not isinstance(result, DomainFailure)
    return result


def test_strategies_share_the_neutral_request_and_normalization_boundary() -> None:
    assert SACRequest is FinancingRequest
    assert PriceRequest is FinancingRequest
    for changes in (
        {"principal": "1.0"},
        {"rate_value": "0.01", "rate_convention": "effective_annual"},
        {"fgts_amount": "1.00"},
        {"fee_amount": "1.00"},
    ):
        price = normalize_price_request(_base_request(**changes))
        sac = normalize_sac_request(_base_request(**changes))
        assert isinstance(price, DomainFailure)
        assert isinstance(sac, DomainFailure)
        assert price.code == sac.code


def test_synthetic_unsupported_clause_matrix_has_sac_price_failure_parity() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    matrix = fixture["fixtures"]["financing_unsupported_clauses"]
    for case in matrix["cases"]:
        price = normalize_price_request(_base_request(**case["changes"]))
        sac = normalize_sac_request(_base_request(**case["changes"]))
        assert isinstance(price, DomainFailure), case["name"]
        assert isinstance(sac, DomainFailure), case["name"]
        assert price.code == case["expected_failure_code"], case["name"]
        assert sac.code == price.code, case["name"]


def test_price_fixture_checkpoints_are_exact() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    price = fixture["fixtures"]["price_basic"]
    request = PriceRequest(
        comparison_opening_cash=fixture["shared_conventions"]["comparison_opening_cash"],
        property_price=price["inputs"]["property_price"],
        cash_down_payment=price["inputs"]["cash_down_payment"],
        principal=price["inputs"]["principal"],
        term_months=price["inputs"]["term_months"],
        rate_value=price["inputs"]["effective_monthly_rate"],
        rate_convention="effective_monthly",
    )
    normalized = normalize_price_request(request)
    assert not isinstance(normalized, DomainFailure)
    result = calculate_price(normalized)
    for checkpoint in price["checkpoints"]:
        if "month" in checkpoint:
            ledger = result.comparison_ledger[checkpoint["month"]]
            for name, expected in checkpoint["expected"].items():
                actual = (
                    getattr(result.contractual_schedule[checkpoint["month"] - 1], name)
                    if name in {"interest", "amortization", "payment"}
                    else getattr(ledger, name)
                )
                assert actual.as_string == expected, f"month {checkpoint['month']} {name}"
        else:
            ledger = result.comparison_ledger[0]
            for name, expected in checkpoint["expected"].items():
                assert getattr(ledger, name).as_string == expected, f"month 0 {name}"


def test_zero_rate_regular_payment_uses_exact_half_up_posting() -> None:
    result = calculate_price(
        _normalized(
            comparison_opening_cash="1.01",
            property_price="1.01",
            cash_down_payment="0.00",
            principal="1.01",
            term_months=2,
            rate_value="0",
        )
    )
    assert result.contractual_schedule[0].payment.as_string == "0.51"
    assert result.contractual_schedule[0].amortization.as_string == "0.51"
    assert result.contractual_schedule[-1].payment.as_string == "0.50"
    assert result.contractual_schedule[-1].closing_principal_balance.as_string == "0.00"


def test_nonzero_rate_regular_payment_uses_exact_half_up_posting() -> None:
    result = calculate_price(
        _normalized(
            comparison_opening_cash="0.05",
            property_price="0.05",
            cash_down_payment="0.00",
            principal="0.05",
            term_months=2,
            rate_value="0.5",
        )
    )
    assert result.contractual_schedule[0].payment.as_string == "0.05"
    assert result.contractual_schedule[0].interest.as_string == "0.03"
    assert result.contractual_schedule[-1].closing_principal_balance.as_string == "0.00"


def test_price_is_independent_of_the_callers_decimal_context() -> None:
    normalized = _normalized()
    baseline = calculate_price(normalized)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert calculate_price(normalized) == baseline


def test_price_uses_shared_rows_and_separate_time_domains() -> None:
    result = calculate_price(
        _normalized(
            property_price="7200.00",
            cash_down_payment="0.00",
            principal="7200.00",
            term_months=72,
            rate_value="0",
        )
    )
    assert isinstance(result.contractual_schedule[0], FinancingContractualRow)
    assert isinstance(result.comparison_ledger[0], ComparisonLedgerRow)
    assert len(result.contractual_schedule) == 72
    assert len(result.comparison_ledger) == 61
    assert result.comparison_ledger[-1].month == 60
    assert result.comparison_ledger[-1].financing_principal_balance.as_string == "1200.00"


def test_price_schedule_and_ledger_invariants_hold_for_every_posted_period() -> None:
    result = calculate_price(_normalized())
    previous_closing = None
    for row in result.contractual_schedule:
        if previous_closing is not None:
            assert row.opening_principal_balance.amount == previous_closing
        assert row.opening_principal_balance.amount >= Decimal("0.00")
        assert row.amortization.amount >= Decimal("0.00")
        assert row.closing_principal_balance.amount >= Decimal("0.00")
        assert row.payment.amount == row.interest.amount + row.amortization.amount
        assert row.closing_principal_balance.amount == (
            row.opening_principal_balance.amount - row.amortization.amount
        )
        previous_closing = row.closing_principal_balance.amount
    assert result.contractual_schedule[-1].closing_principal_balance.amount == Decimal("0.00")

    previous_row = None
    for row in result.comparison_ledger:
        if row.month > 0 and row.month <= len(result.contractual_schedule):
            posting = result.contractual_schedule[row.month - 1]
            assert row.financing_principal_balance.amount == posting.closing_principal_balance.amount
            assert row.nonrecoverable_housing_cost.amount == posting.interest.amount
            assert previous_row is not None
            assert row.cash.amount == previous_row.cash.amount - posting.payment.amount
        elif previous_row is not None:
            assert row.financing_principal_balance.amount == Decimal("0.00")
            assert row.nonrecoverable_housing_cost.amount == Decimal("0.00")
            assert row.cash.amount == previous_row.cash.amount
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
        expected_cumulative_cost = row.nonrecoverable_housing_cost.amount
        if previous_row is not None:
            expected_cumulative_cost += previous_row.cumulative_housing_cost.amount
        assert row.cumulative_housing_cost.amount == expected_cumulative_cost
        previous_row = row


def test_price_outputs_are_deterministic_and_immutable() -> None:
    first = calculate_price(_normalized())
    assert first == calculate_price(_normalized())
    try:
        setattr(first.contractual_schedule[0], "month", 2)
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("contractual rows must be immutable")
    try:
        setattr(first, "comparison_ledger", ())
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("result collections must be immutable")


def test_price_accepts_the_same_explicit_zero_exclusions_as_sac() -> None:
    normalized = _normalized(
        fgts_amount="0.00",
        subsidy_amount="0.00",
        tax_amount="0.00",
        transaction_cost_amount="0.00",
        fee_amount="0.00",
        insurance_amount="0.00",
        extraordinary_amortization_amount="0.00",
        indexation="documented_zero",
    )
    assert calculate_price(normalized) == calculate_price(_normalized())
    assert _failure(indexation="requested_nonzero").code == "unsupported_contract_clause"


def test_price_v2_fixed_fee_is_explicit_and_does_not_change_principal_path() -> None:
    result = calculate_price_v2(_normalized_v2(fee_amount="2.50"))
    first = result.contractual_schedule[0]
    assert first.fee.as_string == "2.50"
    assert first.payment.as_string == "109.12"
    assert result.comparison_ledger[1].nonrecoverable_housing_cost.as_string == "14.50"
    assert result.comparison_ledger[1].financing_principal_balance.as_string == "1105.38"


def test_price_v2_absent_and_zero_fee_preserve_financial_values() -> None:
    absent = calculate_price_v2(_normalized_v2())
    zero = calculate_price_v2(_normalized_v2(fee_amount="0.00"))
    assert absent == zero
    assert all(row.fee.as_string == "0.00" for row in absent.contractual_schedule)


def test_price_v2_matches_independent_centavo_checkpoints() -> None:
    result = calculate_price_v2(_normalized_v2(fee_amount="2.50"))
    rows = (result.contractual_schedule[0], result.contractual_schedule[5], result.contractual_schedule[11])
    assert [
        (
            row.month,
            row.interest.as_string,
            row.amortization.as_string,
            row.fee.as_string,
            row.payment.as_string,
            row.closing_principal_balance.as_string,
        )
        for row in rows
    ] == [
        (1, "12.00", "94.62", "2.50", "109.12", "1105.38"),
        (6, "7.17", "99.45", "2.50", "109.12", "617.89"),
        (12, "1.06", "105.54", "2.50", "109.10", "0.00"),
    ]
    ledger = result.comparison_ledger
    assert (
        ledger[6].cash.as_string,
        ledger[6].nonrecoverable_housing_cost.as_string,
        ledger[6].cumulative_housing_cost.as_string,
    ) == ("19045.28", "9.67", "72.61")
    assert (
        ledger[12].cash.as_string,
        ledger[12].cumulative_housing_cost.as_string,
        ledger[13].cash.as_string,
        ledger[13].nonrecoverable_housing_cost.as_string,
        ledger[13].cumulative_housing_cost.as_string,
    ) == ("18390.58", "109.42", "18390.58", "0.00", "109.42")


def test_v2_normalized_inputs_cannot_cross_strategy_boundaries() -> None:
    normalized = normalize_sac_request_v2(_base_request(fee_amount="2.50"))
    assert not isinstance(normalized, DomainFailure)
    try:
        calculate_price_v2(normalized)
    except ValueError:
        pass
    else:
        raise AssertionError("v2 normalized inputs must retain their selected strategy")
