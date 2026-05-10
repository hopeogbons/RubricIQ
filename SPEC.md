# RubricIQ - Project Specification

## Purpose

Web app for evaluating learner submissions against rubrics. Heavy lifting (the actual evaluation against rubric criteria) is performed by an existing n8n Cloud workflow. This app is the interface, data layer, auth system, and dashboard.

## Stack (final, no alternatives)

- Frontend: React + Vite + TypeScript + TanStack Query + Tailwind + shadcn/ui
- Backend: FastAPI (Python 3.12) + SQLAlchemy 2.0 + Alembic
- Database: Postgres (Railway managed)
- File storage: FastAPI local volume at `/data/artifacts/` (transient, deleted after evaluation)
- Workflow engine: n8n Cloud (already hosted at n8n.io, called via webhook)
- Hosting: Railway (frontend, backend, database all on one project)
- IaC: Terraform (Railway provider)
- CI/CD: GitHub Actions

## Repository structure

```
rubriciq/
├── backend/                FastAPI service
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── rubrics.py
│   │   │   ├── learners.py
│   │   │   ├── submissions.py
│   │   │   ├── artifacts.py
│   │   │   └── webhooks.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── n8n_service.py
│   │   │   ├── artifact_service.py
│   │   │   └── email_service.py
│   │   ├── deps.py
│   │   └── tasks/cleanup.py
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── railway.json
├── frontend/               React app
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/api.ts
│   │   ├── lib/auth.tsx
│   │   └── App.tsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── railway.json
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── .github/
│   └── workflows/
│       ├── backend-deploy.yml
│       ├── frontend-deploy.yml
│       ├── terraform-plan.yml
│       └── terraform-apply.yml
├── .gitignore
├── README.md
└── SPEC.md
```

## Authentication

- On first boot, FastAPI seeds a superadmin from `SUPERADMIN_EMAIL` and `SUPERADMIN_PASSWORD` env vars if no superadmin exists in the database. After first boot, those env vars are ignored.
- Public signup creates a user with `is_active = false`. They cannot log in until activated.
- Superadmin or admin activates a user from the admin panel. Activation triggers an email containing a one-time login link or a notice that they can now log in normally (choose the simpler path: just send a notification email saying "your account is active, log in here").
- Email delivery: use Resend API (free tier covers 100 emails/day, plenty for this).
- Login returns a JWT (HS256, signed with `JWT_SECRET`, 24-hour expiry).
- Roles: `superadmin`, `admin`, `evaluator`, `viewer`. Enforced via FastAPI dependencies.

## Data model (Postgres tables)

```sql
users
  id              uuid pk
  email           text unique not null
  password_hash   text not null
  full_name       text
  role            text check (role in ('superadmin','admin','evaluator','viewer'))
  is_active       boolean default false
  activated_at    timestamptz
  created_at      timestamptz default now()

rubrics
  id                       uuid pk
  unique_name              text unique not null    -- maps to n8n's known rubric identifier
  display_name             text not null
  description              text
  google_sheet_id          text
  google_drive_folder_path text
  created_by               uuid references users(id)
  created_at               timestamptz default now()

learners
  id          uuid pk
  rubric_id   uuid not null references rubrics(id) on delete cascade
  full_name   text not null
  email       text
  cohort      text
  created_at  timestamptz default now()
  unique (rubric_id, email)

submissions
  id              uuid pk
  learner_id      uuid not null references learners(id) on delete cascade
  rubric_id       uuid not null references rubrics(id)
  status          text check (status in ('draft','processing','complete','failed')) default 'draft'
  triggered_at    timestamptz
  completed_at    timestamptz
  error_message   text
  created_by      uuid references users(id)
  created_at      timestamptz default now()

submission_artifacts
  id              uuid pk
  submission_id   uuid not null references submissions(id) on delete cascade
  type            text check (type in ('video_file','screenshot','video_link','github_link'))
  storage_path    text                              -- relative path on FastAPI volume, null for links
  external_url    text                              -- the link itself, null for files
  filename        text
  size_bytes      bigint
  created_at      timestamptz default now()

evaluations
  id              uuid pk unique
  submission_id   uuid not null unique references submissions(id) on delete cascade
  total_score     numeric
  max_total       numeric
  raw_response    jsonb                             -- full n8n payload for audit
  evaluated_at    timestamptz default now()

evaluation_scores
  id              uuid pk
  evaluation_id   uuid not null references evaluations(id) on delete cascade
  criterion       text not null
  score           numeric not null
  max_score       numeric not null
  explanation     text
```

Indexes: `learners(rubric_id)`, `submissions(rubric_id, status)`, `submissions(learner_id)`, `evaluation_scores(evaluation_id)`.

## API endpoints (FastAPI)

```
POST   /auth/signup                       create user (is_active=false)
POST   /auth/login                        return JWT
GET    /auth/me                           current user info
POST   /auth/users/{id}/activate          admin only, activates user, sends email
GET    /auth/users                        admin only, list users

POST   /rubrics                           admin only, create rubric
GET    /rubrics                           list rubrics (scoped by role)
GET    /rubrics/{id}                      get rubric details + stats
PATCH  /rubrics/{id}                      update rubric
DELETE /rubrics/{id}                      admin only

POST   /rubrics/{id}/learners             add learner to rubric
GET    /rubrics/{id}/learners             list learners in rubric
GET    /learners/{id}                     learner detail with submissions
DELETE /learners/{id}                     remove learner

POST   /learners/{id}/submissions         create submission (returns submission_id)
POST   /submissions/{id}/artifacts        upload artifact files (multipart)
POST   /submissions/{id}/artifacts/links  add link-type artifacts (json)
DELETE /submissions/{id}/artifacts/{aid}  remove artifact before evaluation
POST   /submissions/{id}/evaluate         trigger n8n webhook, set status=processing
GET    /submissions/{id}                  get submission with artifacts and evaluation
GET    /submissions/{id}/status           lightweight status check for polling

GET    /artifacts/{token}                 signed-URL endpoint n8n uses to download
                                          token = JWT signed with ARTIFACT_SIGNING_SECRET

POST   /webhooks/n8n-callback             n8n posts results here, verifies callback_token

GET    /dashboard/rubrics/{id}/stats      aggregate stats for dashboard
```

## n8n contract

### Trigger payload (FastAPI -> n8n)

`POST {N8N_WEBHOOK_URL}` with header `X-API-Key: {N8N_WEBHOOK_SECRET}`:

```json
{
  "submission_id": "uuid",
  "rubric_unique_name": "neural-forge-week-5-mcp",
  "learner": {
    "id": "uuid",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "cohort": "cohort-7"
  },
  "artifacts": [
    {
      "type": "video_file",
      "url": "https://api.rubriciq.com/artifacts/<signed-jwt>",
      "filename": "demo.mp4"
    },
    {
      "type": "screenshot",
      "url": "https://api.rubriciq.com/artifacts/<signed-jwt>",
      "filename": "dashboard.png"
    },
    {
      "type": "video_link",
      "url": "https://loom.com/share/abc123"
    },
    {
      "type": "github_link",
      "url": "https://github.com/jane/project"
    }
  ],
  "callback_url": "https://api.rubriciq.com/webhooks/n8n-callback",
  "callback_token": "<JWT signed with CALLBACK_SECRET, includes submission_id, 2-hour TTL>"
}
```

### Callback payload (n8n -> FastAPI)

`POST /webhooks/n8n-callback`:

```json
{
  "submission_id": "uuid",
  "callback_token": "<the same token sent in the trigger>",
  "status": "complete",
  "evaluation": {
    "total_score": 18,
    "max_total": 25,
    "scores": [
      {
        "criterion": "Code quality",
        "score": 4,
        "max": 5,
        "explanation": "Clean structure with one minor naming inconsistency."
      }
    ]
  }
}
```

On `status: failed`, payload includes `"error": "..."` instead of `evaluation`.

### Webhook response

n8n's webhook responds immediately with `{"accepted": true}`. The actual results come via the callback. This means the workflow must be set to "Respond Immediately" mode and include a final HTTP Request node that posts to `callback_url`.

## Artifact handling

1. Files upload via `POST /submissions/{id}/artifacts` (multipart). FastAPI writes to `/data/artifacts/{submission_id}/{filename}`.
2. On `POST /submissions/{id}/evaluate`, FastAPI generates a signed JWT per file (TTL 2 hours, payload includes submission_id and filename) and embeds the URLs in the n8n payload.
3. n8n downloads files via `GET /artifacts/{token}`. FastAPI verifies the token and streams the file.
4. On callback (success or failure), FastAPI deletes `/data/artifacts/{submission_id}/`.
5. A background task runs every hour and deletes any artifact directory older than 6 hours, in case a callback never arrives.

## Frontend pages

```
/login                     login form
/signup                    signup form (creates inactive account)
/dashboard                 list of rubrics + global stats (admin only)
/rubrics                   list rubrics user can access
/rubrics/:id               rubric dashboard - stats, learner list, charts
/rubrics/:id/learners/new  add learner + upload artifacts + trigger evaluation
/learners/:id              learner detail with all submissions and scores
/admin/users               user management (admin only)
/account                   logged-in user profile
```

Dashboard widgets per rubric:
- Header: rubric name, learner count, completion rate, average total score
- Score distribution histogram
- Per-criterion average bar chart
- Learner table: name, total score, status, evaluated_at, link to detail

Use Recharts for charts. Tables via shadcn/ui Table component.

## Environment variables

### Backend service on Railway
```
DATABASE_URL              (Railway Postgres reference)
JWT_SECRET                (random 64-char string)
ARTIFACT_SIGNING_SECRET   (random 64-char string)
CALLBACK_SECRET           (random 64-char string)
N8N_WEBHOOK_URL           (your n8n Cloud production webhook URL)
N8N_WEBHOOK_SECRET        (shared secret configured on n8n's Header Auth)
SUPERADMIN_EMAIL          (your email)
SUPERADMIN_PASSWORD       (initial password, change after first login)
RESEND_API_KEY            (for activation emails)
PUBLIC_API_BASE_URL       (e.g. https://api.rubriciq.com - used to build artifact URLs)
FRONTEND_BASE_URL         (e.g. https://app.rubriciq.com - used in activation emails)
ARTIFACT_DIR              (default: /data/artifacts)
ENV                       (production)
```

### Frontend service on Railway
```
VITE_API_BASE_URL         (https://api.rubriciq.com)
```

## Background jobs

Run via APScheduler embedded in FastAPI (single-process, fine for this scale):
- Hourly: scan `/data/artifacts/`, delete directories older than 6 hours
- Hourly: mark submissions as `failed` if `status='processing'` and `triggered_at` is older than 30 minutes

## Terraform (infra/)

Manages Railway resources via the community Railway provider. Creates: project, three services (backend, frontend, postgres plugin), environment variables, volume for backend, custom domains.

`infra/main.tf`:

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    railway = {
      source  = "terraform-community-providers/railway"
      version = "~> 0.5"
    }
  }
  backend "remote" {
    organization = "rubriciq"
    workspaces { name = "rubriciq-prod" }
  }
}

provider "railway" {
  token = var.railway_token
}

resource "railway_project" "rubriciq" {
  name        = "rubriciq"
  description = "Rubric-based learner evaluation"
}

resource "railway_service" "backend" {
  name       = "backend"
  project_id = railway_project.rubriciq.id
  source_repo = "your-github-org/rubriciq"
  source_repo_branch = "main"
  root_directory = "/backend"
}

resource "railway_service" "frontend" {
  name       = "frontend"
  project_id = railway_project.rubriciq.id
  source_repo = "your-github-org/rubriciq"
  source_repo_branch = "main"
  root_directory = "/frontend"
}

resource "railway_plugin" "postgres" {
  name       = "postgresql"
  project_id = railway_project.rubriciq.id
}

resource "railway_volume" "artifacts" {
  name       = "artifacts"
  project_id = railway_project.rubriciq.id
  service_id = railway_service.backend.id
  mount_path = "/data"
}

# Backend env vars
resource "railway_variable" "backend_database_url" {
  name       = "DATABASE_URL"
  value      = railway_plugin.postgres.database_url
  service_id = railway_service.backend.id
}

resource "railway_variable" "backend_jwt_secret" {
  name       = "JWT_SECRET"
  value      = var.jwt_secret
  service_id = railway_service.backend.id
}

# ... repeat for ARTIFACT_SIGNING_SECRET, CALLBACK_SECRET, N8N_WEBHOOK_URL,
# N8N_WEBHOOK_SECRET, SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD, RESEND_API_KEY,
# PUBLIC_API_BASE_URL, FRONTEND_BASE_URL, ENV

# Frontend env vars
resource "railway_variable" "frontend_api_base" {
  name       = "VITE_API_BASE_URL"
  value      = var.public_api_base_url
  service_id = railway_service.frontend.id
}

# Custom domains
resource "railway_custom_domain" "api" {
  domain     = "api.rubriciq.com"
  service_id = railway_service.backend.id
}

resource "railway_custom_domain" "app" {
  domain     = "app.rubriciq.com"
  service_id = railway_service.frontend.id
}
```

`infra/variables.tf`: declare `railway_token`, `jwt_secret`, `artifact_signing_secret`, `callback_secret`, `n8n_webhook_url`, `n8n_webhook_secret`, `superadmin_email`, `superadmin_password`, `resend_api_key`, `public_api_base_url`, `frontend_base_url`, all marked `sensitive = true` where appropriate.

`infra/terraform.tfvars.example`: documents required values with placeholders. Real `terraform.tfvars` is gitignored.

## GitHub Actions

### `.github/workflows/backend-deploy.yml`

Triggers on push to `main` affecting `backend/**`. Steps:
1. Checkout
2. Setup Python 3.12
3. Install deps and run `pytest`
4. On success, Railway autodeploys via the GitHub integration (no explicit deploy step needed if the service is connected to the repo)

If you prefer explicit deploys via Railway CLI:
```yaml
- uses: actions/checkout@v4
- run: npm install -g @railway/cli
- run: railway up --service backend --detach
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### `.github/workflows/frontend-deploy.yml`

Same pattern for `frontend/**`. Steps:
1. Checkout
2. Setup Node 20
3. `npm ci && npm run build && npm run test`
4. Railway autodeploys, or use `railway up --service frontend --detach`

### `.github/workflows/terraform-plan.yml`

On PR to `main` affecting `infra/**`:
1. Setup Terraform
2. `terraform init`
3. `terraform plan -out=plan.tfplan`
4. Post plan as PR comment via tfcmt or hashicorp/setup-terraform action

### `.github/workflows/terraform-apply.yml`

On push to `main` affecting `infra/**`, with manual approval gate:
1. Setup Terraform
2. `terraform init`
3. `terraform apply -auto-approve`

Required GitHub secrets:
- `RAILWAY_TOKEN` (Railway account token)
- `TF_API_TOKEN` (Terraform Cloud token if using remote backend)
- All sensitive values from `terraform.tfvars` as individual secrets, passed via `TF_VAR_*` env vars in the workflow

## Security checklist

- [ ] All secrets in Railway env vars or Terraform Cloud, never in git
- [ ] CORS on FastAPI restricted to `https://app.rubriciq.com` (and localhost during dev)
- [ ] Passwords hashed with bcrypt (`passlib[bcrypt]`)
- [ ] JWT tokens have reasonable TTLs (24h for auth, 2h for artifacts, 2h for callbacks)
- [ ] Rate limiting on `/auth/login` (slowapi, 5 attempts per minute per IP)
- [ ] n8n webhook auth with shared secret in `X-API-Key` header
- [ ] Callback endpoint verifies signed token, not source IP
- [ ] File uploads have size limits (e.g. 100MB per file, 500MB per submission)
- [ ] File type validation (video_file: mp4/mov/webm; screenshot: png/jpg/jpeg)
- [ ] SQL via SQLAlchemy ORM, no raw string interpolation
- [ ] Alembic migrations run on backend startup
- [ ] Postgres backups: rely on Railway daily backups + monthly manual `pg_dump` to local

## Out of scope for v1

- Bulk learner upload (one-by-one only)
- Re-evaluation / version history (one evaluation per submission)
- Multi-organization tenancy (rubric is the only batch boundary)
- Email notifications beyond activation
- Real-time UI updates (frontend polls `/submissions/{id}/status` every 5s while processing)
- OAuth / SSO logins
- Audit log

## Build order (recommended)

Build in this order to keep things working end-to-end at every stage:

1. Backend skeleton: FastAPI + SQLAlchemy + Alembic, all models migrated
2. Auth: signup, login, activate, JWT, role dependencies
3. Rubric and learner CRUD endpoints
4. Submission and artifact upload endpoints, including signed URL serving
5. n8n trigger and callback endpoints, fully tested with curl
6. Background cleanup tasks
7. Frontend: auth flow (login, signup, account)
8. Frontend: rubric list and detail
9. Frontend: learner add + artifact upload + evaluate flow
10. Frontend: dashboard with charts
11. Admin pages
12. Terraform infra
13. GitHub Actions
14. Custom domains, production smoke test

Test each layer before moving to the next.
