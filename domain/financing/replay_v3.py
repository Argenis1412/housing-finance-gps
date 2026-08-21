"""Centavo-safe versioned financing evaluator with fixed monthly fees.

This module is the sole semantic authority for ``financing-centavo-safe-v3``.
It deliberately rebuilds its own normalized request, contractual schedule, and
comparison ledger instead of adapting a retained historical trace.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
import re
from typing import Literal, cast

from domain.financing import replay_v1


CONTRACT_SCHEMA_VERSION = "financing-replay-v3"
ENGINE_VERSION = "financing-centavo-safe-v3"
RULESET_VERSION = "financing-ruleset-v2"
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
_OPTIONAL_MONEY_FIELDS = (
    "fgts_amount",
    "subsidy_amount",
    "tax_amount",
    "transaction_cost_amount",
    "insurance_amount",
    "extraordinary_amortization_amount",
)
_ZERO = Decimal("0.00")
_ONE_CENT = Decimal("0.01")
_MAX_RATE_FRACTION_DIGITS = 12
_FAILURE_CODES = frozenset(
    {
        "invalid_input",
        "unsupported_rate_convention",
        "unsupported_rule",
        "unsupported_contract_clause",
    }
)
_SCHEDULE_KEYS = frozenset(
    {
        "amortization",
        "closing_principal_balance",
        "fee",
        "interest",
        "month",
        "opening_principal_balance",
        "payment",
    }
)
_LEDGER_KEYS = frozenset(
    {
        "cash",
        "consortium_credit_obligation_balance",
        "consortium_credit_right_balance",
        "cumulative_housing_cost",
        "financing_principal_balance",
        "home_equity",
        "liquid_financial_assets",
        "liquidity",
        "month",
        "net_worth",
        "nonrecoverable_housing_cost",
        "property_value",
        "recoverable_transfer",
        "total_liabilities",
    }
)
_NORMALIZED_KEYS = frozenset(
    {
        "cash_down_payment",
        "comparison_opening_cash",
        "effective_monthly_rate",
        "fee_amount",
        "principal",
        "property_price",
        "term_months",
    }
)

@dataclass(frozen=True, slots=True)
class _Failure:
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class _Money:
    amount: Decimal

    @property
    def as_string(self) -> str:
        return format(self.amount, ".2f")


def canonical_json(value: object) -> str:
    """Render the closed v3 JSON domain in RFC 8785-compatible form."""
    return replay_v1.canonical_json(value)


def parse_canonical_object(text: object) -> dict[str, object]:
    """Accept only a duplicate-free canonical JSON object."""
    if not isinstance(text, str):
        raise ValueError("canonical JSON must be a string")
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("canonical JSON is invalid") from error
    if not isinstance(value, dict):
        raise ValueError("JSON is not canonical")
    object_value = cast(dict[str, object], value)
    if canonical_json(object_value) != text:
        raise ValueError("JSON is not canonical")
    return object_value


def evaluate(raw_request_jcs: str, strategy: Strategy) -> str:
    """Evaluate one v3 request and return its canonical sealed outcome."""
    request_or_failure = _parse_request(raw_request_jcs)
    if isinstance(request_or_failure, _Failure):
        return _failure_outcome(request_or_failure)
    normalized_or_failure = _normalize(request_or_failure)
    if isinstance(normalized_or_failure, _Failure):
        return _failure_outcome(normalized_or_failure)
    schedule = _schedule(normalized_or_failure, strategy)
    trace = {
        "comparison_ledger": _ledger(normalized_or_failure, schedule),
        "contractual_schedule": schedule,
    }
    return canonical_json(
        {
            "kind": "success",
            "normalized_input": _normalized_projection(normalized_or_failure),
            "trace": trace,
        }
    )


def validate_outcome(outcome_jcs: object) -> None:
    """Validate the complete canonical v3 sealed-outcome shape."""
    outcome = parse_canonical_object(outcome_jcs)
    kind = outcome.get("kind")
    if kind == "failure":
        if (
            set(outcome) != {"code", "detail", "kind"}
            or outcome.get("code") not in _FAILURE_CODES
            or not isinstance(outcome.get("detail"), str)
        ):
            raise ValueError("sealed failure is invalid")
        return
    if kind != "success" or set(outcome) != {"kind", "normalized_input", "trace"}:
        raise ValueError("sealed success is invalid")

    normalized = _object(outcome["normalized_input"], "sealed normalized input is invalid")
    if set(normalized) != set(_NORMALIZED_KEYS):
        raise ValueError("sealed normalized input is invalid")
    term = normalized.get("term_months")
    if type(term) is not int or not 1 <= term <= MAX_TERM_MONTHS:
        raise ValueError("sealed normalized input is invalid")
    for name in (
        "cash_down_payment",
        "comparison_opening_cash",
        "fee_amount",
        "principal",
        "property_price",
    ):
        _validated_money_string(normalized.get(name))
    rate = normalized.get("effective_monthly_rate")
    normalized_rate = _rate(rate, "effective_monthly")
    if (
        not isinstance(rate, str)
        or isinstance(normalized_rate, _Failure)
        or format(normalized_rate, "f") != rate
    ):
        raise ValueError("sealed normalized input is invalid")

    trace = _object(outcome["trace"], "sealed trace is invalid")
    if set(trace) != {"comparison_ledger", "contractual_schedule"}:
        raise ValueError("sealed trace is invalid")
    schedule = _list(trace["contractual_schedule"], "sealed schedule is invalid")
    ledger = _list(trace["comparison_ledger"], "sealed ledger is invalid")
    if len(schedule) != term or len(ledger) != COMPARISON_MONTHS + 1:
        raise ValueError("sealed trace length is invalid")

    fee = _validated_money_string(normalized["fee_amount"])
    for month, row_value in enumerate(schedule, start=1):
        row = _object(row_value, "sealed schedule row is invalid")
        if (
            set(row) != set(_SCHEDULE_KEYS)
            or type(row.get("month")) is not int
            or row.get("month") != month
        ):
            raise ValueError("sealed schedule row is invalid")
        amounts = {
            name: _validated_money_string(row.get(name))
            for name in _SCHEDULE_KEYS
            if name != "month"
        }
        if amounts["fee"] != fee or any(amount < _ZERO for amount in amounts.values()):
            raise ValueError("sealed schedule row is invalid")

    for month, row_value in enumerate(ledger):
        row = _object(row_value, "sealed ledger row is invalid")
        if (
            set(row) != set(_LEDGER_KEYS)
            or type(row.get("month")) is not int
            or row.get("month") != month
        ):
            raise ValueError("sealed ledger row is invalid")
        amounts = {
            name: _validated_money_string(row.get(name))
            for name in _LEDGER_KEYS
            if name != "month"
        }
        if (
            amounts["financing_principal_balance"] < _ZERO
            or amounts["total_liabilities"] < _ZERO
            or amounts["consortium_credit_obligation_balance"] < _ZERO
        ):
            raise ValueError("sealed ledger row is invalid")


def _parse_request(raw_request_jcs: str) -> dict[str, object] | _Failure:
    request = parse_canonical_object(raw_request_jcs)
    if frozenset(request) != _REQUIRED_FIELDS:
        raise ValueError("v3 raw request fields are incomplete")
    for name in (
        "comparison_opening_cash",
        "property_price",
        "cash_down_payment",
        "principal",
        "rate_value",
        "rate_convention",
        "indexation",
    ):
        if not isinstance(request[name], str):
            raise ValueError("v3 raw request field types are invalid")
    for name in (*_OPTIONAL_MONEY_FIELDS, "fee_amount"):
        if request[name] is not None and not isinstance(request[name], str):
            raise ValueError("v3 raw request field types are invalid")
    term = request["term_months"]
    if type(term) is not int or term > 9_007_199_254_740_991:
        raise ValueError("v3 term_months is not a JCS-safe positive integer")
    if term < 1:
        return _invalid("term_months must be a positive integer")
    if term > MAX_TERM_MONTHS:
        return _Failure("invalid_input", f"term_months exceeds v3 maximum of {MAX_TERM_MONTHS}")
    return request


def _normalize(request: dict[str, object]) -> dict[str, object] | _Failure:
    money_values: dict[str, Decimal] = {}
    for name in ("comparison_opening_cash", "property_price", "cash_down_payment", "principal"):
        value = _money(name, request[name])
        if isinstance(value, _Failure):
            return value
        money_values[name] = value
    exclusion = _classify_non_fee_exclusions(request)
    if exclusion is not None:
        return exclusion
    fee = _fee(request["fee_amount"])
    if isinstance(fee, _Failure):
        return fee
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
    return {
        **money_values,
        "effective_monthly_rate": rate,
        "fee_amount": fee.amount,
        "term_months": request["term_months"],
    }


def _classify_non_fee_exclusions(request: dict[str, object]) -> _Failure | None:
    for name in ("fgts_amount", "subsidy_amount", "tax_amount"):
        failure = _classify_amount(name, request[name], "unsupported_rule")
        if failure is not None:
            return failure
    for name in _OPTIONAL_MONEY_FIELDS[3:]:
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


def _fee(raw_value: object) -> _Money | _Failure:
    if raw_value is None:
        return _Money(_ZERO)
    value = _money("fee_amount", raw_value)
    if isinstance(value, _Failure):
        return value
    if value < _ZERO:
        return _invalid("fee_amount cannot be negative")
    return _Money(_ZERO if value.is_zero() else value)


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
        return _Failure("unsupported_rate_convention", "rate convention is not supported")
    exponent = rate.as_tuple().exponent
    if not isinstance(exponent, int) or max(0, -exponent) > _MAX_RATE_FRACTION_DIGITS:
        return _invalid("effective_monthly rate has too many fractional digits")
    if rate < Decimal("0"):
        return _invalid("effective_monthly rate must be non-negative")
    return rate.normalize()


def _schedule(normalized: dict[str, object], strategy: Strategy) -> list[dict[str, object]]:
    principal = _decimal(normalized["principal"])
    rate = _decimal(normalized["effective_monthly_rate"])
    fee = _decimal(normalized["fee_amount"])
    term = _integer(normalized["term_months"])
    opening = principal
    regular_sac_amortization = _post(Fraction(principal) / term)
    rate_fraction = Fraction(rate)
    regular_price_payment = _price_payment(Fraction(principal), rate_fraction, term)
    rows: list[dict[str, object]] = []
    for month in range(1, term + 1):
        interest = _post(Fraction(opening) * rate_fraction)
        if month == term:
            amortization = opening
        else:
            if strategy == "sac":
                regular_amortization = regular_sac_amortization
            else:
                regular_amortization = _post(Fraction(regular_price_payment) - Fraction(interest))
            if regular_amortization < _ZERO:
                raise ValueError("v3 regular amortization cannot be negative")
            amortization = min(regular_amortization, max(opening - _ONE_CENT, _ZERO))
        payment = _post(Fraction(interest) + Fraction(amortization) + Fraction(fee))
        closing = _post(Fraction(opening) - Fraction(amortization))
        rows.append(
            {
                "amortization": _money_string(amortization),
                "closing_principal_balance": _money_string(closing),
                "fee": _money_string(fee),
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
            posting = _object(schedule[month - 1], "v3 schedule row is invalid")
            payment = _validated_money_string(posting["payment"])
            balance = _validated_money_string(posting["closing_principal_balance"])
            recoverable = _validated_money_string(posting["amortization"])
            cost = _post(
                Fraction(_validated_money_string(posting["interest"]))
                + Fraction(_validated_money_string(posting["fee"]))
            )
            cash = _post(Fraction(cash) - Fraction(payment))
        else:
            balance = _ZERO
            recoverable = _ZERO
            cost = _ZERO
        cumulative = _post(Fraction(cumulative) + Fraction(cost))
        rows.append(_ledger_row(month, cash, property_price, balance, recoverable, cost, cumulative))
    return rows


def _ledger_row(
    month: int,
    cash: Decimal,
    property_value: Decimal,
    financing_balance: Decimal,
    recoverable: Decimal,
    cost: Decimal,
    cumulative: Decimal,
) -> dict[str, object]:
    liabilities = _post(Fraction(financing_balance))
    home_equity = _post(Fraction(property_value) - Fraction(liabilities))
    liquidity = _post(Fraction(cash))
    net_worth = _post(Fraction(cash) + Fraction(property_value) - Fraction(liabilities))
    return {
        "cash": _money_string(cash),
        "consortium_credit_obligation_balance": "0.00",
        "consortium_credit_right_balance": "0.00",
        "cumulative_housing_cost": _money_string(cumulative),
        "financing_principal_balance": _money_string(financing_balance),
        "home_equity": _money_string(home_equity),
        "liquid_financial_assets": "0.00",
        "liquidity": _money_string(liquidity),
        "month": month,
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
        "fee_amount": _money_string(_decimal(normalized["fee_amount"])),
        "principal": _money_string(_decimal(normalized["principal"])),
        "property_price": _money_string(_decimal(normalized["property_price"])),
        "term_months": _integer(normalized["term_months"]),
    }


def _failure_outcome(failure: _Failure) -> str:
    return canonical_json({"code": failure.code, "detail": failure.detail, "kind": "failure"})


def _post(amount: Fraction) -> Decimal:
    sign = -1 if amount < 0 else 1
    cents = abs(amount) * 100
    posted = (2 * cents.numerator + cents.denominator) // (2 * cents.denominator)
    return Decimal(f"{sign * posted}e-2")


def _money_string(value: Decimal) -> str:
    return format(_post(Fraction(value)), ".2f")


def _validated_money_string(value: object) -> Decimal:
    parsed = _money("sealed monetary value", value)
    if isinstance(parsed, _Failure) or not isinstance(value, str) or format(parsed, ".2f") != value:
        raise ValueError("sealed monetary value is invalid")
    return parsed


def _object(value: object, detail: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(detail)
    return cast(dict[str, object], value)


def _list(value: object, detail: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(detail)
    return cast(list[object], value)


def _invalid(detail: str) -> _Failure:
    return _Failure("invalid_input", detail)


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"JSON constant {value} is not permitted")


def _decimal(value: object) -> Decimal:
    assert isinstance(value, Decimal)
    return value


def _integer(value: object) -> int:
    assert type(value) is int
    return value
