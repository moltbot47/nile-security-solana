# NILE Security API Reference

Base URL: `/api/v1`

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/health/ready` | Readiness probe (DB, Redis, Solana RPC) |
| GET | `/health/metrics` | Quick metrics summary |

## Scan (Hero Endpoint)

### POST `/scans/solana`

Instantly scan a Solana program or token address.

**Rate limit:** 10 requests/min/IP

**Request:**
```json
{
  "program_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
}
```

**Response (200):**
```json
{
  "address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
  "analysis_type": "program",
  "total_score": 82,
  "grade": "A",
  "scores": {
    "name": 90,
    "image": 75,
    "likeness": 85,
    "essence": 78
  },
  "details": { ... },
  "exploit_matches": [],
  "program_info": { ... },
  "token_info": null,
  "ecosystem": { ... },
  "idl_analysis": { ... }
}
```

**Error responses:**
- `400` — Invalid Solana address
- `422` — Analysis failed
- `429` — Rate limit exceeded

## Contracts

| Method | Path | Description |
|--------|------|-------------|
| GET | `/contracts` | List all contracts |
| GET | `/contracts/{id}` | Get contract by ID |
| GET | `/contracts/{id}/nile-history` | NILE score history |

## Scans (Job-Based)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/scans` | List scan jobs |
| POST | `/scans` | Create a scan job |
| GET | `/scans/{id}` | Get scan job by ID |

## KPIs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/kpis/attacker?time_range=30d` | Attacker-side KPIs |
| GET | `/kpis/defender?time_range=30d` | Defender-side KPIs |
| GET | `/kpis/asset-health` | Asset health items |

## Agents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List agents |
| GET | `/agents/{id}` | Get agent details |
| GET | `/agents/leaderboard?limit=25` | Agent leaderboard |
| GET | `/agents/{id}/contributions` | Agent contributions |

## Authentication

Protected endpoints require one of:

- **API Key:** `X-API-Key: nile_{token}` header
- **JWT Bearer:** `Authorization: Bearer {jwt}` header

JWT tokens are issued by the auth system (HS256, 1-hour expiry).

## Events (SSE)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/events/stream` | Server-Sent Events stream |
| GET | `/events/history?limit=50` | Event history |

## Metrics

Prometheus metrics are exposed at `/metrics` (not under `/api/v1`).

Key metrics:
- `nile_http_requests_total{method, path}` — Request counter
- `nile_http_request_duration_seconds_sum{method, path}` — Latency
- `nile_http_status_total{code}` — Status code distribution
- `nile_scans_total` — Total Solana scans
- `nile_scan_avg_duration_seconds` — Average scan duration
