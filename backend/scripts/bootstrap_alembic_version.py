"""Rétablit la table de suivi des migrations quand elle a disparu de la base.

`alembic upgrade head` lit `alembic_version` pour savoir d'où repartir. Si
cette table est vide ou absente alors que le schéma, lui, est en place, Alembic
croit la base vierge et rejoue `001_initial_schema` — d'où
`DuplicateTableError: relation "users" already exists`, et un conteneur qui
meurt avant `uvicorn`.

Ce script tourne juste avant `alembic upgrade head`. Il ne fait quelque chose
que dans ce cas précis : il reconnaît où en est le schéma à partir des
empreintes de `alembic_schema_fingerprints.py`, puis inscrit la révision
correspondante — l'équivalent d'un `alembic stamp`, sans intervention humaine
sur la base.

Trois principes :

- **Ne jamais aggraver.** Toute situation qu'il ne sait pas traiter le fait
  ressortir en 0 après avoir dit pourquoi : Alembic reste l'autorité et
  produira son erreur habituelle.
- **Ne jamais deviner.** Une révision n'est inscrite que si le schéma la
  désigne sans ambiguïté : toutes les empreintes précédentes vraies, la
  suivante reconnaissable et fausse. Sinon, refus motivé.
- **Ne rien rejouer de destructeur.** Les migrations de données — remises à
  zéro, réécritures d'articles — ne laissent pas de trace dans le schéma. Si
  l'incertitude porte sur l'une d'elles, le script refuse plutôt que de
  risquer de l'appliquer une seconde fois.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from scripts.alembic_schema_fingerprints import DATA_ONLY, FINGERPRINTS  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent

# Table dont la présence dit que le schéma existe déjà. C'est la première de
# `001_initial_schema`, et celle sur laquelle la panne se manifeste.
SCHEMA_WITNESS = "users"

PROBES: dict[str, str] = {
    "table": "SELECT to_regclass('public.' || :a) IS NOT NULL",
    "column": (
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        " WHERE table_schema='public' AND table_name=:a AND column_name=:b)"
    ),
    "coltype": (
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        " WHERE table_schema='public' AND table_name=:a AND column_name=:b "
        "   AND data_type=:c AND coalesce(character_maximum_length, -1)=:d)"
    ),
    "colnull": (
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        " WHERE table_schema='public' AND table_name=:a AND column_name=:b AND is_nullable=:c)"
    ),
    "index": "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexdef=:a)",
    "constraint": (
        "SELECT EXISTS (SELECT 1 FROM pg_constraint "
        " WHERE connamespace='public'::regnamespace "
        "   AND conrelid::regclass::text=:a AND conname=:b)"
    ),
    "policy": (
        "SELECT EXISTS (SELECT 1 FROM pg_policies "
        " WHERE schemaname='public' AND tablename=:a AND policyname=:b)"
    ),
    "rls": (
        "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        " WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity AND c.relname=:a)"
    ),
}


def dire(message: str) -> None:
    print(f"[MIGRATIONS] {message}", flush=True)


def probe_of(objet: str) -> tuple[str, dict[str, str]]:
    """Traduit une empreinte en requête et en paramètres."""
    kind, reste = objet.split(":", 1)
    if kind in ("table", "index", "rls"):
        return PROBES[kind], {"a": reste}
    if kind in ("column", "constraint", "policy"):
        cible, nom = reste.rsplit(".", 1)
        return PROBES[kind], {"a": cible, "b": nom}
    if kind == "colnull":
        cible, valeur = reste.split("|", 1)
        table, colonne = cible.rsplit(".", 1)
        return PROBES[kind], {"a": table, "b": colonne, "c": valeur}
    if kind == "coltype":
        cible, typ, longueur = reste.split("|", 2)
        table, colonne = cible.rsplit(".", 1)
        # La longueur part en entier : le pilote refuse une chaîne sur une
        # colonne numérique, quel que soit le CAST écrit dans la requête.
        return PROBES[kind], {"a": table, "b": colonne, "c": typ, "d": int(longueur)}
    raise ValueError(f"empreinte de nature inconnue : {objet}")


def chain() -> list[str]:
    """La chaîne réelle des révisions, de la base à la tête."""
    script = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))
    return [rev.revision for rev in reversed(list(script.walk_revisions("base", "heads")))]


def uncovered(revisions: list[str]) -> list[str]:
    """Révisions que la table d'empreintes ne connaît pas — table à régénérer."""
    return [r for r in revisions if r not in FINGERPRINTS and r not in DATA_ONLY]


def pick(revisions: list[str], holds: dict[str, bool]) -> tuple[str | None, str]:
    """Choisit la révision à inscrire, ou explique pourquoi elle ne l'est pas.

    La plus avancée dont l'empreinte est vraie, à trois conditions : toutes
    celles d'avant le sont aussi (schéma cohérent), la suivante est
    reconnaissable (sinon on ignore si elle est passée), et elle est fausse.
    """
    vraies = [r for r in revisions if holds.get(r)]
    if not vraies:
        return None, "aucune empreinte ne correspond : ce schéma n'est pas celui de Bobby"

    trouvee = vraies[-1]
    rang = revisions.index(trouvee)
    incoherentes = [r for r in revisions[:rang] if r in FINGERPRINTS and not holds[r]]
    if incoherentes:
        return None, (
            f"schéma incohérent : {trouvee} est appliquée mais pas "
            f"{', '.join(incoherentes[:5])} — à examiner à la main"
        )

    suivantes = revisions[rang + 1 :]
    if suivantes and suivantes[0] not in FINGERPRINTS:
        return None, (
            f"impossible de trancher entre {trouvee} et {suivantes[0]} : cette dernière ne "
            "touche pas au schéma (données), et la rejouer par erreur ne serait pas anodin"
        )
    return trouvee, f"schéma reconnu à la révision {trouvee}"


async def main() -> int:
    try:
        from app.config import settings

        engine = create_async_engine(settings.async_database_url, pool_pre_ping=False)
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        dire(f"base injoignable, rien tenté ({type(exc).__name__}) — Alembic prend la main")
        return 0

    try:
        async with engine.connect() as conn:
            suivi = (
                await conn.execute(text("SELECT to_regclass('public.alembic_version')"))
            ).scalar()
            if suivi is not None:
                deja = (await conn.execute(text("SELECT count(*) FROM alembic_version"))).scalar()
                if deja:
                    return 0  # Cas normal : rien à faire, on ne dit rien.

            temoin = (
                await conn.execute(
                    text("SELECT to_regclass('public.' || :t)"), {"t": SCHEMA_WITNESS}
                )
            ).scalar()
            if temoin is None:
                dire("base vierge : Alembic va créer le schéma normalement")
                return 0

            dire(
                "la table de suivi des migrations est vide ou absente alors que le schéma "
                "existe : recherche de la révision réellement appliquée"
            )

            revisions = chain()
            manquantes = uncovered(revisions)
            if manquantes:
                dire(
                    "table d'empreintes incomplète pour "
                    f"{', '.join(manquantes[:5])} : régénérer "
                    "scripts/alembic_schema_fingerprints.py. Rien inscrit."
                )
                return 0

            holds: dict[str, bool] = {}
            for rev in revisions:
                if rev not in FINGERPRINTS:
                    continue
                objet, attendu = FINGERPRINTS[rev]
                requete, params = probe_of(objet)
                present = bool((await conn.execute(text(requete), params)).scalar())
                holds[rev] = present is attendu

            trouvee, raison = pick(revisions, holds)
            dire(raison)
            if trouvee is None:
                dire("aucune révision inscrite — la base est laissée intacte")
                return 0

            # Les sondes ont déjà ouvert la transaction de la connexion : les
            # écritures s'y ajoutent et sont validées d'un bloc.
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS alembic_version ("
                    " version_num VARCHAR(32) NOT NULL,"
                    " CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
                )
            )
            await conn.execute(text("DELETE FROM alembic_version"))
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": trouvee},
            )
            await conn.commit()
            reste = revisions[revisions.index(trouvee) + 1 :]
            dire(
                f"révision {trouvee} inscrite. "
                + (
                    f"Migrations à appliquer : {', '.join(reste)}"
                    if reste
                    else "Le schéma est déjà à jour."
                )
            )
            return 0
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        dire(f"amorçage abandonné ({type(exc).__name__}: {exc}) — Alembic prend la main")
        return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
