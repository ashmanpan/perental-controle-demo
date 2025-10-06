# Amazon MSK (Kafka) Configuration

resource "aws_msk_configuration" "parental_control" {
  name              = "${local.name_prefix}-msk-config"
  kafka_versions    = [var.msk_kafka_version]
  server_properties = <<PROPERTIES
auto.create.topics.enable=true
default.replication.factor=3
min.insync.replicas=2
num.partitions=6
log.retention.hours=168
compression.type=gzip
PROPERTIES
}

resource "aws_msk_cluster" "parental_control" {
  cluster_name           = "${local.name_prefix}-kafka"
  kafka_version          = var.msk_kafka_version
  number_of_broker_nodes = var.msk_broker_count

  broker_node_group_info {
    instance_type   = var.msk_instance_type
    client_subnets  = aws_subnet.private[*].id
    security_groups = [aws_security_group.msk.id]

    storage_info {
      ebs_storage_info {
        volume_size = 500  # 500 GB per broker
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
    encryption_at_rest_kms_key_arn = aws_kms_key.msk.arn
  }

  configuration_info {
    arn      = aws_msk_configuration.parental_control.arn
    revision = aws_msk_configuration.parental_control.latest_revision
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-kafka-cluster"
  })
}

# KMS key for MSK encryption
resource "aws_kms_key" "msk" {
  description             = "KMS key for MSK encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-msk-kms"
  })
}

resource "aws_kms_alias" "msk" {
  name          = "alias/${local.name_prefix}-msk"
  target_key_id = aws_kms_key.msk.key_id
}

# Security Group for MSK
resource "aws_security_group" "msk" {
  name        = "${local.name_prefix}-msk-sg"
  description = "Security group for MSK cluster"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Kafka from ECS"
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  ingress {
    description     = "Kafka TLS from ECS"
    from_port       = 9094
    to_port         = 9094
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
    Name = "${local.name_prefix}-msk-sg"
  })
}

# CloudWatch Log Group for MSK
resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${local.name_prefix}"
  retention_in_days = var.cloudwatch_retention_days

  tags = local.common_tags
}

# Output MSK bootstrap brokers
output "msk_bootstrap_brokers" {
  description = "MSK bootstrap brokers"
  value       = aws_msk_cluster.parental_control.bootstrap_brokers_tls
  sensitive   = true
}

output "msk_zookeeper_connect" {
  description = "MSK Zookeeper connection string"
  value       = aws_msk_cluster.parental_control.zookeeper_connect_string
  sensitive   = true
}
