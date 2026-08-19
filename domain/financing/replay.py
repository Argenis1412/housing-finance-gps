"""Versioned, fail-closed financing replay dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import re
from types import MappingProxyType
from typing import Callable, Literal

from domain.financing import replay_v1
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
        replay_v1.parse_canonical_object(self.raw_request_jcs)
        replay_v1.validate_outcome(self.sealed_outcome_jcs)


@dataclass(frozen=True, slots=True)
class ReplayVerification:
    """Evidence that an envelope was reexecuted and matched exactly."""

    envelope: SimulationReplayEnvelope


def create_v1_envelope(*, strategy: Strategy, raw_request_jcs: str, data_snapshot_id: str) -> SimulationReplayEnvelope:
    """Emit a v1 envelope through the only v1 semantic authority."""
    if strategy not in ("sac", "price"):
        raise ValueError("replay strategy is invalid")
    outcome = replay_v1.evaluate(raw_request_jcs, strategy)
    return SimulationReplayEnvelope(
        contract_schema_version=replay_v1.CONTRACT_SCHEMA_VERSION,
        strategy=strategy,
        raw_request_jcs=raw_request_jcs,
        engine_version=replay_v1.ENGINE_VERSION,
        ruleset_version=replay_v1.RULESET_VERSION,
        data_snapshot_id=data_snapshot_id,
        sealed_outcome_jcs=outcome.outcome_jcs,
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
        replay_v1.parse_canonical_object(envelope.raw_request_jcs)
        replay_v1.validate_outcome(envelope.sealed_outcome_jcs)
    except (AttributeError, KeyError, TypeError, ValueError):
        return DomainFailure("incompatible_contract_version", "historical replay equivalence cannot be proven")
    reproduced = handler(envelope.raw_request_jcs, envelope.strategy)
    if reproduced.outcome_jcs != envelope.sealed_outcome_jcs:
        return DomainFailure("incompatible_contract_version", "historical replay equivalence cannot be proven")
    return ReplayVerification(envelope)


_HANDLERS: Mapping[tuple[str, str, str, Strategy], Callable[[str, Strategy], replay_v1.V1Evaluation]] = MappingProxyType({
    (replay_v1.CONTRACT_SCHEMA_VERSION, replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION, "sac"): replay_v1.evaluate,
    (replay_v1.CONTRACT_SCHEMA_VERSION, replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION, "price"): replay_v1.evaluate,
})
