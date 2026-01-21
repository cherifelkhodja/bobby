# Bobby - Mémoire du Projet

> Ce fichier contient l'historique, les décisions et l'état du projet.
> **Claude doit le consulter avant chaque tâche et le mettre à jour après chaque modification significative.**

---

## Résumé du projet

**Bobby** est une application de cooptation pour Gemini Consulting (ESN) avec intégration BoondManager.

### Stack technique
- **Backend** : Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL, Redis
- **Frontend** : React 18, TypeScript, Vite, TailwindCSS, Zustand
- **IA** : Google Gemini (transformation CV, anonymisation, matching)
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
| CV Transformer | ✅ Done | PDF/DOCX → Word avec Gemini |
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
- **Décision** : Utiliser Google Gemini pour transformation CV, anonymisation, matching
- **Raison** : Coût, qualité, facilité d'intégration

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

### 2026-01-21
- Setup système de documentation (MEMORY.md, docs/skills, docs/api)

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
