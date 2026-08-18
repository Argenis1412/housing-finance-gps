"""Immutable values shared by the deterministic financial domain."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal
import re


FailureCode = Literal[
    "invalid_input",
    "unsupported_rate_convention",
    "unsupported_rule",
    "unsupported_contract_clause",
    "infeasible_scenario",
    "incompatible_contract_version",
]

_BRL_PATTERN = re.compile(r"[+-]?\d+\.\d{2}\Z")
_FAILURE_CODES = frozenset(
    {
        "invalid_input",
        "unsupported_rate_convention",
        "unsupported_rule",
        "unsupported_contract_clause",
        "infeasible_scenario",
        "incompatible_contract_version",
    }
)


@dataclass(frozen=True, slots=True, init=False)
class BRLMoney:
    """A BRL amount created only from an exact-two-fraction contract string."""

    amount: Decimal

    def __init__(self, raw_value: str) -> None:
        if not isinstance(raw_value, str) or not _BRL_PATTERN.fullmatch(raw_value):
            raise ValueError("BRL money must be an exact-two-fraction decimal string")
        try:
            amount = Decimal(raw_value)
        except InvalidOperation as error:
            raise ValueError("BRL money must be a finite decimal string") from error
        if not amount.is_finite():
            raise ValueError("BRL money must be a finite decimal string")
        object.__setattr__(self, "amount", amount)

    @property
    def as_string(self) -> str:
        return format(self.amount, ".2f")


@dataclass(frozen=True, slots=True, init=False)
class DeclaredRate:
    """A finite decimal rate together with the convention originally declared."""

    raw_value: str
    convention: str
    amount: Decimal

    def __init__(self, raw_value: str, convention: str) -> None:
        if not isinstance(raw_value, str) or not isinstance(convention, str):
            raise ValueError("rate value and convention must be strings")
        try:
            amount = Decimal(raw_value)
        except InvalidOperation as error:
            raise ValueError("rate must be a finite decimal string") from error
        if not amount.is_finite():
            raise ValueError("rate must be a finite decimal string")
        object.__setattr__(self, "raw_value", raw_value)
        object.__setattr__(self, "convention", convention)
        object.__setattr__(self, "amount", amount)


@dataclass(frozen=True, slots=True, init=False)
class EffectiveMonthlyRate:
    """The only rate primitive accepted by the SAC calculator."""

    amount: Decimal

    def __init__(self, declared_rate: DeclaredRate) -> None:
        if not isinstance(declared_rate, DeclaredRate):
            raise ValueError("effective monthly rate requires a declared rate")
        if declared_rate.convention != "effective_monthly":
            raise ValueError("rate convention is not effective_monthly")
        if declared_rate.amount < Decimal("0"):
            raise ValueError("effective monthly rate cannot be negative")
        object.__setattr__(self, "amount", declared_rate.amount)

    @classmethod
    def zero(cls) -> "EffectiveMonthlyRate":
        """Create a calculation zero after a documented zero exclusion."""
        return cls(DeclaredRate("0", "effective_monthly"))


@dataclass(frozen=True, slots=True, init=False)
class DomainFailure:
    """A safe, inspectable failure returned by a domain boundary."""

    code: FailureCode
    detail: str

    def __init__(self, code: FailureCode, detail: str) -> None:
        if code not in _FAILURE_CODES or not isinstance(detail, str):
            raise ValueError("domain failure requires a canonical code and safe detail")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "detail", detail)
