"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.dependencies import get_db
from app.domain.value_objects import UserRole
from app.infrastructure.database.models import Base, UserModel
from app.infrastructure.security.jwt import create_access_token, create_refresh_token
from app.infrastructure.security.password import hash_password
from app.main import app
from tests.factories import (
    CandidateFactory,
    CooptationFactory,
    InvitationFactory,
    JobApplicationFactory,
    JobPostingFactory,
    OpportunityFactory,
    UserFactory,
)

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================


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
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


# ============================================================================
# HTTP Client Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ============================================================================
# User Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> UserModel:
    """Create a basic test user in database."""
    user = UserModel(
        id=uuid4(),
        email=f"testuser-{uuid4().hex[:8]}@example.com",
        first_name="Test",
        last_name="User",
        hashed_password=hash_password("TestPassword123!"),
        role=UserRole.USER.value,
        is_verified=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> UserModel:
    """Create an admin user in database."""
    user = UserModel(
        id=uuid4(),
        email=f"admin-{uuid4().hex[:8]}@example.com",
        first_name="Admin",
        last_name="User",
        hashed_password=hash_password("AdminPassword123!"),
        role=UserRole.ADMIN.value,
        is_verified=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def commercial_user(db_session: AsyncSession) -> UserModel:
    """Create a commercial user in database."""
    user = UserModel(
        id=uuid4(),
        email=f"commercial-{uuid4().hex[:8]}@example.com",
        first_name="Commercial",
        last_name="User",
        hashed_password=hash_password("CommercialPassword123!"),
        role=UserRole.COMMERCIAL.value,
        is_verified=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def rh_user(db_session: AsyncSession) -> UserModel:
    """Create an RH user in database."""
    user = UserModel(
        id=uuid4(),
        email=f"rh-{uuid4().hex[:8]}@example.com",
        first_name="RH",
        last_name="User",
        hashed_password=hash_password("RHPassword123!"),
        role=UserRole.RH.value,
        is_verified=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user(db_session: AsyncSession) -> UserModel:
    """Create an unverified user in database."""
    user = UserModel(
        id=uuid4(),
        email=f"unverified-{uuid4().hex[:8]}@example.com",
        first_name="Unverified",
        last_name="User",
        hashed_password=hash_password("UnverifiedPassword123!"),
        role=UserRole.USER.value,
        is_verified=False,
        is_active=True,
        verification_token="test-verification-token",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession) -> UserModel:
    """Create an inactive user in database."""
    user = UserModel(
        id=uuid4(),
        email=f"inactive-{uuid4().hex[:8]}@example.com",
        first_name="Inactive",
        last_name="User",
        hashed_password=hash_password("InactivePassword123!"),
        role=UserRole.USER.value,
        is_verified=True,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ============================================================================
# Authentication Helpers
# ============================================================================


def get_auth_headers(user_id: UUID) -> dict[str, str]:
    """Generate authorization headers for a user."""
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(test_user: UserModel) -> dict[str, str]:
    """Get auth headers for test user."""
    return get_auth_headers(test_user.id)


@pytest.fixture
def admin_headers(admin_user: UserModel) -> dict[str, str]:
    """Get auth headers for admin user."""
    return get_auth_headers(admin_user.id)


@pytest.fixture
def commercial_headers(commercial_user: UserModel) -> dict[str, str]:
    """Get auth headers for commercial user."""
    return get_auth_headers(commercial_user.id)


@pytest.fixture
def rh_headers(rh_user: UserModel) -> dict[str, str]:
    """Get auth headers for RH user."""
    return get_auth_headers(rh_user.id)


# ============================================================================
# Token Fixtures
# ============================================================================


@pytest.fixture
def access_token(test_user: UserModel) -> str:
    """Create access token for test user."""
    return create_access_token(test_user.id)


@pytest.fixture
def refresh_token(test_user: UserModel) -> str:
    """Create refresh token for test user."""
    return create_refresh_token(test_user.id)


@pytest.fixture
def expired_token() -> str:
    """Create an expired token."""
    from datetime import datetime, timedelta

    from jose import jwt

    payload = {
        "sub": str(uuid4()),
        "exp": datetime.utcnow() - timedelta(hours=1),
        "type": "access",
        "iat": datetime.utcnow() - timedelta(hours=2),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def invalid_token() -> str:
    """Create an invalid token."""
    return "invalid.token.here"


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def user_data():
    """Sample user registration data."""
    return {
        "email": f"newuser-{uuid4().hex[:8]}@example.com",
        "password": "NewUserPassword123!",
        "first_name": "New",
        "last_name": "User",
    }


@pytest.fixture
def weak_password_data():
    """Sample user data with weak password."""
    return {
        "email": f"weakpass-{uuid4().hex[:8]}@example.com",
        "password": "123",
        "first_name": "Weak",
        "last_name": "Password",
    }


@pytest.fixture
def candidate_data():
    """Sample candidate data for cooptation."""
    return {
        "candidate_first_name": "Jean",
        "candidate_last_name": "Dupont",
        "candidate_email": f"jean.dupont-{uuid4().hex[:8]}@example.com",
        "candidate_civility": "M",
        "candidate_phone": "+33612345678",
        "candidate_daily_rate": 500.0,
        "candidate_note": "Excellent candidat pour la mission",
    }


@pytest.fixture
def opportunity_data():
    """Sample opportunity data."""
    return {
        "external_id": str(uuid4()),
        "title": "Développeur Python Senior",
        "reference": f"REF-{uuid4().hex[:8].upper()}",
        "budget": 600.0,
        "manager_name": "Manager Test",
        "client_name": "Client Test",
        "description": "Description de l'opportunité de mission",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "location": "Paris",
    }


# ============================================================================
# Factory Fixtures (from factories.py)
# ============================================================================


@pytest.fixture
def user_factory():
    """Provide UserFactory for tests."""
    return UserFactory


@pytest.fixture
def candidate_factory():
    """Provide CandidateFactory for tests."""
    return CandidateFactory


@pytest.fixture
def opportunity_factory():
    """Provide OpportunityFactory for tests."""
    return OpportunityFactory


@pytest.fixture
def cooptation_factory():
    """Provide CooptationFactory for tests."""
    return CooptationFactory


@pytest.fixture
def invitation_factory():
    """Provide InvitationFactory for tests."""
    return InvitationFactory


@pytest.fixture
def job_posting_factory():
    """Provide JobPostingFactory for tests."""
    return JobPostingFactory


@pytest.fixture
def job_application_factory():
    """Provide JobApplicationFactory for tests."""
    return JobApplicationFactory
