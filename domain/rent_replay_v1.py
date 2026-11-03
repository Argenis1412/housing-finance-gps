"""Retained rent-plus-fixed-cash-v1 semantics, independent of live helpers.

The codec is pinned to the retained consortium v1 closed JCS implementation.
Normalization and calculation remain separate to preserve legacy failure timing.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re
from typing import NoReturn, cast

from domain.consortium import replay_v1 as _codec


CONTRACT_SCHEMA_VERSION = "rent-plus-replay-v1"
ENGINE_VERSION = "rent-plus-fixed-cash-v1"
RULESET_VERSION = "rent-plus-ruleset-v1"
_MONEY = re.compile(r"[+-]?\d+\.\d{2}\Z")
_MONEY_FIELDS = (
    "comparison_opening_cash", "starting_monthly_rent",
    "initial_invested_capital", "monthly_contribution",
)
_FIELDS = frozenset({
    *_MONEY_FIELDS, "rent_adjustment_rate_value", "rent_adjustment_rate_convention",
    "return_rate_value", "return_rate_convention", "first_rent_adjustment_month",
    "tax_amount", "investment_product", "withdrawal_restriction", "future_purchase",
})


class _Rejected(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _fail(code: str, detail: str) -> NoReturn:
    raise _Rejected(code, detail)


def _money(name: str, raw: object) -> str:
    if not isinstance(raw, str) or not _MONEY.fullmatch(raw):
        _fail("invalid_input", f"{name} must be an exact-two-fraction BRL string")
    return format(Decimal(raw), ".2f")


def _rate(raw: object, convention: object, expected: str, name: str) -> str:
    detail = f"{name} rate value and convention must be finite decimal and string values"
    if not isinstance(raw, str) or not isinstance(convention, str):
        _fail("invalid_input", detail)
    try:
        value = Decimal(raw)
    except InvalidOperation:
        _fail("invalid_input", detail)
    if not value.is_finite():
        _fail("invalid_input", detail)
    if convention != expected:
        _fail("unsupported_rate_convention", f"{name} rate convention is not supported")
    if value < 0:
        _fail("invalid_input", f"{name} rate must be non-negative")
    return str(value)


def _failure(failure: _Rejected) -> dict[str, object]:
    return {"kind": "failure", "code": failure.code, "detail": failure.detail}


def normalize(request: dict[str, object]) -> dict[str, object]:
    """Normalize without running cash feasibility or future rent postings."""
    try:
        values: dict[str, object] = {name: _money(name, request[name]) for name in _MONEY_FIELDS}
        tax = request["tax_amount"]
        if tax is not None and Decimal(_money("tax_amount", tax)) != 0:
            _fail("unsupported_rule", "tax_amount is not supported")
        for name in ("investment_product", "withdrawal_restriction", "future_purchase"):
            if request[name] == "requested":
                _fail("unsupported_contract_clause", f"{name} is not supported")
            if request[name] != "not_requested":
                _fail("invalid_input", f"{name} declaration is invalid")
        values["effective_annual_rent_adjustment"] = _rate(
            request["rent_adjustment_rate_value"], request["rent_adjustment_rate_convention"],
            "effective_annual", "rent adjustment",
        )
        values["effective_monthly_net_return"] = _rate(
            request["return_rate_value"], request["return_rate_convention"],
            "effective_monthly", "return",
        )
        first = request["first_rent_adjustment_month"]
        if type(first) is not int or first <= 1:
            _fail("invalid_input", "first_rent_adjustment_month must be an integer greater than one")
        for name in _MONEY_FIELDS:
            amount = Decimal(cast(str, values[name]))
            if name == "starting_monthly_rent":
                if amount <= 0:
                    _fail("invalid_input", "starting_monthly_rent must be positive")
            elif amount < 0:
                _fail("invalid_input", f"{name} cannot be negative")
        values["first_rent_adjustment_month"] = first
        return {"kind": "success", "normalized_input": values}
    except _Rejected as failure:
        return _failure(failure)


def _post(amount: Fraction) -> str:
    if amount < 0:
        raise ValueError("monetary posting amount cannot be negative")
    cents = amount * 100
    posted = (2 * cents.numerator + cents.denominator) // (2 * cents.denominator)
    return format(Decimal(f"{posted}e-2"), ".2f")


def _next_rent(rent: str, annual: Fraction, first: int, month: int) -> str:
    if month >= first and (month - first) % 12 == 0:
        return _post(Fraction(rent) * (1 + annual))
    return rent


def rent_amounts(starting: str, annual: str, first: int, months: int) -> tuple[str, ...]:
    """Project only the explicitly needed shared waiting months."""
    rent = starting
    adjustment = Fraction(annual)
    rows: list[str] = []
    for month in range(1, months + 1):
        rent = _next_rent(rent, adjustment, first, month)
        rows.append(rent)
    return tuple(rows)


def _ledger(month: int, cash: str, assets: str, transfer: str, rent: str, cost: str) -> dict[str, object]:
    liquidity = _post(Fraction(cash) + Fraction(assets))
    return {
        "month": month, "cash": _post(Fraction(cash)), "liquid_financial_assets": _post(Fraction(assets)),
        "consortium_credit_right_balance": "0.00", "property_value": "0.00",
        "financing_principal_balance": "0.00", "consortium_credit_obligation_balance": "0.00",
        "recoverable_transfer": _post(Fraction(transfer)), "nonrecoverable_housing_cost": rent,
        "total_liabilities": "0.00", "home_equity": "0.00", "liquidity": liquidity,
        "net_worth": liquidity, "cumulative_housing_cost": cost,
    }


def calculate(normalized: dict[str, object]) -> dict[str, object]:
    """Run the legacy posting order, preserving its early cash short-circuit."""
    values = cast(dict[str, str], normalized)
    cash_fraction = Fraction(values["comparison_opening_cash"]) - Fraction(values["initial_invested_capital"])
    if cash_fraction < 0:
        return {"kind": "failure", "code": "infeasible_scenario", "detail": "initial invested capital exceeds available cash"}
    cash = _post(cash_fraction)
    assets = values["initial_invested_capital"]
    contribution = values["monthly_contribution"]
    cumulative = "0.00"
    ledger = [_ledger(0, cash, assets, assets, "0.00", cumulative)]
    postings: list[dict[str, object]] = []
    rent = values["starting_monthly_rent"]
    annual = Fraction(values["effective_annual_rent_adjustment"])
    monthly_return = Fraction(values["effective_monthly_net_return"])
    first = cast(int, normalized["first_rent_adjustment_month"])
    for month in range(1, 61):
        rent = _next_rent(rent, annual, first, month)
        investment_return = _post(Fraction(assets) * monthly_return)
        next_cash = Fraction(cash) - Fraction(rent) - Fraction(contribution)
        if next_cash < 0:
            return {"kind": "failure", "code": "infeasible_scenario", "detail": f"cash is insufficient in month {month}"}
        closing_assets = _post(Fraction(assets) + Fraction(investment_return) + Fraction(contribution))
        cash = _post(next_cash)
        cumulative = _post(Fraction(cumulative) + Fraction(rent))
        postings.append({
            "month": month, "opening_liquid_financial_assets": _post(Fraction(assets)),
            "investment_return": investment_return, "rent": rent,
            "monthly_contribution": contribution, "closing_liquid_financial_assets": closing_assets,
        })
        ledger.append(_ledger(month, cash, closing_assets, contribution, rent, cumulative))
        assets = closing_assets
    return {"kind": "success", "trace": {"monthly_postings": postings, "comparison_ledger": ledger}}


def evaluate(raw_request_jcs: str) -> str:
    """Evaluate closed canonical rent evidence through the retained authority."""
    request = _codec.parse_canonical_object(raw_request_jcs)
    if request.keys() != _FIELDS:
        return _codec.canonical_json({"kind": "failure", "code": "invalid_input", "detail": "rent request fields are incomplete or unknown"})
    outcome = normalize(request)
    if outcome["kind"] == "success":
        normalized = cast(dict[str, object], outcome["normalized_input"])
        outcome = calculate(normalized)
        if outcome["kind"] == "success":
            outcome["normalized_input"] = normalized
    return _codec.canonical_json(outcome)
