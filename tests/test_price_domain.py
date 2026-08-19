"""Guarantee-focused tests for exact deterministic Price financing."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal, ROUND_DOWN, localcontext
import json
from pathlib import Path
import unittest

from domain.financing.contracts import (
    ComparisonLedgerRow,
    FinancingContractualRow,
    FinancingRequest,
)
from domain.financing.price import PriceRequest, calculate_price, normalize_price_request
from domain.financing.sac import SACRequest, normalize_sac_request
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
    return PriceRequest(**values)  # type: ignore[arg-type]


def _normalized(**changes: object):
    result = normalize_price_request(_base_request(**changes))
    assert not isinstance(result, DomainFailure)
    return result


def _failure(**changes: object) -> DomainFailure:
    result = normalize_price_request(_base_request(**changes))
    assert isinstance(result, DomainFailure)
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


def test_price_outputs_are_deterministic_and_immutable() -> None:
    first = calculate_price(_normalized())
    assert first == calculate_price(_normalized())
    try:
        first.contractual_schedule[0].month = 2  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("contractual rows must be immutable")
    try:
        first.comparison_ledger += ()  # type: ignore[misc]
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


def load_tests(
    loader: unittest.TestLoader,
    standard_tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    """Expose function tests without adding test-only implementation classes."""
    tests = (
        test_strategies_share_the_neutral_request_and_normalization_boundary,
        test_price_fixture_checkpoints_are_exact,
        test_zero_rate_regular_payment_uses_exact_half_up_posting,
        test_price_is_independent_of_the_callers_decimal_context,
        test_price_uses_shared_rows_and_separate_time_domains,
        test_price_outputs_are_deterministic_and_immutable,
        test_price_accepts_the_same_explicit_zero_exclusions_as_sac,
    )
    return unittest.TestSuite(unittest.FunctionTestCase(test) for test in tests)
