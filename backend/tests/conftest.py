"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.infrastructure.database.models import Base
from app.main import app


# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def user_data():
    """Sample user data for tests."""
    return {
        "email": f"test-{uuid4()}@geminiconsulting.fr",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def candidate_data():
    """Sample candidate data for tests."""
    return {
        "candidate_first_name": "Jean",
        "candidate_last_name": "Dupont",
        "candidate_email": f"jean.dupont-{uuid4()}@example.com",
        "candidate_civility": "M",
        "candidate_phone": "0612345678",
        "candidate_daily_rate": 500.0,
        "candidate_note": "Excellent candidate",
    }


@pytest.fixture
def opportunity_data():
    """Sample opportunity data for tests."""
    return {
        "external_id": str(uuid4()),
        "title": "Développeur Python Senior",
        "reference": f"REF-{uuid4().hex[:8].upper()}",
        "budget": 600.0,
        "manager_name": "Manager Test",
        "client_name": "Client Test",
    }
