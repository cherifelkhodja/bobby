"""Magic link purpose value object."""

from enum import Enum


class MagicLinkPurpose(str, Enum):
    """Purpose of a magic link sent to a third party."""

    DOCUMENT_UPLOAD = "document_upload"
    CONTRACT_REVIEW = "contract_review"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable purpose name."""
        names = {
            MagicLinkPurpose.DOCUMENT_UPLOAD: "Upload de documents",
            MagicLinkPurpose.CONTRACT_REVIEW: "Revue du contrat",
        }
        return names[self]
