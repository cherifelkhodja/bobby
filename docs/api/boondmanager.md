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

## Contractualisation — Endpoints Boond

> **Client** : `backend/app/contract_management/infrastructure/adapters/boond_crm_adapter.py`

### Lecture de données

#### GET /positionings/{id}
Récupère un positionnement et les infos du consultant (nom) via `included` + `dependsOn`.

```python
async def get_positioning(self, positioning_id: int) -> dict[str, Any] | None
```

#### GET /opportunities/{id}/information
Récupère un besoin/opportunité avec l'email du commercial (mainManager).
Fallback : `GET /resources/{manager_id}` pour l'email, `GET /opportunities/{id}` pour l'agency_id.

```python
async def get_need(self, need_id: int) -> dict[str, Any] | None
```

**Retourne** : `{"title", "commercial_email", "manager_id", "agency_id"}`

#### GET /deliveries/{id}
Récupère une **prestation** : l'équivalent natif du bon de commande côté Boond.
Elle porte la période, le prix de vente, le coût, les jours vendus et les jours de gratuité.

```python
async def get_delivery(self, delivery_id: int) -> dict[str, Any] | None
```

**Correspondance avec le bon de commande Bobby** :

| Attribut Boond | Champ Bobby | Rôle |
|---|---|---|
| `averageDailyPriceExcludingTax` | `sale_daily_rate` | TJM de vente client (interne) |
| `averageDailyContractCost` / `averageDailyCost` | `purchase_daily_rate` | CJM d'achat fournisseur |
| `numberOfDaysInvoicedOrQuantity` | `days_sold` | Jours vendus |
| `numberOfDaysFree` | `free_days` | Jours de gratuité |
| `startDate` / `endDate` | `start_date` / `end_date` | Période |
| `relationships.contract` | `boond_contract_id` | Contrat déjà rattaché à la ressource |
| `relationships.dependsOn` | ressource | Consultant affecté |
| `relationships.project` | — | Projet (lui-même rattaché au besoin et au client) |

La prestation prime sur le positionnement au préremplissage : elle seule connaît la
gratuité, le prix de vente et le contrat en cours.

#### POST /deliveries/{id}/renew
Renouvellement natif d'une prestation. **Action REST sans corps de requête** : ni JSON,
ni paramètres d'URL. Boond duplique la prestation (mêmes projet, ressource et contrat)
et crée, selon la configuration du dossier, l'achat fournisseur et la commande client.

```python
async def renew_delivery(self, delivery_id: int) -> dict[str, Any] | None
```

La prestation créée **reprend la période de l'originale** : elle doit être recalée sur
les dates du nouveau bon de commande.

#### PUT /deliveries/{id}
Recale une prestation sur la période et les conditions d'un bon de commande.

```python
async def update_delivery(
    self, delivery_id: int, start_date=None, end_date=None,
    days_sold=None, free_days=None, purchase_daily_rate=None, sale_daily_rate=None,
) -> None
```

`forceAverageDailyPriceExcludingTax` est posé avec le prix de vente, sinon Boond le
recalcule depuis la grille du projet et écrase la valeur du bon de commande.

> **NEEDS-CONFIRMATION** : contrairement au renouvellement, la forme de cette mise à
> jour n'a pas été observée. L'échec du recalage n'invalide pas la synchronisation :
> il est signalé sur le bon de commande pour reprise manuelle.

#### GET /resources/{id}/information ou GET /candidates/{id}/information
Récupère les infos du consultant. Route vers `/resources/` ou `/candidates/` selon `consultant_type`.
Si inconnu, essaie `/resources/` d'abord puis fallback `/candidates/`.

```python
async def get_candidate_info(
    self, candidate_id: int, consultant_type: str | None = None,
) -> dict[str, Any] | None
```

**Retourne** : `{"first_name", "last_name", "email", "phone", "type"}`

#### GET /resources/{id}
Récupère le `typeOf` d'une ressource (0=salarié, 1=externe).

```python
async def get_resource_type_of(self, resource_id: int) -> int | None
```

### Société fournisseur

#### POST /companies
Crée une société fournisseur avec toutes les données légales.

```python
async def create_company_full(
    self, company_name: str, state: int,
    postcode: str | None, address: str | None, town: str | None,
    country: str, vat_number: str | None, siret: str | None,
    legal_status: str | None, registered_office: str | None,
    ape_code: str, agency_id: int | None,
) -> int  # Retourne company_id Boond
```

**Payload clé** :
```json
{
  "data": {
    "attributes": {
      "name": "...", "state": 9,
      "postcode": "...", "address": "...", "town": "...", "country": "France",
      "vatNumber": "...", "siretNumber": "...",
      "legalStatus": "SAS au capital de 752 000 €",
      "registeredOffice": "894 213 669 R.C.S. Paris",
      "apeCode": "6202A"
    },
    "relationships": {
      "agency": {"data": {"type": "agency", "id": "5"}}
    }
  }
}
```

> **Note** : `postcode` en minuscules (pas `postCode`).

#### GET /companies/{id}
Vérifie si une société existe encore dans Boond (avant de créer des contacts).

```python
async def verify_company_exists(self, company_id: int) -> bool
```

#### PUT /companies/{id}/information
Met à jour les données d'une société existante.

```python
async def update_company_information(
    self, company_id: int,
    postcode: str | None = None, address: str | None = None,
    town: str | None = None, country: str | None = None,
    legal_status: str | None = None, registered_office: str | None = None,
) -> None
```

### Contacts

#### POST /contacts
Crée un contact lié à une société.

```python
async def create_contact(
    self, company_id: int, civility: str | None,
    first_name: str | None, last_name: str | None,
    email: str | None, phone: str | None, job_title: str | None,
    types_of: list[int] | None = None,
    postcode: str | None = None, address: str | None = None,
    town: str | None = None, agency_id: int | None = None,
) -> int  # Retourne contact_id Boond
```

**Mapping civility** : `"M."` → 0 (homme), `"Mme"` → 1 (femme)

**Types de contact** (`typesOf`) — configurés dans BoondManager, Administration →
Types des contacts. Les valeurs ci-dessous sont celles du CRM du groupe :

| ID | Libellé | Utilisé par Bobby |
|----|---------|-------------------|
| 0 | Décideur | — |
| 1 | Prescripteur | — |
| 2 | Contact facturation | contact facturation du fournisseur |
| 3 | Acheteur | — |
| 4 | Contact - secondaire (archivé) | — |
| 5 | Inactif | — |
| 6 | Client - ADV (archivé) | — |
| 7 | Dirigeant | signataire déclaré dirigeant |
| 8 | Commercial | — |
| 9 | Contact ADV | contact ADV du fournisseur |
| 10 | Signataire | signataire du contrat |

Un contact cumulant plusieurs rôles porte plusieurs types : le dédoublonnage se
fait sur prénom + nom + email (`application/boond_contacts.py`), partagé par la
synchronisation automatique et par l'action manuelle de l'ADV.

### Conversion candidat → ressource

#### PUT /candidates/{id}/information
Convertit un candidat en ressource en passant `state: 3`.

```python
async def convert_candidate_to_resource(
    self, candidate_id: int, state: int = 3,
    state_reason_type_of: int | None = None,
    type_of: int | None = None,
    manager_id: int | None = None,
) -> int  # Retourne le NOUVEAU resource_id
```

**Payload** :
```json
{
  "data": {
    "id": "2565", "type": "candidate",
    "attributes": {
      "state": 3,
      "stateReason": {"typeOf": 0},
      "typeOf": 1
    },
    "relationships": {
      "dependsOn": {"data": {"type": "resource", "id": "1096"}}
    }
  }
}
```

> **IMPORTANT** : Après conversion, le **nouvel ID ressource** est dans
> `response.data.relationships.resource.data.id` (ex: 2674),
> et NON dans `response.data.id` (qui reste l'ID candidat, ex: 2565).

**Paramètres** :
- `state_reason_type_of` : 0 = salarié, 1 = externe
- `type_of` : 0 = salarié, 1 = externe (attribut distinct de `stateReason.typeOf`)
- `manager_id` : ID du responsable hiérarchique (relation `dependsOn`, **obligatoire**)

### Contrat

#### POST /contracts
Crée un contrat Boond pour un consultant externe.

```python
async def create_boond_contract(
    self, resource_id: int, positioning_id: int, daily_rate: float,
    type_of: int, start_date: str | None = None,
    end_date: str | None = None, agency_id: int | None = None,
) -> int  # Retourne contract_id Boond
```

**Payload** :
```json
{
  "data": {
    "attributes": {
      "typeOf": 2,
      "forceContractAverageDailyProductionCost": true,
      "contractAverageDailyProductionCost": 450.0,
      "numberOfHoursPerWeek": 35,
      "numberOfWorkingDays": 210,
      "classification": "-1",
      "currency": 0,
      "workingTimeType": 0,
      "startDate": "2026-04-01",
      "endDate": "2026-12-31"
    },
    "relationships": {
      "dependsOn": {"data": {"type": "resource", "id": "2674"}},
      "positioning": {"data": {"type": "positioning", "id": "1234"}},
      "agency": {"data": {"type": "agency", "id": "5"}}
    }
  }
}
```

**Types de contrat** (`typeOf`) :
| Valeur | Type |
|--------|------|
| 2 | Sous-traitant |
| 3 | Freelance |
| 6 | Portage salarial |
| 7 | Portage commercial |

### Lien ressource ↔ fournisseur

#### PUT /resources/{id}/administrative
Lie une ressource à sa société fournisseur et son contact.

```python
async def update_resource_administrative(
    self, resource_id: int, provider_company_id: int,
    provider_contact_id: int | None,
) -> None
```

**Payload** :
```json
{
  "data": {
    "id": "2674", "type": "resource",
    "relationships": {
      "providerCompany": {"data": {"type": "company", "id": "123"}},
      "providerContact": {"data": {"type": "contact", "id": "456"}}
    }
  }
}
```

### Bon de commande

#### GET /purchases/default puis POST /purchases
Crée l'**achat fournisseur** (« bon de commande » côté Bobby). Il se rattache à
une **prestation**, pas à un positionnement, et **seulement à la création** :
`PUT /purchases/{id}/information` n'expose que `mainManager`, `agency`, `pole`,
`company`, `contact` et `billingDetail`. Un achat posé sur la mauvaise
prestation se supprime (`DELETE /purchases/{id}`) et se recrée.

C'est le même objet que celui produit par le renouvellement natif d'une
prestation, qui le renvoie dans `relationships.purchase`. `/purchase-orders`,
longtemps écrit ici, n'existe pas dans l'API et répondait 404.

**En deux temps**, comme le fait l'interface :

1. `GET /purchases/default?delivery={id}` — Boond renvoie un achat vide déjà
   accordé au contexte de la prestation : `mainManager`, `agency`, `pole`,
   `company`, `contact`, `project`, `delivery`, plus un bloc `included`.
   Paramètres acceptés : `project`, `delivery`, `additionalTurnoverAndCosts`,
   `contact`, `company`.
2. `POST /purchases` — on renvoie ce corps, ajusté. Seul `title` est
   obligatoire dans `attributes`.

Composer le corps à la main plutôt que de partir de ce pré-remplissage est la
cause classique des 422 : prestation, projet, société et agence doivent
s'accorder.

```json
{
  "data": {
    "type": "purchase",
    "attributes": {
      "title": "GEM-BC-001 - Développeur Python",
      "reference": "GEM-BC-001",
      "date": "2026-09-01",
      "startDate": "2026-09-01",
      "endDate": "2027-02-28",
      "quantity": 18,
      "amountExcludingTax": 9000
    },
    "relationships": {
      "delivery": {"data": {"id": "1234", "type": "delivery"}},
      "project": {"data": {"id": "567", "type": "project"}},
      "company":  {"data": {"id": "777", "type": "company"}},
      "contact":  {"data": {"id": "2864", "type": "contact"}},
      "agency":   {"data": {"id": "1", "type": "agency"}}
    }
  }
}
```

> **Coquille de la doc** : le schéma de `POST /purchases` décrit la relation
> `delivery` avec `type: "project"` (copier-coller du bloc voisin). Le type
> attendu est bien `delivery`, comme le confirment les schémas de réponse de
> `/purchases/default` et de `POST /purchases`.

> **La société est le fournisseur**, pas le client : le pré-remplissage vient de
> la prestation et désigne le client, à remplacer — son contact part avec elle.
> Bobby y met le contact de facturation du fournisseur.

Autres attributs disponibles : `number` (réf. fournisseur), `typeOf`, `state`,
`subscription`, `paymentTerm`, `paymentMethod`, `taxRates`, `toReinvoice`,
`reinvoiceRate`, `reinvoiceAmountExcludingTax`, `informationComments`,
`createPayments`, `exchangeRate`, `currency`.

Pour un achat rattaché à un frais ou un CA additionnel plutôt qu'à une
prestation : même flux avec `?additionalTurnoverAndCosts={id}`.

> Ne pas confondre : `/purchases` (finance) est l'**achat fournisseur**,
> `/orders` (staffing) la **commande client**. Le catalogue de l'API ne connaît
> aucun `/purchase-orders`.

#### PUT /positionings/{id} — faire naître la prestation

L'API ne crée pas de prestation. C'est le passage du positionnement à l'état
**1 (« Gagné »)** qui la fait produire par BoondManager, à partir du
positionnement. Le report d'un bon de commande sans prestation passe donc par
là, puis relit le positionnement pour récupérer l'identifiant de la prestation
créée.

> **L'adresse d'écriture suit celle de lecture.** Un positionnement n'a pas
> d'onglet `/information` — `PUT /positionings/{id}/information` répond **404**.
> Il s'écrit à son adresse propre, comme les prestations (`PUT /deliveries/{id}`).
> Les entités qui ont cet onglet sont celles qu'on lit ainsi : candidats,
> sociétés, besoins (`/candidates/{id}/information`, `/companies/{id}/information`,
> `/opportunities/{id}/information`), plus l'onglet `administrative` des ressources.

> Seul l'état est envoyé : les données du positionnement — dates, tarif de
> vente, jours — restent celles du commercial. Une réponse en 200 ne prouvant
> pas que le changement a été pris, l'état renvoyé par Boond est comparé à
> celui demandé, puis relu.

```python
async def update_positioning_state(self, positioning_id: int, state: int) -> None
```

```python
async def create_supplier_purchase(
    self, delivery_id: int, title: str,
    provider_id: int | None = None, provider_contact_id: int | None = None,
    reference: str | None = None,
    start_date: str | None = None, end_date: str | None = None,
    quantity: float | None = None, amount: float | None = None,
) -> int  # Retourne l'ID de l'achat Boond
```

---

## Workflow complet Sync Boond (après signature contrat)

> **Use case** : `backend/app/contract_management/application/use_cases/sync_to_boond_after_signing.py`

**6 étapes (best-effort, continue même si une étape échoue)** :

| Étape | Action | Endpoint Boond | Données persistées |
|-------|--------|----------------|-------------------|
| 1 | Créer société fournisseur | `POST /companies` | `tp.boond_provider_id` |
| 2 | Créer contacts (signataire, ADV, facturation) | `POST /contacts` | `tp.boond_signatory_contact_id`, `tp.boond_adv_contact_id`, `tp.boond_billing_contact_id` |
| 3 | Convertir candidat → ressource | `PUT /candidates/{id}/information` | `cr.boond_candidate_id` (nouvel ID), `cr.boond_consultant_type = "resource"` |
| 4 | Créer contrat Boond | `POST /contracts` | `cr.boond_contract_id` |
| 5 | Créer l'achat fournisseur | `POST /purchases` | `contract.boond_purchase_order_id` |
| 6 | Archiver positionnement | `PATCH /positionings/{id}` | — |

> **Pré-requis étape 3** : `manager_id` récupéré via `get_need()` (mainManager du besoin).
> **Pré-requis étape 4** : `resource_id` doit être le nouvel ID ressource (pas l'ancien ID candidat).

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
| `POST /contract-requests/{id}/boond/create-company` | `create_company_full()`, `create_contact()` |
| `POST /contract-requests/{id}/boond/convert-candidate` | `convert_candidate_to_resource()` |
| `POST /contract-requests/{id}/boond/create-contract` | `create_boond_contract()`, `update_resource_administrative()` |
| `POST /contract-requests/{id}/boond/create-purchase-order` | `create_purchase_order()` |
| `POST /contract-requests/{id}/push-to-crm` | Toutes les méthodes (sync complète 6 étapes) |

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
