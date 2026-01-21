# ESN Cooptation (Bobby) - Project Memory

## Project Overview
Application de cooptation pour ESN (Entreprise de Services du Numérique) avec intégration BoondManager.

**Nom de l'application**: Bobby

## Documentation et Mémoire

### ⚠️ RÈGLE OBLIGATOIRE
**Avant chaque tâche** : Consulter `MEMORY.md` pour comprendre le contexte.
**Après chaque modification significative** : Mettre à jour `MEMORY.md` (changelog + sections concernées).

### Quand mettre à jour MEMORY.md
- ✅ Nouvelle fonctionnalité ajoutée
- ✅ Bug significatif corrigé
- ✅ Décision d'architecture prise (ajouter un ADR)
- ✅ Dépendance majeure mise à jour
- ✅ Problème découvert ou résolu
- ✅ Refactoring important
- ❌ Changements mineurs (typos, formatting)
- ❌ Commits intermédiaires de travail en cours

### Structure de la documentation

| Fichier | Description |
|---------|-------------|
| `MEMORY.md` | État du projet, historique, décisions (**maintenir à jour**) |
| `docs/skills/python-craftsmanship.md` | SOLID, Clean Code, typage, async |
| `docs/skills/hexagonal-architecture.md` | Structure, ports/adapters, DDD |
| `docs/skills/quality-security.md` | Tests, sécurité, observabilité |
| `docs/skills/workflow-devops.md` | Git, CI/CD, Docker, déploiement |
| `docs/api/boondmanager.md` | Endpoints, auth, exemples |
| `docs/api/turnoverit.md` | JobConnect v2 API |
| `docs/api/gemini.md` | CV parsing, anonymisation, matching |

## Tech Stack

### Backend
- **Framework**: FastAPI 0.115+
- **ORM**: SQLAlchemy 2.0.36+ (async)
- **Database**: PostgreSQL (asyncpg)
- **Migrations**: Alembic
- **Cache/Rate Limiting**: Redis
- **Email**: Resend API ou SMTP (MailHog dev, OVH/Gmail prod)
- **AI**: Google Gemini (google-generativeai)
- **Storage**: S3/Scaleway Object Storage
- **Security**: JWT, bcrypt, slowapi (rate limiting)

### Frontend
- **Framework**: React 18.3+
- **Build**: Vite 6+
- **Language**: TypeScript 5.7+
- **Styling**: TailwindCSS 3.4+
- **State**: Zustand (auth), React Query 5.62+ (server)
- **Forms**: React Hook Form + Zod
- **UI**: Headless UI, Lucide React (icons)
- **HTTP**: Axios

### Deployment
- **Platform**: Railway (Docker)
- **CI/CD**: Automatic migrations on startup

## Architecture

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/v1/           # API endpoints par domaine
│   │   ├── middleware/          # Rate limiter, security headers, RLS
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── dependencies.py      # Injection de dépendances
│   ├── application/
│   │   ├── use_cases/           # Logique métier (CQRS-like)
│   │   └── read_models/         # DTOs pour les lectures
│   ├── domain/
│   │   ├── entities/            # Entités métier riches
│   │   └── value_objects/       # Enums, types valeur
│   ├── infrastructure/
│   │   ├── boond/               # Client API BoondManager
│   │   ├── turnoverit/          # Client API Turnover-IT
│   │   ├── cv_transformer/      # Extracteurs PDF/DOCX, Gemini, DOCX generator
│   │   ├── anonymizer/          # Anonymisation Gemini
│   │   ├── matching/            # Matching CV/offre Gemini
│   │   ├── storage/             # Client S3
│   │   ├── database/            # Models SQLAlchemy, repositories
│   │   ├── email/               # Service email (Resend/SMTP)
│   │   ├── security/            # JWT, password hashing
│   │   ├── cache/               # Client Redis
│   │   ├── audit/               # Logging audit structuré
│   │   └── observability/       # Health checks, metrics
│   ├── quotation_generator/     # Module devis Thales (architecture parallèle)
│   ├── config.py                # Pydantic Settings
│   ├── dependencies.py          # DI globales
│   └── main.py                  # Application FastAPI
├── alembic/                     # Migrations
├── tests/                       # Unit, integration, e2e tests
├── pyproject.toml
└── Dockerfile

frontend/
├── src/
│   ├── api/                     # Clients API (axios)
│   ├── components/
│   │   ├── layout/              # Header, Sidebar, Layout
│   │   ├── ui/                  # Composants réutilisables
│   │   ├── cooptations/         # Formulaires cooptation
│   │   ├── ThemeProvider.tsx
│   │   ├── ErrorBoundary.tsx
│   │   └── QueryErrorBoundary.tsx
│   ├── hooks/                   # Hooks personnalisés
│   ├── pages/                   # Pages (routes)
│   │   └── admin/               # Sous-pages admin
│   ├── stores/                  # Zustand stores
│   ├── types/                   # TypeScript interfaces
│   ├── App.tsx                  # Routes + protection
│   └── main.tsx                 # Entry point
├── e2e/                         # Tests Playwright
├── package.json
└── Dockerfile
```

## User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `user` | Consultant | Soumettre cooptations, voir opportunités publiées |
| `commercial` | Commercial | Publier opportunités, gérer ses opportunités Boond |
| `rh` | RH | Créer annonces, gérer candidatures, voir toutes cooptations |
| `admin` | Administrateur | Accès complet à toutes les fonctionnalités |

**Backend enum**: `backend/app/domain/value_objects/status.py`
```python
class UserRole(str, Enum):
    USER = "user"
    COMMERCIAL = "commercial"
    RH = "rh"
    ADMIN = "admin"
```

## Key Features Implemented

### 1. BoondManager Integration
> **Détails complets** : `docs/api/boondmanager.md`

- **Client** : `backend/app/infrastructure/boond/client.py`
- Fetch opportunities, resources, agencies
- Create candidates and positionings
- Retry logic (3 attempts, exponential backoff)

### 2. Invitation System
- Admin invites users from BoondManager resources list
- Stores `boond_resource_id`, `manager_boond_id`, `phone`, `first_name`, `last_name`
- Email sent via Resend/SMTP with registration link
- **Role selector**: Admin can change suggested role before invitation
- **Filters**: Agency, Type, State (default: "En cours")
- **Pre-fill**: Registration form pre-filled with BoondManager data

### 3. Admin Panel (`frontend/src/pages/admin/`)
- **UsersTab**: User management (CRUD, roles, activation)
- **InvitationsTab**: BoondManager resources table with invitation flow
- **BoondTab**: Connection status, sync, test
- **TemplatesTab**: CV templates upload/management
- **StatsTab**: CV transformation statistics
- **ApiTab**: Test API connections (Boond, Gemini, Turnover-IT)

### 4. Authentication
- JWT with access (30min) and refresh (7d) tokens
- Auto token refresh on 401
- Password reset via email
- Email verification
- Magic link support (feature flag)

### 5. Dark Mode Support
- **Tailwind config**: `darkMode: 'class'`
- **Theme hook**: `frontend/src/hooks/useTheme.ts`
  - States: `system` | `light` | `dark`
  - Persists in localStorage
  - Cycles: Auto → Clair → Sombre
- **ThemeProvider**: Initializes on app load
- **Toggle**: In Header (Sun/Moon/Monitor icons)

### 6. CV Transformer
Transform CVs (PDF/DOCX) into standardized Word documents using Google Gemini AI.

**Access**: admin, commercial, rh

**Features**:
- Upload CV (PDF or DOCX, max 16 Mo)
- Select template (configurable)
- Extract text from document
- Parse CV data using Gemini AI
- Generate formatted Word document using docxtpl
- Direct download of result
- Stats tracking per user
- Template management in Admin panel
- Rate limit: 10/hour

**Data Processing** (`docx_generator.py`):
- `_nettoyer_formations()`: Cleans None/null values
- `_formater_langues()`: Bold language names
- `_preparer_experiences_avec_sauts_de_page()`: Page breaks

**Template Variables**:
```jinja2
{{ profil.titre_cible }}
{{ profil.annees_experience }}
{% for t in resume_competences.techniques_list %}
  {{ t.categorie }}: {{ t.valeurs }}
{% endfor %}
{% for d in formations.diplomes %}
  {{ d.display }}
{% endfor %}
{% for c in formations.certifications %}
  {{ c.display }}
{% endfor %}
{% for exp in experiences %}
  {{ exp.client }}, {{ exp.periode }}, {{ exp.titre }}
  {{ exp.contexte }}
  {{ exp.environnement_technique }}
  {{ exp.saut_de_page }}
{% endfor %}
```

### 7. Published Opportunities (Anonymized Boond)
Allow commercials and admins to publish anonymized opportunities for cooptation.

**Access**: admin, commercial (publishing), all authenticated (viewing)

**Features**:
- View Boond opportunities where user is main manager
- AI-powered anonymization using Gemini
- Preview and edit anonymized content
- Skills extraction
- Anti-duplicate check (boond_opportunity_id unique)
- Dedicated detail page at `/opportunities/:id`
- Cooptation support from detail page

**Workflow**:
1. Commercial views Boond opportunities
2. Clicks "Proposer" to anonymize with AI
3. Reviews/edits anonymized content
4. Publishes (saved in database)
5. Consultants see in `/opportunities`
6. Click to view detail page
7. Click "Proposer un candidat" to submit cooptation

**Anonymization Rules** (Gemini):
- Client names → Generic descriptions
- Internal project names → Generic
- Preserves: technical skills, methodologies, duration, experience level
- Preserves formatting: line breaks, bullets, paragraphs

### 8. Quotation Generator (Thales PSTF)
Generate quotations for Thales using BoondManager data and Excel templates.

**Access**: admin only

**Features**:
- Upload CSV with consultant/period data
- Auto-enrichment from BoondManager
- Auto-fill max_price from pricing grid (124-Data domain)
- Preview with validation
- Async background generation
- Create quotation in BoondManager API
- Download BoondManager PDF
- Fill Excel PSTF template
- Merge PDFs
- Download as ZIP

**CSV Columns** (simplified):
- `firstName`, `lastName` - Consultant name
- `po_start_date`, `po_end_date` - Period dates
- `periode` - Human-readable period
- `date` - Quotation date
- `amount_ht_unit` - TJM
- `total_uo` - Number of days
- `C22_domain`, `C22_activity`, `complexity` - Thales classification
- `max_price` - Optional, auto-filled for 124-Data
- `sow_reference`, `object_of_need` - SOW info

### 9. HR Recruitment (Turnover-IT Integration)
> **API Turnover-IT** : `docs/api/turnoverit.md`

Full HR recruitment feature for publishing job postings and managing applications.

**Access** : admin, rh (HR routes), public (application form)

**Features**:
- View opportunities from BoondManager (admin: all, rh: HR manager filtered)
- Create draft job postings from opportunities
- Publish to Turnover-IT
- Public application form (no auth)
- AI-powered CV matching using Gemini
- Application status management with history
- Notes on applications
- Create candidates in BoondManager
- CV storage on S3/Scaleway

**Opportunity Listing**:
- Admin: ALL open opportunities from BoondManager
- RH: Only where user is HR manager (`perimeterManagersType: "hr"`)
- States: `[0, 5, 6, 7, 10]`
- Colored badges for state

**Workflow**:
1. RH views opportunities in `/rh` dashboard
2. Clicks "Créer annonce" to create draft
3. Fills details (title, description, skills, location, salary...)
4. Publishes to Turnover-IT
5. Candidates apply via `/postuler/{token}`
6. System uploads CV to S3, calculates matching score
7. RH reviews applications sorted by score
8. RH changes status (nouveau → en_cours → entretien → accepté/refusé)
9. RH can create candidate in BoondManager

**Application Status Flow**:
```
nouveau → en_cours → entretien → accepté
   ↓         ↓           ↓
 refusé   refusé      refusé
```

**Matching Score Colors**:
- ≥80%: Green (excellent)
- 50-79%: Orange (potential)
- <50%: Red (low)

## API Endpoints

### Health & Monitoring (`/api/v1/health`)
- `GET /live` - Liveness probe
- `GET /ready` - Readiness probe (DB, Redis, Boond checks)
- `GET /metrics` - Prometheus format
- `GET /metrics/json` - JSON format

### Authentication (`/api/v1/auth`)
- `POST /register` - Create account (3/min rate limit)
- `POST /login` - Authenticate (5/min rate limit)
- `POST /refresh` - Refresh token
- `POST /verify-email` - Verify email
- `POST /forgot-password` - Request reset (3/min rate limit)
- `POST /reset-password` - Reset password
- `POST /magic-link` - Passwordless login (feature flag)

### Users (`/api/v1/users`)
- `GET /me` - Current user profile
- `PATCH /me` - Update profile
- `POST /me/password` - Change password

### Admin (`/api/v1/admin`)

**BoondManager:**
- `GET /boond/status` - Connection status
- `POST /boond/sync` - Sync opportunities
- `POST /boond/test` - Test connection
- `GET /boond/resources` - List employees (with filters)

**User Management:**
- `GET /users` - List all users (paginated)
- `GET /users/{id}` - Get user
- `PATCH /users/{id}` - Update user
- `POST /users/{id}/role` - Change role
- `POST /users/{id}/activate` - Activate
- `POST /users/{id}/deactivate` - Deactivate
- `DELETE /users/{id}` - Delete permanently

**Gemini Settings:**
- `GET /gemini/settings` - Get current model config
- `POST /gemini/settings` - Set model
- `POST /gemini/test` - Test connectivity

**Turnover-IT:**
- `GET /turnoverit/skills` - Get cached skills
- `POST /turnoverit/skills/sync` - Force sync

### Invitations (`/api/v1/invitations`)
- `POST /` - Create invitation
- `GET /` - List pending
- `GET /validate/{token}` - Validate token (public)
- `POST /accept` - Accept invitation (public)
- `POST /{id}/resend` - Resend email
- `DELETE /{id}` - Cancel invitation

### Opportunities (`/api/v1/opportunities`)
- `GET /` - List all opportunities
- `GET /my` - List commercial's opportunities
- `GET /{id}` - Get opportunity
- `POST /{id}/share` - Share for cooptation
- `POST /{id}/unshare` - Remove from cooptation
- `POST /{id}/assign` - Assign owner
- `POST /sync` - Sync from BoondManager

### Cooptations (`/api/v1/cooptations`)
- `POST /` - Create cooptation
- `GET /` - List all (admin)
- `GET /me` - List user's cooptations
- `GET /{id}` - Get details
- `GET /me/stats` - User stats
- `GET /stats` - Overall stats
- `PATCH /{id}/status` - Update status

### CV Transformer (`/api/v1/cv-transformer`)
- `GET /templates` - List templates (10/hour rate limit)
- `POST /transform` - Transform CV (10/hour rate limit)
- `POST /templates/{name}` - Upload template (admin)
- `GET /stats` - Statistics (admin)
- `GET /test-gemini` - Test Gemini (admin)

### Published Opportunities (`/api/v1/published-opportunities`)
- `GET /my-boond` - List Boond opportunities (admin/commercial)
- `GET /my-boond/{id}` - Get Boond opportunity detail
- `POST /anonymize` - Anonymize with AI
- `POST /publish` - Publish anonymized
- `GET /` - List published
- `GET /{id}` - Get published opportunity
- `PATCH /{id}/close` - Close opportunity

### HR (`/api/v1/hr`)

**Opportunities:**
- `GET /opportunities` - List open opportunities from Boond

**Job Postings:**
- `POST /job-postings` - Create draft
- `GET /job-postings` - List postings
- `GET /job-postings/{id}` - Get posting
- `PATCH /job-postings/{id}` - Update draft
- `POST /job-postings/{id}/publish` - Publish to Turnover-IT
- `POST /job-postings/{id}/close` - Close posting
- `GET /job-postings/{id}/applications` - List applications

**Applications:**
- `GET /applications/{id}` - Get application
- `PATCH /applications/{id}/status` - Update status
- `PATCH /applications/{id}/note` - Update notes
- `GET /applications/{id}/cv` - Get CV download URL
- `POST /applications/{id}/create-in-boond` - Create candidate in Boond

### Public Applications (`/api/v1/postuler`)
- `GET /{token}` - Get job posting info (public)
- `POST /{token}` - Submit application (public)

### Settings (`/api/v1/settings`)
- `GET /{key}` - Get setting (admin)
- `POST /{key}` - Set setting (admin)

### Quotation Generator (`/api/v1/quotation-generator`)
- `POST /preview` - Parse CSV and preview
- `POST /batches/{id}/generate` - Start generation
- `GET /batches/{id}/progress` - Get progress
- `GET /batches/{id}/details` - Get full details
- `PATCH /batches/{id}/quotations/{row}/contact` - Update contact
- `DELETE /batches/{id}/quotations/{row}` - Delete quotation
- `GET /batches/{id}/download/zip` - Download ZIP

## Database Models

### users
```python
id: UUID (PK)
email: str (unique)
hashed_password: str
first_name: str
last_name: str
role: str  # user, commercial, rh, admin
is_verified: bool
is_active: bool
phone: str | None
boond_resource_id: str | None
manager_boond_id: str | None
verification_token: str | None
reset_token: str | None
reset_token_expires: datetime | None
created_at: datetime
updated_at: datetime
```

### invitations
```python
id: UUID (PK)
email: str
role: str
token: str (unique)
invited_by: UUID (FK users.id)
expires_at: datetime
accepted_at: datetime | None
boond_resource_id: str | None
manager_boond_id: str | None
phone: str | None
first_name: str | None
last_name: str | None
created_at: datetime
```

### candidates
```python
id: UUID (PK)
email: str
first_name: str
last_name: str
civility: str | None
phone: str | None
daily_rate: float | None
cv_filename: str | None
cv_path: str | None
note: str | None
external_id: str | None  # BoondManager
created_at: datetime
updated_at: datetime
```

### opportunities
```python
id: UUID (PK)
external_id: str (unique)  # Boond ID
title: str
reference: str | None
start_date: date | None
end_date: date | None
response_deadline: date | None
budget: float | None
manager_name: str | None
manager_email: str | None
manager_boond_id: str | None
client_name: str | None
description: str | None
skills: JSON | None
location: str | None
is_active: bool
is_shared: bool  # For cooptation
owner_id: UUID (FK users.id) | None  # Commercial owner
synced_at: datetime | None
created_at: datetime
updated_at: datetime
```

### cooptations
```python
id: UUID (PK)
candidate_id: UUID (FK candidates.id)
opportunity_id: UUID (FK opportunities.id)
submitter_id: UUID (FK users.id)
status: str  # pending, in_review, interview, accepted, rejected
external_positioning_id: str | None  # Boond
status_history: JSON
rejection_reason: str | None
submitted_at: datetime
updated_at: datetime
```

### published_opportunities
```python
id: UUID (PK)
boond_opportunity_id: str (unique)  # Anti-doublon
title: str  # Anonymisé
description: text  # Anonymisé
skills: ARRAY(str)  # Extraites par IA
original_title: str | None  # Interne
original_data: JSON | None  # Backup Boond
end_date: date | None
status: str  # draft, published, closed
published_by: UUID (FK users.id)
created_at: datetime
updated_at: datetime
```

### job_postings
```python
id: UUID (PK)
opportunity_id: str (FK)
title: str
description: text
qualifications: text
location_country: str
location_region: str | None
location_city: str | None
location_postal_code: str | None
contract_types: JSON  # Array
skills: JSON  # Array
experience_level: str | None
remote: str | None  # full, partial, none
start_date: date | None
duration_months: int | None
salary_min_annual: int | None
salary_max_annual: int | None
salary_min_daily: int | None
salary_max_daily: int | None
employer_overview: text | None
status: str  # draft, published, closed
turnoverit_reference: str | None
turnoverit_public_url: str | None
application_token: str (unique)
created_by: UUID (FK users.id)
created_at: datetime
updated_at: datetime
published_at: datetime | None
closed_at: datetime | None
```

### job_applications
```python
id: UUID (PK)
job_posting_id: UUID (FK job_postings.id)
first_name: str
last_name: str
email: str
phone: str
job_title: str | None
tjm_min: int | None
tjm_max: int | None
availability_date: date | None
cv_s3_key: str
cv_filename: str
cv_text: text | None
matching_score: int | None
matching_details: JSON | None
status: str  # nouveau, en_cours, entretien, accepte, refuse
status_history: JSON
notes: text | None
boond_candidate_id: str | None
created_at: datetime
updated_at: datetime
```

### cv_templates
```python
id: UUID (PK)
name: str (unique)  # gemini, craftmania
display_name: str
description: str | None
file_content: BYTEA
file_name: str
is_active: bool
created_at: datetime
updated_at: datetime
```

### cv_transformation_logs
```python
id: UUID (PK)
user_id: UUID (FK users.id)
template_id: UUID (FK cv_templates.id) | None
template_name: str
original_filename: str
success: bool
error_message: str | None
created_at: datetime
```

### turnoverit_skills
```python
id: UUID (PK)
name: str
slug: str (unique)
```

### turnoverit_skills_metadata
```python
id: int (PK)
last_synced_at: datetime
total_skills: int
```

### app_settings
```python
id: UUID (PK)
key: str
value: JSON
created_by: UUID (FK users.id)
created_at: datetime
updated_at: datetime
```

## Database Migrations

| Migration | Purpose |
|-----------|---------|
| 001_initial_schema.py | Core tables (users, candidates, opportunities, cooptations) |
| 002_add_roles_invites.py | Invitations table with roles |
| 003_add_inv_boond_ids.py | BoondManager IDs on invitations |
| 004_add_cv_transformer_tables.py | cv_templates, cv_transformation_logs |
| 005_add_phone_to_users_invitations.py | Phone field |
| 006_add_names_to_invitations.py | first_name, last_name for pre-fill |
| 007_add_quotation_templates_table.py | Quotation templates |
| 008_add_published_opportunities.py | published_opportunities table |
| 009_add_hr_feature_tables.py | job_postings, job_applications |
| 010_add_row_level_security.py | PostgreSQL RLS policies |
| 011_add_turnoverit_skills_table.py | turnoverit_skills, metadata |
| 012_add_app_settings_table.py | app_settings table |
| 013_add_turnoverit_skills_table.py | Update turnoverit_skills |

## Environment Variables

### Backend
```bash
# Core
ENV=prod  # dev, test, prod
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
JWT_SECRET=your-secret-key
FRONTEND_URL=https://your-frontend.com

# BoondManager
BOOND_API_URL=https://ui.boondmanager.com/api
BOOND_USERNAME=username
BOOND_PASSWORD=password

# Email (Resend ou SMTP)
RESEND_API_KEY=re_xxx  # Si Resend
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user
SMTP_PASSWORD=password
SMTP_FROM=noreply@example.com

# Google Gemini AI
GEMINI_API_KEY=your-gemini-key

# Turnover-IT
TURNOVERIT_API_KEY=your-turnoverit-key
TURNOVERIT_API_URL=https://api.turnover-it.com/jobconnect/v2

# S3 Storage (Scaleway ou AWS)
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud  # Vide pour AWS
S3_BUCKET_NAME=esn-cooptation-cvs
S3_REGION=fr-par
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key

# AWS Secrets Manager (optionnel)
AWS_SECRETS_ENABLED=false
AWS_SECRETS_NAME=esn-cooptation/prod
AWS_SECRETS_REGION=eu-west-3

# Feature flags
FEATURE_MAGIC_LINK=false
FEATURE_EMAIL_NOTIFICATIONS=true
FEATURE_BOOND_SYNC=true
```

### Frontend
```bash
VITE_API_URL=https://your-backend.com/api/v1
```

## Security

### Rate Limiting
**Configuration**: `backend/app/api/middleware/rate_limiter.py`

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| `/auth/login` | 5/minute | Brute force protection |
| `/auth/register` | 3/minute | Spam prevention |
| `/auth/forgot-password` | 3/minute | Abuse prevention |
| `/cv-transformer/transform` | 10/hour | Expensive operation |
| Standard API | 100/minute | General protection |

**Response Headers**:
- `X-RateLimit-Limit`: Maximum requests
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset time
- `Retry-After`: Wait time (on 429)

### Security Headers
**Configuration**: `backend/app/api/middleware/security_headers.py`

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | max-age=31536000 | HTTPS (prod) |
| `X-Frame-Options` | DENY | Clickjacking |
| `X-Content-Type-Options` | nosniff | MIME sniffing |
| `Referrer-Policy` | strict-origin-when-cross-origin | Referrer control |
| `X-XSS-Protection` | 1; mode=block | XSS (legacy) |
| `Content-Security-Policy` | default-src 'self' | XSS/injection (prod) |
| `Permissions-Policy` | camera=(), microphone=() | Browser features |

### Row Level Security (RLS)
**Migration**: `010_add_row_level_security.py`

**Protected Tables**:
- `cooptations` - Users see own, commercials see their opportunities', admin/rh see all
- `job_applications` - Admin/rh see all, public can insert
- `cv_transformation_logs` - Users see own, admin sees all

**Context Functions**:
```sql
SELECT set_app_context('user-uuid', 'user-role');
SELECT clear_app_context();
```

### Audit Logging
**Module**: `backend/app/infrastructure/audit/logger.py`

**Logged Events**:
- Authentication: login success/failure, password reset
- User management: create, update, delete, role change
- Invitations: create, accept, delete
- Cooptations: create, update, status change
- CV transformations: success/failure
- HR operations: posting publish, application status
- Security events: rate limit exceeded, unauthorized access

**Usage**:
```python
from app.infrastructure.audit import audit_logger, AuditAction, AuditResource

audit_logger.log(
    AuditAction.LOGIN_SUCCESS,
    AuditResource.SESSION,
    user_id=user.id,
    ip_address=request.client.host,
    details={"email": user.email},
)
```

## Frontend Routes

### Public Routes
- `/login` - Login page
- `/register` - Registration
- `/forgot-password` - Password reset request
- `/reset-password` - Reset with token
- `/accept-invitation` - Accept invitation
- `/postuler/:token` - Public job application

### Protected Routes (all authenticated)
- `/dashboard` - User dashboard with stats
- `/opportunities` - List published opportunities
- `/opportunities/:id` - Opportunity detail
- `/my-cooptations` - User's cooptations
- `/profile` - Profile management

### Commercial/Admin Routes
- `/my-boond-opportunities` - Publish from BoondManager
- `/cv-transformer` - CV transformation tool

### HR Routes
- `/rh` - HR dashboard (opportunities + postings)
- `/rh/annonces/nouvelle/:oppId` - Create job posting
- `/rh/annonces/:postingId` - Posting details + applications

### Admin Routes
- `/admin` - Admin panel (tabs)
- `/quotation-generator` - Thales quotations

## TypeScript Interfaces

### User Types
```typescript
type UserRole = 'user' | 'commercial' | 'rh' | 'admin';

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_verified: boolean;
  is_active: boolean;
  phone?: string | null;
  boond_resource_id?: string | null;
  manager_boond_id?: string | null;
  created_at: string;
}
```

### Cooptation Types
```typescript
type CooptationStatus = 'pending' | 'in_review' | 'interview' | 'accepted' | 'rejected';

interface Cooptation {
  id: string;
  candidate: Candidate;
  opportunity: Opportunity;
  submitter: User;
  status: CooptationStatus;
  status_history: StatusChange[];
  rejection_reason?: string;
  submitted_at: string;
}
```

### HR Types
```typescript
type JobPostingStatus = 'draft' | 'published' | 'closed';
type ApplicationStatus = 'nouveau' | 'en_cours' | 'entretien' | 'accepte' | 'refuse';

interface OpportunityForHR {
  id: string;
  title: string;
  reference: string;
  client_name: string | null;
  state: number | null;
  state_name: string | null;
  state_color: string | null;
  hr_manager_name: string | null;
  has_job_posting: boolean;
  job_posting_id: string | null;
  job_posting_status: JobPostingStatus | null;
  applications_count: number;
  new_applications_count: number;
}

interface JobPosting {
  id: string;
  opportunity_id: string;
  title: string;
  description: string;
  qualifications: string;
  location_country: string;
  contract_types: string[];
  skills: string[];
  status: JobPostingStatus;
  application_token: string;
  application_url: string;
  turnoverit_reference?: string;
  applications_total: number;
  applications_new: number;
}

interface JobApplication {
  id: string;
  job_posting_id: string;
  full_name: string;
  email: string;
  phone: string;
  job_title: string;
  tjm_range: string;
  availability_date: string;
  cv_filename: string;
  cv_download_url?: string;
  matching_score?: number;
  matching_details?: MatchingDetails;
  status: ApplicationStatus;
  status_display: string;
  notes?: string;
  boond_candidate_id?: string;
}

interface MatchingDetails {
  score: number;
  strengths: string[];
  gaps: string[];
  summary: string;
}
```

### Published Opportunity Types
```typescript
type PublishedOpportunityStatus = 'draft' | 'published' | 'closed';

interface BoondOpportunity {
  id: string;
  title: string;
  reference: string;
  description: string | null;
  company_name: string | null;
  state: number | null;
  state_name: string | null;
  is_published: boolean;
}

interface PublishedOpportunity {
  id: string;
  boond_opportunity_id: string;
  title: string;
  description: string;
  skills: string[];
  end_date: string | null;
  status: PublishedOpportunityStatus;
  status_display: string;
  created_at: string;
  updated_at: string;
}
```

### BoondManager Types
```typescript
interface BoondResource {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string | null;
  manager_id: string | null;
  manager_name: string | null;
  agency_id: string | null;
  agency_name: string | null;
  resource_type: number | null;
  resource_type_name: string | null;
  state: number | null;
  state_name: string | null;
  suggested_role: UserRole;
}
```

## BoondManager Integration

> **Voir `docs/api/boondmanager.md`** pour les détails complets (endpoints, mapping, hardcoded values).

**Client** : `backend/app/infrastructure/boond/client.py`

**Mapping rapide** :
- Resource types 0, 1, 10 → `user` | Type 2 → `commercial` | Types 5, 6 → `rh`
- States : 0=Sortie, 1=En cours, 2=Intercontrat, 3=Arrivée prochaine, 7=Sortie prochaine

## Common Commands

```bash
# Backend
cd backend
alembic upgrade head          # Run migrations
alembic revision -m "desc"    # Create migration
uvicorn app.main:app --reload # Dev server
pytest                        # Run tests
ruff check .                  # Lint
mypy .                        # Type check

# Frontend
cd frontend
npm run dev                   # Dev server
npm run build                 # Build
npm run lint                  # Lint
npm run test                  # Run tests
npm run type-check            # Type check
npx playwright test           # E2E tests
```

## Deployment (Railway)

**Dockerfile CMD**:
```dockerfile
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
```

- Migrations run automatically on startup
- Backend and Frontend as separate services
- CORS configured in `backend/app/main.py`

## Dependencies

### Backend (pyproject.toml)
```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "python-jose[cryptography]>=3.3.0",
    "bcrypt>=4.2.0",
    "httpx>=0.28.0",
    "tenacity>=9.0.0",
    "redis>=5.2.0",
    "aiosmtplib>=3.0.2",
    "resend>=2.5.0",
    "structlog>=24.4.0",
    "python-multipart>=0.0.18",
    "email-validator>=2.2.0",
    "google-generativeai>=0.8.3",
    "docxtpl>=0.19.0",
    "python-docx>=1.1.2",
    "openpyxl>=3.1.5",
    "PyPDF2>=3.0.1",
    "aioboto3>=13.2.0",
    "boto3>=1.35.0",
    "slowapi>=0.1.9",
]
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "@headlessui/react": "^2.2.0",
    "@tanstack/react-query": "^5.62.0",
    "axios": "^1.7.9",
    "lucide-react": "^0.468.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-hook-form": "^7.54.0",
    "react-router-dom": "^7.0.2",
    "sonner": "^1.7.1",
    "zod": "^3.24.1",
    "zustand": "^5.0.2"
  },
  "devDependencies": {
    "@hookform/resolvers": "^3.9.1",
    "@tailwindcss/forms": "^0.5.9",
    "@types/react": "^18.3.14",
    "@typescript-eslint/eslint-plugin": "^8.18.0",
    "@vitejs/plugin-react": "^4.3.4",
    "tailwindcss": "^3.4.16",
    "typescript": "^5.7.2",
    "vite": "^6.0.3",
    "vitest": "^2.1.8",
    "@testing-library/react": "^16.1.0",
    "@playwright/test": "^1.49.1"
  }
}
```

## Technical Debt & Changelog

> **Voir `MEMORY.md`** pour la dette technique, les ADRs et l'historique complet des changements.
