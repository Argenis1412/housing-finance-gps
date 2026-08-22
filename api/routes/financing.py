"""The sole v1 financing-calculation projection route."""

from __future__ import annotations

from fastapi import APIRouter

from application.financing_projection import (
    ApplicationFailure,
    FinancingProjectionInput,
    calculate_v3_financing_projection,
)
from api.error_mapping import public_error_from_application
from api.resource_limits import bounded_success_response
from api.schemas.financing_v1 import (
    ApiErrorV1,
    CalculationProjectionV1,
    ComparisonLedgerRowV1,
    ContractualScheduleRowV1,
    FinancingCalculationRequestV1,
)


router = APIRouter()
_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    409: {"model": ApiErrorV1},
    413: {"model": ApiErrorV1},
    422: {"model": ApiErrorV1},
    500: {"model": ApiErrorV1},
}


@router.post(
    "/api/v1/financing/calculations",
    response_model=CalculationProjectionV1,
    responses=_ERROR_RESPONSES,
    summary="Calculate an ephemeral v3 financing projection",
    description=(
        "Returns a non-persistent calculation projection. It is not a "
        "simulation result and contains no data snapshot, canonical request, "
        "sealed outcome, timestamp, or replay claim."
    ),
)
async def calculate_financing_projection(
    request: FinancingCalculationRequestV1,
):
    """Project one selected v3 financing strategy without public replay semantics."""
    financing = request.financing
    projection_or_failure = calculate_v3_financing_projection(
        strategy=request.strategy,
        input_value=FinancingProjectionInput(
            comparison_opening_cash=financing.comparison_opening_cash,
            property_price=financing.property_price,
            cash_down_payment=financing.cash_down_payment,
            principal=financing.principal,
            term_months=financing.term_months,
            rate_value=financing.rate_value,
            rate_convention=financing.rate_convention,
            fgts_amount=financing.fgts_amount,
            subsidy_amount=financing.subsidy_amount,
            tax_amount=financing.tax_amount,
            transaction_cost_amount=financing.transaction_cost_amount,
            fee_amount=financing.fee_amount,
            insurance_amount=financing.insurance_amount,
            indexation=financing.indexation,
            extraordinary_amortization_amount=financing.extraordinary_amortization_amount,
        ),
    )
    if isinstance(projection_or_failure, ApplicationFailure):
        raise public_error_from_application(projection_or_failure)

    result = projection_or_failure
    response_model = CalculationProjectionV1(
        api_version="v1",
        strategy=request.strategy,
        contract_schema_version="financing-replay-v3",
        engine_version="financing-centavo-safe-v3",
        ruleset_version="financing-ruleset-v2",
        contractual_schedule=[
            ContractualScheduleRowV1(
                month=row.month,
                opening_principal_balance=row.opening_principal_balance.as_string,
                interest=row.interest.as_string,
                amortization=row.amortization.as_string,
                fee=row.fee.as_string,
                payment=row.payment.as_string,
                closing_principal_balance=row.closing_principal_balance.as_string,
            )
            for row in result.contractual_schedule
        ],
        comparison_ledger=[
            ComparisonLedgerRowV1(
                month=row.month,
                cash=row.cash.as_string,
                liquid_financial_assets=row.liquid_financial_assets.as_string,
                consortium_credit_right_balance=row.consortium_credit_right_balance.as_string,
                property_value=row.property_value.as_string,
                financing_principal_balance=row.financing_principal_balance.as_string,
                consortium_credit_obligation_balance=row.consortium_credit_obligation_balance.as_string,
                recoverable_transfer=row.recoverable_transfer.as_string,
                nonrecoverable_housing_cost=row.nonrecoverable_housing_cost.as_string,
                total_liabilities=row.total_liabilities.as_string,
                home_equity=row.home_equity.as_string,
                liquidity=row.liquidity.as_string,
                net_worth=row.net_worth.as_string,
                cumulative_housing_cost=row.cumulative_housing_cost.as_string,
            )
            for row in result.comparison_ledger
        ],
    )
    return bounded_success_response(response_model.model_dump(mode="json"))
