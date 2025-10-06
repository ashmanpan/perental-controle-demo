# Amazon ElastiCache (Redis) Configuration

resource "aws_elasticache_subnet_group" "parental_control" {
  name       = "${local.name_prefix}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-subnet-group"
  })
}

resource "aws_elasticache_replication_group" "parental_control" {
  replication_group_id = "${local.name_prefix}-redis"
  description          = "Redis cluster for parental control IP/phone mappings"

  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.redis_node_type
  num_cache_clusters   = var.redis_num_cache_clusters
  port                 = 6379

  # Networking
  subnet_group_name  = aws_elasticache_subnet_group.parental_control.name
  security_group_ids = [aws_security_group.redis.id]

  # High Availability
  automatic_failover_enabled = true
  multi_az_enabled           = true

  # Backup and Maintenance
  snapshot_retention_limit = 5
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "mon:05:00-mon:07:00"

  # Security
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = false  # Can enable for additional security

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Logs
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-cluster"
  })
}

# Security Group for Redis
resource "aws_security_group" "redis" {
  name        = "${local.name_prefix}-redis-sg"
  description = "Security group for Redis cluster"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-sg"
  })
}

# CloudWatch Log Group for Redis
resource "aws_cloudwatch_log_group" "redis" {
  name              = "/aws/elasticache/${local.name_prefix}"
  retention_in_days = var.cloudwatch_retention_days

  tags = local.common_tags
}

# Output Redis endpoint
output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.parental_control.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.parental_control.port
}
