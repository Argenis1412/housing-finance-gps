"""Thin immutable live projections over the retained consortium v1 authority."""

from dataclasses import asdict
import json

from domain.consortium import replay_v1
from domain.consortium.contracts import (
    ConsortiumContractualRow,
    ConsortiumMonthlyRow,
    ConsortiumRequest,
    ConsortiumV1Result,
    NormalizedConsortiumV1Input,
)
from domain.ledger import ComparisonLedgerRow
from domain.values import BRLMoney, DomainFailure


def normalize_consortium_request_v1(request: ConsortiumRequest) -> NormalizedConsortiumV1Input | DomainFailure:
    try:
        # Convert immutable input tuples into the codec's closed JSON arrays.
        raw = replay_v1.canonical_json(json.loads(json.dumps(asdict(request), allow_nan=False)))
        outcome = json.loads(replay_v1.evaluate(raw))
    except (TypeError, ValueError):
        return DomainFailure("invalid_input", "consortium request representation is invalid")
    if outcome["kind"] == "failure":
        return DomainFailure(outcome["code"], outcome["detail"])
    return NormalizedConsortiumV1Input(raw)


def calculate_consortium_v1(input_value: NormalizedConsortiumV1Input) -> ConsortiumV1Result:
    if type(input_value) is not NormalizedConsortiumV1Input:
        raise ValueError("consortium calculation requires a v1 normalized input")
    outcome = json.loads(replay_v1.evaluate(input_value.raw_request_jcs))
    if outcome["kind"] != "success":
        raise ValueError("normalized consortium input no longer produces a success")
    trace = outcome["trace"]
    schedule = tuple(ConsortiumContractualRow(
        month=row["month"], credit_component=BRLMoney(row["credit_component"]),
        administration_fee=BRLMoney(row["administration_fee"]), reserve_fund=BRLMoney(row["reserve_fund"]),
        insurance=BRLMoney(row["insurance"]), payment=BRLMoney(row["payment"]),
    ) for row in trace["contractual_schedule"])
    postings = tuple(ConsortiumMonthlyRow(
        month=row["month"], contractual_payment=BRLMoney(row["contractual_payment"]),
        waiting_housing_cost=BRLMoney(row["waiting_housing_cost"]), cash_top_up=BRLMoney(row["cash_top_up"]),
        cash_outflow=BRLMoney(row["cash_outflow"]), transferred_credit_right=BRLMoney(row["transferred_credit_right"]),
        credit_letter_applied=BRLMoney(row["credit_letter_applied"]),
    ) for row in trace["monthly_postings"])
    ledger = tuple(ComparisonLedgerRow(
        month=row["month"], cash=BRLMoney(row["cash"]), liquid_financial_assets=BRLMoney(row["liquid_financial_assets"]),
        consortium_credit_right_balance=BRLMoney(row["consortium_credit_right_balance"]),
        property_value=BRLMoney(row["property_value"]), financing_principal_balance=BRLMoney(row["financing_principal_balance"]),
        consortium_credit_obligation_balance=BRLMoney(row["consortium_credit_obligation_balance"]),
        recoverable_transfer=BRLMoney(row["recoverable_transfer"]), nonrecoverable_housing_cost=BRLMoney(row["nonrecoverable_housing_cost"]),
        total_liabilities=BRLMoney(row["total_liabilities"]), home_equity=BRLMoney(row["home_equity"]),
        liquidity=BRLMoney(row["liquidity"]), net_worth=BRLMoney(row["net_worth"]),
        cumulative_housing_cost=BRLMoney(row["cumulative_housing_cost"]),
    ) for row in trace["comparison_ledger"])
    normalized = outcome["normalized_input"]
    return ConsortiumV1Result(normalized["scenario_kind"], normalized["contemplation_month"], schedule, postings, ledger)
