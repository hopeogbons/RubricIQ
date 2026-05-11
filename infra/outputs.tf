output "project_id" {
  description = "Railway project ID."
  value       = railway_project.rubriciq.id
}

output "backend_service_id" {
  description = "Railway service ID for the backend."
  value       = railway_service.backend.id
}

output "frontend_service_id" {
  description = "Railway service ID for the frontend."
  value       = railway_service.frontend.id
}

output "api_url" {
  description = "Public API URL (custom domain attached to the backend service)."
  value       = "https://${railway_custom_domain.api.domain}"
}

output "app_url" {
  description = "Public app URL (custom domain attached to the frontend service)."
  value       = "https://${railway_custom_domain.app.domain}"
}
