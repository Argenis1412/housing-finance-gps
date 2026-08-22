"""HTTP-only request and response resource limits for the public projection."""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.error_mapping import PublicApiError, error_response


MAX_REQUEST_BYTES = 8_192
MAX_RESPONSE_BYTES = 262_144


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
        while True:
            message = await receive()
            if message["type"] != "http.request":
                await self.app(scope, receive, send)
                return
            body = message.get("body", b"")
            received_bytes += len(body)
            if received_bytes > MAX_REQUEST_BYTES:
                await error_response(413, "request_too_large")(scope, receive, send)
                return
            chunks.append(body)
            if not message.get("more_body", False):
                break

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
