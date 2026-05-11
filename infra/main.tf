terraform {
  required_version = ">= 1.6"
  required_providers {
    railway = {
      source  = "terraform-community-providers/railway"
      version = "~> 0.6"
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

# The community provider v0.6 does not expose a "plugin" resource, so the
# Postgres plugin is provisioned out-of-band (Railway dashboard or CLI) and
# referenced from the backend service via Railway's ${{Postgres.DATABASE_URL}}
# reference-variable syntax below.

resource "railway_service" "backend" {
  name               = "backend"
  project_id         = railway_project.rubriciq.id
  source_repo        = var.github_repo
  source_repo_branch = var.github_branch
  root_directory     = "/backend"

  volume = {
    name       = "artifacts"
    mount_path = "/data"
  }
}

resource "railway_service" "frontend" {
  name               = "frontend"
  project_id         = railway_project.rubriciq.id
  source_repo        = var.github_repo
  source_repo_branch = var.github_branch
  root_directory     = "/frontend"
}

locals {
  default_env_id = railway_project.rubriciq.default_environment.id

  # URLs use Railway's reference-variable syntax so each service learns the
  # other's public *.up.railway.app domain at deploy time without a custom
  # domain. If you later add a custom domain, swap these for fixed strings
  # and add a railway_custom_domain resource per service.
  backend_self_url       = "https://$${{RAILWAY_PUBLIC_DOMAIN}}"
  frontend_url_from_back = "https://$${{frontend.RAILWAY_PUBLIC_DOMAIN}}"
  backend_url_from_front = "https://$${{backend.RAILWAY_PUBLIC_DOMAIN}}"

  # DATABASE_URL is a Railway reference variable that resolves to the Postgres
  # plugin's connection string at deploy time; the plugin itself is created
  # manually since the provider does not expose it.
  backend_env = {
    DATABASE_URL            = "$${{Postgres.DATABASE_URL}}"
    JWT_SECRET              = var.jwt_secret
    ARTIFACT_SIGNING_SECRET = var.artifact_signing_secret
    CALLBACK_SECRET         = var.callback_secret
    N8N_WEBHOOK_URL         = var.n8n_webhook_url
    N8N_WEBHOOK_SECRET      = var.n8n_webhook_secret
    SUPERADMIN_EMAIL        = var.superadmin_email
    SUPERADMIN_PASSWORD     = var.superadmin_password
    RESEND_API_KEY          = var.resend_api_key
    PUBLIC_API_BASE_URL     = local.backend_self_url
    FRONTEND_BASE_URL       = local.frontend_url_from_back
    CORS_ALLOW_ORIGINS      = local.frontend_url_from_back
    ARTIFACT_DIR            = "/data/artifacts"
    ENV                     = "production"
  }
}

resource "railway_variable" "backend_env" {
  for_each = local.backend_env

  name           = each.key
  value          = each.value
  environment_id = local.default_env_id
  service_id     = railway_service.backend.id
}

resource "railway_variable" "frontend_api_base" {
  name           = "VITE_API_BASE_URL"
  value          = local.backend_url_from_front
  environment_id = local.default_env_id
  service_id     = railway_service.frontend.id
}
