# Amazon SQS Configuration

# Main enforcement requests queue
resource "aws_sqs_queue" "enforcement_requests" {
  name                       = "${local.name_prefix}-enforcement-requests"
  visibility_timeout_seconds = 300  # 5 minutes
  message_retention_seconds  = 86400  # 24 hours
  max_message_size          = 262144  # 256 KB
  delay_seconds             = 0
  receive_wait_time_seconds = 20  # Long polling

  # Dead letter queue
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.enforcement_dlq.arn
    maxReceiveCount     = 3
  })

  # Encryption
  sqs_managed_sse_enabled = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-enforcement-queue"
  })
}

# Dead Letter Queue for failed enforcement requests
resource "aws_sqs_queue" "enforcement_dlq" {
  name                      = "${local.name_prefix}-enforcement-dlq"
  message_retention_seconds = 1209600  # 14 days
  sqs_managed_sse_enabled   = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-enforcement-dlq"
  })
}

# Queue policy for ECS tasks
resource "aws_sqs_queue_policy" "enforcement_requests" {
  queue_url = aws_sqs_queue.enforcement_requests.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ecs_task_execution.arn
        }
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = aws_sqs_queue.enforcement_requests.arn
      }
    ]
  })
}

# CloudWatch Alarms for SQS
resource "aws_cloudwatch_metric_alarm" "sqs_high_message_count" {
  alarm_name          = "${local.name_prefix}-sqs-high-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"  # 5 minutes
  statistic           = "Average"
  threshold           = "1000"
  alarm_description   = "Alert when SQS queue has > 1000 messages"

  dimensions = {
    QueueName = aws_sqs_queue.enforcement_requests.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "sqs_dlq_messages" {
  alarm_name          = "${local.name_prefix}-sqs-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when messages appear in DLQ"

  dimensions = {
    QueueName = aws_sqs_queue.enforcement_dlq.name
  }

  tags = local.common_tags
}

# Outputs
output "sqs_queue_url" {
  description = "SQS enforcement queue URL"
  value       = aws_sqs_queue.enforcement_requests.url
}

output "sqs_queue_arn" {
  description = "SQS enforcement queue ARN"
  value       = aws_sqs_queue.enforcement_requests.arn
}

output "sqs_dlq_url" {
  description = "SQS DLQ URL"
  value       = aws_sqs_queue.enforcement_dlq.url
}
