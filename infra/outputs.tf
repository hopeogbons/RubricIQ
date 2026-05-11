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

# The public URLs are only known after Railway issues each service its
# *.up.railway.app domain. Find them on the service pages in the Railway
# dashboard after the first deploy completes.
