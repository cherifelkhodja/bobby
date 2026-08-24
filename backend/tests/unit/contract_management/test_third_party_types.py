"""Types de tiers acceptés par la contractualisation.

Le type détermine trois choses : la nécessité d'un contrat dans Bobby, les
chartes opposables au consultant, et le `typeOf` du contrat créé dans Boond.
"""

import pytest
from pydantic import ValidationError

from app.contract_management.api.schemas import (
    CommercialValidationRequest,
    SupplierDossierCreate,
)
from app.contract_management.application.boond_mappings import (
    CONTRACT_TYPE_BY_THIRD_PARTY_TYPE,
    resource_type_of,
    state_reason_type_of,
)
from app.third_party.domain.value_objects.third_party_type import (
    EXTERNAL_THIRD_PARTY_TYPES,
    ThirdPartyType,
)


class TestPortageCommercial:
    """Le portage commercial, ajouté aux côtés du portage salarial."""

    def test_the_type_exists_and_is_named(self):
        assert ThirdPartyType.PORTAGE_COMMERCIAL.value == "portage_commercial"
        assert ThirdPartyType.PORTAGE_COMMERCIAL.display_name == "Portage commercial"

    def test_it_requires_a_contract(self):
        """Comme tout intervenant externe, il passe par un contrat cadre."""
        assert ThirdPartyType.PORTAGE_COMMERCIAL.requires_contract

    def test_its_consultants_are_external(self):
        """Ce qui décide des chartes opposables au consultant."""
        assert "portage_commercial" in EXTERNAL_THIRD_PARTY_TYPES
        assert "salarie" not in EXTERNAL_THIRD_PARTY_TYPES

    def test_the_boond_contract_type(self):
        """typeOf 7 côté Boond, distinct du portage salarial (6)."""
        assert CONTRACT_TYPE_BY_THIRD_PARTY_TYPE["portage_commercial"] == 7
        assert CONTRACT_TYPE_BY_THIRD_PARTY_TYPE["portage_salarial"] == 6

    def test_the_boond_resource_type(self):
        """« Consultant Portage Commercial » (10) a son propre type dans Boond."""
        assert resource_type_of("portage_commercial") == 10

    def test_the_state_reason_stays_internal_or_external(self):
        """Le motif du changement d'état ne connaît que ces deux valeurs."""
        assert state_reason_type_of("portage_commercial") == 1
        assert state_reason_type_of("salarie") == 0

    def test_opening_a_supplier_dossier_accepts_it(self):
        dossier = SupplierDossierCreate(
            third_party_type="portage_commercial",
            contact_email="contact@porteur.fr",
            notify_third_party=True,
            skip_documents=False,
        )
        assert dossier.third_party_type == "portage_commercial"

    def test_commercial_validation_accepts_it(self):
        validation = CommercialValidationRequest(
            third_party_type="portage_commercial",
            contact_email="contact@porteur.fr",
        )
        assert validation.third_party_type == "portage_commercial"


class TestAcceptedTypes:
    """Garde-fou sur l'ensemble des types."""

    @pytest.mark.parametrize(
        "third_party_type",
        ["freelance", "sous_traitant", "salarie", "portage_salarial", "portage_commercial"],
    )
    def test_every_type_of_the_enum_is_accepted_by_the_api(self, third_party_type):
        assert ThirdPartyType(third_party_type)
        assert SupplierDossierCreate(
            third_party_type=third_party_type,
            contact_email="contact@fournisseur.fr",
            notify_third_party=True,
            skip_documents=False,
        )

    def test_an_unknown_type_is_refused(self):
        with pytest.raises(ValidationError):
            SupplierDossierCreate(
                third_party_type="mandataire",
                contact_email="contact@fournisseur.fr",
                notify_third_party=True,
                skip_documents=False,
            )


class TestBoondResourceTypes:
    """Classement des ressources dans BoondManager, configuré côté CRM."""

    @pytest.mark.parametrize(
        "third_party_type",
        ["freelance", "sous_traitant", "portage_salarial"],
    )
    def test_the_usual_externals_share_one_type(self, third_party_type):
        """« Consultant Externe » (1) couvre les trois."""
        assert resource_type_of(third_party_type) == 1

    def test_an_employee_is_internal(self):
        assert resource_type_of("salarie") == 0

    def test_an_unknown_type_falls_back_to_external(self):
        """Mieux vaut une ressource externe qu'un consultant compté comme interne."""
        assert resource_type_of(None) == 1
        assert resource_type_of("") == 1
