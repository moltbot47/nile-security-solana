"""Prometheus-compatible metrics middleware."""

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response


class _Metrics:
    """In-process metrics collector exposed via /metrics endpoint."""

    def __init__(self) -> None:
        self.request_count: dict[str, int] = defaultdict(int)
        self.request_duration_sum: dict[str, float] = defaultdict(float)
        self.request_duration_count: dict[str, int] = defaultdict(int)
        self.status_count: dict[int, int] = defaultdict(int)
        self.scan_count: int = 0
        self.scan_duration_sum: float = 0.0

    def record(self, method: str, path: str, status: int, duration: float) -> None:
        key = f"{method} {path}"
        self.request_count[key] += 1
        self.request_duration_sum[key] += duration
        self.request_duration_count[key] += 1
        self.status_count[status] += 1

        if path.startswith("/api/v1/scan"):
            self.scan_count += 1
            self.scan_duration_sum += duration

    def render(self) -> str:
        lines: list[str] = []

        lines.append("# HELP nile_http_requests_total Total HTTP requests")
        lines.append("# TYPE nile_http_requests_total counter")
        for key, count in sorted(self.request_count.items()):
            method, path = key.split(" ", 1)
            lines.append(
                f'nile_http_requests_total{{method="{method}",path="{path}"}} {count}'
            )

        lines.append("# HELP nile_http_request_duration_seconds HTTP request duration")
        lines.append("# TYPE nile_http_request_duration_seconds summary")
        for key in sorted(self.request_duration_sum):
            method, path = key.split(" ", 1)
            total = self.request_duration_sum[key]
            count = self.request_duration_count[key]
            label = f'method="{method}",path="{path}"'
            lines.append(
                f"nile_http_request_duration_seconds_sum{{{label}}} {total:.4f}"
            )
            lines.append(
                f"nile_http_request_duration_seconds_count{{{label}}} {count}"
            )

        lines.append("# HELP nile_http_status_total HTTP responses by status code")
        lines.append("# TYPE nile_http_status_total counter")
        for status, count in sorted(self.status_count.items()):
            lines.append(f'nile_http_status_total{{code="{status}"}} {count}')

        lines.append("# HELP nile_scans_total Total Solana program scans")
        lines.append("# TYPE nile_scans_total counter")
        lines.append(f"nile_scans_total {self.scan_count}")

        if self.scan_count > 0:
            avg_scan = self.scan_duration_sum / self.scan_count
            lines.append(
                "# HELP nile_scan_avg_duration_seconds Average scan duration"
            )
            lines.append("# TYPE nile_scan_avg_duration_seconds gauge")
            lines.append(f"nile_scan_avg_duration_seconds {avg_scan:.4f}")

        return "\n".join(lines) + "\n"


metrics = _Metrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records request metrics and serves /metrics endpoint."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Serve Prometheus metrics on /metrics
        if request.url.path == "/metrics":
            return PlainTextResponse(metrics.render(), media_type="text/plain")

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        # Normalize path to avoid high cardinality (strip UUIDs)
        path = request.url.path
        parts = path.split("/")
        normalized = "/".join(
            "{id}" if _looks_like_id(p) else p for p in parts
        )

        metrics.record(request.method, normalized, response.status_code, duration)
        return response


def _looks_like_id(segment: str) -> bool:
    """Heuristic: segment is a UUID or long hex string."""
    if len(segment) >= 20:
        return True
    try:
        int(segment, 16)
        return len(segment) >= 8
    except ValueError:
        return False
