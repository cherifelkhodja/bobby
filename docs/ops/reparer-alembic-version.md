# Réparer `alembic_version` (déploiement qui recrée la table `users`)

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

Aucune correction de fichier ne peut y remédier : il faut écrire dans la base.

## 1. Diagnostic

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

## 2. Réparation

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

La panne a été reproduite à l'identique sur un PostgreSQL 16 local, schéma
complet et `alembic_version` vidée, puis réparée par le SQL ci-dessus :
`alembic upgrade head` redevient muet et `alembic current` répond `082 (head)`.
Le cas d'une base restée à `078` a été vérifié aussi : le diagnostic la désigne
correctement, et le redéploiement applique `079` à `082`.
