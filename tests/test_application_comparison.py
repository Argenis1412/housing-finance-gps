"""Protect projection of sealed comparison evidence, never fresh arithmetic."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import cast

import pytest

from application import comparison_simulation as application
from domain.comparison import replay_comparison
from domain.values import DomainFailure
from tests.test_monthly_resources_comparison import envelope, outcome, raw_request, request
from tests.test_monthly_resources_domain import component


def create(raw: dict[str, object] | None = None) -> dict[str, object] | application.ComparisonApplicationFailure:
    return application.create_comparison_simulation(
        raw if raw is not None else raw_request(),
        clock=lambda: "2026-11-03T12:00:00Z", snapshot_factory=lambda: "synthetic-application",
    )


def test_application_copies_sealed_metrics_groups_and_profile_without_mutating_inputs() -> None:
    raw = raw_request()
    before = deepcopy(raw)
    actual = create(raw)
    assert isinstance(actual, dict) and raw == before
    expected = outcome(raw)
    assert actual["alternatives"] == expected["alternatives"]
    assert actual["normalized_input"] == expected["normalized_input"]
    assert actual["ranking_groups"] == cast(dict[str, object], expected["result"])["ranking_groups"]
    assert create(raw) == actual
    assert not {"raw_request_jcs", "sealed_outcome_jcs", "simulation_id"} & actual.keys()
    assert not isinstance(replay_comparison(envelope(raw)), DomainFailure)


def test_fresh_application_metadata_changes_only_lineage() -> None:
    first = application.create_comparison_simulation(raw_request())
    second = application.create_comparison_simulation(raw_request())
    assert isinstance(first, dict) and isinstance(second, dict)
    assert first["data_snapshot_id"] != second["data_snapshot_id"]
    assert first["normalized_input"] == second["normalized_input"]
    assert first["alternatives"] == second["alternatives"]


def test_global_failure_returns_no_result_projection() -> None:
    raw = raw_request()
    raw["monthly_resources"] = None
    assert create(raw) == application.ComparisonApplicationFailure("invalid_input")


def test_cash_failure_is_safe_and_keeps_month_and_phase_without_partial_metrics() -> None:
    actual = create(raw_request(request("0.00", "0.01", "0.00")))
    assert isinstance(actual, dict) and actual["status"] == "no_eligible"
    for alternative in cast(list[dict[str, object]], actual["alternatives"]):
        assert alternative.keys() == {"strategy", "status", "failure"}
        assert alternative["failure"] == {"code": "infeasible_scenario", "month": 1, "phase": "external_expenses"}


def test_rejected_admission_has_no_invented_classification() -> None:
    raw = raw_request()
    raw["financing"] = None
    actual = create(raw)
    assert isinstance(actual, dict)
    child = cast(list[dict[str, object]], actual["children"])[0]
    assert "input_classification" not in child


def test_large_exact_assets_and_negative_common_resources_stay_strings() -> None:
    value = request("3.00", "1.00", "999999999999999999.99")
    value = replace(value, rent=replace(value.rent, initial_invested_capital="999999999999999999.99", return_rate_value="1"))
    actual = create(raw_request(value))
    assert isinstance(actual, dict)
    rent = cast(list[dict[str, object]], actual["alternatives"])[2]
    final = cast(dict[str, object], cast(dict[str, object], rent["metrics"])["final_ledger_row"])
    assert final["liquid_financial_assets"] == "1152921504606846975988470784953931530.24"
    monthly = value.monthly_resources.months
    value = replace(value, monthly_resources=replace(value.monthly_resources, months=(replace(monthly[0], income_components=(component("income-a", "0.00", projected=False),)), *monthly[1:])))
    actual = create(raw_request(value))
    assert isinstance(actual, dict)
    profile = cast(dict[str, object], cast(dict[str, object], actual["normalized_input"])["monthly_resources"])
    assert cast(list[dict[str, object]], profile["months"])[0]["available_resources"] == "-1.00"


def test_unexpected_domain_execution_error_propagates_to_http_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(**_: object) -> object:
        raise RuntimeError("private diagnostic must not become an exclusion")
    monkeypatch.setattr(application, "create_comparison_v2_envelope", broken)
    with pytest.raises(RuntimeError):
        create()
