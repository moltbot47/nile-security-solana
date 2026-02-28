# NILE Security Architecture

## System Overview

```
                    ┌─────────────┐
                    │   Phantom   │
                    │   Wallet    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Next.js    │
                    │  Frontend   │  Port 3000
                    │  (React)    │
                    └──────┬──────┘
                           │ /api/v1/*
                    ┌──────▼──────┐
                    │  FastAPI    │
                    │  Backend    │  Port 8000
                    └──┬───┬───┬──┘
                       │   │   │
              ┌────────┘   │   └────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌─────────┐  ┌─────────┐
         │PostgreSQL│  │  Redis  │  │ Solana  │
         │  (data) │  │(events) │  │  RPC    │
         └────────┘  └─────────┘  └─────────┘
```

## Backend Stack

- **Framework:** FastAPI (async, Python 3.11+)
- **ORM:** SQLAlchemy 2.0 (async)
- **Database:** PostgreSQL via asyncpg
- **Cache/Events:** Redis (pub/sub for SSE)
- **Package Manager:** uv
- **Linter:** ruff

## Frontend Stack

- **Framework:** Next.js 15 (App Router)
- **State:** Zustand
- **Styling:** Tailwind CSS
- **Wallet:** @solana/wallet-adapter-react (Phantom)

## On-Chain Programs (Anchor)

Three Anchor programs deployed to Solana:

1. **nile_security** — Score storage, agent authorization, report submission
2. **nile_oracle** — Consensus mechanism for oracle events
3. **nile_treasury** — Fee collection and distribution

### Key PDA Accounts

| Account | Seeds | Purpose |
|---------|-------|---------|
| NileAuthority | `[b"authority"]` | Global authority singleton |
| ProgramScore | `[b"score", program_address]` | Per-program NILE score |
| AgentRecord | `[b"agent", agent_id]` | Authorized agent identity |
| SecurityReport | `[b"report", program, agent]` | Agent-submitted findings |

## NILE Scoring Engine

Four dimensions, each 0-100, weighted equally (25%):

| Dimension | What It Measures | Key Inputs |
|-----------|------------------|------------|
| **Name** | Identity & reputation | Verified, audits, age, team, ecosystem presence |
| **Image** | Security posture | Signer checks, PDA collisions, CPI safety, arithmetic |
| **Likeness** | Exploit similarity | Pattern matching against known exploits, rug pull signals |
| **Essence** | Code quality | Test coverage, complexity, upgrade authority, timelocks |

### Grade Mapping

| Score Range | Grade |
|-------------|-------|
| 90-100 | A+ |
| 80-89 | A |
| 70-79 | B |
| 60-69 | C |
| 50-59 | D |
| 0-49 | F |

## Request Flow: Scan Endpoint

```
1. POST /api/v1/scans/solana { program_address }
2. Rate limiter check (10/min/IP)
3. Address validation (Base58, 32-44 chars)
4. ProgramAnalyzer.analyze()
   a. Fetch program info via Solana RPC
   b. Detect analysis type (program vs token)
   c. Fetch IDL (if Anchor program)
   d. Check ecosystem presence (Jupiter, Birdeye)
   e. Pattern match against exploit DB
   f. Compute 4 NILE dimension scores
   g. Calculate composite score + grade
5. Return SolanaScanResponse
6. (Optional) Submit score on-chain via onchain_writer
```

## Middleware Stack

Executed in order (outermost first):

1. **MetricsMiddleware** — Prometheus counters and latency
2. **RequestLoggingMiddleware** — Structured access logs with request IDs
3. **CORSMiddleware** — Cross-origin for frontend

## Monitoring

- **Prometheus** scrapes `/metrics` every 15s
- **Grafana** dashboards for request rate, latency, error rate, scan volume
- **Loki** for centralized log aggregation
- **Discord webhooks** for critical alerts (health degraded, high error rate)

## Directory Structure

```
nile-security-solana/
├── backend/
│   ├── nile/
│   │   ├── app.py              # FastAPI factory
│   │   ├── config.py           # Settings (env vars)
│   │   ├── core/               # Auth, DB, events, exceptions, rate limiting, alerting
│   │   ├── middleware/          # Logging, metrics
│   │   ├── models/             # SQLAlchemy models (19)
│   │   ├── routers/v1/         # API endpoints
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── services/           # Business logic (analyzer, scorer, chain)
│   │   └── workers/            # Background scan worker
│   └── tests/                  # 54 pytest tests
├── frontend/
│   └── src/
│       ├── app/                # Next.js pages
│       ├── components/         # React components
│       ├── lib/                # API client, types, utils
│       ├── providers/          # WalletProvider
│       └── store/              # Zustand stores
├── programs/                   # Anchor (Rust) smart contracts
├── deploy/                     # Docker, nginx, monitoring
├── data/                       # Exploit patterns
└── tests/                      # Anchor Mocha tests
```
