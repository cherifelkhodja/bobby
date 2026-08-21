# Workflow cible : Fournisseur (contrat cadre) + Mission (BDC)

> **Date** : 2026-08-21
> **Statut** : Spécifié, implémentation à venir
> **Remplace** : `refonte-contrat-cadre-bdc.md` (ADR-009, partiellement obsolète depuis la suppression du module BDC le 2026-07-10)

---

## Principes

Deux objets indépendants, **tous deux créés à la main dans Bobby**. Aucun webhook
BoondManager ne déclenche quoi que ce soit.

| Objet | Porte | Créé par | Signé par |
|-------|-------|----------|-----------|
| **Fournisseur / contrat cadre** | La relation commerciale : identité du tiers, vigilance documentaire, chartes partenaire | ADV / admin | Le fournisseur, en fin de workflow cadre |
| **Mission / BDC** | Une mission d'un consultant : client, conditions financières, dates | ADV / admin | Le fournisseur, en fin de workflow BDC |

Les deux signatures sont **séparées** (deux envois distincts). Un fournisseur a
N bons de commande dans le temps, un par consultant et par mission.

**Le contrat cadre n'est pas modifié** : entité, statuts, gabarit PDF, chartes et
push Boond restent tels quels. Le BDC s'ajoute à côté.

---

## Modèle de données

### Ce qui existe et ne bouge pas

- `tp_third_parties` — le fournisseur (identité + contacts + conformité).
- `vig_documents` — la vigilance documentaire, rattachée au fournisseur.
- `cm_contract_requests` + `cm_contracts` — **le contrat cadre**. Un fournisseur a un
  cadre actif dès qu'une demande liée à son `third_party_id` est en `signed` ou `active`.
  Pas de table `framework_contracts` séparée : le cadre *est* la demande signée.
- `cm_charter_templates`, `cm_signature_uploads` — chartes et circuit de signature.

### Nouvelle table : `cm_purchase_orders` (le BDC)

| Colonne | Type | Rôle |
|---|---|---|
| `id` | UUID PK | |
| `reference` | VARCHAR(20) unique | `XXX-BC-NNNN`, séquence par société émettrice |
| `status` | VARCHAR(30) | cf. machine à états |
| `company_id` | FK `cm_contract_companies` | société émettrice (GEM…) |
| `third_party_id` | FK `tp_third_parties` | fournisseur |
| `contract_request_id` | FK `cm_contract_requests` NULL | contrat cadre de rattachement |
| `parent_purchase_order_id` | FK self NULL | BDC d'origine en cas de reconduction |
| `boond_consultant_id` | INT | ID candidat ou ressource |
| `boond_consultant_type` | VARCHAR(20) | `candidate` / `resource` |
| `consultant_civility/first_name/last_name/email/phone` | | identité consultant |
| `boond_positioning_id` | INT | positionnement d'origine (obligatoire au 1er BDC) |
| `boond_need_id` | INT NULL | besoin, dérivé du positionnement |
| `client_name`, `mission_title`, `mission_description` | | mission |
| `mission_site_name/address/postal_code/city` | | lieu d'exécution |
| `sale_daily_rate` | NUMERIC(10,2) NULL | **TJM vente client — interne, jamais imprimé** |
| `purchase_daily_rate` | NUMERIC(10,2) | **CJM achat fournisseur — le seul taux du PDF** |
| `days_sold` | NUMERIC(6,2) | jours vendus |
| `free_days` | NUMERIC(6,2) def. 0 | jours de gratuité |
| `start_date`, `end_date` | DATE | période |
| `s3_key_draft`, `s3_key_signed` | | documents |
| `sent_for_signature_at`, `signed_at` | | horodatage |
| `yousign_envelope_id` | NULL | signature électronique (non branchée) |
| `boond_contract_id`, `boond_purchase_order_id` | INT NULL | résultat du push Boond |
| `boond_sync_error` | TEXT NULL | dernière erreur de synchro |
| `status_history` | JSON | traçabilité |
| `created_by` | FK `users.id` | |
| `created_at`, `updated_at` | | |

**Calculs.**

- Montant du BDC (celui qui figure sur le PDF fournisseur) :
  `(days_sold - free_days) x purchase_daily_rate`
- Marge indicative (affichée dans Bobby uniquement) :
  `(sale_daily_rate - purchase_daily_rate) x (days_sold - free_days)`

Le TJM de vente n'apparaît ni dans le PDF, ni dans les emails, ni dans aucune
réponse d'API accessible au fournisseur (portail).

---

## Machine à états du BDC

```
draft ──> generated ──> sent_for_signature ──> signed ──> active ──> closed
  │           │                  │
  └───────────┴──────────────────┴────────────> cancelled
```

| Statut | Sens |
|---|---|
| `draft` | Saisie en cours, éditable |
| `generated` | PDF généré, éditable après régénération |
| `sent_for_signature` | Envoyé au fournisseur |
| `signed` | Signé, push Boond en attente ou en erreur |
| `active` | Signé et synchronisé dans Boond |
| `closed` | Terminé (date de fin dépassée, ou clôture manuelle) |
| `cancelled` | Annulé avant signature |

**Garde de signature** : `generated → sent_for_signature` est refusé tant que le
contrat cadre du fournisseur n'est pas `signed` ou `active`. Le BDC reste
préparable pendant la contractualisation du cadre ; l'écran affiche « Contrat cadre
en cours — envoi possible dès sa signature ».

---

## Flux A — Création d'un fournisseur

1. **Nouveau fournisseur** (ADV/admin). Saisie : SIRET (auto-remplissage INSEE + INPI
   via `GET /contract-requests/siret-lookup/{siret}`), type de tiers, société
   émettrice, email de contact, et **choix du mode de collecte dès cet écran** :
   - « Le fournisseur remplit via le portail » → magic link, dépôt des documents ;
   - « Je saisis en personne » → l'ADV renseigne l'identité et dépose les documents
     (mécanique `notify_third_party=false` / `skip_documents` existante).
2. **Contrôle SIREN** : si un tiers porte déjà ce SIREN, Bobby propose de reprendre
   la fiche existante au lieu d'en créer une seconde (correction des doublons actuels).
3. La suite est le workflow cadre actuel, inchangé : collecte → conformité →
   brouillon → revue partenaire (ou validation interne) → signature → push Boond
   (société fournisseur + contacts + chartes partenaire).

Différence avec l'existant : plus d'ID consultant obligatoire à la création, et le
type de tiers + le contact sont saisis dès le premier écran (l'étape « validation
commerciale » disparaît de ce parcours).

---

## Flux B — Création d'une mission (BDC)

1. **Nouvelle mission** (ADV/admin). Saisie de l'**ID du positionnement Boond**.
2. Bobby lit `GET /positionings/{id}` et **contrôle l'état du positionnement**
   (pull, pas de webhook). Préremplissage : consultant (ID + candidat/ressource + nom),
   besoin (`opportunity`), CJM (`averageDailyCost`), quantité, dates.
3. Choix du **fournisseur** dans le panel — cadre actif *ou* en cours de création.
   Alerte si le consultant est déjà rattaché à un autre fournisseur.
4. Complément : client, intitulé et description de mission, lieu, TJM, CJM,
   jours vendus, jours de gratuité, dates. Besoin Boond modifiable, facultatif.
5. Génération du PDF (moteur HTML → PDF existant, charte « Éditorial »),
   numéroté `XXX-BC-NNNN` et référençant le contrat cadre parent.
6. Envoi en signature au fournisseur. **Aucune validation fournisseur ni consultant
   en amont** : le dossier est instruit uniquement côté Bobby.
7. À la signature, **push Boond** :
   - conversion candidat → ressource (état 3) si le consultant est encore candidat ;
   - rattachement au fournisseur (`PUT /resources/{id}/administrative`) ;
   - `POST /contracts` : `typeOf` selon le type de tiers, CJM en coût journalier moyen,
     dates de la mission, agence de la société émettrice ;
   - `POST /purchase-orders` : relation positionnement + montant achat
     `(jours vendus - gratuité) x CJM`.

Ce montant lève le `NEEDS-CONFIRMATION` historique sur `amountExcludingTax`.

---

## Flux C — Reconduction

Pas de tacite reconduction. Depuis un BDC `active` ou `closed`, l'action
**Reconduire** ouvre un nouveau BDC prérempli (même consultant, même fournisseur,
même mission), avec de nouvelles dates, quantités et conditions. Il porte
`parent_purchase_order_id` et une référence séquentielle propre.

**Pas de nouveau positionnement Boond** : la reconduction est pilotée depuis Bobby.
Côté Boond, elle produit un nouveau bon de commande sur le positionnement d'origine
et met à jour les dates du contrat Boond existant.

---

## Écrans

| Route | Contenu |
|---|---|
| `/contracts` | Onglet **Fournisseurs** (liste des cadres, existante) + bouton « Nouveau fournisseur » |
| `/contracts/:id` | Fiche cadre (existante) + section « Bons de commande » du fournisseur |
| `/contracts/bdc` | Onglet **Bons de commande** : liste, filtres par fournisseur / statut / consultant |
| `/contracts/bdc/:id` | Détail BDC : mission, conditions, PDF, signature, état de la synchro Boond |

Écriture réservée à ADV + admin. Le commercial garde un accès en lecture.

---

## Conformité documentaire

La vigilance reste portée par le fournisseur, pas par le BDC. Documents expirés au
moment d'un BDC : **alerte visible, pas de blocage** (décision produit de juillet 2026).

---

## Historique

Aucune donnée n'est supprimée. Les demandes existantes restent en l'état ; leurs
champs mission (`daily_rate`, `start_date`, `end_date`, `client_name`…) deviennent de
l'historique et ne sont plus alimentés pour les nouveaux dossiers. Aucune reprise
automatique des missions passées vers `cm_purchase_orders`.

---

## Décisions par défaut (à confirmer en revue)

1. **État du positionnement** autorisant la création d'un BDC : **7 « Gagné attente
   contrat »**, celui déjà utilisé par l'ancien webhook. Rendu configurable via
   `app_settings` pour ne pas figer la valeur dans le code.
2. **Reconduction côté Boond** : nouveau bon de commande sur le positionnement
   d'origine + mise à jour des dates du contrat Boond existant.
3. **Webhooks de création supprimés** : `positioning-update`, `candidate-state-update`,
   `resource-state-update`. Le webhook YouSign est conservé.
