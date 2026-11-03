"""Retained minimum comparison authority over explicitly retained child engines."""

from __future__ import annotations

from datetime import datetime
from decimal import Context, Decimal, localcontext
from fractions import Fraction
import re
from typing import NoReturn, cast

from domain.consortium import replay_v1 as _consortium
from domain.financing import replay_v3 as _financing
from domain import rent_replay_v1 as _rent


CONTRACT_SCHEMA_VERSION = "comparison-simulation-v1"
ENGINE_VERSION = "comparison-minimum-v1"
RULESET_VERSION = "comparison-ruleset-v1"
_ORDER = ("sac", "price", "rent", "consortium")
_MONEY = re.compile(r"[+-]?[0-9]{1,18}\.[0-9]{2}\Z")
_RATE = re.compile(r"(?:0|1)(?:\.[0-9]{1,12})?\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_SHARED_MONEY = ("comparison_opening_cash", "property_price", "starting_monthly_rent")
_RENT_TERMS = ("starting_monthly_rent", "rent_adjustment_rate_value", "rent_adjustment_rate_convention", "first_rent_adjustment_month")
_SHARED = frozenset({*_SHARED_MONEY, *_RENT_TERMS})
_FINANCE_MONEY = ("comparison_opening_cash", "property_price", "cash_down_payment", "principal")
_FINANCE_OPTIONAL = ("fgts_amount", "subsidy_amount", "tax_amount", "transaction_cost_amount", "fee_amount", "insurance_amount", "extraordinary_amortization_amount")
_FINANCE = frozenset({*_FINANCE_MONEY, *_FINANCE_OPTIONAL, "term_months", "rate_value", "rate_convention", "indexation"})
_RENT_MONEY = ("comparison_opening_cash", "starting_monthly_rent", "initial_invested_capital", "monthly_contribution")
_RENT = frozenset({*_RENT_MONEY, *_RENT_TERMS, "return_rate_value", "return_rate_convention", "tax_amount", "investment_product", "withdrawal_restriction", "future_purchase"})
_CONSORTIUM_MONEY = ("comparison_opening_cash", "property_price", "credit_letter", "cash_top_up")
_CONSORTIUM = frozenset({
    *_CONSORTIUM_MONEY, "term_months", "monthly_schedule", "credit_components_apply_to_credit_letter",
    "correction", "reserve_fund_treatment", "installment_schedule_treatment", "scenario_kind",
    "contemplation_month", "property_purchase_event", "waiting_housing_costs",
})
_CONSTRAINTS = frozenset({"minimum_liquidity", "maximum_monthly_housing_outflow"})
_LIMITATIONS = (
    "synthetic_closed_initial_cash_without_monthly_resources",
    "only_rent_invests_and_receives_returns",
    "cash_is_not_reinvested_in_financing_or_consortium",
    "no_post_horizon_cash_feasibility_claim",
    "no_universal_winner_or_private_case_validation",
    "snapshot_is_supplied_lineage_not_authentication",
)


class _Rejected(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _reject(detail: str) -> NoReturn:
    raise _Rejected("invalid_input", detail)


def validate_metadata(value: object) -> dict[str, object]:
    """Metadata is bound to both canonical request and sealed outcome."""
    if not isinstance(value, dict):
        raise ValueError("comparison metadata is invalid")
    metadata = cast(dict[str, object], value)
    if metadata.keys() != {"data_snapshot_id", "calculated_at", "timezone"}:
        raise ValueError("comparison metadata is invalid")
    snapshot = metadata["data_snapshot_id"]
    timestamp = metadata["calculated_at"]
    if not isinstance(snapshot, str) or not _IDENTIFIER.fullmatch(snapshot):
        raise ValueError("comparison snapshot identifier is invalid")
    if not isinstance(timestamp, str) or not _TIMESTAMP.fullmatch(timestamp):
        raise ValueError("comparison timestamp must be canonical UTC")
    datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
    if metadata["timezone"] != "America/Sao_Paulo":
        raise ValueError("comparison timezone metadata is invalid")
    return metadata


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        _reject("comparison object structure is invalid")
    return cast(dict[str, object], value)


def _money_input(value: object) -> bool:
    return isinstance(value, str) and _MONEY.fullmatch(value) is not None


def _rate_input(value: object) -> bool:
    return isinstance(value, str) and _RATE.fullmatch(value) is not None and Fraction(value) <= 1


def _cents(value: object) -> int:
    text = cast(str, value)
    sign = -1 if text.startswith("-") else 1
    whole, fraction = text.lstrip("+-").split(".")
    return sign * (int(whole) * 100 + int(fraction))


def _money(value: int) -> str:
    return f'{"-" if value < 0 else ""}{abs(value) // 100}.{abs(value) % 100:02d}'


def _shared(request: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    if request.keys() != {"shared", "constraints", "financing", "rent", "consortium"}:
        _reject("comparison request fields are incomplete or unknown")
    shared = _object(request["shared"])
    constraints = _object(request["constraints"])
    if shared.keys() != _SHARED or constraints.keys() != _CONSTRAINTS:
        _reject("shared comparison fields are incomplete or unknown")
    if any(not _money_input(shared[name]) for name in _SHARED_MONEY):
        _reject("shared monetary input is outside comparison admission")
    if _cents(shared["comparison_opening_cash"]) < 0 or any(_cents(shared[name]) <= 0 for name in _SHARED_MONEY[1:]):
        _reject("shared cash or housing amounts are invalid")
    if not _rate_input(shared["rent_adjustment_rate_value"]):
        _reject("shared rent rate is outside comparison admission")
    if shared["rent_adjustment_rate_convention"] != "effective_annual":
        raise _Rejected("unsupported_rate_convention", "shared rent convention is not supported")
    first = shared["first_rent_adjustment_month"]
    if type(first) is not int or first <= 1:
        _reject("shared first rent adjustment month is invalid")
    if any(not _money_input(value) or _cents(value) < 0 for value in constraints.values()):
        _reject("comparison constraints must be nonnegative admitted BRL")
    return shared, constraints


def _mismatches(request: dict[str, object], shared: dict[str, object]) -> None:
    for key in ("financing", "rent", "consortium"):
        child = request[key]
        if not isinstance(child, dict):
            continue
        raw = cast(dict[str, object], child)
        fields = ("comparison_opening_cash", *_RENT_TERMS) if key == "rent" else ("comparison_opening_cash", "property_price")
        for name in fields:
            value = raw.get(name)
            if name in _SHARED_MONEY:
                mismatch = _money_input(value) and _cents(value) != _cents(shared[name])
            elif name == "rent_adjustment_rate_value":
                mismatch = _rate_input(value) and Fraction(cast(str, value)) != Fraction(cast(str, shared[name]))
            elif name == "first_rent_adjustment_month":
                mismatch = type(value) is int and value != shared[name]
            else:
                mismatch = isinstance(value, str) and value != shared[name]
            if mismatch:
                _reject("alternative shared input does not match comparison basis")
    consortium = request["consortium"]
    if not isinstance(consortium, dict):
        return
    raw = cast(dict[str, object], consortium)
    contemplation = raw.get("contemplation_month")
    waiting = raw.get("waiting_housing_costs")
    if type(contemplation) is not int or not 1 <= contemplation <= 600 or not isinstance(waiting, list):
        return
    rents = _rent.rent_amounts(
        cast(str, shared["starting_monthly_rent"]), cast(str, shared["rent_adjustment_rate_value"]),
        cast(int, shared["first_rent_adjustment_month"]), min(contemplation, 60),
    )
    for position, row in enumerate(cast(list[object], waiting), 1):
        if isinstance(row, dict) and position <= len(rents):
            entry = cast(dict[str, object], row)
            if type(entry.get("month")) is int and entry["month"] == position and _money_input(entry.get("amount")):
                if _cents(entry["amount"]) != _cents(rents[position - 1]):
                    _reject("consortium waiting cost does not match shared rent")


def _admitted(strategy: str, raw: dict[str, object]) -> bool:
    """Structural/numeric preflight before calling a retained evaluator."""
    if strategy in ("sac", "price"):
        if raw.keys() != _FINANCE:
            return False
        if not all(_money_input(raw[name]) for name in _FINANCE_MONEY):
            return False
        if not all(raw[name] is None or _money_input(raw[name]) for name in _FINANCE_OPTIONAL):
            return False
        return (
            type(raw["term_months"]) is int and 1 <= raw["term_months"] <= 600
            and _rate_input(raw["rate_value"])
            and isinstance(raw["rate_convention"], str) and isinstance(raw["indexation"], str)
        )
    if strategy == "rent":
        if raw.keys() != _RENT or not all(_money_input(raw[name]) for name in _RENT_MONEY):
            return False
        return (
            all(_rate_input(raw[name]) for name in ("rent_adjustment_rate_value", "return_rate_value"))
            and all(isinstance(raw[name], str) for name in ("rent_adjustment_rate_convention", "return_rate_convention", "investment_product", "withdrawal_restriction", "future_purchase"))
            and type(raw["first_rent_adjustment_month"]) is int
            and (raw["tax_amount"] is None or _money_input(raw["tax_amount"]))
        )
    if not _CONSORTIUM <= raw.keys() or not all(_money_input(raw[name]) for name in _CONSORTIUM_MONEY):
        return False
    if type(raw["term_months"]) is not int or not 1 <= raw["term_months"] <= 600:
        return False
    for name, amounts in (
        ("monthly_schedule", ("credit_component", "administration_fee", "reserve_fund", "insurance")),
        ("waiting_housing_costs", ("amount",)),
    ):
        rows = raw[name]
        if not isinstance(rows, list):
            return False
        for entry in cast(list[object], rows):
            if not isinstance(entry, dict):
                return False
            row = cast(dict[str, object], entry)
            if not {"month", *amounts} <= row.keys() or type(row["month"]) is not int:
                return False
            if not all(_money_input(row[field]) for field in amounts):
                return False
    return True


def _versions(strategy: str) -> dict[str, object]:
    engine = _financing if strategy in ("sac", "price") else _rent if strategy == "rent" else _consortium
    return {
        "contract_schema_version": engine.CONTRACT_SCHEMA_VERSION,
        "engine_version": engine.ENGINE_VERSION, "ruleset_version": engine.RULESET_VERSION,
    }


def _classification(strategy: str, raw: dict[str, object]) -> dict[str, object]:
    observed = {"comparison_opening_cash", "cash_down_payment", "starting_monthly_rent"}
    projected = {"initial_invested_capital", "monthly_contribution", *_RENT_TERMS[1:], "return_rate_value", "return_rate_convention", "scenario_kind", "contemplation_month", "property_purchase_event", "cash_top_up", "waiting_housing_costs"}
    rules = {"requested_features", "fgts_amount", "subsidy_amount", "tax_amount", "investment_product", "withdrawal_restriction", "future_purchase"}
    return {
        key: "observed_data" if key in observed else
        "projected_assumption" if key in projected or (key == "property_price" and strategy == "consortium") else
        "rule_request" if key in rules else "contractual_data"
        for key in raw
    }


def _evaluate_child(strategy: str, value: object) -> tuple[dict[str, object], dict[str, object]]:
    raw_jcs = _consortium.canonical_json(value)
    evidence: dict[str, object] = {"strategy": strategy, "versions": _versions(strategy), "raw_request_jcs": raw_jcs}
    if not isinstance(value, dict) or not _admitted(strategy, cast(dict[str, object], value)):
        failure: dict[str, object] = {"kind": "failure", "code": "invalid_input", "detail": "alternative structure or numeric input is outside comparison admission"}
        evidence["admission_failure"] = failure
        return failure, evidence
    raw = cast(dict[str, object], value)
    evidence["input_classification"] = _classification(strategy, raw)
    # No broad ValueError catch: post-preflight engine errors are not financial
    # failures. Creation propagates them; replay fails closed at its boundary.
    # The new bounded boundary supplies an explicit context rather than inheriting
    # a caller's precision/traps. Existing retained child modules stay unchanged.
    # 28 digits cover exact input relationship sums within the 18-digit envelope.
    with localcontext(Context(prec=28)):
        sealed = _financing.evaluate(raw_jcs, strategy) if strategy in ("sac", "price") else _rent.evaluate(raw_jcs) if strategy == "rent" else _consortium.evaluate(raw_jcs)
    evidence["sealed_outcome_jcs"] = sealed
    return _consortium.parse_canonical_object(sealed), evidence


def _measure(strategy: str, outcome: dict[str, object], constraints: dict[str, object]) -> dict[str, object]:
    trace = cast(dict[str, list[dict[str, object]]], outcome["trace"])
    ledger = trace["comparison_ledger"]
    if strategy in ("sac", "price"):
        payments = {cast(int, row["month"]): _cents(row["payment"]) for row in trace["contractual_schedule"]}
        outflows = [payments.get(month, 0) for month in range(1, 61)]
    else:
        field = "rent" if strategy == "rent" else "cash_outflow"
        outflows = [_cents(row[field]) for row in trace["monthly_postings"]]
    liquidity = [_cents(row["liquidity"]) for row in ledger]
    minimum = min(liquidity)
    maximum = max(outflows)
    violations: list[dict[str, object]] = []
    floor = _cents(constraints["minimum_liquidity"])
    cap = _cents(constraints["maximum_monthly_housing_outflow"])
    for name, actuals, threshold, start, lower in (
        ("cash_nonnegative", [_cents(row["cash"]) for row in ledger], 0, 0, True),
        ("minimum_liquidity", liquidity, floor, 0, True),
        ("maximum_monthly_housing_outflow", outflows, cap, 1, False),
    ):
        for month, actual in enumerate(actuals, start):
            violated = actual < threshold if lower else actual > threshold
            if violated:
                violations.append({"constraint": name, "month": month, "actual": _money(actual), "threshold": _money(threshold)})
    return {
        "strategy": strategy, "status": "constraint_infeasible" if violations else "eligible",
        "metrics": {
            "final_ledger_row": ledger[-1], "minimum_liquidity": _money(minimum),
            "minimum_liquidity_months": [month for month, amount in enumerate(liquidity) if amount == minimum],
            "maximum_monthly_housing_outflow": _money(maximum),
            "maximum_monthly_housing_outflow_months": [month for month, amount in enumerate(outflows, 1) if amount == maximum],
        },
        "comparison_ledger": ledger, "violations": violations,
        "monthly_housing_outflows": [_money(amount) for amount in outflows],
    }


def evaluate(raw_request_jcs: str) -> str:
    """Seal a complete comparison; canonical semantic global failures replay."""
    bound = _consortium.parse_canonical_object(raw_request_jcs)
    if bound.keys() != {"metadata", "comparison"}:
        raise ValueError("comparison evidence structure is invalid")
    metadata = validate_metadata(bound["metadata"])
    try:
        request = _object(bound["comparison"])
        shared, constraints = _shared(request)
        _mismatches(request, shared)
    except _Rejected as failure:
        return _consortium.canonical_json({"kind": "failure", "code": failure.code, "detail": failure.detail, "metadata": metadata})
    alternatives: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    scores: dict[int, list[str]] = {}
    for strategy in _ORDER:
        outcome, child_evidence = _evaluate_child(strategy, request["financing" if strategy in ("sac", "price") else strategy])
        evidence.append(child_evidence)
        if outcome["kind"] == "failure":
            alternatives.append({"strategy": strategy, "status": "domain_failure", "failure": outcome})
            continue
        alternative = _measure(strategy, outcome, constraints)
        alternatives.append(alternative)
        if alternative["status"] == "eligible":
            metrics = cast(dict[str, object], alternative["metrics"])
            final = cast(dict[str, object], metrics["final_ledger_row"])
            scores.setdefault(_cents(final["net_worth"]), []).append(strategy)
    groups = [scores[score] for score in sorted(scores, reverse=True)]
    eligible_count = sum(len(group) for group in groups)
    normalized_shared: dict[str, object] = {
        **shared, **{name: _money(_cents(shared[name])) for name in _SHARED_MONEY},
        "rent_adjustment_rate_value": format(Decimal(cast(str, shared["rent_adjustment_rate_value"])), "f"),
    }
    return _consortium.canonical_json({
        "kind": "success", "metadata": metadata,
        "normalized_input": {
            "shared": normalized_shared,
            "constraints": {name: _money(_cents(value)) for name, value in constraints.items()},
            "rule_conventions": {
                "currency": "BRL", "value_basis": "nominal", "rounding": "ROUND_HALF_UP",
                "comparison_horizon_months": 60, "inflation": "documented_zero",
                "property_appreciation": "documented_zero", "transaction_costs": "documented_zero",
                "reference_basis": "synthetic_contract_reference",
            },
            "input_classification": {
                "shared": {**_classification("rent", shared), "property_price": "projected_assumption"},
                "constraints": {name: "user_constraint" for name in constraints},
            },
        },
        "alternatives": alternatives,
        "result": {
            "status": "no_eligible" if not eligible_count else "single_eligible" if eligible_count == 1 else "compared",
            "objective": "maximize_net_worth_at_month_60", "ranking_groups": groups,
        },
        "trace": {"child_evidence": evidence, "limitations": list(_LIMITATIONS)},
    })
