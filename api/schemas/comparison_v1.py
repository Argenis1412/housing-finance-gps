"""Comparison transport admits raw semantics; retained v2 owns validation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


type ClosedJsonValue = dict[str, ClosedJsonValue] | list[ClosedJsonValue] | str | int | bool | None
type MoneyOutput = Annotated[str, StringConstraints(pattern=r"^-?(?:0|[1-9][0-9]*)\.[0-9]{2}$")]
type Strategy = Literal["sac", "price", "rent", "consortium"]
type FailureCategory = Literal[
    "invalid_input", "unsupported_rate_convention", "unsupported_rule",
    "unsupported_contract_clause", "infeasible_scenario", "incompatible_contract_version",
]


class ComparisonInputsV1(BaseModel):
    """Six v2 fields, without coercion or premature child/global validation.

    Expected shapes are defined by comparison-application-api-ui-v1.md and the
    retained monthly-resources contract. Malformed child values intentionally
    reach the domain so other alternatives can still be compared.
    """

    model_config = ConfigDict(extra="forbid", strict=True)
    shared: ClosedJsonValue
    constraints: ClosedJsonValue
    financing: ClosedJsonValue
    rent: ClosedJsonValue
    consortium: ClosedJsonValue
    monthly_resources: ClosedJsonValue


class ComparisonCreationRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    comparison: ComparisonInputsV1


class ComparisonApiErrorV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    api_version: Literal["v1"] = "v1"
    code: str
    message_pt_br: str


class ResourceComponentV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    component_id: str
    amount: MoneyOutput
    classification: Literal["observed_data", "projected_assumption"]
    source_reference: str
    source_as_of: str
    assumption_reference: str | None


class NormalizedResourceMonthV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    month: int
    income_components: list[ResourceComponentV1]
    external_expenses: list[ResourceComponentV1]
    income_total: MoneyOutput
    external_expense_total: MoneyOutput
    available_resources: MoneyOutput


class NormalizedResourcesV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    income_basis: Literal["net_before_household_expenses"]
    expense_scope: Literal["strategy_independent_excluding_strategy_flows_and_netted_deductions"]
    months: Annotated[list[NormalizedResourceMonthV1], Field(min_length=60, max_length=60)]


class NormalizedComparisonV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    shared: dict[str, ClosedJsonValue]
    constraints: dict[str, MoneyOutput]
    monthly_resources: NormalizedResourcesV1
    rule_conventions: dict[str, ClosedJsonValue]
    input_classification: dict[str, ClosedJsonValue]


class ComparisonLedgerV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    month: int
    cash: MoneyOutput
    liquid_financial_assets: MoneyOutput
    consortium_credit_right_balance: MoneyOutput
    property_value: MoneyOutput
    financing_principal_balance: MoneyOutput
    consortium_credit_obligation_balance: MoneyOutput
    recoverable_transfer: MoneyOutput
    nonrecoverable_housing_cost: MoneyOutput
    total_liabilities: MoneyOutput
    home_equity: MoneyOutput
    liquidity: MoneyOutput
    net_worth: MoneyOutput
    cumulative_housing_cost: MoneyOutput


class ComparisonMetricsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    final_ledger_row: ComparisonLedgerV1
    minimum_liquidity: MoneyOutput
    minimum_liquidity_months: list[int]
    maximum_monthly_housing_outflow: MoneyOutput
    maximum_monthly_housing_outflow_months: list[int]


class ComparisonViolationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    constraint: Literal["cash_nonnegative", "minimum_liquidity", "maximum_monthly_housing_outflow"]
    month: int
    actual: MoneyOutput
    threshold: MoneyOutput


class ComparisonFailureV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    code: FailureCategory
    message_pt_br: str
    month: int | None = None
    phase: Literal["opening_allocation", "external_expenses", "strategy_obligations", "investment_contribution"] | None = None


class FailedAlternativeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    strategy: Strategy
    status: Literal["domain_failure"]
    failure: ComparisonFailureV1


class CompleteAlternativeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    strategy: Strategy
    status: Literal["eligible", "constraint_infeasible"]
    metrics: ComparisonMetricsV1
    violations: list[ComparisonViolationV1]
    comparison_ledger: Annotated[list[ComparisonLedgerV1], Field(min_length=61, max_length=61)]
    monthly_housing_outflows: Annotated[list[MoneyOutput], Field(min_length=60, max_length=60)]


class ChildVersionsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    contract_schema_version: str
    engine_version: str
    ruleset_version: str


class ComparisonChildV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    strategy: Strategy
    versions: ChildVersionsV1
    input_classification: dict[str, str] | None = None


class ComparisonSimulationResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    api_version: Literal["v1"]
    kind: Literal["simulation_result"]
    contract_schema_version: Literal["comparison-simulation-v2"]
    engine_version: Literal["comparison-monthly-resources-v2"]
    ruleset_version: Literal["comparison-ruleset-v2"]
    data_snapshot_id: str
    calculated_at: str
    timezone: Literal["America/Sao_Paulo"]
    declared_inputs: ComparisonInputsV1
    normalized_input: NormalizedComparisonV1
    children: Annotated[list[ComparisonChildV1], Field(min_length=4, max_length=4)]
    alternatives: Annotated[list[Annotated[FailedAlternativeV1 | CompleteAlternativeV1, Field(discriminator="status")]], Field(min_length=4, max_length=4)]
    status: Literal["compared", "single_eligible", "no_eligible"]
    objective: Literal["maximize_net_worth_at_month_60"]
    ranking_groups: list[list[Strategy]]
    limitations: list[str]
