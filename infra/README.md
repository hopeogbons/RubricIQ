# infra

Terraform managing the Railway project (backend, frontend, artifact
volume, env vars) per `SPEC.md` section "Terraform (infra/)".

The Postgres plugin and any custom domain are added manually in the
Railway dashboard - see the two notes below.

## State backend

`main.tf` uses Terraform Cloud as the state backend:

```hcl
backend "remote" {
  organization = "rubriciq"
  workspaces { name = "rubriciq-prod" }
}
```

Two options:

1. **Use Terraform Cloud** (recommended for shared infra). Create the
   `rubriciq` organization and a workspace named `rubriciq-prod`, then
   run `terraform login` before `terraform init`. CI also needs
   `TF_API_TOKEN`.
2. **Use local state** for a quick first pass. Comment out the
   `backend "remote"` block in `main.tf` and re-run `terraform init`.
   State will live in `terraform.tfstate` next to this file; do not
   commit it (already gitignored).

## Manual step 1: Postgres plugin (always required)

The community Railway provider v0.6 does not expose a `plugin` resource,
so the Postgres plugin must be provisioned **outside Terraform** the
first time the project is set up:

1. After the first `terraform apply` creates the project, open it in the
   Railway dashboard.
2. Click **New → Database → PostgreSQL** to add the plugin to the
   project.
3. Terraform sets `DATABASE_URL` on the backend service to the Railway
   reference variable `${{Postgres.DATABASE_URL}}`; once the plugin
   exists, Railway resolves it at deploy time. No further Terraform
   changes are required.

## Manual step 2: custom domain (optional)

By default each service uses Railway's auto-issued
`*.up.railway.app` domain. The backend and frontend learn each other's
URL via Railway reference variables (`${{frontend.RAILWAY_PUBLIC_DOMAIN}}`,
etc.) wired into the env vars in `main.tf`, so the app works as soon as
the services boot.

If you later attach a real domain:

1. In the Railway dashboard, add a custom domain to each service.
2. Point the corresponding CNAME at the host Railway shows.
3. Update `main.tf` to set fixed values for `PUBLIC_API_BASE_URL`,
   `FRONTEND_BASE_URL`, `CORS_ALLOW_ORIGINS`, and the frontend's
   `VITE_API_BASE_URL` instead of the reference expressions.
4. Optionally manage the domains in Terraform with `railway_custom_domain`
   resources.

## Bootstrap

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with real values
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
# then add the Postgres plugin in the Railway dashboard (see above)
```

`terraform.tfvars` and any `*.tfstate*` files are gitignored. The
provider lockfile (`.terraform.lock.hcl`) is committed so plans are
reproducible.

## Required GitHub secrets for CI

- `TF_API_TOKEN` (only if using the remote backend)
- One secret per sensitive Terraform variable in `variables.tf`,
  surfaced to the workflow as `TF_VAR_<name>` (e.g. `TF_VAR_jwt_secret`).

## After first apply

- Find the auto-issued public URLs on the service pages in Railway -
  e.g. `https://rubriciq-backend-production-XXXX.up.railway.app`.
- Log in once with the seeded superadmin and change the password.
- Verify `DATABASE_URL` was wired by the plugin (the value is set from
  `${{Postgres.DATABASE_URL}}`).
