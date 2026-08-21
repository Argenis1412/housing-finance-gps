"""Versioned, fail-closed financing replay dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import re
from types import MappingProxyType
from typing import Literal, Protocol, TypeGuard

from domain.financing import replay_v1
from domain.financing import replay_v2
from domain.financing import replay_v3
from domain.values import DomainFailure


Strategy = Literal["sac", "price"]
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _is_text(value: object) -> TypeGuard[str]:
    return isinstance(value, str)


@dataclass(frozen=True, slots=True)
class SimulationReplayEnvelope:
    """The only immutable evidence object eligible for financing replay."""

    contract_schema_version: str
    strategy: Strategy
    raw_request_jcs: str
    engine_version: str
    ruleset_version: str
    data_snapshot_id: str
    sealed_outcome_jcs: str

    def __post_init__(self) -> None:
        version_values: tuple[object, ...] = (
            self.contract_schema_version,
            self.engine_version,
            self.ruleset_version,
            self.data_snapshot_id,
        )
        for value in version_values:
            if not _is_text(value) or not _IDENTIFIER.fullmatch(value):
                raise ValueError("replay version identifiers must be canonical identifiers")
        evidence_values: tuple[object, ...] = (self.raw_request_jcs, self.sealed_outcome_jcs)
        if not all(_is_text(value) for value in evidence_values):
            raise ValueError("replay evidence must be canonical JSON strings")
        if self.strategy not in ("sac", "price"):
            raise ValueError("replay strategy is invalid")


@dataclass(frozen=True, slots=True)
class ReplayVerification:
    """Evidence that an envelope was reexecuted and matched exactly."""

    envelope: SimulationReplayEnvelope


class _ReplayHandler(Protocol):
    def parse_canonical_object(self, text: object) -> dict[str, object]: ...

    def validate_outcome(self, outcome_jcs: object) -> None: ...

    def evaluate(self, raw_request_jcs: str, strategy: Strategy) -> replay_v1.V1Evaluation | str: ...


def create_v1_envelope(*, strategy: Strategy, raw_request_jcs: str, data_snapshot_id: str) -> SimulationReplayEnvelope:
    """Emit a v1 envelope through the only v1 semantic authority."""
    if strategy not in ("sac", "price"):
        raise ValueError("replay strategy is invalid")
    outcome = replay_v1.evaluate(raw_request_jcs, strategy)
    replay_v1.parse_canonical_object(raw_request_jcs)
    replay_v1.validate_outcome(outcome.outcome_jcs)
    return SimulationReplayEnvelope(
        contract_schema_version=replay_v1.CONTRACT_SCHEMA_VERSION,
        strategy=strategy,
        raw_request_jcs=raw_request_jcs,
        engine_version=replay_v1.ENGINE_VERSION,
        ruleset_version=replay_v1.RULESET_VERSION,
        data_snapshot_id=data_snapshot_id,
        sealed_outcome_jcs=outcome.outcome_jcs,
    )


def create_v2_envelope(*, strategy: Strategy, raw_request_jcs: str, data_snapshot_id: str) -> SimulationReplayEnvelope:
    """Emit a v2 envelope through the single v2 semantic authority."""
    if strategy not in ("sac", "price"):
        raise ValueError("replay strategy is invalid")
    replay_v2.parse_canonical_object(raw_request_jcs)
    outcome = replay_v2.evaluate(raw_request_jcs, strategy)
    replay_v2.validate_outcome(outcome)
    return SimulationReplayEnvelope(
        contract_schema_version=replay_v2.CONTRACT_SCHEMA_VERSION,
        strategy=strategy,
        raw_request_jcs=raw_request_jcs,
        engine_version=replay_v2.ENGINE_VERSION,
        ruleset_version=replay_v2.RULESET_VERSION,
        data_snapshot_id=data_snapshot_id,
        sealed_outcome_jcs=outcome,
    )


def create_v3_envelope(*, strategy: Strategy, raw_request_jcs: str, data_snapshot_id: str) -> SimulationReplayEnvelope:
    """Emit a v3 envelope through the centavo-safe semantic authority."""
    if strategy not in ("sac", "price"):
        raise ValueError("replay strategy is invalid")
    replay_v3.parse_canonical_object(raw_request_jcs)
    outcome = replay_v3.evaluate(raw_request_jcs, strategy)
    replay_v3.validate_outcome(outcome)
    return SimulationReplayEnvelope(
        contract_schema_version=replay_v3.CONTRACT_SCHEMA_VERSION,
        strategy=strategy,
        raw_request_jcs=raw_request_jcs,
        engine_version=replay_v3.ENGINE_VERSION,
        ruleset_version=replay_v3.RULESET_VERSION,
        data_snapshot_id=data_snapshot_id,
        sealed_outcome_jcs=outcome,
    )


def replay_financing(envelope: SimulationReplayEnvelope) -> ReplayVerification | DomainFailure:
    """Reexecute an envelope or fail closed when equivalence is unprovable."""
    try:
        handler = _HANDLERS[
            (
                envelope.contract_schema_version,
                envelope.engine_version,
                envelope.ruleset_version,
                envelope.strategy,
            )
        ]
        handler.parse_canonical_object(envelope.raw_request_jcs)
        handler.validate_outcome(envelope.sealed_outcome_jcs)
    except (AttributeError, KeyError, TypeError, ValueError):
        return DomainFailure("incompatible_contract_version", "historical replay equivalence cannot be proven")
    try:
        reproduced = handler.evaluate(envelope.raw_request_jcs, envelope.strategy)
    except ValueError:
        return DomainFailure("incompatible_contract_version", "historical replay equivalence cannot be proven")
    reproduced_outcome = (
        reproduced.outcome_jcs if isinstance(reproduced, replay_v1.V1Evaluation) else reproduced
    )
    if reproduced_outcome != envelope.sealed_outcome_jcs:
        return DomainFailure("incompatible_contract_version", "historical replay equivalence cannot be proven")
    return ReplayVerification(envelope)


_HANDLERS: Mapping[tuple[str, str, str, Strategy], _ReplayHandler] = MappingProxyType({
    (replay_v1.CONTRACT_SCHEMA_VERSION, replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION, "sac"): replay_v1,
    (replay_v1.CONTRACT_SCHEMA_VERSION, replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION, "price"): replay_v1,
    (replay_v2.CONTRACT_SCHEMA_VERSION, replay_v2.ENGINE_VERSION, replay_v2.RULESET_VERSION, "sac"): replay_v2,
    (replay_v2.CONTRACT_SCHEMA_VERSION, replay_v2.ENGINE_VERSION, replay_v2.RULESET_VERSION, "price"): replay_v2,
    (replay_v3.CONTRACT_SCHEMA_VERSION, replay_v3.ENGINE_VERSION, replay_v3.RULESET_VERSION, "sac"): replay_v3,
    (replay_v3.CONTRACT_SCHEMA_VERSION, replay_v3.ENGINE_VERSION, replay_v3.RULESET_VERSION, "price"): replay_v3,
})
