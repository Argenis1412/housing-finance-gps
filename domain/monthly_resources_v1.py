"""Retained common-resource admission and exact-cent postings for comparison v2.

Source declarations establish a common basis, not factual authenticity. This
module has no clock, service, mutable live calculator or Decimal dependency.
"""

from __future__ import annotations

from datetime import datetime
from fractions import Fraction
import re
from typing import NoReturn, cast


_MONEY = re.compile(r"[+-]?[0-9]{1,18}\.[0-9]{2}\Z")
_RATE = re.compile(r"(?:0|1)(?:\.[0-9]{1,12})?\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_INCOME_BASIS = "net_before_household_expenses"
_EXPENSE_SCOPE = "strategy_independent_excluding_strategy_flows_and_netted_deductions"
_COMPONENT = {
    "component_id",
    "amount",
    "classification",
    "source_reference",
    "source_as_of",
    "assumption_reference",
}
_FINANCE_MONEY = (
    "comparison_opening_cash",
    "property_price",
    "cash_down_payment",
    "principal",
)
_FINANCE_OPTIONAL = (
    "fgts_amount",
    "subsidy_amount",
    "tax_amount",
    "transaction_cost_amount",
    "fee_amount",
    "insurance_amount",
    "extraordinary_amortization_amount",
)
_RENT_MONEY = (
    "comparison_opening_cash",
    "starting_monthly_rent",
    "initial_invested_capital",
    "monthly_contribution",
)
_RENT_TERMS = (
    "rent_adjustment_rate_value",
    "rent_adjustment_rate_convention",
    "first_rent_adjustment_month",
)
_CONSORTIUM_MONEY = (
    "comparison_opening_cash",
    "property_price",
    "credit_letter",
    "cash_top_up",
)
_CONSORTIUM = {
    *_CONSORTIUM_MONEY,
    "term_months",
    "monthly_schedule",
    "credit_components_apply_to_credit_letter",
    "correction",
    "reserve_fund_treatment",
    "installment_schedule_treatment",
    "scenario_kind",
    "contemplation_month",
    "property_purchase_event",
    "waiting_housing_costs",
}


class Rejected(Exception):
    """Known admission or cash failure; unexpected execution errors escape."""

    def __init__(self, code: str, detail: str) -> None:
        self.code, self.detail = code, detail
        super().__init__(detail)


def _invalid() -> NoReturn:
    raise Rejected(
        "invalid_input",
        "monthly resource structure, scope, provenance or amounts are invalid",
    )


def cents(value: object) -> int:
    """Decode an already admitted or calculated exact-cent string."""
    text = cast(str, value)
    whole, fraction = text.lstrip("+-").split(".")
    return (-1 if text.startswith("-") else 1) * (int(whole) * 100 + int(fraction))


def money(value: int) -> str:
    return f"{'-' if value < 0 else ''}{abs(value) // 100}.{abs(value) % 100:02d}"


def _money_input(value: object) -> bool:
    return isinstance(value, str) and _MONEY.fullmatch(value) is not None


def _rate_input(value: object) -> bool:
    return (
        isinstance(value, str)
        and _RATE.fullmatch(value) is not None
        and Fraction(value) <= 1
    )


def _identifier(value: object) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _component(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        _invalid()
    row = cast(dict[str, object], value)
    if row.keys() != _COMPONENT:
        _invalid()
    if not all(_identifier(row[name]) for name in ("component_id", "source_reference")):
        _invalid()
    if not _money_input(row["amount"]) or cents(row["amount"]) < 0:
        _invalid()
    timestamp = row["source_as_of"]
    if not isinstance(timestamp, str) or not _TIME.fullmatch(timestamp):
        _invalid()
    try:
        datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
    except ValueError:
        _invalid()
    if row["classification"] == "projected_assumption":
        if not _identifier(row["assumption_reference"]):
            _invalid()
    elif (
        row["classification"] != "observed_data"
        or row["assumption_reference"] is not None
    ):
        _invalid()
    return {**row, "amount": money(cents(row["amount"]))}


def normalize(value: object) -> dict[str, object]:
    """Validate every month before cash execution; derive rather than accept totals."""
    if not isinstance(value, dict):
        _invalid()
    profile = cast(dict[str, object], value)
    if profile.keys() != {"income_basis", "expense_scope", "months"}:
        _invalid()
    if (
        profile["income_basis"] != _INCOME_BASIS
        or profile["expense_scope"] != _EXPENSE_SCOPE
    ):
        _invalid()
    months = profile["months"]
    if not isinstance(months, list) or len(cast(list[object], months)) != 60:
        _invalid()
    sides: dict[str, str] = {}
    normalized: list[dict[str, object]] = []
    for month, value in enumerate(cast(list[object], months), 1):
        if not isinstance(value, dict):
            _invalid()
        row = cast(dict[str, object], value)
        if (
            row.keys() != {"month", "income_components", "external_expenses"}
            or type(row["month"]) is not int
            or row["month"] != month
        ):
            _invalid()
        output: dict[str, object] = {"month": month}
        seen: set[str] = set()
        totals: list[int] = []
        for side in ("income_components", "external_expenses"):
            entries = row[side]
            if not isinstance(entries, list):
                _invalid()
            components = [_component(entry) for entry in cast(list[object], entries)]
            for component in components:
                identity = cast(str, component["component_id"])
                if identity in seen or sides.get(identity, side) != side:
                    _invalid()
                seen.add(identity)
                sides[identity] = side
            output[side] = components
            totals.append(sum(cents(component["amount"]) for component in components))
        output.update(
            income_total=money(totals[0]),
            external_expense_total=money(totals[1]),
            available_resources=money(totals[0] - totals[1]),
        )
        normalized.append(output)
    return {
        "income_basis": _INCOME_BASIS,
        "expense_scope": _EXPENSE_SCOPE,
        "months": normalized,
    }


def child_input(strategy: str, value: object) -> dict[str, object]:
    """Own the successor's closed numeric boundary before pinned normalization.

    Consortium unknown clauses deliberately reach its retained support rejection.
    """
    if not isinstance(value, dict) or not _admitted(
        strategy, cast(dict[str, object], value)
    ):
        raise Rejected(
            "invalid_input",
            "alternative structure or numeric input is outside comparison admission",
        )
    return cast(dict[str, object], value)


def _admitted(strategy: str, raw: dict[str, object]) -> bool:
    if strategy in ("sac", "price"):
        return (
            raw.keys()
            == {
                *_FINANCE_MONEY,
                *_FINANCE_OPTIONAL,
                "term_months",
                "rate_value",
                "rate_convention",
                "indexation",
            }
            and all(_money_input(raw[name]) for name in _FINANCE_MONEY)
            and all(
                raw[name] is None or _money_input(raw[name])
                for name in _FINANCE_OPTIONAL
            )
            and type(raw["term_months"]) is int
            and 1 <= raw["term_months"] <= 600
            and _rate_input(raw["rate_value"])
            and all(
                isinstance(raw[name], str) for name in ("rate_convention", "indexation")
            )
        )
    if strategy == "rent":
        return (
            raw.keys()
            == {
                *_RENT_MONEY,
                *_RENT_TERMS,
                "return_rate_value",
                "return_rate_convention",
                "tax_amount",
                "investment_product",
                "withdrawal_restriction",
                "future_purchase",
            }
            and all(_money_input(raw[name]) for name in _RENT_MONEY)
            and all(
                _rate_input(raw[name])
                for name in ("rent_adjustment_rate_value", "return_rate_value")
            )
            and all(
                isinstance(raw[name], str)
                for name in (
                    "rent_adjustment_rate_convention",
                    "return_rate_convention",
                    "investment_product",
                    "withdrawal_restriction",
                    "future_purchase",
                )
            )
            and type(raw["first_rent_adjustment_month"]) is int
            and (raw["tax_amount"] is None or _money_input(raw["tax_amount"]))
        )
    if not _CONSORTIUM <= raw.keys() or not all(
        _money_input(raw[name]) for name in _CONSORTIUM_MONEY
    ):
        return False
    if type(raw["term_months"]) is not int or not 1 <= raw["term_months"] <= 600:
        return False
    for name, amounts in (
        (
            "monthly_schedule",
            ("credit_component", "administration_fee", "reserve_fund", "insurance"),
        ),
        ("waiting_housing_costs", ("amount",)),
    ):
        rows = raw[name]
        if not isinstance(rows, list):
            return False
        for entry in cast(list[object], rows):
            if not isinstance(entry, dict):
                return False
            row = cast(dict[str, object], entry)
            if (
                not {"month", *amounts} <= row.keys()
                or type(row["month"]) is not int
                or not all(_money_input(row[field]) for field in amounts)
            ):
                return False
    return True


def unwrap(
    value: dict[str, object], strategy: str
) -> tuple[dict[str, object], dict[str, object]]:
    if value.keys() != {"strategy_input", "monthly_resources"}:
        raise Rejected(
            "invalid_input", "resource-aware child wrapper is incomplete or unknown"
        )
    profile = normalize(value["monthly_resources"])
    return child_input(strategy, value["strategy_input"]), profile


def spend(cash: int, amount: int, month: int, phase: str) -> int:
    closing = cash - amount
    if closing < 0:
        raise Rejected(
            "infeasible_scenario",
            f"cash is insufficient in month {month} during {phase}",
        )
    return closing


def resource_posting(
    cash: int, row: dict[str, object]
) -> tuple[int, dict[str, object]]:
    closing = spend(
        cash,
        -cents(row["available_resources"]),
        cast(int, row["month"]),
        "external_expenses",
    )
    return closing, {
        "month": row["month"],
        "income_total": row["income_total"],
        "external_expense_total": row["external_expense_total"],
        "available_resources": row["available_resources"],
        "opening_cash": money(cash),
        "cash_after_external_expenses": money(closing),
    }


def ledger_row(
    month: int,
    cash: int,
    *,
    assets: int = 0,
    right: int = 0,
    property_value: int = 0,
    finance: int = 0,
    obligation: int = 0,
    transfer: int = 0,
    cost: int = 0,
    cumulative: int = 0,
) -> dict[str, object]:
    liabilities = finance + obligation
    return {
        "month": month,
        "cash": money(cash),
        "liquid_financial_assets": money(assets),
        "consortium_credit_right_balance": money(right),
        "property_value": money(property_value),
        "financing_principal_balance": money(finance),
        "consortium_credit_obligation_balance": money(obligation),
        "recoverable_transfer": money(transfer),
        "nonrecoverable_housing_cost": money(cost),
        "total_liabilities": money(liabilities),
        "home_equity": money(property_value - liabilities),
        "liquidity": money(cash + assets),
        "net_worth": money(cash + assets + right + property_value - liabilities),
        "cumulative_housing_cost": money(cumulative),
    }


def failure(error: Rejected) -> dict[str, object]:
    return {"kind": "failure", "code": error.code, "detail": error.detail}
