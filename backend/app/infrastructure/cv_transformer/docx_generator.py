"""DOCX document generator using templates."""

import io
from typing import Any

from docxtpl import DocxTemplate, RichText


class DocxGenerator:
    """Generator for creating DOCX documents from templates."""

    def generate(self, template_content: bytes, cv_data: dict[str, Any]) -> bytes:
        """Generate a DOCX document from a template and CV data.

        Args:
            template_content: Binary content of the DOCX template.
            cv_data: Structured CV data to fill the template.

        Returns:
            Generated DOCX document as bytes.

        Raises:
            ValueError: If generation fails.
        """
        try:
            # Load template from bytes
            template_io = io.BytesIO(template_content)
            doc = DocxTemplate(template_io)

            # Prepare context with CV data
            context = self._prepare_context(cv_data)

            # Render template
            doc.render(context)

            # Save to bytes
            output = io.BytesIO()
            doc.save(output)
            output.seek(0)

            return output.read()

        except Exception as e:
            raise ValueError(f"Erreur lors de la génération du document: {str(e)}")

    def _prepare_context(self, cv_data: dict[str, Any]) -> dict[str, Any]:
        """Prepare the template context from CV data.

        Ensures all expected variables are present to avoid template errors.
        Applies formatting (page breaks, bold text) using RichText.

        Args:
            cv_data: Raw CV data from Gemini.

        Returns:
            Prepared context dictionary.
        """
        # Default structure for missing data
        default_profil = {
            "titre_cible": "",
            "annees_experience": "",
        }

        default_resume = {
            "techniques": {},
            "metiers": [],
            "fonctionnelles": [],
            "langues": [],
        }

        default_formations = {
            "diplomes": [],
            "certifications": [],
        }

        # Merge with defaults
        profil = {**default_profil, **(cv_data.get("profil") or {})}
        resume_competences = {**default_resume, **(cv_data.get("resume_competences") or {})}
        formations_raw = {**default_formations, **(cv_data.get("formations") or {})}
        experiences = cv_data.get("experiences") or []

        # Clean formations: remove None/null years and format properly
        formations = self._nettoyer_formations(formations_raw)

        # Format techniques for easier template rendering
        # Convert dict to list of tuples for iteration in template
        techniques_list = []
        if isinstance(resume_competences.get("techniques"), dict):
            for category, values in resume_competences["techniques"].items():
                techniques_list.append({
                    "categorie": category,
                    "valeurs": values,
                })
        resume_competences["techniques_list"] = techniques_list

        # Format languages with bold (e.g., "Français : Natif" -> Français bold, rest normal)
        langues_formatees = self._formater_langues(resume_competences.get("langues") or [])
        resume_competences["langues_formatees"] = langues_formatees

        # Clean None values in experiences
        for exp in experiences:
            for key in ("contexte", "environnement_technique"):
                val = exp.get(key)
                if val is None or str(val).strip().lower() in ("none", "null"):
                    exp[key] = ""

        # Add page breaks between experiences
        experiences_avec_sauts = self._preparer_experiences_avec_sauts_de_page(experiences)

        return {
            "profil": profil,
            "resume_competences": resume_competences,
            "formations": formations,
            "experiences": experiences_avec_sauts,
        }

    def _formater_langues(self, langues: list) -> list:
        """Format languages with bold language name and normal level.

        Args:
            langues: List of language strings (e.g., ["Français : Natif", "Anglais : Courant"])

        Returns:
            List of RichText objects with formatting.
        """
        langues_formatees = []

        for langue in langues:
            rt = RichText()
            if " : " in langue:
                parties = langue.split(" : ", 1)
                rt.add(parties[0], bold=True)  # Language name in bold
                rt.add(f" : {parties[1]}")     # Level in normal
            else:
                rt.add(langue, bold=True)
            langues_formatees.append(rt)

        return langues_formatees

    def _nettoyer_formations(self, formations: dict[str, Any]) -> dict[str, Any]:
        """Clean formations data by removing None values and formatting properly.

        Args:
            formations: Raw formations data from Gemini.

        Returns:
            Cleaned formations dictionary with formatted display field.
        """
        cleaned = {
            "diplomes": [],
            "certifications": [],
        }

        for diplome in formations.get("diplomes") or []:
            if isinstance(diplome, dict):
                annee = diplome.get("annee")
                libelle = diplome.get("libelle", "")
                # Skip if no libelle
                if not libelle:
                    continue
                # Clean None/null values - set to empty string
                if annee is None or str(annee).lower() in ("none", "null", ""):
                    annee = ""
                # Create display string: "2015: Master" or just "Master" if no year
                display = f"{annee}: {libelle}" if annee else libelle
                cleaned["diplomes"].append({
                    "annee": annee,
                    "libelle": libelle,
                    "display": display,
                })

        for cert in formations.get("certifications") or []:
            if isinstance(cert, dict):
                annee = cert.get("annee")
                libelle = cert.get("libelle", "")
                # Skip if no libelle
                if not libelle:
                    continue
                # Clean None/null values - set to empty string
                if annee is None or str(annee).lower() in ("none", "null", ""):
                    annee = ""
                # Create display string: "2020: AWS" or just "AWS" if no year
                display = f"{annee}: {libelle}" if annee else libelle
                cleaned["certifications"].append({
                    "annee": annee,
                    "libelle": libelle,
                    "display": display,
                })

        return cleaned

    def _preparer_experiences_avec_sauts_de_page(self, experiences: list) -> list:
        """Add page breaks after each experience except the last one.

        Args:
            experiences: List of experience dictionaries.

        Returns:
            List of experiences with 'saut_de_page' RichText field.
        """
        experiences_preparees = []
        total = len(experiences)

        for index, experience in enumerate(experiences):
            exp_copy = experience.copy() if isinstance(experience, dict) else {}
            if index < total - 1:  # No page break after the last experience
                rt = RichText()
                rt.add('\f')  # Form feed character = page break
                exp_copy["saut_de_page"] = rt
            else:
                exp_copy["saut_de_page"] = ""
            experiences_preparees.append(exp_copy)

        return experiences_preparees
