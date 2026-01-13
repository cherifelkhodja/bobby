# ESN Cooptation - Project Memory

## Project Overview
Application de cooptation pour ESN (Entreprise de Services du Numérique) avec intégration BoondManager.

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend**: React, TypeScript, Vite, TailwindCSS, React Query
- **Authentication**: JWT (access + refresh tokens)
- **Email**: Resend API
- **Deployment**: Railway (Docker)

## Architecture
```
backend/
├── app/
│   ├── api/routes/v1/      # API endpoints
│   ├── application/        # Use cases
│   ├── domain/             # Entities, value objects
│   ├── infrastructure/     # External services (Boond, DB, cache, email)
│   └── config.py           # Settings
├── alembic/                # Database migrations
└── Dockerfile

frontend/
├── src/
│   ├── api/                # API client functions
│   ├── components/         # React components
│   │   ├── layout/         # Header, Footer, Layout
│   │   ├── ui/             # Reusable UI components
│   │   └── ThemeProvider.tsx
│   ├── contexts/           # Auth context
│   ├── hooks/              # Custom hooks (useTheme)
│   ├── pages/              # Page components
│   └── types/              # TypeScript interfaces
└── Dockerfile
```

## User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `user` | Consultant | Submit cooptations |
| `commercial` | Commercial | Manage opportunities, view associated cooptations |
| `rh` | RH | Manage users, view all cooptations, change cooptation status |
| `admin` | Administrator | Full access to all features |

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
- **Client**: `backend/app/infrastructure/boond/client.py`
- Fetches opportunities, resources (employees), agencies
- Resource filtering by state (1=actif, 2=mission)
- Resource type to role mapping:
  - Types 0, 1, 10 → `user` (Consultant)
  - Type 2 → `commercial`
  - Types 5, 6 → `rh` (RH, Direction RH)

### 2. Invitation System
- Admin can invite users from BoondManager resources list
- Stores `boond_resource_id` and `manager_boond_id` with invitations
- Email sent via Resend API with registration link
- **Role selector**: Admin can change the suggested role before sending invitation
- **Filters**: Filter resources by Agency and Type
- **Migration**: `003_add_inv_boond_ids.py`

### 3. Admin Panel (`frontend/src/pages/Admin.tsx`)
- **BoondTab**: Connection status, sync button, test connection
- **InvitationsTab**: Table of BoondManager resources with:
  - Consultant name, agency, type, suggested role
  - Role selector dropdown to change role before invitation
  - Agency and Type filters
  - "Inviter" button (disabled if already registered or pending invitation)
- **UsersTab**: User management (activate/deactivate, change role)

### 4. Authentication
- JWT with access (15min) and refresh (7d) tokens
- Password reset via email
- Email verification

### 5. Dark Mode Support
- **Tailwind config**: `darkMode: 'class'` for manual control
- **Theme hook**: `frontend/src/hooks/useTheme.ts`
  - Manages theme state: `system` | `light` | `dark`
  - Persists preference in localStorage
  - Cycles through modes: Auto → Clair → Sombre
- **ThemeProvider**: `frontend/src/components/ThemeProvider.tsx`
  - Initializes theme on app load
  - Listens for system preference changes
- **Toggle button**: In Header component (Sun/Moon/Monitor icons)
- All UI components styled with `dark:` variants

### 6. CV Transformer
Transform CVs (PDF/DOCX) into standardized Word documents using Google Gemini AI.

**Access**: admin, commercial, rh roles only

**Features**:
- Upload CV (PDF or DOCX, max 16 Mo)
- Select template (Gemini, Craftmania)
- Extract text from document
- Parse CV data using Gemini AI
- Generate formatted Word document using docxtpl
- Direct download of result
- Stats tracking per user (admin only)
- Template management in Admin panel

**Dependencies**:
- `google-generativeai` - Gemini API client
- `docxtpl` - Word template engine (Jinja2)
- `pypdf` - PDF text extraction
- `python-docx` - DOCX text extraction

**Database tables** (migration `004_add_cv_transformer_tables.py`):
- `cv_templates` - Word templates stored as BYTEA
- `cv_transformation_logs` - Usage tracking

**Files**:
- Backend: `backend/app/infrastructure/cv_transformer/`
- Use cases: `backend/app/application/use_cases/cv_transformer.py`
- API: `backend/app/api/routes/v1/cv_transformer.py`
- Frontend: `frontend/src/pages/CvTransformer.tsx`
- API client: `frontend/src/api/cvTransformer.ts`

## API Endpoints

### Admin (`/api/v1/admin`)
- `GET /boond/status` - BoondManager connection status
- `POST /boond/sync` - Sync opportunities
- `POST /boond/test` - Test connection
- `GET /boond/resources` - List BoondManager employees (states 1,2 only)
- `GET /users` - List all users
- `PATCH /users/{id}` - Update user
- `POST /users/{id}/role` - Change role
- `POST /users/{id}/activate` - Activate user
- `POST /users/{id}/deactivate` - Deactivate user

### Invitations (`/api/v1/invitations`)
- `POST /` - Create invitation (accepts `boond_resource_id`, `manager_boond_id`)
- `GET /` - List invitations
- `DELETE /{id}` - Cancel invitation

### CV Transformer (`/api/v1/cv-transformer`)
- `GET /templates` - List available templates (admin/commercial/rh)
- `POST /transform` - Transform CV file (multipart form: file + template_name)
- `POST /templates/{name}` - Upload/update template (admin only)
- `GET /stats` - Get transformation stats (admin only)

## Database Models

### Invitation
```python
id: UUID
email: str
first_name: str
last_name: str
role: str
token: str
boond_resource_id: str | None  # Added in migration 003
manager_boond_id: str | None   # Added in migration 003
expires_at: datetime
created_at: datetime
```

### User
```python
id: UUID
email: str
first_name: str
last_name: str
hashed_password: str
role: str  # user, commercial, rh, admin
is_verified: bool
is_active: bool
boond_resource_id: str | None
manager_boond_id: str | None
created_at: datetime
updated_at: datetime
```

### CvTemplate
```python
id: UUID
name: str  # unique identifier (gemini, craftmania)
display_name: str
description: str | None
file_content: bytes  # BYTEA
file_name: str
is_active: bool
created_at: datetime
updated_at: datetime
```

### CvTransformationLog
```python
id: UUID
user_id: UUID  # FK to users
template_id: UUID | None  # FK to cv_templates
template_name: str
original_filename: str
success: bool
error_message: str | None
created_at: datetime
```

## Environment Variables

### Backend
```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET=...
BOOND_API_URL=https://ui.boondmanager.com/api
BOOND_USERNAME=...
BOOND_PASSWORD=...
RESEND_API_KEY=...
FRONTEND_URL=https://...
GEMINI_API_KEY=...  # Google Gemini API key for CV transformation
```

### Frontend
```
VITE_API_URL=https://.../api/v1
```

## Deployment Notes

### Railway
- Backend and Frontend deployed as separate services
- **Dockerfile CMD**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2`
- Migrations run automatically on startup

### CORS
- Configured in `backend/app/main.py`
- Allows frontend URL origin

## Performance Optimizations

### BoondManager API Calls (2025-01-13)
- Removed separate `get_resource_types()` call - uses hardcoded mapping
- Removed separate `get_agencies()` call - extracts from `included` section
- **Resource type names hardcoded** (types 0, 1, 10 are all Consultant):
  ```python
  RESOURCE_TYPE_NAMES = {
      0: "Consultant",
      1: "Consultant",
      2: "Commercial",
      5: "RH",
      6: "Direction RH",
      10: "Consultant",
  }
  ```
- **Agency IDs**:
  ```python
  AGENCY_NAMES = {
      1: "Gemini",
      5: "Craftmania",
  }
  ```
- Reduced API calls from 4 to 2 for fetching resources

## TypeScript Interfaces

### BoondResource
```typescript
interface BoondResource {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  manager_id: string | null;
  agency_id: string | null;
  agency_name: string | null;
  resource_type: number | null;
  resource_type_name: string | null;
  suggested_role: UserRole;
}
```

## Common Commands

```bash
# Backend
cd backend
alembic upgrade head          # Run migrations
alembic revision -m "desc"    # Create migration
uvicorn app.main:app --reload # Dev server

# Frontend
cd frontend
npm run dev                   # Dev server
npm run build                 # Build
npm run lint                  # Lint
```

## Recent Changes Log

### 2026-01-13
- Added CV Transformer feature for transforming CVs to standardized Word documents
- Created migration `004_add_cv_transformer_tables.py` for templates and logs
- Added Gemini AI integration for CV data extraction
- Created infrastructure services for PDF/DOCX text extraction
- Added CvTransformer page with drag & drop upload, template selection, progress
- Added Templates management tab in Admin panel
- Added Stats tab in Admin panel for transformation statistics
- Added `/cv-transformer` route accessible to admin, commercial, rh roles
- Added "Outils" section in sidebar navigation

### 2025-01-13
- Added BoondManager resources endpoint for invitations
- Created migration `003_add_inv_boond_ids.py` for boond fields
- Redesigned InvitationsTab with resources table
- Added resource state filtering (1, 2 only)
- Implemented role suggestion based on resource type
- Fixed Mail icon import in Admin.tsx
- Added automatic migration execution in Dockerfile
- Optimized BoondManager API calls (removed unnecessary requests)
- Added pagination support to fetch all resources (maxResults=500)
- Added agency and type filters to InvitationsTab
- Added role selector dropdown before sending invitation
- Created new `rh` role for HR users (types 5, 6)
- Added system-based dark mode support (`darkMode: 'media'` → `darkMode: 'class'`)
- Created `useTheme` hook for theme management
- Created `ThemeProvider` component for theme initialization
- Added manual theme toggle button in Header (Auto/Clair/Sombre)
- Fixed dark mode styling across all Admin page components
