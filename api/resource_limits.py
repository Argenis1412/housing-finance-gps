"""HTTP-only request and response resource limits for the public projection."""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.error_mapping import PublicApiError, comparison_error_response, error_response


MAX_REQUEST_BYTES = 8_192
MAX_RESPONSE_BYTES = 262_144
COMPARISON_MAX_REQUEST_BYTES = 1_048_576
COMPARISON_MAX_RESPONSE_BYTES = 4_194_304
COMPARISON_PATH = "/api/v1/comparison/simulations"


def is_comparison_request(method: str, path: str) -> bool:
    return method == "POST" and path in {COMPARISON_PATH, COMPARISON_PATH + "/"}


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _integer(value: str) -> int:
    number = int(value)
    if abs(number) > 9_007_199_254_740_991:
        raise ValueError("unsafe integer")
    return number


def _reject_number(_: str) -> object:
    raise ValueError("non-integer JSON number")


def _check_json(value: object, depth: int = 0) -> None:
    if depth > 64 or (depth == 64 and isinstance(value, (dict, list))):
        raise ValueError("JSON depth")
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif isinstance(value, dict):
        from typing import cast
        for key, child in cast(dict[str, object], value).items():
            _check_json(key, depth + 1)
            _check_json(child, depth + 1)
    elif isinstance(value, list):
        from typing import cast
        for child in cast(list[object], value):
            _check_json(child, depth + 1)


def _admit_comparison_json(body: bytes) -> None:
    value: object = json.loads(
        body.decode("utf-8"), object_pairs_hook=_pairs, parse_int=_integer,
        parse_float=_reject_number, parse_constant=_reject_number,
    )
    _check_json(value)


class RequestBodyLimitMiddleware:
    """Reject an oversized HTTP body while it is being received."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        received_bytes = 0
        comparison = is_comparison_request(scope["method"], scope["path"])
        respond = comparison_error_response if comparison else error_response
        limit = COMPARISON_MAX_REQUEST_BYTES if comparison else MAX_REQUEST_BYTES
        while True:
            message = await receive()
            if message["type"] != "http.request":
                await self.app(scope, receive, send)
                return
            body = message.get("body", b"")
            received_bytes += len(body)
            if received_bytes > limit:
                await respond(413, "request_too_large")(scope, receive, send)
                return
            chunks.append(body)
            if not message.get("more_body", False):
                break

        if comparison:
            try:
                _admit_comparison_json(b"".join(chunks))
            except (ValueError, UnicodeError, RecursionError):
                await respond(422, "invalid_input")(scope, receive, send)
                return
            except Exception:
                await respond(500, "internal_error")(scope, receive, send)
                return

        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {
                    "type": "http.request",
                    "body": b"".join(chunks),
                    "more_body": False,
                }
            return await receive()

        await self.app(scope, bounded_receive, send)


def bounded_success_response(payload: dict[str, object]):
    """Serialize once and reject a projection that exceeds its public byte budget."""
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_RESPONSE_BYTES:
        raise PublicApiError(status_code=422, code="invalid_input")
    from fastapi.responses import Response

    return Response(content=body, media_type="application/json")


def bounded_comparison_response(payload: dict[str, object]):
    from fastapi.responses import Response

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(body) > COMPARISON_MAX_RESPONSE_BYTES:
        return comparison_error_response(422, "response_too_large")
    return Response(content=body, media_type="application/json", headers={"Cache-Control": "no-store"})
