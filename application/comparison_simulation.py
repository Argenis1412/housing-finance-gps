"""Explicit transient comparison creation; all financial output stays domain-owned."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import cast
from uuid import uuid4

from domain.comparison import create_comparison_v2_envelope
from domain.consortium.replay_v1 import canonical_json


@dataclass(frozen=True, slots=True)
class ComparisonApplicationFailure:
    code: str


def _clock() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _snapshot() -> str:
    return f"comparison-{uuid4()}"


def _object(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def create_comparison_simulation(
    comparison: dict[str, object],
    *,
    clock: Callable[[], str] = _clock,
    snapshot_factory: Callable[[], str] = _snapshot,
) -> dict[str, object] | ComparisonApplicationFailure:
    """Create v2 evidence once and copy its sealed outcome without recalculation.

    Clocks and identifiers are application dependencies, never domain inputs
    inferred from component provenance. No evidence is persisted or exported.
    """
    envelope = create_comparison_v2_envelope(
        raw_request_jcs=canonical_json(comparison),
        data_snapshot_id=snapshot_factory(),
        calculated_at=clock(),
    )
    outcome = _object(json.loads(envelope.sealed_outcome_jcs))
    if outcome["kind"] == "failure":
        return ComparisonApplicationFailure(cast(str, outcome["code"]))
    alternatives: list[dict[str, object]] = []
    for raw in cast(list[dict[str, object]], outcome["alternatives"]):
        alternative = dict(raw)
        if raw["status"] == "domain_failure":
            failure = _object(raw["failure"])
            safe: dict[str, object] = {"code": failure["code"]}
            match = re.fullmatch(
                r"cash is insufficient in month (0|[1-9][0-9]?) during "
                r"(opening_allocation|external_expenses|strategy_obligations|investment_contribution)",
                cast(str, failure["detail"]),
            )
            if failure["code"] == "infeasible_scenario" and match and int(match[1]) <= 60:
                safe.update(month=int(match[1]), phase=match[2])
            alternative["failure"] = safe
        alternatives.append(alternative)
    trace = _object(outcome["trace"])
    children: list[dict[str, object]] = []
    for child in cast(list[dict[str, object]], trace["child_evidence"]):
        projected: dict[str, object] = {
            "strategy": child["strategy"], "versions": child["versions"],
        }
        if "input_classification" in child:
            projected["input_classification"] = child["input_classification"]
        children.append(projected)
    result = _object(outcome["result"])
    return {
        "api_version": "v1", "kind": "simulation_result",
        "contract_schema_version": envelope.contract_schema_version,
        "engine_version": envelope.engine_version, "ruleset_version": envelope.ruleset_version,
        "data_snapshot_id": envelope.data_snapshot_id,
        "calculated_at": envelope.calculated_at, "timezone": envelope.timezone,
        "declared_inputs": json.loads(canonical_json(comparison)),
        "normalized_input": outcome["normalized_input"],
        "children": children, "alternatives": alternatives,
        "status": result["status"], "objective": result["objective"],
        "ranking_groups": result["ranking_groups"], "limitations": trace["limitations"],
    }
