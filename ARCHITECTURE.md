# Shiksha Setu architecture

## Current foundation

The repository is a two-application workspace:

```text
frontend (React/Vite/TypeScript)
        |
        | HTTP JSON API
        v
backend (FastAPI)
        |
        | SQLAlchemy + psycopg
        v
Neon PostgreSQL
```

The frontend owns presentation and API calls. The backend is the authority for validation, authorization, workflow transitions, inventory allocation, and metrics. Database schema changes are managed through Alembic migrations.

The Week 1 backend currently provides:

- environment-based settings
- liveness and database-readiness endpoints
- SQLAlchemy engine/session setup
- `users` and revocable `auth_sessions` tables through Alembic migrations
- JWT access tokens and hashed, rotating refresh sessions
- registration, login, refresh, logout, and current-user endpoints
- reusable role and ownership authorization dependencies
- administrator-only user listing and owner-or-administrator account access
- school profiles with restricted verification submissions and administrator decisions
- immutable onboarding audit events
- CORS configuration for the frontend origin

## Connection strategy

- Use Neon's pooled connection string for normal FastAPI runtime traffic.
- Use Neon's direct connection string for Alembic migrations when available.
- Keep both URLs in backend-only environment variables with `sslmode=require` and `channel_binding=require`.
- Never expose database URLs or future LLM keys through frontend environment variables.

## Planned boundaries

Future domain behavior should be added behind modular FastAPI routers and service functions for authentication, schools, needs, donations, matching, reservations, distributions, education-support programs, notifications, impact metrics, and AI adapters. The deterministic domain services remain authoritative; LLM output is advisory and validated before use.

Authentication is backend-authoritative. Public registration supports donor, school, and volunteer roles; administrator accounts must be provisioned through an administrative workflow. Access tokens are short-lived JWTs, while refresh tokens are opaque values whose hashes are stored in `auth_sessions` and rotated on use.

Authorization is also backend-authoritative. `require_roles` protects role-scoped endpoints, while `require_self_or_roles` protects account resources that are available to the owner and configured privileged roles. The frontend uses `ProtectedRoute` and `RoleGate` for responsive user experience, but those components do not replace API authorization.

School onboarding is split into safe public-profile fields and restricted verification data. A school representative creates one profile and submits verification evidence; administrators can review pending submissions, approve or reject them with a reason, and inspect the resulting audit events. The school’s profile status mirrors the latest decision, while prior verification records remain available as history.