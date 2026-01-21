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

## Changelog

> ⚠️ **OBLIGATOIRE** : Mettre à jour cette section après chaque modification significative.

### 2026-01-21
- Setup système de documentation (MEMORY.md, docs/skills, docs/api)

### 2026-01-19
- Mise à jour documentation CLAUDE.md

### 2026-01-18
- Security hardening : rate limiting, security headers, RLS, audit logging

### 2026-01-17
- HR : Listing opportunités depuis Boond API
- Tests complets feature HR

### 2026-01-15
- Feature opportunités publiées avec anonymisation IA
- Fixes quotation generator

### 2026-01-14
- Support numéro téléphone
- Filtre état ressources Boond
- Delete user functionality

### 2026-01-13
- CV Transformer feature
- Dark mode
- Rôle RH créé
