"""Neutral deterministic comparison-ledger primitives."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from domain.values import BRLMoney, DomainFailure


COMPARISON_MONTHS = 60


@dataclass(frozen=True, slots=True)
class ComparisonLedgerRow:
    """One closing row in the fixed 60-month strategy comparison domain."""

    month: int
    cash: BRLMoney
    liquid_financial_assets: BRLMoney
    consortium_credit_right_balance: BRLMoney
    property_value: BRLMoney
    financing_principal_balance: BRLMoney
    consortium_credit_obligation_balance: BRLMoney
    recoverable_transfer: BRLMoney
    nonrecoverable_housing_cost: BRLMoney
    total_liabilities: BRLMoney
    home_equity: BRLMoney
    liquidity: BRLMoney
    net_worth: BRLMoney
    cumulative_housing_cost: BRLMoney


def comparison_ledger_row(
    *,
    month: int,
    cash: Decimal,
    liquid_financial_assets: Decimal,
    consortium_credit_right_balance: Decimal,
    property_value: Decimal,
    financing_principal_balance: Decimal,
    consortium_credit_obligation_balance: Decimal,
    recoverable_transfer: Decimal,
    nonrecoverable_housing_cost: Decimal,
    cumulative_housing_cost: Decimal,
) -> ComparisonLedgerRow:
    """Build one row from closing balances and classified flows.

    Strategies own their balance transitions. This constructor owns only the
    common derived accounting identities.
    """
    total_liabilities = post_fraction(
        Fraction(financing_principal_balance) + Fraction(consortium_credit_obligation_balance)
    )
    home_equity = post_fraction(Fraction(property_value) - Fraction(total_liabilities))
    liquidity = post_fraction(Fraction(cash) + Fraction(liquid_financial_assets))
    net_worth = post_fraction(
        Fraction(cash)
        + Fraction(liquid_financial_assets)
        + Fraction(consortium_credit_right_balance)
        + Fraction(property_value)
        - Fraction(total_liabilities)
    )
    return ComparisonLedgerRow(
        month=month,
        cash=money(cash),
        liquid_financial_assets=money(liquid_financial_assets),
        consortium_credit_right_balance=money(consortium_credit_right_balance),
        property_value=money(property_value),
        financing_principal_balance=money(financing_principal_balance),
        consortium_credit_obligation_balance=money(consortium_credit_obligation_balance),
        recoverable_transfer=money(recoverable_transfer),
        nonrecoverable_housing_cost=money(nonrecoverable_housing_cost),
        total_liabilities=money(total_liabilities),
        home_equity=money(home_equity),
        liquidity=money(liquidity),
        net_worth=money(net_worth),
        cumulative_housing_cost=money(cumulative_housing_cost),
    )


def post_decimal(amount: Decimal) -> Decimal:
    """Post a finite monetary amount using the accepted centavo rule."""
    return post_fraction(Fraction(amount))


def post_fraction(amount: Fraction) -> Decimal:
    """Post an exact rational amount to centavos with half-up rounding."""
    if amount < 0:
        return -post_nonnegative_fraction(-amount)
    return post_nonnegative_fraction(amount)


def post_nonnegative_fraction(amount: Fraction) -> Decimal:
    """Post a non-negative exact rational amount to centavos with half-up."""
    if amount < 0:
        raise ValueError("monetary posting amount cannot be negative")
    cent_amount = amount * 100
    posted_cents = (2 * cent_amount.numerator + cent_amount.denominator) // (
        2 * cent_amount.denominator
    )
    return Decimal(f"{posted_cents}e-2")


def money(amount: Decimal) -> BRLMoney:
    """Create a posted BRL value from a calculated amount."""
    return BRLMoney(format(post_decimal(amount), ".2f"))


def normalize_brl_money(name: str, raw_value: object) -> BRLMoney | DomainFailure:
    """Normalize one exact-two-fraction BRL value at a domain boundary."""
    if not isinstance(raw_value, str):
        return DomainFailure("invalid_input", f"{name} must be an exact-two-fraction BRL string")
    try:
        return BRLMoney(raw_value)
    except ValueError:
        return DomainFailure("invalid_input", f"{name} must be an exact-two-fraction BRL string")
