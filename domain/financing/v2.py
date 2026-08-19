"""Explicit v2 live-financing projections over the retained v2 authority."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Literal

from domain.financing import replay_v2
from domain.financing.contracts import FinancingRequest
from domain.ledger import ComparisonLedgerRow
from domain.values import BRLMoney, DomainFailure


Strategy = Literal["sac", "price"]


@dataclass(frozen=True, slots=True)
class NormalizedV2FinancingInput:
    """Canonical v2 request selected before any financial normalization."""

    raw_request_jcs: str
    strategy: Strategy


@dataclass(frozen=True, slots=True)
class FinancingV2ContractualRow:
    """One v2 posted schedule row, including the fixed monthly fee."""

    month: int
    opening_principal_balance: BRLMoney
    interest: BRLMoney
    amortization: BRLMoney
    fee: BRLMoney
    payment: BRLMoney
    closing_principal_balance: BRLMoney


@dataclass(frozen=True, slots=True)
class FinancingV2Result:
    """Immutable v2 result projected from the canonical evaluator trace."""

    contractual_schedule: tuple[FinancingV2ContractualRow, ...]
    comparison_ledger: tuple[ComparisonLedgerRow, ...]


def normalize_sac_request_v2(request: FinancingRequest) -> NormalizedV2FinancingInput | DomainFailure:
    """Select and normalize a SAC v2 request explicitly."""
    return _normalize(request, "sac")


def normalize_price_request_v2(request: FinancingRequest) -> NormalizedV2FinancingInput | DomainFailure:
    """Select and normalize a Price v2 request explicitly."""
    return _normalize(request, "price")


def calculate_sac_v2(input_value: NormalizedV2FinancingInput) -> FinancingV2Result:
    """Project the canonical v2 SAC outcome without new financial formulas."""
    return _calculate(input_value, "sac")


def calculate_price_v2(input_value: NormalizedV2FinancingInput) -> FinancingV2Result:
    """Project the canonical v2 Price outcome without new financial formulas."""
    return _calculate(input_value, "price")


def _normalize(request: FinancingRequest, strategy: Strategy) -> NormalizedV2FinancingInput | DomainFailure:
    try:
        raw_request_jcs = replay_v2.canonical_json(asdict(request))
        outcome = json.loads(replay_v2.evaluate(raw_request_jcs, strategy))
    except (TypeError, ValueError):
        return DomainFailure("invalid_input", "v2 financing request is invalid")
    if outcome["kind"] == "failure":
        return DomainFailure(outcome["code"], outcome["detail"])
    return NormalizedV2FinancingInput(raw_request_jcs=raw_request_jcs, strategy=strategy)


def _calculate(input_value: NormalizedV2FinancingInput, strategy: Strategy) -> FinancingV2Result:
    if input_value.strategy != strategy:
        raise ValueError("v2 normalized input strategy does not match calculator")
    outcome = json.loads(replay_v2.evaluate(input_value.raw_request_jcs, strategy))
    if outcome["kind"] != "success":
        raise ValueError("v2 normalized input no longer produces a successful outcome")
    trace = outcome["trace"]
    schedule = tuple(
        FinancingV2ContractualRow(
            month=row["month"],
            opening_principal_balance=BRLMoney(row["opening_principal_balance"]),
            interest=BRLMoney(row["interest"]),
            amortization=BRLMoney(row["amortization"]),
            fee=BRLMoney(row["fee"]),
            payment=BRLMoney(row["payment"]),
            closing_principal_balance=BRLMoney(row["closing_principal_balance"]),
        )
        for row in trace["contractual_schedule"]
    )
    ledger = tuple(
        ComparisonLedgerRow(
            month=row["month"],
            cash=BRLMoney(row["cash"]),
            liquid_financial_assets=BRLMoney(row["liquid_financial_assets"]),
            consortium_credit_right_balance=BRLMoney(row["consortium_credit_right_balance"]),
            property_value=BRLMoney(row["property_value"]),
            financing_principal_balance=BRLMoney(row["financing_principal_balance"]),
            consortium_credit_obligation_balance=BRLMoney(row["consortium_credit_obligation_balance"]),
            recoverable_transfer=BRLMoney(row["recoverable_transfer"]),
            nonrecoverable_housing_cost=BRLMoney(row["nonrecoverable_housing_cost"]),
            total_liabilities=BRLMoney(row["total_liabilities"]),
            home_equity=BRLMoney(row["home_equity"]),
            liquidity=BRLMoney(row["liquidity"]),
            net_worth=BRLMoney(row["net_worth"]),
            cumulative_housing_cost=BRLMoney(row["cumulative_housing_cost"]),
        )
        for row in trace["comparison_ledger"]
    )
    return FinancingV2Result(contractual_schedule=schedule, comparison_ledger=ledger)
