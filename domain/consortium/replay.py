"""Dedicated immutable evidence and exact in-memory consortium replay."""

from dataclasses import dataclass
import re
from typing import Literal, TypeGuard

from domain.consortium import replay_v1
from domain.values import DomainFailure


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _is_text(value: object) -> TypeGuard[str]:
    return isinstance(value, str)


@dataclass(frozen=True, slots=True)
class ConsortiumReplayEnvelope:
    contract_schema_version: str
    strategy: Literal["consortium"]
    raw_request_jcs: str
    engine_version: str
    ruleset_version: str
    data_snapshot_id: str
    sealed_outcome_jcs: str

    def __post_init__(self) -> None:
        identifiers: tuple[object, ...] = (
            self.contract_schema_version, self.engine_version, self.ruleset_version, self.data_snapshot_id,
        )
        if any(not _is_text(value) or not _IDENTIFIER.fullmatch(value) for value in identifiers):
            raise ValueError("consortium versions must be canonical identifiers")
        evidence: tuple[object, ...] = (self.raw_request_jcs, self.sealed_outcome_jcs)
        if self.strategy != "consortium" or any(not _is_text(value) for value in evidence):
            raise ValueError("consortium replay container is invalid")


@dataclass(frozen=True, slots=True)
class ConsortiumReplayVerification:
    envelope: ConsortiumReplayEnvelope


def create_consortium_v1_envelope(*, raw_request_jcs: str, data_snapshot_id: str) -> ConsortiumReplayEnvelope:
    outcome = replay_v1.evaluate(raw_request_jcs)
    return ConsortiumReplayEnvelope(
        replay_v1.CONTRACT_SCHEMA_VERSION, "consortium", raw_request_jcs,
        replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION, data_snapshot_id, outcome,
    )


def replay_consortium(envelope: ConsortiumReplayEnvelope) -> ConsortiumReplayVerification | DomainFailure:
    try:
        if (
            envelope.contract_schema_version, envelope.engine_version, envelope.ruleset_version, envelope.strategy,
        ) != (
            replay_v1.CONTRACT_SCHEMA_VERSION, replay_v1.ENGINE_VERSION, replay_v1.RULESET_VERSION, "consortium",
        ):
            raise ValueError("historical consortium handler unavailable")
        # Revalidate containers too: callers can bypass dataclass construction.
        envelope.__post_init__()
        replay_v1.parse_canonical_object(envelope.sealed_outcome_jcs)
        if replay_v1.evaluate(envelope.raw_request_jcs) == envelope.sealed_outcome_jcs:
            return ConsortiumReplayVerification(envelope)
    except (AttributeError, TypeError, ValueError, RecursionError):
        pass
    return DomainFailure("incompatible_contract_version", "historical consortium replay equivalence cannot be proven")
