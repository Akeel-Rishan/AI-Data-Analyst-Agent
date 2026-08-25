"""HTTP request and response logging middleware."""

from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.utils.logger import get_logger


logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request timing and attach a short request identifier."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process one request while recording identifiers and elapsed time."""
        request_id = uuid4().hex[:8]
        skip_logging = request.url.path.startswith("/health")

        if not skip_logging:
            logger.info(
                "→ %s %s | request_id=%s",
                request.method,
                request.url.path,
                request_id,
            )

        started_at = perf_counter()
        response = await call_next(request)
        elapsed_ms = (perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id

        if not skip_logging:
            logger.info(
                "← %s %s %s | %.2fms | request_id=%s",
                response.status_code,
                request.method,
                request.url.path,
                elapsed_ms,
                request_id,
            )

        return response
