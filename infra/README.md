# infra

Terraform managing the Railway project (backend, frontend, Postgres plugin,
artifact volume, env vars, custom domains) per `SPEC.md` section "Terraform
(infra/)".

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
   `rubriciq` organization and a workspace named `rubriciq-prod`, then run
   `terraform login` before `terraform init`. CI also needs `TF_API_TOKEN`.

2. **Use local state** for a quick first pass. Comment out the `backend "remote"`
   block in `main.tf` and re-run `terraform init`. State will live in
   `terraform.tfstate` next to this file; do not commit it (already gitignored).

## Manual step before `terraform apply`

The community Railway provider v0.6 does not expose a `plugin` resource, so
the Postgres plugin must be provisioned **outside Terraform** the first time
the project is set up:

1. After the first `terraform apply` creates the project, open it in the
   Railway dashboard.
2. Click **New → Database → PostgreSQL** to add the plugin to the project.
3. Terraform sets `DATABASE_URL` on the backend service to the Railway
   reference variable `${{Postgres.DATABASE_URL}}`; once the plugin exists,
   Railway resolves it at deploy time. No further Terraform changes are
   required.

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

`terraform.tfvars` and any `*.tfstate*` files are gitignored. The provider
lockfile (`.terraform.lock.hcl`) is committed so plans are reproducible.

## Required GitHub secrets for CI (used in Step 13)

- `RAILWAY_TOKEN`
- `TF_API_TOKEN` (only if using the remote backend)
- One secret per sensitive Terraform variable, surfaced to the workflow as
  `TF_VAR_<name>` (e.g. `TF_VAR_jwt_secret`).

## After first apply

- Point DNS for `api.rubriciq.com` and `app.rubriciq.com` at the Railway
  custom domains shown in `terraform output`.
- Log in once with the seeded superadmin and change the password.
- Verify `DATABASE_URL` was wired by the plugin (the value is set from
  `railway_plugin.postgres.database_url`).
