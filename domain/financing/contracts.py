"""Shared deterministic contracts for supported financing strategies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
from typing import Literal

from domain.values import BRLMoney, DeclaredRate, DomainFailure, EffectiveMonthlyRate


IndexationDeclaration = Literal["not_requested", "documented_zero", "requested_nonzero"]
_CENT = Decimal("0.01")
_ZERO = Decimal("0.00")
_COMPARISON_MONTHS = 60
_CALCULATION_CONTEXT = Context(prec=50, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class FinancingRequest:
    """Closed request shape shared by the initial SAC and Price slices."""

    comparison_opening_cash: str
    property_price: str
    cash_down_payment: str
    principal: str
    term_months: int
    rate_value: str
    rate_convention: str
    fgts_amount: str | None = None
    subsidy_amount: str | None = None
    tax_amount: str | None = None
    transaction_cost_amount: str | None = None
    fee_amount: str | None = None
    insurance_amount: str | None = None
    indexation: IndexationDeclaration = "not_requested"
    extraordinary_amortization_amount: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedFinancingInput:
    """Validated common financing input accepted by pure calculators."""

    comparison_opening_cash: BRLMoney
    property_price: BRLMoney
    cash_down_payment: BRLMoney
    principal: BRLMoney
    term_months: int
    effective_monthly_rate: EffectiveMonthlyRate


@dataclass(frozen=True, slots=True)
class FinancingContractualRow:
    """One posted financing schedule row shared by SAC and Price."""

    month: int
    opening_principal_balance: BRLMoney
    interest: BRLMoney
    amortization: BRLMoney
    payment: BRLMoney
    closing_principal_balance: BRLMoney


@dataclass(frozen=True, slots=True)
class ComparisonLedgerRow:
    """One closing row in the fixed 60-month financing comparison domain."""

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


def normalize_financing_request(request: FinancingRequest) -> NormalizedFinancingInput | DomainFailure:
    """Normalize the closed financing boundary before a strategy calculates."""
    money_fields = (
        ("comparison_opening_cash", request.comparison_opening_cash),
        ("property_price", request.property_price),
        ("cash_down_payment", request.cash_down_payment),
        ("principal", request.principal),
    )
    normalized_money: dict[str, BRLMoney] = {}
    for name, raw_value in money_fields:
        money_value = _normalize_money(name, raw_value)
        if isinstance(money_value, DomainFailure):
            return money_value
        normalized_money[name] = money_value

    exclusion_failure = _classify_exclusions(request)
    if exclusion_failure is not None:
        return exclusion_failure

    rate = _normalize_rate(request.rate_value, request.rate_convention)
    if isinstance(rate, DomainFailure):
        return rate

    if type(request.term_months) is not int or request.term_months <= 0:
        return _invalid("term_months must be a positive integer")
    if normalized_money["property_price"].amount <= _ZERO:
        return _invalid("property_price must be positive")
    if normalized_money["principal"].amount <= _ZERO:
        return _invalid("principal must be positive")
    if normalized_money["cash_down_payment"].amount < _ZERO:
        return _invalid("cash_down_payment cannot be negative")
    with localcontext(
        context_for_amounts(
            normalized_money["cash_down_payment"].amount,
            normalized_money["principal"].amount,
            extra_digits=2,
        )
    ):
        balance_matches = normalized_money["property_price"].amount == (
            normalized_money["cash_down_payment"].amount + normalized_money["principal"].amount
        )
    if not balance_matches:
        return _invalid("property_price must equal cash_down_payment plus principal")

    return NormalizedFinancingInput(
        comparison_opening_cash=normalized_money["comparison_opening_cash"],
        property_price=normalized_money["property_price"],
        cash_down_payment=normalized_money["cash_down_payment"],
        principal=normalized_money["principal"],
        term_months=request.term_months,
        effective_monthly_rate=rate,
    )


def build_financing_comparison_ledger(
    input_value: NormalizedFinancingInput,
    schedule: tuple[FinancingContractualRow, ...],
) -> tuple[ComparisonLedgerRow, ...]:
    """Build the common financing ledger from already-posted schedule values."""
    rows: list[ComparisonLedgerRow] = []
    cash = post_decimal(input_value.comparison_opening_cash.amount - input_value.cash_down_payment.amount)
    cumulative_cost = _ZERO
    rows.append(
        _ledger_row(
            month=0,
            cash=cash,
            property_value=input_value.property_price.amount,
            financing_balance=input_value.principal.amount,
            recoverable_transfer=input_value.cash_down_payment.amount,
            nonrecoverable_cost=_ZERO,
            cumulative_cost=cumulative_cost,
        )
    )
    for month in range(1, _COMPARISON_MONTHS + 1):
        if month <= len(schedule):
            posting = schedule[month - 1]
            cash = post_decimal(cash - posting.payment.amount)
            financing_balance = posting.closing_principal_balance.amount
            recoverable_transfer = posting.amortization.amount
            nonrecoverable_cost = posting.interest.amount
        else:
            financing_balance = _ZERO
            recoverable_transfer = _ZERO
            nonrecoverable_cost = _ZERO
        cumulative_cost = post_decimal(cumulative_cost + nonrecoverable_cost)
        rows.append(
            _ledger_row(
                month=month,
                cash=cash,
                property_value=input_value.property_price.amount,
                financing_balance=financing_balance,
                recoverable_transfer=recoverable_transfer,
                nonrecoverable_cost=nonrecoverable_cost,
                cumulative_cost=cumulative_cost,
            )
        )
    return tuple(rows)


def post_decimal(amount: Decimal) -> Decimal:
    """Post a finite monetary amount using the accepted centavo rule."""
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)


def calculation_context(input_value: NormalizedFinancingInput) -> Context:
    """Size Decimal arithmetic from a closed normalized financing input."""
    money_digits = max(
        len(value.amount.as_tuple().digits)
        for value in (
            input_value.comparison_opening_cash,
            input_value.property_price,
            input_value.cash_down_payment,
            input_value.principal,
        )
    )
    rate_digits = len(input_value.effective_monthly_rate.amount.as_tuple().digits)
    term_digits = len(str(input_value.term_months))
    context = _CALCULATION_CONTEXT.copy()
    context.prec = max(context.prec, money_digits + rate_digits + term_digits + 8)
    return context


def context_for_amounts(*amounts: Decimal, extra_digits: int = 0) -> Context:
    """Create deterministic precision wide enough for finite Decimal arithmetic."""
    coefficient_digits = max((len(amount.as_tuple().digits) for amount in amounts), default=1)
    context = _CALCULATION_CONTEXT.copy()
    context.prec = max(context.prec, coefficient_digits + extra_digits)
    return context


def money(amount: Decimal) -> BRLMoney:
    """Create a posted BRL value from a calculated amount."""
    return BRLMoney(format(post_decimal(amount), ".2f"))


def _normalize_money(name: str, raw_value: object) -> BRLMoney | DomainFailure:
    try:
        return BRLMoney(raw_value)  # type: ignore[arg-type]
    except ValueError:
        return _invalid(f"{name} must be an exact-two-fraction BRL string")


def _normalize_rate(raw_value: object, convention: object) -> EffectiveMonthlyRate | DomainFailure:
    try:
        declared_rate = DeclaredRate(raw_value, convention)  # type: ignore[arg-type]
    except ValueError:
        return _invalid("rate value and convention must be finite decimal and string values")

    if declared_rate.convention != "effective_monthly":
        if declared_rate.amount == Decimal("0"):
            return EffectiveMonthlyRate.zero()
        return DomainFailure("unsupported_rate_convention", "rate convention is not supported")
    try:
        return EffectiveMonthlyRate(declared_rate)
    except ValueError:
        return _invalid("effective_monthly rate must be non-negative")


def _classify_exclusions(request: FinancingRequest) -> DomainFailure | None:
    rule_fields = (("fgts_amount", request.fgts_amount), ("subsidy_amount", request.subsidy_amount), ("tax_amount", request.tax_amount))
    clause_fields = (("transaction_cost_amount", request.transaction_cost_amount), ("fee_amount", request.fee_amount), ("insurance_amount", request.insurance_amount), ("extraordinary_amortization_amount", request.extraordinary_amortization_amount))
    for name, raw_value in rule_fields:
        failure = _classify_exclusion_amount(name, raw_value, "unsupported_rule")
        if failure is not None:
            return failure
    for name, raw_value in clause_fields:
        failure = _classify_exclusion_amount(name, raw_value, "unsupported_contract_clause")
        if failure is not None:
            return failure
    if request.indexation in ("not_requested", "documented_zero"):
        return None
    if request.indexation == "requested_nonzero":
        return DomainFailure("unsupported_contract_clause", "indexation is not supported")
    return _invalid("indexation declaration is invalid")


def _classify_exclusion_amount(name: str, raw_value: object, failure_code: Literal["unsupported_rule", "unsupported_contract_clause"]) -> DomainFailure | None:
    if raw_value is None:
        return None
    money_value = _normalize_money(name, raw_value)
    if isinstance(money_value, DomainFailure):
        return money_value
    if money_value.amount == _ZERO:
        return None
    return DomainFailure(failure_code, f"{name} is not supported")


def _ledger_row(*, month: int, cash: Decimal, property_value: Decimal, financing_balance: Decimal, recoverable_transfer: Decimal, nonrecoverable_cost: Decimal, cumulative_cost: Decimal) -> ComparisonLedgerRow:
    liquid_assets = _ZERO
    credit_right = _ZERO
    consortium_obligation = _ZERO
    total_liabilities = post_decimal(financing_balance + consortium_obligation)
    home_equity = post_decimal(property_value - total_liabilities)
    liquidity = post_decimal(cash + liquid_assets)
    net_worth = post_decimal(cash + liquid_assets + credit_right + property_value - total_liabilities)
    return ComparisonLedgerRow(month=month, cash=money(cash), liquid_financial_assets=money(liquid_assets), consortium_credit_right_balance=money(credit_right), property_value=money(property_value), financing_principal_balance=money(financing_balance), consortium_credit_obligation_balance=money(consortium_obligation), recoverable_transfer=money(recoverable_transfer), nonrecoverable_housing_cost=money(nonrecoverable_cost), total_liabilities=money(total_liabilities), home_equity=money(home_equity), liquidity=money(liquidity), net_worth=money(net_worth), cumulative_housing_cost=money(cumulative_cost))


def _invalid(detail: str) -> DomainFailure:
    return DomainFailure("invalid_input", detail)
