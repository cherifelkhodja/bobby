# Turnover-IT API (JobConnect v2)

Documentation de l'intégration Turnover-IT pour Bobby.

---

## Vue d'ensemble

Turnover-IT est la plateforme utilisée pour :
- Publier des offres d'emploi (diffusion sur Free-Work)
- Synchroniser les compétences disponibles
- Recevoir les candidatures via webhook

**Base URL** : `https://api.turnover-it.com/jobconnect/v2`

---

## Configuration

### Variables d'environnement

```bash
TURNOVERIT_API_KEY=your-api-key
TURNOVERIT_API_URL=https://api.turnover-it.com/jobconnect/v2
```

### Authentification

L'API utilise **OAuth Bearer token** :

```bash
curl --request POST \
  --url https://api.turnover-it.com/jobconnect/v2/jobs \
  --header 'Authorization: Bearer 10a9cea1-0001-0002-0003-113a756cf4a3'
```

> **Note** : Les tokens préfixés par `test-` sont des tokens de test. Les offres sont automatiquement en Draft et ne peuvent pas être publiées.

### Format de sortie

Utiliser `Accept: application/ld+json` pour le format JSON-LD avec pagination Hydra (recommandé).

---

## Endpoints API

### Jobs

#### GET /jobs/list
Liste toutes les offres **sans les candidatures** (recommandé pour listing).

```bash
curl --request GET \
  --url https://api.turnover-it.com/jobconnect/v2/jobs/list \
  --header 'Authorization: Bearer {token}' \
  --header 'Accept: application/ld+json'
```

#### GET /jobs
Liste toutes les offres **avec leurs candidatures** (backup uniquement).

#### GET /jobs/:reference
Récupère une offre et ses candidatures par référence.

```bash
curl --request GET \
  --url https://api.turnover-it.com/jobconnect/v2/jobs/ref-001 \
  --header 'Authorization: Bearer {token}'
```

#### POST /jobs
Crée une nouvelle offre d'emploi.

```bash
curl --request POST \
  --url https://api.turnover-it.com/jobconnect/v2/jobs \
  --header 'Authorization: Bearer {token}' \
  --header 'Content-Type: application/json' \
  --data '{
    "reference": "ref-001",
    "contract": ["PERMANENT", "FREELANCE"],
    "title": "Front-end developer",
    "description": "(≥500 chars) Lorem ipsum...",
    "qualifications": "(≥150 chars) Lorem ipsum...",
    "employerOverview": "Description entreprise...",
    "experienceLevel": "INTERMEDIATE",
    "startDate": "2024-04-30",
    "skills": ["php", "go", "sql"],
    "durationInMonths": 10,
    "salary": {
      "minAnnual": 20000,
      "maxAnnual": 40000,
      "minDaily": 500,
      "maxDaily": 900,
      "currency": "EUR"
    },
    "location": {
      "country": "France",
      "locality": "Paris",
      "region": "Île-de-France",
      "postalCode": "75008"
    },
    "remote": "PARTIAL",
    "application": {
      "callbackUrl": "https://bobby.example.com/webhook/turnoverit"
    },
    "status": "PUBLISHED"
  }'
```

**Réponse 201** :
```json
{
  "success": true,
  "message": "Job created successfully"
}
```

#### PUT /jobs/:reference
Met à jour une offre (tous les champs doivent être renvoyés).

#### DELETE /jobs/:reference
Supprime une offre.

```bash
curl --request DELETE \
  --url https://api.turnover-it.com/jobconnect/v2/jobs/ref-001 \
  --header 'Authorization: Bearer {token}'
```

### Skills

#### GET /jobconnect/skills
Liste des compétences disponibles (paginé, ~1244 skills).

```bash
curl --request GET \
  --url https://api.turnover-it.com/jobconnect/skills \
  --header 'Authorization: Bearer {token}'
```

**Recherche** : `GET /jobconnect/skills?q=python`

---

## Enums officiels

### Contract (type de contrat)

| Key | Description |
|-----|-------------|
| `PERMANENT` | CDI |
| `FIXED-TERM` | CDD |
| `FREELANCE` | Freelance |
| `INTERCONTRACT` | Sous-traitance (spécifique ESN) |

> **Note** : Seules ces 4 valeurs sont acceptées par l'API Turnover-IT.

### Remote (télétravail)

| Key | Description |
|-----|-------------|
| `""` (vide) | Non spécifié |
| `NONE` | Pas de télétravail |
| `PARTIAL` | 50% télétravail |
| `FULL` | 100% télétravail |

> **Note** : La valeur peut être une chaîne vide dans les réponses API.

### Experience Level

| Key | Description |
|-----|-------------|
| `JUNIOR` | 0-2 ans |
| `INTERMEDIATE` | 3-5 ans |
| `SENIOR` | 6-10 ans |
| `EXPERT` | > 10 ans |

### Status

| Key | Description |
|-----|-------------|
| `DRAFT` | Brouillon |
| `PUBLISHED` | Publiée |
| `PRIVATE` | Privée |
| `INACTIVE` | Inactive |
| `EXPIRED` | Expirée |

### Currency

| Key | Description |
|-----|-------------|
| `EUR` | Euros |
| `USD` | US Dollars |
| `GBP` | British Pounds |

### Availability (candidat)

| Key | Description |
|-----|-------------|
| `IMMEDIATE` | Immédiate |
| `WITHIN_1_MONTH` | Sous 1 mois |
| `WITHIN_2_MONTH` | Sous 2 mois |
| `WITHIN_3_MONTH` | Sous 3 mois |
| `MORE_THAN_3_MONTH` | Plus de 3 mois |

### Language Level

| Key | Description |
|-----|-------------|
| `NOTIONS` | Notions |
| `LIMITED_PROFESSIONAL_SKILLS` | Compétences professionnelles limitées |
| `FULL_PROFESSIONAL_CAPACITY` | Capacité professionnelle complète |
| `NATIVE_OR_BILINGUAL` | Natif ou bilingue |

---

## Job Resource (structure complète)

### Champs pour création (POST /jobs)

```json
{
  "reference": "ref-001",           // required, unique
  "recruiterAlias": "recruiter-1",  // optional
  "contract": ["PERMANENT"],        // required, array
  "title": "Front-end developer",   // required, 5-100 chars
  "description": "...",             // required, 500-3000 chars
  "qualifications": "...",          // required, 150-3000 chars
  "employerOverview": "...",        // optional, <3000 chars
  "experienceLevel": "INTERMEDIATE",// optional, enum
  "startDate": "2024-04-30",        // optional, yyyy-mm-dd (null = ASAP)
  "skills": ["php", "go"],          // optional, slugs from /skills
  "durationInMonths": 10,           // optional, for fixed-term
  "pushToTop": true,                // optional, push d+7
  "salary": {
    "minAnnual": 40000,
    "maxAnnual": 50000,
    "minDaily": 350,                // for FREELANCE
    "maxDaily": 500,
    "currency": "EUR"               // required in salary
  },
  "location": {                     // required
    "country": "France",            // required
    "region": "Île-de-France",      // required (or postalCode)
    "locality": "Paris",            // optional
    "postalCode": "75008"           // optional (or region)
  },
  "remote": "PARTIAL",              // optional, default NONE
  "application": {                  // optional
    "name": "Jane Doe",             // contact name (option payante)
    "phone": "06 01 02 03 04",      // contact phone (option payante)
    "email": "jane@company.com",    // contact email (option payante)
    "url": "https://apply.com",     // redirect URL (option payante)
    "callbackUrl": "https://webhook.com"  // webhook URL
  },
  "status": "PUBLISHED"             // required, enum
}
```

### Champs supplémentaires en lecture (GET /jobs)

```json
{
  "@id": "/jobconnect/v2/jobs/ref-001",
  "@type": "JobPosting",
  "publicUrl": "https://www.free-work.com/fr/tech-it/.../job-mission/...",
  "location": {
    "county": "Paris",              // Département
    "latitude": 48.8588897,         // Coordonnées GPS
    "longitude": 2.320041
  },
  "salary": {
    "@type": "SalaryDTO",
    "@id": "/.well-known/genid/..."
  }
}
```

> **Note** : Les champs `@id`, `@type`, `publicUrl`, `county`, `latitude`, `longitude` sont retournés uniquement en lecture.

### Contraintes de validation

| Champ | Contrainte |
|-------|------------|
| `title` | 5-100 caractères |
| `description` | 500-3000 caractères |
| `qualifications` | 150-3000 caractères (sinon null) |
| `salary.maxDaily - minDaily` | ≤ 500 |
| `salary.maxAnnual - minAnnual` | ≤ 50000 |

---

## Application Resource (candidature)

Structure reçue via webhook ou GET /jobs/:reference :

```json
{
  "jobPostingReference": "ref-001",
  "jobConnectToken": "1234-1234-1234-1234",
  "title": "Full-stack developer",
  "content": "Message du candidat...",
  "gender": "male",
  "firstname": "Jean-Paul",
  "lastname": "Dumas",
  "email": "jean-paul@example.com",
  "phone": "+33602030405",
  "contracts": ["PERMANENT"],
  "studyLevel": 5,
  "studies": [
    {
      "diplomaTitle": "Software Engineer",
      "diplomaLevel": "Bac+ 5",
      "school": "EFREI",
      "graduationYear": 2022
    }
  ],
  "experience": "JUNIOR",
  "remoteModes": ["PARTIAL", "NONE"],
  "availability": "WITHIN_1_MONTH",
  "salary": {
    "averageDaily": 500,
    "grossAnnual": 48000,
    "currency": "EUR"
  },
  "desiredJobs": ["Administrateur BDD", "Dev Full-Stack"],
  "professionalExperience": [
    {
      "jobTitle": "Developer",
      "contract": "PERMANENT",
      "companyName": "Company",
      "location": { "region": "Île-de-France", "country": "France" },
      "description": "...",
      "remoteMode": "NONE",
      "startYearAt": 2020,
      "endYearAt": 2023,
      "current": false
    }
  ],
  "skills": ["php", "go", "sql"],
  "softSkills": ["Agilité", "Gestion de projet"],
  "languages": [
    { "language": "FR", "level": "NATIVE_OR_BILINGUAL" },
    { "language": "EN", "level": "FULL_PROFESSIONAL_CAPACITY" }
  ],
  "location": {
    "locality": "Lyon",
    "region": "Auvergne-Rhône-Alpes",
    "country": "France"
  },
  "mobilities": [
    { "region": "Île-de-France", "country": "France" }
  ],
  "linkedInUrl": null,
  "downloadUrl": "https://app.turnover-it.com/download/cv.pdf",
  "additionalDocumentUrl": null
}
```

> **Note** : `downloadUrl` valide 1 heure seulement.

---

## Pagination (JSON-LD Hydra)

```json
{
  "@context": "/contexts/JobPosting",
  "@id": "/jobconnect/v2/jobs/list",
  "@type": "hydra:Collection",
  "hydra:totalItems": 54,
  "hydra:member": [...],
  "hydra:view": {
    "@id": "/jobconnect/v2/jobs/list?page=1",
    "@type": "hydra:PartialCollectionView",
    "hydra:first": "/jobconnect/v2/jobs/list?page=1",
    "hydra:last": "/jobconnect/v2/jobs/list?page=2",
    "hydra:next": "/jobconnect/v2/jobs/list?page=2"
  }
}
```

**Pagination** : `GET /jobs/list?page=2` (30 items/page par défaut)

---

## Webhook (réception candidatures)

Un webhook est une URL à laquelle Turnover-IT envoie les candidatures dès leur réception.

### Fonctionnement

Quand un candidat postule à une offre, Turnover-IT envoie une requête **POST** à l'URL configurée avec les données JSON de la candidature. Chaque requête contient une seule candidature.

### Configuration de l'URL

L'URL doit utiliser **HTTPS**. Deux options :

| Option | Description |
|--------|-------------|
| **URL globale** | Une seule URL pour toutes les candidatures. Utiliser `jobPostingReference` et `jobConnectToken` pour identifier l'offre. Configuré dans les paramètres du compte client. |
| **URL dynamique** | Une URL différente par offre via `application.callbackUrl` lors de la création. Ex: `https://bobby.example.com/webhook/turnoverit/{reference}` |

### Politique de retry

En cas d'indisponibilité du webhook (code != 200/201), Turnover-IT renvoie la candidature :

| Retry | Délai |
|-------|-------|
| 1 | 0.6s |
| 2 | 3s |
| 3 | 15s |
| 4 | 75s |
| 5-10 | 90s |

Après échec, renvoi toutes les **6 heures** pendant **1 semaine maximum**. Ensuite, utiliser `GET /jobs/:reference` pour récupérer les candidatures.

### Payload reçu (exemple)

```json
{
  "jobPostingReference": "ref-001",
  "jobConnectToken": "1234-1234-1234-1234",
  "title": "Full-stack developer",
  "gender": "male",
  "firstname": "Jean-Paul",
  "lastname": "Dumas",
  "email": "jean-paul.dumas@example.com",
  "phone": "+33602030405",
  "studyLevel": "5",
  "studies": [
    {
      "diplomaTitle": "Ingénieur logiciel",
      "diplomaLevel": "Bac+ 5",
      "school": "EFREI",
      "graduationYear": 2022
    }
  ],
  "experience": "JUNIOR",
  "remote": ["PARTIAL", "NONE"],
  "availability": "WITHIN_1_MONTH",
  "desiredJobs": ["Administrateur BDD", "Dev Full-Stack"],
  "skills": ["php", "go", "sql"],
  "softSkills": ["Agilité", "Gestion de projet"],
  "languages": [
    { "language": "PT", "level": "FULL_PROFESSIONAL_CAPACITY" }
  ],
  "location": {
    "locality": "Lyon",
    "postalCode": null,
    "county": "Métropole de Lyon",
    "region": "Auvergne-Rhône-Alpes",
    "country": "France"
  },
  "mobilities": [
    {
      "locality": "Paris",
      "postalCode": "75000",
      "county": null,
      "region": "Île-de-France",
      "country": "France"
    }
  ],
  "downloadUrl": "https://example.com/download/url"
}
```

### Test du webhook

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"jobPostingReference":"ref-001","firstname":"Test","lastname":"User","email":"test@example.com"}' \
  "https://bobby.example.com/webhook/turnoverit"
```

### Implémentation Bobby

> **Note** : Bobby n'utilise pas actuellement le webhook. Les candidatures sont soumises via le formulaire public `/postuler/:token` qui stocke directement en base.

**Alternative future** : Implémenter un endpoint webhook pour recevoir les candidatures Free-Work directement.

---

## Client Bobby

**Fichier** : `backend/app/infrastructure/turnoverit/client.py`

### Implémentation

```python
class TurnoverITClient:
    def __init__(self, api_url: str, api_key: str, timeout: float = 10.0):
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout

    async def publish_job(self, job: JobPostingCreate) -> JobPublishResult:
        payload = {
            "reference": job.reference,
            "contract": job.contract_types,  # ["FREELANCE", "PERMANENT"]
            "title": job.title,
            "description": job.description,  # ≥500 chars
            "qualifications": job.qualifications,  # ≥150 chars
            "employerOverview": job.employer_overview,
            "experienceLevel": job.experience_level,  # JUNIOR, INTERMEDIATE, SENIOR, EXPERT
            "startDate": job.start_date.isoformat() if job.start_date else None,
            "skills": job.skills,  # slugs from /skills
            "durationInMonths": job.duration_months,
            "salary": {
                "minAnnual": job.salary_min_annual,
                "maxAnnual": job.salary_max_annual,
                "minDaily": job.salary_min_daily,
                "maxDaily": job.salary_max_daily,
                "currency": "EUR",
            },
            "location": {
                "country": job.location_country,
                "region": job.location_region,
                "locality": job.location_city,
                "postalCode": job.location_postal_code,
            },
            "remote": job.remote,  # NONE, PARTIAL, FULL
            "status": "PUBLISHED",
        }
        response = await self._post("/jobs", json=payload)
        # Response contains publicUrl after publication
        return JobPublishResult(reference=job.reference, public_url=response.get("publicUrl"))

    async def delete_job(self, reference: str) -> None:
        await self._delete(f"/jobs/{reference}")

    async def get_skills(self, page: int = 1) -> list[Skill]:
        response = await self._get(f"/skills?page={page}")
        return [Skill(name=s["name"], slug=s["slug"]) for s in response["hydra:member"]]
```

---

## Cache des compétences Bobby

### Tables SQL

```sql
CREATE TABLE turnoverit_skills (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    slug VARCHAR UNIQUE NOT NULL
);

CREATE TABLE turnoverit_skills_metadata (
    id INTEGER PRIMARY KEY,
    last_synced_at TIMESTAMP NOT NULL,
    total_skills INTEGER NOT NULL
);
```

### Endpoints Bobby

| Endpoint Bobby | Action |
|----------------|--------|
| `GET /admin/turnoverit/skills` | Liste depuis cache DB |
| `POST /admin/turnoverit/skills/sync` | Sync depuis API Turnover-IT |
| `POST /hr/job-postings/{id}/publish` | Publie sur Turnover-IT |
| `POST /hr/job-postings/{id}/close` | Supprime de Turnover-IT |

---

## Gestion des erreurs

```python
class TurnoverITError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

class TurnoverITValidationError(TurnoverITError):
    """400 - Erreur de validation."""
    pass

class TurnoverITAuthError(TurnoverITError):
    """401 - Token invalide."""
    pass
```

**Exemple erreur 400** :
```json
{
  "success": false,
  "message": [
    {
      "title": "An error occurred",
      "detail": "description: String must be at least 500 characters long.",
      "message": "String must be at least 500 characters long."
    }
  ]
}
```

---

## Références

- **API Base URL** : `https://api.turnover-it.com/jobconnect/v2`
- **Skills URL** : `https://api.turnover-it.com/jobconnect/skills`
- **Diffusion** : Free-Work (www.free-work.com)
- **Token management** : https://app.turnover-it.com/
