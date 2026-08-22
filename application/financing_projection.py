"""Application use case for the bounded v3 financing projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from domain.financing.contracts import FinancingRequest, IndexationDeclaration
from domain.financing.price import calculate_price_v3, normalize_price_request_v3
from domain.financing.sac import calculate_sac_v3, normalize_sac_request_v3
from domain.financing.v3 import FinancingV3Result
from domain.values import DomainFailure, FailureCode


Strategy = Literal["sac", "price"]


@dataclass(frozen=True, slots=True)
class FinancingProjectionInput:
    """Transport-independent input accepted by the financing projection use case."""

    comparison_opening_cash: str
    property_price: str
    cash_down_payment: str
    principal: str
    term_months: int
    rate_value: str
    rate_convention: str
    fgts_amount: str | None
    subsidy_amount: str | None
    tax_amount: str | None
    transaction_cost_amount: str | None
    fee_amount: str | None
    insurance_amount: str | None
    indexation: IndexationDeclaration
    extraordinary_amortization_amount: str | None


@dataclass(frozen=True, slots=True)
class ApplicationFailure:
    """Stable domain failure category exposed to the HTTP adapter without detail."""

    code: FailureCode


def calculate_v3_financing_projection(
    *, strategy: Strategy, input_value: FinancingProjectionInput
) -> FinancingV3Result | ApplicationFailure:
    """Select v3 before normalization and return only its pure domain projection."""
    request = FinancingRequest(
        comparison_opening_cash=input_value.comparison_opening_cash,
        property_price=input_value.property_price,
        cash_down_payment=input_value.cash_down_payment,
        principal=input_value.principal,
        term_months=input_value.term_months,
        rate_value=input_value.rate_value,
        rate_convention=input_value.rate_convention,
        fgts_amount=input_value.fgts_amount,
        subsidy_amount=input_value.subsidy_amount,
        tax_amount=input_value.tax_amount,
        transaction_cost_amount=input_value.transaction_cost_amount,
        fee_amount=input_value.fee_amount,
        insurance_amount=input_value.insurance_amount,
        indexation=input_value.indexation,
        extraordinary_amortization_amount=input_value.extraordinary_amortization_amount,
    )
    if strategy == "sac":
        normalized = normalize_sac_request_v3(request)
        if isinstance(normalized, DomainFailure):
            return ApplicationFailure(code=normalized.code)
        result = calculate_sac_v3(normalized)
    elif strategy == "price":
        normalized = normalize_price_request_v3(request)
        if isinstance(normalized, DomainFailure):
            return ApplicationFailure(code=normalized.code)
        result = calculate_price_v3(normalized)
    else:
        return ApplicationFailure(code="invalid_input")
    return result
