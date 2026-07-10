"""Use case: Create a contract request manually (no Boond webhook)."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from app.contract_management.domain.entities.contract_request import ContractRequest

logger = structlog.get_logger()


@dataclass
class ManualContractRequestCommand:
    """Data for a manual contract request creation."""

    boond_resource_id: int
    commercial_email: str = ""
    company_id: UUID | None = None
    client_name: str | None = None
    mission_title: str | None = None
    consultant_civility: str | None = None
    consultant_first_name: str | None = None
    consultant_last_name: str | None = None
    consultant_email: str | None = None
    consultant_phone: str | None = None


class CreateManualContractRequestUseCase:
    """Create a ContractRequest from scratch (manual ADV entry).

    Unlike the webhook flow there is no positioning: the ADV supplies the Boond
    resource ID directly. When a CRM service is available, the consultant identity
    (and the commercial, via the resource's manager) is best-effort enriched from
    Boond; a lookup failure never blocks creation. The request starts in
    PENDING_COMMERCIAL_VALIDATION, then follows the standard flow.
    """

    def __init__(self, contract_request_repository, crm_service=None, user_repository=None) -> None:
        self._cr_repo = contract_request_repository
        self._crm = crm_service
        self._user_repo = user_repository

    async def execute(self, command: ManualContractRequestCommand) -> ContractRequest:
        """Execute the use case."""
        consultant_civility = command.consultant_civility
        consultant_first_name = command.consultant_first_name
        consultant_last_name = command.consultant_last_name
        consultant_email = command.consultant_email
        consultant_phone = command.consultant_phone
        commercial_email = command.commercial_email

        # Best-effort Boond enrichment from the resource id (never blocks creation).
        if self._crm is not None:
            info = None
            try:
                info = await self._crm.get_candidate_info(command.boond_resource_id, "resource")
            except Exception as exc:
                logger.warning(
                    "manual_cr_boond_lookup_failed",
                    resource_id=command.boond_resource_id,
                    error=str(exc),
                )
            if info:
                consultant_civility = info.get("civility") or consultant_civility
                consultant_first_name = info.get("first_name") or consultant_first_name
                consultant_last_name = info.get("last_name") or consultant_last_name
                consultant_email = info.get("email") or consultant_email
                consultant_phone = info.get("phone") or consultant_phone
                manager_id = info.get("manager_id")
                if manager_id and self._user_repo:
                    user = None
                    try:
                        user = await self._user_repo.get_by_boond_resource_id(str(manager_id))
                    except Exception:
                        user = None
                    if user and getattr(user, "email", None):
                        commercial_email = str(user.email)

        reference = await self._cr_repo.get_next_provisional_reference()

        cr = ContractRequest(
            provisional_reference=reference,
            trigger_type="manual",
            boond_resource_id=command.boond_resource_id,
            boond_consultant_type="resource",
            commercial_email=commercial_email or "",
            company_id=command.company_id,
            client_name=command.client_name,
            mission_title=command.mission_title,
            consultant_civility=consultant_civility,
            consultant_first_name=consultant_first_name,
            consultant_last_name=consultant_last_name,
            consultant_email=consultant_email,
            consultant_phone=consultant_phone,
        )
        saved = await self._cr_repo.save(cr)

        logger.info(
            "manual_contract_request_created",
            cr_id=str(saved.id),
            reference=reference,
            boond_resource_id=command.boond_resource_id,
        )
        return saved
