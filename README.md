# Bobby

Application web de cooptation permettant aux collaborateurs de l'ESN de proposer des profils candidats sur les opportunites/besoins en cours.

## Stack Technique

### Backend
- Python 3.12+
- FastAPI
- SQLAlchemy 2.0 (async)
- Alembic
- PostgreSQL 16
- Redis 7

### Frontend
- React 18
- TypeScript (strict)
- Vite
- TailwindCSS
- React Query
- Zustand

### Infrastructure
- Docker + Docker Compose
- GitHub Actions (CI/CD)

## Demarrage Rapide

### Prerequis
- Docker et Docker Compose
- macOS Apple Silicon (arm64) ou Linux

### Installation

1. Cloner le repository
```bash
git clone <repository-url>
cd bobby
```

2. Copier le fichier d'environnement
```bash
cp .env.example .env
```

3. Demarrer les services
```bash
make build
make up
```

4. Executer les migrations
```bash
make migrate
```

5. Acceder a l'application
- Frontend: http://localhost:3012
- Backend API: http://localhost:8012
- API Docs: http://localhost:8012/api/docs
- Mailhog: http://localhost:8025

### Compte Admin par defaut (dev)
- Email: cherif.elkhodja@geminiconsulting.fr
- Password: Admin@2024!

## Commandes Make

```bash
make help           # Afficher l'aide
make build          # Build les containers
make up             # Demarrer les services
make down           # Arreter les services
make logs           # Voir les logs
make test           # Lancer les tests backend
make lint           # Linter le code
make format         # Formater le code
make migrate        # Executer les migrations
make ci             # Simuler la CI localement
make fresh          # Reinstallation complete
```

## Structure du Projet

```
bobby/
├── backend/
│   ├── app/
│   │   ├── domain/          # Logique metier
│   │   ├── application/     # Use cases
│   │   ├── infrastructure/  # Implementations
│   │   └── api/            # Routes FastAPI
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/            # Clients API
│       ├── components/     # Composants UI
│       ├── pages/          # Pages
│       └── stores/         # State management
├── docker-compose.yml
├── Makefile
└── MEMORY.md               # Journal de dev
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Inscription
- `POST /api/v1/auth/login` - Connexion
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/forgot-password` - Reset password
- `POST /api/v1/auth/verify-email` - Verification email

### Users
- `GET /api/v1/users/me` - Profil utilisateur
- `PATCH /api/v1/users/me` - Mise a jour profil
- `POST /api/v1/users/me/password` - Changement mot de passe

### Opportunities
- `GET /api/v1/opportunities` - Liste des opportunites
- `GET /api/v1/opportunities/{id}` - Detail opportunite
- `POST /api/v1/opportunities/sync` - Sync BoondManager

### Cooptations
- `POST /api/v1/cooptations` - Creer cooptation
- `GET /api/v1/cooptations` - Liste (admin)
- `GET /api/v1/cooptations/me` - Mes cooptations
- `GET /api/v1/cooptations/me/stats` - Mes statistiques
- `GET /api/v1/cooptations/{id}` - Detail cooptation
- `PATCH /api/v1/cooptations/{id}/status` - Maj statut (admin)

### Health
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe

## Tests

```bash
# Backend
make test           # Tous les tests
make test-unit      # Tests unitaires
make test-cov       # Avec coverage

# Frontend
make test-frontend
```

## License

Proprietary - Bobby Consulting
