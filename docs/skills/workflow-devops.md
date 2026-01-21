# Workflow & DevOps

Standards Git, CI/CD et déploiement pour les projets Gemini Consulting.

---

## Git Workflow

### Branches

```
main (production)
  └── develop (staging)
        ├── feature/XXX-description
        ├── fix/XXX-description
        └── refactor/XXX-description
```

### Règles

| Règle | Description |
|-------|-------------|
| Jamais de push direct sur `main` | Toujours via PR |
| Feature branches depuis `develop` | `git checkout -b feature/123-add-login develop` |
| PR = 1 fonctionnalité | Pas de PR monstre |
| Review obligatoire | Au moins 1 approbation |
| Tests passent | CI verte avant merge |

---

## Conventional Commits

### Format

```
<type>(<scope>): <description>

[body]

[footer]
```

### Types

| Type | Usage |
|------|-------|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `refactor` | Refactoring (pas de changement fonctionnel) |
| `docs` | Documentation uniquement |
| `test` | Ajout/modification de tests |
| `chore` | Maintenance (deps, config) |
| `style` | Formatting, semicolons, etc. |
| `perf` | Amélioration de performance |
| `ci` | CI/CD changes |

### Exemples

```bash
# Feature
git commit -m "feat(auth): add magic link authentication"

# Fix
git commit -m "fix(cv-transformer): handle empty PDF files"

# Refactor
git commit -m "refactor(boond): extract client to separate module"

# Breaking change
git commit -m "feat(api)!: change response format for opportunities

BREAKING CHANGE: opportunities endpoint now returns paginated response"

# With scope
git commit -m "feat(hr): add application status history"

# Multi-line
git commit -m "fix(auth): resolve token refresh race condition

When multiple requests triggered refresh simultaneously,
some would fail with 401. Added mutex to prevent this.

Fixes #142"
```

---

## CI/CD (GitHub Actions)

### Workflow standard

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install ruff mypy
      - name: Lint
        run: ruff check .
      - name: Type check
        run: mypy .

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest --cov=app --cov-fail-under=85
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/test
          REDIS_URL: redis://localhost:6379/0

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t app:${{ github.sha }} .
```

---

## Docker

### Dockerfile multi-stage

```dockerfile
# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir build \
    && pip wheel --no-cache-dir --wheel-dir=/wheels -e .

# Runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Install runtime dependencies only
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

# Copy application
COPY --chown=app:app . .

USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

# Run
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### .dockerignore

```
.git
.github
__pycache__
*.pyc
.pytest_cache
.coverage
.env
.env.*
*.md
tests/
docs/
```

---

## Makefile

```makefile
.PHONY: help install dev test lint format migrate run

help:
	@echo "Commands:"
	@echo "  install  - Install production dependencies"
	@echo "  dev      - Install development dependencies"
	@echo "  test     - Run tests"
	@echo "  lint     - Run linters"
	@echo "  format   - Format code"
	@echo "  migrate  - Run database migrations"
	@echo "  run      - Start development server"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check .
	mypy .

format:
	ruff check --fix .
	ruff format .

migrate:
	alembic upgrade head

run:
	uvicorn app.main:app --reload
```

---

## Déploiement Railway

### Configuration

```toml
# railway.toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/api/v1/health/live"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

### Variables d'environnement

```bash
# Core
ENV=prod
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
JWT_SECRET=...
FRONTEND_URL=https://...

# External APIs
BOOND_API_URL=https://ui.boondmanager.com/api
BOOND_USERNAME=...
BOOND_PASSWORD=...
GEMINI_API_KEY=...
TURNOVERIT_API_KEY=...

# Email
RESEND_API_KEY=...

# Storage
S3_ENDPOINT_URL=...
S3_BUCKET_NAME=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
```

### Rollback

```bash
# Via Railway CLI
railway up --detach  # Deploy
railway rollback     # Rollback to previous
```
