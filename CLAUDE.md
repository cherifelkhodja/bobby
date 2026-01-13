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
│   ├── contexts/           # Auth context
│   ├── pages/              # Page components
│   └── types/              # TypeScript interfaces
└── Dockerfile
```

## Key Features Implemented

### 1. BoondManager Integration
- **Client**: `backend/app/infrastructure/boond/client.py`
- Fetches opportunities, resources (employees), agencies
- Resource filtering by state (1=actif, 2=mission)
- Resource type to role mapping:
  - Types 0, 1, 10 → `user` (Consultant)
  - Type 2 → `commercial`
  - Types 5, 6 → `admin` (RH)

### 2. Invitation System
- Admin can invite users from BoondManager resources list
- Stores `boond_resource_id` and `manager_boond_id` with invitations
- Email sent via Resend API with registration link
- **Migration**: `003_add_inv_boond_ids.py`

### 3. Admin Panel (`frontend/src/pages/Admin.tsx`)
- **BoondTab**: Connection status, sync button, test connection
- **InvitationsTab**: Table of BoondManager resources with:
  - Consultant name, agency, type, suggested role
  - "Inviter" button (disabled if already registered or pending invitation)
- **UsersTab**: User management (activate/deactivate, change role)

### 4. Authentication
- JWT with access (15min) and refresh (7d) tokens
- Password reset via email
- Email verification

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
role: str  # user, commercial, admin
is_verified: bool
is_active: bool
boond_resource_id: str | None
manager_boond_id: str | None
created_at: datetime
updated_at: datetime
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
- **Resource type names hardcoded**:
  ```python
  RESOURCE_TYPE_NAMES = {
      0: "Consultant",
      1: "Manager",
      2: "Commercial",
      5: "RH",
      6: "Direction RH",
      10: "Consultant Senior",
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

### 2025-01-13
- Added BoondManager resources endpoint for invitations
- Created migration `003_add_inv_boond_ids.py` for boond fields
- Redesigned InvitationsTab with resources table
- Added resource state filtering (1, 2 only)
- Implemented role suggestion based on resource type
- Fixed Mail icon import in Admin.tsx
- Added automatic migration execution in Dockerfile
- Optimized BoondManager API calls (removed unnecessary requests)
