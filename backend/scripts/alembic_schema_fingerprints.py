"""Empreintes de schéma : à quoi reconnaître qu'une migration est appliquée.

Table **générée** par `scripts/generer_empreintes_alembic.py`, qui déroule la
chaîne Alembic sur un PostgreSQL réel et retient, pour chaque révision, un objet
qui bascule exactement là — absent partout avant, présent partout après. C'est
ce qui permet à `bootstrap_alembic_version.py` de reconnaître où en est une base
dont la table de suivi a été perdue.

Ne pas éditer à la main : régénérer après l'ajout d'une migration. Un test
vérifie que la chaîne est couverte de bout en bout.

Format : ``révision: (objet, doit_être_présent)``. Les objets sont préfixés par
leur nature — `table:`, `column:`, `coltype:`, `colnull:`, `index:`,
`constraint:`, `policy:`, `rls:`.
"""

# Révisions reconnaissables à un objet du schéma.
FINGERPRINTS: dict[str, tuple[str, bool]] = {
    "001_initial_schema": ("table:candidates", True),
    "002_add_roles_invites": ("table:business_leads", True),
    "003_add_inv_boond_ids": ("column:invitations.boond_resource_id", True),
    "004_add_cv_transformer_tables": ("table:cv_templates", True),
    "005_add_phone_fields": ("column:invitations.phone", True),
    "006_add_names_invitations": ("column:invitations.first_name", True),
    "007_add_quotation_templates": ("table:quotation_templates", True),
    "008_add_published_opportunities": ("table:published_opportunities", True),
    "009_add_hr_feature_tables": ("table:job_applications", True),
    "010_add_row_level_security": ("policy:cooptations.cooptations_admin_rh_all", True),
    "011_add_turnoverit_skills_table": ("table:turnoverit_skills", True),
    "012_add_app_settings_table": ("table:app_settings", True),
    "014_add_location_key": ("column:job_postings.location_key", True),
    "016_add_application_form_fields": ("column:job_applications.availability", True),
    "017_add_cv_quality_fields": ("column:job_applications.cv_quality", True),
    "018_simplify_application_status": ("column:job_applications.is_read", True),
    "019_add_civility_and_boond_sync": ("column:job_applications.boond_sync_error", True),
    "023_add_view_count": ("column:job_postings.view_count", True),
    "025_contract_vigil": ("table:cm_contract_requests", True),
    "026_partial_uniq_pos": (
        "index:CREATE UNIQUE INDEX uq_cm_contract_requests_boond_positioning ON public.cm_contract_requests USING btree (boond_positioning_id) WHERE ((status)::text <> 'cancelled'::text)",
        True,
    ),
    "027_cr_end_date_title": ("column:cm_contract_requests.end_date", True),
    "028_cr_consultant_address": ("column:cm_contract_requests.consultant_civility", True),
    "029_tp_nullable_identity": ("colnull:tp_third_parties.company_name|YES", True),
    "030_tp_contact_fields": ("column:tp_third_parties.adv_contact_civility", True),
    "031_remove_siren_unique": (
        "index:CREATE INDEX ix_tp_third_parties_siren ON public.tp_third_parties USING btree (siren)",
        True,
    ),
    "032_add_doc_extraction_fields": ("column:vig_documents.document_date", True),
    "033_add_doc_unavailability": ("column:vig_documents.is_unavailable", True),
    "034_contract_articles": ("table:cm_contract_article_templates", True),
    "035_add_entity_category": ("column:tp_third_parties.entity_category", True),
    "036": ("column:tp_third_parties.head_office_city", True),
    "037": ("coltype:tp_third_parties.entity_category|character varying|20", True),
    "038": ("column:tp_third_parties.company_info_submitted", True),
    "040": ("column:cm_contract_requests.status_history", True),
    "042": ("table:cm_contract_companies", True),
    "043": ("column:cm_contract_companies.logo_s3_key", True),
    "046": ("table:cm_contract_annex_templates", True),
    "049": ("column:cm_contract_companies.invoices_company_mail", True),
    "050": ("column:cm_contract_article_templates.is_optional", True),
    "051": ("column:cm_contract_companies.code", True),
    "052": ("column:cm_contract_requests.consultant_email", True),
    "053": ("column:cm_contract_companies.boond_agency_id", True),
    "054": ("column:cm_contract_requests.boond_consultant_type", True),
    "055": ("column:cm_contract_requests.provisional_reference", True),
    "056": ("column:cm_contract_requests.quantity_sold", True),
    "057": ("column:tp_third_parties.ape_code", True),
    "058": ("column:tp_third_parties.signatory_is_director", True),
    "059": ("column:cm_contract_companies.tva_number", True),
    "060": ("column:tp_third_parties.boond_adv_contact_id", True),
    "064": ("column:cm_contract_requests.boond_resource_id", True),
    "065": ("column:tp_third_parties.last_expiration_alert_at", True),
    "066": ("column:cm_contract_companies.email_from", True),
    "067": ("table:cm_charter_acknowledgements", True),
    "068": ("column:cm_charter_templates.company_id", True),
    "069": ("column:cm_charter_templates.ar_file_name", True),
    "070": ("column:cm_charter_templates.consultant_scope", True),
    "071": ("table:cm_signature_uploads", True),
    "072": ("column:tp_third_parties.boond_resource_id", True),
    "078": ("column:cm_contract_requests.documents_skipped", True),
    "079": ("column:cm_purchase_orders.boond_consultant_id", True),
    "080": ("column:cm_purchase_orders.provisional_reference", True),
    "081": ("column:tp_third_parties.vat_liable", True),
    "082": ("column:tp_third_parties.boond_billing_contact_id", True),
}

# Révisions qui ne touchent pas au schéma — contenu d'articles, remises à zéro,
# corrections de données —, et celles dont les objets ont été repris par une
# migration ultérieure. Rien ne les distingue de la précédente ; une base
# arrêtée sur l'une d'elles n'est donc pas reconnaissable, et l'amorçage refuse
# alors d'inscrire une révision plutôt que de risquer de les rejouer.
DATA_ONLY: frozenset[str] = frozenset(
    {
        "013_add_turnoverit_skills_table",
        "015_fix_contract_types_enum",
        "020_reset_apps_revalidation",
        "021_delete_all_job_postings",
        "022_reset_hr_data",
        "024_reset_opps_coopts",
        "039",
        "041",
        "044",
        "045",
        "047",
        "048",
        "061",
        "062",
        "063",
        "073",
        "074",
        "075",
        "076",
        "077",
    }
)
