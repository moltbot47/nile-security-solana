# NILE Security for Solana

Pre-transaction security intelligence for the Phantom wallet ecosystem. Paste a Solana program or token address, get a NILE score (0-100) in seconds.

## What It Does

NILE scores Solana programs across 4 dimensions:

- **Name** — Identity, audits, team reputation, ecosystem presence
- **Image** — Signer checks, account validation, CPI safety (via IDL analysis)
- **Likeness** — Pattern matching against 10 known exploit categories
- **Essence** — Code quality, upgrade authority, timelocks, complexity

Each dimension is scored 0-100 and weighted equally. The composite score maps to a letter grade (A+ through F).

## Quick Start

```bash
# Backend
cd backend
uv sync
uv run uvicorn nile.app:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Or use Make
make dev
```

## Scan a Program

```bash
curl -X POST http://localhost:8000/api/v1/scans/solana \
  -H "Content-Type: application/json" \
  -d '{"program_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}'
```

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React, Tailwind CSS, Zustand |
| Wallet | @solana/wallet-adapter-react (Phantom) |
| Backend | FastAPI, SQLAlchemy 2.0 (async), PostgreSQL |
| Events | Redis pub/sub, Server-Sent Events |
| Chain | Solana (devnet), Anchor framework |
| Monitoring | Prometheus, Grafana, Loki |
| CI/CD | GitHub Actions |

## Tests

```bash
cd backend && uv run pytest -v          # 54 tests
cd frontend && npx tsc --noEmit         # Type check
cd frontend && npx next build           # 15 pages
```

## Documentation

- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Scoring Methodology](docs/SCORING.md)

## Project Structure

```
├── backend/           FastAPI backend (Python)
│   ├── nile/          Application code
│   │   ├── core/      Auth, DB, events, exceptions
│   │   ├── middleware/ Logging, metrics
│   │   ├── models/    SQLAlchemy models
│   │   ├── routers/   API endpoints
│   │   ├── schemas/   Pydantic models
│   │   ├── services/  Business logic
│   │   └── workers/   Background jobs
│   └── tests/         Test suite
├── frontend/          Next.js frontend
├── programs/          Anchor smart contracts (Rust)
├── deploy/            Docker, monitoring, deploy scripts
├── data/              Exploit pattern database
└── docs/              Documentation
```

## License

Proprietary. See LICENSE for details.
