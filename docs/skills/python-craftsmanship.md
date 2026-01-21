# Python Craftsmanship

Standards de développement Python pour les projets Gemini Consulting.

---

## Principes SOLID

### Single Responsibility (SRP)
Chaque classe/fonction a une seule raison de changer.

```python
# ❌ Mauvais : fait trop de choses
class UserService:
    def create_user(self, data): ...
    def send_email(self, user): ...
    def generate_report(self): ...

# ✅ Bon : responsabilités séparées
class UserService:
    def create_user(self, data): ...

class EmailService:
    def send_welcome_email(self, user): ...

class ReportGenerator:
    def generate_user_report(self): ...
```

### Open/Closed (OCP)
Ouvert à l'extension, fermé à la modification.

```python
# ✅ Utiliser des abstractions
from abc import ABC, abstractmethod

class NotificationSender(ABC):
    @abstractmethod
    async def send(self, message: str, recipient: str) -> bool: ...

class EmailSender(NotificationSender):
    async def send(self, message: str, recipient: str) -> bool:
        # Implémentation email
        ...

class SmsSender(NotificationSender):
    async def send(self, message: str, recipient: str) -> bool:
        # Implémentation SMS
        ...
```

### Liskov Substitution (LSP)
Les sous-types doivent être substituables à leurs types de base.

### Interface Segregation (ISP)
Plusieurs interfaces spécifiques plutôt qu'une interface générale.

```python
# ❌ Interface trop large
class Repository(ABC):
    @abstractmethod
    def get(self, id): ...
    @abstractmethod
    def create(self, entity): ...
    @abstractmethod
    def update(self, entity): ...
    @abstractmethod
    def delete(self, id): ...
    @abstractmethod
    def search(self, query): ...

# ✅ Interfaces séparées
class Reader(ABC):
    @abstractmethod
    def get(self, id): ...

class Writer(ABC):
    @abstractmethod
    def create(self, entity): ...
    @abstractmethod
    def update(self, entity): ...

class Deleter(ABC):
    @abstractmethod
    def delete(self, id): ...
```

### Dependency Inversion (DIP)
Dépendre des abstractions, pas des implémentations.

```python
# ❌ Dépendance concrète
class UserService:
    def __init__(self):
        self.repo = PostgresUserRepository()

# ✅ Injection de dépendance
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
```

---

## Clean Code

### Nommage
```python
# Variables : snake_case, descriptif
user_count = 10
is_active = True
created_at = datetime.now()

# Fonctions : verbe + objet
def get_user_by_id(user_id: UUID) -> User: ...
def calculate_total_amount(items: list[Item]) -> Decimal: ...
def send_notification(user: User, message: str) -> bool: ...

# Classes : PascalCase, nom
class UserRepository: ...
class EmailNotificationService: ...

# Constantes : SCREAMING_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_PAGE_SIZE = 50
```

### Fonctions courtes
```python
# ❌ Fonction trop longue
def process_order(order):
    # 100 lignes de code...

# ✅ Fonctions décomposées
def process_order(order: Order) -> ProcessedOrder:
    validated = validate_order(order)
    enriched = enrich_with_pricing(validated)
    return finalize_order(enriched)
```

### Pas de magic numbers
```python
# ❌ Mauvais
if retry_count > 3:
    ...

# ✅ Bon
MAX_RETRIES = 3
if retry_count > MAX_RETRIES:
    ...
```

---

## Typage strict

### Type hints obligatoires
```python
from typing import Optional
from uuid import UUID
from datetime import datetime

def get_user(
    user_id: UUID,
    include_deleted: bool = False,
) -> Optional[User]:
    ...

async def create_user(
    email: str,
    password: str,
    role: UserRole = UserRole.USER,
) -> User:
    ...
```

### Pydantic pour validation
```python
from pydantic import BaseModel, EmailStr, Field

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True)
```

### Éviter Any
```python
# ❌ Éviter
def process(data: Any) -> Any: ...

# ✅ Préférer
def process(data: dict[str, str]) -> ProcessedData: ...
```

---

## Async/Await

### Toujours async pour I/O
```python
# ❌ Bloquant
def get_user(user_id: UUID) -> User:
    return db.query(User).filter_by(id=user_id).first()

# ✅ Async
async def get_user(user_id: UUID) -> User | None:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```

### Context managers async
```python
async with httpx.AsyncClient() as client:
    response = await client.get(url)

async with session.begin():
    session.add(entity)
```

### Gather pour parallélisme
```python
# Exécution parallèle
results = await asyncio.gather(
    fetch_user(user_id),
    fetch_permissions(user_id),
    fetch_preferences(user_id),
)
```

---

## Gestion d'erreurs

### Exceptions custom
```python
class DomainError(Exception):
    """Base pour erreurs métier."""
    pass

class UserNotFoundError(DomainError):
    def __init__(self, user_id: UUID):
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")

class InvalidCredentialsError(DomainError):
    pass
```

### Pas d'exceptions silencieuses
```python
# ❌ Mauvais
try:
    result = risky_operation()
except Exception:
    pass

# ✅ Bon
try:
    result = risky_operation()
except SpecificError as e:
    logger.error("Operation failed", error=str(e))
    raise
```

---

## Docstrings (Google format)

```python
async def create_candidate(
    self,
    email: str,
    first_name: str,
    last_name: str,
    cv_path: str | None = None,
) -> Candidate:
    """Crée un nouveau candidat.

    Args:
        email: Adresse email du candidat.
        first_name: Prénom.
        last_name: Nom de famille.
        cv_path: Chemin vers le CV (optionnel).

    Returns:
        Le candidat créé avec son ID généré.

    Raises:
        DuplicateEmailError: Si l'email existe déjà.
        ValidationError: Si les données sont invalides.
    """
    ...
```

---

## Logging structuré

```python
import structlog

logger = structlog.get_logger()

# ✅ Structured logging
logger.info(
    "user_created",
    user_id=str(user.id),
    email=user.email,
    role=user.role,
)

logger.error(
    "api_call_failed",
    service="boondmanager",
    endpoint="/resources",
    status_code=500,
    error=str(e),
)
```
