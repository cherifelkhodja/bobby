# 🔧 Auto-Healer History

Historique des corrections automatiques effectuées par le Railway Healer.

> Ce fichier est mis à jour automatiquement à chaque intervention du healer.
> Ne pas modifier manuellement.

---
## 📅 09/02/2026 — Auto-Heal #4 : dataclass field ordering

| | |
|---|---|
| **Service** | backend |
| **Environment** | production |
| **Status** | ✅ Réparé |

### Erreur détectée
```
TypeError: non-default argument 'availability' follows default argument
  File "/app/app/application/use_cases/job_applications.py", line 40, in SubmitApplicationCommand
```

### Analyse
Dans le dataclass `SubmitApplicationCommand`, le champ `civility: Optional[str] = None` avait une valeur par défaut, mais les champs suivants (`availability`, `employment_status`, `english_level`, `tjm_current`, etc.) n'en avaient pas. Python interdit les champs sans défaut après un champ avec défaut → `TypeError` au chargement du module → uvicorn crash → healthcheck timeout → déploiement échoué.

### Correction appliquée
Réorganisation des champs : champs requis sans défaut placés avant les champs optionnels. Ajout de `= None` aux champs `Optional[float]`. Tous les appelants utilisent des keyword arguments → pas d'impact.

### Commit
*(voir ci-dessous)*

---
## 📅 09/02/2026 — Crash #3 : Docker cache périmé

| | |
|---|---|
| **Service** | backend |
| **Environment** | production |
| **Status** | ✅ Réparé (intervention manuelle) |

### Erreur détectée
```
Container failed to start
(toutes les layers Docker "cached" y compris COPY . .)
```

### Analyse
Malgré les commits de fix poussés sur `origin/main`, Railway servait un cache Docker périmé. Le layer `COPY . .` restait "cached", donc le container démarrait avec l'ancien code (migration 019 cassée). Le healer auto a tenté 5 corrections sans succès car le problème était côté build, pas côté code. De plus, le healer a corrompu le git staging area (tous les fichiers marqués "deleted").

### Correction appliquée
- Ajout `ARG CACHEBUST=1` avant `COPY . .` dans le Dockerfile pour casser le cache Docker
- Conversion `CMD` en format JSON (corrige warning `JSONArgsRecommended`)
- Nettoyage migration 019 : constructeurs `sa.Text()` / `sa.DateTime()` avec parenthèses
- `git reset HEAD` pour réparer le staging area corrompu

### Commit
`b3447d7`

---
## 📅 09/02/2026 — Crash #2 : Alembic revision chain cassée

| | |
|---|---|
| **Service** | backend |
| **Environment** | production |
| **Status** | ✅ Réparé (healer auto) |

### Erreur détectée
```
KeyError: '018'
UserWarning: Revision 018 referenced from 018 -> 019 (head),
Add civility and Boond sync tracking fields to job_applications. is not present
```

### Analyse
Migration `019_add_civility_and_boond_sync.py` avait `down_revision = '018'` (ID court) au lieu de `down_revision = '018_simplify_application_status'` (ID complet). Alembic ne pouvait pas résoudre la chaîne de révisions → `KeyError: '018'` → `alembic upgrade head` échoue → app ne démarre pas → 5 déploiements échoués consécutifs.

### Correction appliquée
Fix des revision IDs : `revision = '019_add_civility_and_boond_sync'` et `down_revision = '018_simplify_application_status'`.

### Commit
`79a75a9`

---

## 📅 08/02/2026 18:35:00

| | |
|---|---|
| **Service** | backend + frontend |
| **Environment** | production |
| **Status** | ✅ Réparé (intervention manuelle) |

### Erreur détectée
```
Backend: Healthcheck /api/v1/health/live timeout (1m40s) — le service ne démarre jamais
Frontend: Build failed — 14 erreurs TypeScript dans src/pages/admin/ApiTab.tsx
```

### Analyse
Le commit `4a9a290` (feat: add Claude Sonnet 4.5 as alternative AI provider) a ajouté `anthropic>=0.40.0` dans `pyproject.toml` mais pas dans le Dockerfile (qui utilise une liste `pip install` manuelle). L'import `anthropic` échouait au démarrage → app ne démarre jamais → healthcheck timeout. Côté frontend, le même commit introduisait des erreurs TS : `useQuery` non typé (`as any`), `onSuccess` deprecated (React Query v5), `Badge variant="info"` inexistant, paramètres implicitement `any`. En bonus, un import circulaire `Admin.tsx` → `./admin` sur macOS (case-insensitive FS) cassait aussi le build Vite.

Le healer auto n'a pas pu intervenir car **Tailscale Funnel était désactivé** — les webhooks Railway n'atteignaient pas le serveur healer. Funnel réactivé dans la foulée.

### Correction appliquée
- `backend/Dockerfile` : ajout `"anthropic>=0.40.0"` dans la liste pip install
- `frontend/src/pages/admin/ApiTab.tsx` : typage `useQuery<CvAiSettings>`, remplacement `onSuccess` par `useEffect`, suppression variables inutilisées, types explicites, `variant="primary"`
- `frontend/src/components/ui/Badge.tsx` : ajout prop `className`
- `frontend/src/pages/Admin.tsx` : import `./admin/index` au lieu de `./admin`

### Commit
`80904b6`

---
## 📅 08/02/2026 14:30:00

| | |
|---|---|
| **Service** | bobby-backend |
| **Environment** | production |
| **Status** | ✅ Réparé |

### Erreur détectée
```
FutureWarning: All support for the `google.generativeai` package has ended.
/app/app/infrastructure/matching/gemini_matcher.py:12: FutureWarning
```

### Analyse
Le package `google-generativeai` (deprecated) emet un `FutureWarning` a chaque demarrage de worker uvicorn. Ce warning est emis 2x (1 par worker) et pollue les logs de production. Le package est utilise dans 6 fichiers (gemini_matcher.py, gemini_client.py, gemini_anonymizer.py, job_posting_anonymizer.py, settings.py, cv_transformer.py). Une migration complete vers `google.genai` est necessaire a terme mais represente un changement majeur (nouvelle API surface). Fix minimal applique : suppression du FutureWarning via `warnings.filterwarnings` dans main.py.

### Correction appliquée
Ajout d'un filtre `warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")` dans `backend/app/main.py` pour supprimer le FutureWarning en production. TODO ajoute pour migration vers `google.genai`.

### Commit
`auto-heal-suppress-gemini-futurewarning`

---

## 📅 08/02/2026 13:56:54

| | |
|---|---|
| **Service** | bobby-backend |
| **Environment** | production |
| **Status** | ❌ Échec |

### Erreur détectée
```
Voir logs complets
```

### Analyse
Analyse automatique par Claude

### Correction appliquée
Correction automatique appliquée

### Commit
Aucun commit

---

## 📅 08/02/2026 13:37:48

| | |
|---|---|
| **Service** | bobby-backend |
| **Environment** | production |
| **Status** | ❌ Échec |

### Erreur détectée
```
Voir logs complets
```

### Analyse
Analyse automatique par Claude

### Correction appliquée
Correction automatique appliquée

### Commit
Aucun commit

---

## 📅 08/02/2026 13:37:48

| | |
|---|---|
| **Service** | unknown |
| **Environment** | production |
| **Status** | ❌ Échec |

### Erreur détectée
```
Voir logs complets
```

### Analyse
Analyse automatique par Claude

### Correction appliquée
Correction automatique appliquée

### Commit
Aucun commit

---

## 📅 08/02/2026 13:28:40

| | |
|---|---|
| **Service** | test-service |
| **Environment** | test |
| **Status** | ✅ Réparé |

### Erreur détectée
```
Test error simulation
```

### Analyse
Ceci est un test du système de healer

### Correction appliquée
Aucune correction (test)

### Commit
`test-000`

---

## 📅 08/02/2026 13:28:27

| | |
|---|---|
| **Service** | test-service |
| **Environment** | test |
| **Status** | ✅ Réparé |

### Erreur détectée
```
Test error simulation
```

### Analyse
Ceci est un test du système de healer

### Correction appliquée
Aucune correction (test)

### Commit
`test-000`

---

## 📅 08/02/2026 13:12:13

| | |
|---|---|
| **Service** | test-service |
| **Environment** | test |
| **Status** | ✅ Réparé |

### Erreur détectée
```
Test error simulation
```

### Analyse
Ceci est un test du système de healer

### Correction appliquée
Aucune correction (test)

### Commit
`test-000`

---

## 📅 08/02/2026 12:57:24

| | |
|---|---|
| **Service** | test-service |
| **Environment** | test |
| **Status** | ✅ Réparé |

### Erreur détectée
```
Test error simulation
```

### Analyse
Ceci est un test du système de healer

### Correction appliquée
Aucune correction (test)

### Commit
`test-000`

---

