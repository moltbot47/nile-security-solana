# NILE Security Deployment Guide

## Prerequisites

- Docker & Docker Compose
- Node.js 18+ / npm
- Python 3.11+ / uv
- PostgreSQL 15+
- Redis 7+
- (Optional) Solana CLI + Anchor CLI for on-chain programs

## Local Development

### Backend

```bash
cd backend
cp .env.example .env  # Configure your environment
uv sync               # Install dependencies
uv run uvicorn nile.app:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev            # Starts on port 3000
```

### Full Stack (Make)

```bash
make dev               # Backend (8000) + Frontend (3000)
make lint              # Ruff + TypeScript checks
make test              # pytest with coverage
make ci                # Full CI: lint + test + typecheck + build
```

## Docker Compose

### Application Stack

```bash
docker compose build
docker compose up -d
```

Services:
- **backend** — FastAPI on port 8000
- **frontend** — Next.js on port 3000
- **postgres** — PostgreSQL on port 5432
- **redis** — Redis on port 6379
- **nginx** — Reverse proxy on port 80

### Monitoring Stack

```bash
cd deploy
docker compose -f docker-compose.monitoring.yml up -d
```

Services:
- **Prometheus** — http://localhost:9090
- **Grafana** — http://localhost:3001 (admin / nile-admin)
- **Loki** — http://localhost:3100

## Environment Variables

All prefixed with `NILE_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `NILE_DATABASE_URL` | `postgresql+asyncpg://nile:nile@localhost:5432/nile_solana` | PostgreSQL connection |
| `NILE_REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `NILE_SOLANA_RPC_URL` | `https://api.devnet.solana.com` | Solana RPC endpoint |
| `NILE_SOLANA_NETWORK` | `devnet` | Network (devnet/mainnet-beta) |
| `NILE_JWT_SECRET` | — | JWT signing secret (change in prod) |
| `NILE_API_KEY` | — | Master API key |
| `NILE_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `NILE_PROGRAM_ID` | — | Deployed NILE program address |
| `NILE_DEPLOYER_PRIVATE_KEY` | — | On-chain writer keypair |

## Database Migrations

```bash
cd backend
uv run alembic upgrade head     # Apply migrations
uv run alembic revision --autogenerate -m "description"  # New migration
```

## Solana Program Deployment

Requires Solana CLI and Anchor CLI installed.

```bash
chmod +x deploy/scripts/deploy_devnet.sh
./deploy/scripts/deploy_devnet.sh
```

The script will:
1. Build Anchor programs
2. Deploy to devnet
3. Initialize authority PDA
4. Save deployment info to `devnet-deployment.json`

## Production Checklist

- [ ] Set `NILE_JWT_SECRET` to a strong random value
- [ ] Set `NILE_CORS_ORIGINS` to your production domain
- [ ] Set `NILE_SOLANA_NETWORK=mainnet-beta` and appropriate RPC URL
- [ ] Configure PostgreSQL with SSL
- [ ] Set up Redis with authentication
- [ ] Enable HTTPS via nginx or load balancer
- [ ] Configure Discord alert webhook
- [ ] Verify health checks: `GET /api/v1/health/ready`
- [ ] Verify metrics: `GET /metrics`

## Health Checks

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `GET /api/v1/health` | Liveness | `{"status": "ok"}` |
| `GET /api/v1/health/ready` | Readiness | `{"status": "ready", "checks": {...}}` |
| `GET /metrics` | Prometheus | Text metrics |
