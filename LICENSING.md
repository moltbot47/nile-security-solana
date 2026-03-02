# NILE Security — Open-Core Licensing

## Overview

NILE Security uses an **open-core licensing model**. The core security scanning engine is open-source under Apache 2.0. Commercial features (agent ecosystem, trading engine, premium analytics, dashboard) are licensed under the Business Source License 1.1 (BSL 1.1).

## License Resolution

The license for any file is determined by the nearest `LICENSE` file in its directory ancestry. If no `LICENSE` file exists in the file's directory or any parent below the repo root, the root `LICENSE` (Apache 2.0) applies.

## Directory-to-License Map

### Apache 2.0 — Open-Source Core

| Path | Component |
|------|-----------|
| `backend/nile/services/nile_scorer.py` | NILE 4-dimension scoring algorithm |
| `backend/nile/services/program_analyzer.py` | Solana program analysis pipeline |
| `backend/nile/services/chain_service.py` | Solana RPC interactions |
| `backend/nile/services/idl_fetcher.py` | Anchor IDL parsing & analysis |
| `backend/nile/services/ecosystem_checker.py` | Jupiter/Birdeye registry verification |
| `backend/nile/services/pumpfun_analyzer.py` | Pump.fun token risk heuristics |
| `backend/nile/services/pattern_library.py` | Vulnerability pattern matching |
| `backend/nile/routers/v1/scans.py` | Hero scan endpoint (`POST /api/v1/scans/solana`) |
| `backend/nile/routers/v1/health.py` | Health check endpoints |
| `backend/nile/schemas/solana_scan.py` | Scan request/response schemas |
| `backend/nile/schemas/scan.py` | Core scan schemas |
| `programs/nile_security/` | Anchor on-chain program (Rust) |
| `data/exploit_patterns/` | Known exploit signature database |
| `docs/` | All documentation |

### BSL 1.1 — Commercial Features

| Path | Component |
|------|-----------|
| `backend/nile/services/` (all others) | Agent scoring, oracle consensus, trading, risk engine, incentives |
| `backend/nile/routers/v1/` (all others) | Agent, oracle, trading, KPI, benchmark, person endpoints |
| `backend/nile/discord/` | Discord bot integration |
| `backend/nile/middleware/` | Metrics and monitoring middleware |
| `frontend/` | Next.js dashboard |
| `deploy/` | Docker, nginx, Prometheus, Grafana configs |

## BSL 1.1 Parameters

- **Licensor:** Eula Labs Ventures LLC
- **Change Date:** 2030-03-01
- **Change License:** Apache License 2.0
- **Additional Use Grant:** You may use the Licensed Work for non-commercial research, education, and internal evaluation purposes.

On the Change Date, all BSL 1.1 code automatically converts to Apache License 2.0.

## For Contributors

- Contributions to **Apache 2.0 components** (core engine, scan endpoint, on-chain program, exploit patterns) are welcome under the Apache 2.0 license.
- Contributions to **BSL 1.1 components** require a Contributor License Agreement (CLA). Contact dbutler@eulaproperties.com.

## For Grant Reviewers

The open-source core engine is independently buildable and usable:

```bash
# Install and run the scanning engine
cd backend && uv sync
uv run uvicorn nile.app:app --host 0.0.0.0 --port 8000

# Scan any Solana program or token
curl -X POST http://localhost:8000/api/v1/scans/solana \
  -H "Content-Type: application/json" \
  -d '{"program_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}'
```

The core engine includes:
- 4-dimension NILE scoring (Name / Image / Likeness / Essence)
- 14 known Solana exploit pattern signatures
- Pump.fun token risk analysis (holder concentration, LP detection, creator profiling)
- Anchor IDL security analysis
- Ecosystem verification (Jupiter strict list, Birdeye, known auditors)

## Commercial Licensing

For commercial use of BSL 1.1 components (enterprise dashboard, agent ecosystem, trading engine, premium analytics), contact:

**Durayveon Butler**
dbutler@eulaproperties.com
Eula Labs Ventures LLC
