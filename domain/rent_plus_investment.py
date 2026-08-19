"""Pure deterministic rent-plus-investment calculation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal

from domain.ledger import (
    COMPARISON_MONTHS,
    ComparisonLedgerRow,
    comparison_ledger_row,
    money,
    normalize_brl_money,
    post_nonnegative_fraction,
)
from domain.values import BRLMoney, DeclaredRate, DomainFailure, EffectiveMonthlyRate


UnsupportedDeclaration = Literal["not_requested", "requested"]
_ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class RentPlusInvestmentRequest:
    """Closed request for the initial supported rent-plus strategy."""

    comparison_opening_cash: str
    starting_monthly_rent: str
    initial_invested_capital: str
    monthly_contribution: str
    rent_adjustment_rate_value: str
    rent_adjustment_rate_convention: str
    return_rate_value: str
    return_rate_convention: str
    first_rent_adjustment_month: int
    tax_amount: str | None = None
    investment_product: UnsupportedDeclaration = "not_requested"
    withdrawal_restriction: UnsupportedDeclaration = "not_requested"
    future_purchase: UnsupportedDeclaration = "not_requested"


@dataclass(frozen=True, slots=True)
class NormalizedRentPlusInvestmentInput:
    """Validated input accepted by the pure rent-plus calculator."""

    comparison_opening_cash: BRLMoney
    starting_monthly_rent: BRLMoney
    initial_invested_capital: BRLMoney
    monthly_contribution: BRLMoney
    effective_annual_rent_adjustment: Decimal
    effective_monthly_net_return: EffectiveMonthlyRate
    first_rent_adjustment_month: int


@dataclass(frozen=True, slots=True)
class RentPlusInvestmentMonthlyRow:
    """One strategy-owned rent-plus posting that reconciles asset return."""

    month: int
    opening_liquid_financial_assets: BRLMoney
    investment_return: BRLMoney
    rent: BRLMoney
    monthly_contribution: BRLMoney
    closing_liquid_financial_assets: BRLMoney


@dataclass(frozen=True, slots=True)
class RentPlusInvestmentResult:
    """Immutable rent-plus postings and common comparison ledger."""

    monthly_postings: tuple[RentPlusInvestmentMonthlyRow, ...]
    comparison_ledger: tuple[ComparisonLedgerRow, ...]


def normalize_rent_plus_investment_request(
    request: RentPlusInvestmentRequest,
) -> NormalizedRentPlusInvestmentInput | DomainFailure:
    """Normalize the closed request before any rent-plus calculation."""
    money_fields = (
        ("comparison_opening_cash", request.comparison_opening_cash),
        ("starting_monthly_rent", request.starting_monthly_rent),
        ("initial_invested_capital", request.initial_invested_capital),
        ("monthly_contribution", request.monthly_contribution),
    )
    normalized_money: dict[str, BRLMoney] = {}
    for name, raw_value in money_fields:
        money_value = normalize_brl_money(name, raw_value)
        if isinstance(money_value, DomainFailure):
            return money_value
        normalized_money[name] = money_value

    tax_failure = _classify_tax(request.tax_amount)
    if tax_failure is not None:
        return tax_failure
    declaration_failure = _classify_unsupported_declarations(request)
    if declaration_failure is not None:
        return declaration_failure

    annual_rate = _normalize_rate(
        request.rent_adjustment_rate_value,
        request.rent_adjustment_rate_convention,
        "effective_annual",
        "rent adjustment",
    )
    if isinstance(annual_rate, DomainFailure):
        return annual_rate
    return_rate = _normalize_rate(
        request.return_rate_value,
        request.return_rate_convention,
        "effective_monthly",
        "return",
    )
    if isinstance(return_rate, DomainFailure):
        return return_rate

    if type(request.first_rent_adjustment_month) is not int or request.first_rent_adjustment_month <= 1:
        return _invalid("first_rent_adjustment_month must be an integer greater than one")
    if normalized_money["starting_monthly_rent"].amount <= _ZERO:
        return _invalid("starting_monthly_rent must be positive")
    if normalized_money["initial_invested_capital"].amount < _ZERO:
        return _invalid("initial_invested_capital cannot be negative")
    if normalized_money["monthly_contribution"].amount < _ZERO:
        return _invalid("monthly_contribution cannot be negative")

    return NormalizedRentPlusInvestmentInput(
        comparison_opening_cash=normalized_money["comparison_opening_cash"],
        starting_monthly_rent=normalized_money["starting_monthly_rent"],
        initial_invested_capital=normalized_money["initial_invested_capital"],
        monthly_contribution=normalized_money["monthly_contribution"],
        effective_annual_rent_adjustment=annual_rate,
        effective_monthly_net_return=EffectiveMonthlyRate(
            DeclaredRate(request.return_rate_value, request.return_rate_convention)
        ),
        first_rent_adjustment_month=request.first_rent_adjustment_month,
    )


def calculate_rent_plus_investment(
    input_value: NormalizedRentPlusInvestmentInput,
) -> RentPlusInvestmentResult | DomainFailure:
    """Calculate rent-plus postings and ledger rows without partial results."""
    cash_fraction = Fraction(input_value.comparison_opening_cash.amount) - Fraction(
        input_value.initial_invested_capital.amount
    )
    if cash_fraction < 0:
        return DomainFailure("infeasible_scenario", "initial invested capital exceeds available cash")

    cash = post_nonnegative_fraction(cash_fraction)
    liquid_assets = input_value.initial_invested_capital.amount
    cumulative_housing_cost = _ZERO
    ledger_rows = [
        comparison_ledger_row(
            month=0,
            cash=cash,
            liquid_financial_assets=liquid_assets,
            consortium_credit_right_balance=_ZERO,
            property_value=_ZERO,
            financing_principal_balance=_ZERO,
            consortium_credit_obligation_balance=_ZERO,
            recoverable_transfer=input_value.initial_invested_capital.amount,
            nonrecoverable_housing_cost=_ZERO,
            cumulative_housing_cost=cumulative_housing_cost,
        )
    ]
    postings: list[RentPlusInvestmentMonthlyRow] = []
    rent = input_value.starting_monthly_rent.amount
    annual_adjustment = Fraction(input_value.effective_annual_rent_adjustment)
    monthly_return = Fraction(input_value.effective_monthly_net_return.amount)

    for month in range(1, COMPARISON_MONTHS + 1):
        if month >= input_value.first_rent_adjustment_month and (
            month - input_value.first_rent_adjustment_month
        ) % 12 == 0:
            rent = post_nonnegative_fraction(Fraction(rent) * (Fraction(1) + annual_adjustment))
        investment_return = post_nonnegative_fraction(Fraction(liquid_assets) * monthly_return)
        next_cash = (
            Fraction(cash)
            - Fraction(rent)
            - Fraction(input_value.monthly_contribution.amount)
        )
        if next_cash < 0:
            return DomainFailure("infeasible_scenario", f"cash is insufficient in month {month}")
        closing_liquid_assets = post_nonnegative_fraction(
            Fraction(liquid_assets)
            + Fraction(investment_return)
            + Fraction(input_value.monthly_contribution.amount)
        )
        cash = post_nonnegative_fraction(next_cash)
        cumulative_housing_cost = post_nonnegative_fraction(
            Fraction(cumulative_housing_cost) + Fraction(rent)
        )
        postings.append(
            RentPlusInvestmentMonthlyRow(
                month=month,
                opening_liquid_financial_assets=money(liquid_assets),
                investment_return=money(investment_return),
                rent=money(rent),
                monthly_contribution=input_value.monthly_contribution,
                closing_liquid_financial_assets=money(closing_liquid_assets),
            )
        )
        ledger_rows.append(
            comparison_ledger_row(
                month=month,
                cash=cash,
                liquid_financial_assets=closing_liquid_assets,
                consortium_credit_right_balance=_ZERO,
                property_value=_ZERO,
                financing_principal_balance=_ZERO,
                consortium_credit_obligation_balance=_ZERO,
                recoverable_transfer=input_value.monthly_contribution.amount,
                nonrecoverable_housing_cost=rent,
                cumulative_housing_cost=cumulative_housing_cost,
            )
        )
        liquid_assets = closing_liquid_assets

    return RentPlusInvestmentResult(
        monthly_postings=tuple(postings), comparison_ledger=tuple(ledger_rows)
    )


def _classify_tax(raw_value: object) -> DomainFailure | None:
    if raw_value is None:
        return None
    tax_amount = normalize_brl_money("tax_amount", raw_value)
    if isinstance(tax_amount, DomainFailure):
        return tax_amount
    if tax_amount.amount == _ZERO:
        return None
    return DomainFailure("unsupported_rule", "tax_amount is not supported")


def _classify_unsupported_declarations(
    request: RentPlusInvestmentRequest,
) -> DomainFailure | None:
    for name, value in (
        ("investment_product", request.investment_product),
        ("withdrawal_restriction", request.withdrawal_restriction),
        ("future_purchase", request.future_purchase),
    ):
        if value == "not_requested":
            continue
        if value == "requested":
            return DomainFailure("unsupported_contract_clause", f"{name} is not supported")
        return _invalid(f"{name} declaration is invalid")
    return None


def _normalize_rate(
    raw_value: object,
    convention: object,
    expected_convention: str,
    name: str,
) -> Decimal | DomainFailure:
    try:
        declared_rate = DeclaredRate(raw_value, convention)  # type: ignore[arg-type]
    except ValueError:
        return _invalid(f"{name} rate value and convention must be finite decimal and string values")
    if declared_rate.convention != expected_convention:
        return DomainFailure("unsupported_rate_convention", f"{name} rate convention is not supported")
    if declared_rate.amount < 0:
        return _invalid(f"{name} rate must be non-negative")
    return declared_rate.amount


def _invalid(detail: str) -> DomainFailure:
    return DomainFailure("invalid_input", detail)
