# Production Dockerfile for Railway
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml ./

# Install dependencies directly (simpler and more reliable)
# v2: Added CV transformer deps (google-generativeai, docxtpl, pypdf, python-docx)
RUN pip install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "sqlalchemy[asyncio]>=2.0.25" \
    "asyncpg>=0.29.0" \
    "alembic>=1.13.1" \
    "pydantic>=2.5.3" \
    "pydantic-settings>=2.1.0" \
    "python-jose[cryptography]>=3.3.0" \
    "bcrypt>=4.0.0" \
    "httpx>=0.26.0" \
    "tenacity>=8.2.3" \
    "redis>=5.0.1" \
    "aiosmtplib>=3.0.1" \
    "resend>=2.0.0" \
    "structlog>=24.1.0" \
    "python-multipart>=0.0.6" \
    "email-validator>=2.1.0" \
    "google-generativeai>=0.8.0" \
    "docxtpl>=0.18.0" \
    "pypdf>=4.0.0" \
    "python-docx>=1.1.0"

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Railway uses PORT env variable
ENV PORT=8000
EXPOSE $PORT

# Production command - run migrations then start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
