# BoondManager API

Documentation de l'intégration BoondManager pour Bobby.

---

## Vue d'ensemble

BoondManager est l'ERP utilisé par Gemini Consulting pour gérer :
- Les ressources (employés)
- Les opportunités commerciales
- Les candidats
- Les positionnements (cooptations)

---

## Configuration

### Variables d'environnement

```bash
BOOND_API_URL=https://ui.boondmanager.com/api
BOOND_USERNAME=your-username
BOOND_PASSWORD=your-password
```

### Authentification

L'API utilise **Basic Auth** :

```python
import httpx
from base64 import b64encode

credentials = b64encode(f"{username}:{password}".encode()).decode()
headers = {"Authorization": f"Basic {credentials}"}
```

---

## Client Bobby

**Fichier** : `backend/app/infrastructure/boond/client.py`

### Configuration

```python
class BoondClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 5.0,
    ):
        self.base_url = base_url
        self._auth = (username, password)
        self.timeout = timeout
```

### Retry Logic

Le client utilise `tenacity` pour les retries :

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
)
async def _request(self, method: str, endpoint: str, **kwargs):
    ...
```

---

## Endpoints utilisés

### Opportunités

#### GET /opportunities
Liste toutes les opportunités.

```python
async def get_opportunities(self) -> list[Opportunity]:
    response = await self._get("/opportunities")
    return [self._parse_opportunity(item) for item in response["data"]]
```

#### GET /opportunities/{id}
Récupère une opportunité spécifique.

```python
async def get_opportunity(self, external_id: str) -> Opportunity:
    response = await self._get(f"/opportunities/{external_id}")
    return self._parse_opportunity(response["data"])
```

### Ressources (Employés)

#### GET /resources
Liste les employés avec pagination (max 500).

**Paramètres de filtrage** :
- `state` : Filtre par état (0, 1, 2, 3, 7)
- `agencyId` : Filtre par agence
- `typeOf` : Filtre par type de ressource

```python
async def get_resources(
    self,
    state: int | None = None,
    agency_id: int | None = None,
) -> list[Resource]:
    params = {"maxResults": 500}
    if state is not None:
        params["state"] = state
    if agency_id is not None:
        params["agencyId"] = agency_id

    response = await self._get("/resources", params=params)
    return [self._parse_resource(item) for item in response["data"]]
```

### Candidats

#### POST /candidates
Crée un nouveau candidat.

```python
async def create_candidate(self, candidate: CandidateCreate) -> str:
    payload = {
        "data": {
            "attributes": {
                "firstName": candidate.first_name,
                "lastName": candidate.last_name,
                "email1": candidate.email,
                "civility": candidate.civility,
                "phone1": candidate.phone,
            }
        }
    }
    response = await self._post("/candidates", json=payload)
    return response["data"]["id"]
```

### Positionnements (Cooptations)

#### POST /positionings
Crée un positionnement (lien candidat-opportunité).

```python
async def create_positioning(
    self,
    candidate_id: str,
    opportunity_id: str,
) -> str:
    payload = {
        "data": {
            "relationships": {
                "candidate": {"data": {"id": candidate_id}},
                "opportunity": {"data": {"id": opportunity_id}},
            }
        }
    }
    response = await self._post("/positionings", json=payload)
    return response["data"]["id"]
```

### Opportunités par Manager

#### GET /opportunities (filtered)
Récupère les opportunités d'un commercial (main manager).

```python
async def get_manager_opportunities(
    self,
    manager_id: str,
) -> list[Opportunity]:
    params = {
        "perimeterManagersType": "main",
        "perimeterManagersId": manager_id,
    }
    response = await self._get("/opportunities", params=params)
    return [self._parse_opportunity(item) for item in response["data"]]
```

#### GET /opportunities (HR filtered)
Récupère les opportunités pour un RH (HR manager).

```python
async def get_hr_manager_opportunities(
    self,
    manager_id: str,
) -> list[Opportunity]:
    params = {
        "perimeterManagersType": "hr",
        "perimeterManagersId": manager_id,
    }
    response = await self._get("/opportunities", params=params)
    return [self._parse_opportunity(item) for item in response["data"]]
```

### Health Check

#### GET /candidates
Simple ping pour vérifier la connectivité.

```python
async def health_check(self) -> bool:
    try:
        await self._get("/candidates", params={"maxResults": 1})
        return True
    except Exception:
        return False
```

---

## Mapping des données

### États des ressources

```python
RESOURCE_STATE_NAMES = {
    0: "Sortie",
    1: "En cours",
    2: "Intercontrat",
    3: "Arrivée prochaine",
    7: "Sortie prochaine",
}
```

### Types de ressources → Rôles Bobby

```python
RESOURCE_TYPE_TO_ROLE = {
    0: "user",      # Consultant
    1: "user",      # Consultant
    2: "commercial",# Commercial
    5: "rh",        # RH
    6: "rh",        # Direction RH
    10: "user",     # Consultant
}

RESOURCE_TYPE_NAMES = {
    0: "Consultant",
    1: "Consultant",
    2: "Commercial",
    5: "RH",
    6: "Direction RH",
    10: "Consultant",
}
```

### Agences

```python
AGENCY_NAMES = {
    1: "Gemini",
    5: "Craftmania",
}
```

### États des opportunités

```python
OPPORTUNITY_STATE_NAMES = {
    0: "Piste identifiée",
    5: "En cours",
    6: "Récurrent",
    7: "AO ouvert",
    10: "Besoin en avant de phase",
}

# États actifs pour le recrutement RH
ACTIVE_OPPORTUNITY_STATES = [0, 5, 6, 7, 10]
```

---

## Gestion des erreurs

### Exceptions

```python
class BoondAPIError(Exception):
    """Erreur générique API Boond."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

class BoondNotFoundError(BoondAPIError):
    """Ressource non trouvée (404)."""
    pass

class BoondAuthError(BoondAPIError):
    """Erreur d'authentification (401)."""
    pass
```

### Handling

```python
async def _request(self, method: str, endpoint: str, **kwargs):
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.request(
            method,
            f"{self.base_url}{endpoint}",
            auth=self._auth,
            **kwargs,
        )

        if response.status_code == 401:
            raise BoondAuthError(401, "Invalid credentials")
        if response.status_code == 404:
            raise BoondNotFoundError(404, f"Resource not found: {endpoint}")
        if response.status_code >= 400:
            raise BoondAPIError(response.status_code, response.text)

        return response.json()
```

---

## Utilisation dans Bobby

### Endpoints API Bobby

| Endpoint Bobby | Méthode Boond |
|----------------|---------------|
| `GET /admin/boond/status` | `health_check()` |
| `GET /admin/boond/resources` | `get_resources()` |
| `POST /cooptations` | `create_candidate()`, `create_positioning()` |
| `GET /opportunities/sync` | `get_opportunities()` |
| `GET /published-opportunities/my-boond` | `get_manager_opportunities()` |
| `GET /hr/opportunities` | `get_hr_manager_opportunities()` |

### Exemple d'utilisation

```python
from app.infrastructure.boond.client import BoondClient
from app.config import settings

# Initialisation
boond = BoondClient(
    base_url=settings.boond_api_url,
    username=settings.boond_username,
    password=settings.boond_password,
)

# Récupérer les ressources "En cours"
resources = await boond.get_resources(state=1)

# Créer une cooptation
candidate_id = await boond.create_candidate(candidate_data)
positioning_id = await boond.create_positioning(candidate_id, opportunity_id)
```

---

## Limites connues

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Rate limiting non documenté | Risque de 429 | Retry avec backoff |
| Pagination max 500 | Besoin de boucle | Prévoir pagination manuelle |
| Timeout 5s | Lenteur possible | Retry automatique |

---

## Références

- API Documentation (interne BoondManager)
- Base URL : `https://ui.boondmanager.com/api`
