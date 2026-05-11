# RubricIQ

Web app for evaluating learner submissions against rubrics. The actual
evaluation happens in an n8n Cloud workflow; this codebase is the
interface, data layer, auth system, and dashboard around it.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, APScheduler |
| Database | PostgreSQL |
| Auth | bcrypt + HS256 JWT (24 h TTL) + slowapi rate limit |
| Frontend | React + Vite + TypeScript, TanStack Query, Tailwind + shadcn/ui, Recharts |
| Hosting | Railway (backend, frontend, Postgres plugin) |
| Infra | Terraform (community Railway provider) |
| CI/CD | GitHub Actions |

## Repository layout

```
backend/   FastAPI app, Alembic migrations, pytest suite
frontend/  React app, Vitest + MSW suite
infra/     Terraform for the Railway project + services + env vars
docs/      Operational docs (GO_LIVE.md)
scripts/   smoke_test.py for post-deploy verification
SPEC.md    The build spec; treat as the source of truth
```

## Local development

### Backend

```bash
cd backend
cp .env.example .env                                # fill in secrets
uv sync                                             # installs Python 3.12 deps
createdb rubriciq                                   # one-time
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The server boots on `http://localhost:8000`. The first start seeds the
superadmin from `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD`; those env
vars are ignored on subsequent boots once a superadmin row exists.

Tests use `pytest-postgresql` to spawn an ephemeral cluster, so they
don't touch the dev DB:

```bash
uv run pytest
```

### Frontend

```bash
cd frontend
cp .env.example .env                                # sets VITE_API_BASE_URL
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and expects the backend
at `VITE_API_BASE_URL`. Test commands:

```bash
npm run test          # Vitest + RTL + MSW
npm run typecheck     # tsc --noEmit
npm run build         # production bundle
```

## n8n integration

Triggers go from FastAPI to the n8n webhook URL with header
`X-API-Key: $N8N_WEBHOOK_SECRET`, body shape:

```json
{
  "learner_id": "<uuid>",
  "assessment_id": "<rubric.unique_name>",
  "cohort": "<string|null>",
  "artifacts": [
    {"type": "screenshot", "url": "<signed URL>"},
    {"type": "loom",         "url": "..."},
    {"type": "gdrive_video", "url": "..."},
    {"type": "github",       "url": "..."},
    {"type": "text",         "value": "..."}
  ]
}
```

n8n returns results to `POST /webhooks/n8n-callback` with header
`X-API-Key: $CALLBACK_SECRET`; correlation is by `learner_id` since
each learner has at most one submission.

## Going to production

Terraform manages everything except the Postgres plugin (the community
provider doesn't expose it; add it once via the Railway dashboard after
the first apply). See:

- [`infra/README.md`](infra/README.md) — Terraform bootstrap and the
  manual Postgres step
- [`docs/GO_LIVE.md`](docs/GO_LIVE.md) — pre-flight checklist, DNS,
  smoke test, security checklist, end-to-end walk
- [`scripts/smoke_test.py`](scripts/smoke_test.py) — runs after a deploy
  to confirm `/health`, login, CORS, and callback auth all behave

## Project status

The SPEC build order (`SPEC.md` → "Build order") is complete. Test totals:
178 backend, 49 frontend; all green.
