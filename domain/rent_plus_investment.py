"""Pure deterministic rent-plus-investment calculation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Literal, cast

from domain.ledger import ComparisonLedgerRow
from domain import rent_replay_v1 as _retained
from domain.values import BRLMoney, DeclaredRate, DomainFailure, EffectiveMonthlyRate, FailureCode


UnsupportedDeclaration = Literal["not_requested", "requested"]


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


def _failure(outcome: dict[str, object]) -> DomainFailure:
    return DomainFailure(cast(FailureCode, outcome["code"]), cast(str, outcome["detail"]))


def normalize_rent_plus_investment_request(
    request: RentPlusInvestmentRequest,
) -> NormalizedRentPlusInvestmentInput | DomainFailure:
    """Preserve the live normalization boundary over the retained authority."""
    outcome = _retained.normalize(asdict(request))
    if outcome["kind"] == "failure":
        return _failure(outcome)
    values = cast(dict[str, str], outcome["normalized_input"])
    return NormalizedRentPlusInvestmentInput(
        comparison_opening_cash=BRLMoney(values["comparison_opening_cash"]),
        starting_monthly_rent=BRLMoney(values["starting_monthly_rent"]),
        initial_invested_capital=BRLMoney(values["initial_invested_capital"]),
        monthly_contribution=BRLMoney(values["monthly_contribution"]),
        effective_annual_rent_adjustment=Decimal(values["effective_annual_rent_adjustment"]),
        effective_monthly_net_return=EffectiveMonthlyRate(DeclaredRate(
            values["effective_monthly_net_return"], "effective_monthly",
        )),
        first_rent_adjustment_month=cast(int, cast(dict[str, object], outcome["normalized_input"])["first_rent_adjustment_month"]),
    )


def calculate_rent_plus_investment(
    input_value: NormalizedRentPlusInvestmentInput,
) -> RentPlusInvestmentResult | DomainFailure:
    """Decode retained postings without changing legacy cash failure timing."""
    normalized: dict[str, object] = {
        "comparison_opening_cash": input_value.comparison_opening_cash.as_string,
        "starting_monthly_rent": input_value.starting_monthly_rent.as_string,
        "initial_invested_capital": input_value.initial_invested_capital.as_string,
        "monthly_contribution": input_value.monthly_contribution.as_string,
        "effective_annual_rent_adjustment": str(input_value.effective_annual_rent_adjustment),
        "effective_monthly_net_return": str(input_value.effective_monthly_net_return.amount),
        "first_rent_adjustment_month": input_value.first_rent_adjustment_month,
    }
    outcome = _retained.calculate(normalized)
    if outcome["kind"] == "failure":
        return _failure(outcome)
    trace = cast(dict[str, list[dict[str, object]]], outcome["trace"])
    postings = tuple(RentPlusInvestmentMonthlyRow(
        month=cast(int, row["month"]),
        opening_liquid_financial_assets=BRLMoney(cast(str, row["opening_liquid_financial_assets"])),
        investment_return=BRLMoney(cast(str, row["investment_return"])),
        rent=BRLMoney(cast(str, row["rent"])),
        monthly_contribution=BRLMoney(cast(str, row["monthly_contribution"])),
        closing_liquid_financial_assets=BRLMoney(cast(str, row["closing_liquid_financial_assets"])),
    ) for row in trace["monthly_postings"])
    ledger = tuple(ComparisonLedgerRow(
        month=cast(int, row["month"]),
        **{name: BRLMoney(cast(str, value)) for name, value in row.items() if name != "month"},
    ) for row in trace["comparison_ledger"])
    return RentPlusInvestmentResult(postings, ledger)
