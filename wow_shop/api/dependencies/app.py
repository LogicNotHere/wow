from __future__ import annotations

import logging
from uuid import uuid4
from typing import Annotated

from fastapi import Header, Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
log = logging.getLogger("wow_shop.request")


async def handle_request_id(
    request: Request,
    response: Response,
    request_id: Annotated[str | None, Header(alias=REQUEST_ID_HEADER)] = None,
) -> str:
    resolved_request_id = request_id.strip() if request_id else str(uuid4())
    request.state.request_id = resolved_request_id
    response.headers[REQUEST_ID_HEADER] = resolved_request_id
    return resolved_request_id


async def log_request(request: Request) -> None:
    request_id = getattr(request.state, "request_id", "missing")
    log.info(
        "request received: method=%s path=%s request_id=%s",
        request.method,
        request.url.path,
        request_id,
    )
