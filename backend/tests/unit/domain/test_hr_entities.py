"""Tests for HR feature domain entities (JobPosting, JobApplication)."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities import (
    JobPosting,
    JobApplication,
    ApplicationStatus,
    JobPostingStatus,
    ContractType,
    RemotePolicy,
    ExperienceLevel,
)
from app.domain.exceptions import (
    InvalidStatusTransitionError,
    InvalidJobPostingError,
    InvalidJobApplicationError,
)


class TestJobPostingStatus:
    """Tests for JobPostingStatus value object."""

    def test_status_values(self):
        assert JobPostingStatus.DRAFT.value == "draft"
        assert JobPostingStatus.PUBLISHED.value == "published"
        assert JobPostingStatus.CLOSED.value == "closed"

    def test_draft_can_transition_to_published(self):
        assert JobPostingStatus.DRAFT.can_transition_to(JobPostingStatus.PUBLISHED)

    def test_published_can_transition_to_closed(self):
        assert JobPostingStatus.PUBLISHED.can_transition_to(JobPostingStatus.CLOSED)

    def test_draft_cannot_transition_to_closed(self):
        assert not JobPostingStatus.DRAFT.can_transition_to(JobPostingStatus.CLOSED)

    def test_closed_cannot_transition(self):
        assert not JobPostingStatus.CLOSED.can_transition_to(JobPostingStatus.DRAFT)
        assert not JobPostingStatus.CLOSED.can_transition_to(JobPostingStatus.PUBLISHED)


class TestApplicationStatus:
    """Tests for ApplicationStatus value object."""

    def test_status_values(self):
        assert ApplicationStatus.NOUVEAU.value == "nouveau"
        assert ApplicationStatus.EN_COURS.value == "en_cours"
        assert ApplicationStatus.ENTRETIEN.value == "entretien"
        assert ApplicationStatus.ACCEPTE.value == "accepte"
        assert ApplicationStatus.REFUSE.value == "refuse"

    def test_nouveau_can_transition_to_en_cours(self):
        assert ApplicationStatus.NOUVEAU.can_transition_to(ApplicationStatus.EN_COURS)

    def test_nouveau_can_transition_to_refuse(self):
        assert ApplicationStatus.NOUVEAU.can_transition_to(ApplicationStatus.REFUSE)

    def test_en_cours_can_transition_to_entretien(self):
        assert ApplicationStatus.EN_COURS.can_transition_to(ApplicationStatus.ENTRETIEN)

    def test_entretien_can_transition_to_accepte(self):
        assert ApplicationStatus.ENTRETIEN.can_transition_to(ApplicationStatus.ACCEPTE)

    def test_accepte_is_final(self):
        assert not ApplicationStatus.ACCEPTE.can_transition_to(ApplicationStatus.REFUSE)

    def test_refuse_is_final(self):
        assert not ApplicationStatus.REFUSE.can_transition_to(ApplicationStatus.ACCEPTE)


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

    def test_title_too_short_raises_error(self):
        with pytest.raises(InvalidJobPostingError, match="titre"):
            self._create_valid_posting(title="ABC")  # Min 5 chars

    def test_title_too_long_raises_error(self):
        with pytest.raises(InvalidJobPostingError, match="titre"):
            self._create_valid_posting(title="T" * 101)  # Max 100 chars

    def test_description_too_short_raises_error(self):
        with pytest.raises(InvalidJobPostingError, match="description"):
            self._create_valid_posting(description="D" * 499)  # Min 500 chars

    def test_description_too_long_raises_error(self):
        with pytest.raises(InvalidJobPostingError, match="description"):
            self._create_valid_posting(description="D" * 3001)  # Max 3000 chars

    def test_qualifications_too_short_raises_error(self):
        with pytest.raises(InvalidJobPostingError, match="qualifications"):
            self._create_valid_posting(qualifications="Q" * 149)  # Min 150 chars

    def test_qualifications_too_long_raises_error(self):
        with pytest.raises(InvalidJobPostingError, match="qualifications"):
            self._create_valid_posting(qualifications="Q" * 3001)  # Max 3000 chars

    def test_empty_contract_types_raises_error(self):
        with pytest.raises(InvalidJobPostingError, match="contrat"):
            self._create_valid_posting(contract_types=[])

    def test_publish_draft_posting(self):
        posting = self._create_valid_posting()
        posting.publish("turnoverit-ref-123")
        assert posting.status == JobPostingStatus.PUBLISHED
        assert posting.turnoverit_reference == "turnoverit-ref-123"
        assert posting.published_at is not None

    def test_publish_non_draft_raises_error(self):
        posting = self._create_valid_posting()
        posting.publish("ref-123")
        with pytest.raises(InvalidStatusTransitionError):
            posting.publish("ref-456")

    def test_close_published_posting(self):
        posting = self._create_valid_posting()
        posting.publish("ref-123")
        posting.close()
        assert posting.status == JobPostingStatus.CLOSED
        assert posting.closed_at is not None

    def test_close_draft_raises_error(self):
        posting = self._create_valid_posting()
        with pytest.raises(InvalidStatusTransitionError):
            posting.close()

    def test_status_display(self):
        posting = self._create_valid_posting()
        assert posting.status_display == "Brouillon"
        posting.publish("ref")
        assert posting.status_display == "Publiée"
        posting.close()
        assert posting.status_display == "Fermée"

    def test_salary_range_display_daily(self):
        posting = self._create_valid_posting(salary_min_daily=400, salary_max_daily=550)
        assert "400" in posting.salary_range_display
        assert "550" in posting.salary_range_display

    def test_salary_range_display_annual(self):
        posting = self._create_valid_posting(salary_min_annual=45000, salary_max_annual=60000)
        assert "45000" in posting.salary_range_display or "45 000" in posting.salary_range_display


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
        assert application.status == ApplicationStatus.NOUVEAU
        assert application.full_name == "Jean DUPONT"

    def test_full_name_format(self):
        application = self._create_valid_application(first_name="Jean-Pierre", last_name="De La Fontaine")
        # Last name should be uppercased
        assert "Jean-Pierre" in application.full_name
        assert "DE LA FONTAINE" in application.full_name

    def test_tjm_range(self):
        application = self._create_valid_application(tjm_min=400, tjm_max=500)
        assert "400" in application.tjm_range
        assert "500" in application.tjm_range

    def test_invalid_tjm_range_raises_error(self):
        with pytest.raises(InvalidJobApplicationError, match="TJM"):
            self._create_valid_application(tjm_min=500, tjm_max=400)

    def test_invalid_email_raises_error(self):
        with pytest.raises(InvalidJobApplicationError, match="email"):
            self._create_valid_application(email="invalid-email")

    def test_invalid_phone_raises_error(self):
        with pytest.raises(InvalidJobApplicationError, match="téléphone"):
            self._create_valid_application(phone="123")

    def test_change_status_valid_transition(self):
        application = self._create_valid_application()
        user_id = uuid4()
        application.change_status(ApplicationStatus.EN_COURS, user_id, "Profil intéressant")
        assert application.status == ApplicationStatus.EN_COURS
        assert len(application.status_history) == 1
        assert application.status_history[0]["from_status"] == "nouveau"
        assert application.status_history[0]["to_status"] == "en_cours"
        assert application.status_history[0]["comment"] == "Profil intéressant"

    def test_change_status_invalid_transition_raises_error(self):
        application = self._create_valid_application()
        with pytest.raises(InvalidStatusTransitionError):
            application.change_status(ApplicationStatus.ACCEPTE, uuid4())

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

    def test_set_matching_score_out_of_range_raises_error(self):
        application = self._create_valid_application()
        with pytest.raises(InvalidJobApplicationError, match="score"):
            application.set_matching_score(101, {})

    def test_set_matching_score_negative_raises_error(self):
        application = self._create_valid_application()
        with pytest.raises(InvalidJobApplicationError, match="score"):
            application.set_matching_score(-1, {})

    def test_update_notes(self):
        application = self._create_valid_application()
        application.update_notes("À rappeler la semaine prochaine")
        assert application.notes == "À rappeler la semaine prochaine"

    def test_status_display(self):
        application = self._create_valid_application()
        assert application.status_display == "Nouveau"
        application.change_status(ApplicationStatus.EN_COURS, uuid4())
        assert application.status_display == "En cours"

    def test_workflow_from_nouveau_to_accepte(self):
        """Test complete workflow from new application to accepted."""
        application = self._create_valid_application()
        user_id = uuid4()

        # nouveau -> en_cours
        application.change_status(ApplicationStatus.EN_COURS, user_id, "CV validé")
        assert application.status == ApplicationStatus.EN_COURS

        # en_cours -> entretien
        application.change_status(ApplicationStatus.ENTRETIEN, user_id, "Entretien planifié")
        assert application.status == ApplicationStatus.ENTRETIEN

        # entretien -> accepte
        application.change_status(ApplicationStatus.ACCEPTE, user_id, "Candidat retenu")
        assert application.status == ApplicationStatus.ACCEPTE

        # Verify history
        assert len(application.status_history) == 3

    def test_workflow_from_nouveau_to_refuse(self):
        """Test rejection workflow."""
        application = self._create_valid_application()
        user_id = uuid4()

        # nouveau -> refuse (direct)
        application.change_status(ApplicationStatus.REFUSE, user_id, "Profil non adapté")
        assert application.status == ApplicationStatus.REFUSE
        assert len(application.status_history) == 1
