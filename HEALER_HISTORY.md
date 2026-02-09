# 🔧 Auto-Healer History

Historique des corrections automatiques effectuées par le Railway Healer.

> Ce fichier est mis à jour automatiquement à chaque intervention du healer.
> Ne pas modifier manuellement.

---
## 📅 08/02/2026 19:28:28

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

