"""Authentication API integration tests."""

import pytest
from httpx import AsyncClient

from app.infrastructure.database.models import UserModel


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        test_user: UserModel,
    ):
        """Test successful login with valid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email
        assert data["user"]["id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with non-existent email."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        test_user: UserModel,
    ):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_unverified_user(
        self,
        client: AsyncClient,
        unverified_user: UserModel,
    ):
        """Test login with unverified email."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": unverified_user.email,
                "password": "UnverifiedPassword123!",
            },
        )

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        inactive_user: UserModel,
    ):
        """Test login with inactive account."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": inactive_user.email,
                "password": "InactivePassword123!",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, client: AsyncClient):
        """Test login with invalid email format."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, client: AsyncClient):
        """Test login with missing required fields."""
        response = await client.post(
            "/api/v1/auth/login",
            json={},
        )

        assert response.status_code == 422


class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        client: AsyncClient,
        user_data: dict,
    ):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert data["role"] == "user"
        assert data["is_verified"] is False  # Not verified until email confirmed
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_user: UserModel,
    ):
        """Test registration with already existing email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "NewPassword123!",
                "first_name": "Duplicate",
                "last_name": "User",
            },
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_weak_password(
        self,
        client: AsyncClient,
        weak_password_data: dict,
    ):
        """Test registration with weak password."""
        response = await client.post(
            "/api/v1/auth/register",
            json=weak_password_data,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "ValidPassword123!",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client: AsyncClient):
        """Test registration with missing required fields."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                # Missing password, first_name, last_name
            },
        )

        assert response.status_code == 422


class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        client: AsyncClient,
        test_user: UserModel,
        refresh_token: str,
    ):
        """Test successful token refresh."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(
        self,
        client: AsyncClient,
        invalid_token: str,
    ):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": invalid_token},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_expired(
        self,
        client: AsyncClient,
        expired_token: str,
    ):
        """Test refresh with expired token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token},
        )

        assert response.status_code == 401


class TestVerifyEmail:
    """Tests for POST /api/v1/auth/verify-email."""

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self,
        client: AsyncClient,
        unverified_user: UserModel,
    ):
        """Test successful email verification."""
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": "test-verification-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, client: AsyncClient):
        """Test email verification with invalid token."""
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-token"},
        )

        assert response.status_code == 401


class TestForgotPassword:
    """Tests for POST /api/v1/auth/forgot-password."""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_email(
        self,
        client: AsyncClient,
        test_user: UserModel,
    ):
        """Test forgot password with existing email - always returns success."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )

        # Always returns 200 to not reveal if email exists
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(self, client: AsyncClient):
        """Test forgot password with non-existent email - still returns success."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        # Always returns 200 to not reveal if email exists (security)
        assert response.status_code == 200


class TestResetPassword:
    """Tests for POST /api/v1/auth/reset-password."""

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, client: AsyncClient):
        """Test password reset with invalid token."""
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-reset-token",
                "new_password": "NewPassword123!",
            },
        )

        assert response.status_code == 401


class TestProtectedEndpoints:
    """Tests for authentication on protected endpoints."""

    @pytest.mark.asyncio
    async def test_access_protected_route_without_token(
        self,
        client: AsyncClient,
    ):
        """Test accessing protected route without auth token."""
        response = await client.get("/api/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_invalid_token(
        self,
        client: AsyncClient,
        invalid_token: str,
    ):
        """Test accessing protected route with invalid token."""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_expired_token(
        self,
        client: AsyncClient,
        expired_token: str,
    ):
        """Test accessing protected route with expired token."""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_valid_token(
        self,
        client: AsyncClient,
        test_user: UserModel,
        auth_headers: dict,
    ):
        """Test accessing protected route with valid token."""
        response = await client.get(
            "/api/v1/users/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
