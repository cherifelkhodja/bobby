"""Régénère `alembic_schema_fingerprints.py` à partir des migrations réelles.

À relancer après l'ajout d'une migration — un test échoue tant que la table
n'est pas à jour.

Le principe : dérouler la chaîne Alembic sur une base jetable, relever le
catalogue après chaque révision, et retenir pour chacune un objet qui **bascule
exactement là** — absent partout avant, présent partout après (ou l'inverse
pour une suppression). C'est cette bascule qui permet ensuite de reconnaître où
en est une base dont la table de suivi a été perdue.

Les migrations qui ne touchent pas au schéma — remises à zéro, contenu
d'articles — ne laissent évidemment aucune trace : elles sont listées à part,
et l'amorçage refuse d'inscrire une révision lorsque l'incertitude porte sur
l'une d'elles.

Usage (nécessite un PostgreSQL joignable et une base jetable) :

    EMPREINTES_DSN="postgresql://postgres@localhost:5432" \\
    python scripts/generer_empreintes_alembic.py
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import psycopg2

BACKEND = Path(__file__).resolve().parent.parent
CIBLE = BACKEND / "scripts" / "alembic_schema_fingerprints.py"

# Base jetable : elle est supprimée et recréée à chaque exécution.
DSN = os.environ.get("EMPREINTES_DSN", "postgresql://postgres@localhost:5432")
BASE = os.environ.get("EMPREINTES_DB", "bobby_empreintes")

# Ordre de préférence des empreintes : le plus simple à sonder d'abord.
RANG = {
    "table": 0,
    "column": 1,
    "index": 2,
    "constraint": 3,
    "policy": 4,
    "rls": 5,
    "coltype": 6,
    "colnull": 7,
}

ENV = {
    **os.environ,
    "DATABASE_URL": DSN.replace("postgresql://", "postgresql+asyncpg://", 1).rstrip("/")
    + f"/{BASE}",
    "JWT_SECRET": "generation-empreintes",
    "ENV": "test",
    "AWS_SECRETS_ENABLED": "false",
}


def connexion(base: str):
    parts = urlsplit(DSN)
    return psycopg2.connect(
        host=parts.hostname,
        port=parts.port or 5432,
        user=parts.username or "postgres",
        password=parts.password,
        dbname=base,
    )


def recreer_base() -> None:
    conn = connexion("postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{BASE}"')
        cur.execute(f'CREATE DATABASE "{BASE}"')
    conn.close()


def catalogue() -> set[str]:
    """Objets du schéma public, assez fins pour distinguer deux migrations voisines.

    Les valeurs par défaut sont volontairement écartées : leur forme varie d'un
    PostgreSQL à l'autre, une empreinte fondée dessus ne vaudrait pas ailleurs.
    """
    objs: set[str] = set()
    conn = connexion(BASE)
    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            " WHERE table_schema='public' AND table_type='BASE TABLE'"
        )
        objs |= {f"table:{r[0]}" for r in cur.fetchall()}
        cur.execute(
            "SELECT table_name, column_name, data_type, "
            "       coalesce(character_maximum_length, -1), is_nullable "
            "  FROM information_schema.columns WHERE table_schema='public'"
        )
        for table, colonne, typ, longueur, nullable in cur.fetchall():
            objs.add(f"column:{table}.{colonne}")
            objs.add(f"coltype:{table}.{colonne}|{typ}|{longueur}")
            objs.add(f"colnull:{table}.{colonne}|{nullable}")
        cur.execute("SELECT indexdef FROM pg_indexes WHERE schemaname='public'")
        objs |= {f"index:{r[0]}" for r in cur.fetchall()}
        cur.execute(
            "SELECT conrelid::regclass::text, conname FROM pg_constraint "
            " WHERE connamespace = 'public'::regnamespace"
        )
        objs |= {f"constraint:{t}.{n}" for t, n in cur.fetchall()}
        cur.execute("SELECT tablename, policyname FROM pg_policies WHERE schemaname='public'")
        objs |= {f"policy:{t}.{n}" for t, n in cur.fetchall()}
        cur.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            " WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity"
        )
        objs |= {f"rls:{r[0]}" for r in cur.fetchall()}
    conn.close()
    return {o for o in objs if "alembic_version" not in o}


def revisions() -> list[str]:
    """La chaîne réelle, de la base à la tête."""
    sys.path.insert(0, str(BACKEND))
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))
    return [rev.revision for rev in reversed(list(script.walk_revisions("base", "heads")))]


def bascule(index: int, revs: list[str], releves: dict[str, set[str]]) -> tuple[str, bool] | None:
    """Objet qui bascule exactement à cette révision, s'il en existe un."""
    avant = releves[revs[index - 1]] if index else set()
    apres = releves[revs[index]]
    tous_avant = [releves[r] for r in revs[:index]]
    tous_apres = [releves[r] for r in revs[index + 1 :]]

    ajoutes = sorted(apres - avant, key=lambda o: (RANG.get(o.split(":", 1)[0], 9), o))
    for obj in ajoutes:
        if all(obj not in s for s in tous_avant) and all(obj in s for s in tous_apres):
            return obj, True

    retires = sorted(avant - apres, key=lambda o: (RANG.get(o.split(":", 1)[0], 9), o))
    for obj in retires:
        if all(obj in s for s in tous_avant) and all(obj not in s for s in tous_apres):
            return obj, False
    return None


def main() -> int:
    recreer_base()
    revs = revisions()
    print(f"{len(revs)} révisions, de {revs[0]} à {revs[-1]}")

    releves: dict[str, set[str]] = {}
    for rev in revs:
        subprocess.run(
            ["alembic", "upgrade", rev], cwd=BACKEND, check=True, capture_output=True, env=ENV
        )
        releves[rev] = catalogue()

    empreintes: dict[str, tuple[str, bool]] = {}
    donnees_seules: list[str] = []
    for i, rev in enumerate(revs):
        trouvee = bascule(i, revs, releves)
        if trouvee:
            empreintes[rev] = trouvee
        else:
            donnees_seules.append(rev)

    CIBLE.write_text(rendre(empreintes, donnees_seules))
    # Le fichier produit passe sous le formateur du dépôt : sans cela, chaque
    # régénération ferait rougir `ruff format --check` en intégration.
    subprocess.run(["ruff", "format", str(CIBLE)], cwd=BACKEND, check=False, capture_output=True)
    print(f"{len(empreintes)} empreintes, {len(donnees_seules)} migrations de données")
    print(f"écrit dans {CIBLE.relative_to(BACKEND)}")
    return 0


def rendre(empreintes: dict[str, tuple[str, bool]], donnees_seules: list[str]) -> str:
    lignes = "\n".join(
        f"    {rev!r}: ({obj!r}, {present})," for rev, (obj, present) in empreintes.items()
    )
    autres = "\n".join(f"    {rev!r}," for rev in donnees_seules)
    return f'''"""Empreintes de schéma : à quoi reconnaître qu'une migration est appliquée.

Table **générée** par `scripts/generer_empreintes_alembic.py`, qui déroule la
chaîne Alembic sur un PostgreSQL réel et retient, pour chaque révision, un objet
qui bascule exactement là — absent partout avant, présent partout après. C'est
ce qui permet à `bootstrap_alembic_version.py` de reconnaître où en est une base
dont la table de suivi a été perdue.

Ne pas éditer à la main : régénérer après l'ajout d'une migration. Un test
vérifie que la chaîne est couverte de bout en bout.

Format : ``révision: (objet, doit_être_présent)``. Les objets sont préfixés par
leur nature — `table:`, `column:`, `coltype:`, `colnull:`, `index:`,
`constraint:`, `policy:`, `rls:`.
"""

# Révisions reconnaissables à un objet du schéma.
FINGERPRINTS: dict[str, tuple[str, bool]] = {{
{lignes}
}}

# Révisions qui ne touchent pas au schéma — contenu d'articles, remises à zéro,
# corrections de données —, et celles dont les objets ont été repris par une
# migration ultérieure. Rien ne les distingue de la précédente ; une base
# arrêtée sur l'une d'elles n'est donc pas reconnaissable, et l'amorçage refuse
# alors d'inscrire une révision plutôt que de risquer de les rejouer.
DATA_ONLY: frozenset[str] = frozenset({{
{autres}
}})
'''


if __name__ == "__main__":
    raise SystemExit(main())
