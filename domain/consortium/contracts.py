"""Immutable inputs and projections for the admitted consortium v1 boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from domain.ledger import ComparisonLedgerRow
from domain.values import BRLMoney


ConsortiumScenarioKind = Literal["early", "intermediate", "late"]


@dataclass(frozen=True, slots=True)
class ConsortiumScheduleInput:
    month: int
    credit_component: str
    administration_fee: str
    reserve_fund: str
    insurance: str


@dataclass(frozen=True, slots=True)
class ConsortiumWaitingCostInput:
    month: int
    amount: str


@dataclass(frozen=True, slots=True)
class ConsortiumRequest:
    """Closed proposal declarations and separately classified scenario inputs."""

    comparison_opening_cash: str
    credit_letter: str
    term_months: int
    monthly_schedule: tuple[ConsortiumScheduleInput, ...]
    credit_components_apply_to_credit_letter: bool
    correction: str
    reserve_fund_treatment: str
    installment_schedule_treatment: str
    scenario_kind: ConsortiumScenarioKind
    contemplation_month: int
    property_purchase_event: bool
    property_price: str
    cash_top_up: str
    waiting_housing_costs: tuple[ConsortiumWaitingCostInput, ...]
    requested_features: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedConsortiumV1Input:
    raw_request_jcs: str


@dataclass(frozen=True, slots=True)
class ConsortiumContractualRow:
    month: int
    credit_component: BRLMoney
    administration_fee: BRLMoney
    reserve_fund: BRLMoney
    insurance: BRLMoney
    payment: BRLMoney


@dataclass(frozen=True, slots=True)
class ConsortiumMonthlyRow:
    """Cash postings and separate noncash purchase events through month 60."""

    month: int
    contractual_payment: BRLMoney
    waiting_housing_cost: BRLMoney
    cash_top_up: BRLMoney
    cash_outflow: BRLMoney
    transferred_credit_right: BRLMoney
    credit_letter_applied: BRLMoney


@dataclass(frozen=True, slots=True)
class ConsortiumV1Result:
    scenario_kind: ConsortiumScenarioKind
    contemplation_month: int
    contractual_schedule: tuple[ConsortiumContractualRow, ...]
    monthly_postings: tuple[ConsortiumMonthlyRow, ...]
    comparison_ledger: tuple[ComparisonLedgerRow, ...]
