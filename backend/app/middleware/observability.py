import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()

        logger_ctx = logging.LoggerAdapter(logger, {"request_id": request_id})

        try:
            response = await call_next(request)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger_ctx.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger_ctx.info(
            f"{request.method} {request.url.path}",
            extra={
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        response.headers["X-Request-ID"] = request_id
        return response
