# 🚀 Full AWS Deployment Guide

## Prerequisites Completed ✅
- ✅ AWS Account: 264314137331
- ✅ AWS Region: ap-south-1 (Mumbai)
- ✅ AWS CLI configured

## Estimated Costs
**Monthly**: ~₹1,13,000 (~$1,350 USD)
- MSK (Kafka): ₹45,000
- ElastiCache (Redis): ₹15,000
- ECS Fargate: ₹20,000
- Cisco FTD EC2: ₹18,000
- DynamoDB: ₹3,000
- NAT Gateway: ₹7,500
- Data Transfer: ₹4,000
- Other: ₹500

---

## Deployment Steps

### Step 1: Validate Template (1 minute)

```bash
cd /home/kpanse/wsl-myprojects/parental-control-demo

# Validate CloudFormation template
aws cloudformation validate-template \
  --template-body file://parental-control-backend/infrastructure/cloudformation/infrastructure.yaml \
  --region ap-south-1
```

### Step 2: Deploy Infrastructure with CloudFormation (45-60 minutes)

```bash
# Automated deployment (RECOMMENDED)
./deploy-to-aws.sh
```

**OR** manually:

```bash
aws cloudformation create-stack \
  --stack-name parental-control-prod \
  --template-body file://parental-control-backend/infrastructure/cloudformation/infrastructure.yaml \
  --parameters file://parental-control-backend/infrastructure/cloudformation/parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1

# Monitor progress
aws cloudformation wait stack-create-complete \
  --stack-name parental-control-prod \
  --region ap-south-1

# Get outputs
aws cloudformation describe-stacks \
  --stack-name parental-control-prod \
  --region ap-south-1 \
  --query 'Stacks[0].Outputs' \
  --output table > deployment-outputs.txt
```

**What this creates**:
- VPC with 3 public + 3 private subnets
- 3 NAT Gateways
- Amazon MSK (Kafka) - 3 broker cluster
- ElastiCache (Redis) - with replication
- 5 DynamoDB tables
- SQS queue + DLQ
- 5 ECR repositories
- ECS Fargate cluster
- Security groups, IAM roles
- CloudWatch logs and alarms

### Step 3: Build and Push Docker Images (15 minutes)

```bash
cd /home/kpanse/wsl-myprojects/parental-control-demo

# Get stack outputs
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-south-1"

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Get ECR URLs from CloudFormation outputs
get_output() {
  aws cloudformation describe-stacks \
    --stack-name parental-control-prod \
    --region $REGION \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text
}

ECR_P_GATEWAY=$(get_output "PGatewayECRUrl")
ECR_KAFKA=$(get_output "KafkaSubscriberECRUrl")
ECR_ENFORCER=$(get_output "PolicyEnforcerECRUrl")
ECR_FTD=$(get_output "FTDIntegrationECRUrl")
ECR_ANALYTICS=$(get_output "AnalyticsDashboardECRUrl")

# Build and push each service
cd parental-control-backend/services/p-gateway-simulator
docker build -t $ECR_P_GATEWAY:latest .
docker push $ECR_P_GATEWAY:latest

cd ../kafka-subscriber
docker build -t $ECR_KAFKA:latest .
docker push $ECR_KAFKA:latest

cd ../policy-enforcer
docker build -t $ECR_ENFORCER:latest .
docker push $ECR_ENFORCER:latest

cd ../ftd-integration
docker build -t $ECR_FTD:latest .
docker push $ECR_FTD:latest

cd ../analytics-dashboard
docker build -t $ECR_ANALYTICS:latest .
docker push $ECR_ANALYTICS:latest
```

### Step 4: Update ECS Services (5 minutes)

```bash
# Get cluster name from outputs
CLUSTER_NAME=$(aws cloudformation describe-stacks \
  --stack-name parental-control-prod \
  --region ap-south-1 \
  --query "Stacks[0].Outputs[?OutputKey=='ECSClusterName'].OutputValue" \
  --output text)

# Force new deployment with latest images
aws ecs update-service --cluster $CLUSTER_NAME --service pc-prod-p-gateway-service --force-new-deployment --region ap-south-1
aws ecs update-service --cluster $CLUSTER_NAME --service pc-prod-kafka-subscriber-service --force-new-deployment --region ap-south-1
aws ecs update-service --cluster $CLUSTER_NAME --service pc-prod-policy-enforcer-service --force-new-deployment --region ap-south-1
aws ecs update-service --cluster $CLUSTER_NAME --service pc-prod-ftd-integration-service --force-new-deployment --region ap-south-1
aws ecs update-service --cluster $CLUSTER_NAME --service pc-prod-analytics-dashboard-service --force-new-deployment --region ap-south-1
```

### CloudFormation Management Commands

```bash
# Update stack (after template changes)
aws cloudformation update-stack \
  --stack-name parental-control-prod \
  --template-body file://parental-control-backend/infrastructure/cloudformation/infrastructure.yaml \
  --parameters file://parental-control-backend/infrastructure/cloudformation/parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1

# Delete stack (cleanup)
aws cloudformation delete-stack \
  --stack-name parental-control-prod \
  --region ap-south-1

# View stack events
aws cloudformation describe-stack-events \
  --stack-name parental-control-prod \
  --region ap-south-1 \
  --max-items 20
```

## Deployment Timeline

| Task | Time | Status |
|------|------|--------|
| Validate CloudFormation Template | 1 min | Pending |
| CloudFormation Stack Deployment | 60 min | Pending |
| Build Docker Images | 15 min | Pending |
| Push to ECR | 10 min | Pending |
| Update ECS Services | 5 min | Pending |
| Deploy to Amplify | 10 min | Pending |
| Deploy Cisco FTD | 30 min | Pending |
| Configure & Test | 15 min | Pending |
| **TOTAL** | **~146 min (2.4 hours)** | |

---

## Quick Commands Summary

```bash
# All in one deployment script
cd /home/kpanse/wsl-myprojects/parental-control-demo

# Automated deployment (recommended)
./deploy-to-aws.sh

# OR manual step-by-step:

# 1. Validate template
aws cloudformation validate-template \
  --template-body file://parental-control-backend/infrastructure/cloudformation/infrastructure.yaml \
  --region ap-south-1

# 2. Deploy infrastructure
aws cloudformation create-stack \
  --stack-name parental-control-prod \
  --template-body file://parental-control-backend/infrastructure/cloudformation/infrastructure.yaml \
  --parameters file://parental-control-backend/infrastructure/cloudformation/parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1

# 3. Deploy frontend
cd frontend
amplify init
amplify add hosting
amplify publish
```

---

## Monitoring & Troubleshooting

### View All Services
```bash
aws ecs list-services --cluster pc-prod-cluster --region ap-south-1
```

### View Logs
```bash
# P-Gateway
aws logs tail /ecs/pc-prod/p-gateway --follow --region ap-south-1

# Kafka Subscriber
aws logs tail /ecs/pc-prod/kafka-subscriber --follow --region ap-south-1

# Policy Enforcer
aws logs tail /ecs/pc-prod/policy-enforcer --follow --region ap-south-1

# FTD Integration
aws logs tail /ecs/pc-prod/ftd-integration --follow --region ap-south-1
```

### Check Resource Status
```bash
# ECS
aws ecs describe-services --cluster pc-prod-cluster --services pc-prod-p-gateway-service --region ap-south-1

# MSK
aws kafka list-clusters --region ap-south-1

# Redis
aws elasticache describe-replication-groups --region ap-south-1

# DynamoDB
aws dynamodb describe-table --table-name ParentalPolicies --region ap-south-1
```

---

## Cost Optimization Tips

1. **Use Spot Instances** for P-Gateway simulator (60% savings)
2. **Schedule ECS** tasks (stop at night if not needed)
3. **Use Reserved Instances** for MSK and ElastiCache (40% savings)
4. **Monitor and alert** on unexpected costs
5. **Right-size resources** after monitoring usage

---

## Cleanup (To Avoid Charges)

```bash
# Destroy everything
aws cloudformation delete-stack \
  --stack-name parental-control-prod \
  --region ap-south-1

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name parental-control-prod \
  --region ap-south-1
```

---

## Support

- **Documentation**: See DESIGN.md for architecture details
- **Logs**: Check CloudWatch Logs
- **Alarms**: Check CloudWatch Alarms
- **Costs**: Check AWS Cost Explorer

---

**Ready to deploy?** Run the commands above! 🚀
