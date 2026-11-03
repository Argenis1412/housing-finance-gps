"""Retained rent investment with explicit monthly resources and mandatory transfers."""

from __future__ import annotations

from decimal import Context, localcontext
from fractions import Fraction
from typing import cast

from domain import monthly_resources_v1 as _resources
from domain import rent_replay_v1 as _contract
from domain.consortium import replay_v1 as _codec


CONTRACT_SCHEMA_VERSION = "rent-plus-replay-v2"
ENGINE_VERSION = "rent-plus-monthly-resources-v2"
RULESET_VERSION = "rent-plus-ruleset-v2"


def evaluate(raw_request_jcs: str) -> str:
    request = _codec.parse_canonical_object(raw_request_jcs)
    try:
        raw, profile = _resources.unwrap(request, "rent")
        with localcontext(Context(prec=28)):
            admission = _contract.normalize(raw)
        if admission["kind"] == "failure":
            return _codec.canonical_json(admission)
        values = cast(dict[str, object], admission["normalized_input"])
        for name in (
            "comparison_opening_cash",
            "starting_monthly_rent",
            "initial_invested_capital",
            "monthly_contribution",
        ):
            values[name] = _resources.money(_resources.cents(values[name]))
        trace = _trace(values, profile)
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


def _trace(values: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
    assets = _resources.cents(values["initial_invested_capital"])
    cash = _resources.spend(
        _resources.cents(values["comparison_opening_cash"]),
        assets,
        0,
        "opening_allocation",
    )
    contribution = _resources.cents(values["monthly_contribution"])
    rent = _resources.money(_resources.cents(values["starting_monthly_rent"]))
    annual = Fraction(cast(str, values["effective_annual_rent_adjustment"]))
    monthly_return = Fraction(cast(str, values["effective_monthly_net_return"]))
    first = cast(int, values["first_rent_adjustment_month"])
    ledger = [_resources.ledger_row(0, cash, assets=assets, transfer=assets)]
    resources: list[dict[str, object]] = []
    postings: list[dict[str, object]] = []
    cumulative = 0
    for month, resource in enumerate(
        cast(list[dict[str, object]], profile["months"]), 1
    ):
        rent = _contract._next_rent(rent, annual, first, month)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
        investment_return = _resources.cents(
            _contract._post(Fraction(_resources.money(assets)) * monthly_return)  # pyright: ignore[reportPrivateUsage]  # Pinned posting.
        )
        cash, posting = _resources.resource_posting(cash, resource)
        cash = _resources.spend(
            cash, _resources.cents(rent), month, "strategy_obligations"
        )
        cash = _resources.spend(cash, contribution, month, "investment_contribution")
        closing_assets = assets + investment_return + contribution
        cumulative += _resources.cents(rent)
        postings.append(
            {
                "month": month,
                "opening_liquid_financial_assets": _resources.money(assets),
                "investment_return": _resources.money(investment_return),
                "rent": rent,
                "monthly_contribution": _resources.money(contribution),
                "closing_liquid_financial_assets": _resources.money(closing_assets),
            }
        )
        resources.append({**posting, "closing_cash": _resources.money(cash)})
        ledger.append(
            _resources.ledger_row(
                month,
                cash,
                assets=closing_assets,
                transfer=contribution,
                cost=_resources.cents(rent),
                cumulative=cumulative,
            )
        )
        assets = closing_assets
    return {
        "monthly_postings": postings,
        "resource_postings": resources,
        "comparison_ledger": ledger,
    }
