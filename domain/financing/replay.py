"""Versioned, fail-closed financing replay dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import re
from types import MappingProxyType
from typing import Literal

from domain.financing import replay_v1
from domain.financing import replay_v2
from domain.values import DomainFailure


Strategy = Literal["sac", "price"]
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


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
        for value in (
            self.contract_schema_version,
            self.engine_version,
            self.ruleset_version,
            self.data_snapshot_id,
        ):
            if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
                raise ValueError("replay version identifiers must be canonical identifiers")
        if self.strategy not in ("sac", "price"):
            raise ValueError("replay strategy is invalid")
        if not isinstance(self.raw_request_jcs, str) or not isinstance(self.sealed_outcome_jcs, str):
            raise ValueError("replay evidence must be canonical JSON strings")


@dataclass(frozen=True, slots=True)
class ReplayVerification:
    """Evidence that an envelope was reexecuted and matched exactly."""

    envelope: SimulationReplayEnvelope


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
    reproduced_outcome = reproduced.outcome_jcs if hasattr(reproduced, "outcome_jcs") else reproduced
    if reproduced_outcome != envelope.sealed_outcome_jcs:
        return DomainFailure("incompatible_contract_version", "historical replay equivalence cannot be proven")
    return ReplayVerification(envelope)


_HANDLERS: Mapping[tuple[str, str, str, Strategy], object] = MappingProxyType({
    (replay_v1.CONTRACT_SCHEMA_VERSION, replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION, "sac"): replay_v1,
    (replay_v1.CONTRACT_SCHEMA_VERSION, replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION, "price"): replay_v1,
    (replay_v2.CONTRACT_SCHEMA_VERSION, replay_v2.ENGINE_VERSION, replay_v2.RULESET_VERSION, "sac"): replay_v2,
    (replay_v2.CONTRACT_SCHEMA_VERSION, replay_v2.ENGINE_VERSION, replay_v2.RULESET_VERSION, "price"): replay_v2,
})
