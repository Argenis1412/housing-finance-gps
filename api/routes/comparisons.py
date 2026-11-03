"""Explicit comparison creation, separate from the financing projection."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter

from application.comparison_simulation import ComparisonApplicationFailure, create_comparison_simulation
from api.error_mapping import comparison_error_response, public_message
from api.resource_limits import bounded_comparison_response
from api.schemas.comparison_v1 import ComparisonApiErrorV1, ComparisonCreationRequestV1, ComparisonSimulationResultV1


router = APIRouter()


@router.post(
    "/api/v1/comparison/simulations",
    response_model=ComparisonSimulationResultV1,
    responses={status: {"model": ComparisonApiErrorV1} for status in (413, 422, 500)},
    summary="Create a transient synthetic comparison v2 simulation",
    description="Creates sealed evidence internally. No persistence, retrieval, export or HTTP replay. Only rent invests.",
)
def create_simulation(request: ComparisonCreationRequestV1):
    try:
        result = create_comparison_simulation(request.comparison.model_dump())
        if isinstance(result, ComparisonApplicationFailure):
            return comparison_error_response(422, result.code)
        for alternative in cast(list[dict[str, object]], result["alternatives"]):
            if alternative["status"] == "domain_failure":
                failure = cast(dict[str, object], alternative["failure"])
                failure["message_pt_br"] = public_message(cast(str, failure["code"]))
        payload = ComparisonSimulationResultV1.model_validate(result)
        serialized = payload.model_dump(mode="json")
        # Preserve required null provenance fields. Only optional presentation
        # fields are omitted; recursive exclude_none would corrupt the profile.
        for alternative in serialized["alternatives"]:
            if alternative["status"] == "domain_failure":
                for key in ("month", "phase"):
                    if alternative["failure"][key] is None:
                        del alternative["failure"][key]
        for child in serialized["children"]:
            if child["input_classification"] is None:
                del child["input_classification"]
        return bounded_comparison_response(serialized)
    except Exception:
        # Handle before server error middleware can log an exception containing
        # financial inputs. An execution bug must never become an exclusion.
        return comparison_error_response(500, "internal_error")
