# Bobby — Spécifications Techniques : Contractualisation & Vigilance Documentaire

## Contexte

Bobby est une plateforme de recrutement avec intégration BoondManager. Ces spécifications couvrent deux nouveaux use cases développés en parallèle :

1. **Contractualisation** : Gestion automatisée de la création des contrats (freelance, sous-traitant, salarié) lors d'un nouveau contrat gagné
2. **Vigilance documentaire** : Gestion du cycle de vie des documents légaux des freelances et sous-traitants

**Principe fondamental** : BoondManager reste le CRM principal. Bobby orchestre ce que BoondManager ne fait pas (collecte documentaire, génération de contrats, vigilance, signature électronique).

---

## Stack technique

- **Backend** : Python / FastAPI / Architecture hexagonale
- **Stockage documents** : AWS S3
- **Emails** : Resend
- **Signature électronique** : YouSign API
- **CRM** : BoondManager API (source de vérité pour candidats, besoins, positionnements, fournisseurs)
- **Vérification légale** : API INSEE/Sirene
- **Base de données** : PostgreSQL (à confirmer selon existant Bobby)

---

## 1. Modèle de Domaine

### 1.1 Entités principales

#### Tiers (`ThirdParty`)

Représente un freelance ou un sous-traitant. Ne duplique PAS les données BoondManager — stocke uniquement ce que Boond ne gère pas.

```python
class ThirdPartyType(str, Enum):
    FREELANCE = "freelance"
    SOUS_TRAITANT = "sous_traitant"
    SALARIE = "salarie"  # Cas minimal, redirigé vers Payfit

class ThirdParty:
    id: UUID
    boond_provider_id: Optional[int]  # ID fournisseur dans BoondManager (si existant)
    type: ThirdPartyType
    company_name: str  # Raison sociale
    legal_form: str  # SAS, EURL, SASU, Auto-entrepreneur...
    capital: Optional[str]  # Capital social
    siren: str
    siret: str
    rcs_city: str  # Ville du RCS
    rcs_number: str  # Numéro RCS
    head_office_address: str  # Siège social
    representative_name: str  # Nom du représentant légal
    representative_title: str  # Qualité (Gérant, Président, Directeur associé...)
    contact_email: str  # Email de la personne en charge de la contractualisation
    compliance_status: ComplianceStatus  # Statut de conformité documentaire global
    created_at: datetime
    updated_at: datetime
```

#### Statut de conformité (`ComplianceStatus`)

```python
class ComplianceStatus(str, Enum):
    PENDING = "pending"  # Dossier en cours de constitution
    COMPLIANT = "compliant"  # Tous les documents valides et à jour
    EXPIRING_SOON = "expiring_soon"  # Au moins un document expire dans les 30 jours
    NON_COMPLIANT = "non_compliant"  # Au moins un document expiré ou manquant
```

#### Document de vigilance (`VigilanceDocument`)

```python
class DocumentType(str, Enum):
    KBIS = "kbis"
    EXTRAIT_INSEE = "extrait_insee"  # Pour les auto-entrepreneurs
    ATTESTATION_URSSAF = "attestation_urssaf"
    ATTESTATION_HONNEUR = "attestation_honneur"
    ATTESTATION_FISCALE = "attestation_fiscale"
    RC_PRO = "rc_pro"
    LISTE_SALARIES_ETRANGERS = "liste_salaries_etrangers"

class DocumentStatus(str, Enum):
    REQUESTED = "requested"  # Demandé, en attente d'upload
    RECEIVED = "received"  # Uploadé, en attente de vérification
    UNDER_REVIEW = "under_review"  # En cours de vérification par l'ADV
    VALIDATED = "validated"  # Validé et actif
    REJECTED = "rejected"  # Rejeté (document invalide, illisible, etc.)
    EXPIRING_SOON = "expiring_soon"  # Valide mais expire dans les 30 jours
    EXPIRED = "expired"  # Expiré

class VigilanceDocument:
    id: UUID
    third_party_id: UUID
    document_type: DocumentType
    status: DocumentStatus
    s3_key: Optional[str]  # Clé S3 du fichier
    file_name: Optional[str]
    file_size: Optional[int]
    uploaded_at: Optional[datetime]
    validated_at: Optional[datetime]
    validated_by: Optional[str]  # Email de l'ADV qui a validé
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    expires_at: Optional[datetime]  # Date d'expiration du document
    auto_check_results: Optional[dict]  # Résultats des vérifications automatiques (SIREN, etc.)
    created_at: datetime
    updated_at: datetime
```

#### Demande de contractualisation (`ContractRequest`)

Créée quand un positionnement passe en statut 7 ("Gagné attente contrat") dans BoondManager.

```python
class ContractRequestStatus(str, Enum):
    PENDING_COMMERCIAL_VALIDATION = "pending_commercial_validation"
    COMMERCIAL_VALIDATED = "commercial_validated"
    COLLECTING_DOCUMENTS = "collecting_documents"
    DOCUMENTS_COMPLETE = "documents_complete"
    CONFIGURING_CONTRACT = "configuring_contract"
    DRAFT_GENERATED = "draft_generated"
    DRAFT_SENT_TO_PARTNER = "draft_sent_to_partner"
    PARTNER_APPROVED = "partner_approved"
    PARTNER_REQUESTED_CHANGES = "partner_requested_changes"
    SENT_FOR_SIGNATURE = "sent_for_signature"
    SIGNED = "signed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"
    REDIRECTED_PAYFIT = "redirected_payfit"  # Cas salarié

class ContractRequest:
    id: UUID
    reference: str  # Auto-incrémenté : AT-XXX
    boond_positioning_id: int  # ID du positionnement BoondManager
    boond_candidate_id: int  # ID du candidat BoondManager
    boond_need_id: int  # ID du besoin BoondManager
    third_party_id: Optional[UUID]  # Lien vers le tiers (créé ou existant)
    status: ContractRequestStatus
    
    # Infos saisies par le commercial
    third_party_type: ThirdPartyType  # Freelance, sous-traitant, salarié
    daily_rate: Decimal  # TJM achat (CJM)
    start_date: date
    client_name: str  # Récupéré du besoin BoondManager
    mission_description: str  # Récupéré du besoin BoondManager
    mission_location: Optional[str]
    contractualization_contact_email: str  # Email de la personne à contacter pour le contrat
    
    # Infos saisies par l'ADV pour la génération du contrat
    contract_config: Optional[ContractConfig]
    
    # Tracking
    commercial_email: str
    commercial_validated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

#### Configuration du contrat (`ContractConfig`)

Options choisies par l'ADV pour la génération du contrat.

```python
class PaymentTerms(str, Enum):
    THIRTY_DAYS_END_OF_MONTH = "30_jours_fin_de_mois"
    THIRTY_DAYS_ON_RECEIPT = "30_jours_reception"
    FORTY_FIVE_DAYS_END_OF_MONTH = "45_jours_fin_de_mois"
    SIXTY_DAYS = "60_jours"

class InvoiceSubmissionMethod(str, Enum):
    BOONDMANAGER = "boondmanager"
    EMAIL = "email"

class ContractConfig:
    payment_terms: PaymentTerms
    invoice_submission_method: InvoiceSubmissionMethod
    invoice_email: Optional[str]  # Si méthode = email
    has_confidentiality_clause: bool = True
    has_non_compete_clause: bool = True
    non_compete_duration_months: int = 12  # Durée de la clause post-contrat
    non_compete_penalty_description: str = "montant total du contrat"
    contract_duration: Optional[str]  # Ex: "3 mois", "6 mois", "12 mois"
    renewal_type: str = "tacite_reconduction"  # Tacite reconduction
    renewal_period: Optional[str]  # Ex: "6 mois"
    end_date: Optional[date]
    notice_period_gemini_months: int = 1  # Préavis résiliation côté Gemini
    notice_period_partner_months: int = 1  # Préavis résiliation côté partenaire
    replacement_notice_months: int = 3  # Préavis remplacement intervenant
    special_conditions: Optional[str]  # Conditions particulières libres
```

#### Contrat (`Contract`)

```python
class Contract:
    id: UUID
    contract_request_id: UUID
    third_party_id: UUID
    reference: str  # AT-XXX (même référence que la demande)
    version: int  # Numéro de version (incrémenté à chaque modification)
    s3_key_draft: str  # Clé S3 du draft DOCX
    s3_key_signed: Optional[str]  # Clé S3 du document signé (PDF depuis YouSign)
    yousign_procedure_id: Optional[str]  # ID de la procédure YouSign
    yousign_status: Optional[str]
    boond_purchase_order_id: Optional[int]  # ID du bon de commande créé dans Boond
    created_at: datetime
    signed_at: Optional[datetime]
```

#### Lien magique (`MagicLink`)

```python
class MagicLinkPurpose(str, Enum):
    DOCUMENT_UPLOAD = "document_upload"  # Upload documents de vigilance
    CONTRACT_REVIEW = "contract_review"  # Review d'un draft de contrat

class MagicLink:
    id: UUID
    token: str  # Token unique, URL-safe, 64 caractères minimum
    third_party_id: UUID
    contract_request_id: Optional[UUID]  # Si lié à une demande de contrat
    purpose: MagicLinkPurpose
    email_sent_to: str
    expires_at: datetime  # Durée de validité : 7 jours par défaut
    accessed_at: Optional[datetime]
    is_revoked: bool = False
    created_at: datetime
```

### 1.2 Référentiel documentaire

Configuration des documents attendus par type de tiers.

```python
VIGILANCE_REQUIREMENTS = {
    ThirdPartyType.FREELANCE: [
        {
            "type": DocumentType.KBIS,  # ou EXTRAIT_INSEE si auto-entrepreneur
            "periodicity": "annual",  # Recommandé à jour (<3 mois à la signature)
            "validity_months": 3,
            "required_at_signature": True,
            "auto_checks": ["siren_validation", "dirigeant_check", "activite_check"],
            "description": "Extrait Kbis ou extrait INSEE (auto-entrepreneur)"
        },
        {
            "type": DocumentType.ATTESTATION_URSSAF,
            "periodicity": "semi_annual",  # Tous les 6 mois, obligatoire
            "validity_months": 6,
            "required_at_signature": True,
            "auto_checks": ["siren_validation", "date_validite"],
            "description": "Attestation de vigilance URSSAF"
        },
        {
            "type": DocumentType.ATTESTATION_HONNEUR,
            "periodicity": "annual",
            "validity_months": 12,
            "required_at_signature": True,
            "auto_checks": [],
            "description": "Attestation sur l'honneur (signature représentant légal)"
        },
        {
            "type": DocumentType.ATTESTATION_FISCALE,
            "periodicity": "annual",  # Bonne pratique
            "validity_months": 12,
            "required_at_signature": False,  # Recommandé mais pas bloquant
            "auto_checks": ["siren_validation", "date_validite"],
            "description": "Attestation de régularité fiscale"
        },
        {
            "type": DocumentType.RC_PRO,
            "periodicity": "annual",
            "validity_months": 12,
            "required_at_signature": True,
            "auto_checks": ["date_validite"],
            "description": "Attestation d'assurance RC Professionnelle"
        }
    ],
    ThirdPartyType.SOUS_TRAITANT: [
        # Mêmes documents que freelance +
        {
            "type": DocumentType.LISTE_SALARIES_ETRANGERS,
            "periodicity": "on_change",  # Mise à jour si changement
            "validity_months": None,  # Pas d'expiration fixe
            "required_at_signature": False,  # Si applicable seulement
            "auto_checks": [],
            "description": "Liste des salariés étrangers intervenant sur la mission"
        }
        # + tous les documents du freelance ci-dessus
    ]
}
```

### 1.3 Règles RGPD

```python
# Documents INTERDITS — Bobby doit rejeter/alerter si uploadés
FORBIDDEN_DOCUMENT_TYPES = [
    "piece_identite",       # Copies de pièces d'identité
    "titre_sejour",         # Titres de séjour
    "bulletin_paie",        # Bulletins de paie
    "contrat_travail",      # Contrats de travail
]

# Durée de conservation
RETENTION_RULES = {
    "during_contract": True,  # Conservation pendant la durée de la relation contractuelle
    "post_contract_years": 5,  # + 5 ans après fin de relation
    "action_after_retention": "delete_or_secure_archive"  # Suppression ou archivage sécurisé
}

# Accès restreint — seuls ces rôles peuvent accéder aux dossiers de vigilance
ALLOWED_ROLES = ["direction", "finance", "juridique", "adv"]
# Les commerciaux n'ont PAS accès aux documents de vigilance
```

---

## 2. Workflows

### 2.1 Workflow de Contractualisation

```
[BoondManager: Positionnement modifié → Webhook envoyé à Bobby]
    │
    ▼
[Bobby: Webhook reçu → Appel API Boond GET /api/positioning/{id}]
    │
    ├── Si state ≠ 7 → Ignorer (200 OK)
    │
    ▼ Si state == 7 ("Gagné attente contrat")
[Bobby: Vérification idempotence (pas de ContractRequest existante pour ce positionnement)]
    │
    ▼
[Bobby: Récupération infos besoin + candidat via API Boond]
    │
    ▼
[Bobby: Création ContractRequest status=PENDING_COMMERCIAL_VALIDATION]
    │
    ▼
[Bobby: Envoi email au commercial via Resend]
    │ (email contient un lien vers Bobby pour compléter les infos)
    │
    ▼
[Commercial: Complète le formulaire dans Bobby]
    │ - Choisit le type : freelance / sous-traitant / salarié
    │ - Renseigne : TJM achat, date de démarrage
    │ - Renseigne : Société du fournisseur
      - Renseigne : email du contact contractualisation
    │ - Client et mission sont pré-remplis depuis le besoin BoondManager mais possibilité de modifier
    │ - Valide
    │
    ├── Si SALARIE ──► status=REDIRECTED_PAYFIT → Notification vers process Payfit → FIN
    │
    ▼ Si FREELANCE ou SOUS_TRAITANT
[status=COMMERCIAL_VALIDATED]
    │
    ▼
[Bobby: Recherche ou création du Tiers]
    │ - Si le tiers existe déjà dans Bobby (match sur SIREN) → on le réutilise
    │ - Sinon → création d'un nouveau Tiers
    │
    ▼
[Bobby: Vérifie la conformité documentaire du Tiers]
    │
    ├── Si COMPLIANT → status=DOCUMENTS_COMPLETE → passe directement à la configuration
    │
    ▼ Si NON_COMPLIANT ou PENDING
[status=COLLECTING_DOCUMENTS]
    │
    ▼
[Bobby: Génération d'un MagicLink + envoi email au contact contractualisation via Resend]
    │ (le mail contient le lien vers le portail de collecte)
    │
    ▼
[Tiers: Accède au portail via MagicLink]
    │ - Voit la liste des documents attendus
    │ - Uploade ses documents
    │ - Bobby effectue les vérifications automatiques au fil de l'eau
    │
    ▼
[Bobby: Relances automatiques si documents manquants]
    │ - J+3 : première relance
    │ - J+7 : deuxième relance
    │ - J+14 : troisième relance + alerte ADV
    │ - Calendrier configurable
    │
    ▼
[ADV: Vérifie les documents reçus dans Bobby]
    │ - Valide ou rejette chaque document
    │ - Si rejet → notification au tiers avec motif → retour upload
    │
    ▼ (tous les documents requis validés)
[status=DOCUMENTS_COMPLETE]
    │
    ▼
[ADV: Configure les paramètres du contrat dans Bobby]
    │ - Conditions de paiement
    │ - Clause de confidentialité (oui/non)
    │ - Clause de non-concurrence (oui/non + durée)
    │ - Méthode de dépôt des factures
    │ - Durée / date de fin / reconduction
    │ - Conditions particulières
    │
    ▼
[status=CONFIGURING_CONTRACT → Bobby génère le DOCX → status=DRAFT_GENERATED]
    │
    ▼
[ADV: Vérifie le draft, peut regénérer si besoin]
    │
    ▼
[ADV: Envoie le draft au partenaire via Bobby]
    │ (MagicLink de type CONTRACT_REVIEW + email via Resend)
    │
    ▼
[status=DRAFT_SENT_TO_PARTNER]
    │
    ▼
[Tiers: Consulte le draft via le portail]
    │
    ├── Approuve → status=PARTNER_APPROVED
    │
    ├── Demande des modifications (commentaire texte libre)
    │   → status=PARTNER_REQUESTED_CHANGES
    │   → Notification ADV
    │   → ADV modifie la config, regénère, renvoie
    │   → Retour à DRAFT_SENT_TO_PARTNER (version incrémentée)
    │
    ▼ (une fois approuvé)
[status=PARTNER_APPROVED]
    │
    ▼
[ADV: Déclenche l'envoi pour signature via YouSign]
    │ - Bobby appelle l'API YouSign pour créer la procédure de signature
    │ - Upload du document DOCX converti en PDF
    │ - Définition des signataires (Gemini + Partenaire)
    │
    ▼
[status=SENT_FOR_SIGNATURE]
    │
    ▼
[YouSign: Webhook → Signature complétée]
    │
    ▼
[status=SIGNED]
    │ - Bobby récupère le document signé (PDF) depuis YouSign
    │ - Archivage S3 du document signé dans le dossier du tiers
    │
    ▼
[Bobby: Push des infos achats vers BoondManager]
    │ - Création ou mise à jour du fournisseur dans Boond
    │ - Création du bon de commande / ordre de mission
    │ - Rattachement au projet/affaire
    │
    ▼
[status=ARCHIVED] → FIN
```

### 2.2 Workflow de Vigilance Documentaire

```
[Déclencheur: Création d'un Tiers OU expiration d'un document OU demande manuelle ADV]
    │
    ▼
[Bobby: Détermine les documents attendus selon le type de tiers]
    │ (cf. VIGILANCE_REQUIREMENTS)
    │
    ▼
[Bobby: Crée les entrées VigilanceDocument en status=REQUESTED pour chaque document manquant]
    │
    ▼
[Bobby: Envoie MagicLink au tiers pour upload]
    │
    ▼
[Tiers: Uploade les documents via le portail]
    │ → Chaque document passe en status=RECEIVED
    │ → Vérifications automatiques lancées immédiatement
    │
    ▼
[Bobby: Vérifications automatiques]
    │ - SIREN via API INSEE : vérification existence, dirigeant, activité
    │ - Dates de validité : extraction si possible
    │ - Format et lisibilité du fichier
    │ → Résultats stockés dans auto_check_results
    │ → Document passe en status=UNDER_REVIEW
    │
    ▼
[ADV: Vérification manuelle dans Bobby]
    │
    ├── Valide → status=VALIDATED, expires_at calculé selon périodicité
    │
    ├── Rejette → status=REJECTED avec motif
    │   → Notification au tiers → retour en REQUESTED
    │
    ▼
[Bobby: Monitoring continu des expirations]
    │ - CRON quotidien : vérifie tous les documents validés
    │ - J-30 avant expiration → status=EXPIRING_SOON + alerte tiers + alerte ADV
    │ - J-15 → relance tiers
    │ - J-7 → relance tiers + alerte direction
    │ - J0 (expiration) → status=EXPIRED → mise à jour compliance_status du tiers
    │
    ▼
[Impact sur contractualisation]
    │ - Si tiers NON_COMPLIANT → blocage de la génération de contrat
    │ - L'ADV peut forcer (soft block) avec justification tracée
```

---

## 3. API Endpoints

### 3.1 Webhook BoondManager (Positionnement modification)

```
POST /api/v1/webhooks/boondmanager/positioning-update
```

Reçoit les notifications webhook de BoondManager. Le webhook est configuré dans Boond sur l'événement **"Positionnement > Modification"**.

**Configuration dans BoondManager** : Administration > Webhooks > Créer
- Nom : "Bobby - Positionnement gagné"
- URL : `https://{bobby_domain}/api/v1/webhooks/boondmanager/positioning-update`
- Événements déclencheurs : Positionnement > Modification (case "Modification" cochée)

**Payload réel BoondManager** (tableau JSON — peut contenir plusieurs events) :
```json
[
    {
        "data": {
            "id": "3_6991c54471a73",
            "type": "webhookevent",
            "attributes": {
                "userToken": "3138352e67656d696e69",
                "clientToken": "67656d696e69",
                "type": "update"
            },
            "relationships": {
                "webhook": {
                    "id": "3",
                    "type": "webhook"
                },
                "dependsOn": {
                    "id": "433",
                    "type": "positioning"
                },
                "log": {
                    "id": "117497",
                    "type": "log"
                }
            },
            "included": [
                {
                    "id": "2543",
                    "type": "resource",
                    "attributes": {
                        "lastName": "EL KHODJA",
                        "firstName": "Cherif"
                    }
                },
                {
                    "id": "117497",
                    "type": "log",
                    "attributes": {
                        "creationDate": "2026-02-15T14:08:20+0100",
                        "auth": "normal",
                        "action": "update",
                        "typeOf": "positioning",
                        "content": {
                            "version": 2,
                            "context": {
                                "currency": 0,
                                "currencyAgency": 0,
                                "exchangeRate": 1,
                                "exchangeRateAgency": 1,
                                "id": "433"
                            },
                            "diff": {
                                "state": {
                                    "old": 0,
                                    "new": 7
                                }
                            }
                        },
                        "isEntityDeleted": false
                    },
                    "relationships": {
                        "createdBy": {
                            "data": {
                                "id": "2543",
                                "type": "resource"
                            }
                        },
                        "dependsOn": {
                            "data": {
                                "id": "433",
                                "type": "positioning"
                            }
                        }
                    }
                }
            ]
        }
    }
]
```

**Champs clés à exploiter** :
- `data.relationships.dependsOn.id` → ID du positionnement BoondManager (ex: "433")
- `data.relationships.dependsOn.type` → Doit être "positioning"
- `data.attributes.type` → Type d'événement ("update")
- `data.included[type=log].attributes.content.diff.state.new` → **Nouveau statut** (7 = "Gagné attente contrat")
- `data.included[type=log].attributes.content.diff.state.old` → Ancien statut
- `data.included[type=resource]` → Utilisateur ayant déclenché le changement (le commercial)
- `data.included[type=log].attributes.creationDate` → Date de l'événement
- `data.id` → ID unique de l'événement webhook (pour idempotence)

**IMPORTANT** : Le payload est un **tableau JSON** (root = `[]`). Bobby doit itérer sur chaque élément. Le diff de statut est directement dans le payload (`included[type=log].attributes.content.diff.state`), donc Bobby peut filtrer sur `state.new == 7` **sans appel API supplémentaire** pour vérifier le statut.

**Actions** :
1. Parser le payload (tableau JSON)
2. Pour chaque event :
   a. Vérifier que `dependsOn.type == "positioning"`
   b. Extraire le log depuis `included` (matcher par `type == "log"`)
   c. Vérifier que `log.attributes.content.diff.state.new == 7`
   d. Si state.new ≠ 7 → ignorer, répondre 200 OK
3. Vérifier l'idempotence : le webhook event ID (`data.id`) n'a pas déjà été traité
4. Vérifier qu'une `ContractRequest` n'existe pas déjà pour ce positionnement (`dependsOn.id`)
5. Extraire l'ID du positionnement : `dependsOn.id` (ici "433")
6. Appeler l'API BoondManager `GET /api/positioning/{id}` pour récupérer les détails (candidat lié, besoin lié)
7. Appeler l'API BoondManager `GET /api/need/{need_id}` pour récupérer le client, la mission, le lieu
8. Appeler l'API BoondManager `GET /api/candidate/{candidate_id}` pour récupérer les infos du candidat
9. Identifier le commercial depuis `included[type=resource]` (nom/prénom) et rechercher son email dans Bobby ou BoondManager
10. Créer la `ContractRequest` en status `PENDING_COMMERCIAL_VALIDATION`
11. Envoyer un email au commercial via Resend avec le lien vers le formulaire Bobby
12. Répondre 200 OK à BoondManager

**Idempotence** : Toujours répondre 200 OK à BoondManager (même en cas d'erreur interne) pour éviter les retries. Logger les erreurs côté Bobby. Stocker les `data.id` d'événements traités pour détecter les doublons.

### 3.2 Validation commerciale

```
GET /api/v1/contract-requests/{id}/commercial-form
```

Retourne les données pré-remplies (client, mission, candidat) pour que le commercial complète.

```
POST /api/v1/contract-requests/{id}/commercial-validate
```

**Body** :
```json
{
    "third_party_type": "freelance",
    "daily_rate": 650.00,
    "start_date": "2026-01-01",
    "contractualization_contact_email": "contact@partenaire.fr",
    "mission_location": "Thales Campus Helios, 19 Av. Morane Saulnier, 78140 Vélizy-Villacoublay"
}
```

**Actions** :
1. Mettre à jour la `ContractRequest` avec les infos du commercial
2. Si type = salarié → status = `REDIRECTED_PAYFIT`, notification Payfit, FIN
3. Si freelance/sous-traitant → status = `COMMERCIAL_VALIDATED`
4. Rechercher un tiers existant par SIREN ou créer un nouveau tiers
5. Vérifier la conformité documentaire
6. Si conforme → `DOCUMENTS_COMPLETE`
7. Si non conforme → `COLLECTING_DOCUMENTS` → envoi MagicLink

### 3.3 Portail Tiers (Magic Link)

```
GET /api/v1/portal/{magic_link_token}
```

Vérifie la validité du token (non expiré, non révoqué). Retourne les infos du tiers et la liste des actions attendues (documents à uploader et/ou contrat à reviewer).

```
POST /api/v1/portal/{magic_link_token}/documents/{document_type}/upload
```

Upload d'un document de vigilance. Multipart form data. Stockage S3. Lance les vérifications automatiques.

**Validations** :
- Formats acceptés : PDF, JPG, PNG
- Taille max : 10 Mo par fichier
- Vérification que le type de document n'est pas dans `FORBIDDEN_DOCUMENT_TYPES`

```
GET /api/v1/portal/{magic_link_token}/contract-draft
```

Téléchargement du draft de contrat pour review.

```
POST /api/v1/portal/{magic_link_token}/contract-review
```

**Body** :
```json
{
    "decision": "approved",  // ou "changes_requested"
    "comments": "Optionnel : détail des modifications demandées"
}
```

### 3.4 Gestion documentaire (ADV)

```
GET /api/v1/third-parties
```

Liste des tiers avec leur statut de conformité. Filtres : type, compliance_status, search.

```
GET /api/v1/third-parties/{id}/documents
```

Liste des documents de vigilance d'un tiers avec leur statut.

```
POST /api/v1/third-parties/{id}/documents/{document_id}/validate
```

Validation d'un document par l'ADV.

```
POST /api/v1/third-parties/{id}/documents/{document_id}/reject
```

**Body** :
```json
{
    "reason": "Document illisible, merci de renvoyer un scan de meilleure qualité"
}
```

```
POST /api/v1/third-parties/{id}/request-documents
```

Demande manuelle de renouvellement de documents. Génère un nouveau MagicLink et envoie l'email.

### 3.5 Configuration et génération du contrat (ADV)

```
GET /api/v1/contract-requests/{id}
```

Détail de la demande de contractualisation avec toutes les infos.

```
POST /api/v1/contract-requests/{id}/configure
```

**Body** : `ContractConfig` (voir modèle de domaine)

```
POST /api/v1/contract-requests/{id}/generate-draft
```

Génère le DOCX à partir du template et de la configuration. Stocke sur S3. Retourne l'URL de téléchargement.

```
POST /api/v1/contract-requests/{id}/send-draft-to-partner
```

Envoie le draft au partenaire via MagicLink + email Resend.

```
POST /api/v1/contract-requests/{id}/send-for-signature
```

Déclenche la procédure YouSign. Convertit le DOCX en PDF, upload vers YouSign, crée la procédure de signature.

### 3.6 Webhooks YouSign

```
POST /api/v1/webhooks/yousign/signature-completed
```

Reçoit la notification de signature complétée. Récupère le PDF signé, archive sur S3, push vers BoondManager.

### 3.7 Dashboard de conformité

```
GET /api/v1/compliance/dashboard
```

**Response** :
```json
{
    "total_third_parties": 45,
    "compliant": 38,
    "expiring_soon": 4,
    "non_compliant": 3,
    "expiring_documents_next_30_days": [
        {
            "third_party_id": "...",
            "third_party_name": "MOD Consulting",
            "document_type": "attestation_urssaf",
            "expires_at": "2026-03-15"
        }
    ],
    "blocked_contract_requests": [
        {
            "contract_request_id": "...",
            "reference": "AT-128",
            "third_party_name": "Crafters",
            "missing_documents": ["kbis", "rc_pro"]
        }
    ]
}
```

### 3.8 Gestion des numéros de contrat

```
GET /api/v1/contracts/next-reference
```

Retourne la prochaine référence disponible (AT-XXX). Auto-incrémentation basée sur le dernier contrat en base.

---

## 4. Template de contrat

### 4.1 Variables du template

Le template est un fichier DOCX avec des variables Jinja2 (via python-docx-template).

#### Variables Gemini (pré-remplies, gérées en configuration Bobby)

```python
GEMINI_INFO = {
    "gemini_company_name": "GEMINI",
    "gemini_legal_form": "SAS",
    "gemini_capital": "10 000",
    "gemini_head_office": "54 Avenue Hoche - 75008 Paris",  # Adresse actuelle
    "gemini_rcs_city": "Paris",
    "gemini_rcs_number": "842 799 959",
    "gemini_representative_entity": "la société SC Holding",
    "gemini_representative_quality": "Président",
    "gemini_representative_sub": "Représentée par sa Présidente Madame Selma HIZEM",
    "gemini_signatory_name": "Mme Selma HIZEM",
    "gemini_signatory_title": "SAS GEMINI"
}
```

#### Variables du partenaire (issues du Tiers)

```python
partner_vars = {
    "partner_company_name": third_party.company_name,
    "partner_legal_form": third_party.legal_form,
    "partner_capital": third_party.capital,
    "partner_head_office": third_party.head_office_address,
    "partner_rcs_city": third_party.rcs_city,
    "partner_rcs_number": third_party.rcs_number,
    "partner_representative_name": third_party.representative_name,
    "partner_representative_title": third_party.representative_title,
    "partner_signatory_name": f"{third_party.representative_name}",
    "partner_signatory_title": f"{third_party.legal_form} {third_party.company_name}"
}
```

#### Variables du contrat (issues de ContractRequest + ContractConfig)

```python
contract_vars = {
    "contract_reference": contract_request.reference,  # AT-XXX
    "payment_terms_text": "30 jours fin de mois, net d'agios par virement bancaire",  # Selon config
    "invoice_submission_text": "à déposer sur la plateforme Boondmanager de la société Gemini avant le 5 du mois suivant la prestation",  # Selon config
    "has_confidentiality_clause": config.has_confidentiality_clause,
    "has_non_compete_clause": config.has_non_compete_clause,
    "non_compete_duration_months": config.non_compete_duration_months,
    "non_compete_penalty": config.non_compete_penalty_description,
    "notice_period_gemini": config.notice_period_gemini_months,
    "notice_period_partner": config.notice_period_partner_months,
    "replacement_notice_months": config.replacement_notice_months,
    "special_conditions": config.special_conditions,
}
```

#### Variables de l'annexe

```python
annexe_vars = {
    "consultant_name": "Récupéré depuis BoondManager (candidat)",
    "client_final": contract_request.client_name,
    "mission_nature": contract_request.mission_description,
    "mission_location": contract_request.mission_location,
    "start_date": contract_request.start_date.strftime("%d/%m/%Y"),
    "end_date": config.end_date.strftime("%d/%m/%Y") if config.end_date else None,
    "duration": config.contract_duration,  # "3 mois", "6 mois"...
    "renewal_text": "Tacite reconduction par période de 6 mois ensuite",  # Selon config
    "daily_rate": contract_request.daily_rate,
    "daily_rate_text": f"{contract_request.daily_rate} Euros Hors Taxe / Jour"
}
```

### 4.2 Mapping des conditions de paiement

```python
PAYMENT_TERMS_TEXT = {
    PaymentTerms.THIRTY_DAYS_END_OF_MONTH: "30 jours fin de mois, net d'agios par virement bancaire",
    PaymentTerms.THIRTY_DAYS_ON_RECEIPT: "30 jours à réception de la facture, net d'agios par virement bancaire",
    PaymentTerms.FORTY_FIVE_DAYS_END_OF_MONTH: "45 jours fin de mois, net d'agios par virement bancaire",
    PaymentTerms.SIXTY_DAYS: "60 jours, net d'agios par virement bancaire",
}

INVOICE_SUBMISSION_TEXT = {
    InvoiceSubmissionMethod.BOONDMANAGER: "Les factures seront à déposer sur la plateforme Boondmanager de la société Gemini avant le 5 du mois suivant la prestation pour mise en paiement dans les temps.",
    InvoiceSubmissionMethod.EMAIL: "Les factures seront à envoyer exclusivement à l'adresse suivante {invoice_email} avant le 5 du mois suivant la prestation pour mise en paiement dans les temps.",
}
```

### 4.3 Structure du template DOCX

Le template doit reproduire la structure exacte des contrats Gemini existants :

```
Page 1 : Page de garde
    - Titre : "CONTRAT {contract_reference}"
    - Logo Gemini
    - Pied de page : "Référence du contrat N° {contract_reference}"

Page 2+ : Corps du contrat
    - En-tête : identification des parties (Gemini + Partenaire)
    - Article 1 – OBJET (texte fixe)
    - Article 2 – DEFINITION DU SERVICE (texte fixe)
    - Article 3 – MODALITES D'EXECUTION DE LA SOUS TRAITANCE (texte fixe)
    - Article 4 – DUREE DU CONTRAT (texte fixe, renvoi annexe)
    - Article 5 – CONDITIONS FINANCIERES (texte fixe, renvoi annexe)
    - Article 6 – FACTURATION ET CONDITIONS DE PAIEMENT (variable : conditions + méthode facture)
    {% if has_confidentiality_clause %}
    - Article N – CONFIDENTIALITE (texte fixe)
    {% endif %}
    - Article N – RESILIATION (variable : durées de préavis)
    - Article N – STATUT DU PARTENAIRE (texte fixe)
    - Article N – LITIGES (texte fixe)
    - Article N – INDIVISIBILITE (texte fixe)
    - Article N – ELECTION DE DOMICILE (texte fixe)
    {% if has_non_compete_clause %}
    - Article N – NON CONCURENCE (variable : durée, pénalité)
    {% endif %}
    - Bloc signature : Fait à Paris, le {date}
    - Signatures Gemini + Partenaire

Dernière page : ANNEXE N° 1
    - Nom et Prénom du consultant
    - Client Final
    - Nature de la prestation
    - Lieu de la prestation
    - Date de début
    - Date de fin / Durée + reconduction
    - Tarif (TJM)
    - Signatures Gemini + Partenaire
```

**IMPORTANT** : La numérotation des articles est dynamique. Si la clause de confidentialité est désactivée, les articles suivants se renumérotent. Le template doit gérer cela (soit via Jinja2 avec un compteur, soit en pré-calculant les numéros dans le code Python avant injection).

---

## 5. Intégrations

### 5.1 BoondManager API

**Lecture (Bobby consomme)** :
- `GET /positioning/{id}` : Détail du positionnement (statut, candidat, besoin)
- `GET /need/{id}` : Détail du besoin (client, mission, description)
- `GET /candidate/{id}` : Détail du candidat (nom, prénom, infos)
- `GET /provider/{id}` : Détail du fournisseur (si existe déjà)

**Écriture (Bobby pousse)** :
- `POST /provider` : Création d'un fournisseur (après signature du contrat)
- `PUT /provider/{id}` : Mise à jour d'un fournisseur
- Création du bon de commande / ordre de mission (endpoint à identifier selon API Boond)

**Webhook (BoondManager → Bobby)** :
- Notification sur changement de statut des positionnements
- Bobby filtre sur statut = 7

### 5.2 AWS S3

**Structure des buckets/clés** :
```
bobby-documents/
    vigilance/
        {third_party_id}/
            kbis/
                {document_id}_{timestamp}.pdf
            attestation_urssaf/
                {document_id}_{timestamp}.pdf
            ...
    contracts/
        {contract_request_id}/
            drafts/
                v{version}_{timestamp}.docx
            signed/
                {contract_reference}_signed.pdf
```

**Sécurité** :
- Chiffrement at rest (SSE-S3 ou SSE-KMS)
- Accès via presigned URLs pour le téléchargement (durée limitée)
- Pas d'accès public

### 5.3 Resend (Emails)

**Templates d'emails à créer** :

| Email | Destinataire | Déclencheur |
|-------|-------------|-------------|
| `commercial_validation_request` | Commercial | Positionnement statut 7 |
| `document_collection_request` | Contact tiers | Début collecte documentaire |
| `document_reminder_1` | Contact tiers | J+3 sans upload complet |
| `document_reminder_2` | Contact tiers | J+7 sans upload complet |
| `document_reminder_3` | Contact tiers + ADV | J+14 sans upload complet |
| `document_rejected` | Contact tiers | Document rejeté par ADV |
| `contract_draft_review` | Contact tiers | Draft prêt pour review |
| `contract_changes_requested` | ADV | Tiers demande des modifications |
| `signature_request` | Via YouSign | N/A (géré par YouSign) |
| `contract_signed_notification` | ADV + Commercial | Contrat signé |
| `document_expiring_30d` | Contact tiers + ADV | J-30 avant expiration |
| `document_expiring_15d` | Contact tiers | J-15 avant expiration |
| `document_expiring_7d` | Contact tiers + Direction | J-7 avant expiration |
| `document_expired` | Contact tiers + ADV + Direction | Document expiré |

### 5.4 YouSign API

**Flow** :
1. `POST /signature_requests` : Créer une procédure de signature
2. Upload du document PDF
3. Définir les signataires (Gemini + Partenaire) avec leurs zones de signature
4. Activer la procédure
5. Recevoir le webhook de complétion
6. `GET /signature_requests/{id}/documents/{id}/download` : Récupérer le PDF signé

### 5.5 API INSEE / Sirene

**Utilisation** : Vérification automatique lors de l'upload du Kbis ou de la création d'un tiers.

- `GET /siret/{siret}` : Vérifier l'existence et récupérer les infos
- Vérifier : SIREN actif, dénomination sociale, dirigeant, code NAF/activité
- Stocker les résultats dans `auto_check_results`

---

## 6. Jobs CRON

### 6.1 Vérification des expirations documentaires

**Fréquence** : Quotidien, 8h00

**Actions** :
1. Sélectionner tous les documents en status `VALIDATED` dont `expires_at` est dans les 30 prochains jours
2. J-30 : passer en `EXPIRING_SOON`, envoyer notification
3. J-15 : relance tiers
4. J-7 : relance tiers + alerte direction
5. J0 : passer en `EXPIRED`, mettre à jour le `compliance_status` du tiers

### 6.2 Relances collecte documentaire

**Fréquence** : Quotidien, 9h00

**Actions** :
1. Sélectionner toutes les `ContractRequest` en status `COLLECTING_DOCUMENTS`
2. Pour chaque demande, vérifier l'ancienneté du MagicLink envoyé
3. Envoyer les relances selon le calendrier (J+3, J+7, J+14)

### 6.3 Purge RGPD

**Fréquence** : Mensuel, 1er du mois à 2h00

**Actions** :
1. Identifier les tiers dont la relation contractuelle est terminée depuis + de 5 ans
2. Supprimer les documents de vigilance de S3
3. Supprimer les entrées en base
4. Logger l'opération pour audit

### 6.4 Expiration des MagicLinks

**Fréquence** : Quotidien, 0h00

**Actions** :
1. Révoquer tous les MagicLinks expirés non encore révoqués
2. Nettoyer les tokens en base (soft delete)

---

## 7. Règles métier importantes

### 7.1 Blocage contractualisation si non conforme

Avant de permettre la génération d'un contrat (`generate-draft`), Bobby DOIT vérifier que :
- Tous les documents `required_at_signature` sont en status `VALIDATED`
- Aucun document requis n'est en status `EXPIRED`

Si non conforme :
- **Soft block** : l'ADV voit un avertissement mais peut forcer avec une justification
- La justification est tracée et horodatée
- Un flag `compliance_override = True` est posé sur la `ContractRequest`

### 7.2 Auto-détection du type de document Kbis/INSEE

Si le tiers est de type `FREELANCE` :
- Vérifier via API INSEE si le SIREN correspond à un auto-entrepreneur
- Si oui → le document attendu est `EXTRAIT_INSEE` au lieu de `KBIS`
- Si non (EURL, SASU, etc.) → `KBIS`

### 7.3 Numérotation dynamique des articles

Le template de contrat a des clauses optionnelles (confidentialité, non-concurrence). La numérotation des articles doit être continue. Le code de génération doit calculer les numéros d'articles AVANT l'injection dans le template.

Exemple :
- Avec confidentialité + non-concurrence : articles 1 à 13
- Sans confidentialité, avec non-concurrence : articles 1 à 12
- Sans confidentialité ni non-concurrence : articles 1 à 11

### 7.4 Gestion des versions de draft

Chaque modification de la configuration et regénération du draft incrémente le numéro de version. Les anciennes versions sont conservées sur S3 pour traçabilité. L'historique des commentaires du tiers est conservé et associé à chaque version.

### 7.5 Réutilisation du dossier tiers

Quand un commercial valide une nouvelle contractualisation pour un tiers déjà connu (match sur SIREN) :
- Bobby réutilise le tiers existant
- Bobby vérifie sa conformité documentaire actuelle
- Si conforme → pas de nouvelle collecte, on passe directement à la config du contrat
- Si non conforme → collecte des documents manquants/expirés uniquement

### 7.6 Données interdites RGPD

Si Bobby détecte un upload potentiellement interdit (via le nom du fichier ou un check basique) :
- Ne pas stocker le fichier sur S3
- Alerter le tiers que ce type de document n'est pas accepté
- Logger l'événement pour audit

---

## 8. Permissions et rôles

| Action | Commercial | ADV | Direction | Finance |
|--------|-----------|-----|-----------|---------|
| Voir ses demandes de contrat | ✅ | ✅ | ✅ | ❌ |
| Valider une demande (formulaire) | ✅ | ❌ | ❌ | ❌ |
| Voir les documents de vigilance | ❌ | ✅ | ✅ | ✅ |
| Valider/rejeter un document | ❌ | ✅ | ✅ | ❌ |
| Configurer un contrat | ❌ | ✅ | ✅ | ❌ |
| Générer un draft | ❌ | ✅ | ✅ | ❌ |
| Envoyer pour signature | ❌ | ✅ | ✅ | ❌ |
| Forcer un soft block compliance | ❌ | ✅ (avec justification) | ✅ | ❌ |
| Dashboard de conformité | ❌ | ✅ | ✅ | ✅ |
| Configuration référentiel docs | ❌ | ❌ | ✅ | ❌ |

---

## 9. Architecture hexagonale

### 9.1 Organisation des bounded contexts

```
src/
    contract_management/           # Use case 1 : Contractualisation
        domain/
            entities/
                contract_request.py
                contract.py
                contract_config.py
            value_objects/
                contract_reference.py
                payment_terms.py
            events/
                contract_request_created.py
                contract_signed.py
                draft_generated.py
            ports/
                contract_repository.py      # Interface
                contract_generator.py       # Interface (génération DOCX)
                signature_service.py        # Interface (YouSign)
                crm_service.py              # Interface (BoondManager)
            services/
                contract_workflow_service.py
        application/
            use_cases/
                create_contract_request.py
                validate_commercial.py
                configure_contract.py
                generate_draft.py
                send_draft_to_partner.py
                process_partner_review.py
                send_for_signature.py
                handle_signature_completed.py
                push_to_crm.py
        infrastructure/
            adapters/
                postgres_contract_repository.py
                docx_contract_generator.py
                yousign_signature_service.py
                boondmanager_crm_service.py
            api/
                contract_routes.py
                webhook_routes.py

    vigilance/                     # Use case 2 : Vigilance documentaire
        domain/
            entities/
                vigilance_document.py
            value_objects/
                document_type.py
                compliance_status.py
            events/
                document_validated.py
                document_expired.py
                compliance_status_changed.py
            ports/
                document_repository.py
                document_storage.py         # Interface (S3)
                legal_verification.py       # Interface (API INSEE)
            services/
                vigilance_service.py
                compliance_checker.py
                expiration_monitor.py
        application/
            use_cases/
                request_documents.py
                upload_document.py
                validate_document.py
                reject_document.py
                check_compliance.py
                process_expirations.py
                purge_expired_data.py
        infrastructure/
            adapters/
                postgres_document_repository.py
                s3_document_storage.py
                insee_legal_verification.py
            api/
                vigilance_routes.py
                dashboard_routes.py

    third_party/                   # Contexte partagé : Tiers
        domain/
            entities/
                third_party.py
                magic_link.py
            ports/
                third_party_repository.py
                magic_link_repository.py
            services/
                third_party_service.py
                magic_link_service.py
        application/
            use_cases/
                find_or_create_third_party.py
                generate_magic_link.py
                verify_magic_link.py
        infrastructure/
            adapters/
                postgres_third_party_repository.py
            api/
                portal_routes.py           # Routes du portail tiers (magic link)

    shared/                        # Services transverses
        notification/
            ports/
                email_service.py           # Interface
            infrastructure/
                resend_email_service.py     # Implémentation Resend
            templates/                     # Templates d'emails
        scheduling/
            cron_jobs.py                   # Configuration des CRON
        auth/
            permissions.py                 # Gestion des rôles et permissions
```

### 9.2 Events inter-contextes

Les bounded contexts communiquent via des domain events :

- `ContractRequestCreated` → Vigilance vérifie la conformité du tiers
- `ComplianceStatusChanged` → Contractualisation met à jour les blocages
- `ContractSigned` → Push vers BoondManager, archivage
- `DocumentExpired` → Mise à jour compliance, alertes

---

## 10. Notes d'implémentation

### 10.1 Génération DOCX

Utiliser `python-docx-template` (basé sur python-docx + Jinja2). Le template DOCX maître est stocké dans le repo, pas en base. Les clauses optionnelles sont gérées avec des blocs Jinja2 `{% if %}` dans le template. La numérotation des articles est pré-calculée en Python et injectée comme variables.

### 10.2 Conversion DOCX → PDF

Nécessaire avant l'envoi à YouSign. Utiliser LibreOffice en mode headless :
```bash
libreoffice --headless --convert-to pdf document.docx
```

### 10.3 Sécurité des MagicLinks

- Token : UUID v4 + hash SHA-256, minimum 64 caractères
- Durée de validité par défaut : 7 jours
- Un seul magic link actif par tiers et par purpose à la fois
- Rate limiting sur le portail tiers
- Log de tous les accès

### 10.4 Idempotence des webhooks

Les webhooks BoondManager et YouSign peuvent être reçus en double. Implémenter une vérification d'idempotence :
- Stocker les event IDs déjà traités
- Ignorer les doublons

---

*Document de spécifications v1.0 — Bobby Contractualisation & Vigilance*
