# Amazon ECS Fargate Configuration

# ECS Cluster
resource "aws_ecs_cluster" "parental_control" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-cluster"
  })
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${local.name_prefix}-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-tasks-sg"
  })
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Tasks (Application)
resource "aws_iam_role" "ecs_task_role" {
  name = "${local.name_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

# Policy for ECS tasks to access AWS services
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${local.name_prefix}-ecs-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DeleteItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.parental_policies.arn,
          aws_dynamodb_table.application_registry.arn,
          aws_dynamodb_table.enforcement_history.arn,
          aws_dynamodb_table.blocked_request_metrics.arn,
          aws_dynamodb_table.ftd_rule_mapping.arn,
          "${aws_dynamodb_table.parental_policies.arn}/index/*",
          "${aws_dynamodb_table.blocked_request_metrics.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = [
          aws_sqs_queue.enforcement_requests.arn,
          aws_sqs_queue.enforcement_dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "p_gateway" {
  name              = "/ecs/${local.name_prefix}/p-gateway"
  retention_in_days = var.cloudwatch_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "kafka_subscriber" {
  name              = "/ecs/${local.name_prefix}/kafka-subscriber"
  retention_in_days = var.cloudwatch_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "policy_enforcer" {
  name              = "/ecs/${local.name_prefix}/policy-enforcer"
  retention_in_days = var.cloudwatch_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "ftd_integration" {
  name              = "/ecs/${local.name_prefix}/ftd-integration"
  retention_in_days = var.cloudwatch_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "analytics_dashboard" {
  name              = "/ecs/${local.name_prefix}/analytics-dashboard"
  retention_in_days = var.cloudwatch_retention_days
  tags              = local.common_tags
}

# 1. P-Gateway Simulator Task Definition
resource "aws_ecs_task_definition" "p_gateway" {
  family                   = "${local.name_prefix}-p-gateway"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "p-gateway-simulator"
    image = "${aws_ecr_repository.p_gateway.repository_url}:latest"

    environment = [
      { name = "KAFKA_BOOTSTRAP_SERVERS", value = aws_msk_cluster.parental_control.bootstrap_brokers_tls },
      { name = "KAFKA_TOPIC", value = "session-data" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "LOG_LEVEL", value = "INFO" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.p_gateway.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = local.common_tags
}

# 2. Kafka Subscriber Task Definition
resource "aws_ecs_task_definition" "kafka_subscriber" {
  family                   = "${local.name_prefix}-kafka-subscriber"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "kafka-subscriber"
    image = "${aws_ecr_repository.kafka_subscriber.repository_url}:latest"

    environment = [
      { name = "KAFKA_BOOTSTRAP_SERVERS", value = aws_msk_cluster.parental_control.bootstrap_brokers_tls },
      { name = "KAFKA_TOPIC", value = "session-data" },
      { name = "KAFKA_GROUP_ID", value = "parental-control-subscriber" },
      { name = "REDIS_HOST", value = aws_elasticache_replication_group.parental_control.primary_endpoint_address },
      { name = "REDIS_PORT", value = "6379" },
      { name = "DYNAMODB_TABLE_POLICIES", value = aws_dynamodb_table.parental_policies.name },
      { name = "SQS_QUEUE_URL", value = aws_sqs_queue.enforcement_requests.url },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "LOG_LEVEL", value = "INFO" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.kafka_subscriber.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = local.common_tags
}

# 3. Policy Enforcer Task Definition
resource "aws_ecs_task_definition" "policy_enforcer" {
  family                   = "${local.name_prefix}-policy-enforcer"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "policy-enforcer"
    image = "${aws_ecr_repository.policy_enforcer.repository_url}:latest"

    environment = [
      { name = "SQS_QUEUE_URL", value = aws_sqs_queue.enforcement_requests.url },
      { name = "REDIS_HOST", value = aws_elasticache_replication_group.parental_control.primary_endpoint_address },
      { name = "REDIS_PORT", value = "6379" },
      { name = "DYNAMODB_TABLE_POLICIES", value = aws_dynamodb_table.parental_policies.name },
      { name = "DYNAMODB_TABLE_ENFORCEMENT_HISTORY", value = aws_dynamodb_table.enforcement_history.name },
      { name = "DYNAMODB_TABLE_METRICS", value = aws_dynamodb_table.blocked_request_metrics.name },
      { name = "DYNAMODB_TABLE_FTD_RULES", value = aws_dynamodb_table.ftd_rule_mapping.name },
      { name = "FTD_INTEGRATION_URL", value = "http://ftd-integration:5000" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "LOG_LEVEL", value = "INFO" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.policy_enforcer.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = local.common_tags
}

# 4. FTD Integration Task Definition
resource "aws_ecs_task_definition" "ftd_integration" {
  family                   = "${local.name_prefix}-ftd-integration"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "ftd-integration"
    image = "${aws_ecr_repository.ftd_integration.repository_url}:latest"

    portMappings = [{
      containerPort = 5000
      protocol      = "tcp"
    }]

    environment = [
      { name = "FTD_HOST", value = var.ftd_host },
      { name = "FTD_USERNAME", value = var.ftd_username },
      { name = "FTD_PASSWORD", value = var.ftd_password },
      { name = "API_PORT", value = "5000" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "LOG_LEVEL", value = "INFO" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ftd_integration.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:5000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = local.common_tags
}

# 5. Analytics Dashboard Task Definition
resource "aws_ecs_task_definition" "analytics_dashboard" {
  family                   = "${local.name_prefix}-analytics-dashboard"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "analytics-dashboard"
    image = "${aws_ecr_repository.analytics_dashboard.repository_url}:latest"

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "DYNAMODB_TABLE_POLICIES", value = aws_dynamodb_table.parental_policies.name },
      { name = "DYNAMODB_TABLE_METRICS", value = aws_dynamodb_table.blocked_request_metrics.name },
      { name = "DYNAMODB_TABLE_ENFORCEMENT_HISTORY", value = aws_dynamodb_table.enforcement_history.name },
      { name = "API_PORT", value = "8000" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "LOG_LEVEL", value = "INFO" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.analytics_dashboard.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = local.common_tags
}

# ECS Services
resource "aws_ecs_service" "p_gateway" {
  name            = "${local.name_prefix}-p-gateway-service"
  cluster         = aws_ecs_cluster.parental_control.id
  task_definition = aws_ecs_task_definition.p_gateway.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-p-gateway-service"
  })
}

resource "aws_ecs_service" "kafka_subscriber" {
  name            = "${local.name_prefix}-kafka-subscriber-service"
  cluster         = aws_ecs_cluster.parental_control.id
  task_definition = aws_ecs_task_definition.kafka_subscriber.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-kafka-subscriber-service"
  })
}

resource "aws_ecs_service" "policy_enforcer" {
  name            = "${local.name_prefix}-policy-enforcer-service"
  cluster         = aws_ecs_cluster.parental_control.id
  task_definition = aws_ecs_task_definition.policy_enforcer.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-policy-enforcer-service"
  })
}

# FTD Integration and Analytics Dashboard services would use load balancers in production
# For now, they're internal services

resource "aws_ecs_service" "ftd_integration" {
  name            = "${local.name_prefix}-ftd-integration-service"
  cluster         = aws_ecs_cluster.parental_control.id
  task_definition = aws_ecs_task_definition.ftd_integration.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.ftd_integration.arn
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ftd-integration-service"
  })
}

resource "aws_ecs_service" "analytics_dashboard" {
  name            = "${local.name_prefix}-analytics-dashboard-service"
  cluster         = aws_ecs_cluster.parental_control.id
  task_definition = aws_ecs_task_definition.analytics_dashboard.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-analytics-dashboard-service"
  })
}

# Service Discovery for internal service-to-service communication
resource "aws_service_discovery_private_dns_namespace" "parental_control" {
  name        = "${local.name_prefix}.local"
  description = "Private DNS namespace for parental control services"
  vpc         = aws_vpc.main.id

  tags = local.common_tags
}

resource "aws_service_discovery_service" "ftd_integration" {
  name = "ftd-integration"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.parental_control.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = local.common_tags
}

# Outputs
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.parental_control.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.parental_control.arn
}
