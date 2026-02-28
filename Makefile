.PHONY: dev lint test test-unit test-cov typecheck build up down deploy migrate seed ci

# Development
dev:
	@echo "Starting backend..."
	cd backend && uv run uvicorn nile.app:app --reload --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev &

# Quality
lint:
	cd backend && uv run ruff check nile/ tests/
	cd frontend && npx tsc --noEmit

test:
	cd backend && uv run pytest -v --cov=nile

test-unit:
	cd backend && uv run pytest -v -x

test-cov:
	cd backend && uv run pytest -v --cov=nile --cov-report=term-missing --cov-fail-under=60

typecheck:
	cd frontend && npx tsc --noEmit

# Full CI check (runs locally)
ci: lint test-cov typecheck
	cd frontend && npx next build
	@echo "CI checks passed."

# Docker
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

# Deployment
deploy:
	ssh root@159.203.138.96 'cd /opt/nile-security && git pull && docker compose -f docker-compose.yml up -d --build'

# Backend utilities
migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python -c "from nile.services.nile_scorer import *; print('NILE scoring engine loaded OK')"
