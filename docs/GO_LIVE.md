# Go-live runbook

The day-of operational steps for putting RubricIQ in production.

By default the app runs on Railway's auto-issued `*.up.railway.app`
URLs - no custom domain or DNS step required. The "Custom domain
(optional)" section near the bottom covers attaching a real domain
later.

## Pre-flight checklist

- [ ] `terraform plan` is clean in CI (no drift) and the last
      `terraform apply` succeeded.
- [ ] The Postgres plugin is attached to the Railway project. The
      community Railway provider does not create it; you add it once
      via the Railway dashboard → **New → Database → PostgreSQL** in
      the project.
- [ ] All `TF_VAR_*` secrets exist in the GitHub repo *and* the
      Terraform Cloud workspace `rubriciq/rubriciq-prod`.
- [ ] Strong superadmin password set in `TF_VAR_superadmin_password`.
      You will change it again immediately after first login.
- [ ] Resend API key set; sender domain verified at Resend so
      activation emails actually deliver.
- [ ] n8n side is ready:
      - Webhook URL matches `var.n8n_webhook_url`.
      - n8n's "Header Auth account" credential has `X-API-Key
        = $N8N_WEBHOOK_SECRET` so it accepts our trigger.
      - n8n's HTTP Request node that posts to `/webhooks/n8n-callback`
        sends `X-API-Key = $CALLBACK_SECRET`.

## First-deploy sequence

1. Push the merge commit to `main`. The `terraform-apply` workflow
   runs behind the `production` GitHub environment; approve it once
   the plan looks right. Backend and frontend Railway services
   autodeploy from their respective `*-deploy` workflows.
2. Wait until **both services show "Active"** in Railway and the most
   recent deploy log ends without errors. Note the public URLs on the
   service pages - they look like
   `https://rubriciq-backend-production-XXXX.up.railway.app` and
   `https://rubriciq-frontend-production-XXXX.up.railway.app`.
3. Tail the backend logs (`railway logs --service backend`) and
   confirm you see one of:
   - `superadmin seeded` on a first-ever boot, or
   - no seed message on subsequent boots (env vars are ignored once
     a superadmin exists).
4. Run the smoke script from your laptop, plugging in the real
   Railway URLs:
   ```bash
   python scripts/smoke_test.py \
     --api-url https://<backend-railway-host> \
     --app-origin https://<frontend-railway-host> \
     --email <superadmin email> \
     --password '<superadmin password>'
   ```
   It checks `/health`, login, `/auth/me`, the rubrics list, CORS
   preflight from the app origin, foreign-origin CORS rejection, and
   callback `X-API-Key` enforcement. Exits non-zero on the first
   failure.
5. Log in at the frontend URL, open `/account`, change the superadmin
   password.

## End-to-end walk

With everything green, exercise one learner end-to-end:

1. Sign in as an admin user.
2. Create a rubric (or pick an existing one whose `unique_name`
   matches a sheet your n8n workflow knows about).
3. From the rubric page, **Add learner** → fill name → continue.
4. In the artifact panel:
   - Upload one screenshot (`.png`).
   - Add one GitHub link.
   - Optional: add a text note.
5. Click **Start evaluation**. The status should flip to *processing*.
6. Watch n8n's workflow execution log; confirm the trigger fired and
   the workflow runs to completion.
7. Within a couple of minutes you should see the learner's status
   flip to *complete* and a score appear. If it lands as *failed*,
   the error message column on the learner page shows what n8n
   reported.

## Custom domain (optional)

To attach a real domain later, e.g. `api.example.com` /
`app.example.com`:

1. Buy the domain at any registrar.
2. In the Railway dashboard, add a custom domain to each service.
   Railway shows the target hostname (and any verification record).
3. Add the CNAME records at your registrar and wait for them to flip
   from "Pending verification" to "Active" in Railway.
4. Update `infra/main.tf` to set fixed values for
   `PUBLIC_API_BASE_URL`, `FRONTEND_BASE_URL`, `CORS_ALLOW_ORIGINS`,
   and the frontend's `VITE_API_BASE_URL` instead of the reference
   expressions. (Optionally manage the domains in Terraform with
   `railway_custom_domain` resources.)
5. Apply the change.

## SPEC security checklist

Run each item before declaring go-live done.

- [ ] **No secrets in git.** `git log -p` shows `change-me`
      placeholders only; real values live in Terraform Cloud + Railway.
- [ ] **CORS is locked to the app origin.** The smoke script's CORS
      step asserts this; from dev tools on an unrelated site, a fetch
      to the backend `/health` should yield a CORS error.
- [ ] **Passwords are bcrypt-hashed.** A row from `users` shows a
      `$2b$…` prefix in `password_hash`.
- [ ] **JWT TTLs**: auth 24 h, artifact 2 h. Callback auth is a
      static shared secret (`CALLBACK_SECRET`), not a per-submission
      JWT.
- [ ] **/auth/login is rate-limited**. Five failed attempts in a
      minute from one IP returns 429.
- [ ] **n8n inbound auth**: trigger requests carry `X-API-Key:
      $N8N_WEBHOOK_SECRET`.
- [ ] **n8n callback auth**: `POST /webhooks/n8n-callback` without
      `X-API-Key` returns 401; the smoke script asserts this.
- [ ] **File uploads have size + type limits**: the per-file
      (`MAX_FILE_BYTES`) and per-submission (`MAX_SUBMISSION_BYTES`)
      caps from the env file are in effect; only `.png/.jpg/.jpeg` is
      accepted as a screenshot.
- [ ] **SQL via SQLAlchemy ORM**: a quick grep for `text(` in
      `app/routers/` shows only the harmless `SELECT 1` health probe.
- [ ] **Alembic migrations run on startup** (or at least pre-deploy).
      Logs show `Will assume transactional DDL` followed by the latest
      revision when the backend boots after a schema change.
- [ ] **Backups**: Railway daily Postgres backups enabled on the
      Postgres plugin; a manual monthly `pg_dump` lands on your laptop.

## If the smoke test fails

The script prints the first failing step and exits 1. Common causes,
roughly in order of likelihood:

- `CORS_ALLOW_ORIGINS` not set or mismatched. It should be the exact
  frontend origin (the auto-issued Railway URL, or your custom
  domain). The Terraform sets it from a reference variable - if the
  frontend service hadn't booted at backend deploy time, redeploy the
  backend to pick up the resolved value.
- Database not migrated. `railway run --service backend alembic
  current` should show the latest revision.
- Superadmin credentials don't match what was seeded. The first-boot
  env vars are authoritative until the first superadmin exists;
  after that, env changes are ignored.
- n8n credential mismatch. The trigger fails with 401 from n8n's side
  rather than ours; surface it via `railway logs --service backend`.
