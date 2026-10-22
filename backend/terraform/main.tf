# ==============================================================================
# OmniSight Backend Infrastructure Definition
# Provisions containerized FastAPI backend on AWS App Runner with secure secrets.
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "OmniSight"
      Role        = "Member-1-Backend"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# IAM Role for AWS App Runner Service
resource "aws_iam_role" "apprunner_instance_role" {
  name = "${var.app_name}-${var.environment}-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

# AWS App Runner Service (Fully managed containerized deployment for FastAPI Gateway)
resource "aws_apprunner_service" "backend_service" {
  service_name = "${var.app_name}-${var.environment}"

  source_configuration {
    auto_deployments_enabled = false

    image_repository {
      image_identifier      = var.container_image
      image_repository_type = "ECR"

      image_configuration {
        port = tostring(var.container_port)

        runtime_environment_variables = {
          REPO_NAME            = var.repo_name
          MOCK_GITHUB          = tostring(var.mock_github)
          ALLOWED_TARGET_HOSTS = var.allowed_target_hosts
          BACKEND_HOST         = "0.0.0.0"
          BACKEND_PORT         = tostring(var.container_port)
        }

        runtime_environment_secrets = {
          GITHUB_TOKEN = var.github_token
        }
      }
    }
  }

  instance_configuration {
    cpu               = var.cpu
    memory            = var.memory
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 3
  }
}
