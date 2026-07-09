"""YouSign API v3 client for electronic signatures."""

import httpx
import structlog

logger = structlog.get_logger()


class YouSignClient:
    """Client for YouSign API v3.

    Handles creating signature procedures, uploading documents,
    adding signers, and retrieving signed documents.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.yousign.app/v3") -> None:
        self._api_key = api_key
        self._base_url = base_url

    def _headers(self) -> dict[str, str]:
        """Return authorization headers."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def create_procedure(
        self,
        document_content: bytes,
        document_name: str,
        signer_name: str,
        signer_email: str,
        signer_phone: str | None = None,
        signer_country_code: str = "+33",
    ) -> str:
        """Create a full signature procedure.

        Args:
            document_content: PDF content.
            document_name: Document name.
            signer_name: Name of the signer.
            signer_email: Email of the signer.
            signer_phone: Phone of the signer.
            signer_country_code: Indicatif téléphonique du signataire
                (par défaut "+33" / France ; à dériver du pays du signataire
                lorsque l'information est disponible côté appelant).

        Returns:
            Signature request ID.
        """
        if not self._api_key:
            logger.warning("yousign_api_key_not_configured")
            raise ValueError("YouSign API key not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Create signature request
            sr_response = await client.post(
                f"{self._base_url}/signature_requests",
                headers=self._headers(),
                json={
                    "name": document_name,
                    "delivery_mode": "email",
                    "timezone": "Europe/Paris",
                },
            )
            sr_response.raise_for_status()
            sr_data = sr_response.json()
            sr_id = sr_data["id"]

            # Step 2: Upload document
            upload_headers = {
                "Authorization": f"Bearer {self._api_key}",
            }
            doc_response = await client.post(
                f"{self._base_url}/signature_requests/{sr_id}/documents",
                headers=upload_headers,
                files={"file": (document_name, document_content, "application/pdf")},
                data={"nature": "signable_document"},
            )
            doc_response.raise_for_status()
            doc_data = doc_response.json()
            doc_id = doc_data["id"]

            # Step 3: Add signer
            # YouSign exige un first_name ET un last_name non vides. Si le nom
            # ne contient pas d'espace, on réutilise le nom complet pour les deux
            # champs plutôt que de laisser last_name vide (ce qui ferait échouer
            # la validation de l'API).
            name_parts = signer_name.strip().split(" ", 1)
            signer_first_name = name_parts[0]
            signer_last_name = name_parts[1] if len(name_parts) > 1 else name_parts[0]
            signer_payload = {
                "info": {
                    "first_name": signer_first_name,
                    "last_name": signer_last_name,
                    "email": signer_email,
                    "locale": "fr",
                },
                "signature_level": "electronic_signature",
                "fields": [
                    {
                        "document_id": doc_id,
                        "type": "signature",
                        "page": 1,
                        "x": 100,
                        "y": 700,
                        "width": 200,
                        "height": 50,
                    }
                ],
            }
            if signer_phone:
                signer_payload["info"]["phone_number"] = {
                    # Indicatif désormais paramétrable (défaut FR "+33").
                    "country_code": signer_country_code,
                    "number": signer_phone,
                }

            signer_response = await client.post(
                f"{self._base_url}/signature_requests/{sr_id}/signers",
                headers=self._headers(),
                json=signer_payload,
            )
            signer_response.raise_for_status()

            # Step 4: Activate the procedure
            activate_response = await client.post(
                f"{self._base_url}/signature_requests/{sr_id}/activate",
                headers=self._headers(),
            )
            activate_response.raise_for_status()

            logger.info(
                "yousign_procedure_created",
                signature_request_id=sr_id,
                signer_email=signer_email,
            )
            return sr_id

    async def get_procedure_status(self, procedure_id: str) -> str:
        """Get the status of a signature request."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self._base_url}/signature_requests/{procedure_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json().get("status", "unknown")

    async def get_signed_document(self, procedure_id: str) -> bytes:
        """Download the signed document."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get documents list
            docs_response = await client.get(
                f"{self._base_url}/signature_requests/{procedure_id}/documents",
                headers=self._headers(),
            )
            docs_response.raise_for_status()
            documents = docs_response.json()

            if not documents:
                raise ValueError(f"No documents found for procedure {procedure_id}")

            doc_id = documents[0]["id"]

            # Download signed version
            dl_response = await client.get(
                f"{self._base_url}/signature_requests/{procedure_id}/documents/{doc_id}/download",
                headers=self._headers(),
            )
            dl_response.raise_for_status()
            return dl_response.content
