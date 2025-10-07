# CloudFormation Infrastructure

AWS CloudFormation template for Cisco AI Family Safety Parental Control system.

## Why CloudFormation?

✅ **No installation needed** - AWS CLI already configured
✅ **AWS-native** - better AWS service integration
✅ **Built-in state management** - no S3/DynamoDB setup needed
✅ **Change sets** - preview changes before applying
✅ **Automatic rollback** - on deployment failures

## Files

- **infrastructure.yaml** - Main CloudFormation template (all resources)
- **parameters.json** - Parameter values for deployment
- **README.md** - This file

## Resources Created

### Networking (VPC)
- VPC (10.0.0.0/16)
- 3 Public subnets
- 3 Private subnets
- 3 NAT Gateways
- Internet Gateway
- Route tables
- VPC Endpoints (S3, DynamoDB)

### Data Services
- **Amazon MSK (Kafka)** - 3 broker cluster
- **ElastiCache (Redis)** - Multi-AZ with replication
- **DynamoDB** - 5 tables:
  - ParentalPolicies
  - ApplicationRegistry
  - EnforcementHistory
  - BlockedRequestMetrics
  - FTDRuleMapping

### Messaging & Queues
- **SQS Queue** - Enforcement requests
- **SQS DLQ** - Dead letter queue

### Container Infrastructure
- **ECR Repositories** - 5 repositories for Docker images
- **ECS Fargate Cluster** - Container orchestration
- **ECS Services** - 5 microservices:
  - P-Gateway Simulator
  - Kafka Subscriber
  - Policy Enforcer
  - FTD Integration
  - Analytics Dashboard

### Security & Monitoring
- **Security Groups** - ECS, MSK, Redis
- **IAM Roles** - ECS task execution and task roles
- **KMS Keys** - MSK encryption
- **CloudWatch Logs** - All services
- **CloudWatch Alarms** - SQS monitoring

## Quick Start

### 1. Validate Template

```bash
aws cloudformation validate-template \
  --template-body file://infrastructure.yaml \
  --region ap-south-1
```

### 2. Deploy Stack

```bash
# Automated deployment
cd /home/kpanse/wsl-myprojects/parental-control-demo
./deploy-to-aws-cloudformation.sh
```

**OR** manually:

```bash
aws cloudformation create-stack \
  --stack-name parental-control-prod \
  --template-body file://infrastructure.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1
```

### 3. Monitor Deployment

```bash
# Watch stack events
aws cloudformation describe-stack-events \
  --stack-name parental-control-prod \
  --region ap-south-1 \
  --max-items 20

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name parental-control-prod \
  --region ap-south-1
```

### 4. Get Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name parental-control-prod \
  --region ap-south-1 \
  --query 'Stacks[0].Outputs' \
  --output table
```

## Parameters

Edit `parameters.json` to customize your deployment:

| Parameter | Default | Description |
|-----------|---------|-------------|
| Environment | prod | Environment name (dev/staging/prod) |
| VpcCidr | 10.0.0.0/16 | VPC CIDR block |
| MSKInstanceType | kafka.m5.large | MSK broker instance type |
| MSKBrokerCount | 3 | Number of MSK brokers |
| MSKKafkaVersion | 3.5.1 | Kafka version |
| RedisNodeType | cache.r6g.large | Redis node type |
| RedisNumCacheClusters | 2 | Number of Redis replicas |
| ECSTaskCPU | 1024 | ECS task CPU units |
| ECSTaskMemory | 2048 | ECS task memory (MB) |
| ECSDesiredCount | 2 | Desired ECS tasks per service |
| FTDHost | "" | Cisco FTD hostname/IP |
| FTDUsername | admin | FTD username |
| FTDPassword | "" | FTD password |
| CloudWatchRetentionDays | 30 | Log retention in days |

## Update Stack

```bash
aws cloudformation update-stack \
  --stack-name parental-control-prod \
  --template-body file://infrastructure.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1
```

## Create Change Set (Preview Changes)

```bash
# Create change set
aws cloudformation create-change-set \
  --stack-name parental-control-prod \
  --change-set-name my-changes \
  --template-body file://infrastructure.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1

# View changes
aws cloudformation describe-change-set \
  --stack-name parental-control-prod \
  --change-set-name my-changes \
  --region ap-south-1

# Execute change set
aws cloudformation execute-change-set \
  --stack-name parental-control-prod \
  --change-set-name my-changes \
  --region ap-south-1
```

## Delete Stack

```bash
aws cloudformation delete-stack \
  --stack-name parental-control-prod \
  --region ap-south-1

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name parental-control-prod \
  --region ap-south-1
```

## Outputs

The stack provides these outputs:

### Network
- VpcId, VpcCidr
- PrivateSubnetIds, PublicSubnetIds
- NatGatewayIPs

### DynamoDB
- ParentalPoliciesTableName
- ApplicationRegistryTableName
- EnforcementHistoryTableName
- BlockedRequestMetricsTableName
- FTDRuleMappingTableName

### MSK (Kafka)
- MSKClusterArn
- MSKBootstrapBrokers

### Redis
- RedisEndpoint
- RedisPort

### SQS
- SQSQueueUrl, SQSQueueArn
- SQSDLQUrl

### ECR
- PGatewayECRUrl
- KafkaSubscriberECRUrl
- PolicyEnforcerECRUrl
- FTDIntegrationECRUrl
- AnalyticsDashboardECRUrl

### ECS
- ECSClusterName, ECSClusterArn
- ServiceDiscoveryNamespace

## Cost Estimate

**Monthly Cost (Mumbai region)**: ~₹1,13,000 (~$1,350 USD)

| Service | Monthly Cost |
|---------|--------------|
| Amazon MSK (3 x kafka.m5.large) | ₹45,000 |
| ElastiCache (2 x cache.r6g.large) | ₹15,000 |
| ECS Fargate (5 services x 2 tasks) | ₹20,000 |
| NAT Gateways (3) | ₹7,500 |
| DynamoDB | ₹3,000 |
| Data Transfer | ₹4,000 |
| Other (CloudWatch, ECR, etc.) | ₹500 |

## Troubleshooting

### Stack Creation Failed

```bash
# View stack events to see error
aws cloudformation describe-stack-events \
  --stack-name parental-control-prod \
  --region ap-south-1 \
  --max-items 50

# Stack will automatically rollback on failure
```

### Update Failed

```bash
# Check current stack status
aws cloudformation describe-stacks \
  --stack-name parental-control-prod \
  --region ap-south-1 \
  --query 'Stacks[0].StackStatus'

# Cancel update if stuck
aws cloudformation cancel-update-stack \
  --stack-name parental-control-prod \
  --region ap-south-1
```

### View Specific Resource

```bash
# List all resources in stack
aws cloudformation list-stack-resources \
  --stack-name parental-control-prod \
  --region ap-south-1

# Describe specific resource
aws cloudformation describe-stack-resource \
  --stack-name parental-control-prod \
  --logical-resource-id ECSCluster \
  --region ap-south-1
```

## Best Practices

1. **Use Change Sets** - Preview changes before applying
2. **Tag Resources** - All resources tagged with Project and Environment
3. **Enable Rollback** - CloudFormation automatically rolls back on failure
4. **Parameter Files** - Use separate parameter files for dev/staging/prod
5. **Version Control** - Commit template changes to git
6. **Stack Policies** - Protect critical resources from accidental deletion

## Additional Commands

```bash
# Export stack template
aws cloudformation get-template \
  --stack-name parental-control-prod \
  --region ap-south-1 > current-template.yaml

# Estimate cost (requires AWS Cost Explorer)
aws cloudformation estimate-template-cost \
  --template-body file://infrastructure.yaml \
  --parameters file://parameters.json \
  --region ap-south-1

# Drift detection (check if resources changed outside CloudFormation)
aws cloudformation detect-stack-drift \
  --stack-name parental-control-prod \
  --region ap-south-1
```

## Support

- **Documentation**: See [DEPLOYMENT_GUIDE.md](../../../DEPLOYMENT_GUIDE.md)
- **Design**: See [DESIGN.md](../../../DESIGN.md)
- **Status**: See [WHAT_IS_WORKING_AND_NOT_WORKING.md](../../../WHAT_IS_WORKING_AND_NOT_WORKING.md)

---

**Ready to deploy?** Run `./deploy-to-aws-cloudformation.sh` from project root! 🚀
