"""Public HTTP error mapping for the v1 financing projection."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from application.financing_projection import ApplicationFailure
from api.schemas.financing_v1 import ApiErrorV1


_MESSAGES = {
    "invalid_input": "Os dados informados são inválidos.",
    "unsupported_rate_convention": "A convenção de taxa informada não é suportada.",
    "unsupported_rule": "A regra solicitada não é suportada.",
    "unsupported_contract_clause": "A cláusula contratual solicitada não é suportada.",
    "infeasible_scenario": "O cenário informado não é viável.",
    "incompatible_contract_version": "A versão contratual informada é incompatível.",
    "request_too_large": "A solicitação excede o limite de tamanho da API.",
    "internal_error": "Ocorreu um erro interno ao processar a solicitação.",
}


class PublicApiError(Exception):
    """A deliberately small public error independent of domain diagnostic text."""

    def __init__(self, *, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code


def public_error_from_application(failure: ApplicationFailure) -> PublicApiError:
    """Map only the application failure category to its public HTTP contract."""
    if failure.code == "incompatible_contract_version":
        return PublicApiError(status_code=409, code=failure.code)
    return PublicApiError(status_code=422, code=failure.code)


def error_response(status_code: int, code: str) -> JSONResponse:
    """Render the versioned safe public error schema."""
    payload = ApiErrorV1(code=code, message_pt_br=_MESSAGES[code])
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))
