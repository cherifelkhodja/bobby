# `alembic_version` perdue : réparation automatique au démarrage

> **Depuis le 2026-08-24, il n'y a plus rien à faire à la main** : le conteneur
> répare la situation lui-même au démarrage
> (`scripts/bootstrap_alembic_version.py`, lancé avant `alembic upgrade head`).
> Ce document explique ce qu'il fait, et ce qui reste à faire dans les cas où
> il refuse d'agir.


## Le symptôme

Le conteneur backend meurt au démarrage, avant `uvicorn` :

```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema, Initial schema creation
asyncpg.exceptions.DuplicateTableError: relation "users" already exists
```

## La cause

`alembic upgrade head` repart de zéro (`Running upgrade  ->`, sans révision de
départ) : la table `alembic_version` est **vide ou absente** dans la base. Le
schéma, lui, est bien là — d'où la collision sur `users`.

Ce n'est pas un problème de code : la chaîne de migrations est saine (racine
unique `001_initial_schema`, tête unique, aucune branche). Rien dans
l'application ne crée de table hors Alembic (`create_all` n'existe nulle part),
donc la table de suivi a été perdue côté base : suppression manuelle, ou
restauration d'un dump qui ne l'emportait pas.

## Ce que fait l'amorçage

`scripts/bootstrap_alembic_version.py` tourne juste avant `alembic upgrade head`.

Dans le cas normal — la table de suivi porte une révision — il ne dit rien et
rend la main. Il n'agit que si elle est vide ou absente **et** que le schéma
existe : il reconnaît alors où en est la base et inscrit la révision
correspondante, l'équivalent d'un `alembic stamp`.

La reconnaissance s'appuie sur `scripts/alembic_schema_fingerprints.py` : pour
chaque migration, un objet du schéma qui **bascule exactement là** — absent
partout avant, présent partout après. Cette table est *générée* en déroulant la
chaîne sur un PostgreSQL réel (`scripts/generer_empreintes_alembic.py`) ; un
test échoue si une migration ajoutée n'y figure pas.

Trois règles gouvernent l'écriture :

- **Ne jamais aggraver.** Toute situation non traitée ressort sans rien écrire,
  après l'avoir dit dans les logs (préfixe `[MIGRATIONS]`). Alembic reste
  l'autorité et produit son erreur habituelle. Le `CMD` utilise d'ailleurs `||`
  et non `&&` : même un plantage de l'amorçage ne retient pas le déploiement.
- **Ne jamais deviner.** Une révision n'est inscrite que si toutes les
  empreintes antérieures sont vraies (schéma cohérent) et que la suivante est
  reconnaissable et fausse.
- **Ne rien rejouer de destructeur.** Les migrations de données — remises à
  zéro, réécritures d'articles — ne laissent pas de trace dans le schéma. Si
  l'incertitude porte sur l'une d'elles, l'amorçage refuse.

## S'il refuse

Le message dit lequel des trois cas s'applique. La réparation manuelle
ci-dessous reste alors valable.

## 1. Diagnostic manuel

Sur la base de production (`railway connect Postgres`) :

```sql
-- Quelle base, quel schéma, la table de suivi existe-t-elle ?
SELECT current_database() AS base, current_schema() AS schema_courant,
       to_regclass('public.alembic_version') AS table_alembic;

-- Que contient-elle ? (ne casse pas si elle est absente)
DO $$
DECLARE v text;
BEGIN
  IF to_regclass('public.alembic_version') IS NULL THEN
    RAISE NOTICE 'alembic_version : TABLE ABSENTE';
  ELSE
    EXECUTE 'SELECT coalesce(string_agg(version_num, '', ''), ''(TABLE VIDE)'') FROM alembic_version' INTO v;
    RAISE NOTICE 'alembic_version : %', v;
  END IF;
END $$;

-- Jusqu'où va réellement le schéma ?
SELECT
  to_regclass('public.cm_contract_requests') IS NOT NULL AS m025_contrats,
  to_regclass('public.cm_purchase_order_requests') IS NULL
    AND to_regclass('public.cm_framework_contracts') IS NULL       AS m077_anciennes_tables_supprimees,
  EXISTS (SELECT 1 FROM information_schema.columns
           WHERE table_name='cm_contract_requests' AND column_name='documents_skipped')    AS m078_documents_skipped,
  to_regclass('public.cm_purchase_orders') IS NOT NULL                                     AS m079_bons_de_commande,
  EXISTS (SELECT 1 FROM information_schema.columns
           WHERE table_name='cm_purchase_orders' AND column_name='provisional_reference')  AS m080_reference_provisoire,
  EXISTS (SELECT 1 FROM information_schema.columns
           WHERE table_name='tp_third_parties' AND column_name='vat_liable')               AS m081_tva,
  EXISTS (SELECT 1 FROM information_schema.columns
           WHERE table_name='tp_third_parties' AND column_name='boond_billing_contact_id') AS m082_contact_facturation;
```

**La révision à inscrire est la dernière colonne à `t`** : tout à `t` → `082` ;
`m078` à `t` et le reste à `f` → `078` ; etc.

## 2. Réparation manuelle

Même effet qu'un `alembic stamp`, sans avoir à lancer l'outil contre la
production. Remplacer `082` par la révision trouvée ci-dessus.

```sql
BEGIN;
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('082');
COMMIT;
```

Aucune donnée métier n'est touchée : cette table ne contient qu'une ligne, le
numéro de la dernière migration appliquée.

## 3. Redéployer

`alembic upgrade head` repart alors de la révision inscrite : rien à rejouer si
elle vaut `082`, sinon seules les migrations suivantes s'appliquent.

## Vérifié

Sur un PostgreSQL 16 local, la panne a d'abord été reproduite à l'identique
(schéma complet, `alembic_version` vidée). Le `CMD` du conteneur a ensuite été
rejoué tel quel sur sept états de base :

| État de départ | Résultat |
|---|---|
| Schéma à jour, suivi vidé (le cas de la prod) | `082` inscrite, aucune migration rejouée |
| Schéma à jour, table de suivi supprimée | idem |
| Schéma arrêté à `078`, suivi supprimé | `078` inscrite, `079` à `082` appliquées |
| Base vierge | rien inscrit, Alembic crée le schéma |
| Déploiement normal (suivi renseigné) | muet, aucune écriture |
| Base arrêtée sur une migration de données (`063`) | refus motivé, base intacte |
| Schéma étranger, ou incohérent (une table ancienne manquante) | refus motivé, base intacte |
