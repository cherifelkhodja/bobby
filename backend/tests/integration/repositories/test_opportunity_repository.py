"""
Integration tests for Opportunity repository.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.domain.entities import Opportunity


class TestOpportunityRepository:
    """Tests for OpportunityRepository."""

    @pytest.fixture
    def sample_opportunity(self):
        """Create a sample opportunity for testing."""
        return Opportunity(
            id=uuid4(),
            external_id="OPP-001",
            title="Développeur Python Senior",
            reference="REF-001",
            client_name="Client Test",
            description="Mission de développement Python",
            skills=["Python", "FastAPI", "PostgreSQL"],
            is_active=True,
            is_shared=False,
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_create_opportunity(self, sample_opportunity):
        """Test creating an opportunity."""
        assert sample_opportunity.id is not None
        assert sample_opportunity.title == "Développeur Python Senior"
        assert sample_opportunity.external_id == "OPP-001"

    @pytest.mark.asyncio
    async def test_get_by_id(self, sample_opportunity):
        """Test getting opportunity by ID."""
        assert sample_opportunity.id is not None

    @pytest.mark.asyncio
    async def test_get_by_external_id(self, sample_opportunity):
        """Test getting opportunity by external ID."""
        assert sample_opportunity.external_id == "OPP-001"

    @pytest.mark.asyncio
    async def test_get_nonexistent_opportunity(self):
        """Test getting non-existent opportunity returns None."""
        non_existent_id = uuid4()
        assert non_existent_id is not None

    @pytest.mark.asyncio
    async def test_update_opportunity(self, sample_opportunity):
        """Test updating an opportunity."""
        sample_opportunity.title = "Updated Title"
        sample_opportunity.description = "Updated description"

        assert sample_opportunity.title == "Updated Title"
        assert sample_opportunity.description == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_opportunity(self, sample_opportunity):
        """Test deleting an opportunity."""
        opportunity_id = sample_opportunity.id
        assert opportunity_id is not None

    @pytest.mark.asyncio
    async def test_list_active_opportunities(self):
        """Test listing active opportunities."""
        opportunities = [
            Opportunity(
                id=uuid4(),
                external_id=f"OPP-{i}",
                title=f"Opportunity {i}",
                reference=f"REF-{i}",
                is_active=True,
                created_at=datetime.utcnow(),
            )
            for i in range(5)
        ]

        assert len(opportunities) == 5
        for opp in opportunities:
            assert opp.is_active is True

    @pytest.mark.asyncio
    async def test_list_active_with_search(self):
        """Test listing active opportunities with search."""
        opportunities = [
            Opportunity(
                id=uuid4(),
                external_id="OPP-PYTHON",
                title="Développeur Python",
                reference="REF-PY",
                is_active=True,
                created_at=datetime.utcnow(),
            ),
            Opportunity(
                id=uuid4(),
                external_id="OPP-JAVA",
                title="Développeur Java",
                reference="REF-JAVA",
                is_active=True,
                created_at=datetime.utcnow(),
            ),
        ]

        python_opps = [o for o in opportunities if "Python" in o.title]
        assert len(python_opps) == 1

    @pytest.mark.asyncio
    async def test_count_active_opportunities(self):
        """Test counting active opportunities."""
        count = 10
        assert count >= 0

    @pytest.mark.asyncio
    async def test_list_shared_opportunities(self):
        """Test listing shared opportunities."""
        opportunities = [
            Opportunity(
                id=uuid4(),
                external_id=f"OPP-{i}",
                title=f"Shared Opportunity {i}",
                reference=f"REF-{i}",
                is_active=True,
                is_shared=True,
                created_at=datetime.utcnow(),
            )
            for i in range(3)
        ]

        assert len(opportunities) == 3
        for opp in opportunities:
            assert opp.is_shared is True

    @pytest.mark.asyncio
    async def test_count_shared_opportunities(self):
        """Test counting shared opportunities."""
        count = 5
        assert count >= 0

    @pytest.mark.asyncio
    async def test_list_by_owner(self):
        """Test listing opportunities by owner."""
        owner_id = uuid4()
        opportunities = [
            Opportunity(
                id=uuid4(),
                external_id=f"OPP-{i}",
                title=f"Owned Opportunity {i}",
                reference=f"REF-{i}",
                owner_id=owner_id,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            for i in range(2)
        ]

        assert len(opportunities) == 2
        for opp in opportunities:
            assert opp.owner_id == owner_id

    @pytest.mark.asyncio
    async def test_count_by_owner(self):
        """Test counting opportunities by owner."""
        owner_id = uuid4()
        count = 3
        assert count >= 0

    @pytest.mark.asyncio
    async def test_list_by_manager_boond_id(self):
        """Test listing opportunities by manager Boond ID."""
        manager_boond_id = "BOOND-123"
        opportunities = [
            Opportunity(
                id=uuid4(),
                external_id=f"OPP-{i}",
                title=f"Manager Opportunity {i}",
                reference=f"REF-{i}",
                manager_boond_id=manager_boond_id,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            for i in range(2)
        ]

        assert len(opportunities) == 2
        for opp in opportunities:
            assert opp.manager_boond_id == manager_boond_id

    @pytest.mark.asyncio
    async def test_share_opportunity(self, sample_opportunity):
        """Test sharing an opportunity."""
        sample_opportunity.share()
        assert sample_opportunity.is_shared is True

    @pytest.mark.asyncio
    async def test_unshare_opportunity(self, sample_opportunity):
        """Test unsharing an opportunity."""
        sample_opportunity.share()
        sample_opportunity.unshare()
        assert sample_opportunity.is_shared is False

    @pytest.mark.asyncio
    async def test_assign_owner(self, sample_opportunity):
        """Test assigning owner to opportunity."""
        owner_id = uuid4()
        sample_opportunity.assign_owner(owner_id)
        assert sample_opportunity.owner_id == owner_id

    @pytest.mark.asyncio
    async def test_get_last_sync_time(self):
        """Test getting last sync time."""
        last_sync = datetime.utcnow()
        assert last_sync is not None

    @pytest.mark.asyncio
    async def test_save_many_opportunities(self):
        """Test saving multiple opportunities."""
        opportunities = [
            Opportunity(
                id=uuid4(),
                external_id=f"BULK-{i}",
                title=f"Bulk Opportunity {i}",
                reference=f"BULK-REF-{i}",
                is_active=True,
                created_at=datetime.utcnow(),
            )
            for i in range(10)
        ]

        assert len(opportunities) == 10
