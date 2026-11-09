# ==============================================================================
# OmniSight Cloud Infrastructure as Code (Terraform)
# AWS App Runner / ECS Container Deployment for OmniSight CI/CD Gateway
# Zero hardcoded credentials - all secrets managed via AWS Secrets Manager & SSM
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
      ManagedBy   = "Terraform"
      Environment = var.environment
      Component   = "BackendGateway"
    }
  }
}

# ------------------------------------------------------------------------------
# CloudWatch Log Group for Application Telemetry & Audit Logs
# ------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "omnisight_logs" {
  name              = "/aws/apprunner/${var.service_name}-${var.environment}"
  retention_in_days = 30
}

# ------------------------------------------------------------------------------
# IAM Execution Role for App Runner Container Instances
# ------------------------------------------------------------------------------
resource "aws_iam_role" "apprunner_instance_role" {
  name = "${var.service_name}-instance-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# IAM Policy for CloudWatch Logging and Secrets Retrieval
resource "aws_iam_policy" "apprunner_instance_policy" {
  name        = "${var.service_name}-policy-${var.environment}"
  description = "Permissions for OmniSight container to write logs and read secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogging"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "${aws_cloudwatch_log_group.omnisight_logs.arn}:*"
      },
      {
        Sid    = "SecretsAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:omnisight/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_policy_attach" {
  role       = aws_iam_role.apprunner_instance_role.name
  policy_arn = aws_iam_policy.apprunner_instance_policy.arn
}

# ------------------------------------------------------------------------------
# AWS App Runner Service (Fully Managed, Auto-Scaling Container Gateway)
# ------------------------------------------------------------------------------
resource "aws_apprunner_service" "omnisight_gateway" {
  service_name = "${var.service_name}-${var.environment}"

  source_configuration {
    auto_deployments_enabled = false

    image_repository {
      image_identifier      = var.container_image
      image_repository_type = "ECR"

      image_configuration {
        port = tostring(var.container_port)

        runtime_environment_variables = {
          APP_ENV              = var.environment
          BACKEND_PORT         = tostring(var.container_port)
          ALLOWED_TARGET_HOSTS = var.allowed_target_hosts
          REPO_NAME            = var.github_repo
          MOCK_GITHUB          = tostring(var.mock_github)
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
    path                = var.health_check_path
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 3
  }
}
