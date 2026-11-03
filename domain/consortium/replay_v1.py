"""Retained authority for consortium-explicit-schedule-v1.

Only the standard library is imported. Codec, validation and ledger semantics
are version-owned so later live helpers cannot reinterpret historical results.
All supplied amounts are already posted centavos: integer addition/subtraction
is exact and introduces no intermediate Decimal context or rounding step.
"""

from __future__ import annotations

import json
import re
from typing import cast


CONTRACT_SCHEMA_VERSION = "consortium-replay-v1"
ENGINE_VERSION = "consortium-explicit-schedule-v1"
RULESET_VERSION = "consortium-ruleset-v1"
MAX_TERM_MONTHS = 600
COMPARISON_MONTHS = 60
_COMPONENTS = ("credit_component", "administration_fee", "reserve_fund", "insurance")
_MONEY_FIELDS = ("comparison_opening_cash", "credit_letter", "property_price", "cash_top_up")
_DECLARATIONS = {
    "correction": ("documented_zero", "requested_nonzero"),
    "reserve_fund_treatment": ("nonrecoverable_no_refund", "refundable"),
    "installment_schedule_treatment": (
        "fixed_independent_of_contemplation", "changes_on_contemplation",
    ),
}
_REQUIRED = frozenset({
    *_MONEY_FIELDS, *_DECLARATIONS, "term_months", "monthly_schedule",
    "credit_components_apply_to_credit_letter", "scenario_kind", "contemplation_month",
    "property_purchase_event", "waiting_housing_costs",
})
_RULE_FEATURES = frozenset({"tax", "fgts", "subsidy", "eligibility"})
_MONEY = re.compile(r"[+-]?[0-9]+\.[0-9]{2}\Z")
_FEATURE = re.compile(r"[a-z][a-z0-9_]*\Z")


class _Rejected(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


def canonical_json(value: object) -> str:
    """Encode the closed JCS domain: strings, safe integers, booleans and null."""
    if value is None or type(value) is bool:
        return json.dumps(value)
    if type(value) is int and abs(value) <= 9_007_199_254_740_991:
        return str(value)
    if isinstance(value, str):
        value.encode("utf-8")  # Reject unpaired surrogates.
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(canonical_json(item) for item in cast(list[object], value)) + "]"
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        if not all(isinstance(key, str) for key in mapping):
            raise ValueError("canonical object keys must be strings")
        typed = cast(dict[str, object], mapping)
        keys = sorted(typed, key=lambda key: key.encode("utf-16-be"))
        return "{" + ",".join(canonical_json(key) + ":" + canonical_json(typed[key]) for key in keys) + "}"
    raise ValueError("value is outside the closed JCS domain")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object key")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ValueError("nonfinite JSON value")


def parse_canonical_object(text: object) -> dict[str, object]:
    """Reject malformed, non-object, duplicate or noncanonical evidence."""
    if not isinstance(text, str):
        raise ValueError("canonical evidence must be text")
    value: object = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    if not isinstance(value, dict):
        raise ValueError("evidence must be a canonical object")
    object_value = cast(dict[str, object], value)
    if canonical_json(object_value) != text:
        raise ValueError("evidence must be a canonical object")
    return object_value


def _invalid() -> None:
    raise _Rejected("invalid_input", "consortium input structure, units or bounds are invalid")


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        _invalid()
    return cast(dict[str, object], value)


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        _invalid()
    return cast(list[object], value)


def _integer(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _invalid()
    return cast(int, value)


def _cents(value: object) -> int:
    if not isinstance(value, str) or not _MONEY.fullmatch(value):
        _invalid()
    text = cast(str, value)
    digits = text.lstrip("+-").replace(".", "")
    amount = 0
    # Small chunks avoid dependence on sys.int_max_str_digits. No monetary
    # length bound is part of this contract, in either parsing or emission.
    for offset in range(0, len(digits), 9):
        chunk = digits[offset:offset + 9]
        amount = amount * (10 ** len(chunk)) + int(chunk)
    if text.startswith("-") and amount:
        _invalid()
    return amount


def _digits(amount: int) -> str:
    chunks: list[int] = []
    while amount >= 1_000_000_000:
        amount, remainder = divmod(amount, 1_000_000_000)
        chunks.append(remainder)
    return str(amount) + "".join(f"{chunk:09d}" for chunk in reversed(chunks))


def _money(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}{_digits(abs(amount) // 100)}.{abs(amount) % 100:02d}"


def _normalize(request: dict[str, object]) -> dict[str, object]:
    # Known structure is checked before support declarations or reconciliation.
    if not _REQUIRED <= request.keys():
        _invalid()
    term = _integer(request["term_months"], 1, MAX_TERM_MONTHS)
    contemplation = _integer(request["contemplation_month"], 1, term)
    amounts = {name: _cents(request[name]) for name in _MONEY_FIELDS}
    if amounts["credit_letter"] == 0:
        _invalid()
    for name in ("credit_components_apply_to_credit_letter", "property_purchase_event"):
        if type(request[name]) is not bool:
            _invalid()
    if request["scenario_kind"] not in ("early", "intermediate", "late"):
        _invalid()
    for name, choices in _DECLARATIONS.items():
        if request[name] not in choices:
            _invalid()

    unknown = bool(request.keys() - (_REQUIRED | {"requested_features"}))
    schedule = _list(request["monthly_schedule"])
    if len(schedule) != term:
        _invalid()
    normalized_schedule: list[dict[str, object]] = []
    credit_total = 0
    for month, value in enumerate(schedule, 1):
        row = _object(value)
        required = {"month", *_COMPONENTS}
        if not required <= row.keys() or _integer(row["month"], 1, term) != month:
            _invalid()
        components = {name: _cents(row[name]) for name in _COMPONENTS}
        credit_total += components["credit_component"]
        unknown |= bool(row.keys() - required)
        normalized_schedule.append({"month": month, **{name: _money(value) for name, value in components.items()}})

    waiting = _list(request["waiting_housing_costs"])
    if len(waiting) != min(contemplation, COMPARISON_MONTHS):
        _invalid()
    normalized_waiting: list[dict[str, object]] = []
    for month, value in enumerate(waiting, 1):
        row = _object(value)
        if not {"month", "amount"} <= row.keys() or _integer(row["month"], 1, COMPARISON_MONTHS) != month:
            _invalid()
        amount = _cents(row["amount"])
        unknown |= bool(row.keys() - {"month", "amount"})
        normalized_waiting.append({"month": month, "amount": _money(amount)})

    features = _list(request.get("requested_features", []))
    for feature in features:
        if not isinstance(feature, str) or not _FEATURE.fullmatch(feature):
            _invalid()
    if any(feature in _RULE_FEATURES for feature in cast(list[str], features)):
        raise _Rejected("unsupported_rule", "requested consortium rule is not supported")
    if (
        unknown or features
        or request["credit_components_apply_to_credit_letter"] is False
        or request["property_purchase_event"] is False
        or any(request[name] != choices[0] for name, choices in _DECLARATIONS.items())
    ):
        raise _Rejected("unsupported_contract_clause", "consortium clause has no admitted treatment")
    if credit_total != amounts["credit_letter"] or amounts["property_price"] != amounts["credit_letter"] + amounts["cash_top_up"]:
        raise _Rejected("invalid_input", "consortium schedule or purchase amounts do not reconcile")

    classification = {
        name: (
            "observed_data" if name == "comparison_opening_cash" else
            "projected_assumption" if name in {
                "scenario_kind", "contemplation_month", "property_purchase_event",
                "property_price", "cash_top_up", "waiting_housing_costs",
            } else "contractual_data"
        ) for name in _REQUIRED
    }
    classification["requested_features"] = "rule_request"
    return {
        **request, **{name: _money(value) for name, value in amounts.items()},
        "monthly_schedule": normalized_schedule, "waiting_housing_costs": normalized_waiting,
        "requested_features": [], "input_classification": classification,
        "reference_basis": "synthetic_contract_reference",
        "rule_conventions": {
            "currency": "BRL", "value_basis": "nominal", "rounding": "ROUND_HALF_UP",
            "comparison_months": COMPARISON_MONTHS, "period": "one_based_month",
            "ruleset_version": RULESET_VERSION,
        },
    }


def _trace(normalized: dict[str, object]) -> dict[str, object]:
    schedule: list[dict[str, object]] = []
    for value in _list(normalized["monthly_schedule"]):
        row = _object(value)
        payment = sum(_cents(row[name]) for name in _COMPONENTS)
        schedule.append({**row, "payment": _money(payment)})
    waiting = [_cents(_object(row)["amount"]) for row in _list(normalized["waiting_housing_costs"])]
    contemplation = cast(int, normalized["contemplation_month"])
    letter = _cents(normalized["credit_letter"])
    price = _cents(normalized["property_price"])
    top_up = _cents(normalized["cash_top_up"])
    cash = _cents(normalized["comparison_opening_cash"])
    right = obligation = property_value = cumulative = 0
    ledger: list[dict[str, object]] = []
    postings: list[dict[str, object]] = []
    for month in range(COMPARISON_MONTHS + 1):
        row = schedule[month - 1] if 0 < month <= len(schedule) else None
        credit = _cents(row["credit_component"]) if row is not None else 0
        payment = _cents(row["payment"]) if row is not None else 0
        housing = waiting[month - 1] if 0 < month <= len(waiting) else 0
        purchase_top_up = top_up if month == contemplation else 0
        cost = payment - credit + housing
        outflow = payment + housing + purchase_top_up
        cash -= outflow
        if cash < 0:
            raise _Rejected("infeasible_scenario", "cash is insufficient within the comparison horizon")
        cumulative += cost
        transferred = applied = 0
        if 0 < month <= contemplation:
            right += credit
        elif month > contemplation:
            obligation -= credit
        if month == contemplation:
            transferred, applied = right, letter
            obligation, right, property_value = letter - right, 0, price
        ledger.append({
            "month": month, "cash": _money(cash), "liquid_financial_assets": "0.00",
            "consortium_credit_right_balance": _money(right), "property_value": _money(property_value),
            "financing_principal_balance": "0.00", "consortium_credit_obligation_balance": _money(obligation),
            "recoverable_transfer": _money(credit + purchase_top_up), "nonrecoverable_housing_cost": _money(cost),
            "total_liabilities": _money(obligation), "home_equity": _money(property_value - obligation),
            "liquidity": _money(cash), "net_worth": _money(cash + right + property_value - obligation),
            "cumulative_housing_cost": _money(cumulative),
        })
        if month:
            postings.append({
                "month": month, "contractual_payment": _money(payment),
                "waiting_housing_cost": _money(housing), "cash_top_up": _money(purchase_top_up),
                "cash_outflow": _money(outflow), "transferred_credit_right": _money(transferred),
                "credit_letter_applied": _money(applied),
            })
    return {"contractual_schedule": schedule, "monthly_postings": postings, "comparison_ledger": ledger}


def evaluate(raw_request_jcs: str) -> str:
    """Seal a canonical domain success or failure; malformed evidence raises."""
    request = parse_canonical_object(raw_request_jcs)
    try:
        normalized = _normalize(request)
        trace = _trace(normalized)
    except _Rejected as failure:
        return canonical_json({"kind": "failure", "code": failure.code, "detail": failure.detail})
    return canonical_json({"kind": "success", "normalized_input": normalized, "trace": trace})
