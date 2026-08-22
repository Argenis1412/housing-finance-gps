"""Public v1 schemas for ephemeral financing calculation projections."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


BRLInput = Annotated[
    str,
    StringConstraints(pattern=r"^[+-]?\d{1,18}\.\d{2}$"),
]
RateInput = Annotated[
    str,
    StringConstraints(pattern=r"^(?:0(?:\.\d{1,12})?|1(?:\.0{1,12})?)$"),
]
BRLOutput = Annotated[
    str,
    StringConstraints(pattern=r"^[+-]?\d{1,22}\.\d{2}$"),
]


class FinancingInputV1(BaseModel):
    """HTTP-admitted financing fields; financial semantics remain in the domain."""

    model_config = ConfigDict(extra="forbid", strict=True)

    comparison_opening_cash: BRLInput
    property_price: BRLInput
    cash_down_payment: BRLInput
    principal: BRLInput
    term_months: Annotated[int, Field(ge=1, le=600, strict=True)]
    rate_value: RateInput
    rate_convention: Annotated[str, Field(min_length=1, max_length=64, strict=True)]
    fgts_amount: BRLInput | None = None
    subsidy_amount: BRLInput | None = None
    tax_amount: BRLInput | None = None
    transaction_cost_amount: BRLInput | None = None
    fee_amount: BRLInput | None = None
    insurance_amount: BRLInput | None = None
    indexation: Literal["not_requested", "documented_zero", "requested_nonzero"] = "not_requested"
    extraordinary_amortization_amount: BRLInput | None = None


class FinancingCalculationRequestV1(BaseModel):
    """Request for one non-persistent, explicitly v3 financing projection."""

    model_config = ConfigDict(extra="forbid", strict=True)

    strategy: Literal["sac", "price"]
    financing: FinancingInputV1


class ContractualScheduleRowV1(BaseModel):
    """One v3 contractual schedule posting."""

    model_config = ConfigDict(extra="forbid", strict=True)

    month: int
    opening_principal_balance: BRLOutput
    interest: BRLOutput
    amortization: BRLOutput
    fee: BRLOutput
    payment: BRLOutput
    closing_principal_balance: BRLOutput


class ComparisonLedgerRowV1(BaseModel):
    """One neutral common ledger row for the month 0..60 comparison timeline."""

    model_config = ConfigDict(extra="forbid", strict=True)

    month: int
    cash: BRLOutput
    liquid_financial_assets: BRLOutput
    consortium_credit_right_balance: BRLOutput
    property_value: BRLOutput
    financing_principal_balance: BRLOutput
    consortium_credit_obligation_balance: BRLOutput
    recoverable_transfer: BRLOutput
    nonrecoverable_housing_cost: BRLOutput
    total_liabilities: BRLOutput
    home_equity: BRLOutput
    liquidity: BRLOutput
    net_worth: BRLOutput
    cumulative_housing_cost: BRLOutput


class CalculationProjectionV1(BaseModel):
    """Versioned ephemeral calculation projection, distinct from a simulation result."""

    model_config = ConfigDict(extra="forbid", strict=True)

    api_version: Literal["v1"]
    strategy: Literal["sac", "price"]
    contract_schema_version: Literal["financing-replay-v3"]
    engine_version: Literal["financing-centavo-safe-v3"]
    ruleset_version: Literal["financing-ruleset-v2"]
    contractual_schedule: list[ContractualScheduleRowV1]
    comparison_ledger: list[ComparisonLedgerRowV1]


class ApiErrorV1(BaseModel):
    """Stable public error without internal domain diagnostic text."""

    model_config = ConfigDict(extra="forbid", strict=True)

    code: str
    message_pt_br: str
