"""Public HTTP error mapping for the v1 financing projection."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from application.financing_projection import ApplicationFailure
from api.schemas.financing_v1 import ApiErrorV1
from api.schemas.comparison_v1 import ComparisonApiErrorV1


_MESSAGES = {
    "simulation_not_found": "A comparação salva não foi encontrada.",
    "simulation_deleted": "Esta comparação foi excluída e não será recriada por uma nova tentativa.",
    "operation_id_conflict": "Esta operação já foi usada com outras declarações.",
    "incompatible_storage_version": "A versão do armazenamento não é suportada.",
    "stored_simulation_corrupt": "A integridade do registro salvo não pôde ser confirmada.",
    "evidence_too_large": "A evidência completa excede o limite de armazenamento.",
    "storage_not_configured": "Configure o banco local para usar comparações salvas.",
    "storage_not_initialized": "Inicialize o banco local com o comando de migração.",
    "storage_busy": "O banco local está ocupado. Tente novamente.",
    "storage_unavailable": "O banco local está indisponível. Verifique sua configuração e tente novamente.",
    "invalid_input": "Os dados informados são inválidos.",
    "unsupported_rate_convention": "A convenção de taxa informada não é suportada.",
    "unsupported_rule": "A regra solicitada não é suportada.",
    "unsupported_contract_clause": "A cláusula contratual solicitada não é suportada.",
    "infeasible_scenario": "O cenário informado não é viável.",
    "incompatible_contract_version": "A versão contratual informada é incompatível.",
    "request_too_large": "A solicitação excede o limite de tamanho da API.",
    "internal_error": "Ocorreu um erro interno ao processar a solicitação.",
    "response_too_large": "O resultado excede o limite de tamanho. Reduza as declarações e revise novamente.",
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


def public_message(code: str) -> str:
    """Use only fixed messages, never retained diagnostic text."""
    return _MESSAGES.get(code, _MESSAGES["internal_error"])


def comparison_error_response(status_code: int, code: str) -> JSONResponse:
    payload = ComparisonApiErrorV1(code=code, message_pt_br=public_message(code))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
