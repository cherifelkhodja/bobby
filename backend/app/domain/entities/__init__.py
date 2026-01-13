"""Domain entities - core business objects."""

from app.domain.entities.business_lead import BusinessLead, BusinessLeadStatus
from app.domain.entities.candidate import Candidate
from app.domain.entities.cooptation import Cooptation
from app.domain.entities.cv_template import CvTemplate
from app.domain.entities.cv_transformation_log import CvTransformationLog
from app.domain.entities.invitation import Invitation
from app.domain.entities.opportunity import Opportunity
from app.domain.entities.user import User

__all__ = [
    "BusinessLead",
    "BusinessLeadStatus",
    "Candidate",
    "Cooptation",
    "CvTemplate",
    "CvTransformationLog",
    "Invitation",
    "Opportunity",
    "User",
]
