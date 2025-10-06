# AWS Region
aws_region = "ap-south-1"  # Mumbai

# Environment
environment = "prod"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

# MSK (Kafka) Configuration
msk_instance_type = "kafka.m5.large"  # Production instance
msk_broker_count  = 3                  # High availability
msk_kafka_version = "3.5.1"

# ElastiCache (Redis) Configuration
redis_node_type           = "cache.r6g.large"  # Production instance
redis_num_cache_clusters  = 2                   # Primary + 1 replica

# ECS Fargate Configuration
ecs_task_cpu      = 1024   # 1 vCPU
ecs_task_memory   = 2048   # 2 GB RAM
ecs_desired_count = 2      # 2 tasks per service
ecs_min_capacity  = 2      # Min auto-scaling
ecs_max_capacity  = 10     # Max auto-scaling

# CloudWatch Logs
cloudwatch_retention_days = 90  # 90 days retention

# FTD Configuration (Placeholder - will be updated after FTD deployment)
ftd_host     = "ftd-placeholder.local"
ftd_username = "admin"
ftd_password = "ChangeMeAfterDeployment"

# Additional Tags
additional_tags = {
  Owner       = "Cisco-AI-Family-Safety"
  CostCenter  = "Engineering"
  Compliance  = "Required"
}
