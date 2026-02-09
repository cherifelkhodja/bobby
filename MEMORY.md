# Bobby - Mémoire du Projet

> Ce fichier contient l'historique, les décisions et l'état du projet.
> **Claude doit le consulter avant chaque tâche et le mettre à jour après chaque modification significative.**

---

## Résumé du projet

**Bobby** est une application de cooptation pour Gemini Consulting (ESN) avec intégration BoondManager.

### Stack technique
- **Backend** : Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL, Redis
- **Frontend** : React 18, TypeScript, Vite, TailwindCSS, Zustand
- **IA** : Google Gemini (anonymisation, matching) + Claude Sonnet 4.5 / Gemini (transformation CV, configurable)
- **Déploiement** : Railway (Docker)

---

## État actuel des fonctionnalités

| Fonctionnalité | Status | Notes |
|----------------|--------|-------|
| Auth JWT (access + refresh) | ✅ Done | Password reset, email verification |
| Intégration BoondManager | ✅ Done | Resources, opportunities, candidates |
| Système d'invitations | ✅ Done | Depuis ressources Boond |
| Panel Admin | ✅ Done | Users, invitations, Boond, templates |
| Dark Mode | ✅ Done | System/Light/Dark |
| CV Transformer | ✅ Done | PDF/DOCX → Word, multi-provider (Gemini/Claude) |
| Opportunités publiées | ✅ Done | Anonymisation IA |
| Quotation Generator (Thales) | ✅ Done | Excel + PDF merge |
| Recrutement RH | ✅ Done | Turnover-IT, matching IA |
| Rate Limiting | ✅ Done | Redis + slowapi |
| Security Headers | ✅ Done | HSTS, CSP, etc. |
| Row Level Security | ✅ Done | PostgreSQL RLS |
| Audit Logging | ✅ Done | Structuré |

---

## Décisions techniques (ADRs)

### ADR-001 : Architecture Hexagonale
- **Date** : 2024-12
- **Décision** : Adopter l'architecture hexagonale (ports/adapters)
- **Raison** : Séparation claire domain/infra, testabilité, flexibilité
- **Structure** : domain/ → application/ → infrastructure/ → api/

### ADR-002 : SQLAlchemy Async
- **Date** : 2024-12
- **Décision** : Utiliser SQLAlchemy 2.0 en mode async avec asyncpg
- **Raison** : Performance, cohérence avec FastAPI async

### ADR-003 : Google Gemini pour l'IA
- **Date** : 2024-12
- **Décision** : Utiliser Google Gemini pour anonymisation et matching
- **Raison** : Coût, qualité, facilité d'intégration

### ADR-006 : Multi-provider IA pour CV Transformer (Gemini + Claude)
- **Date** : 2026-02
- **Décision** : Permettre le choix entre Gemini et Claude Sonnet 4.5 pour la transformation CV
- **Raison** : Claude Sonnet 4.5 produit des résultats plus fidèles (dates correctes, pas d'invention, meilleure extraction)
- **Architecture** : Port `CvDataExtractorPort` avec 2 adapters (`GeminiClient`, `AnthropicClient`), sélection runtime via `app_settings`
- **Prompt** : v5 optimisé pour extraction fidèle ("reproduire exactement", pas de transformation)

### ADR-004 : JWT avec Refresh Token
- **Date** : 2025-01
- **Décision** : Access token 30min, refresh token 7 jours
- **Raison** : Sécurité + UX (pas de re-login fréquent)

### ADR-005 : Turnover-IT pour le recrutement
- **Date** : 2025-01
- **Décision** : Intégrer JobConnect v2 pour publier les offres
- **Raison** : Visibilité sur Free-Work, intégration existante Gemini

---

## Problèmes connus

| Problème | Impact | Workaround | Priorité |
|----------|--------|------------|----------|
| Rate limit Boond non documenté | Faible | Retry avec backoff | Low |
| Gemini SDK deprecated | Medium | Fonctionne encore | Medium |

---

## Dette technique

| Élément | Description | Priorité |
|---------|-------------|----------|
| Google Gemini SDK | Migration `google-generativeai` → `google-genai` | Medium |
| Tests E2E | Couverture à améliorer | Medium |

### Détails dette Gemini SDK
- **Current** : `google-generativeai` (deprecated)
- **Target** : `google-genai`
- **Fichiers à migrer** :
  - `backend/app/infrastructure/cv_transformer/gemini_client.py`
  - `backend/app/infrastructure/anonymizer/gemini_anonymizer.py`
  - `backend/app/infrastructure/matching/gemini_matcher.py`
- **Référence** : https://github.com/google-gemini/deprecated-generative-ai-python

---

## Prochaines étapes

- [ ] Migration SDK Gemini
- [ ] Améliorer couverture tests E2E
- [ ] Dashboard analytics cooptations
- [ ] Notifications push

---

## Commandes utiles

```bash
# Backend
cd backend
make dev          # Start dev server
make test         # Run tests
make lint         # Run linters
make migrate      # Run migrations
make seed         # Seed admin user

# Frontend
cd frontend
npm run dev       # Start dev server
npm run build     # Build production
npm run test      # Run tests
npm run lint      # Run linters

# Docker
make fresh        # Clean restart
make ci           # Simulate CI locally
docker-compose up # Start all services
```

---

## Changelog

> ⚠️ **OBLIGATOIRE** : Mettre à jour cette section après chaque modification significative.

### 2026-02-09
- **fix(ci)**: Amélioration résilience workflow GitHub Actions
  - Ajout `concurrency` group pour annuler les runs CI redondants
  - Ajout `timeout-minutes` sur tous les jobs (15min backend/docker, 10min frontend)
  - `fetch-depth: 1` explicite pour shallow clones plus rapides
  - `npm ci` au lieu de `npm install` pour builds reproductibles
  - Contexte : erreurs transitoires HTTP 500/502 de GitHub sur `actions/checkout@v4`

### 2026-02-08
- **feat(cv-transformer)**: Intégration Claude Sonnet 4.5 comme provider IA alternatif
  - Nouveau client `AnthropicClient` implémentant `CvDataExtractorPort` (architecture hexagonale)
  - Prompt v5 optimisé pour extraction fidèle des données CV
  - Sélection dynamique du provider (Gemini/Claude) depuis l'admin panel
  - 3 nouveaux endpoints admin : `GET/POST /admin/cv-ai/settings`, `POST /admin/cv-ai/test`
  - Interface admin : carte "IA pour Transformation CV" avec sélecteur provider/modèle + test
  - Settings DB : `cv_ai_provider`, `cv_ai_model_claude`
  - Modèles disponibles : Claude Sonnet 4.5 (recommandé), Claude Haiku 4.5 (rapide)
  - Dépendance ajoutée : `anthropic>=0.40.0`
  - Fichiers créés : `anthropic_client.py`
  - Fichiers modifiés : `config.py`, `pyproject.toml`, `app_settings_service.py`, `cv_transformer.py` (route), `admin.py` (route + schemas), `ApiTab.tsx`, `admin.ts`

### 2026-01-21
- **feat(hr)**: Statut professionnel dynamique selon type de contrat
  - Checkboxes au lieu de dropdown pour le statut professionnel (Freelance / Salarié)
  - Affichage conditionnel selon les types de contrat de l'annonce :
    - CDI/CDD → seulement "Salarié" disponible
    - Freelance/Intercontrat → seulement "Freelance" disponible
    - Mixte → les deux options disponibles
  - Possibilité de cocher les deux statuts simultanément
  - Stockage en format comma-separated ("freelance", "employee", "freelance,employee")
  - Filtre RH mis à jour pour recherche partielle (LIKE)
  - Fichiers modifiés : `PublicApplication.tsx`, `JobPostingDetails.tsx`, `job_application.py`, `job_application_repository.py`
- **feat(hr)**: Évaluation qualité CV (/20) - indépendante de l'offre
  - Score global /20 avec classification (EXCELLENT/BON/MOYEN/FAIBLE)
  - Détection automatique niveau expérience (JUNIOR/CONFIRME/SENIOR)
  - Critères d'évaluation :
    - Stabilité des missions (/8) : durée moyenne, cohérence
    - Qualité des comptes (/6) : grands comptes CAC40, éditeurs logiciels, ESN
    - Parcours scolaire (/2, /4 ou /6 selon niveau) : écoles d'ingénieurs, universités
    - Continuité parcours (/4) : trous dans le CV
    - Bonus/malus (-1 à +1) : certifications, contributions, qualité rédaction
  - Exécution en parallèle avec le matching offre (asyncio.gather)
  - Migration 017 : colonnes `cv_quality_score` et `cv_quality` (JSON)
  - Fichiers modifiés : `gemini_matcher.py`, `job_applications.py`, `job_application_repository.py`, `hr.py` (read_models), `job_application.py` (entity), `models.py`, `types/index.ts`
- **feat(hr)**: Système de matching CV-offre amélioré
  - Nouvelle configuration Gemini (temperature 0.1 pour des résultats plus cohérents)
  - Prompt enrichi avec critères pondérés : techniques (40%), expérience (25%), formation (15%), soft skills (20%)
  - Réponse JSON native (`response_mime_type: application/json`)
  - Scores détaillés par catégorie dans `scores_details`
  - Nouvelles infos : `competences_matchees`, `competences_manquantes`, `points_forts`, `points_vigilance`
  - Recommandation avec niveau (fort/moyen/faible) et action suggérée
  - Inclusion des infos candidat (poste, TJM, disponibilité) dans l'analyse
  - Rétrocompatibilité complète avec l'ancien format
  - Fichiers modifiés : `gemini_matcher.py`, `job_applications.py`, `hr.py` (read_models), `types/index.ts`
- **fix(ui)**: Correction superposition filtres avec z-index et overflow
  - Création classe CSS `.filter-select` pour styling cohérent des dropdowns
  - Fichiers modifiés : `JobPostingDetails.tsx`, `index.css`
- **feat(hr)**: 4 modes d'affichage pour les détails candidature
  - Modal (défaut), Drawer (panneau latéral), Split view (écran divisé), Inline (expansion dans le tableau)
  - Sélecteur de mode avec icônes
  - Composant `ApplicationDetailContent` réutilisable
  - Fichier modifié : `JobPostingDetails.tsx`
- **feat(hr)**: Filtres et tri pour les candidatures
  - Filtres: statut application, statut professionnel (freelance/salarié/les deux), disponibilité
  - Tri: score matching, TJM, salaire, date de candidature (asc/desc)
  - Harmonisation styles table avec HRDashboard (text-xs, padding compact)
  - Fichiers modifiés : `job_application_repository.py`, `job_applications.py`, `hr.py`, `hr.ts`, `JobPostingDetails.tsx`
- **feat(hr)**: Renommage CV au format "Prenom NOM - date.ext"
  - Nom de fichier propre pour téléchargement (ex: "Jean DUPONT - 20260121.pdf")
- **feat(hr)**: Gestion automatique du statut "nouveau"
  - Auto-transition vers "en_cours" quand le RH ouvre le détail d'une candidature
  - Bouton "Marquer comme vu" (✓) dans la liste pour les candidatures nouvelles
  - Paramètre API `mark_viewed` pour contrôler le comportement
- **feat(hr)**: Cache local des réponses du formulaire de candidature (48h)
  - Sauvegarde automatique dans localStorage à chaque modification
  - Restauration des données si l'utilisateur revient dans les 48h
  - Effacement du cache après soumission réussie
  - Indicateur visuel de restauration des données
  - Fichier modifié : `PublicApplication.tsx`
- **feat(hr)**: Bouton "Modifier" pour les annonces d'emploi (tous statuts)
  - Permet d'éditer les annonces publiées avec synchronisation automatique vers Turnover-IT
  - Fichiers modifiés : `JobPostingDetails.tsx`, `EditJobPosting.tsx`, `job_postings.py` (use case), `hr.py` (route)
- **feat(hr)**: Formulaire de candidature enrichi avec nouveaux champs
  - Téléphone international avec sélecteur de pays (react-phone-number-input)
  - Disponibilité en dropdown (ASAP, Sous 1/2/3 mois, Plus de 3 mois)
  - Statut professionnel (Freelance, Salarié, Les deux)
  - Champs TJM/Salaire conditionnels selon le statut
  - Niveau d'anglais avec descriptions (Notions → Bilingue C2)
  - CV max 10 Mo, formats PDF/Word
  - Migration 016 : nouveaux champs `availability`, `employment_status`, `english_level`, `tjm_current`, `tjm_desired`, `salary_current`, `salary_desired`
  - Fichiers modifiés : `PublicApplication.tsx`, `hr.ts`, `public_applications.py`, `job_applications.py` (use case + entity), `job_application_repository.py`, `models.py`
- **fix(turnoverit)**: Correction types de contrat - `TEMPORARY` → `FIXED-TERM` (seule valeur CDD acceptée par API)
  - Fichiers modifiés : `CreateJobPosting.tsx`, `EditJobPosting.tsx`, `job_posting.py`, `turnoverit.md`
  - Suppression des types non valides : INTERNSHIP, APPRENTICESHIP
  - Valeurs valides API : PERMANENT, FIXED-TERM, FREELANCE, INTERCONTRACT
- Setup système de documentation (MEMORY.md, docs/skills, docs/api)
- Allègement CLAUDE.md (-112 lignes) : déport des infos dupliquées vers fichiers spécialisés
- Création docs/api/gemini.md (CV parsing, anonymisation, matching)
- Mise à jour docs/api/turnoverit.md avec documentation officielle JobConnect v2 + webhook + réponse API réelle
- Ajout documentation AWS Secrets Manager dans docs/skills/quality-security.md

### 2026-01-19
- Mise à jour documentation CLAUDE.md

### 2026-01-18
**Security Hardening Implementation**
- Rate limiting avec slowapi + Redis backend
- Security headers middleware (HSTS, CSP, X-Frame-Options, etc.)
- Row Level Security (RLS) sur tables PostgreSQL
- Audit logging structuré pour événements sécurité

**Fichiers créés** :
- `backend/app/api/middleware/rate_limiter.py`
- `backend/app/api/middleware/security_headers.py`
- `backend/app/api/middleware/rls_context.py`
- `backend/app/infrastructure/audit/logger.py`
- Migrations : `010_add_row_level_security.py`, `011-013_turnoverit_skills_and_settings.py`

### 2026-01-17
**HR Opportunities from BoondManager**
- Listing opportunités HR depuis API BoondManager (Admin: ALL, RH: HR manager filtered)
- Affichage état Boond avec badges colorés
- Batch lookup efficace pour statut job postings

**HR Feature Review & Quality**
- Tests backend complets
- Tests frontend
- Tests E2E
- Mise à jour dépendances

### 2026-01-15
**Published Opportunities Feature**
- Migration table `published_opportunities`
- Anonymisation IA avec Gemini
- Page détail dédiée
- Support cooptation depuis page détail

**Quotation Generator Fixes**
- Fix sérialisation Redis
- Fix collision PDF template
- Fix garbage collection background tasks
- Fonctionnalité delete quotation

### 2026-01-14
- Support numéro téléphone (users + invitations)
- Modal détails utilisateur dans Admin
- Fix CV Transformer préfixe "none:"
- Filtre état ressources BoondManager
- Fonctionnalité delete user

### 2026-01-13
**CV Transformer Feature**
- Upload CV (PDF/DOCX)
- Extraction avec Gemini AI
- Génération Word formaté avec templates

**Autres**
- Endpoint ressources BoondManager
- Redesign InvitationsTab
- Dark mode (System/Light/Dark)
- Création rôle `rh`

### 2026-01-12 (Création initiale)
- Structure projet complète (backend + frontend)
- Configuration Docker (docker-compose, Dockerfiles)
- Backend FastAPI avec architecture Domain-Driven
  - Domain layer (entités, value objects, exceptions, ports)
  - Infrastructure layer (database, security, boond, cache, email)
  - Application layer (use cases, read models)
  - API layer (routes v1, schemas, middleware)
- Frontend React/TypeScript avec Vite
  - Composants UI (Button, Input, Modal, Card, Badge, Spinner)
  - Pages (Login, Register, Dashboard, Opportunities, MyCooptations, Profile)
  - State management Zustand + React Query
- CI/CD GitHub Actions
- Tests backend (structure et fixtures)
