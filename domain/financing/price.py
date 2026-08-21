"""Pure deterministic Price calculation with exact rational installments."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction

from domain.financing.contracts import (
    ComparisonLedgerRow,
    FinancingContractualRow,
    FinancingRequest,
    NormalizedFinancingInput,
    build_financing_comparison_ledger,
    calculation_context,
    money,
    normalize_financing_request,
    post_decimal,
)
from domain.ledger import post_nonnegative_fraction
from domain.values import DomainFailure
from domain.financing.v2 import (
    FinancingV2Result,
    NormalizedV2FinancingInput,
    calculate_price_v2 as _calculate_price_v2,
    normalize_price_request_v2 as _normalize_price_request_v2,
)
from domain.financing.v3 import (
    FinancingV3Result,
    NormalizedV3FinancingInput,
    calculate_price_v3 as _calculate_price_v3,
    normalize_price_request_v3 as _normalize_price_request_v3,
)


PriceRequest = FinancingRequest
NormalizedPriceInput = NormalizedFinancingInput
PriceContractualRow = FinancingContractualRow


@dataclass(frozen=True, slots=True)
class PriceResult:
    """Immutable Price output with shared schedule and ledger rows."""

    contractual_schedule: tuple[PriceContractualRow, ...]
    comparison_ledger: tuple[ComparisonLedgerRow, ...]


def normalize_price_request(request: PriceRequest) -> NormalizedPriceInput | DomainFailure:
    """Normalize a Price request through the neutral financing boundary."""
    return normalize_financing_request(request)


def calculate_price(input_value: NormalizedPriceInput) -> PriceResult:
    """Calculate Price postings using exact rational regular-installment math."""
    with localcontext(calculation_context(input_value)):
        schedule = _build_contractual_schedule(input_value)
        ledger = build_financing_comparison_ledger(input_value, schedule)
    return PriceResult(contractual_schedule=schedule, comparison_ledger=ledger)


def normalize_price_request_v2(request: PriceRequest) -> NormalizedV2FinancingInput | DomainFailure:
    """Select Price v2 explicitly before normalization."""
    return _normalize_price_request_v2(request)


def calculate_price_v2(input_value: NormalizedV2FinancingInput) -> FinancingV2Result:
    """Project the retained Price v2 evaluator output."""
    return _calculate_price_v2(input_value)


def normalize_price_request_v3(request: PriceRequest) -> NormalizedV3FinancingInput | DomainFailure:
    """Select Price v3 explicitly before normalization."""
    return _normalize_price_request_v3(request)


def calculate_price_v3(input_value: NormalizedV3FinancingInput) -> FinancingV3Result:
    """Project the centavo-safe Price v3 evaluator output."""
    return _calculate_price_v3(input_value)


def _build_contractual_schedule(input_value: NormalizedPriceInput) -> tuple[PriceContractualRow, ...]:
    rows: list[PriceContractualRow] = []
    opening = input_value.principal.amount
    rate = _fraction(input_value.effective_monthly_rate.amount)
    regular_payment = _regular_payment(_fraction(input_value.principal.amount), rate, input_value.term_months)
    for month in range(1, input_value.term_months + 1):
        interest = post_nonnegative_fraction(_fraction(opening) * rate)
        if month == input_value.term_months:
            amortization = opening
            payment = post_decimal(interest + amortization)
        else:
            payment = regular_payment
            amortization = post_decimal(payment - interest)
        closing = post_decimal(opening - amortization)
        rows.append(
            PriceContractualRow(
                month=month,
                opening_principal_balance=money(opening),
                interest=money(interest),
                amortization=money(amortization),
                payment=money(payment),
                closing_principal_balance=money(closing),
            )
        )
        opening = closing
    return tuple(rows)


def _regular_payment(principal: Fraction, rate: Fraction, term_months: int) -> Decimal:
    if rate == 0:
        return post_nonnegative_fraction(principal / term_months)
    growth = (Fraction(1) + rate) ** term_months
    return post_nonnegative_fraction(principal * rate * growth / (growth - 1))


def _fraction(value: Decimal) -> Fraction:
    numerator, denominator = value.as_integer_ratio()
    return Fraction(numerator, denominator)
