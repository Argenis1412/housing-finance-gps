"""Profile admission protects origin, scope, composition and exact centavos."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from typing import cast

import pytest

from domain import monthly_resources_v1 as resources
from domain.comparison import (
    CommonMonthlyResourcesInput,
    ResourceComponentInput,
    ResourceMonthInput,
)


def component(
    identity: str, amount: str, *, projected: bool = True
) -> ResourceComponentInput:
    return ResourceComponentInput(
        identity,
        amount,
        "projected_assumption" if projected else "observed_data",
        "synthetic-source",
        "2026-11-03T12:00:00Z",
        "explicit-profile-v1" if projected else None,
    )


def profile(income: str = "3.00", expense: str = "1.00") -> CommonMonthlyResourcesInput:
    return CommonMonthlyResourcesInput(
        "net_before_household_expenses",
        "strategy_independent_excluding_strategy_flows_and_netted_deductions",
        tuple(
            ResourceMonthInput(
                month,
                (component("income-a", income),),
                (component("expense-a", expense),),
            )
            for month in range(1, 61)
        ),
    )


def raw_profile(value: CommonMonthlyResourcesInput | None = None) -> dict[str, object]:
    return json.loads(json.dumps(asdict(value or profile())))


def test_variable_components_derive_signed_resources_without_defaults() -> None:
    value = profile()
    value = replace(
        value,
        months=(
            ResourceMonthInput(
                1,
                (
                    component("income-a", "+0001.00", projected=False),
                    component("income-b", "2.00"),
                ),
                (component("expense-a", "4.00"),),
            ),
            ResourceMonthInput(2, (), (component("expense-a", "-0.00"),)),
            *value.months[2:],
        ),
    )
    normalized = resources.normalize(raw_profile(value))
    months = cast(list[dict[str, object]], normalized["months"])
    assert [
        months[0][key]
        for key in ("income_total", "external_expense_total", "available_resources")
    ] == ["3.00", "4.00", "-1.00"]
    assert months[1]["available_resources"] == "0.00"
    assert (
        cast(list[dict[str, object]], months[0]["income_components"])[0]["amount"]
        == "1.00"
    )
    assert (
        cast(list[dict[str, object]], months[0]["income_components"])[0][
            "assumption_reference"
        ]
        is None
    )
    assert months[2]["available_resources"] == "2.00"
    # Explicit components can sum beyond the input bound without aggregate capping.
    huge = component("income-b", "999999999999999999.99")
    extended = replace(
        profile(),
        months=tuple(
            ResourceMonthInput(m, (component("income-a", huge.amount), huge), ())
            for m in range(1, 61)
        ),
    )
    assert (
        cast(
            list[dict[str, object]],
            resources.normalize(raw_profile(extended))["months"],
        )[0]["income_total"]
        == "1999999999999999999.98"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "profile_type",
        "profile_extra",
        "profile_missing",
        "basis",
        "scope",
        "months_type",
        "month_missing",
        "month_extra",
        "month_order",
        "month_bool",
        "month_type",
        "month_fields",
        "month_unknown",
        "array_type",
        "component_type",
        "component_missing",
        "component_extra",
        "duplicate",
        "cross_side",
        "side_change",
    ],
)
def test_complete_profile_structure_and_identity_are_required(mutation: str) -> None:
    value: object = raw_profile()
    raw = value
    months = cast(list[dict[str, object]], raw["months"])
    row = months[-1]
    income = cast(list[dict[str, object]], row["income_components"])
    if mutation == "profile_type":
        value = []
    elif mutation == "profile_extra":
        raw["available_resources"] = "2.00"
    elif mutation == "profile_missing":
        del raw["expense_scope"]
    elif mutation == "basis":
        raw["income_basis"] = "gross"
    elif mutation == "scope":
        raw["expense_scope"] = "includes_housing"
    elif mutation == "months_type":
        raw["months"] = None
    elif mutation == "month_missing":
        months.pop()
    elif mutation == "month_extra":
        months.append(row)
    elif mutation == "month_order":
        row["month"] = 59
    elif mutation == "month_bool":
        months[0]["month"] = True
    elif mutation == "month_type":
        cast(list[object], raw["months"])[59] = []
    elif mutation == "month_fields":
        del row["external_expenses"]
    elif mutation == "month_unknown":
        row["income_total"] = "3.00"
    elif mutation == "array_type":
        row["external_expenses"] = None
    elif mutation == "component_type":
        cast(list[object], row["income_components"])[0] = None
    elif mutation == "component_missing":
        del income[0]["source_reference"]
    elif mutation == "component_extra":
        income[0]["description"] = "synthetic"
    elif mutation == "duplicate":
        income.append(income[0])
    elif mutation == "cross_side":
        cast(list[dict[str, object]], row["external_expenses"])[0]["component_id"] = (
            "income-a"
        )
    elif mutation == "side_change":
        row["income_components"], row["external_expenses"] = (
            row["external_expenses"],
            row["income_components"],
        )
    with pytest.raises(resources.Rejected, match="monthly resource"):
        resources.normalize(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("component_id", ""),
        ("source_reference", "contains spaces"),
        ("source_reference", None),
        ("amount", "-0.01"),
        ("amount", "1.001"),
        ("amount", "1e2"),
        ("amount", "١.00"),
        ("amount", "1000000000000000000.00"),
        ("amount", 1),
        ("classification", "contractual_data"),
        ("assumption_reference", None),
        ("assumption_reference", ""),
        ("source_as_of", "2026-02-30T12:00:00Z"),
        ("source_as_of", "2026-11-03"),
        ("source_as_of", "2026-11-03T12:00:00+00:00"),
        ("source_as_of", None),
    ],
)
def test_component_units_and_provenance_are_explicit(field: str, value: object) -> None:
    raw = raw_profile()
    row = cast(list[dict[str, object]], raw["months"])[59]
    cast(list[dict[str, object]], row["income_components"])[0][field] = value
    with pytest.raises(resources.Rejected):
        resources.normalize(raw)


def test_observed_values_cannot_carry_a_projected_assumption() -> None:
    value = profile()
    observed = replace(
        component("income-a", "3.00", projected=False), assumption_reference="invented"
    )
    value = replace(
        value,
        months=(
            replace(value.months[0], income_components=(observed,)),
            *value.months[1:],
        ),
    )
    with pytest.raises(resources.Rejected):
        resources.normalize(raw_profile(value))
