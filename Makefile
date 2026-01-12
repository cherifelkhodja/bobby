.PHONY: help build up down restart logs shell test lint format migrate seed clean

# Variables
DOCKER_COMPOSE = docker compose
BACKEND_CONTAINER = backend
FRONTEND_CONTAINER = frontend

# Colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

## Help
help: ## Show this help
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  ${YELLOW}%-15s${RESET} %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## Docker
build: ## Build all containers
	$(DOCKER_COMPOSE) build

up: ## Start all containers
	$(DOCKER_COMPOSE) up -d

down: ## Stop all containers
	$(DOCKER_COMPOSE) down

restart: down up ## Restart all containers

logs: ## Show logs (all containers)
	$(DOCKER_COMPOSE) logs -f

logs-backend: ## Show backend logs
	$(DOCKER_COMPOSE) logs -f $(BACKEND_CONTAINER)

logs-frontend: ## Show frontend logs
	$(DOCKER_COMPOSE) logs -f $(FRONTEND_CONTAINER)

## Shell access
shell-backend: ## Open shell in backend container
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) bash

shell-frontend: ## Open shell in frontend container
	$(DOCKER_COMPOSE) exec $(FRONTEND_CONTAINER) sh

shell-db: ## Open psql shell
	$(DOCKER_COMPOSE) exec postgres psql -U cooptation -d cooptation

## Backend commands
test: ## Run all backend tests
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) pytest -v

test-unit: ## Run backend unit tests
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) pytest tests/unit -v

test-integration: ## Run backend integration tests
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) pytest tests/integration -v

test-cov: ## Run tests with coverage
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) pytest --cov=app --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) ptw -- -v

lint: ## Run linter (ruff)
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) ruff check .

lint-fix: ## Fix linting issues
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) ruff check --fix .

format: ## Format code (ruff)
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) ruff format .

type-check: ## Run type checker (mypy)
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) mypy app

check-imports: ## Verify all imports work
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) python -c "from app.main import app; print('Imports OK')"

## Database
migrate: ## Run database migrations
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) alembic upgrade head

migrate-new: ## Create new migration (usage: make migrate-new MSG="add users table")
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) alembic downgrade -1

seed: ## Seed database with initial data
	$(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER) python -m app.infrastructure.database.seed

## Frontend commands
test-frontend: ## Run frontend tests
	$(DOCKER_COMPOSE) exec $(FRONTEND_CONTAINER) npm test -- --run

test-frontend-watch: ## Run frontend tests in watch mode
	$(DOCKER_COMPOSE) exec $(FRONTEND_CONTAINER) npm test

lint-frontend: ## Lint frontend
	$(DOCKER_COMPOSE) exec $(FRONTEND_CONTAINER) npm run lint

type-check-frontend: ## Type check frontend
	$(DOCKER_COMPOSE) exec $(FRONTEND_CONTAINER) npm run type-check

build-frontend: ## Build frontend for production
	$(DOCKER_COMPOSE) exec $(FRONTEND_CONTAINER) npm run build

## CI simulation
ci: lint type-check check-imports test lint-frontend type-check-frontend test-frontend ## Run full CI locally

## Cleanup
clean: ## Remove all containers, volumes, and images
	$(DOCKER_COMPOSE) down -v --rmi local

clean-volumes: ## Remove only volumes
	$(DOCKER_COMPOSE) down -v

## Quick commands
dev: up logs ## Start and show logs

fresh: clean build up migrate seed ## Fresh start with clean database
