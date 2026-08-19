"""Self-contained historical evaluator for ``financing-fixed-principal-v1``.

This module deliberately imports only the Python standard library.  It is the
single authority that emits and replays v1 financing envelopes; later live
financial modules must not change its semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
import re
from typing import Literal


CONTRACT_SCHEMA_VERSION = "financing-replay-v1"
ENGINE_VERSION = "financing-fixed-principal-v1"
RULESET_VERSION = "financing-ruleset-v1"
MAX_TERM_MONTHS = 600
COMPARISON_MONTHS = 60

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
_OPTIONAL_MONEY_FIELDS = (
    "fgts_amount",
    "subsidy_amount",
    "tax_amount",
    "transaction_cost_amount",
    "fee_amount",
    "insurance_amount",
    "extraordinary_amortization_amount",
)
_ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class V1Evaluation:
    """Canonical sealed result produced by the retained v1 evaluator."""

    outcome_jcs: str


@dataclass(frozen=True, slots=True)
class _Failure:
    code: str
    detail: str


def canonical_json(value: object) -> str:
    """Render the closed v1 JSON domain in RFC 8785-compatible form."""
    _reject_non_jcs_values(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def parse_canonical_object(text: object) -> dict[str, object]:
    """Accept only a duplicate-free canonical JSON object."""
    if not isinstance(text, str):
        raise ValueError("canonical JSON must be a string")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_object_pairs,
            parse_constant=_reject_json_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("canonical JSON is invalid") from error
    if not isinstance(value, dict) or canonical_json(value) != text:
        raise ValueError("JSON is not canonical")
    return value


def evaluate(raw_request_jcs: str, strategy: Strategy) -> V1Evaluation:
    """Evaluate one v1 request and return its single canonical outcome."""
    request_or_failure = _parse_request(raw_request_jcs)
    if isinstance(request_or_failure, _Failure):
        return V1Evaluation(_failure_outcome(request_or_failure))
    normalized_or_failure = _normalize(request_or_failure)
    if isinstance(normalized_or_failure, _Failure):
        return V1Evaluation(_failure_outcome(normalized_or_failure))
    trace = _trace(normalized_or_failure, strategy)
    outcome = {
        "kind": "success",
        "normalized_input": _normalized_projection(normalized_or_failure),
        "trace": trace,
    }
    return V1Evaluation(canonical_json(outcome))


def validate_outcome(outcome_jcs: object) -> None:
    """Validate the closed sealed-outcome shape without accepting alternatives."""
    outcome = parse_canonical_object(outcome_jcs)
    kind = outcome.get("kind")
    if kind == "failure":
        if set(outcome) != {"code", "detail", "kind"} or not isinstance(outcome["code"], str) or not isinstance(outcome["detail"], str):
            raise ValueError("sealed failure is invalid")
        return
    if kind == "success":
        if set(outcome) != {"kind", "normalized_input", "trace"}:
            raise ValueError("sealed success is invalid")
        if not isinstance(outcome["normalized_input"], dict) or not isinstance(outcome["trace"], dict):
            raise ValueError("sealed success is invalid")
        return
    raise ValueError("sealed outcome kind is invalid")


def _parse_request(raw_request_jcs: str) -> dict[str, object] | _Failure:
    request = parse_canonical_object(raw_request_jcs)
    if set(request) != _REQUIRED_FIELDS:
        raise ValueError("v1 raw request fields are incomplete")
    for name in ("comparison_opening_cash", "property_price", "cash_down_payment", "principal", "rate_value", "rate_convention", "indexation"):
        if not isinstance(request[name], str):
            raise ValueError("v1 raw request field types are invalid")
    for name in _OPTIONAL_MONEY_FIELDS:
        if request[name] is not None and not isinstance(request[name], str):
            raise ValueError("v1 raw request field types are invalid")
    term = request["term_months"]
    if type(term) is not int or term > 9_007_199_254_740_991:
        raise ValueError("v1 term_months is not a JCS-safe positive integer")
    if term < 1:
        return _invalid("term_months must be a positive integer")
    if term > MAX_TERM_MONTHS:
        return _Failure("invalid_input", f"term_months exceeds v1 maximum of {MAX_TERM_MONTHS}")
    return request


def _normalize(request: dict[str, object]) -> dict[str, object] | _Failure:
    money_values: dict[str, Decimal] = {}
    for name in ("comparison_opening_cash", "property_price", "cash_down_payment", "principal"):
        value = _money(name, request[name])
        if isinstance(value, _Failure):
            return value
        money_values[name] = value

    exclusion = _classify_exclusions(request)
    if exclusion is not None:
        return exclusion
    rate = _rate(request["rate_value"], request["rate_convention"])
    if isinstance(rate, _Failure):
        return rate
    if money_values["property_price"] <= _ZERO:
        return _invalid("property_price must be positive")
    if money_values["principal"] <= _ZERO:
        return _invalid("principal must be positive")
    if money_values["cash_down_payment"] < _ZERO:
        return _invalid("cash_down_payment cannot be negative")
    if money_values["property_price"] != money_values["cash_down_payment"] + money_values["principal"]:
        return _invalid("property_price must equal cash_down_payment plus principal")
    return {**money_values, "term_months": request["term_months"], "effective_monthly_rate": rate}


def _classify_exclusions(request: dict[str, object]) -> _Failure | None:
    for name in ("fgts_amount", "subsidy_amount", "tax_amount"):
        failure = _classify_amount(name, request[name], "unsupported_rule")
        if failure is not None:
            return failure
    for name in ("transaction_cost_amount", "fee_amount", "insurance_amount", "extraordinary_amortization_amount"):
        failure = _classify_amount(name, request[name], "unsupported_contract_clause")
        if failure is not None:
            return failure
    indexation = request["indexation"]
    if indexation in ("not_requested", "documented_zero"):
        return None
    if indexation == "requested_nonzero":
        return _Failure("unsupported_contract_clause", "indexation is not supported")
    return _invalid("indexation declaration is invalid")


def _classify_amount(name: str, raw_value: object, code: str) -> _Failure | None:
    if raw_value is None:
        return None
    value = _money(name, raw_value)
    if isinstance(value, _Failure):
        return value
    if value == _ZERO:
        return None
    return _Failure(code, f"{name} is not supported")


def _money(name: str, raw_value: object) -> Decimal | _Failure:
    if not isinstance(raw_value, str) or not _MONEY_PATTERN.fullmatch(raw_value):
        return _invalid(f"{name} must be an exact-two-fraction BRL string")
    try:
        value = Decimal(raw_value)
    except InvalidOperation:
        return _invalid(f"{name} must be an exact-two-fraction BRL string")
    if not value.is_finite():
        return _invalid(f"{name} must be an exact-two-fraction BRL string")
    return value


def _rate(raw_value: object, convention: object) -> Decimal | _Failure:
    if not isinstance(raw_value, str) or not isinstance(convention, str):
        return _invalid("rate value and convention must be finite decimal and string values")
    try:
        rate = Decimal(raw_value)
    except InvalidOperation:
        return _invalid("rate value and convention must be finite decimal and string values")
    if not rate.is_finite():
        return _invalid("rate value and convention must be finite decimal and string values")
    if convention != "effective_monthly":
        if rate == Decimal("0"):
            return Decimal("0")
        return _Failure("unsupported_rate_convention", "rate convention is not supported")
    if rate < Decimal("0"):
        return _invalid("effective_monthly rate must be non-negative")
    return rate


def _trace(normalized: dict[str, object], strategy: Strategy) -> dict[str, object]:
    schedule = _schedule(normalized, strategy)
    return {"comparison_ledger": _ledger(normalized, schedule), "contractual_schedule": schedule}


def _schedule(normalized: dict[str, object], strategy: Strategy) -> list[dict[str, object]]:
    principal = _decimal(normalized["principal"])
    rate = _decimal(normalized["effective_monthly_rate"])
    term = _integer(normalized["term_months"])
    opening = principal
    rows: list[dict[str, object]] = []
    regular_amortization = _post(Fraction(principal) / term)
    rate_fraction = Fraction(rate)
    regular_payment = _price_payment(Fraction(principal), rate_fraction, term)
    for month in range(1, term + 1):
        interest = _post(Fraction(opening) * rate_fraction)
        if strategy == "sac":
            amortization = opening if month == term else regular_amortization
            payment = _post(Fraction(interest) + Fraction(amortization))
        else:
            if month == term:
                amortization = opening
                payment = _post(Fraction(interest) + Fraction(amortization))
            else:
                payment = regular_payment
                amortization = _post(Fraction(payment) - Fraction(interest))
        closing = _post(Fraction(opening) - Fraction(amortization))
        rows.append(
            {
                "amortization": _money_string(amortization),
                "closing_principal_balance": _money_string(closing),
                "interest": _money_string(interest),
                "month": month,
                "opening_principal_balance": _money_string(opening),
                "payment": _money_string(payment),
            }
        )
        opening = closing
    return rows


def _price_payment(principal: Fraction, rate: Fraction, term: int) -> Decimal:
    if rate == 0:
        return _post(principal / term)
    growth = (Fraction(1) + rate) ** term
    return _post(principal * rate * growth / (growth - 1))


def _ledger(normalized: dict[str, object], schedule: list[dict[str, object]]) -> list[dict[str, object]]:
    opening_cash = _decimal(normalized["comparison_opening_cash"])
    down_payment = _decimal(normalized["cash_down_payment"])
    property_price = _decimal(normalized["property_price"])
    principal = _decimal(normalized["principal"])
    cash = _post(Fraction(opening_cash) - Fraction(down_payment))
    cumulative = _ZERO
    rows = [_ledger_row(0, cash, property_price, principal, down_payment, _ZERO, cumulative)]
    for month in range(1, COMPARISON_MONTHS + 1):
        if month <= len(schedule):
            posting = schedule[month - 1]
            payment = Decimal(_string(posting["payment"]))
            balance = Decimal(_string(posting["closing_principal_balance"]))
            recoverable = Decimal(_string(posting["amortization"]))
            cost = Decimal(_string(posting["interest"]))
            cash = _post(Fraction(cash) - Fraction(payment))
        else:
            balance = _ZERO
            recoverable = _ZERO
            cost = _ZERO
        cumulative = _post(Fraction(cumulative) + Fraction(cost))
        rows.append(_ledger_row(month, cash, property_price, balance, recoverable, cost, cumulative))
    return rows


def _ledger_row(month: int, cash: Decimal, property_value: Decimal, financing_balance: Decimal, recoverable: Decimal, cost: Decimal, cumulative: Decimal) -> dict[str, object]:
    liabilities = _post(Fraction(financing_balance))
    home_equity = _post(Fraction(property_value) - Fraction(liabilities))
    liquidity = _post(Fraction(cash))
    net_worth = _post(Fraction(cash) + Fraction(property_value) - Fraction(liabilities))
    return {
        "cash": _money_string(cash),
        "month": month,
        "consortium_credit_obligation_balance": "0.00",
        "consortium_credit_right_balance": "0.00",
        "cumulative_housing_cost": _money_string(cumulative),
        "financing_principal_balance": _money_string(financing_balance),
        "home_equity": _money_string(home_equity),
        "liquid_financial_assets": "0.00",
        "liquidity": _money_string(liquidity),
        "net_worth": _money_string(net_worth),
        "nonrecoverable_housing_cost": _money_string(cost),
        "property_value": _money_string(property_value),
        "recoverable_transfer": _money_string(recoverable),
        "total_liabilities": _money_string(liabilities),
    }


def _normalized_projection(normalized: dict[str, object]) -> dict[str, object]:
    return {
        "cash_down_payment": _money_string(_decimal(normalized["cash_down_payment"])),
        "comparison_opening_cash": _money_string(_decimal(normalized["comparison_opening_cash"])),
        "effective_monthly_rate": format(_decimal(normalized["effective_monthly_rate"]), "f"),
        "principal": _money_string(_decimal(normalized["principal"])),
        "property_price": _money_string(_decimal(normalized["property_price"])),
        "term_months": _integer(normalized["term_months"]),
    }


def _failure_outcome(failure: _Failure) -> str:
    return canonical_json({"code": failure.code, "detail": failure.detail, "kind": "failure"})


def _post(amount: Fraction) -> Decimal:
    sign = -1 if amount < 0 else 1
    amount = abs(amount)
    cents = amount * 100
    posted = (2 * cents.numerator + cents.denominator) // (2 * cents.denominator)
    return Decimal(f"{sign * posted}e-2")


def _money_string(value: Decimal) -> str:
    return format(_post(Fraction(value)), ".2f")


def _invalid(detail: str) -> _Failure:
    return _Failure("invalid_input", detail)


def _reject_duplicate_object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"invalid JSON constant: {value}")


def _reject_non_jcs_values(value: object) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if type(value) is int:
        if not -9_007_199_254_740_991 <= value <= 9_007_199_254_740_991:
            raise ValueError("JSON integer is outside the JCS-safe range")
        return
    if isinstance(value, list):
        for item in value:
            _reject_non_jcs_values(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object key must be a string")
            _reject_non_jcs_values(item)
        return
    raise ValueError("JSON value is outside the closed JCS domain")


def _decimal(value: object) -> Decimal:
    assert isinstance(value, Decimal)
    return value


def _integer(value: object) -> int:
    assert type(value) is int
    return value


def _string(value: object) -> str:
    assert isinstance(value, str)
    return value
