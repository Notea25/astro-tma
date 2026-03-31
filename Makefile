# Astro TMA — developer convenience commands
# Usage: make <target>

.PHONY: help up down logs migrate seed test lint build clean

# Default
help:
	@echo ""
	@echo "  Astro TMA — Dev Commands"
	@echo "  ────────────────────────────────────────"
	@echo "  make up        Start all services (backend + DB + Redis)"
	@echo "  make down      Stop all services"
	@echo "  make logs      Follow backend logs"
	@echo "  make migrate   Run Alembic migrations"
	@echo "  make seed      Seed tarot deck (78 cards) into DB"
	@echo "  make test      Run backend test suite"
	@echo "  make lint      Run ruff + mypy"
	@echo "  make dev-fe    Start frontend dev server"
	@echo "  make build     Build production Docker images"
	@echo "  make clean     Remove all containers and volumes"
	@echo ""

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	docker compose up -d
	@echo "✅ Services running. Backend: http://localhost:8000"

down:
	docker compose down

logs:
	docker compose logs -f backend

restart-backend:
	docker compose restart backend

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head
	@echo "✅ Migrations applied"

migrate-down:
	docker compose exec backend alembic downgrade -1

migration-new:
	@read -p "Migration name: " name; \
	docker compose exec backend alembic revision --autogenerate -m "$$name"

seed:
	docker compose exec backend python infra/scripts/seed_tarot.py
	@echo "✅ Tarot deck seeded"

psql:
	docker compose exec postgres psql -U astro -d astro_tma

redis-cli:
	docker compose exec redis redis-cli

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	cd backend && pytest tests/ -v --tb=short

test-cov:
	cd backend && pytest tests/ -v --cov=services --cov-report=term-missing

# ── Linting ───────────────────────────────────────────────────────────────────
lint:
	cd backend && ruff check . && mypy services/ api/ core/ --ignore-missing-imports
	@echo "✅ Lint passed"

lint-fix:
	cd backend && ruff check . --fix

# ── Frontend ──────────────────────────────────────────────────────────────────
dev-fe:
	cd frontend && npm run dev

build-fe:
	cd frontend && npm run build

# ── Telegram webhook setup ────────────────────────────────────────────────────
set-webhook:
	@if [ -z "$(TOKEN)" ] || [ -z "$(URL)" ] || [ -z "$(SECRET)" ]; then \
		echo "Usage: make set-webhook TOKEN=<bot_token> URL=<webhook_url> SECRET=<secret>"; \
		exit 1; \
	fi
	curl -s "https://api.telegram.org/bot$(TOKEN)/setWebhook" \
		-d "url=$(URL)/api/payments/webhook" \
		-d "secret_token=$(SECRET)" \
		-d "allowed_updates=[\"message\",\"pre_checkout_query\"]" | python3 -m json.tool

# ── Production build ──────────────────────────────────────────────────────────
build:
	docker compose build --no-cache

clean:
	docker compose down -v --remove-orphans
	@echo "⚠️  All containers and volumes removed"
