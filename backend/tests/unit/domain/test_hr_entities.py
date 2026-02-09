"""Tests for HR feature domain entities (JobPosting, JobApplication)."""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.domain.entities import (
    ApplicationStatus,
    ContractType,
    JobApplication,
    JobPosting,
    JobPostingStatus,
)


class TestJobPostingStatus:
    """Tests for JobPostingStatus value object."""

    def test_status_values(self):
        assert JobPostingStatus.DRAFT.value == "draft"
        assert JobPostingStatus.PUBLISHED.value == "published"
        assert JobPostingStatus.CLOSED.value == "closed"

    def test_display_name(self):
        assert JobPostingStatus.DRAFT.display_name == "Brouillon"
        assert JobPostingStatus.PUBLISHED.display_name == "Publiée"
        assert JobPostingStatus.CLOSED.display_name == "Fermée"

    def test_is_active(self):
        assert JobPostingStatus.DRAFT.is_active is False
        assert JobPostingStatus.PUBLISHED.is_active is True
        assert JobPostingStatus.CLOSED.is_active is False


class TestApplicationStatus:
    """Tests for ApplicationStatus value object."""

    def test_status_values(self):
        assert ApplicationStatus.EN_COURS.value == "en_cours"
        assert ApplicationStatus.VALIDE.value == "valide"
        assert ApplicationStatus.REFUSE.value == "refuse"

    def test_en_cours_can_transition_to_valide(self):
        assert ApplicationStatus.EN_COURS.can_transition_to(ApplicationStatus.VALIDE)

    def test_en_cours_can_transition_to_refuse(self):
        assert ApplicationStatus.EN_COURS.can_transition_to(ApplicationStatus.REFUSE)

    def test_valide_is_final(self):
        assert not ApplicationStatus.VALIDE.can_transition_to(ApplicationStatus.EN_COURS)
        assert not ApplicationStatus.VALIDE.can_transition_to(ApplicationStatus.REFUSE)

    def test_refuse_is_final(self):
        assert not ApplicationStatus.REFUSE.can_transition_to(ApplicationStatus.EN_COURS)
        assert not ApplicationStatus.REFUSE.can_transition_to(ApplicationStatus.VALIDE)


class TestJobPosting:
    """Tests for JobPosting entity."""

    def _create_valid_posting(self, **kwargs) -> JobPosting:
        """Create a valid JobPosting for testing."""
        defaults = {
            "opportunity_id": uuid4(),
            "title": "Développeur Senior Python",
            "description": "D" * 500,  # Min 500 chars
            "qualifications": "Q" * 150,  # Min 150 chars
            "location_country": "France",
            "contract_types": [ContractType.FREELANCE],
            "skills": ["Python", "FastAPI"],
        }
        defaults.update(kwargs)
        return JobPosting(**defaults)

    def test_create_posting(self):
        posting = self._create_valid_posting()
        assert posting.status == JobPostingStatus.DRAFT
        assert posting.application_token is not None
        assert len(posting.application_token) > 0

    def test_create_posting_generates_unique_token(self):
        posting1 = self._create_valid_posting()
        posting2 = self._create_valid_posting()
        assert posting1.application_token != posting2.application_token

    def test_validate_title_too_short(self):
        posting = self._create_valid_posting(title="ABC")
        errors = posting.validate_for_publication()
        assert any("titre" in e or "5" in e for e in errors)

    def test_validate_title_too_long(self):
        posting = self._create_valid_posting(title="T" * 101)
        errors = posting.validate_for_publication()
        assert any("titre" in e or "100" in e for e in errors)

    def test_validate_description_too_short(self):
        posting = self._create_valid_posting(description="D" * 499)
        errors = posting.validate_for_publication()
        assert any("description" in e for e in errors)

    def test_validate_description_too_long(self):
        posting = self._create_valid_posting(description="D" * 3001)
        errors = posting.validate_for_publication()
        assert any("description" in e for e in errors)

    def test_validate_qualifications_too_short(self):
        posting = self._create_valid_posting(qualifications="Q" * 149)
        errors = posting.validate_for_publication()
        assert any("qualifications" in e for e in errors)

    def test_validate_qualifications_too_long(self):
        posting = self._create_valid_posting(qualifications="Q" * 3001)
        errors = posting.validate_for_publication()
        assert any("qualifications" in e for e in errors)

    def test_validate_empty_contract_types(self):
        posting = self._create_valid_posting(contract_types=[])
        errors = posting.validate_for_publication()
        assert any("contrat" in e for e in errors)

    def test_publish_draft_posting(self):
        posting = self._create_valid_posting()
        posting.publish()
        assert posting.status == JobPostingStatus.PUBLISHED
        assert posting.turnoverit_reference is not None
        assert posting.published_at is not None

    def test_publish_closed_raises_error(self):
        posting = self._create_valid_posting()
        posting.publish()
        posting.close()
        with pytest.raises(ValueError):
            posting.publish()

    def test_close_published_posting(self):
        posting = self._create_valid_posting()
        posting.publish()
        posting.close()
        assert posting.status == JobPostingStatus.CLOSED
        assert posting.closed_at is not None

    def test_close_draft_posting(self):
        posting = self._create_valid_posting()
        posting.close()
        assert posting.status == JobPostingStatus.CLOSED

    def test_turnoverit_reference_auto_generated(self):
        posting = self._create_valid_posting()
        assert posting.turnoverit_reference is not None
        assert posting.turnoverit_reference.startswith("ESN-")


class TestJobApplication:
    """Tests for JobApplication entity."""

    def _create_valid_application(self, **kwargs) -> JobApplication:
        """Create a valid JobApplication for testing."""
        defaults = {
            "job_posting_id": uuid4(),
            "first_name": "Jean",
            "last_name": "Dupont",
            "email": "jean.dupont@example.com",
            "phone": "+33612345678",
            "job_title": "Développeur Python Senior",
            "availability": "asap",
            "employment_status": "freelance",
            "english_level": "professional",
            "tjm_current": 450.0,
            "tjm_desired": 550.0,
            "tjm_min": 450.0,
            "tjm_max": 550.0,
            "availability_date": date.today() + timedelta(days=30),
            "cv_s3_key": "cvs/2024/01/cv-uuid.pdf",
            "cv_filename": "CV_Jean_Dupont.pdf",
        }
        defaults.update(kwargs)
        return JobApplication(**defaults)

    def test_create_application(self):
        application = self._create_valid_application()
        assert application.status == ApplicationStatus.EN_COURS
        assert application.is_read is False
        assert application.full_name == "Jean Dupont"

    def test_full_name_formatted(self):
        application = self._create_valid_application(
            first_name="Jean-Pierre", last_name="De La Fontaine"
        )
        assert application.full_name_formatted == "Jean-Pierre DE LA FONTAINE"

    def test_tjm_range_uses_current_desired(self):
        """tjm_range uses tjm_current/tjm_desired when available."""
        application = self._create_valid_application(
            tjm_current=450, tjm_desired=550, tjm_min=400, tjm_max=500
        )
        assert "450" in application.tjm_range
        assert "550" in application.tjm_range

    def test_tjm_range_fallback_to_min_max(self):
        """tjm_range falls back to tjm_min/tjm_max when current/desired are None."""
        application = self._create_valid_application(
            tjm_current=None, tjm_desired=None, tjm_min=400, tjm_max=500
        )
        assert "400" in application.tjm_range
        assert "500" in application.tjm_range

    def test_change_status_valid_transition(self):
        application = self._create_valid_application()
        user_id = uuid4()
        application.change_status(ApplicationStatus.VALIDE, user_id, "Profil intéressant")
        assert application.status == ApplicationStatus.VALIDE
        assert len(application.status_history) == 1
        assert application.status_history[0]["from_status"] == "en_cours"
        assert application.status_history[0]["to_status"] == "valide"
        assert application.status_history[0]["comment"] == "Profil intéressant"

    def test_change_status_invalid_transition_raises_error(self):
        application = self._create_valid_application()
        # First validate the application (makes it final)
        application.change_status(ApplicationStatus.VALIDE, uuid4())
        # Then try to change it again - should fail
        with pytest.raises(ValueError):
            application.change_status(ApplicationStatus.REFUSE, uuid4())

    def test_set_matching_score(self):
        application = self._create_valid_application()
        details = {
            "strengths": ["Expérience Python", "Compétences FastAPI"],
            "gaps": ["Pas d'expérience AWS"],
            "summary": "Bon profil technique",
        }
        application.set_matching_score(75, details)
        assert application.matching_score == 75
        assert application.matching_details == details

    def test_set_matching_score_clamped_at_100(self):
        application = self._create_valid_application()
        application.set_matching_score(150, {})
        assert application.matching_score == 100

    def test_set_matching_score_clamped_at_0(self):
        application = self._create_valid_application()
        application.set_matching_score(-10, {})
        assert application.matching_score == 0

    def test_mark_as_read(self):
        application = self._create_valid_application()
        assert application.is_read is False
        result = application.mark_as_read()
        assert result is True
        assert application.is_read is True
        # Second call should return False (already read)
        result = application.mark_as_read()
        assert result is False

    def test_add_note(self):
        application = self._create_valid_application()
        application.add_note("À rappeler la semaine prochaine")
        assert application.notes == "À rappeler la semaine prochaine"

    def test_status_display(self):
        application = self._create_valid_application()
        assert application.status.display_name == "En cours"
        application.change_status(ApplicationStatus.VALIDE, uuid4())
        assert application.status.display_name == "Validé"

    def test_workflow_to_valide(self):
        """Test complete workflow from en_cours to validated."""
        application = self._create_valid_application()
        user_id = uuid4()

        # Mark as read first
        application.mark_as_read()
        assert application.is_read is True

        # en_cours -> valide
        application.change_status(ApplicationStatus.VALIDE, user_id, "Candidat retenu")
        assert application.status == ApplicationStatus.VALIDE
        assert application.status.is_final
        assert application.status.is_positive_final

        # Verify history
        assert len(application.status_history) == 1

    def test_workflow_to_refuse(self):
        """Test rejection workflow."""
        application = self._create_valid_application()
        user_id = uuid4()

        # en_cours -> refuse (direct)
        application.change_status(ApplicationStatus.REFUSE, user_id, "Profil non adapté")
        assert application.status == ApplicationStatus.REFUSE
        assert application.status.is_final
        assert not application.status.is_positive_final
        assert len(application.status_history) == 1
