"""Mappers between BoondManager DTOs and Domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.domain.entities import Candidate, Opportunity
from app.infrastructure.boond.dtos import BoondOpportunityDTO

if TYPE_CHECKING:
    from app.domain.entities.job_application import JobApplication


# Mapping employment_status → BoondManager typeOf
# 0 = Salarié, 1 = Freelance
EMPLOYMENT_STATUS_TO_TYPEOF = {
    "employee": 0,
    "freelance": 1,
    "both": 0,  # Salarié par défaut si les deux
    "freelance,employee": 0,
    "employee,freelance": 0,
}

# Mapping employment_status → BoondManager desiredContract
# 0 = CDI, 3 = Freelance
EMPLOYMENT_STATUS_TO_CONTRACT = {
    "employee": 0,
    "freelance": 3,
    "both": 0,
    "freelance,employee": 0,
    "employee,freelance": 0,
}

# Employment statuses that include employee
_EMPLOYEE_STATUSES = {"employee", "both", "freelance,employee", "employee,freelance"}
# Employment statuses that are freelance only
_FREELANCE_ONLY_STATUSES = {"freelance"}


@dataclass
class BoondCandidateContext:
    """Extra Boond-specific context for candidate creation.

    Contains data that comes from the opportunity and the validating user,
    not from the candidate entity itself.
    """

    employment_status: str | None = None  # freelance, employee, both
    boond_opportunity_id: str | None = None  # For sourceDetail
    hr_manager_boond_id: str | None = None  # User who validates
    main_manager_boond_id: str | None = None  # Opportunity main manager
    agency_boond_id: str | None = None  # Opportunity agency
    job_title: str | None = None  # Candidate's job title


@dataclass
class BoondAdministrativeData:
    """Administrative data for PUT /candidates/{id}/administrative.

    Maps application salary/TJM fields to Boond administrative attributes.

    Logic per employment_status:
    - employee: salary fields only
    - freelance: TJM fields only
    - both/employee,freelance: salary fields + TJM in administrativeComments
    """

    salary_current: float | None = None
    salary_desired: float | None = None
    tjm_current: float | None = None
    tjm_desired: float | None = None
    desired_contract: int | None = None  # Boond dictionary integer
    administrative_comments: str | None = None  # For TJM info when status is "both"

    @classmethod
    def from_application(cls, application: JobApplication) -> BoondAdministrativeData:
        """Build admin data from application based on employment status.

        - employee: fill salary fields only
        - freelance only: fill TJM fields only
        - both: fill salary fields + TJM info in administrativeComments
        """
        status = application.employment_status or ""
        desired_contract = EMPLOYMENT_STATUS_TO_CONTRACT.get(status, 0)

        if status in _FREELANCE_ONLY_STATUSES:
            # Pure freelance: TJM only
            return cls(
                tjm_current=application.tjm_current,
                tjm_desired=application.tjm_desired,
                desired_contract=desired_contract,
            )

        if status in _EMPLOYEE_STATUSES and status != "employee":
            # Both (employee + freelance): salary fields + TJM in comments
            comments_parts = ["[b0bby] Informations freelance :"]
            tjm_current_str = (
                f"{int(application.tjm_current)}\u20ac/j"
                if application.tjm_current
                else "Non sp\u00e9cifi\u00e9"
            )
            tjm_desired_str = (
                f"{int(application.tjm_desired)}\u20ac/j"
                if application.tjm_desired
                else "Non sp\u00e9cifi\u00e9"
            )
            comments_parts.append(f"TJM actuel : {tjm_current_str}")
            comments_parts.append(f"TJM souhait\u00e9 : {tjm_desired_str}")

            return cls(
                salary_current=application.salary_current,
                salary_desired=application.salary_desired,
                desired_contract=desired_contract,
                administrative_comments="\n".join(comments_parts),
            )

        # Pure employee: salary only
        return cls(
            salary_current=application.salary_current,
            salary_desired=application.salary_desired,
            desired_contract=desired_contract,
        )


def map_boond_opportunity_to_domain(dto: BoondOpportunityDTO) -> Opportunity:
    """Map BoondManager opportunity DTO to domain entity."""
    return Opportunity(
        external_id=str(dto.id),
        title=dto.title,
        reference=dto.reference,
        start_date=dto.startDate,
        end_date=dto.endDate,
        response_deadline=dto.responseDeadline,
        budget=dto.averageDailyRate,
        manager_name=dto.manager_full_name,
        manager_email=dto.managerEmail,
        client_name=dto.clientName,
        description=dto.description,
        skills=dto.skills or [],
        location=dto.location,
    )


def map_candidate_to_boond(
    candidate: Candidate,
    context: BoondCandidateContext | None = None,
) -> dict:
    """Map domain candidate to BoondManager JSON:API payload.

    BoondManager uses JSON:API format: {"data": {"attributes": {...}}}
    Email field must be "email1" (not "email").

    Args:
        candidate: The candidate domain entity.
        context: Optional Boond-specific context (typeOf, source, managers, agency).
    """
    attributes: dict = {
        "firstName": candidate.first_name,
        "lastName": candidate.last_name,
        "email1": str(candidate.email),
        "civility": candidate.civility,
    }

    if candidate.phone:
        attributes["phone1"] = str(candidate.phone)

    if candidate.daily_rate is not None:
        attributes["averageDailyPriceForSale"] = candidate.daily_rate

    if candidate.note:
        attributes["internalNote"] = candidate.note

    # Add Boond-specific fields from context
    if context:
        # title: candidate's job title
        if context.job_title:
            attributes["title"] = context.job_title

        # typeOf: 0=Salarié, 1=Freelance
        if context.employment_status:
            attributes["typeOf"] = EMPLOYMENT_STATUS_TO_TYPEOF.get(context.employment_status, 0)

        # Source: 6 = Annonce, sourceDetail = Boond opportunity ID
        attributes["source"] = 6
        if context.boond_opportunity_id:
            attributes["sourceDetail"] = context.boond_opportunity_id

    # Build relationships
    relationships: dict = {}
    if context:
        if context.hr_manager_boond_id:
            relationships["hrManager"] = {
                "data": {"id": int(context.hr_manager_boond_id), "type": "resource"}
            }
        if context.main_manager_boond_id:
            relationships["mainManager"] = {
                "data": {"id": int(context.main_manager_boond_id), "type": "resource"}
            }
        if context.agency_boond_id:
            relationships["agency"] = {
                "data": {"id": int(context.agency_boond_id), "type": "agency"}
            }

    payload: dict = {
        "data": {
            "attributes": attributes,
        }
    }

    if relationships:
        payload["data"]["relationships"] = relationships

    return payload


def map_candidate_administrative_to_boond(
    candidate_id: str,
    admin_data: BoondAdministrativeData,
) -> dict:
    """Map administrative data to BoondManager PUT /candidates/{id}/administrative payload.

    Populates salary (actualSalary, desiredSalary) and TJM (actualAverageDailyCost,
    desiredAverageDailyCost) based on the application data.
    """
    attributes: dict = {}

    if admin_data.salary_current is not None:
        attributes["actualSalary"] = admin_data.salary_current

    if admin_data.salary_desired is not None or admin_data.salary_current is not None:
        attributes["desiredSalary"] = {
            "min": admin_data.salary_current or admin_data.salary_desired,
            "max": admin_data.salary_desired or admin_data.salary_current,
        }

    if admin_data.tjm_current is not None:
        attributes["actualAverageDailyCost"] = admin_data.tjm_current

    if admin_data.tjm_desired is not None or admin_data.tjm_current is not None:
        attributes["desiredAverageDailyCost"] = {
            "min": admin_data.tjm_current or admin_data.tjm_desired,
            "max": admin_data.tjm_desired or admin_data.tjm_current,
        }

    if admin_data.desired_contract is not None:
        attributes["desiredContract"] = admin_data.desired_contract

    if admin_data.administrative_comments:
        attributes["administrativeComments"] = admin_data.administrative_comments

    return {
        "data": {
            "id": candidate_id,
            "type": "candidate",
            "attributes": attributes,
        }
    }


def map_opportunity_to_read_model(opportunity: Opportunity) -> dict:
    """Map opportunity to dictionary for caching."""
    return {
        "id": str(opportunity.id),
        "external_id": opportunity.external_id,
        "title": opportunity.title,
        "reference": opportunity.reference,
        "start_date": opportunity.start_date.isoformat() if opportunity.start_date else None,
        "end_date": opportunity.end_date.isoformat() if opportunity.end_date else None,
        "response_deadline": (
            opportunity.response_deadline.isoformat() if opportunity.response_deadline else None
        ),
        "budget": opportunity.budget,
        "manager_name": opportunity.manager_name,
        "client_name": opportunity.client_name,
        "is_active": opportunity.is_active,
    }


def format_analyses_as_boond_html(
    matching_details: dict[str, Any] | None,
    cv_quality: dict[str, Any] | None,
    candidate_name: str = "",
    job_title: str = "",
) -> str:
    """Format matching + CV quality analyses as HTML for a BoondManager action text.

    Args:
        matching_details: The matching analysis dict (enhanced or legacy format).
        cv_quality: The CV quality evaluation dict.
        candidate_name: Candidate full name for the header.
        job_title: Job posting title for context.

    Returns:
        HTML-formatted string for the Boond action text field.
    """
    parts: list[str] = []

    parts.append(
        f"<div><b>[b0bby] Analyse candidature{f' - {candidate_name}' if candidate_name else ''}</b></div>"
    )
    if job_title:
        parts.append(f"<div>Poste : {job_title}</div>")
    parts.append("<div>&nbsp;</div>")

    # --- Matching Analysis ---
    if matching_details:
        score_global = matching_details.get("score_global", matching_details.get("score", 0))
        parts.append(f"<div><b>MATCHING CV / OFFRE : {score_global}%</b></div>")

        # Scores details
        scores_details = matching_details.get("scores_details")
        if scores_details:
            parts.append("<div>&nbsp;</div>")
            parts.append("<div><u>Scores d\u00e9taill\u00e9s :</u></div>")
            labels = {
                "competences_techniques": "Comp\u00e9tences techniques",
                "experience": "Exp\u00e9rience",
                "formation": "Formation",
                "soft_skills": "Soft skills",
            }
            for key, label in labels.items():
                val = scores_details.get(key)
                if val is not None:
                    parts.append(f"<div>- {label} : {val}%</div>")

        # Matched skills
        competences_matchees = matching_details.get("competences_matchees", [])
        if competences_matchees:
            parts.append("<div>&nbsp;</div>")
            parts.append(
                f"<div><u>Comp\u00e9tences match\u00e9es :</u> {', '.join(competences_matchees)}</div>"
            )

        # Missing skills
        competences_manquantes = matching_details.get(
            "competences_manquantes", matching_details.get("gaps", [])
        )
        if competences_manquantes:
            parts.append(
                f"<div><u>Comp\u00e9tences manquantes :</u> {', '.join(competences_manquantes)}</div>"
            )

        # Strengths
        points_forts = matching_details.get("points_forts", matching_details.get("strengths", []))
        if points_forts:
            parts.append("<div>&nbsp;</div>")
            parts.append("<div><u>Points forts :</u></div>")
            for pf in points_forts:
                parts.append(f"<div>- {pf}</div>")

        # Vigilance points
        points_vigilance = matching_details.get("points_vigilance", [])
        if points_vigilance:
            parts.append("<div>&nbsp;</div>")
            parts.append("<div><u>Points de vigilance :</u></div>")
            for pv in points_vigilance:
                parts.append(f"<div>- {pv}</div>")

        # Synthesis
        synthese = matching_details.get("synthese", matching_details.get("summary", ""))
        if synthese:
            parts.append("<div>&nbsp;</div>")
            parts.append(f"<div><u>Synth\u00e8se :</u> {synthese}</div>")

        # Recommendation
        recommandation = matching_details.get("recommandation", {})
        if recommandation:
            niveau = recommandation.get("niveau", "")
            action = recommandation.get("action_suggeree", "")
            niveau_display = {"fort": "Fort", "moyen": "Moyen", "faible": "Faible"}.get(
                niveau, niveau
            )
            if niveau_display:
                parts.append(f"<div><u>Recommandation :</u> {niveau_display}")
                if action:
                    parts.append(f" - {action}")
                parts.append("</div>")

    # --- CV Quality ---
    if cv_quality:
        parts.append("<div>&nbsp;</div>")
        parts.append("<div>---</div>")
        parts.append("<div>&nbsp;</div>")

        note_globale = cv_quality.get("note_globale", 0)
        classification = cv_quality.get("classification", "")
        niveau_exp = cv_quality.get("niveau_experience", "")
        annees = cv_quality.get("annees_experience", 0)

        parts.append(f"<div><b>QUALIT\u00c9 CV : {note_globale}/20 ({classification})</b></div>")
        if niveau_exp or annees:
            parts.append(f"<div>Niveau : {niveau_exp}{f' ({annees} ans)' if annees else ''}</div>")

        # Detail scores
        details_notes = cv_quality.get("details_notes", {})
        if details_notes:
            parts.append("<div>&nbsp;</div>")
            parts.append("<div><u>D\u00e9tails :</u></div>")

            for key, label in [
                ("stabilite_missions", "Stabilit\u00e9 missions"),
                ("qualite_comptes", "Qualit\u00e9 comptes"),
                ("parcours_scolaire", "Parcours scolaire"),
                ("continuite_parcours", "Continuit\u00e9 parcours"),
            ]:
                detail = details_notes.get(key, {})
                if detail:
                    note = detail.get("note", 0)
                    max_note = detail.get("max", 0)
                    comment = detail.get("commentaire", "")
                    line = f"<div>- {label} : {note}/{max_note}"
                    if comment:
                        line += f" ({comment})"
                    line += "</div>"
                    parts.append(line)

            bonus = details_notes.get("bonus_malus", {})
            if bonus:
                valeur = bonus.get("valeur", 0)
                raisons = bonus.get("raisons", [])
                sign = "+" if valeur >= 0 else ""
                line = f"<div>- Bonus/malus : {sign}{valeur}"
                if raisons:
                    line += f" ({', '.join(raisons)})"
                line += "</div>"
                parts.append(line)

        # Points forts / faibles CV
        cv_points_forts = cv_quality.get("points_forts", [])
        if cv_points_forts:
            parts.append("<div>&nbsp;</div>")
            parts.append("<div><u>Points forts CV :</u></div>")
            for pf in cv_points_forts:
                parts.append(f"<div>- {pf}</div>")

        cv_points_faibles = cv_quality.get("points_faibles", [])
        if cv_points_faibles:
            parts.append("<div><u>Points faibles CV :</u></div>")
            for pf in cv_points_faibles:
                parts.append(f"<div>- {pf}</div>")

        # Synthesis
        cv_synthese = cv_quality.get("synthese", "")
        if cv_synthese:
            parts.append("<div>&nbsp;</div>")
            parts.append(f"<div><u>Synth\u00e8se CV :</u> {cv_synthese}</div>")

    parts.append("<div>&nbsp;</div>")
    parts.append("<div><i>Analyse g\u00e9n\u00e9r\u00e9e automatiquement par b0bby</i></div>")

    return "\n".join(parts)
