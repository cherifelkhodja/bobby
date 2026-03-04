"""INPI RNE API client for company information lookup.

Uses a static Bearer token stored in AWS Secrets Manager (INPI_TOKEN).
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

from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger()

INPI_BASE_URL = "https://registre-national-entreprises.inpi.fr/api"


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
# Source: Infogreffe / Legalin.fr - Open Licence v2.0 (2025-04-09), 134 greffes
# Notes:
#   - Pour les depts avec plusieurs TC, on retourne le greffe principal (préfecture/le plus grand).
#     Une commune précise permettrait de raffiner (non implémenté ici).
#   - Alsace-Moselle (57, 67, 68) : pas de TC, compétence du Tribunal Judiciaire (TJ).
#   - Corse (2A, 2B) : codes postaux 20xxx — dérivation via derive_greffe_city().
# =============================================================================
DEPT_TO_GREFFE: dict[str, str] = {
    "01": "Bourg-en-Bresse",
    "02": "Saint-Quentin",          # Aussi: Soissons
    "03": "Cusset",                 # Aussi: Montluçon
    "04": "Manosque",
    "05": "Gap",
    "06": "Nice",                   # Aussi: Antibes, Cannes, Grasse
    "07": "Aubenas",
    "08": "Sedan",
    "09": "Foix",
    "10": "Troyes",
    "11": "Carcassonne",            # Aussi: Narbonne
    "12": "Rodez",
    "13": "Marseille",              # Aussi: Aix-en-Provence, Salon-de-Provence, Tarascon
    "14": "Caen",                   # Aussi: Lisieux
    "15": "Aurillac",
    "16": "Angoulême",
    "17": "La Rochelle",            # Aussi: Saintes
    "18": "Bourges",
    "19": "Brive-la-Gaillarde",
    # 2A et 2B (Corse) gérés dans derive_greffe_city() via le code postal 20xxx
    "2A": "Ajaccio",
    "2B": "Bastia",
    "21": "Dijon",
    "22": "Saint-Brieuc",
    "23": "Guéret",
    "24": "Périgueux",              # Aussi: Bergerac
    "25": "Besançon",
    "26": "Romans-sur-Isère",
    "27": "Evreux",                 # Aussi: Bernay
    "28": "Chartres",
    "29": "Brest",                  # Aussi: Quimper
    "30": "Nîmes",
    "31": "Toulouse",
    "32": "Auch",
    "33": "Bordeaux",               # Aussi: Libourne
    "34": "Montpellier",            # Aussi: Béziers
    "35": "Rennes",                 # Aussi: Saint-Malo
    "36": "Châteauroux",
    "37": "Tours",
    "38": "Grenoble",               # Aussi: Vienne
    "39": "Lons-le-Saunier",
    "40": "Mont-de-Marsan",         # Aussi: Dax
    "41": "Blois",
    "42": "Saint-Etienne",          # Aussi: Roanne
    "43": "Le Puy-en-Velay",
    "44": "Nantes",                 # Aussi: Saint-Nazaire
    "45": "Orléans",
    "46": "Cahors",
    "47": "Agen",
    "48": "Mende",
    "49": "Angers",
    "50": "Cherbourg-Octeville",    # Aussi: Coutances
    "51": "Reims",                  # Aussi: Châlons-en-Champagne
    "52": "Chaumont",
    "53": "Laval",
    "54": "Nancy",                  # Aussi: Briey
    "55": "Bar-le-Duc",
    "56": "Vannes",                 # Aussi: Lorient
    "57": "Metz",                   # TJ Alsace-Moselle (pas de TC) — Aussi: Sarreguemines, Thionville
    "58": "Nevers",
    "59": "Lille Métropole",        # Aussi: Douai, Dunkerque, Valenciennes
    "60": "Beauvais",               # Aussi: Compiègne
    "61": "Alençon",
    "62": "Arras",                  # Aussi: Boulogne-sur-Mer
    "63": "Clermont-Ferrand",
    "64": "Pau",                    # Aussi: Bayonne
    "65": "Tarbes",
    "66": "Perpignan",
    "67": "Strasbourg",             # TJ Alsace-Moselle (pas de TC) — Aussi: Saverne
    "68": "Colmar",                 # TJ Alsace-Moselle (pas de TC) — Aussi: Mulhouse
    "69": "Lyon",                   # Aussi: Villefranche-Tarare
    "70": "Vesoul",
    "71": "Chalon-sur-Saône",       # Aussi: Mâcon
    "72": "Le Mans",
    "73": "Chambéry",
    "74": "Annecy",                 # Aussi: Thonon-les-Bains
    "75": "Paris",
    "76": "Rouen",                  # Aussi: Le Havre, Dieppe
    "77": "Meaux",                  # Aussi: Melun
    "78": "Versailles",
    "79": "Niort",
    "80": "Amiens",
    "81": "Albi",                   # Aussi: Castres
    "82": "Montauban",
    "83": "Toulon",                 # Aussi: Draguignan, Fréjus
    "84": "Avignon",
    "85": "La Roche-sur-Yon",
    "86": "Poitiers",
    "87": "Limoges",
    "88": "Epinal",
    "89": "Auxerre",                # Aussi: Sens
    "90": "Belfort",
    "91": "Evry",
    "92": "Nanterre",
    "93": "Bobigny",
    "94": "Créteil",
    "95": "Pontoise",
    # DOM-TOM
    "971": "Pointe-à-Pitre",        # Aussi: Basse-Terre
    "972": "Fort-de-France",
    "973": "Cayenne",
    "974": "Saint-Denis",
}


def derive_greffe_city(postal_code: str, commune: str | None = None) -> str | None:
    """Derive the greffe (Tribunal de Commerce / Judiciaire) city from a French postal code.

    Uses the department code extracted from the postal code. For departments with
    multiple greffes, returns the principal one (préfecture / largest city).

    Special cases:
    - Corse: postal codes start with "20" but map to 2A or 2B depending on range.
      20000–20199 → Corse-du-Sud (2A) → Ajaccio
      20200–20999 → Haute-Corse (2B) → Bastia
    - DOM-TOM: 97x → 3-digit department code.
    - Alsace-Moselle (57, 67, 68): Tribunal Judiciaire, not TC (same city returned).
    """
    if not postal_code or len(postal_code) < 2:
        return None

    # Corse: postal codes 20xxx map to 2A or 2B (not "20")
    if postal_code.startswith("20") and len(postal_code) == 5:
        try:
            num = int(postal_code)
            return "Ajaccio" if num < 20200 else "Bastia"
        except ValueError:
            pass

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


import time as _time

# Module-level token cache: (token, expiry_timestamp)
_token_cache: tuple[str, float] | None = None
_TOKEN_TTL = 3600  # Refresh token after 1 hour


async def _login_inpi(username: str, password: str) -> str | None:
    """Login to INPI RNE API and return a fresh Bearer token."""
    url = f"{INPI_BASE_URL}/sso/login"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"username": username, "password": password})
        if resp.status_code == 200:
            token = resp.json().get("token")
            logger.info("inpi_login_success")
            return token
        logger.error("inpi_login_failed", status_code=resp.status_code)
        return None
    except Exception as exc:
        logger.error("inpi_login_error", error=str(exc))
        return None


async def _get_inpi_token(username: str, password: str, static_token: str) -> str | None:
    """Return a valid INPI token, refreshing via login if expired."""
    global _token_cache

    now = _time.monotonic()
    if _token_cache and now < _token_cache[1]:
        return _token_cache[0]

    # Try to login with credentials
    if username and password:
        token = await _login_inpi(username, password)
        if token:
            _token_cache = (token, now + _TOKEN_TTL)
            return token

    # Fallback to static token
    if static_token:
        return static_token

    return None


class InpiClient:
    """Client for the INPI Registre National des Entreprises (RNE) API.

    Authentication: auto-login with INPI_USERNAME/INPI_PASSWORD (JWT cached 1h).
    Falls back to static INPI_TOKEN if credentials are not configured.
    """

    def __init__(self, username: str = "", password: str = "", token: str = "") -> None:
        self._username = username
        self._password = password
        self._static_token = token

    async def get_company(self, siren: str) -> InpiCompanyInfo | None:
        """Fetch company info from INPI RNE by SIREN.

        Returns InpiCompanyInfo with legal form, capital, and greffe city,
        or None if not found or on error.
        """
        global _token_cache

        token = await _get_inpi_token(self._username, self._password, self._static_token)
        if not token:
            logger.warning("inpi_token_not_configured")
            return None

        url = f"{INPI_BASE_URL}/companies/{siren}"

        for attempt in range(2):  # at most 1 retry after token refresh
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    logger.info("inpi_company_not_found", siren=siren)
                    return None

                if response.status_code in (401, 403) and attempt == 0:
                    # Token expired — force refresh and retry once
                    logger.warning("inpi_token_expired_refreshing", siren=siren)
                    _token_cache = None
                    token = await _get_inpi_token(self._username, self._password, self._static_token)
                    if not token:
                        return None
                    continue

                if response.status_code in (401, 403):
                    logger.error("inpi_token_rejected", status_code=response.status_code, siren=siren)
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
