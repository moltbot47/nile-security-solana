"""Tests for metrics middleware — Prometheus-compatible in-process metrics."""

from nile.middleware.metrics import _Metrics, _looks_like_id


class TestMetrics:
    def test_record_increments_counts(self):
        m = _Metrics()
        m.record("GET", "/api/v1/health", 200, 0.05)
        assert m.request_count["GET /api/v1/health"] == 1
        assert m.status_count[200] == 1

    def test_record_scan_tracks_separately(self):
        m = _Metrics()
        m.record("POST", "/api/v1/scans/solana", 200, 1.2)
        assert m.scan_count == 1
        assert m.scan_duration_sum == 1.2

    def test_record_non_scan_doesnt_track_scan(self):
        m = _Metrics()
        m.record("GET", "/api/v1/contracts", 200, 0.01)
        assert m.scan_count == 0

    def test_render_produces_prometheus_format(self):
        m = _Metrics()
        m.record("GET", "/api/v1/health", 200, 0.05)
        m.record("POST", "/api/v1/scans/solana", 200, 1.5)
        output = m.render()
        assert "nile_http_requests_total" in output
        assert "nile_http_status_total" in output
        assert "nile_scans_total 1" in output
        assert "nile_scan_avg_duration_seconds" in output

    def test_render_empty_metrics(self):
        m = _Metrics()
        output = m.render()
        assert "nile_scans_total 0" in output
        assert "nile_scan_avg_duration_seconds" not in output

    def test_multiple_requests_accumulate(self):
        m = _Metrics()
        for _i in range(5):
            m.record("GET", "/api/v1/health", 200, 0.1)
        assert m.request_count["GET /api/v1/health"] == 5
        assert m.request_duration_count["GET /api/v1/health"] == 5


class TestLooksLikeId:
    def test_uuid_length(self):
        assert _looks_like_id("550e8400-e29b-41d4-a716-446655440000") is True

    def test_short_hex(self):
        assert _looks_like_id("deadbeef") is True

    def test_short_word(self):
        assert _looks_like_id("health") is False

    def test_non_hex(self):
        assert _looks_like_id("contracts") is False
