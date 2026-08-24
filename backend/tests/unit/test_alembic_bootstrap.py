"""Tests de l'amorçage de `alembic_version`.

Ce qui est vérifié ici sans base : que la table d'empreintes couvre toute la
chaîne des migrations — sans quoi l'amorçage ne saurait pas lire une base
récente —, que chaque empreinte se traduit bien en requête, et que le choix de
la révision refuse tout ce qui n'est pas certain.

Le comportement contre une vraie base est vérifié à part, sur un PostgreSQL de
test (voir `docs/ops/reparer-alembic-version.md`).
"""

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from scripts.alembic_schema_fingerprints import DATA_ONLY, FINGERPRINTS  # noqa: E402
from scripts.bootstrap_alembic_version import chain, pick, probe_of, uncovered  # noqa: E402


class TestCouverture:
    """La table d'empreintes doit suivre les migrations."""

    def test_toute_la_chaine_est_couverte(self):
        """Une migration ajoutée sans régénérer la table casse la lecture d'une base."""
        oubliees = uncovered(chain())
        assert not oubliees, (
            "révisions absentes de la table d'empreintes : "
            f"{', '.join(oubliees)} — relancer scripts/generer_empreintes_alembic.py"
        )

    def test_la_tete_est_reconnaissable(self):
        """Le cas courant — une base à jour — doit toujours pouvoir être reconnu."""
        assert chain()[-1] in FINGERPRINTS

    def test_les_deux_ensembles_sont_disjoints(self):
        assert not (set(FINGERPRINTS) & DATA_ONLY)

    @pytest.mark.parametrize("revision", sorted(FINGERPRINTS))
    def test_chaque_empreinte_se_traduit_en_requete(self, revision):
        requete, params = probe_of(FINGERPRINTS[revision][0])
        assert requete.startswith("SELECT")
        assert params


class TestChoixDeLaRevision:
    """Ce que l'amorçage accepte d'inscrire, et ce qu'il refuse."""

    revisions = ["001", "002", "003", "004"]

    def test_la_derniere_empreinte_vraie_est_retenue(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.bootstrap_alembic_version.FINGERPRINTS",
            dict.fromkeys(self.revisions, ("table:x", True)),
        )
        trouvee, raison = pick(
            self.revisions, {"001": True, "002": True, "003": False, "004": False}
        )
        assert trouvee == "002"
        assert "002" in raison

    def test_une_base_a_jour_donne_la_tete(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.bootstrap_alembic_version.FINGERPRINTS",
            dict.fromkeys(self.revisions, ("table:x", True)),
        )
        trouvee, _ = pick(self.revisions, dict.fromkeys(self.revisions, True))
        assert trouvee == "004"

    def test_un_trou_dans_le_schema_est_refuse(self, monkeypatch):
        """Une empreinte ancienne fausse sous une récente vraie : schéma abîmé."""
        monkeypatch.setattr(
            "scripts.bootstrap_alembic_version.FINGERPRINTS",
            dict.fromkeys(self.revisions, ("table:x", True)),
        )
        trouvee, raison = pick(
            self.revisions, {"001": False, "002": True, "003": True, "004": False}
        )
        assert trouvee is None
        assert "incohérent" in raison

    def test_une_migration_de_donnees_suivante_est_refusee(self, monkeypatch):
        """Rien ne dit si elle est passée : la rejouer effacerait des données."""
        monkeypatch.setattr(
            "scripts.bootstrap_alembic_version.FINGERPRINTS",
            {"001": ("table:x", True), "002": ("table:y", True), "004": ("table:z", True)},
        )
        trouvee, raison = pick(self.revisions, {"001": True, "002": True, "004": False})
        assert trouvee is None
        assert "003" in raison

    def test_un_schema_etranger_est_refuse(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.bootstrap_alembic_version.FINGERPRINTS",
            dict.fromkeys(self.revisions, ("table:x", True)),
        )
        trouvee, raison = pick(self.revisions, dict.fromkeys(self.revisions, False))
        assert trouvee is None
        assert "n'est pas celui de Bobby" in raison


class TestTraductionDesEmpreintes:
    """Chaque nature d'empreinte donne les bons paramètres."""

    def test_une_table(self):
        _, params = probe_of("table:cm_purchase_orders")
        assert params == {"a": "cm_purchase_orders"}

    def test_une_colonne(self):
        _, params = probe_of("column:tp_third_parties.vat_liable")
        assert params == {"a": "tp_third_parties", "b": "vat_liable"}

    def test_une_longueur_part_en_entier(self):
        """Le pilote refuse une chaîne sur une colonne numérique."""
        _, params = probe_of("coltype:tp_third_parties.entity_category|character varying|20")
        assert params["d"] == 20

    def test_une_nature_inconnue_est_une_erreur(self):
        with pytest.raises(ValueError):
            probe_of("trigger:users.audit")
