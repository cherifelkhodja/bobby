# Turnover-IT API (JobConnect v2)

Documentation de l'intégration Turnover-IT pour Bobby.

---

## Vue d'ensemble

Turnover-IT est la plateforme utilisée pour :
- Publier des offres d'emploi (diffusion sur Free-Work)
- Synchroniser les compétences disponibles
- Gérer les candidatures externes

---

## Configuration

### Variables d'environnement

```bash
TURNOVERIT_API_KEY=your-api-key
TURNOVERIT_API_URL=https://api.turnover-it.com/jobconnect/v2
```

### Authentification

L'API utilise une **API Key** dans le header :

```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
```

---

## Client Bobby

**Fichier** : `backend/app/infrastructure/turnoverit/client.py`

### Configuration

```python
class TurnoverITClient:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        timeout: float = 10.0,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
```

---

## Endpoints utilisés

### Compétences

#### GET /skills
Récupère la liste des compétences disponibles.

```python
async def get_skills(self) -> list[Skill]:
    response = await self._get("/skills")
    return [
        Skill(
            name=item["name"],
            slug=item["slug"],
        )
        for item in response["data"]
    ]
```

**Réponse** :
```json
{
  "data": [
    {"name": "Python", "slug": "python"},
    {"name": "React", "slug": "react"},
    {"name": "FastAPI", "slug": "fastapi"}
  ]
}
```

### Offres d'emploi

#### POST /jobs
Publie une nouvelle offre d'emploi.

```python
async def publish_job(self, job: JobPostingCreate) -> JobPublishResult:
    payload = {
        "title": job.title,
        "description": job.description,
        "qualifications": job.qualifications,
        "location": {
            "country": job.location_country,
            "region": job.location_region,
            "city": job.location_city,
            "postalCode": job.location_postal_code,
        },
        "contractTypes": job.contract_types,
        "skills": job.skills,
        "experienceLevel": job.experience_level,
        "remote": job.remote,
        "startDate": job.start_date.isoformat() if job.start_date else None,
        "durationMonths": job.duration_months,
        "salary": {
            "minAnnual": job.salary_min_annual,
            "maxAnnual": job.salary_max_annual,
            "minDaily": job.salary_min_daily,
            "maxDaily": job.salary_max_daily,
        },
        "employerOverview": job.employer_overview,
    }

    response = await self._post("/jobs", json=payload)

    return JobPublishResult(
        reference=response["data"]["reference"],
        public_url=response["data"]["publicUrl"],
    )
```

**Payload d'exemple** :
```json
{
  "title": "Développeur Python Senior",
  "description": "Mission de 6 mois...",
  "qualifications": "5 ans d'expérience minimum...",
  "location": {
    "country": "FR",
    "region": "Île-de-France",
    "city": "Paris",
    "postalCode": "75008"
  },
  "contractTypes": ["freelance", "portage"],
  "skills": ["python", "fastapi", "postgresql"],
  "experienceLevel": "senior",
  "remote": "partial",
  "startDate": "2026-02-01",
  "durationMonths": 6,
  "salary": {
    "minDaily": 500,
    "maxDaily": 650
  },
  "employerOverview": "ESN spécialisée..."
}
```

**Réponse** :
```json
{
  "data": {
    "reference": "TIT-2026-12345",
    "publicUrl": "https://www.free-work.com/fr/jobs/12345"
  }
}
```

#### PATCH /jobs/{reference}
Met à jour une offre existante.

```python
async def update_job(
    self,
    reference: str,
    updates: JobPostingUpdate,
) -> None:
    payload = updates.model_dump(exclude_unset=True)
    await self._patch(f"/jobs/{reference}", json=payload)
```

#### DELETE /jobs/{reference}
Ferme/supprime une offre.

```python
async def close_job(self, reference: str) -> None:
    await self._delete(f"/jobs/{reference}")
```

---

## Modèles de données

### JobPostingCreate

```python
@dataclass
class JobPostingCreate:
    title: str
    description: str
    qualifications: str
    location_country: str  # Code ISO (FR, BE, CH...)
    location_region: str | None = None
    location_city: str | None = None
    location_postal_code: str | None = None
    contract_types: list[str] = field(default_factory=list)  # freelance, portage, cdi, cdd
    skills: list[str] = field(default_factory=list)  # Slugs des compétences
    experience_level: str | None = None  # junior, mid, senior, lead
    remote: str | None = None  # full, partial, none
    start_date: date | None = None
    duration_months: int | None = None
    salary_min_annual: int | None = None
    salary_max_annual: int | None = None
    salary_min_daily: int | None = None  # TJM min
    salary_max_daily: int | None = None  # TJM max
    employer_overview: str | None = None
```

### JobPublishResult

```python
@dataclass
class JobPublishResult:
    reference: str  # Référence Turnover-IT
    public_url: str  # URL publique Free-Work
```

### Skill

```python
@dataclass
class Skill:
    name: str   # Nom affiché
    slug: str   # Identifiant pour l'API
```

---

## Cache des compétences

Les compétences sont cachées dans la base de données pour éviter les appels API répétés.

### Tables

```sql
-- turnoverit_skills
CREATE TABLE turnoverit_skills (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    slug VARCHAR UNIQUE NOT NULL
);

-- turnoverit_skills_metadata
CREATE TABLE turnoverit_skills_metadata (
    id INTEGER PRIMARY KEY,
    last_synced_at TIMESTAMP NOT NULL,
    total_skills INTEGER NOT NULL
);
```

### Synchronisation

```python
async def sync_skills(self) -> int:
    """Synchronise les compétences depuis Turnover-IT."""
    skills = await self.client.get_skills()

    # Upsert dans la base
    for skill in skills:
        await self.skill_repo.upsert(skill)

    # Mettre à jour metadata
    await self.metadata_repo.update(
        last_synced_at=datetime.utcnow(),
        total_skills=len(skills),
    )

    return len(skills)
```

---

## Utilisation dans Bobby

### Endpoints API Bobby

| Endpoint Bobby | Méthode Turnover-IT |
|----------------|---------------------|
| `GET /admin/turnoverit/skills` | Cache local (DB) |
| `POST /admin/turnoverit/skills/sync` | `get_skills()` |
| `POST /hr/job-postings/{id}/publish` | `publish_job()` |
| `POST /hr/job-postings/{id}/close` | `close_job()` |

### Workflow de publication

```python
# 1. Créer le brouillon en base
job_posting = await job_posting_repo.create(draft_data)

# 2. Publier sur Turnover-IT
result = await turnoverit.publish_job(job_posting)

# 3. Mettre à jour avec la référence
job_posting.turnoverit_reference = result.reference
job_posting.turnoverit_public_url = result.public_url
job_posting.status = "published"
job_posting.published_at = datetime.utcnow()

await job_posting_repo.save(job_posting)
```

---

## Types de contrats

| Code | Description |
|------|-------------|
| `freelance` | Freelance / Indépendant |
| `portage` | Portage salarial |
| `cdi` | CDI |
| `cdd` | CDD |
| `interim` | Intérim |

---

## Niveaux d'expérience

| Code | Description |
|------|-------------|
| `junior` | 0-2 ans |
| `mid` | 3-5 ans |
| `senior` | 5-10 ans |
| `lead` | 10+ ans |

---

## Télétravail

| Code | Description |
|------|-------------|
| `full` | 100% télétravail |
| `partial` | Hybride |
| `none` | Présentiel uniquement |

---

## Gestion des erreurs

### Exceptions

```python
class TurnoverITError(Exception):
    """Erreur générique API Turnover-IT."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

class TurnoverITValidationError(TurnoverITError):
    """Erreur de validation (400)."""
    pass

class TurnoverITAuthError(TurnoverITError):
    """Erreur d'authentification (401)."""
    pass

class TurnoverITRateLimitError(TurnoverITError):
    """Rate limit dépassé (429)."""
    pass
```

### Handling

```python
async def _request(self, method: str, endpoint: str, **kwargs):
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.request(
            method,
            f"{self.api_url}{endpoint}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            **kwargs,
        )

        if response.status_code == 400:
            raise TurnoverITValidationError(400, response.json().get("message"))
        if response.status_code == 401:
            raise TurnoverITAuthError(401, "Invalid API key")
        if response.status_code == 429:
            raise TurnoverITRateLimitError(429, "Rate limit exceeded")
        if response.status_code >= 400:
            raise TurnoverITError(response.status_code, response.text)

        return response.json()
```

---

## Références

- API Documentation : JobConnect v2
- Base URL : `https://api.turnover-it.com/jobconnect/v2`
- Diffusion : Free-Work (www.free-work.com)
