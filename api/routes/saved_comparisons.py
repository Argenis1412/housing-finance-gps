"""Explicit saved-comparison operations with serialization before commit."""

from collections.abc import Callable
import base64
import json
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import Response
from pydantic import ValidationError

from application.saved_comparisons import (
    ComparisonRepository, SavedComparisonError, delete_comparison,
    list_comparisons, read_comparison, save_comparison,
)
from api.error_mapping import comparison_error_response, public_message
from api import resource_limits
from api.schemas.comparison_v1 import ComparisonApiErrorV1
from api.schemas.saved_comparison_v1 import (
    IndexLocator, SavedComparisonCreationV1, SavedComparisonListV1, SavedComparisonV1,
)


router = APIRouter(prefix="/api/v1/comparison/saved-simulations")
_ERRORS: dict[int | str, dict[str, object]] = {status: {"model": ComparisonApiErrorV1} for status in (404, 409, 410, 413, 422, 500, 503)}


def _repository(request: Request) -> ComparisonRepository:
    return cast(ComparisonRepository, request.app.state.comparison_repository)


def _index_id(locator: str) -> str:
    if not locator.startswith("~"):
        return locator
    try:
        encoded = locator[1:]
        raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        if base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != encoded:
            raise ValueError("noncanonical locator")
        return raw.decode("utf-8")
    except ValueError:
        raise SavedComparisonError("invalid_input", 422) from None


def _bytes(payload: dict[str, object]) -> bytes:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(body) > resource_limits.COMPARISON_MAX_RESPONSE_BYTES:
        raise SavedComparisonError("response_too_large", 422)
    return body


def _prepare(payload: dict[str, object]) -> bytes:
    result = cast(dict[str, object], payload["result"])
    for alternative in cast(list[dict[str, object]], result["alternatives"]):
        if alternative["status"] == "domain_failure":
            failure = cast(dict[str, object], alternative["failure"])
            failure["message_pt_br"] = public_message(cast(str, failure["code"]))
    serialized = SavedComparisonV1.model_validate(payload).model_dump(mode="json")
    for alternative in serialized["result"]["alternatives"]:
        if alternative["status"] == "domain_failure":
            for key in ("month", "phase"):
                if alternative["failure"][key] is None:
                    del alternative["failure"][key]
    for child in serialized["result"]["children"]:
        if child["input_classification"] is None:
            del child["input_classification"]
    return _bytes(serialized)


def _response(body: bytes = b"", status: int = 200) -> Response:
    return Response(body, status_code=status, media_type="application/json" if status != 204 else None, headers={"Cache-Control": "no-store"})


def _safe(action: Callable[[], Response]) -> Response:
    try:
        return action()
    except SavedComparisonError as error:
        return comparison_error_response(error.status, error.code)
    except Exception:
        # Suppress input-bearing exception text before server logging middleware.
        return comparison_error_response(500, "internal_error")


@router.post("", response_model=SavedComparisonV1, status_code=201, responses={**_ERRORS, 200: {"model": SavedComparisonV1}}, summary="Compare once and save complete local synthetic evidence")
def create_saved(request: SavedComparisonCreationV1, repository: Annotated[ComparisonRepository, Depends(_repository)]) -> Response:
    def action() -> Response:
        prepared = save_comparison(repository, request.operation_id, request.comparison.model_dump(), _prepare)
        return _response(prepared.body, 201 if prepared.created else 200)
    return _safe(action)


@router.get("", response_model=SavedComparisonListV1, responses=_ERRORS, summary="List unverified saved-comparison index metadata")
def list_saved(
    repository: Annotated[ComparisonRepository, Depends(_repository)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=9_007_199_254_740_991)] = 0,
) -> Response:
    return _safe(lambda: _response(_bytes(SavedComparisonListV1.model_validate(list_comparisons(repository, limit, offset)).model_dump(mode="json"))))


@router.get("/{simulation_id}", response_model=SavedComparisonV1, responses=_ERRORS, summary="Read stored historical output without calculation or replay")
def read_saved(simulation_id: Annotated[IndexLocator, Path()], repository: Annotated[ComparisonRepository, Depends(_repository)]) -> Response:
    def action() -> Response:
        try:
            return _response(_prepare(read_comparison(repository, _index_id(simulation_id))))
        except (ValidationError, TypeError, KeyError, IndexError, AttributeError):
            raise SavedComparisonError("stored_simulation_corrupt", 500) from None
    return _safe(action)


@router.delete("/{simulation_id}", status_code=204, responses=_ERRORS, summary="Delete evidence while retaining its opaque operation ID")
def delete_saved(simulation_id: Annotated[IndexLocator, Path()], repository: Annotated[ComparisonRepository, Depends(_repository)]) -> Response:
    def action() -> Response:
        delete_comparison(repository, _index_id(simulation_id))
        return _response(status=204)
    return _safe(action)
