# 🚀 Full AWS Deployment Guide

## Deployment Options

**Option A: CloudFormation (Recommended)** ✅
- No installation needed (uses AWS CLI)
- AWS-native with built-in state management
- Automatic rollback on failures
- [Jump to CloudFormation Guide](#cloudformation-deployment)

**Option B: Terraform**
- Industry standard IaC tool
- Requires installation
- [Jump to Terraform Guide](#terraform-deployment)

---

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

## CloudFormation Deployment

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
./deploy-to-aws-cloudformation.sh
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

---

## Terraform Deployment

### Prerequisites for Terraform
- ✅ S3 bucket for Terraform state: `parental-control-terraform-state-mumbai`
- ✅ DynamoDB table for state locking: `terraform-state-lock`

### Step 1: Install Terraform (5 minutes)

```bash
# Download and install Terraform
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/
terraform version
```

### Step 2: Deploy Infrastructure with Terraform (45-60 minutes)

```bash
cd /home/kpanse/wsl-myprojects/parental-control-demo/parental-control-backend/infrastructure/terraform

# Initialize Terraform
terraform init

# Preview what will be created
terraform plan

# Deploy (this will take 45-60 minutes)
terraform apply -auto-approve

# Save outputs
terraform output > deployment-outputs.txt
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

# Login to ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 264314137331.dkr.ecr.ap-south-1.amazonaws.com

# Get ECR URLs from Terraform output
ECR_P_GATEWAY=$(terraform -chdir=parental-control-backend/infrastructure/terraform output -raw ecr_p_gateway_url)
ECR_KAFKA=$(terraform -chdir=parental-control-backend/infrastructure/terraform output -raw ecr_kafka_subscriber_url)
ECR_ENFORCER=$(terraform -chdir=parental-control-backend/infrastructure/terraform output -raw ecr_policy_enforcer_url)
ECR_FTD=$(terraform -chdir=parental-control-backend/infrastructure/terraform output -raw ecr_ftd_integration_url)
ECR_ANALYTICS=$(terraform -chdir=parental-control-backend/infrastructure/terraform output -raw ecr_analytics_dashboard_url)

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
# Force new deployment with latest images
aws ecs update-service --cluster pc-prod-cluster --service pc-prod-p-gateway-service --force-new-deployment --region ap-south-1
aws ecs update-service --cluster pc-prod-cluster --service pc-prod-kafka-subscriber-service --force-new-deployment --region ap-south-1
aws ecs update-service --cluster pc-prod-cluster --service pc-prod-policy-enforcer-service --force-new-deployment --region ap-south-1
aws ecs update-service --cluster pc-prod-cluster --service pc-prod-ftd-integration-service --force-new-deployment --region ap-south-1
aws ecs update-service --cluster pc-prod-cluster --service pc-prod-analytics-dashboard-service --force-new-deployment --region ap-south-1
```

### Step 5: Deploy Frontend to AWS Amplify (10 minutes)

```bash
# Install Amplify CLI (if not installed)
npm install -g @aws-amplify/cli

# Initialize Amplify project
cd /home/kpanse/wsl-myprojects/parental-control-demo/frontend
amplify init

# Follow prompts:
# - Name: parental-control-frontend
# - Environment: prod
# - Editor: VS Code
# - App type: javascript
# - Framework: none
# - Source directory: .
# - Distribution directory: .
# - Build command: (leave empty)
# - Start command: (leave empty)

# Add hosting
amplify add hosting
# Choose: Hosting with Amplify Console
# Choose: Manual deployment

# Publish
amplify publish

# Get URL from output
```

### Step 6: Deploy Cisco FTD from AWS Marketplace (30 minutes)

#### Option A: AWS Console (Recommended)

1. Go to AWS Marketplace: https://aws.amazon.com/marketplace
2. Search for "Cisco Firepower Threat Defense"
3. Click "Continue to Subscribe"
4. Accept terms (wait 5-10 minutes for subscription)
5. Click "Continue to Configuration"
   - Region: ap-south-1 (Mumbai)
   - Version: Latest
6. Click "Continue to Launch"
   - Choose Action: "Launch through EC2"
7. Configure:
   - Instance Type: m5.xlarge (minimum)
   - VPC: Select `pc-prod-vpc`
   - Subnet: Select public subnet
   - Security Group: Create new or use existing
   - Key Pair: Select or create
8. Launch

#### Option B: AWS CLI

```bash
# Find AMI ID for Cisco FTD
aws ec2 describe-images \
  --owners 679593333241 \
  --filters "Name=name,Values=*FTDv*" \
  --query 'Images[0].ImageId' \
  --output text \
  --region ap-south-1

# Launch instance (replace AMI_ID, SUBNET_ID, SG_ID, KEY_NAME)
aws ec2 run-instances \
  --image-id AMI_ID \
  --instance-type m5.xlarge \
  --subnet-id SUBNET_ID \
  --security-group-ids SG_ID \
  --key-name KEY_NAME \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cisco-ftd-prod}]' \
  --region ap-south-1
```

#### Configure FTD

1. SSH to the FTD instance
2. Initial configuration:
   ```
   configure manager add HOSTNAME cisco123 cisco123
   ```
3. Configure interfaces
4. Note down FTD management IP
5. Update Terraform variables:
   ```bash
   cd parental-control-backend/infrastructure/terraform

   # Update terraform.tfvars
   ftd_host = "YOUR_FTD_IP"
   ftd_username = "admin"
   ftd_password = "YOUR_PASSWORD"

   # Apply changes
   terraform apply -auto-approve
   ```

### Step 7: Verify Deployment (5 minutes)

```bash
# Check ECS services are running
aws ecs describe-services \
  --cluster pc-prod-cluster \
  --services pc-prod-p-gateway-service \
  --region ap-south-1 \
  --query 'services[0].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}'

# Check MSK cluster
aws kafka describe-cluster \
  --cluster-arn $(terraform -chdir=parental-control-backend/infrastructure/terraform output -raw msk_cluster_arn) \
  --region ap-south-1

# Check Redis
aws elasticache describe-replication-groups \
  --replication-group-id pc-prod-redis \
  --region ap-south-1

# Check DynamoDB tables
aws dynamodb list-tables --region ap-south-1 | grep ParentalPolicies

# View CloudWatch logs
aws logs tail /ecs/pc-prod/p-gateway --follow --region ap-south-1
```

### Step 8: Test End-to-End (10 minutes)

```bash
# 1. Add test policy to DynamoDB
aws dynamodb put-item \
  --table-name ParentalPolicies \
  --item '{
    "childPhoneNumber": {"S": "+15551234567"},
    "policyId": {"S": "policy_test_001"},
    "childName": {"S": "Test Child"},
    "parentEmail": {"S": "test@example.com"},
    "blockedApps": {"L": [
      {"M": {
        "appName": {"S": "TikTok"},
        "ports": {"L": [{"M": {"port": {"N": "443"}, "protocol": {"S": "TCP"}}}]}
      }}
    ]},
    "status": {"S": "active"},
    "createdAt": {"S": "2025-10-07T00:00:00Z"},
    "updatedAt": {"S": "2025-10-07T00:00:00Z"}
  }' \
  --region ap-south-1

# 2. Watch logs to see policy enforcement
aws logs tail /ecs/pc-prod/policy-enforcer --follow --region ap-south-1

# 3. Check SQS messages
aws sqs receive-message \
  --queue-url $(terraform -chdir=parental-control-backend/infrastructure/terraform output -raw sqs_queue_url) \
  --region ap-south-1

# 4. Verify FTD rules created
# (SSH to FTD and check rules)

# 5. Test Analytics API
ANALYTICS_URL="http://ANALYTICS_DASHBOARD_IP:8000"
curl $ANALYTICS_URL/health
curl $ANALYTICS_URL/api/v1/parent/test@example.com/dashboard
```

---

## Deployment Timeline

| Task | Time | Status |
|------|------|--------|
| Install Terraform | 5 min | Pending |
| Terraform Init & Apply | 60 min | Pending |
| Build Docker Images | 15 min | Pending |
| Push to ECR | 10 min | Pending |
| Update ECS Services | 5 min | Pending |
| Deploy to Amplify | 10 min | Pending |
| Deploy Cisco FTD | 30 min | Pending |
| Configure & Test | 15 min | Pending |
| **TOTAL** | **~150 min (2.5 hours)** | |

---

## Quick Commands Summary

```bash
# All in one deployment script
cd /home/kpanse/wsl-myprojects/parental-control-demo

# 1. Install Terraform
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# 2. Deploy infrastructure
cd parental-control-backend/infrastructure/terraform
terraform init
terraform apply -auto-approve

# 3. Build and push (automated script coming next)
# ./scripts/deploy-all.sh

# 4. Deploy frontend
cd ../../../frontend
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
cd parental-control-backend/infrastructure/terraform
terraform destroy -auto-approve

# Confirm S3 bucket cleanup
aws s3 rb s3://parental-control-terraform-state-mumbai --force --region ap-south-1

# Confirm DynamoDB lock table cleanup
aws dynamodb delete-table --table-name terraform-state-lock --region ap-south-1
```

---

## Support

- **Documentation**: See DESIGN.md for architecture details
- **Logs**: Check CloudWatch Logs
- **Alarms**: Check CloudWatch Alarms
- **Costs**: Check AWS Cost Explorer

---

**Ready to deploy?** Run the commands above! 🚀
