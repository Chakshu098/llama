"""
server/middleware.py — Request logging, timing, and basic rate limiting.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        t0 = time.perf_counter()

        response = await call_next(request)

        duration_ms = int((time.perf_counter() - t0) * 1000)
        print(
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration_ms}ms)",
            flush=True,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Duration-Ms"] = str(duration_ms)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter per IP.
    Allows MAX_REQUESTS per WINDOW_SECONDS.
    Exempt: /health, /tasks (read-only, low cost).
    """

    MAX_REQUESTS = 120      # per window
    WINDOW_SECONDS = 60

    EXEMPT_PATHS = {"/health", "/tasks"}

    def __init__(self, app):
        super().__init__(app)
        self._counters: dict = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Slide window
        self._counters[client_ip] = [
            t for t in self._counters[client_ip]
            if now - t < self.WINDOW_SECONDS
        ]

        if len(self._counters[client_ip]) >= self.MAX_REQUESTS:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded: {self.MAX_REQUESTS} requests per {self.WINDOW_SECONDS}s"
                },
            )

        self._counters[client_ip].append(now)
        return await call_next(request)
