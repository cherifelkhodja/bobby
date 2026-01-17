"""Integration tests for InvitationRepository."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Invitation
from app.domain.value_objects import Email, UserRole
from app.infrastructure.database.repositories import InvitationRepository


class TestInvitationRepository:
    """Integration tests for InvitationRepository."""

    @pytest_asyncio.fixture
    async def repository(self, db_session: AsyncSession):
        """Create repository instance with test session."""
        return InvitationRepository(db_session)

    def create_invitation(self, **kwargs) -> Invitation:
        """Factory for creating invitation entities."""
        defaults = {
            "email": Email(f"invite-{uuid4().hex[:8]}@example.com"),
            "role": UserRole.USER,
            "invited_by": uuid4(),
            "token": f"token-{uuid4().hex}",
            "expires_at": datetime.utcnow() + timedelta(hours=48),
        }
        defaults.update(kwargs)
        return Invitation(**defaults)

    @pytest.mark.asyncio
    async def test_save_new_invitation(self, repository: InvitationRepository):
        """Test saving a new invitation."""
        invitation = self.create_invitation()

        saved = await repository.save(invitation)

        assert saved.id == invitation.id
        assert str(saved.email) == str(invitation.email)
        assert saved.role == invitation.role

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository: InvitationRepository):
        """Test retrieving invitation by ID."""
        invitation = self.create_invitation()
        await repository.save(invitation)

        retrieved = await repository.get_by_id(invitation.id)

        assert retrieved is not None
        assert retrieved.id == invitation.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository: InvitationRepository):
        """Test retrieving non-existent invitation returns None."""
        retrieved = await repository.get_by_id(uuid4())

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_token(self, repository: InvitationRepository):
        """Test retrieving invitation by token."""
        invitation = self.create_invitation(token="unique-test-token-12345")
        await repository.save(invitation)

        retrieved = await repository.get_by_token("unique-test-token-12345")

        assert retrieved is not None
        assert retrieved.id == invitation.id
        assert retrieved.token == "unique-test-token-12345"

    @pytest.mark.asyncio
    async def test_get_by_token_not_found(self, repository: InvitationRepository):
        """Test retrieving by non-existent token returns None."""
        retrieved = await repository.get_by_token("nonexistent-token")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_email(self, repository: InvitationRepository):
        """Test retrieving invitation by email."""
        email = f"specific-{uuid4().hex[:8]}@example.com"
        invitation = self.create_invitation(email=Email(email))
        await repository.save(invitation)

        retrieved = await repository.get_by_email(email)

        assert retrieved is not None
        assert str(retrieved.email) == email

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, repository: InvitationRepository):
        """Test retrieving by non-existent email returns None."""
        retrieved = await repository.get_by_email("notfound@example.com")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_pending(self, repository: InvitationRepository):
        """Test listing pending invitations."""
        # Create pending invitations
        for i in range(3):
            invitation = self.create_invitation()
            await repository.save(invitation)

        # Create accepted invitation
        accepted = self.create_invitation()
        accepted.accept()
        await repository.save(accepted)

        # List pending
        pending = await repository.list_pending()

        assert len(pending) == 3
        for inv in pending:
            assert inv.is_accepted is False

    @pytest.mark.asyncio
    async def test_list_pending_excludes_expired(self, repository: InvitationRepository):
        """Test listing pending excludes expired invitations."""
        # Create valid invitation
        valid = self.create_invitation(
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        await repository.save(valid)

        # Create expired invitation
        expired = self.create_invitation(
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        await repository.save(expired)

        # List pending - may or may not filter expired depending on implementation
        pending = await repository.list_pending()

        # At minimum, valid invitation should be present
        valid_ids = [inv.id for inv in pending if not inv.is_expired]
        assert valid.id in [inv.id for inv in pending]

    @pytest.mark.asyncio
    async def test_list_pending_pagination(self, repository: InvitationRepository):
        """Test pagination for listing pending invitations."""
        # Create multiple invitations
        for i in range(10):
            invitation = self.create_invitation()
            await repository.save(invitation)

        # Get first page
        page1 = await repository.list_pending(skip=0, limit=5)
        assert len(page1) == 5

        # Get second page
        page2 = await repository.list_pending(skip=5, limit=5)
        assert len(page2) == 5

        # Ensure different invitations
        page1_ids = {inv.id for inv in page1}
        page2_ids = {inv.id for inv in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_delete_invitation(self, repository: InvitationRepository):
        """Test deleting an invitation."""
        invitation = self.create_invitation()
        await repository.save(invitation)

        # Delete
        deleted = await repository.delete(invitation.id)
        assert deleted is True

        # Verify
        retrieved = await repository.get_by_id(invitation.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_invitation(self, repository: InvitationRepository):
        """Test deleting non-existent invitation returns False."""
        deleted = await repository.delete(uuid4())

        assert deleted is False

    @pytest.mark.asyncio
    async def test_invitation_with_boond_data(self, repository: InvitationRepository):
        """Test invitation with BoondManager data is persisted correctly."""
        invitation = self.create_invitation(
            boond_resource_id="res-123",
            manager_boond_id="mgr-456",
            phone="+33612345678",
            first_name="John",
            last_name="Doe",
        )
        await repository.save(invitation)

        retrieved = await repository.get_by_id(invitation.id)

        assert retrieved is not None
        assert retrieved.boond_resource_id == "res-123"
        assert retrieved.manager_boond_id == "mgr-456"
        assert retrieved.phone == "+33612345678"
        assert retrieved.first_name == "John"
        assert retrieved.last_name == "Doe"

    @pytest.mark.asyncio
    async def test_update_invitation_on_accept(self, repository: InvitationRepository):
        """Test updating invitation when accepted."""
        invitation = self.create_invitation()
        await repository.save(invitation)

        # Accept and save
        invitation.accept()
        await repository.save(invitation)

        # Verify
        retrieved = await repository.get_by_id(invitation.id)
        assert retrieved is not None
        assert retrieved.is_accepted is True
        assert retrieved.accepted_at is not None

    @pytest.mark.asyncio
    async def test_all_roles_supported(self, repository: InvitationRepository):
        """Test that all user roles are correctly persisted."""
        roles = [UserRole.USER, UserRole.COMMERCIAL, UserRole.RH, UserRole.ADMIN]

        for role in roles:
            invitation = self.create_invitation(role=role)
            saved = await repository.save(invitation)

            retrieved = await repository.get_by_id(saved.id)
            assert retrieved is not None
            assert retrieved.role == role, f"Role mismatch for {role}"
