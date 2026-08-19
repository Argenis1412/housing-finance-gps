"""Guarantee-focused tests for the deterministic SAC domain."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal, ROUND_DOWN, localcontext
import json
from pathlib import Path
import unittest

from domain.financing.sac import (
    SACRequest,
    calculate_sac,
    calculate_sac_v2,
    normalize_sac_request,
    normalize_sac_request_v2,
)
from domain.values import BRLMoney, DomainFailure


FIXTURE_PATH = Path("docs/fixtures/milestone-0-synthetic-regression.json")


def _base_request(**changes: object) -> SACRequest:
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
    return SACRequest(**values)  # type: ignore[arg-type]


def _normalized(**changes: object):
    result = normalize_sac_request(_base_request(**changes))
    assert not isinstance(result, DomainFailure)
    return result


def _failure(**changes: object) -> DomainFailure:
    result = normalize_sac_request(_base_request(**changes))
    assert isinstance(result, DomainFailure)
    return result


def _normalized_v2(**changes: object):
    result = normalize_sac_request_v2(_base_request(**changes))
    assert not isinstance(result, DomainFailure)
    return result


def _failure_v2(**changes: object) -> DomainFailure:
    result = normalize_sac_request_v2(_base_request(**changes))
    assert isinstance(result, DomainFailure)
    return result


def test_money_requires_exact_contract_representation() -> None:
    for value in ("1.0", "1.000", "1.001", 1.0, Decimal("1.00")):
        assert _failure(principal=value).code == "invalid_input"
    assert BRLMoney("1.00").as_string == "1.00"


def test_rate_and_term_validation_are_explicit() -> None:
    for changes in (
        {"rate_value": 0.01},
        {"rate_value": "NaN"},
        {"rate_value": "-0.01"},
        {"term_months": True},
    ):
        assert _failure(**changes).code == "invalid_input"


def test_normalization_rejects_invalid_exclusions_and_financing_relationships() -> None:
    for changes in (
        {"transaction_cost_amount": "1.0"},
        {"indexation": "unknown"},
        {"property_price": "0.00", "cash_down_payment": "0.00", "principal": "0.00"},
        {"property_price": "300.00", "cash_down_payment": "300.00", "principal": "0.00"},
        {"property_price": "100.00", "cash_down_payment": "-1.00", "principal": "101.00"},
        {"cash_down_payment": "301.00"},
    ):
        assert _failure(**changes).code == "invalid_input"


def test_normalization_balance_check_ignores_callers_decimal_context() -> None:
    request = _base_request(
        comparison_opening_cash="1.01",
        property_price="1.01",
        cash_down_payment="0.01",
        principal="1.00",
        term_months=1,
        rate_value="0",
    )
    with localcontext() as context:
        context.prec = 2
        assert not isinstance(normalize_sac_request(request), DomainFailure)


def test_non_monthly_zero_is_classified_before_effective_rate_construction() -> None:
    normalized = _normalized(rate_value="0", rate_convention="effective_annual")
    assert normalized.effective_monthly_rate.amount == Decimal("0")
    assert _failure(rate_value="0.01", rate_convention="effective_annual").code == "unsupported_rate_convention"


def test_closed_exclusions_use_canonical_failure_categories() -> None:
    for name in ("fgts_amount", "subsidy_amount", "tax_amount"):
        assert _failure(**{name: "1.00"}).code == "unsupported_rule"
    for name in (
        "transaction_cost_amount",
        "fee_amount",
        "insurance_amount",
        "extraordinary_amortization_amount",
    ):
        assert _failure(**{name: "1.00"}).code == "unsupported_contract_clause"
    assert _failure(indexation="requested_nonzero").code == "unsupported_contract_clause"


def test_synthetic_unsupported_clause_matrix_matches_the_financing_boundary() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    matrix = fixture["fixtures"]["financing_unsupported_clauses"]
    for case in matrix["cases"]:
        failure = _failure(**case["changes"])
        assert failure.code == case["expected_failure_code"], case["name"]


def test_explicit_zero_exclusions_have_no_calculation_effect() -> None:
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
    assert calculate_sac(normalized) == calculate_sac(_normalized())


def test_sac_rounding_and_final_settlement() -> None:
    result = calculate_sac(
        _normalized(
            property_price="10.00",
            cash_down_payment="0.00",
            principal="10.00",
            term_months=3,
            rate_value="0.10",
        )
    )
    assert result.contractual_schedule[0].amortization.as_string == "3.33"
    assert result.contractual_schedule[-1].amortization.as_string == "3.34"
    assert result.contractual_schedule[-1].closing_principal_balance.as_string == "0.00"


def test_sac_is_independent_of_callers_decimal_context() -> None:
    normalized = _normalized(
        property_price="10.00",
        cash_down_payment="0.00",
        principal="10.00",
        term_months=3,
        rate_value="0.10",
    )
    baseline = calculate_sac(normalized)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert calculate_sac(normalized) == baseline


def test_sac_accepts_large_two_fraction_amounts() -> None:
    principal = "9" * 60 + ".00"
    normalized = _normalized(
        comparison_opening_cash=principal,
        property_price=principal,
        cash_down_payment="0.00",
        principal=principal,
        term_months=1,
        rate_value="0",
    )
    result = calculate_sac(normalized)
    assert result.contractual_schedule[-1].closing_principal_balance.as_string == "0.00"


def test_schedule_and_ledger_have_separate_time_domains() -> None:
    result = calculate_sac(
        _normalized(
            property_price="7200.00",
            cash_down_payment="0.00",
            principal="7200.00",
            term_months=72,
            rate_value="0",
        )
    )
    assert len(result.contractual_schedule) == 72
    assert len(result.comparison_ledger) == 61
    assert result.comparison_ledger[-1].month == 60
    assert result.comparison_ledger[-1].financing_principal_balance.as_string == "1200.00"


def test_sac_schedule_and_ledger_invariants_hold_for_every_posted_period() -> None:
    result = calculate_sac(_normalized())
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


def test_synthetic_sac_fixture_checkpoints() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    sac = fixture["fixtures"]["sac_basic"]
    request = SACRequest(
        comparison_opening_cash=fixture["shared_conventions"]["comparison_opening_cash"],
        property_price=sac["inputs"]["property_price"],
        cash_down_payment=sac["inputs"]["cash_down_payment"],
        principal=sac["inputs"]["principal"],
        term_months=sac["inputs"]["term_months"],
        rate_value=sac["inputs"]["effective_monthly_rate"],
        rate_convention="effective_monthly",
    )
    normalized = normalize_sac_request(request)
    assert not isinstance(normalized, DomainFailure)
    result = calculate_sac(normalized)
    for checkpoint in sac["checkpoints"]:
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


def test_outputs_are_deterministic_and_immutable() -> None:
    normalized = _normalized()
    first = calculate_sac(normalized)
    assert first == calculate_sac(normalized)
    try:
        first.contractual_schedule[0].month = 2  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("contractual rows must be immutable")
    try:
        first.contractual_schedule += ()  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("result collections must be immutable")
    failure = _failure(principal="1.0")
    try:
        failure.code = "unsupported_rule"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("domain failures must be immutable")


def test_v2_fixed_fee_is_explicit_and_nonrecoverable() -> None:
    result = calculate_sac_v2(_normalized_v2(fee_amount="2.50", term_months=2, rate_value="0"))
    first = result.contractual_schedule[0]
    assert first.fee.as_string == "2.50"
    assert first.payment.as_string == "602.50"
    assert result.comparison_ledger[1].cash.as_string == "19097.50"
    assert result.comparison_ledger[1].nonrecoverable_housing_cost.as_string == "2.50"
    assert result.comparison_ledger[1].financing_principal_balance.as_string == "600.00"
    assert result.comparison_ledger[2].cash.as_string == "18495.00"
    assert result.comparison_ledger[2].cumulative_housing_cost.as_string == "5.00"
    assert result.comparison_ledger[3].cash.as_string == "18495.00"
    assert result.comparison_ledger[3].nonrecoverable_housing_cost.as_string == "0.00"
    assert result.comparison_ledger[3].cumulative_housing_cost.as_string == "5.00"


def test_v2_absent_and_zero_fee_preserve_financial_values() -> None:
    absent = calculate_sac_v2(_normalized_v2())
    zero = calculate_sac_v2(_normalized_v2(fee_amount="0.00"))
    assert absent == zero
    assert all(row.fee.as_string == "0.00" for row in absent.contractual_schedule)


def test_v2_fee_validation_is_explicit_and_v1_remains_rejection_boundary() -> None:
    assert _failure_v2(fee_amount="-1.00").code == "invalid_input"
    assert _failure_v2(fee_amount="1.0").code == "invalid_input"
    assert _failure(fee_amount="1.00").code == "unsupported_contract_clause"

    signed_zero = calculate_sac_v2(_normalized_v2(fee_amount="-0.00"))
    assert signed_zero == calculate_sac_v2(_normalized_v2(fee_amount="0.00"))
    assert all(row.fee.as_string == "0.00" for row in signed_zero.contractual_schedule)


def test_v2_sac_matches_independent_centavo_checkpoints() -> None:
    result = calculate_sac_v2(
        _normalized_v2(fee_amount="2.50", term_months=3, rate_value="0.01")
    )
    schedule = [
        (
            row.month,
            row.interest.as_string,
            row.amortization.as_string,
            row.fee.as_string,
            row.payment.as_string,
            row.closing_principal_balance.as_string,
        )
        for row in result.contractual_schedule
    ]
    assert schedule == [
        (1, "12.00", "400.00", "2.50", "414.50", "800.00"),
        (2, "8.00", "400.00", "2.50", "410.50", "400.00"),
        (3, "4.00", "400.00", "2.50", "406.50", "0.00"),
    ]
    ledger = result.comparison_ledger
    assert (ledger[1].cash.as_string, ledger[1].cumulative_housing_cost.as_string) == (
        "19285.50",
        "14.50",
    )
    assert (ledger[3].cash.as_string, ledger[3].cumulative_housing_cost.as_string) == (
        "18468.50",
        "31.50",
    )
    assert (ledger[4].cash.as_string, ledger[4].cumulative_housing_cost.as_string) == (
        "18468.50",
        "31.50",
    )


def test_v2_outputs_are_context_independent_deterministic_and_immutable() -> None:
    normalized = _normalized_v2(fee_amount="2.50")
    expected = calculate_sac_v2(normalized)
    assert calculate_sac_v2(normalized) == expected

    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert calculate_sac_v2(normalized) == expected

    try:
        expected.contractual_schedule[0].fee = BRLMoney("0.00")  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("v2 contractual rows must be immutable")


def load_tests(
    loader: unittest.TestLoader,
    standard_tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    """Expose function tests without introducing a tenth implementation class."""
    tests = (
        test_money_requires_exact_contract_representation,
        test_rate_and_term_validation_are_explicit,
        test_normalization_rejects_invalid_exclusions_and_financing_relationships,
        test_normalization_balance_check_ignores_callers_decimal_context,
        test_non_monthly_zero_is_classified_before_effective_rate_construction,
        test_closed_exclusions_use_canonical_failure_categories,
        test_synthetic_unsupported_clause_matrix_matches_the_financing_boundary,
        test_explicit_zero_exclusions_have_no_calculation_effect,
        test_sac_rounding_and_final_settlement,
        test_sac_is_independent_of_callers_decimal_context,
        test_sac_accepts_large_two_fraction_amounts,
        test_schedule_and_ledger_have_separate_time_domains,
        test_sac_schedule_and_ledger_invariants_hold_for_every_posted_period,
        test_synthetic_sac_fixture_checkpoints,
        test_outputs_are_deterministic_and_immutable,
        test_v2_fixed_fee_is_explicit_and_nonrecoverable,
        test_v2_absent_and_zero_fee_preserve_financial_values,
        test_v2_fee_validation_is_explicit_and_v1_remains_rejection_boundary,
        test_v2_sac_matches_independent_centavo_checkpoints,
        test_v2_outputs_are_context_independent_deterministic_and_immutable,
    )
    return unittest.TestSuite(unittest.FunctionTestCase(test) for test in tests)
