# Deployment Guide - Parental Control Backend

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [AWS Deployment](#aws-deployment)
3. [Configuration](#configuration)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites
- Docker & Docker Compose (>= v2.0)
- Python 3.11+
- AWS CLI
- cloudformation >= 1.5.0

### Step 1: Start Local Services

```bash
cd deployment/docker
docker-compose up -d
```

This will start:
- **Kafka** (port 9092)
- **Zookeeper** (port 2181)
- **Redis** (port 6379)
- **DynamoDB Local** (port 8000)
- **Kafka UI** (port 8080) - http://localhost:8080
- **Redis Commander** (port 8081) - http://localhost:8081
- **DynamoDB Admin** (port 8001) - http://localhost:8001

### Step 2: Create DynamoDB Tables Locally

```bash
cd scripts
./setup-dynamodb-local.sh
```

Or manually using AWS CLI:

```bash
aws dynamodb create-table \
    --table-name ParentalPolicies \
    --attribute-definitions \
        AttributeName=childPhoneNumber,AttributeType=S \
        AttributeName=policyId,AttributeType=S \
    --key-schema \
        AttributeName=childPhoneNumber,KeyType=HASH \
        AttributeName=policyId,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url http://localhost:8000 \
    --region ap-south-1
```

### Step 3: Seed Test Data

```bash
python scripts/seed-data.py --endpoint http://localhost:8000
```

### Step 4: Run Services Locally

#### Terminal 1: P-Gateway Simulator
```bash
cd services/p-gateway-simulator
pip install -r requirements.txt
python src/generator.py
```

#### Terminal 2: Kafka Subscriber
```bash
cd services/kafka-subscriber
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export REDIS_HOST=localhost
export DYNAMODB_ENDPOINT=http://localhost:8000
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
python src/consumer.py
```

### Step 5: Verify Data Flow

1. **Check Kafka Messages**: http://localhost:8080
   - Topic: `session-data`
   - Should see SESSION_START events

2. **Check Redis Data**: http://localhost:8081
   - Keys: `imsi:*`, `phone:*`, `ip:*`

3. **Check DynamoDB**: http://localhost:8001
   - Tables should have data

---

## AWS Deployment

### Step 1: Configure AWS Credentials

```bash
aws configure
# Use Mumbai region: ap-south-1
```

### Step 2: Create S3 Bucket for cloudformation State

```bash
aws s3 mb s3://parental-control-cloudformation-state-mumbai --region ap-south-1
aws s3api put-bucket-versioning \
    --bucket parental-control-cloudformation-state-mumbai \
    --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
    --table-name cloudformation-state-lock \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region ap-south-1
```

### Step 3: Initialize cloudformation

```bash
cd infrastructure/cloudformation
cloudformation init
```

### Step 4: Create Variables File

Create `cloudformation.yamlvars`:

```hcl
aws_region   = "ap-south-1"
environment  = "prod"

# FTD Configuration
ftd_host     = "ftd.example.com"
ftd_username = "admin"
ftd_password = "SecurePassword123!"  # Use AWS Secrets Manager instead

# Network Configuration
vpc_cidr             = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

# MSK Configuration
msk_instance_type  = "kafka.m5.large"
msk_broker_count   = 3
msk_kafka_version  = "3.5.1"

# ElastiCache Configuration
redis_node_type          = "cache.r6g.large"
redis_num_cache_clusters = 2

# ECS Configuration
ecs_task_cpu       = 1024
ecs_task_memory    = 2048
ecs_desired_count  = 2
ecs_min_capacity   = 2
ecs_max_capacity   = 10
```

### Step 5: Plan Infrastructure

```bash
cloudformation plan -var-file=cloudformation.yamlvars
```

### Step 6: Deploy Infrastructure

```bash
cloudformation apply -var-file=cloudformation.yamlvars
```

This will create:
- VPC with public/private subnets across 3 AZs
- NAT Gateways for private subnet internet access
- Amazon MSK (Kafka) cluster with 3 brokers
- ElastiCache (Redis) cluster with replication
- DynamoDB tables (5 tables)
- SQS queues for policy enforcement
- ECS cluster and task definitions
- IAM roles and policies
- CloudWatch log groups and dashboards
- Secrets Manager for FTD credentials

**Estimated Cost** (Mumbai region):
- MSK (3 x m5.large): ~$600/month
- ElastiCache (2 x r6g.large): ~$200/month
- ECS Fargate (2-10 tasks): ~$150-750/month
- DynamoDB (on-demand): ~$50-500/month (depends on traffic)
- NAT Gateway: ~$100/month
- Data transfer: ~$50-200/month
- **Total**: ~$1,150 - $2,400/month

### Step 7: Build and Push Docker Images

```bash
# Login to ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-south-1.amazonaws.com

# Build and push P-Gateway Simulator
cd services/p-gateway-simulator
docker build -t p-gateway-simulator:latest .
docker tag p-gateway-simulator:latest <account-id>.dkr.ecr.ap-south-1.amazonaws.com/p-gateway-simulator:latest
docker push <account-id>.dkr.ecr.ap-south-1.amazonaws.com/p-gateway-simulator:latest

# Build and push Kafka Subscriber
cd ../kafka-subscriber
docker build -t kafka-subscriber:latest .
docker tag kafka-subscriber:latest <account-id>.dkr.ecr.ap-south-1.amazonaws.com/kafka-subscriber:latest
docker push <account-id>.dkr.ecr.ap-south-1.amazonaws.com/kafka-subscriber:latest

# Repeat for other services
```

### Step 8: Deploy ECS Services

```bash
cd scripts
./deploy-services.sh prod
```

### Step 9: Seed Production Data

```bash
python scripts/seed-data.py --region ap-south-1
```

---

## Configuration

### Environment Variables

#### P-Gateway Simulator
```bash
KAFKA_BOOTSTRAP_SERVERS=<msk-endpoint>
KAFKA_TOPIC=session-data
SESSIONS_PER_SECOND=10
LOG_LEVEL=INFO
AWS_REGION=ap-south-1
```

#### Kafka Subscriber
```bash
KAFKA_BOOTSTRAP_SERVERS=<msk-endpoint>
KAFKA_TOPIC=session-data
KAFKA_GROUP_ID=parental-control-subscriber
REDIS_HOST=<elasticache-endpoint>
REDIS_PORT=6379
AWS_REGION=ap-south-1
DYNAMODB_TABLE_POLICIES=ParentalPolicies
DYNAMODB_TABLE_APP_REGISTRY=ApplicationRegistry
DYNAMODB_TABLE_HISTORY=EnforcementHistory
LOG_LEVEL=INFO
```

#### Policy Enforcer
```bash
AWS_REGION=ap-south-1
REDIS_HOST=<elasticache-endpoint>
DYNAMODB_TABLE_POLICIES=ParentalPolicies
SQS_ENFORCEMENT_QUEUE=<sqs-queue-url>
FTD_HOST=<from-secrets-manager>
FTD_USERNAME=<from-secrets-manager>
FTD_PASSWORD_SECRET_ARN=<secrets-manager-arn>
LOG_LEVEL=INFO
```

---

## Monitoring

### CloudWatch Dashboards

1. **Main Dashboard**: `parental-control-main`
   - Active sessions
   - Kafka consumer lag
   - Redis memory utilization
   - DynamoDB throttles
   - FTD API latency

2. **Cost Dashboard**: `parental-control-costs`
   - Service-wise cost breakdown
   - Data transfer costs
   - Projected monthly cost

### Key Metrics

| Metric | Threshold | Action |
|--------|-----------|--------|
| Kafka Consumer Lag | > 1000 | Scale up consumers |
| Redis Memory | > 80% | Increase node size |
| DynamoDB Read Throttles | > 10/min | Increase capacity |
| FTD API Error Rate | > 5% | Check FTD health |
| ECS CPU Utilization | > 70% | Scale up tasks |

### Alarms

```bash
aws cloudwatch describe-alarms --region ap-south-1
```

Critical alarms:
- `pc-prod-kafka-lag-critical`
- `pc-prod-redis-memory-high`
- `pc-prod-ftd-api-errors`
- `pc-prod-ecs-cpu-high`

---

## Troubleshooting

### Issue: Kafka Consumer Not Processing Messages

**Symptoms**: Consumer lag increasing, no new sessions in Redis

**Diagnosis**:
```bash
# Check consumer group status
docker exec -it pc-kafka kafka-consumer-groups \
    --bootstrap-server kafka:29092 \
    --describe --group parental-control-subscriber

# Check consumer logs
docker logs pc-kafka-subscriber
```

**Solution**:
- Check Kafka connectivity
- Verify consumer group ID
- Check for exceptions in logs
- Reset consumer offset if needed

---

### Issue: Redis Memory Full

**Symptoms**: Redis evicting keys, sessions disappearing

**Diagnosis**:
```bash
# Check Redis memory
redis-cli info memory

# Check key count
redis-cli dbsize
```

**Solution**:
- Increase `maxmemory` setting
- Verify TTL is set on all keys
- Scale up Redis node size
- Enable eviction policy: `allkeys-lru`

---

### Issue: DynamoDB Throttling

**Symptoms**: Write/read throttles in CloudWatch

**Diagnosis**:
```bash
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name UserErrors \
    --dimensions Name=TableName,Value=ParentalPolicies \
    --start-time 2025-10-03T00:00:00Z \
    --end-time 2025-10-03T23:59:59Z \
    --period 300 \
    --statistics Sum \
    --region ap-south-1
```

**Solution**:
- Switch to on-demand billing mode
- Increase provisioned capacity
- Implement exponential backoff
- Batch writes where possible

---

### Issue: FTD API Connection Failures

**Symptoms**: Enforcement history shows "failed" status

**Diagnosis**:
```bash
# Check FTD connectivity
curl -k https://<ftd-host>/api/fmc_platform/v1/auth/generatetoken

# Check security group rules
aws ec2 describe-security-groups --region ap-south-1

# Check secrets
aws secretsmanager get-secret-value \
    --secret-id ftd-credentials \
    --region ap-south-1
```

**Solution**:
- Verify FTD IP/hostname
- Check security group allows outbound HTTPS
- Verify credentials in Secrets Manager
- Check FTD certificate validity

---

## Rollback Procedure

### cloudformation Rollback

```bash
cd infrastructure/cloudformation

# View previous state versions
cloudformation state list

# Rollback to previous version
cloudformation apply -var-file=cloudformation.yamlvars -target=<resource>

# Or full rollback
cloudformation destroy -var-file=cloudformation.yamlvars
```

### ECS Service Rollback

```bash
# Rollback to previous task definition
aws ecs update-service \
    --cluster pc-prod-cluster \
    --service kafka-subscriber \
    --task-definition kafka-subscriber:5 \
    --region ap-south-1
```

---

## Scaling

### Horizontal Scaling

**Kafka Subscriber**:
```bash
aws ecs update-service \
    --cluster pc-prod-cluster \
    --service kafka-subscriber \
    --desired-count 5 \
    --region ap-south-1
```

**Policy Enforcer**:
```bash
aws application-autoscaling put-scaling-policy \
    --policy-name pc-scale-out \
    --service-namespace ecs \
    --resource-id service/pc-prod-cluster/policy-enforcer \
    --scalable-dimension ecs:service:DesiredCount \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration \
        "TargetValue=70.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageCPUUtilization}"
```

### Vertical Scaling

**Redis**:
```bash
aws elasticache modify-replication-group \
    --replication-group-id pc-prod-redis \
    --cache-node-type cache.r6g.xlarge \
    --apply-immediately \
    --region ap-south-1
```

---

## Maintenance Windows

Schedule maintenance during low-traffic hours (2 AM - 5 AM IST).

```bash
# Stop P-Gateway simulator
aws ecs update-service \
    --cluster pc-prod-cluster \
    --service p-gateway-simulator \
    --desired-count 0

# Perform maintenance...

# Restart
aws ecs update-service \
    --cluster pc-prod-cluster \
    --service p-gateway-simulator \
    --desired-count 2
```

---

## Support

For deployment issues:
- GitHub Issues: https://github.com/yourorg/parental-control/issues
- Email: devops@example.com
- Slack: #parental-control-ops
