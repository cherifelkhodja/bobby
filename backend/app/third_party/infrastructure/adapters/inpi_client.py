"""INPI RNE API client for company information lookup.

Uses username/password → Bearer token flow (token cached until expiry).
Fetches forme juridique, capital social, and ville du greffe for a given SIREN.

Response structure (verified on real payload):
  data["formality"]["content"]["personneMorale"]["identite"]["entreprise"]["denomination"]
  data["formality"]["content"]["personneMorale"]["identite"]["entreprise"]["formeJuridique"]  # code
  data["formality"]["content"]["personneMorale"]["identite"]["description"]["montantCapital"]
  data["formality"]["content"]["personneMorale"]["identite"]["description"]["deviseCapital"]
  data["formality"]["content"]["personneMorale"]["adresseEntreprise"]["adresse"]["codePostal"]
  data["formality"]["content"]["personneMorale"]["adresseEntreprise"]["adresse"]["commune"]
  → Greffe is derived from postal code (no direct field for the company itself)
"""

import time
from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger()

INPI_BASE_URL = "https://registre-national-entreprises.inpi.fr/api"
INPI_LOGIN_URL = f"{INPI_BASE_URL}/sso/login"
INPI_TOKEN_TTL_SECONDS = 3600  # Refresh every hour


# =============================================================================
# INSEE nomenclature — Catégories juridiques (formeJuridique codes → labels)
# Source: https://www.insee.fr/fr/information/2028129
# =============================================================================
FORME_JURIDIQUE_LABELS: dict[str, str] = {
    # Personnes physiques
    "1000": "Entrepreneur individuel",
    "1100": "Agriculteur exploitant",
    "1200": "Artisan",
    "1300": "Commerçant",
    "1400": "Autre personne physique",
    # Indivisions
    "2110": "Indivision entre personnes physiques",
    "2120": "Indivision avec personne morale",
    # Groupements européens
    "3110": "GEIE",
    "3120": "GIE",
    # Sociétés civiles
    "4110": "Société créée de fait entre personnes physiques",
    "4120": "Société créée de fait avec personne morale",
    "4130": "Société en participation entre personnes physiques",
    "4140": "Société en participation avec personne morale",
    "4150": "Société en participation de personnes physiques",
    "4160": "Société en participation de personnes morales",
    "5100": "SNC",
    "5105": "SNC",
    "5108": "SNC avec conseil d'administration",
    "5202": "SARL (avant 1985)",
    "5203": "SARL",
    "5306": "EURL (gérant non associé)",
    "5307": "EURL (gérant associé)",
    "5308": "EARL",
    "5309": "EURL",
    "5310": "EURL",
    "5385": "SARL",
    "5389": "SARL",
    "5395": "SARL coopérative",
    "5399": "SARL",
    # Sociétés anonymes et assimilées
    "5410": "SA coopérative",
    "5415": "SA à directoire",
    "5416": "SA à conseil d'administration",
    "5417": "SA",
    "5418": "SA à organe collégial",
    "5419": "SA",
    "5420": "Société anonyme à responsabilité limitée",
    "5422": "SA coopérative à directoire",
    "5423": "SA coopérative à conseil d'administration",
    "5498": "SA",
    "5499": "SA",
    # Société européenne
    "5500": "SE (Societas Europaea)",
    "5505": "SE à directoire",
    "5510": "SE à conseil d'administration",
    # SAS / SASU
    "5515": "SASU",
    "5522": "SCA",
    # Autres formes
    "5531": "SCPI",
    "5532": "SICOMI",
    "5533": "Groupement d'investissement immobilier",
    "5542": "Société à intérêt collectif agricole (SICA)",
    "5543": "GAEC",
    "5546": "Société anonyme mixte d'investissement local (SEMIL)",
    "5547": "Société coopérative agricole",
    "5548": "Société de caution mutuelle",
    "5551": "Société coopérative de production (SCOP) SA",
    "5552": "Société anonyme de HLM",
    "5553": "Société anonyme coopérative de construction",
    "5554": "SA d'attribution d'immeubles en jouissance à temps partagé",
    "5555": "Société anonyme coopérative d'intérêt collectif",
    "5560": "Caisse d'épargne et de prévoyance",
    "5570": "Société par actions simplifiée",
    "5585": "Société d'exercice libéral par actions simplifiée (SELAS)",
    "5599": "SA (autre)",
    "5600": "Autre SA",
    # SAS / SASU (codes récents RNE)
    "5710": "SAS",
    "5720": "SASU",
    "5785": "SCA",
    # Sociétés coopératives
    "6100": "Caisse d'épargne et de prévoyance",
    "6210": "SARL coopérative",
    "6220": "SA coopérative",
    "6316": "Coopérative",
    # Organismes
    "7111": "Organisme de placement collectif en valeurs mobilières (OPCVM)",
    "7118": "Fonds commun de placement",
    "7120": "Organisme d'investissement alternatif (OIA)",
    "7130": "Fonds de pension",
    "7310": "Organisme gérant des régimes de protection sociale",
    "7320": "Organisme mutualiste",
    "7329": "Mutuelle",
    "7340": "Organisme professionnel",
    "7360": "Syndicat de propriétaires",
    "7370": "Association syndicale libre",
    "7371": "Association syndicale libre",
    "7372": "Association foncière",
    "7373": "Association foncière",
    "7378": "Groupement de propriétaires",
    "7379": "Association foncière",
    "7381": "Comité d'établissement",
    "7382": "Comité central d'entreprise",
    "7383": "Comité de groupe",
    "7384": "Comité interentreprises ou sectoriel d'activité",
    "7385": "Comité social et économique",
    "7389": "Autre organisme professionnel",
    "7410": "Syndicat",
    "7490": "Autre syndicat",
    # Associations
    "9110": "Fondation",
    "9150": "Association de droit local Alsace-Moselle",
    "9210": "Association loi 1901",
    "9220": "Association intermédiaire",
    "9221": "Association déclarée de bienfaisance ou de charité",
    "9222": "Association reconnue d'utilité publique",
    "9223": "Association d'insertion par l'activité économique",
    "9224": "Association agréée",
    "9229": "Association loi 1901 (autre)",
    "9230": "Association loi 1905 (culte)",
    "9240": "Association des Alsaciens-Mosellans",
    "9260": "Association sportive",
    "9300": "Autre personne morale de droit privé",
}


# =============================================================================
# Mapping département → ville principale du greffe (Tribunal de Commerce)
# Source: liste des greffes des tribunaux de commerce de France
# Pour les départements sans TC propre (agriculture), tribunal judiciaire compétent
# =============================================================================
DEPT_TO_GREFFE: dict[str, str] = {
    "01": "Bourg-en-Bresse",
    "02": "Soissons",
    "03": "Cusset",
    "04": "Digne-les-Bains",
    "05": "Gap",
    "06": "Nice",
    "07": "Privas",
    "08": "Charleville-Mézières",
    "09": "Foix",
    "10": "Troyes",
    "11": "Carcassonne",
    "12": "Rodez",
    "13": "Marseille",
    "14": "Caen",
    "15": "Aurillac",
    "16": "Angoulême",
    "17": "La Rochelle",
    "18": "Bourges",
    "19": "Brive-la-Gaillarde",
    "21": "Dijon",
    "22": "Saint-Brieuc",
    "23": "Guéret",
    "24": "Périgueux",
    "25": "Besançon",
    "26": "Romans-sur-Isère",
    "27": "Évreux",
    "28": "Chartres",
    "29": "Brest",
    "30": "Nîmes",
    "31": "Toulouse",
    "32": "Auch",
    "33": "Bordeaux",
    "34": "Montpellier",
    "35": "Rennes",
    "36": "Châteauroux",
    "37": "Tours",
    "38": "Grenoble",
    "39": "Lons-le-Saunier",
    "40": "Mont-de-Marsan",
    "41": "Blois",
    "42": "Saint-Étienne",
    "43": "Le Puy-en-Velay",
    "44": "Nantes",
    "45": "Orléans",
    "46": "Cahors",
    "47": "Agen",
    "48": "Mende",
    "49": "Angers",
    "50": "Cherbourg-en-Cotentin",
    "51": "Reims",
    "52": "Chaumont",
    "53": "Laval",
    "54": "Nancy",
    "55": "Bar-le-Duc",
    "56": "Vannes",
    "57": "Metz",
    "58": "Nevers",
    "59": "Lille",
    "60": "Beauvais",
    "61": "Alençon",
    "62": "Arras",
    "63": "Clermont-Ferrand",
    "64": "Pau",
    "65": "Tarbes",
    "66": "Perpignan",
    "67": "Strasbourg",
    "68": "Colmar",
    "69": "Lyon",
    "70": "Vesoul",
    "71": "Mâcon",
    "72": "Le Mans",
    "73": "Chambéry",
    "74": "Annecy",
    "75": "Paris",
    "76": "Rouen",
    "77": "Meaux",
    "78": "Versailles",
    "79": "Niort",
    "80": "Amiens",
    "81": "Albi",
    "82": "Montauban",
    "83": "Toulon",
    "84": "Avignon",
    "85": "La Roche-sur-Yon",
    "86": "Poitiers",
    "87": "Limoges",
    "88": "Épinal",
    "89": "Auxerre",
    "90": "Belfort",
    "91": "Évry-Courcouronnes",
    "92": "Nanterre",
    "93": "Bobigny",
    "94": "Créteil",
    "95": "Pontoise",
    # DOM-TOM
    "971": "Pointe-à-Pitre",
    "972": "Fort-de-France",
    "973": "Cayenne",
    "974": "Saint-Denis",
    "976": "Mamoudzou",
}


def derive_greffe_city(postal_code: str, commune: str | None = None) -> str | None:
    """Derive the greffe (Tribunal de Commerce) city from a French postal code.

    Uses the department code extracted from the postal code to map to the
    principal tribunal de commerce for that department.

    Args:
        postal_code: French postal code (5 digits).
        commune: Commune name (unused currently, reserved for future refinement).

    Returns:
        City name of the tribunal de commerce, or None if not determinable.
    """
    if not postal_code or len(postal_code) < 2:
        return None

    # DOM-TOM: 97x codes use 3 digits for department
    if postal_code.startswith("97") and len(postal_code) >= 3:
        dept = postal_code[:3]
        if dept in DEPT_TO_GREFFE:
            return DEPT_TO_GREFFE[dept]

    dept = postal_code[:2]
    return DEPT_TO_GREFFE.get(dept)


def forme_juridique_label(code: str | None) -> str | None:
    """Return the human-readable label for an INSEE forme juridique code.

    Falls back to the raw code if no label is found.
    """
    if not code:
        return None
    return FORME_JURIDIQUE_LABELS.get(code, code)


# =============================================================================
# Client
# =============================================================================


@dataclass
class InpiCompanyInfo:
    """Company information fetched from INPI RNE."""

    siren: str
    company_name: str
    legal_form_code: str | None       # INSEE code e.g. "5710"
    legal_form_label: str | None      # Human-readable e.g. "SAS"
    capital_amount: float | None
    capital_currency: str | None
    capital_variable: bool
    greffe_city: str | None           # Derived from postal code


class InpiClient:
    """Client for the INPI Registre National des Entreprises (RNE) API.

    Authentication: POST /api/sso/login with username/password → Bearer token.
    Token is cached and refreshed before expiry.
    """

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def _get_access_token(self) -> str | None:
        """Obtain or return cached Bearer token."""
        if self._access_token and time.monotonic() < self._token_expires_at - 60:
            return self._access_token

        if not self._username or not self._password:
            logger.warning("inpi_credentials_not_configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    INPI_LOGIN_URL,
                    json={"username": self._username, "password": self._password},
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

            token = data.get("token")
            if not token:
                logger.error("inpi_login_no_token", response=str(data)[:200])
                return None

            self._access_token = token
            self._token_expires_at = time.monotonic() + INPI_TOKEN_TTL_SECONDS
            logger.info("inpi_token_obtained")
            return self._access_token

        except httpx.HTTPStatusError as exc:
            logger.error(
                "inpi_login_failed",
                status_code=exc.response.status_code,
                body=exc.response.text[:200],
            )
            return None
        except httpx.RequestError as exc:
            logger.error("inpi_login_request_error", error=str(exc))
            return None

    async def get_company(self, siren: str) -> InpiCompanyInfo | None:
        """Fetch company info from INPI RNE by SIREN.

        Returns InpiCompanyInfo with legal form, capital, and greffe city,
        or None if not found or on error.
        """
        token = await self._get_access_token()
        if not token:
            return None

        url = f"{INPI_BASE_URL}/companies/{siren}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 404:
                logger.info("inpi_company_not_found", siren=siren)
                return None

            if response.status_code == 401:
                # Token rejected — clear and retry once
                self._access_token = None
                self._token_expires_at = 0
                token = await self._get_access_token()
                if not token:
                    return None
                headers["Authorization"] = f"Bearer {token}"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    logger.error("inpi_auth_failed_after_retry", siren=siren)
                    return None

            response.raise_for_status()
            return self._parse_company(siren, response.json())

        except httpx.HTTPStatusError as exc:
            logger.error("inpi_api_error", siren=siren, status_code=exc.response.status_code)
            return None
        except httpx.RequestError as exc:
            logger.error("inpi_api_request_error", siren=siren, error=str(exc))
            return None

    def _parse_company(self, siren: str, data: dict) -> InpiCompanyInfo:
        """Extract relevant fields from INPI RNE JSON response.

        Field paths verified on real payload (GEMINI / 842799959):
          formality.content.personneMorale.identite.entreprise.denomination
          formality.content.personneMorale.identite.entreprise.formeJuridique  (code)
          formality.content.personneMorale.identite.description.montantCapital
          formality.content.personneMorale.identite.description.deviseCapital
          formality.content.personneMorale.identite.description.capitalVariable
          formality.content.personneMorale.adresseEntreprise.adresse.codePostal
          formality.content.personneMorale.adresseEntreprise.adresse.commune
          → greffe derived via derive_greffe_city(codePostal)
        """
        formality = data.get("formality", data)
        content = formality.get("content", {})

        # Support personneMorale (société) and personnePhysique (entrepreneur)
        pm = content.get("personneMorale", {})
        pp = content.get("personnePhysique", {})
        entity = pm or pp

        identite = entity.get("identite", {})
        entreprise_info = identite.get("entreprise", {})
        description = identite.get("description", {})

        # Company name
        company_name = (
            entreprise_info.get("denomination")
            or identite.get("denomination")
            or formality.get("siren", siren)
        )

        # Forme juridique — code only in response, label from local nomenclature
        forme_code = (
            entreprise_info.get("formeJuridique")
            or formality.get("formeJuridique")
            or content.get("natureCreation", {}).get("formeJuridique")
        )
        forme_code = str(forme_code) if forme_code else None
        forme_label = forme_juridique_label(forme_code)

        # Capital social
        capital_amount = description.get("montantCapital")
        capital_currency = description.get("deviseCapital", "EUR")
        capital_variable = bool(description.get("capitalVariable", False))

        # Greffe — derived from company address postal code
        adresse = entity.get("adresseEntreprise", {}).get("adresse", {})
        postal_code = adresse.get("codePostal", "")
        commune = adresse.get("commune")
        greffe_city = derive_greffe_city(postal_code, commune)

        logger.info(
            "inpi_company_parsed",
            siren=siren,
            company_name=company_name,
            legal_form_code=forme_code,
            capital_amount=capital_amount,
            greffe_city=greffe_city,
        )

        return InpiCompanyInfo(
            siren=siren,
            company_name=company_name,
            legal_form_code=forme_code,
            legal_form_label=forme_label,
            capital_amount=float(capital_amount) if capital_amount is not None else None,
            capital_currency=capital_currency,
            capital_variable=capital_variable,
            greffe_city=greffe_city,
        )
