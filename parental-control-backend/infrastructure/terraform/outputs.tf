# Consolidated Outputs

# VPC Outputs
output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

# NAT Gateway IPs
output "nat_gateway_ips" {
  description = "NAT Gateway public IPs"
  value       = aws_eip.nat[*].public_ip
}

# Account Info
output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS Region"
  value       = var.aws_region
}

# DynamoDB Tables
output "dynamodb_table_names" {
  description = "DynamoDB table names"
  value = {
    policies     = aws_dynamodb_table.parental_policies.name
    app_registry = aws_dynamodb_table.application_registry.name
    enforcement  = aws_dynamodb_table.enforcement_history.name
    metrics      = aws_dynamodb_table.blocked_request_metrics.name
    ftd_rules    = aws_dynamodb_table.ftd_rule_mapping.name
  }
}

# Service Discovery
output "service_discovery_namespace" {
  description = "Service Discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.parental_control.name
}

# Quick Start Commands
output "quick_start_commands" {
  description = "Quick start commands for deployment"
  value = <<-EOT

    ==========================================
    DEPLOYMENT SUCCESSFUL!
    ==========================================

    Next Steps:

    1. Build and Push Docker Images:
       cd ../../../
       ./scripts/build-and-push.sh

    2. View Services:
       aws ecs list-services --cluster ${aws_ecs_cluster.parental_control.name} --region ${var.aws_region}

    3. View Logs:
       aws logs tail /ecs/${local.name_prefix}/p-gateway --follow --region ${var.aws_region}

    4. Access MSK:
       Bootstrap Brokers: ${aws_msk_cluster.parental_control.bootstrap_brokers_tls}

    5. Access Redis:
       Endpoint: ${aws_elasticache_replication_group.parental_control.primary_endpoint_address}:6379

    6. SQS Queue:
       URL: ${aws_sqs_queue.enforcement_requests.url}

    ==========================================
  EOT
}
