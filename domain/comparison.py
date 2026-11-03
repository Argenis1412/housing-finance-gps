"""Explicit immutable in-memory simulation creation and verified comparison."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import cast

from domain import comparison_v1 as _retained
from domain.consortium import replay_v1 as _codec
from domain.consortium.contracts import ConsortiumRequest
from domain.financing.contracts import FinancingRequest
from domain.ledger import ComparisonLedgerRow
from domain.rent_plus_investment import RentPlusInvestmentRequest
from domain.values import BRLMoney, DomainFailure, FailureCode


def _is_text(value: object) -> bool:
    return isinstance(value, str)


@dataclass(frozen=True, slots=True)
class SharedComparisonInput:
    comparison_opening_cash: str
    property_price: str
    starting_monthly_rent: str
    rent_adjustment_rate_value: str
    rent_adjustment_rate_convention: str
    first_rent_adjustment_month: int


@dataclass(frozen=True, slots=True)
class ComparisonConstraints:
    minimum_liquidity: str
    maximum_monthly_housing_outflow: str


@dataclass(frozen=True, slots=True)
class ComparisonRequest:
    shared: SharedComparisonInput
    constraints: ComparisonConstraints
    financing: FinancingRequest
    rent: RentPlusInvestmentRequest
    consortium: ConsortiumRequest


@dataclass(frozen=True, slots=True)
class ComparisonSimulationEnvelope:
    contract_schema_version: str
    engine_version: str
    ruleset_version: str
    data_snapshot_id: str
    calculated_at: str
    timezone: str
    raw_request_jcs: str
    sealed_outcome_jcs: str

    def __post_init__(self) -> None:
        _retained.validate_metadata({
            "data_snapshot_id": self.data_snapshot_id,
            "calculated_at": self.calculated_at, "timezone": self.timezone,
        })
        evidence: tuple[object, ...] = (
            self.contract_schema_version, self.engine_version, self.ruleset_version,
            self.raw_request_jcs, self.sealed_outcome_jcs,
        )
        if any(not _is_text(value) for value in evidence):
            raise ValueError("comparison evidence fields must be strings")


@dataclass(frozen=True, slots=True)
class ConstraintViolation:
    constraint: str
    month: int
    actual: BRLMoney
    threshold: BRLMoney


@dataclass(frozen=True, slots=True)
class ComparisonMetrics:
    final_ledger_row: ComparisonLedgerRow
    minimum_liquidity: BRLMoney
    minimum_liquidity_months: tuple[int, ...]
    maximum_monthly_housing_outflow: BRLMoney
    maximum_monthly_housing_outflow_months: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class AlternativeComparison:
    strategy: str
    status: str
    failure: DomainFailure | None
    metrics: ComparisonMetrics | None
    violations: tuple[ConstraintViolation, ...]
    comparison_ledger: tuple[ComparisonLedgerRow, ...]
    monthly_housing_outflows: tuple[BRLMoney, ...]


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    envelope: ComparisonSimulationEnvelope
    status: str
    alternatives: tuple[AlternativeComparison, ...]
    ranking_groups: tuple[tuple[str, ...], ...]
    limitations: tuple[str, ...]


def create_comparison_v1_envelope(
    *, raw_request_jcs: str, data_snapshot_id: str, calculated_at: str,
) -> ComparisonSimulationEnvelope:
    """Bind metadata to a canonical comparison request before evaluation.

    Invalid representations/metadata raise ValueError without an artifact.
    Canonical semantic failures are sealed. Unexpected evaluator errors escape.
    """
    metadata = _retained.validate_metadata({
        "data_snapshot_id": data_snapshot_id, "calculated_at": calculated_at,
        "timezone": "America/Sao_Paulo",
    })
    raw = _codec.parse_canonical_object(raw_request_jcs)
    bound = _codec.canonical_json({"metadata": metadata, "comparison": raw})
    outcome = _retained.evaluate(bound)
    return ComparisonSimulationEnvelope(
        _retained.CONTRACT_SCHEMA_VERSION, _retained.ENGINE_VERSION, _retained.RULESET_VERSION,
        data_snapshot_id, calculated_at, "America/Sao_Paulo", bound, outcome,
    )


def _failure(value: dict[str, object]) -> DomainFailure:
    return DomainFailure(cast(FailureCode, value["code"]), cast(str, value["detail"]))


def _ledger(value: dict[str, object]) -> ComparisonLedgerRow:
    return ComparisonLedgerRow(
        month=cast(int, value["month"]),
        **{name: BRLMoney(cast(str, amount)) for name, amount in value.items() if name != "month"},
    )


def _decode(envelope: ComparisonSimulationEnvelope) -> ComparisonResult | DomainFailure:
    outcome = _codec.parse_canonical_object(envelope.sealed_outcome_jcs)
    if outcome["kind"] == "failure":
        return _failure(outcome)
    alternatives: list[AlternativeComparison] = []
    for value in cast(list[dict[str, object]], outcome["alternatives"]):
        if value["status"] == "domain_failure":
            alternatives.append(AlternativeComparison(
                cast(str, value["strategy"]), "domain_failure",
                _failure(cast(dict[str, object], value["failure"])), None, (), (), (),
            ))
            continue
        metrics = cast(dict[str, object], value["metrics"])
        typed_metrics = ComparisonMetrics(
            _ledger(cast(dict[str, object], metrics["final_ledger_row"])),
            BRLMoney(cast(str, metrics["minimum_liquidity"])),
            tuple(cast(list[int], metrics["minimum_liquidity_months"])),
            BRLMoney(cast(str, metrics["maximum_monthly_housing_outflow"])),
            tuple(cast(list[int], metrics["maximum_monthly_housing_outflow_months"])),
        )
        violations = tuple(ConstraintViolation(
            cast(str, row["constraint"]), cast(int, row["month"]),
            BRLMoney(cast(str, row["actual"])), BRLMoney(cast(str, row["threshold"])),
        ) for row in cast(list[dict[str, object]], value["violations"]))
        alternatives.append(AlternativeComparison(
            cast(str, value["strategy"]), cast(str, value["status"]), None,
            typed_metrics, violations,
            tuple(_ledger(row) for row in cast(list[dict[str, object]], value["comparison_ledger"])),
            tuple(BRLMoney(amount) for amount in cast(list[str], value["monthly_housing_outflows"])),
        ))
    result = cast(dict[str, object], outcome["result"])
    trace = cast(dict[str, object], outcome["trace"])
    return ComparisonResult(
        envelope, cast(str, result["status"]), tuple(alternatives),
        tuple(tuple(group) for group in cast(list[list[str]], result["ranking_groups"])),
        tuple(cast(list[str], trace["limitations"])),
    )


def calculate_comparison_v1(
    request: ComparisonRequest, *, data_snapshot_id: str, calculated_at: str,
) -> ComparisonResult | DomainFailure:
    """Create a simulation explicitly and return its immutable typed projection."""
    # Tuples in immutable consortium requests become JSON arrays before JCS.
    raw = _codec.canonical_json(json.loads(json.dumps(asdict(request), allow_nan=False)))
    return _decode(create_comparison_v1_envelope(
        raw_request_jcs=raw, data_snapshot_id=data_snapshot_id, calculated_at=calculated_at,
    ))


def replay_comparison(envelope: ComparisonSimulationEnvelope) -> ComparisonResult | DomainFailure:
    """Reexecute the retained evaluator, never return a stored-outcome fallback."""
    try:
        if (envelope.contract_schema_version, envelope.engine_version, envelope.ruleset_version) != (
            _retained.CONTRACT_SCHEMA_VERSION, _retained.ENGINE_VERSION, _retained.RULESET_VERSION,
        ):
            raise ValueError("comparison historical handler unavailable")
        envelope.__post_init__()
        bound = _codec.parse_canonical_object(envelope.raw_request_jcs)
        metadata = {
            "data_snapshot_id": envelope.data_snapshot_id,
            "calculated_at": envelope.calculated_at, "timezone": envelope.timezone,
        }
        if bound.get("metadata") != metadata:
            raise ValueError("comparison metadata differs from bound request")
        _codec.parse_canonical_object(envelope.sealed_outcome_jcs)
        if _retained.evaluate(envelope.raw_request_jcs) != envelope.sealed_outcome_jcs:
            raise ValueError("comparison outcome differs on reexecution")
        return _decode(envelope)
    except Exception:
        # Verification failure is typed even for unexpected retained execution
        # errors. Creation deliberately does not catch these exceptions.
        return DomainFailure("incompatible_contract_version", "historical comparison equivalence cannot be proven")
