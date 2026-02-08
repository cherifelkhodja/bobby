# 🔧 Auto-Healer History

Historique des corrections automatiques effectuées par le Railway Healer.

> Ce fichier est mis à jour automatiquement à chaque intervention du healer.
> Ne pas modifier manuellement.

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

