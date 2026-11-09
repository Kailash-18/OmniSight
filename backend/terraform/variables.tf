variable "aws_region" {
  type        = string
  description = "AWS region for deployment"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment name (production, staging, dev)"
  default     = "production"
}

variable "service_name" {
  type        = string
  description = "Name identifier for the OmniSight backend service"
  default     = "omnisight-backend"
}

variable "container_image" {
  type        = string
  description = "Fully qualified container image URI (e.g. AWS ECR repository URI)"
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/omnisight-backend:latest"
}

variable "container_port" {
  type        = number
  description = "Internal port exposed by FastAPI container"
  default     = 8000
}

variable "cpu" {
  type        = string
  description = "CPU units allocated for container instance (e.g., 1024 = 1 vCPU, 2048 = 2 vCPU)"
  default     = "1024"
}

variable "memory" {
  type        = string
  description = "Memory allocated for container instance in MB (e.g., 2048 = 2 GB, 4096 = 4 GB)"
  default     = "2048"
}

variable "health_check_path" {
  type        = string
  description = "Health check path for service readiness probes"
  default     = "/health"
}

variable "allowed_target_hosts" {
  type        = string
  description = "Comma-separated allowlist of target hostnames for visual QA audits"
  default     = "localhost,127.0.0.1,staging.internal"
}

variable "github_repo" {
  type        = string
  description = "Target GitHub repository for automated fix Pull Requests"
  default     = "Kailash-18/OmniSight"
}

variable "mock_github" {
  type        = bool
  description = "Whether to use deterministic mock PR generation instead of live GitHub API calls"
  default     = false
}

variable "github_token_secret_arn" {
  type        = string
  description = "ARN of AWS Secrets Manager secret holding the fine-grained GitHub PAT (leave empty if using MOCK_GITHUB)"
  default     = ""
}

variable "webhook_secret_arn" {
  type        = string
  description = "ARN of AWS Secrets Manager secret holding the CI/CD webhook secret"
  default     = ""
}
