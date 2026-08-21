"""Explicit v3 live-financing projections over the centavo-safe authority."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Literal

from domain.financing import replay_v3
from domain.financing.contracts import FinancingRequest
from domain.ledger import ComparisonLedgerRow
from domain.values import BRLMoney, DomainFailure


Strategy = Literal["sac", "price"]


@dataclass(frozen=True, slots=True)
class NormalizedV3FinancingInput:
    """Canonical v3 request selected before any financial normalization."""

    raw_request_jcs: str
    strategy: Strategy


@dataclass(frozen=True, slots=True)
class FinancingV3ContractualRow:
    """One v3 posted schedule row, including the fixed monthly fee."""

    month: int
    opening_principal_balance: BRLMoney
    interest: BRLMoney
    amortization: BRLMoney
    fee: BRLMoney
    payment: BRLMoney
    closing_principal_balance: BRLMoney


@dataclass(frozen=True, slots=True)
class FinancingV3Result:
    """Immutable v3 result projected from the canonical evaluator trace."""

    contractual_schedule: tuple[FinancingV3ContractualRow, ...]
    comparison_ledger: tuple[ComparisonLedgerRow, ...]


def normalize_sac_request_v3(request: FinancingRequest) -> NormalizedV3FinancingInput | DomainFailure:
    """Select and normalize a SAC v3 request explicitly."""
    return _normalize(request, "sac")


def normalize_price_request_v3(request: FinancingRequest) -> NormalizedV3FinancingInput | DomainFailure:
    """Select and normalize a Price v3 request explicitly."""
    return _normalize(request, "price")


def calculate_sac_v3(input_value: NormalizedV3FinancingInput) -> FinancingV3Result:
    """Project the canonical v3 SAC outcome without duplicate formulas."""
    return _calculate(input_value, "sac")


def calculate_price_v3(input_value: NormalizedV3FinancingInput) -> FinancingV3Result:
    """Project the canonical v3 Price outcome without duplicate formulas."""
    return _calculate(input_value, "price")


def _normalize(request: FinancingRequest, strategy: Strategy) -> NormalizedV3FinancingInput | DomainFailure:
    try:
        raw_request_jcs = replay_v3.canonical_json(asdict(request))
        outcome = json.loads(replay_v3.evaluate(raw_request_jcs, strategy))
    except (TypeError, ValueError):
        return DomainFailure("invalid_input", "v3 financing request is invalid")
    if outcome["kind"] == "failure":
        return DomainFailure(outcome["code"], outcome["detail"])
    return NormalizedV3FinancingInput(raw_request_jcs=raw_request_jcs, strategy=strategy)


def _calculate(input_value: NormalizedV3FinancingInput, strategy: Strategy) -> FinancingV3Result:
    if type(input_value) is not NormalizedV3FinancingInput:
        raise ValueError("v3 calculation requires a v3 normalized input")
    if input_value.strategy != strategy:
        raise ValueError("v3 normalized input strategy does not match calculator")
    outcome = json.loads(replay_v3.evaluate(input_value.raw_request_jcs, strategy))
    if outcome["kind"] != "success":
        raise ValueError("v3 normalized input no longer produces a successful outcome")
    trace = outcome["trace"]
    schedule = tuple(
        FinancingV3ContractualRow(
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
    return FinancingV3Result(contractual_schedule=schedule, comparison_ledger=ledger)
