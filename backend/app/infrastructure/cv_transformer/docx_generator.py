"""DOCX document generator using templates."""

import io
from typing import Any

from docxtpl import DocxTemplate


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
        formations = {**default_formations, **(cv_data.get("formations") or {})}
        experiences = cv_data.get("experiences") or []

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

        return {
            "profil": profil,
            "resume_competences": resume_competences,
            "formations": formations,
            "experiences": experiences,
        }
