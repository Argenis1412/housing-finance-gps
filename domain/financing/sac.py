"""Pure, deterministic SAC calculation using shared financing contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import localcontext

from domain.financing.contracts import (
    ComparisonLedgerRow,
    FinancingContractualRow,
    FinancingRequest,
    NormalizedFinancingInput,
    build_financing_comparison_ledger,
    calculation_context,
    money,
    normalize_financing_request,
    post_decimal,
)
from domain.values import DomainFailure
from domain.financing.v2 import (
    FinancingV2Result,
    NormalizedV2FinancingInput,
    calculate_sac_v2 as _calculate_sac_v2,
    normalize_sac_request_v2 as _normalize_sac_request_v2,
)
from domain.financing.v3 import (
    FinancingV3Result,
    NormalizedV3FinancingInput,
    calculate_sac_v3 as _calculate_sac_v3,
    normalize_sac_request_v3 as _normalize_sac_request_v3,
)


SACRequest = FinancingRequest
NormalizedSACInput = NormalizedFinancingInput
SACContractualRow = FinancingContractualRow


@dataclass(frozen=True, slots=True)
class SACResult:
    """Immutable SAC output with shared schedule and ledger rows."""

    contractual_schedule: tuple[SACContractualRow, ...]
    comparison_ledger: tuple[ComparisonLedgerRow, ...]


def normalize_sac_request(request: SACRequest) -> NormalizedSACInput | DomainFailure:
    """Preserve the SAC entry point over the neutral financing boundary."""
    return normalize_financing_request(request)


def calculate_sac(input_value: NormalizedSACInput) -> SACResult:
    """Calculate SAC postings and the 60-month comparison ledger purely."""
    with localcontext(calculation_context(input_value)):
        schedule = _build_contractual_schedule(input_value)
        ledger = build_financing_comparison_ledger(input_value, schedule)
    return SACResult(contractual_schedule=schedule, comparison_ledger=ledger)


def normalize_sac_request_v2(request: SACRequest) -> NormalizedV2FinancingInput | DomainFailure:
    """Select SAC v2 explicitly before normalization."""
    return _normalize_sac_request_v2(request)


def calculate_sac_v2(input_value: NormalizedV2FinancingInput) -> FinancingV2Result:
    """Project the retained SAC v2 evaluator output."""
    return _calculate_sac_v2(input_value)


def normalize_sac_request_v3(request: SACRequest) -> NormalizedV3FinancingInput | DomainFailure:
    """Select SAC v3 explicitly before normalization."""
    return _normalize_sac_request_v3(request)


def calculate_sac_v3(input_value: NormalizedV3FinancingInput) -> FinancingV3Result:
    """Project the centavo-safe SAC v3 evaluator output."""
    return _calculate_sac_v3(input_value)


def _build_contractual_schedule(input_value: NormalizedSACInput) -> tuple[SACContractualRow, ...]:
    rows: list[SACContractualRow] = []
    opening = input_value.principal.amount
    regular_amortization = post_decimal(input_value.principal.amount / input_value.term_months)
    for month in range(1, input_value.term_months + 1):
        interest = post_decimal(opening * input_value.effective_monthly_rate.amount)
        amortization = opening if month == input_value.term_months else regular_amortization
        payment = post_decimal(interest + amortization)
        closing = post_decimal(opening - amortization)
        rows.append(
            SACContractualRow(
                month=month,
                opening_principal_balance=money(opening),
                interest=money(interest),
                amortization=money(amortization),
                payment=money(payment),
                closing_principal_balance=money(closing),
            )
        )
        opening = closing
    return tuple(rows)
