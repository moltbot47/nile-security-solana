# NILE Security for Solana

## Project Overview
NILE (Name Image Likeness Essence) for Solana is a smart contract security intelligence platform that scores Solana programs through four dimensions. Built for the Phantom wallet ecosystem (15M+ MAU). Fork of the EVM version — the original remains at `moltbot47/nile-security` for EVMbench/OpenAI integration.

## Tech Stack
- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy 2.0 / asyncpg / Pydantic v2
- **Frontend:** Next.js 16 / React 19 / Tailwind CSS 4 / shadcn/ui / Zustand / Recharts
- **Database:** PostgreSQL 18 / Redis 7
- **Blockchain:** Anchor (Rust) / Solana CLI / solders / anchorpy
- **Oracles:** Pyth Network (price feeds) / Custom oracle consensus (NILE agents)
- **AI:** Claude API (Anthropic) + OpenAI API
- **Deployment:** Docker Compose on Digital Ocean

## Commands
- `make dev` - Start development environment
- `make lint` - Run ruff (Python) + biome (TypeScript)
- `make test` - Run pytest (backend) + bun test (frontend)
- `make typecheck` - Run type checking
- `make build` - Build Docker images
- `anchor build` - Build Solana programs
- `anchor test` - Run Anchor program tests
- `anchor deploy` - Deploy programs to devnet/mainnet

## Project Structure
- `backend/` - FastAPI application with NILE scoring engine
- `frontend/` - Next.js dashboard + Phantom wallet integration
- `programs/` - Anchor/Rust Solana programs (replaces contracts/)
- `tests/` - Anchor integration tests
- `app/` - Anchor workspace config
- `deploy/` - Docker and deployment configurations
- `docs/` - Architecture docs, ADRs

## NILE Scoring Model (Solana-Adapted)
Each program scored 0-100 across four dimensions (25% each):
- **Name** (N): Source verification (Anchor IDL published), audit history (OtterSec, Sec3, Neodyme), program age, team identity, ecosystem presence (Jupiter strict list, Birdeye verified)
- **Image** (I): Security posture — missing signer checks, PDA seed collisions, unchecked arithmetic, CPI vulnerabilities, upgrade authority status
- **Likeness** (L): Pattern matching against known Solana exploits (Wormhole, Mango, Cashio, Crema patterns)
- **Essence** (E): Test coverage, instruction handler complexity, upgrade authority risk, CPI call count

## Key Differences from EVM Version
- `contracts/` (Solidity/Foundry) → `programs/` (Rust/Anchor)
- `chain_service.py` uses `solders` + `anchorpy` instead of `web3.py`
- Chainlink price feeds → Pyth Network
- Slither static analysis → Custom Rust/Anchor analysis + Soteria
- ERC-20 → SPL Token
- Address format: base58 (44 char) instead of hex (42 char, 0x prefix)
- No reentrancy guards needed (Solana single-threaded execution)

## Development Guidelines
- All API endpoints under `/api/v1/`
- Use async SQLAlchemy throughout
- Pydantic v2 for all request/response schemas
- Test on Solana devnet/localnet only
- Phantom wallet connection via `@phantom/react-sdk`
- Program addresses derived via PDA seeds
