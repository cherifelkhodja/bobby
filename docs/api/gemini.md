# Google Gemini AI Integration

Documentation de l'intégration Google Gemini pour Bobby.

---

## Vue d'ensemble

Google Gemini est utilisé pour 3 fonctionnalités IA :
1. **CV Transformer** : Extraction et parsing de CV
2. **Anonymizer** : Anonymisation des opportunités
3. **Matcher** : Calcul de score de correspondance CV/offre

---

## Configuration

### Variable d'environnement

```bash
GEMINI_API_KEY=your-gemini-api-key
```

### SDK utilisé

```python
# Actuellement (deprecated)
import google.generativeai as genai

# Cible migration
from google import genai  # google-genai package
```

> ⚠️ **Dette technique** : Migration `google-generativeai` → `google-genai` en cours.
> Voir https://github.com/google-gemini/deprecated-generative-ai-python

---

## 1. CV Transformer

**Fichier** : `backend/app/infrastructure/cv_transformer/gemini_client.py`

### Fonctionnalité

Extrait les données structurées d'un CV (texte brut) vers un format JSON.

### Prompt principal

Le prompt demande à Gemini d'extraire :
- Profil (titre, années d'expérience)
- Compétences techniques (catégorisées)
- Formations (diplômes, certifications)
- Expériences professionnelles (client, période, titre, contexte, environnement technique)
- Langues

### Utilisation

```python
from app.infrastructure.cv_transformer.gemini_client import GeminiClient

client = GeminiClient(api_key=settings.gemini_api_key)
parsed_cv = await client.parse_cv(cv_text)
```

### Sortie JSON attendue

```json
{
  "profil": {
    "titre_cible": "Développeur Full Stack",
    "annees_experience": 5
  },
  "resume_competences": {
    "techniques_list": [
      {"categorie": "Backend", "valeurs": "Python, FastAPI, Django"},
      {"categorie": "Frontend", "valeurs": "React, TypeScript"}
    ]
  },
  "formations": {
    "diplomes": [
      {"annee": "2018", "intitule": "Master Informatique", "etablissement": "Université Paris"}
    ],
    "certifications": [
      {"annee": "2022", "intitule": "AWS Solutions Architect"}
    ]
  },
  "experiences": [
    {
      "client": "Banque XYZ",
      "periode": "2022-2024",
      "titre": "Tech Lead",
      "contexte": "Refonte du système de paiement...",
      "environnement_technique": "Python, FastAPI, PostgreSQL, Docker"
    }
  ],
  "langues": [
    {"langue": "Français", "niveau": "Natif"},
    {"langue": "Anglais", "niveau": "Courant"}
  ]
}
```

---

## 2. Anonymizer

**Fichier** : `backend/app/infrastructure/anonymizer/gemini_anonymizer.py`

### Fonctionnalité

Anonymise les opportunités BoondManager avant publication pour cooptation.

### Règles d'anonymisation

| Élément | Traitement |
|---------|------------|
| Noms de clients | → Descriptions génériques ("Grand compte bancaire") |
| Noms de projets internes | → Descriptions génériques |
| Compétences techniques | Préservées |
| Méthodologies | Préservées |
| Durée, niveau d'expérience | Préservés |
| Formatting (bullets, paragraphes) | Préservé |

### Utilisation

```python
from app.infrastructure.anonymizer.gemini_anonymizer import GeminiAnonymizer

anonymizer = GeminiAnonymizer(api_key=settings.gemini_api_key)
result = await anonymizer.anonymize(
    title=opportunity.title,
    description=opportunity.description,
)
# result.anonymized_title, result.anonymized_description, result.skills
```

### Extraction des compétences

Le prompt extrait également les compétences clés de l'opportunité sous forme de liste.

---

## 3. Matcher

**Fichier** : `backend/app/infrastructure/matching/gemini_matcher.py`

### Fonctionnalité

Calcule un score de correspondance entre un CV et une offre d'emploi.

### Utilisation

```python
from app.infrastructure.matching.gemini_matcher import GeminiMatcher

matcher = GeminiMatcher(api_key=settings.gemini_api_key)
result = await matcher.calculate_match(
    cv_text=application.cv_text,
    job_description=job_posting.description,
    job_qualifications=job_posting.qualifications,
)
```

### Sortie

```python
@dataclass
class MatchingResult:
    score: int           # 0-100
    strengths: list[str] # Points forts du candidat
    gaps: list[str]      # Lacunes identifiées
    summary: str         # Résumé de l'évaluation
```

### Affichage des scores

| Score | Couleur | Interprétation |
|-------|---------|----------------|
| ≥80% | 🟢 Vert | Excellent match |
| 50-79% | 🟠 Orange | Potentiel |
| <50% | 🔴 Rouge | Faible correspondance |

---

## Modèle utilisé

```python
# Configuration par défaut
model = genai.GenerativeModel('gemini-1.5-flash')

# Configurable via Admin panel
# GET /api/v1/admin/gemini/settings
# POST /api/v1/admin/gemini/settings
```

---

## Rate Limiting

Les appels Gemini sont limités côté Bobby :
- CV Transform : 10/heure par utilisateur
- Autres appels : inclus dans le rate limit général API

---

## Tests

```python
# Test de connectivité Gemini
GET /api/v1/admin/gemini/test

# Test CV Transform
GET /api/v1/cv-transformer/test-gemini
```

---

## Migration vers google-genai

### Changements à effectuer

```python
# Avant (deprecated)
import google.generativeai as genai
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content(prompt)

# Après (nouveau SDK)
from google import genai
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model='gemini-1.5-flash',
    contents=prompt,
)
```

### Fichiers à migrer

1. `backend/app/infrastructure/cv_transformer/gemini_client.py`
2. `backend/app/infrastructure/anonymizer/gemini_anonymizer.py`
3. `backend/app/infrastructure/matching/gemini_matcher.py`
