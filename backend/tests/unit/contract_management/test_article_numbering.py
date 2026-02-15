"""Tests for dynamic article numbering."""

import pytest

from app.contract_management.domain.services.article_numbering import compute_article_numbers


class TestArticleNumbering:
    """Tests for dynamic article numbering."""

    def test_all_clauses_enabled(self):
        """Given all clauses enabled, numbering should be sequential."""
        config = {
            "include_confidentiality": True,
            "include_non_compete": True,
            "include_intellectual_property": True,
            "include_liability": True,
        }
        numbers = compute_article_numbers(config)

        assert numbers["objet"] == 1
        assert numbers["duree"] == 2
        assert numbers["conditions_financieres"] == 3
        assert numbers["modalites_facturation"] == 4
        assert numbers["obligations_prestataire"] == 5
        assert numbers["confidentialite"] == 6
        assert numbers["non_concurrence"] == 7
        assert numbers["propriete_intellectuelle"] == 8
        assert numbers["responsabilite"] == 9
        assert numbers["resiliation"] == 10
        assert numbers["droit_applicable"] == 11

    def test_no_optional_clauses(self):
        """Given no optional clauses, articles are renumbered correctly."""
        config = {
            "include_confidentiality": False,
            "include_non_compete": False,
            "include_intellectual_property": False,
            "include_liability": False,
        }
        numbers = compute_article_numbers(config)

        assert numbers["objet"] == 1
        assert numbers["obligations_prestataire"] == 5
        assert "confidentialite" not in numbers
        assert "non_concurrence" not in numbers
        assert numbers["resiliation"] == 6
        assert numbers["droit_applicable"] == 7

    def test_partial_clauses(self):
        """Given some clauses enabled, numbering adjusts correctly."""
        config = {
            "include_confidentiality": True,
            "include_non_compete": False,
            "include_intellectual_property": True,
            "include_liability": False,
        }
        numbers = compute_article_numbers(config)

        assert numbers["confidentialite"] == 6
        assert "non_concurrence" not in numbers
        assert numbers["propriete_intellectuelle"] == 7
        assert "responsabilite" not in numbers
        assert numbers["resiliation"] == 8
