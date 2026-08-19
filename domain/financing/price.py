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
from domain.values import DomainFailure


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


def _build_contractual_schedule(input_value: NormalizedPriceInput) -> tuple[PriceContractualRow, ...]:
    rows: list[PriceContractualRow] = []
    opening = input_value.principal.amount
    rate = _fraction(input_value.effective_monthly_rate.amount)
    regular_payment = _regular_payment(_fraction(input_value.principal.amount), rate, input_value.term_months)
    for month in range(1, input_value.term_months + 1):
        interest = _post_fraction(_fraction(opening) * rate)
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
        return _post_fraction(principal / term_months)
    growth = (Fraction(1) + rate) ** term_months
    return _post_fraction(principal * rate * growth / (growth - 1))


def _fraction(value: Decimal) -> Fraction:
    numerator, denominator = value.as_integer_ratio()
    return Fraction(numerator, denominator)


def _post_fraction(amount: Fraction) -> Decimal:
    if amount < 0:
        raise ValueError("Price posting amount cannot be negative")
    cent_amount = amount * 100
    posted_cents = (2 * cent_amount.numerator + cent_amount.denominator) // (2 * cent_amount.denominator)
    return Decimal(posted_cents).scaleb(-2)
