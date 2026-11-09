# ==============================================================================
# OmniSight Terraform Cloud Infrastructure Outputs
# ==============================================================================

output "service_url" {
  description = "The public HTTPS URL of the deployed OmniSight App Runner gateway"
  value       = "https://${aws_apprunner_service.omnisight_gateway.service_url}"
}

output "service_arn" {
  description = "The Amazon Resource Name (ARN) of the App Runner service"
  value       = aws_apprunner_service.omnisight_gateway.arn
}

output "service_id" {
  description = "The unique service identifier assigned by AWS App Runner"
  value       = aws_apprunner_service.omnisight_gateway.service_id
}

output "cloudwatch_log_group" {
  description = "The name of the CloudWatch log group collecting runtime telemetry"
  value       = aws_cloudwatch_log_group.omnisight_logs.name
}

output "health_check_url" {
  description = "Public health check URL for monitoring probes and uptime alerts"
  value       = "https://${aws_apprunner_service.omnisight_gateway.service_url}${var.health_check_path}"
}
