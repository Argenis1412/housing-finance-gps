"""Pure, deterministic SAC normalization and schedule generation."""

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
class SACRequest:
    """Closed contractual request shape for the initial supported SAC slice."""

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
class NormalizedSACInput:
    """Validated input accepted by the pure SAC calculator."""

    comparison_opening_cash: BRLMoney
    property_price: BRLMoney
    cash_down_payment: BRLMoney
    principal: BRLMoney
    term_months: int
    effective_monthly_rate: EffectiveMonthlyRate


@dataclass(frozen=True, slots=True)
class SACContractualRow:
    """One contractual SAC posting for a financing month."""

    month: int
    opening_principal_balance: BRLMoney
    interest: BRLMoney
    amortization: BRLMoney
    payment: BRLMoney
    closing_principal_balance: BRLMoney


@dataclass(frozen=True, slots=True)
class ComparisonLedgerRow:
    """One closing row in the fixed 60-month comparison time domain."""

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


@dataclass(frozen=True, slots=True)
class SACResult:
    """Immutable SAC output with separate contractual and comparison domains."""

    contractual_schedule: tuple[SACContractualRow, ...]
    comparison_ledger: tuple[ComparisonLedgerRow, ...]


def normalize_sac_request(request: SACRequest) -> NormalizedSACInput | DomainFailure:
    """Validate a closed SAC request before it reaches the calculator."""
    money_fields = (
        ("comparison_opening_cash", request.comparison_opening_cash),
        ("property_price", request.property_price),
        ("cash_down_payment", request.cash_down_payment),
        ("principal", request.principal),
    )
    normalized_money: dict[str, BRLMoney] = {}
    for name, raw_value in money_fields:
        money = _normalize_money(name, raw_value)
        if isinstance(money, DomainFailure):
            return money
        normalized_money[name] = money

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
    if (
        normalized_money["property_price"].amount
        != normalized_money["cash_down_payment"].amount + normalized_money["principal"].amount
    ):
        return _invalid("property_price must equal cash_down_payment plus principal")

    return NormalizedSACInput(
        comparison_opening_cash=normalized_money["comparison_opening_cash"],
        property_price=normalized_money["property_price"],
        cash_down_payment=normalized_money["cash_down_payment"],
        principal=normalized_money["principal"],
        term_months=request.term_months,
        effective_monthly_rate=rate,
    )


def calculate_sac(input_value: NormalizedSACInput) -> SACResult:
    """Calculate SAC postings and the 60-month comparison ledger purely."""
    with localcontext(_CALCULATION_CONTEXT):
        schedule = _build_contractual_schedule(input_value)
        ledger = _build_comparison_ledger(input_value, schedule)
    return SACResult(contractual_schedule=schedule, comparison_ledger=ledger)


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


def _classify_exclusions(request: SACRequest) -> DomainFailure | None:
    rule_fields = (
        ("fgts_amount", request.fgts_amount),
        ("subsidy_amount", request.subsidy_amount),
        ("tax_amount", request.tax_amount),
    )
    clause_fields = (
        ("transaction_cost_amount", request.transaction_cost_amount),
        ("fee_amount", request.fee_amount),
        ("insurance_amount", request.insurance_amount),
        ("extraordinary_amortization_amount", request.extraordinary_amortization_amount),
    )
    for name, raw_value in rule_fields:
        failure = _classify_exclusion_amount(name, raw_value, "unsupported_rule")
        if failure is not None:
            return failure
    for name, raw_value in clause_fields:
        failure = _classify_exclusion_amount(name, raw_value, "unsupported_contract_clause")
        if failure is not None:
            return failure
    if request.indexation == "not_requested" or request.indexation == "documented_zero":
        return None
    if request.indexation == "requested_nonzero":
        return DomainFailure("unsupported_contract_clause", "indexation is not supported")
    return _invalid("indexation declaration is invalid")


def _classify_exclusion_amount(
    name: str,
    raw_value: object,
    failure_code: Literal["unsupported_rule", "unsupported_contract_clause"],
) -> DomainFailure | None:
    if raw_value is None:
        return None
    money = _normalize_money(name, raw_value)
    if isinstance(money, DomainFailure):
        return money
    if money.amount == _ZERO:
        return None
    return DomainFailure(failure_code, f"{name} is not supported")


def _build_contractual_schedule(input_value: NormalizedSACInput) -> tuple[SACContractualRow, ...]:
    rows: list[SACContractualRow] = []
    opening = input_value.principal.amount
    regular_amortization = _post(input_value.principal.amount / input_value.term_months)
    for month in range(1, input_value.term_months + 1):
        interest = _post(opening * input_value.effective_monthly_rate.amount)
        amortization = opening if month == input_value.term_months else regular_amortization
        payment = _post(interest + amortization)
        closing = _post(opening - amortization)
        rows.append(
            SACContractualRow(
                month=month,
                opening_principal_balance=_money(opening),
                interest=_money(interest),
                amortization=_money(amortization),
                payment=_money(payment),
                closing_principal_balance=_money(closing),
            )
        )
        opening = closing
    return tuple(rows)


def _build_comparison_ledger(
    input_value: NormalizedSACInput,
    schedule: tuple[SACContractualRow, ...],
) -> tuple[ComparisonLedgerRow, ...]:
    rows: list[ComparisonLedgerRow] = []
    cash = _post(input_value.comparison_opening_cash.amount - input_value.cash_down_payment.amount)
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
            cash = _post(cash - posting.payment.amount)
            financing_balance = posting.closing_principal_balance.amount
            recoverable_transfer = posting.amortization.amount
            nonrecoverable_cost = posting.interest.amount
        else:
            financing_balance = _ZERO
            recoverable_transfer = _ZERO
            nonrecoverable_cost = _ZERO
        cumulative_cost = _post(cumulative_cost + nonrecoverable_cost)
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


def _ledger_row(
    *,
    month: int,
    cash: Decimal,
    property_value: Decimal,
    financing_balance: Decimal,
    recoverable_transfer: Decimal,
    nonrecoverable_cost: Decimal,
    cumulative_cost: Decimal,
) -> ComparisonLedgerRow:
    liquid_assets = _ZERO
    credit_right = _ZERO
    consortium_obligation = _ZERO
    total_liabilities = _post(financing_balance + consortium_obligation)
    home_equity = _post(property_value - total_liabilities)
    liquidity = _post(cash + liquid_assets)
    net_worth = _post(cash + liquid_assets + credit_right + property_value - total_liabilities)
    return ComparisonLedgerRow(
        month=month,
        cash=_money(cash),
        liquid_financial_assets=_money(liquid_assets),
        consortium_credit_right_balance=_money(credit_right),
        property_value=_money(property_value),
        financing_principal_balance=_money(financing_balance),
        consortium_credit_obligation_balance=_money(consortium_obligation),
        recoverable_transfer=_money(recoverable_transfer),
        nonrecoverable_housing_cost=_money(nonrecoverable_cost),
        total_liabilities=_money(total_liabilities),
        home_equity=_money(home_equity),
        liquidity=_money(liquidity),
        net_worth=_money(net_worth),
        cumulative_housing_cost=_money(cumulative_cost),
    )


def _post(amount: Decimal) -> Decimal:
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)


def _money(amount: Decimal) -> BRLMoney:
    return BRLMoney(format(_post(amount), ".2f"))


def _invalid(detail: str) -> DomainFailure:
    return DomainFailure("invalid_input", detail)
