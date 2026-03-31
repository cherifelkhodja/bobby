# Configuration des Webhooks BoondManager (ADR-009)

## Webhooks a configurer dans BoondManager

> **Acces** : BoondManager > Parametrage > API > Webhooks
> **URL de base backend** : `https://<your-backend>/api/v1/webhooks`

---

## 1. Webhook existant : Positionnement (state 7)

| Parametre | Valeur |
|-----------|--------|
| **Nom** | Bobby - Positionnement gagne |
| **URL** | `https://<backend>/api/v1/webhooks/boondmanager/positioning-update` |
| **Entite** | Positionnement |
| **Evenement** | Modification |
| **Filtre etat** | State = 7 (Gagne attente contrat) |

---

## 2. Nouveau webhook : Candidat (state 11)

| Parametre | Valeur |
|-----------|--------|
| **Nom** | Bobby - Candidat en attente de contrat |
| **URL** | `https://<backend>/api/v1/webhooks/boondmanager/candidate-state-update` |
| **Entite** | Candidat |
| **Evenement** | Modification |
| **Filtre etat** | State = 11 (En attente de contrat) |

**Declencheur** : Quand un candidat passe en state 11, Bobby cree automatiquement une demande de contrat cadre (trigger_type=candidat_11).

---

## 3. Nouveau webhook : Ressource (states 4 et 5)

| Parametre | Valeur |
|-----------|--------|
| **Nom** | Bobby - Ressource attente/changement contrat |
| **URL** | `https://<backend>/api/v1/webhooks/boondmanager/resource-state-update` |
| **Entite** | Ressource |
| **Evenement** | Modification |
| **Filtre etat** | States = 4 (Attente nouveau contrat) ou 5 (Changement de contrat) |

**Declencheurs** :
- **State 4** : Contrat expire, meme societe → re-contractualisation avec reutilisation des docs valides (trigger_type=ressource_4)
- **State 5** : Changement de societe → nouveau contrat cadre complet (trigger_type=ressource_5)

> **Note** : Si Boond ne permet pas de filtrer sur 2 states dans un seul webhook, creer 2 webhooks separees avec la meme URL. Le backend filtre correctement les deux states.

---

## Format du payload webhook Boond

Tous les webhooks Boond (positionnement, candidat, ressource) utilisent le **meme format** :

```json
[
  {
    "data": {
      "id": "3_abc123...",
      "type": "webhookevent",
      "attributes": {
        "type": "update"
      },
      "relationships": {
        "dependsOn": {
          "id": "433",
          "type": "positioning"
        },
        "log": {
          "id": "117497",
          "type": "log"
        }
      },
      "included": [
        {
          "id": "117497",
          "type": "log",
          "attributes": {
            "content": {
              "context": {
                "id": "433"
              },
              "diff": {
                "state": {
                  "old": 0,
                  "new": 7
                }
              }
            }
          }
        }
      ]
    }
  }
]
```

### Differences par entite

| Champ | Positionnement | Candidat | Ressource |
|-------|---------------|----------|-----------|
| `dependsOn.type` | `"positioning"` | `"candidate"` | `"resource"` |
| `dependsOn.id` | ID positionnement | ID candidat | ID ressource |
| `diff.state.new` | 7 | 11 | 4 ou 5 |

### Cle d'idempotence

| Webhook | Format cle |
|---------|-----------|
| Positionnement | `positioning_update_{positioningId}_{state}` |
| Candidat | `candidate_state_{candidateId}_{state}` |
| Ressource | `resource_state_{resourceId}_{state}` |

---

## Verification

Apres configuration, tester chaque webhook :

1. **Candidat state 11** : Passer un candidat en "En attente de contrat" dans Boond. Verifier qu'une demande de contrat apparait dans Bobby (`/contracts`).
2. **Ressource state 4** : Passer une ressource en "Attente nouveau contrat". Verifier la creation avec `trigger_type=ressource_4`.
3. **Ressource state 5** : Passer une ressource en "Changement de contrat". Verifier la creation avec `trigger_type=ressource_5`.

### Endpoint de debug (dev/staging uniquement)

```
GET /api/v1/webhooks/boondmanager/debug-cr
```

Retourne les 10 dernieres demandes de contrat avec leurs references, statuts et triggers.
