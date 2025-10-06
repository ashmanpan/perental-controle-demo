# DynamoDB Tables for Parental Control

# Table 1: ParentalPolicies
resource "aws_dynamodb_table" "parental_policies" {
  name           = "${local.name_prefix}-parental-policies"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "childPhoneNumber"
  range_key      = "policyId"
  stream_enabled = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "childPhoneNumber"
    type = "S"
  }

  attribute {
    name = "policyId"
    type = "S"
  }

  attribute {
    name = "parentEmail"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "S"
  }

  global_secondary_index {
    name            = "ParentEmailIndex"
    hash_key        = "parentEmail"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-parental-policies"
  })
}

# Table 2: ApplicationRegistry
resource "aws_dynamodb_table" "application_registry" {
  name         = "${local.name_prefix}-application-registry"
  billing_mode = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 1
  hash_key     = "appName"

  attribute {
    name = "appName"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-application-registry"
  })
}

# Table 3: EnforcementHistory
resource "aws_dynamodb_table" "enforcement_history" {
  name         = "${local.name_prefix}-enforcement-history"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "childPhoneNumber"
  range_key    = "timestamp"

  attribute {
    name = "childPhoneNumber"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "StatusTimestampIndex"
    hash_key        = "status"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # Enable TTL to auto-delete old records after 90 days
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-enforcement-history"
  })
}

# Table 4: BlockedRequestMetrics
resource "aws_dynamodb_table" "blocked_request_metrics" {
  name         = "${local.name_prefix}-blocked-request-metrics"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "childPhoneNumber"
  range_key    = "dateApp"

  attribute {
    name = "childPhoneNumber"
    type = "S"
  }

  attribute {
    name = "dateApp"
    type = "S"
  }

  attribute {
    name = "parentEmail"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  global_secondary_index {
    name            = "ParentEmailDateIndex"
    hash_key        = "parentEmail"
    range_key       = "date"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup after 1 year
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-blocked-request-metrics"
  })
}

# Table 5: FTDRuleMapping
resource "aws_dynamodb_table" "ftd_rule_mapping" {
  name           = "${local.name_prefix}-ftd-rule-mapping"
  billing_mode   = "PROVISIONED"
  read_capacity  = 20
  write_capacity = 20
  hash_key       = "childPhoneNumber"
  range_key      = "ruleId"

  attribute {
    name = "childPhoneNumber"
    type = "S"
  }

  attribute {
    name = "ruleId"
    type = "S"
  }

  # TTL for automatic cleanup when sessions expire
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ftd-rule-mapping"
  })
}

# Outputs
output "dynamodb_parental_policies_table" {
  value = aws_dynamodb_table.parental_policies.name
}

output "dynamodb_parental_policies_stream_arn" {
  value = aws_dynamodb_table.parental_policies.stream_arn
}

output "dynamodb_application_registry_table" {
  value = aws_dynamodb_table.application_registry.name
}

output "dynamodb_enforcement_history_table" {
  value = aws_dynamodb_table.enforcement_history.name
}

output "dynamodb_blocked_request_metrics_table" {
  value = aws_dynamodb_table.blocked_request_metrics.name
}

output "dynamodb_ftd_rule_mapping_table" {
  value = aws_dynamodb_table.ftd_rule_mapping.name
}
