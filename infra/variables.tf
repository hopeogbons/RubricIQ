variable "railway_token" {
  description = "Railway account token. Get one from https://railway.app/account/tokens."
  type        = string
  sensitive   = true
}

variable "github_repo" {
  description = "GitHub repository to deploy from, in 'owner/name' form."
  type        = string
  default     = "hopeogbons/RubricIQ"
}

variable "github_branch" {
  description = "Branch to deploy from."
  type        = string
  default     = "main"
}

variable "jwt_secret" {
  description = "HS256 signing secret for auth JWTs (64 random characters)."
  type        = string
  sensitive   = true
}

variable "artifact_signing_secret" {
  description = "Signing secret for artifact download tokens (64 random characters)."
  type        = string
  sensitive   = true
}

variable "callback_secret" {
  description = "Signing secret for n8n callback tokens (64 random characters)."
  type        = string
  sensitive   = true
}

variable "n8n_webhook_url" {
  description = "n8n Cloud production webhook URL."
  type        = string
  sensitive   = true
}

variable "n8n_webhook_secret" {
  description = "Shared secret for n8n header auth (X-API-Key)."
  type        = string
  sensitive   = true
}

variable "superadmin_email" {
  description = "Email of the initial superadmin user, seeded on first boot."
  type        = string
  sensitive   = true
}

variable "superadmin_password" {
  description = "Password for the initial superadmin user, seeded on first boot."
  type        = string
  sensitive   = true
}

variable "resend_api_key" {
  description = "Resend API key for activation emails."
  type        = string
  sensitive   = true
}

variable "public_api_base_url" {
  description = "Public base URL of the backend (e.g. https://api.rubriciq.com)."
  type        = string
}

variable "frontend_base_url" {
  description = "Public base URL of the frontend (e.g. https://app.rubriciq.com), used in activation emails."
  type        = string
}
