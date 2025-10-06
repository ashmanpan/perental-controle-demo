variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"  # Mumbai region
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# MSK Configuration
variable "msk_instance_type" {
  description = "MSK broker instance type"
  type        = string
  default     = "kafka.t3.small"
}

variable "msk_broker_count" {
  description = "Number of MSK brokers"
  type        = number
  default     = 3
}

variable "msk_kafka_version" {
  description = "Kafka version"
  type        = string
  default     = "3.5.1"
}

# ElastiCache (Redis) Configuration
variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_num_cache_clusters" {
  description = "Number of Redis cache clusters (replicas)"
  type        = number
  default     = 2
}

# ECS Configuration
variable "ecs_task_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "ECS task memory (MB)"
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_min_capacity" {
  description = "Minimum ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_max_capacity" {
  description = "Maximum ECS tasks"
  type        = number
  default     = 10
}

# FTD Configuration
variable "ftd_host" {
  description = "Cisco FTD/FMC hostname or IP"
  type        = string
  sensitive   = true
}

variable "ftd_username" {
  description = "FTD username"
  type        = string
  sensitive   = true
}

variable "ftd_password" {
  description = "FTD password"
  type        = string
  sensitive   = true
}

# Docker Image Configuration
variable "ecr_p_gateway_image" {
  description = "P-Gateway simulator Docker image"
  type        = string
  default     = "p-gateway-simulator:latest"
}

variable "ecr_kafka_subscriber_image" {
  description = "Kafka subscriber Docker image"
  type        = string
  default     = "kafka-subscriber:latest"
}

variable "ecr_policy_enforcer_image" {
  description = "Policy enforcer Docker image"
  type        = string
  default     = "policy-enforcer:latest"
}

# CloudWatch Configuration
variable "cloudwatch_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# Tags
variable "additional_tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
