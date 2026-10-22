# ==============================================================================
# OmniSight Backend Terraform Outputs
# Exposes service endpoint URLs and configuration IDs.
# ==============================================================================

output "backend_service_id" {
  description = "The ID of the provisioned App Runner service"
  value       = aws_apprunner_service.backend_service.service_id
}

output "backend_service_url" {
  description = "Public URL of the OmniSight FastAPI backend service"
  value       = "https://${aws_apprunner_service.backend_service.service_url}"
}

output "backend_health_check_url" {
  description = "Health check URL for automated monitoring"
  value       = "https://${aws_apprunner_service.backend_service.service_url}/health"
}

output "backend_webhook_url" {
  description = "Webhook receiver endpoint for external CI/CD integrations"
  value       = "https://${aws_apprunner_service.backend_service.service_url}/webhook/build"
}
