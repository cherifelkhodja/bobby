# Architecture Hexagonale

Structure et principes de l'architecture hexagonale (Ports & Adapters) pour Bobby.

---

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                            │
│                    (FastAPI routes)                          │
├─────────────────────────────────────────────────────────────┤
│                     Application Layer                        │
│                      (Use Cases)                             │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│              (Entities, Value Objects, Ports)                │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│         (Repositories, External APIs, Database)              │
└─────────────────────────────────────────────────────────────┘
```

---

## Structure du projet

```
backend/app/
├── api/                          # Couche API (adapters primaires)
│   ├── routes/v1/                # Endpoints FastAPI
│   ├── schemas/                  # Pydantic request/response
│   ├── middleware/               # Rate limiting, security
│   └── dependencies.py           # Injection dépendances
│
├── application/                  # Couche Application
│   ├── use_cases/                # Logique métier orchestrée
│   │   ├── create_user.py
│   │   ├── submit_cooptation.py
│   │   └── transform_cv.py
│   └── read_models/              # DTOs pour les lectures
│
├── domain/                       # Couche Domain (cœur)
│   ├── entities/                 # Entités métier riches
│   │   ├── user.py
│   │   ├── candidate.py
│   │   └── opportunity.py
│   ├── value_objects/            # Enums, types valeur
│   │   └── status.py
│   └── ports/                    # Interfaces (abstractions)
│       ├── user_repository.py
│       └── email_service.py
│
└── infrastructure/               # Couche Infrastructure (adapters secondaires)
    ├── database/
    │   ├── models/               # SQLAlchemy models
    │   └── repositories/         # Implémentations des ports
    ├── boond/                    # Client API BoondManager
    ├── turnoverit/               # Client API Turnover-IT
    ├── email/                    # Service email
    ├── storage/                  # S3 client
    └── security/                 # JWT, hashing
```

---

## Règles d'import

### Direction des dépendances
Les dépendances pointent vers le centre (domain).

```
api → application → domain ← infrastructure
```

### Ce qui est autorisé

| Depuis | Peut importer |
|--------|---------------|
| `api/` | `application/`, `domain/`, `infrastructure/` |
| `application/` | `domain/` uniquement |
| `domain/` | Rien (ou stdlib uniquement) |
| `infrastructure/` | `domain/` uniquement |

### Ce qui est interdit

```python
# ❌ Domain ne doit JAMAIS importer infrastructure
# domain/entities/user.py
from app.infrastructure.database.models import UserModel  # INTERDIT

# ❌ Application ne doit pas importer infrastructure directement
# application/use_cases/create_user.py
from app.infrastructure.database.repositories import PostgresUserRepository  # INTERDIT
```

### Bonne pratique

```python
# ✅ Application dépend de l'abstraction (port)
# application/use_cases/create_user.py
from app.domain.ports.user_repository import UserRepository

class CreateUserUseCase:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
```

---

## Couche Domain

### Entités
Objets avec identité et comportement métier.

```python
# domain/entities/user.py
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from app.domain.value_objects.status import UserRole

@dataclass
class User:
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def can_publish_opportunity(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.COMMERCIAL)

    def can_manage_users(self) -> bool:
        return self.role == UserRole.ADMIN
```

### Value Objects
Objets immuables sans identité.

```python
# domain/value_objects/status.py
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    COMMERCIAL = "commercial"
    RH = "rh"
    ADMIN = "admin"

class CooptationStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    INTERVIEW = "interview"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
```

### Ports (Interfaces)
Contrats que l'infrastructure doit implémenter.

```python
# domain/ports/user_repository.py
from abc import ABC, abstractmethod
from uuid import UUID
from app.domain.entities.user import User

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def save(self, user: User) -> User:
        ...
```

---

## Couche Application

### Use Cases
Orchestrent la logique métier.

```python
# application/use_cases/create_user.py
from uuid import UUID
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepository
from app.domain.ports.email_service import EmailService

class CreateUserUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        email_service: EmailService,
    ):
        self.user_repo = user_repo
        self.email_service = email_service

    async def execute(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> User:
        # Vérifier si l'email existe
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise DuplicateEmailError(email)

        # Créer l'utilisateur
        user = User(
            id=uuid4(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.USER,
            is_active=False,
            created_at=datetime.utcnow(),
        )

        # Sauvegarder
        saved_user = await self.user_repo.save(user)

        # Envoyer email de bienvenue
        await self.email_service.send_welcome(saved_user)

        return saved_user
```

---

## Couche Infrastructure

### Repository (Adapter)
Implémente le port avec PostgreSQL.

```python
# infrastructure/database/repositories/user_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepository
from app.infrastructure.database.models.user import UserModel

class PostgresUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, user: User) -> User:
        model = self._to_model(user)
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            first_name=model.first_name,
            last_name=model.last_name,
            role=UserRole(model.role),
            is_active=model.is_active,
            created_at=model.created_at,
        )

    def _to_model(self, entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            email=entity.email,
            first_name=entity.first_name,
            last_name=entity.last_name,
            role=entity.role.value,
            is_active=entity.is_active,
            created_at=entity.created_at,
        )
```

---

## Couche API

### Routes
Point d'entrée HTTP, injecte les dépendances.

```python
# api/routes/v1/users.py
from fastapi import APIRouter, Depends
from app.api.dependencies import get_create_user_use_case
from app.api.schemas.users import CreateUserRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
):
    user = await use_case.execute(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
    )
    return UserResponse.from_entity(user)
```

### Injection de dépendances

```python
# api/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_session
from app.infrastructure.database.repositories import PostgresUserRepository
from app.infrastructure.email.resend_service import ResendEmailService
from app.application.use_cases.create_user import CreateUserUseCase

def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    return PostgresUserRepository(session)

def get_email_service() -> EmailService:
    return ResendEmailService()

def get_create_user_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
    email_service: EmailService = Depends(get_email_service),
) -> CreateUserUseCase:
    return CreateUserUseCase(user_repo, email_service)
```
