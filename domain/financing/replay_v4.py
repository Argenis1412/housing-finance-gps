"""Retained monthly-funded financing; contractual settlement is pinned to v3."""

from __future__ import annotations

from decimal import Context, localcontext
from typing import cast

from domain import monthly_resources_v1 as _resources
from domain.consortium import replay_v1 as _codec
from domain.financing import replay_v3 as _contract


CONTRACT_SCHEMA_VERSION = "financing-replay-v4"
ENGINE_VERSION = "financing-monthly-resources-v4"
RULESET_VERSION = "financing-ruleset-v3"


def evaluate(raw_request_jcs: str, strategy: _contract.Strategy) -> str:
    request = _codec.parse_canonical_object(raw_request_jcs)
    try:
        raw, profile = _resources.unwrap(request, strategy)
        with localcontext(Context(prec=28)):
            normalized = _contract._normalize(raw)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
            if isinstance(normalized, _contract._Failure):  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
                return _codec.canonical_json(
                    {
                        "kind": "failure",
                        "code": normalized.code,
                        "detail": normalized.detail,
                    }
                )
            schedule = _contract._schedule(normalized, strategy)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
            values = _contract._normalized_projection(normalized)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
        for name in (
            "comparison_opening_cash",
            "property_price",
            "cash_down_payment",
            "principal",
            "fee_amount",
        ):
            values[name] = _resources.money(_resources.cents(values[name]))
        trace = _trace(values, schedule, profile)
    except _resources.Rejected as error:
        return _codec.canonical_json(_resources.failure(error))
    return _codec.canonical_json(
        {
            "kind": "success",
            "normalized_input": {
                "strategy_input": values,
                "monthly_resources": profile,
            },
            "trace": trace,
        }
    )


def _trace(
    values: dict[str, object],
    schedule: list[dict[str, object]],
    profile: dict[str, object],
) -> dict[str, object]:
    down = _resources.cents(values["cash_down_payment"])
    cash = _resources.spend(
        _resources.cents(values["comparison_opening_cash"]),
        down,
        0,
        "opening_allocation",
    )
    price, principal = (
        _resources.cents(values[name]) for name in ("property_price", "principal")
    )
    ledger = [
        _resources.ledger_row(
            0, cash, property_value=price, finance=principal, transfer=down
        )
    ]
    postings: list[dict[str, object]] = []
    cumulative = 0
    for month, resource in enumerate(
        cast(list[dict[str, object]], profile["months"]), 1
    ):
        cash, posting = _resources.resource_posting(cash, resource)
        payment = balance = amortization = cost = 0
        if month <= len(schedule):
            row = schedule[month - 1]
            payment, balance, amortization = (
                _resources.cents(row[name])
                for name in ("payment", "closing_principal_balance", "amortization")
            )
            cost = _resources.cents(row["interest"]) + _resources.cents(row["fee"])
        cash = _resources.spend(cash, payment, month, "strategy_obligations")
        cumulative += cost
        postings.append({**posting, "closing_cash": _resources.money(cash)})
        ledger.append(
            _resources.ledger_row(
                month,
                cash,
                property_value=price,
                finance=balance,
                transfer=amortization,
                cost=cost,
                cumulative=cumulative,
            )
        )
    return {
        "contractual_schedule": schedule,
        "resource_postings": postings,
        "comparison_ledger": ledger,
    }
