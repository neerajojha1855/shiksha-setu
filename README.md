# Shiksha Setu

Shiksha Setu connects under-resourced schools with donors, volunteers, and verified education-support programs.

This repository currently contains the Week 1 foundation and D6 authentication:

- `frontend/`: React, Vite, and TypeScript client
- `backend/`: FastAPI service with SQLAlchemy, Alembic, and Neon PostgreSQL configuration
- `SHIKSHA_SETU_IMPLEMENTATION_PLAN.md`: product scope and 30-day delivery plan

## Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer
- A Neon PostgreSQL database for database readiness and migrations

## Backend setup

```sh
cd backend

python -m venv .venv
source .venv/Scripts/activate

pip install -r requirements.txt

cp .env.example .env
```

Set `DATABASE_URL` in `backend/.env` to Neon's pooled runtime connection string. Set `DIRECT_DATABASE_URL` to Neon's direct connection string for migrations when available. Both values must include SSL parameters.

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Run migrations:

```bash
alembic upgrade head
```

API endpoints:

- `GET http://localhost:8000/health` — liveness check
- `GET http://localhost:8000/ready` — application and database readiness
- `GET http://localhost:8000/docs` — FastAPI OpenAPI documentation

Authentication endpoints:

- `POST /api/auth/register` — create a donor, school, or volunteer account
- `POST /api/auth/login` — authenticate by email or username
- `POST /api/auth/refresh` — rotate a refresh token and issue new tokens
- `POST /api/auth/logout` — revoke a refresh session
- `GET /api/auth/me` — return the authenticated user

Use a long random `JWT_SECRET_KEY` in non-development environments. Access tokens are short-lived JWTs; refresh tokens are opaque, rotated, revocable values whose hashes are stored in PostgreSQL. Administrator accounts must be provisioned by an administrator rather than through public registration.

## Frontend setup

```bash
cd frontend
npm install

cp .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL` to the backend URL if it is not `http://localhost:8000`.

Available frontend commands:

```bash
npm run dev
npm run build
npm run lint
```

## Backend checks

From `backend/`:

```bash
pytest
pytest tests/test_health.py -q
```

The backend auth tests use an isolated in-memory database. Database integration checks use the configured Neon database through Alembic and the readiness endpoint.

## Development data and credentials

Do not commit `.env` files, Neon credentials, API keys, or real student information. Any future seed data must be explicitly labeled as fictional.