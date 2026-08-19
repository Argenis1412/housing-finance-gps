"""Versioned financing evaluator for the admitted fixed monthly fee."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
import re
from typing import Literal

from domain.financing import replay_v1


CONTRACT_SCHEMA_VERSION = "financing-replay-v2"
ENGINE_VERSION = "financing-fixed-principal-v2"
RULESET_VERSION = "financing-ruleset-v1"
MAX_TERM_MONTHS = replay_v1.MAX_TERM_MONTHS
COMPARISON_MONTHS = replay_v1.COMPARISON_MONTHS
Strategy = Literal["sac", "price"]
_MONEY_PATTERN = re.compile(r"[+-]?\d+\.\d{2}\Z")
_REQUIRED_FIELDS = frozenset(
    {
        "comparison_opening_cash",
        "property_price",
        "cash_down_payment",
        "principal",
        "term_months",
        "rate_value",
        "rate_convention",
        "fgts_amount",
        "subsidy_amount",
        "tax_amount",
        "transaction_cost_amount",
        "fee_amount",
        "insurance_amount",
        "indexation",
        "extraordinary_amortization_amount",
    }
)
_ZERO = Decimal("0.00")


def canonical_json(value: object) -> str:
    """Render the closed v2 JSON domain in canonical form."""
    return replay_v1.canonical_json(value)


def parse_canonical_object(text: object) -> dict[str, object]:
    """Parse only a duplicate-free canonical JSON object for v2."""
    if not isinstance(text, str):
        raise ValueError("canonical JSON must be a string")
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("canonical JSON is invalid") from error
    if not isinstance(value, dict) or canonical_json(value) != text:
        raise ValueError("JSON is not canonical")
    return value


def evaluate(raw_request_jcs: str, strategy: Strategy) -> str:
    """Evaluate one v2 request and return its canonical outcome."""
    request = parse_canonical_object(raw_request_jcs)
    if set(request) != _REQUIRED_FIELDS:
        raise ValueError("v2 raw request fields are incomplete")
    fee = _fee(request["fee_amount"])
    if isinstance(fee, str):
        return fee
    fee_free = dict(request)
    fee_free["fee_amount"] = "0.00"
    base = json.loads(replay_v1.evaluate(canonical_json(fee_free), strategy).outcome_jcs)
    if base.get("kind") != "success":
        return canonical_json(base)
    trace = base["trace"]
    schedule = trace["contractual_schedule"]
    ledger = trace["comparison_ledger"]
    for row in schedule:
        row["fee"] = fee.as_string
        row["payment"] = _post(Decimal(row["payment"]) + fee.amount)
    for row in ledger:
        month = row["month"]
        if isinstance(month, int) and 1 <= month <= len(schedule):
            cost = Decimal(row["nonrecoverable_housing_cost"]) + fee.amount
            row["cash"] = _post(Decimal(row["cash"]) - fee.amount)
            row["nonrecoverable_housing_cost"] = _post(cost)
            row["cumulative_housing_cost"] = _post(Decimal(row["cumulative_housing_cost"]) + fee.amount)
            row["liquidity"] = row["cash"]
            row["net_worth"] = _post(Decimal(row["net_worth"]) - fee.amount)
    normalized = dict(base["normalized_input"])
    normalized["fee_amount"] = fee.as_string
    return canonical_json({"kind": "success", "normalized_input": normalized, "trace": trace})


def validate_outcome(outcome_jcs: object) -> None:
    """Validate the complete version-specific v2 outcome shape."""
    outcome = parse_canonical_object(outcome_jcs)
    if outcome.get("kind") == "failure":
        if set(outcome) != {"code", "detail", "kind"} or not all(isinstance(outcome[name], str) for name in ("code", "detail")):
            raise ValueError("sealed failure is invalid")
        return
    if outcome.get("kind") != "success" or set(outcome) != {"kind", "normalized_input", "trace"}:
        raise ValueError("sealed success is invalid")
    normalized = outcome["normalized_input"]
    trace = outcome["trace"]
    if not isinstance(normalized, dict) or set(normalized) != {"cash_down_payment", "comparison_opening_cash", "effective_monthly_rate", "fee_amount", "principal", "property_price", "term_months"}:
        raise ValueError("sealed normalized input is invalid")
    if not isinstance(trace, dict) or set(trace) != {"comparison_ledger", "contractual_schedule"}:
        raise ValueError("sealed trace is invalid")
    schedule = trace["contractual_schedule"]
    ledger = trace["comparison_ledger"]
    if not isinstance(schedule, list) or not isinstance(ledger, list):
        raise ValueError("sealed trace rows are invalid")
    for row in schedule:
        if not isinstance(row, dict) or set(row) != {"amortization", "closing_principal_balance", "fee", "interest", "month", "opening_principal_balance", "payment"}:
            raise ValueError("sealed schedule row is invalid")
    ledger_keys = {"cash", "consortium_credit_obligation_balance", "consortium_credit_right_balance", "cumulative_housing_cost", "financing_principal_balance", "home_equity", "liquid_financial_assets", "liquidity", "month", "net_worth", "nonrecoverable_housing_cost", "property_value", "recoverable_transfer", "total_liabilities"}
    for row in ledger:
        if not isinstance(row, dict) or set(row) != ledger_keys:
            raise ValueError("sealed ledger row is invalid")


def _fee(raw_value: object) -> object:
    if raw_value is None:
        return _Money(_ZERO)
    if not isinstance(raw_value, str) or not _MONEY_PATTERN.fullmatch(raw_value):
        return _failure("invalid_input", "fee_amount must be an exact-two-fraction BRL string")
    try:
        amount = Decimal(raw_value)
    except InvalidOperation:
        return _failure("invalid_input", "fee_amount must be an exact-two-fraction BRL string")
    if amount < _ZERO:
        return _failure("invalid_input", "fee_amount cannot be negative")
    return _Money(amount)


class _Money:
    def __init__(self, amount: Decimal) -> None:
        self.amount = amount

    @property
    def as_string(self) -> str:
        return format(self.amount, ".2f")


def _post(amount: Decimal) -> str:
    fraction = Fraction(amount)
    sign = -1 if fraction < 0 else 1
    fraction = abs(fraction) * 100
    cents = (2 * fraction.numerator + fraction.denominator) // (2 * fraction.denominator)
    return format(Decimal(f"{sign * cents}e-2"), ".2f")


def _failure(code: str, detail: str) -> str:
    return canonical_json({"code": code, "detail": detail, "kind": "failure"})


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"JSON constant {value} is not permitted")
