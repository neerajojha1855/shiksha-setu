# Shiksha Setu

Shiksha Setu connects under-resourced schools with donors, volunteers, and verified education-support programs.

This repository currently contains the Week 1 foundation, D6 authentication, D7 authorization, and D8 school onboarding:

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

For the linked Neon project, `neon deploy` writes `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, and `NEON_BRANCH` to the root `.env.local`. The backend reads that file automatically when `backend/.env` does not provide overrides; `DATABASE_URL_UNPOOLED` is used as the migration connection fallback.

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
- `GET /api/auth/users` — list accounts (administrator only)
- `GET /api/auth/users/{user_id}` — return an account (the account owner or an administrator)
- `POST /api/schools/profile` — create a school profile (school role only)
- `GET /api/schools/profile` — return the signed-in school profile
- `POST /api/schools/profile/verification` — submit restricted verification evidence
- `GET /api/schools/profile/verifications` — return the school’s verification history
- `GET /api/admin/school-verifications` — review queue (administrator only)
- `POST /api/admin/school-verifications/{verification_id}/decision` — approve or reject a submission
- `GET /api/admin/audit-events` — review onboarding audit events (administrator only)
- `POST /api/needs` — create a school need as a draft (school role only)
- `GET /api/needs` — discover published needs with search, filters, and pagination
- `GET /api/needs/discover` — paginated public discovery results with school verification and fulfillment progress
- `GET /api/needs/{need_id}` — view a published need
- `PATCH /api/needs/{need_id}` — edit an owned draft, published, or paused need
- `POST /api/needs/{need_id}/publish` — publish an owned need (approved schools only)
- `POST /api/needs/{need_id}/pause` — pause a published owned need
- `POST /api/needs/{need_id}/close` — close an owned need
- `GET /api/needs/school/mine` — list all needs for the signed-in school
- `GET /api/donations` — discover active donation listings with filters and pagination
- `GET /api/donations/profile` / `POST /api/donations/profile` — read or create the signed-in donor profile
- `GET /api/donations/mine` — list the signed-in donor's listings
- `POST /api/donations` — create a donation listing
- `PATCH /api/donations/{donation_id}` — edit an active owned listing
- `POST /api/donations/{donation_id}/withdraw` — withdraw an owned listing without deleting its history
- `POST /api/donations/{donation_id}/images` — upload an owned donation image to Cloudinary
- `GET /api/donations/{donation_id}/images` — list image metadata for an owned donation
- `DELETE /api/donations/{donation_id}/images/{image_id}` — remove an owned donation image from Cloudinary
- `POST /api/matches/generate/{need_id}` — generate deterministic, explainable matches for an owned published need
- `GET /api/matches/need/{need_id}` — list ranked matches for an owned school need
- `GET /api/matches/mine` — list proposed or accepted matches for the signed-in donor
- `POST /api/matches/{match_id}/accept` — accept an accessible proposed match
- `POST /api/matches/{match_id}/reject` — reject an accessible proposed match
- `POST /api/reservations/matches/{match_id}` — reserve the remaining compatible donation quantity transactionally
- `GET /api/reservations/mine` — list reservations for the signed-in donor or school
- `GET /api/distributions/mine` — list distributions visible to the signed-in participant
- `GET /api/distributions/{distribution_id}/history` — list immutable distribution transitions
- `POST /api/distributions/{distribution_id}/dispatch` — move a reserved distribution into transit
- `POST /api/distributions/{distribution_id}/mark-delivered` — mark delivery pending school confirmation
- `POST /api/distributions/{distribution_id}/confirm-receipt` — school confirms receipt
- `POST /api/distributions/{distribution_id}/verify` — administrator verifies the distribution
- `POST /api/distributions/{distribution_id}/cancel` — cancel a reserved or in-transit distribution

Use a long random `JWT_SECRET_KEY` in non-development environments. Access tokens are short-lived JWTs; refresh tokens are opaque, rotated, revocable values whose hashes are stored in PostgreSQL. Administrator accounts must be provisioned by an administrator rather than through public registration.

Protected endpoints require an `Authorization: Bearer <access-token>` header. Authorization is enforced by the backend using role checks and ownership checks; frontend route and role gates only control presentation.

School profiles expose only safe school-level information. Verification references and evidence descriptions are restricted to the school representative and administrators. Every profile creation, verification submission, and review decision creates an audit event.

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