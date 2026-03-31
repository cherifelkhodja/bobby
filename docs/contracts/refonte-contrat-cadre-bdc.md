# Refonte : Simplification Workflow Fournisseurs (Contrat Cadre + BDC)

> **Date** : 2026-03-31
> **Statut** : Planifié
> **Auteur** : Discussion product owner + dev

---

## Contexte & Problématique

### Situation actuelle
Le workflow de contractualisation est déclenché par un webhook Boond sur le **positionnement state 7** ("Gagné attente contrat"). Ce webhook mélange dans un seul `ContractRequest` (14 statuts) la création du contrat cadre fournisseur ET les informations liées à la mission (BDC).

### Problèmes identifiés
1. **Timing** : Les informations du BDC (TJM mission, dates, etc.) arrivent parfois plusieurs jours après le GO client, mais il faut sécuriser le consultant en contractualisant immédiatement un contrat cadre.
2. **Couplage** : Le contrat cadre (relation fournisseur) et le BDC (mission spécifique) ont des cycles de vie différents mais sont gérés ensemble.
3. **Saisie commerciale lourde** : Le commercial doit renseigner trop d'informations à la validation (type tiers, TJM, dates mission, contact, consultant, adresse...) alors que pour un contrat cadre seul, on n'a besoin que du minimum.
4. **UI surchargée** : La page de gestion affiche toutes les étapes du workflow d'un coup, même celles qui ne sont pas encore atteignables.
5. **Pas de gestion des re-contractualisations** : Aucun workflow pour les ressources existantes dont le contrat a expiré ou qui changent de société.

---

## Décisions

### 1. Nouveaux webhooks Boond (déclencheurs)

Le workflow n'est plus déclenché uniquement par le positionnement. On ajoute 2 nouveaux webhooks sur les entités **candidat** et **ressource** :

| Webhook | Entité Boond | State | Libellé | Scénario |
|---------|-------------|-------|---------|----------|
| **Nouveau** | Candidat | **11** | En attente de contrat | Nouveau consultant → contrat cadre complet |
| **Nouveau** | Ressource | **4** | Attente nouveau contrat | Contrat cadre expiré → re-contractualisation (même société, données pré-remplies) |
| **Nouveau** | Ressource | **5** | Changement de contrat | Changement de société → contrat cadre complet (nouvelle entité fournisseur) |
| **Existant** | Positionnement | **7** | Gagné attente contrat | BDC (inchangé pour le moment) |

#### États candidats Boond (référence complète)

| ID | Libellé | Pertinence workflow |
|----|---------|-------------------|
| 0 | A traiter ! | - |
| 1 | En cours de qualif. | - |
| 2 | Vivier | - |
| 8 | Vivier / Top Profil | - |
| 6 | CV Intéressant | - |
| 7 | Proposition en cours | - |
| 3 | Converti en Ressource | Auto (Boond) |
| 5 | Ne plus contacter | - |
| 4 | Leonum | - |
| 9 | En mission ailleurs | - |
| 10 | Cooptation via plateforme | - |
| **11** | **En attente de contrat** | **Trigger contrat cadre** |

#### États ressources Boond (référence complète)

| ID | Libellé | Pertinence workflow |
|----|---------|-------------------|
| 1 | En cours | Défaut |
| 2 | Intercontrat | - |
| 0 | Sortie | Auto (Boond) |
| 3 | Arrivée prochaine | Après conversion candidat → ressource |
| 7 | Sortie Prochaine | - |
| **4** | **Attente nouveau contrat** | **Trigger re-contractualisation (contrat expiré)** |
| **5** | **Changement de contrat** | **Trigger nouveau contrat cadre (nouvelle société)** |

### 2. Séparation complète Contrat Cadre / BDC

Deux workflows totalement indépendants :

#### Workflow Contrat Cadre (simplifié)

```
Webhook (candidat 11 / ressource 4 / ressource 5)
    │
    ▼
PENDING_COMMERCIAL ─── Validation commerciale simplifiée
    │                   (type tiers + contact contractualisation)
    ▼
COLLECTING_DOCS ────── Portail magic link (docs fournisseur, inchangé)
    │
    ▼
REVIEWING_COMPLIANCE ─ Conformité (intégrée dans la page contrat)
    │
    ▼
DRAFT_GENERATED ────── Génération contrat cadre
    │
    ▼
SENT_TO_PARTNER ────── Envoi au partenaire pour review
    │
    ├── PARTNER_APPROVED → SENT_FOR_SIGNATURE → SIGNED → ACTIVE
    │
    └── PARTNER_REQUESTED_CHANGES → retour DRAFT_GENERATED
```

**Statuts supprimés** :
- `CONFIGURING_CONTRACT` : intégré dans la génération du draft (pas d'étape séparée)

**Statuts conservés** :
- `REDIRECTED_PAYFIT` : type salarié → redirection PayFit (terminal)
- `COMPLIANCE_BLOCKED` : blocage conformité
- `CANCELLED` : annulation à tout moment

#### Workflow BDC (existant, inchangé pour le moment)

```
Webhook positionnement state 7
    │
    ▼
PurchaseOrderRequest (7 statuts existants)
```

Le BDC est géré dans une **page séparée** (Option B), liée au contrat cadre mais avec son propre cycle de vie.

### 3. Simplification de la saisie commerciale

Pour un contrat cadre, le commercial ne renseigne que :

| Champ | Obligatoire | Notes |
|-------|-------------|-------|
| Type de tiers | Oui | freelance / sous-traitant / portage salarial |
| Email contact contractualisation | Oui | Pour envoi magic link portail |
| Consultant (civilité, nom, prénom) | Si absent Boond | Pré-rempli depuis données Boond |

**Champs déplacés vers le BDC** :
- TJM / daily_rate
- Dates de mission (start_date, end_date)
- Adresse de mission
- Client
- Description mission

### 4. Traitement différencié selon le déclencheur

#### Candidat state 11 → Nouveau contrat cadre
- Workflow complet : validation commerciale → docs → conformité → contrat → signature
- Conversion candidat → ressource (state 3) après signature du contrat cadre (inchangé)
- Push Boond : création société fournisseur + contrat

#### Ressource state 4 → Re-contractualisation (contrat expiré)
- **Même société** (même SIREN) : données fournisseur pré-remplies depuis le contrat cadre précédent
- Docs de conformité : **réutiliser les documents encore valides**, ne redemander que les expirés ou non conformes
- Si documents non conformes lors de la review → on les redemande via le portail
- Workflow allégé : validation commerciale (pré-remplie) → collecte docs manquants → conformité → nouveau contrat cadre → signature
- Pas de conversion candidat → ressource (déjà une ressource)

#### Ressource state 5 → Changement de société
- **Nouvelle société** : workflow complet comme candidat state 11
- Pas de pré-remplissage (nouvelle entité fournisseur)
- Pas de conversion candidat → ressource (déjà une ressource)

### 5. UI/UX : Blocage progressif

La page détail d'un contrat cadre n'affiche les sections que quand leurs prérequis sont remplis :

| Section | Prérequis | Visible quand |
|---------|-----------|---------------|
| Validation commerciale | Aucun | Toujours (si status = PENDING_COMMERCIAL) |
| Documents fournisseur | Validation commerciale faite | Status >= COLLECTING_DOCS |
| Conformité | Documents uploadés | Status >= REVIEWING_COMPLIANCE |
| Génération contrat | Conformité validée | Status >= DRAFT_GENERATED (ou prêt à générer) |
| Envoi partenaire | Draft généré | Status >= DRAFT_GENERATED |
| Signature | Partenaire a approuvé | Status >= PARTNER_APPROVED |
| Actions Boond | Contrat signé | Status >= SIGNED |

**Principe** : Pas de configuration/action disponible tant que l'étape précédente n'est pas terminée.

### 6. Conformité intégrée dans la page contrat

Au lieu d'un dashboard conformité séparé (`/compliance`), la section conformité est directement intégrée dans la page de chaque contrat cadre :

- Liste des documents demandés avec statuts (en attente, reçu, validé, rejeté, expiré)
- Actions valider/rejeter directement dans la page
- Alertes documents expirants
- Le dashboard `/compliance` reste comme **vue d'ensemble** transversale pour l'ADV

### 7. BDC : Pages séparées (Option B)

Les bons de commande sont gérés dans des **pages séparées** mais liées :

- **Liste BDC** : `/contracts/purchase-orders` — tous les BDC avec filtre par contrat cadre
- **Détail BDC** : `/contracts/purchase-orders/:id` — formulaire BDC avec lien vers le contrat cadre parent
- **Depuis la page contrat cadre** : section avec la liste des BDC associés + bouton "Nouveau BDC"

Un contrat cadre peut avoir **N bons de commande** au fil du temps.

---

## Impacts techniques

### Backend

| Composant | Impact |
|-----------|--------|
| Webhooks (`/api/v1/webhooks`) | 2 nouveaux endpoints : candidat state change, ressource state change |
| `ContractRequest` entity | Champs mission (TJM, dates, adresse) déplacés vers `PurchaseOrderRequest` |
| `ContractRequestStatus` | Suppression `CONFIGURING_CONTRACT`, simplification machine à états |
| `validate_commercial` use case | Allégé (plus de TJM, dates, adresse mission) |
| `create_contract_request` use case | 3 modes : candidat 11, ressource 4, ressource 5 |
| Vigilance | Logique de réutilisation docs valides pour state 4 |
| Boond client | Ajout endpoints lecture candidat/ressource par state |

### Frontend

| Composant | Impact |
|-----------|--------|
| `ContractDetail.tsx` | Refonte : affichage progressif par section |
| `ContractManagement.tsx` | Séparation claire onglets contrat cadre / BDC |
| Formulaire validation commerciale | Simplifié (3 champs au lieu de 10+) |
| Section conformité | Intégrée dans page contrat |
| Pages BDC | Pages séparées avec lien vers contrat cadre |

### Migrations DB

| Migration | Description |
|-----------|-------------|
| TBD | Déplacement champs mission de `cm_contract_requests` vers `cm_purchase_order_requests` |
| TBD | Ajout `trigger_type` sur `cm_contract_requests` (candidat_11, ressource_4, ressource_5) |
| TBD | Ajout `previous_contract_request_id` pour re-contractualisations |

### Configuration Boond

| Action | Description |
|--------|-------------|
| Webhook candidat | Configurer webhook sur changement d'état candidat, filtre state 11 |
| Webhook ressource | Configurer webhook sur changement d'état ressource, filtre states 4 et 5 |
| État ressource 5 | Déjà créé ("Changement de contrat") |

---

## Ce qui ne change PAS

- Webhook positionnement state 7 pour les BDC (conservé)
- Portail tiers magic link (documents fournisseur)
- Documents de conformité demandés par type d'entité (EI, société, portage)
- CRON jobs (expirations, relances, purge)
- Génération PDF contrat (HTML + WeasyPrint)
- Signature (manuelle ou YouSign)
- Push Boond après signature (société fournisseur + contrat + conversion candidat)
- Conversion candidat → ressource (state 3) après signature

---

## Questions résolues

- [x] **Docs non conformes (state 4)** : Si les documents sont non conformes, on les redemande via le portail. Pas de bypass.
- [x] **Idempotence candidat state 11** : Si un candidat state 11 est déclenché mais qu'un ContractRequest est déjà en cours → on ignore (idempotence).
- [x] **État ACTIVE contrat cadre** : Oui, on conserve l'état ACTIVE entre SIGNED et ARCHIVED.

## Questions ouvertes

- [ ] Format exact des webhooks Boond pour candidat/ressource state change (à vérifier dans la doc Boond)
- [ ] Payload webhook candidat : quelles données sont incluses ? (ID candidat, state, etc.)
- [ ] Payload webhook ressource : quelles données sont incluses ? (ID ressource, state, société liée, etc.)
