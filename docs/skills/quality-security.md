# Quality & Security

Standards de qualité et sécurité pour les projets Gemini Consulting.

---

## Tests

### Pyramide des tests

```
        /\
       /  \     E2E (10%)
      /----\    - Playwright
     /      \   - Parcours critiques
    /--------\  Integration (20%)
   /          \ - API tests
  /------------\- DB tests
 /              \
/----------------\ Unit (70%)
                  - Domain logic
                  - Pure functions
```

### Structure des tests

```
tests/
├── unit/
│   ├── domain/
│   │   ├── test_user_entity.py
│   │   └── test_cooptation_status.py
│   └── application/
│       └── test_create_user_use_case.py
├── integration/
│   ├── test_user_repository.py
│   ├── test_boond_client.py
│   └── test_auth_endpoints.py
└── e2e/
    ├── test_login_flow.py
    └── test_cooptation_flow.py
```

### Pattern Given/When/Then

```python
import pytest
from app.domain.entities.user import User
from app.domain.value_objects.status import UserRole

class TestUserEntity:
    def test_admin_can_manage_users(self):
        # Given
        user = User(
            id=uuid4(),
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        # When
        result = user.can_manage_users()

        # Then
        assert result is True

    def test_regular_user_cannot_manage_users(self):
        # Given
        user = User(
            id=uuid4(),
            email="user@test.com",
            first_name="Regular",
            last_name="User",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        # When
        result = user.can_manage_users()

        # Then
        assert result is False
```

### Fixtures réutilisables

```python
# tests/conftest.py
import pytest
from uuid import uuid4

@pytest.fixture
def user_factory():
    def _create_user(
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        **kwargs,
    ) -> User:
        defaults = {
            "id": uuid4(),
            "email": f"test-{uuid4()}@test.com",
            "first_name": "Test",
            "last_name": "User",
            "role": role,
            "is_active": is_active,
            "created_at": datetime.utcnow(),
        }
        defaults.update(kwargs)
        return User(**defaults)
    return _create_user

@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()
```

### Tests d'intégration API

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestAuthEndpoints:
    async def test_login_success(self, client: AsyncClient, test_user):
        # Given
        payload = {
            "email": test_user.email,
            "password": "validpassword123",
        }

        # When
        response = await client.post("/api/v1/auth/login", json=payload)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_invalid_credentials(self, client: AsyncClient):
        # Given
        payload = {
            "email": "wrong@test.com",
            "password": "wrongpassword",
        }

        # When
        response = await client.post("/api/v1/auth/login", json=payload)

        # Then
        assert response.status_code == 401
```

### Couverture cible : 85%

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=85
```

---

## Sécurité

### Checklist obligatoire

#### Injection SQL
```python
# ❌ JAMAIS de f-strings avec SQL
query = f"SELECT * FROM users WHERE email = '{email}'"

# ✅ Toujours des paramètres
stmt = select(User).where(User.email == email)
```

#### Command Injection
```python
# ❌ JAMAIS de shell avec input utilisateur
os.system(f"convert {user_filename}")

# ✅ Utiliser des bibliothèques, pas le shell
from PIL import Image
Image.open(validated_path).convert()
```

#### Path Traversal
```python
# ❌ Dangereux
file_path = f"/uploads/{user_input}"

# ✅ Valider et normaliser
from pathlib import Path
base = Path("/uploads")
requested = (base / user_input).resolve()
if not requested.is_relative_to(base):
    raise SecurityError("Invalid path")
```

#### Authentication
```python
# Toujours hasher les mots de passe
from bcrypt import hashpw, gensalt, checkpw

hashed = hashpw(password.encode(), gensalt())
is_valid = checkpw(password.encode(), hashed)
```

#### Authorization
```python
# Vérifier les permissions à chaque endpoint
from app.api.dependencies import require_role

@router.get("/admin/users")
async def list_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    ...
```

#### Secrets
```python
# ❌ JAMAIS de secrets dans le code
API_KEY = "sk-1234567890"

# ✅ Variables d'environnement
from app.config import settings
API_KEY = settings.api_key
```

### Gestion des secrets

#### Variables d'environnement (par défaut)

```bash
# .env (local) ou Railway/Docker (prod)
JWT_SECRET=your-secret-key
BOOND_PASSWORD=your-password
GEMINI_API_KEY=your-api-key
```

#### AWS Secrets Manager (optionnel)

Pour les environnements sensibles, Bobby supporte AWS Secrets Manager.

**Configuration** :
```bash
AWS_SECRETS_ENABLED=true
AWS_SECRETS_NAME=esn-cooptation/prod
AWS_SECRETS_REGION=eu-west-3
```

**Implémentation** : `backend/app/infrastructure/secrets/aws_secrets_manager.py`

```python
from app.infrastructure.secrets import load_secrets_from_aws

# Chargement au démarrage
secrets = load_secrets_from_aws(
    region_name="eu-west-3",
    secret_name="esn-cooptation/prod",
)

# Accès à un secret
jwt_secret = secrets.get("JWT_SECRET")
```

**Fonctionnalités** :
- Cache mémoire (évite les appels répétés)
- Fallback sur variables d'environnement si désactivé/erreur
- Support IAM roles (ECS, Lambda) ou credentials explicites

**Structure du secret AWS** (JSON) :
```json
{
  "JWT_SECRET": "...",
  "DATABASE_URL": "...",
  "BOOND_PASSWORD": "...",
  "GEMINI_API_KEY": "...",
  "TURNOVERIT_API_KEY": "..."
}
```

### Rate Limiting

```python
# Configuration slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

### Security Headers

```python
# Middleware
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if settings.env == "prod":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

### Row Level Security (PostgreSQL)

```sql
-- Politique RLS
ALTER TABLE cooptations ENABLE ROW LEVEL SECURITY;

CREATE POLICY cooptations_user_policy ON cooptations
    FOR SELECT
    USING (
        current_setting('app.user_role') = 'admin'
        OR submitter_id = current_setting('app.user_id')::uuid
    );
```

---

## Audit Logging

```python
from app.infrastructure.audit import audit_logger, AuditAction

# Logger les événements importants
audit_logger.log(
    action=AuditAction.USER_CREATED,
    resource_type="user",
    resource_id=str(user.id),
    user_id=str(current_user.id),
    ip_address=request.client.host,
    details={"email": user.email, "role": user.role},
)
```

### Événements à logger

| Action | Priorité |
|--------|----------|
| Login success/failure | ✅ Obligatoire |
| Password reset | ✅ Obligatoire |
| Role change | ✅ Obligatoire |
| User create/delete | ✅ Obligatoire |
| Permission denied | ✅ Obligatoire |
| Data export | ✅ Obligatoire |
| Settings change | ✅ Obligatoire |

---

## Observabilité

### Health checks

```python
@router.get("/health/live")
async def liveness():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
):
    checks = {
        "database": await check_db(db),
        "redis": await check_redis(redis),
        "boond": await check_boond(),
    }
    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

### Structured logging

```python
import structlog

logger = structlog.get_logger()

# Contexte automatique
logger = logger.bind(
    service="bobby",
    environment=settings.env,
)

# Logs structurés
logger.info(
    "request_completed",
    method=request.method,
    path=request.url.path,
    status_code=response.status_code,
    duration_ms=duration,
)
```
