# ==============================================================================
# OmniSight Backend Terraform Variables
# All credentials, configuration, and infrastructure parameters are parameterized.
# DO NOT hardcode sensitive tokens or credentials in this file.
# Supply secret values using terraform.tfvars or environment variables (TF_VAR_*).
# ==============================================================================

variable "aws_region" {
  description = "Target AWS region for deploying OmniSight backend infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (e.g., development, staging, production)"
  type        = string
  default     = "staging"
}

variable "app_name" {
  description = "Name of the OmniSight application service"
  type        = string
  default     = "omnisight-backend"
}

variable "container_image" {
  description = "Docker container image URI for the FastAPI backend"
  type        = string
  default     = "omnisight-backend:latest"
}

variable "container_port" {
  description = "Port exposed by the FastAPI container"
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "CPU units allocated for the backend service (1024 = 1 vCPU)"
  type        = string
  default     = "1024"
}

variable "memory" {
  description = "Memory allocated for the backend service in MB"
  type        = string
  default     = "2048"
}

variable "github_token" {
  description = "GitHub fine-grained personal access token for PR automation. Must be passed via terraform.tfvars or TF_VAR_github_token"
  type        = string
  sensitive   = true
}

variable "repo_name" {
  description = "Target GitHub repository in 'owner/repo' format"
  type        = string
  default     = "Kailash-18/OmniSight"
}

variable "mock_github" {
  description = "Enable mock GitHub operations for offline testing or demo environments"
  type        = bool
  default     = false
}

variable "allowed_target_hosts" {
  description = "Comma-separated list of allowed hostname patterns for browser audits (SSRF prevention)"
  type        = string
  default     = "localhost,127.0.0.1,staging.internal"
}
