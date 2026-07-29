# ═══════════════════════════════════════════════════════════════════
# Rafeeq Kernel v2.3.0 — Makefile
# Quick commands for development & deployment
# ═══════════════════════════════════════════════════════════════════

.PHONY: help setup dev prod stop logs test lint clean backup health

help: ## Show this help
	@echo "🐺 Rafeeq Kernel v2.3.0 — Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## One-time setup (creates .env, SSL certs, directories)
	@chmod +x scripts/setup.sh && ./scripts/setup.sh

dev: ## Start development environment with hot-reload
	@docker-compose -f docker-compose.dev.yml up -d
	@echo "🚀 Dev environment running on http://localhost:8001"

prod: ## Start production environment
	@docker-compose up -d
	@echo "🚀 Production environment running!"
	@echo "   🌐 App:       https://localhost"
	@echo "   📊 Grafana:   http://localhost:3000"
	@echo "   📈 Prometheus: http://localhost:9090"

stop: ## Stop all containers
	@docker-compose down
	@docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
	@echo "🛑 All containers stopped"

logs: ## Follow application logs
	@docker-compose logs -f app

test: ## Run tests
	@docker-compose exec app pytest -v --cov=. --cov-report=term

lint: ## Run linting
	@docker-compose exec app black --check .
	@docker-compose exec app flake8 .

backup: ## Run backup script
	@chmod +x scripts/backup.sh && ./scripts/backup.sh

health: ## Run health check
	@chmod +x scripts/health-check.sh && ./scripts/health-check.sh

clean: ## Clean Docker volumes, images, and cache
	@docker-compose down -v
	@docker system prune -f
	@echo "🧹 Cleanup complete"

migrate: ## Run database migrations
	@docker-compose exec -T postgres psql -U rafeeq -d rafeeq -f /docker-entrypoint-initdb.d/init.sql
	@echo "🗄️  Migrations applied"

shell: ## Open shell in app container
	@docker-compose exec app /bin/bash

redis-cli: ## Open Redis CLI
	@docker-compose exec redis redis-cli

psql: ## Open PostgreSQL CLI
	@docker-compose exec postgres psql -U rafeeq -d rafeeq
