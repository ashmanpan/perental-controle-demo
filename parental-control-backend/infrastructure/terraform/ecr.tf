# Amazon ECR Repositories

# P-Gateway Simulator
resource "aws_ecr_repository" "p_gateway" {
  name                 = "${local.name_prefix}/p-gateway-simulator"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-p-gateway-repo"
    Service = "p-gateway-simulator"
  })
}

# Kafka Subscriber
resource "aws_ecr_repository" "kafka_subscriber" {
  name                 = "${local.name_prefix}/kafka-subscriber"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-kafka-subscriber-repo"
    Service = "kafka-subscriber"
  })
}

# Policy Enforcer
resource "aws_ecr_repository" "policy_enforcer" {
  name                 = "${local.name_prefix}/policy-enforcer"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-policy-enforcer-repo"
    Service = "policy-enforcer"
  })
}

# FTD Integration
resource "aws_ecr_repository" "ftd_integration" {
  name                 = "${local.name_prefix}/ftd-integration"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-ftd-integration-repo"
    Service = "ftd-integration"
  })
}

# Analytics Dashboard
resource "aws_ecr_repository" "analytics_dashboard" {
  name                 = "${local.name_prefix}/analytics-dashboard"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-analytics-dashboard-repo"
    Service = "analytics-dashboard"
  })
}

# Lifecycle policy to keep only last 10 images
resource "aws_ecr_lifecycle_policy" "cleanup_policy" {
  for_each = {
    p_gateway         = aws_ecr_repository.p_gateway.name
    kafka_subscriber  = aws_ecr_repository.kafka_subscriber.name
    policy_enforcer   = aws_ecr_repository.policy_enforcer.name
    ftd_integration   = aws_ecr_repository.ftd_integration.name
    analytics         = aws_ecr_repository.analytics_dashboard.name
  }

  repository = each.value

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# Outputs
output "ecr_p_gateway_url" {
  description = "ECR repository URL for P-Gateway"
  value       = aws_ecr_repository.p_gateway.repository_url
}

output "ecr_kafka_subscriber_url" {
  description = "ECR repository URL for Kafka Subscriber"
  value       = aws_ecr_repository.kafka_subscriber.repository_url
}

output "ecr_policy_enforcer_url" {
  description = "ECR repository URL for Policy Enforcer"
  value       = aws_ecr_repository.policy_enforcer.repository_url
}

output "ecr_ftd_integration_url" {
  description = "ECR repository URL for FTD Integration"
  value       = aws_ecr_repository.ftd_integration.repository_url
}

output "ecr_analytics_dashboard_url" {
  description = "ECR repository URL for Analytics Dashboard"
  value       = aws_ecr_repository.analytics_dashboard.repository_url
}
