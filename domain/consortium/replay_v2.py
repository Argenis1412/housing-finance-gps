"""Retained monthly-funded consortium; supported clauses remain pinned to v1."""

from __future__ import annotations

from typing import cast

from domain import monthly_resources_v1 as _resources
from domain.consortium import replay_v1 as _contract


CONTRACT_SCHEMA_VERSION = "consortium-replay-v2"
ENGINE_VERSION = "consortium-monthly-resources-v2"
RULESET_VERSION = "consortium-ruleset-v2"
_COMPONENTS = ("credit_component", "administration_fee", "reserve_fund", "insurance")


def evaluate(raw_request_jcs: str) -> str:
    request = _contract.parse_canonical_object(raw_request_jcs)
    try:
        raw, profile = _resources.unwrap(request, "consortium")
        normalized = _contract._normalize(raw)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
        normalized["rule_conventions"] = {
            **cast(dict[str, object], normalized["rule_conventions"]),
            "ruleset_version": RULESET_VERSION,
        }
        trace = _trace(normalized, profile)
    except (_resources.Rejected, _contract._Rejected) as error:  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
        return _contract.canonical_json(
            {"kind": "failure", "code": error.code, "detail": error.detail}
        )
    return _contract.canonical_json(
        {
            "kind": "success",
            "normalized_input": {
                "strategy_input": normalized,
                "monthly_resources": profile,
            },
            "trace": trace,
        }
    )


def _trace(
    normalized: dict[str, object], profile: dict[str, object]
) -> dict[str, object]:
    schedule = [
        {
            **row,
            "payment": _resources.money(
                sum(_resources.cents(row[name]) for name in _COMPONENTS)
            ),
        }
        for row in cast(list[dict[str, object]], normalized["monthly_schedule"])
    ]
    waiting = [
        _resources.cents(row["amount"])
        for row in cast(list[dict[str, object]], normalized["waiting_housing_costs"])
    ]
    contemplation = cast(int, normalized["contemplation_month"])
    letter, price, top_up, cash = (
        _resources.cents(normalized[name])
        for name in (
            "credit_letter",
            "property_price",
            "cash_top_up",
            "comparison_opening_cash",
        )
    )
    right = obligation = property_value = cumulative = 0
    ledger = [_resources.ledger_row(0, cash)]
    postings: list[dict[str, object]] = []
    resources: list[dict[str, object]] = []
    for month, resource in enumerate(
        cast(list[dict[str, object]], profile["months"]), 1
    ):
        cash, posting = _resources.resource_posting(cash, resource)
        row = schedule[month - 1] if month <= len(schedule) else None
        credit = _resources.cents(row["credit_component"]) if row is not None else 0
        payment = _resources.cents(row["payment"]) if row is not None else 0
        housing = waiting[month - 1] if month <= len(waiting) else 0
        purchase_top_up = top_up if month == contemplation else 0
        cost = payment - credit + housing
        outflow = payment + housing + purchase_top_up
        cash = _resources.spend(cash, outflow, month, "strategy_obligations")
        cumulative += cost
        transferred = applied = 0
        if month <= contemplation:
            right += credit
        else:
            obligation -= credit
        if month == contemplation:
            transferred, applied = right, letter
            obligation, right, property_value = letter - right, 0, price
        ledger.append(
            _resources.ledger_row(
                month,
                cash,
                right=right,
                property_value=property_value,
                obligation=obligation,
                transfer=credit + purchase_top_up,
                cost=cost,
                cumulative=cumulative,
            )
        )
        resources.append({**posting, "closing_cash": _resources.money(cash)})
        postings.append(
            {
                "month": month,
                "contractual_payment": _resources.money(payment),
                "waiting_housing_cost": _resources.money(housing),
                "cash_top_up": _resources.money(purchase_top_up),
                "cash_outflow": _resources.money(outflow),
                "transferred_credit_right": _resources.money(transferred),
                "credit_letter_applied": _resources.money(applied),
            }
        )
    return {
        "contractual_schedule": schedule,
        "monthly_postings": postings,
        "resource_postings": resources,
        "comparison_ledger": ledger,
    }
