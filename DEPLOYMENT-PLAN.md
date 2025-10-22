# AWS Deployment Plan - New Account Migration

**Date:** 2025-10-14
**Purpose:** Complete automated deployment to new AWS account

---

## Current Status Analysis

### Existing Components ✅
1. **Infrastructure Template** (infrastructure.yaml - 1,654 lines)
   - VPC with 3 public + 3 private subnets
   - NAT Gateways (3x for HA)
   - MSK Kafka cluster (3 brokers)
   - ElastiCache Redis cluster (2 nodes)
   - DynamoDB tables (5 tables)
   - SQS queues
   - ECS Fargate cluster
   - IAM roles
   - CloudWatch logs
   - Service Discovery

2. **FTDv Deployment Template** (ftd-deployment.yaml)
   - EC2 instance for FTDv
   - Security groups
   - Network interfaces

### Missing Components ❌

1. **ECR Repository Creation**
   - Single repository needs to be created before image push
   - Currently commented in template as "manually created"

2. **Docker Image Build & Push**
   - 5 microservices need to be built and pushed
   - No automated build script

3. **Deployment Orchestration**
   - No single command to deploy everything
   - Manual steps required

4. **Pre-deployment Validation**
   - No checks for prerequisites
   - No AWS account validation

5. **Parameter Management**
   - Parameters currently in template
   - No separate parameter files for different environments

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   NEW AWS ACCOUNT                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: Pre-Deployment Validation                          │
│  ├── Check AWS CLI configured                               │
│  ├── Check AWS credentials                                  │
│  ├── Verify region (ap-south-1)                             │
│  └── Check required permissions                             │
│                                                              │
│  Step 2: Create ECR Repository                              │
│  └── Single repo: parental-control                          │
│                                                              │
│  Step 3: Build & Push Docker Images                         │
│  ├── p-gateway-simulator                                    │
│  ├── kafka-subscriber                                       │
│  ├── policy-enforcer                                        │
│  ├── ftd-integration                                        │
│  └── analytics-dashboard                                    │
│                                                              │
│  Step 4: Deploy Infrastructure Stack                        │
│  ├── VPC & Networking (5-10 min)                           │
│  ├── DynamoDB Tables (2 min)                                │
│  ├── MSK Kafka Cluster (20-30 min) ← LONGEST               │
│  ├── ElastiCache Redis (10-15 min)                          │
│  ├── SQS Queues (1 min)                                     │
│  ├── ECS Cluster (2 min)                                    │
│  └── ECS Services (5 min)                                   │
│                                                              │
│  Step 5: Optional - Deploy FTDv                             │
│  └── EC2 instance with FTDv AMI (5-10 min)                 │
│                                                              │
│  Step 6: Post-Deployment Verification                       │
│  ├── Check all services running                             │
│  ├── Verify Kafka topics created                            │
│  ├── Test connectivity                                      │
│  └── View CloudWatch logs                                   │
│                                                              │
│  Total Time: ~45-60 minutes                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## What Will Be Created

### 1. Networking Infrastructure
- 1 VPC (10.0.0.0/16)
- 3 Public Subnets (10.0.101.0/24, 10.0.102.0/24, 10.0.103.0/24)
- 3 Private Subnets (10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24)
- 1 Internet Gateway
- 3 NAT Gateways (1 per AZ for HA)
- 3 Elastic IPs
- Route tables
- VPC Endpoints (S3, DynamoDB)

### 2. Database & Storage
- **DynamoDB Tables (5):**
  - parental-policies
  - application-registry
  - enforcement-history
  - blocked-request-metrics
  - ftd-rule-mapping

- **ElastiCache Redis:**
  - Engine: Redis 7.1
  - 2-node cluster (Multi-AZ)
  - TLS encryption
  - Automatic failover

### 3. Messaging & Streaming
- **Amazon MSK:**
  - 3 Kafka brokers
  - kafka.m5.large instances
  - 500GB storage per broker
  - TLS encryption
  - CloudWatch logging

- **SQS Queues:**
  - enforcement-requests queue
  - enforcement-dlq (dead letter queue)

### 4. Compute & Container Services
- **ECS Cluster:** Fargate-based
- **5 ECS Services:**
  - p-gateway-simulator (2 tasks)
  - kafka-subscriber (2 tasks)
  - policy-enforcer (2 tasks)
  - ftd-integration (2 tasks)
  - analytics-dashboard (2 tasks)

### 5. Security & IAM
- ECS Task Execution Role
- ECS Task Role (with DynamoDB, SQS, CloudWatch permissions)
- Security Groups (ECS tasks, MSK, Redis)
- KMS key for MSK encryption

### 6. Monitoring & Logging
- CloudWatch Log Groups (5 for each service)
- CloudWatch Alarms (SQS)
- Container Insights enabled

---

## Files to Create

### 1. ECR Repository Template
**File:** `ecr-repository.yaml`
- Creates single ECR repository
- Lifecycle policy for image cleanup
- Permissions for ECS

### 2. Docker Build Script
**File:** `build-and-push.sh`
- Builds all 5 microservices
- Tags images appropriately
- Pushes to ECR
- Validates successful push

### 3. Deployment Orchestration Script
**File:** `deploy.sh`
- Master deployment script
- Runs all steps in order
- Validates each step
- Provides progress updates
- Handles errors gracefully

### 4. Parameter Files
**Files:**
- `parameters-dev.json`
- `parameters-staging.json`
- `parameters-prod.json`

### 5. Pre-Deployment Validation Script
**File:** `validate-prerequisites.sh`
- Checks AWS CLI installed
- Validates credentials
- Checks permissions
- Verifies Docker installed

### 6. Post-Deployment Verification Script
**File:** `verify-deployment.sh`
- Checks stack status
- Verifies services running
- Tests connectivity
- Generates deployment report

### 7. Complete Deployment Guide
**File:** `COMPLETE-DEPLOYMENT-GUIDE.md`
- Step-by-step instructions
- Troubleshooting
- Rollback procedures

---

## Deployment Steps (Simplified)

### One-Command Deployment (Recommended)
```bash
./deploy.sh --environment prod --region ap-south-1 --ftdv-enabled
```

### Manual Step-by-Step
```bash
# 1. Validate prerequisites
./validate-prerequisites.sh

# 2. Create ECR repository
aws cloudformation create-stack \
  --stack-name pc-prod-ecr \
  --template-body file://ecr-repository.yaml \
  --region ap-south-1

# 3. Build and push Docker images
./build-and-push.sh --region ap-south-1

# 4. Deploy infrastructure
aws cloudformation create-stack \
  --stack-name pc-prod-infrastructure \
  --template-body file://infrastructure.yaml \
  --parameters file://parameters-prod.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1

# 5. Wait for completion (~45 min)
aws cloudformation wait stack-create-complete \
  --stack-name pc-prod-infrastructure \
  --region ap-south-1

# 6. Verify deployment
./verify-deployment.sh
```

---

## Cost Estimation (Monthly)

| Component | Instance Type | Quantity | Cost/Month |
|-----------|---------------|----------|------------|
| NAT Gateways | - | 3 | $108 |
| MSK Brokers | kafka.m5.large | 3 | $450 |
| MSK Storage | 500GB x 3 | 1500GB | $150 |
| ElastiCache Redis | cache.r6g.large | 2 | $260 |
| ECS Fargate | 1vCPU/2GB | 10 tasks | $220 |
| DynamoDB | On-demand | - | $50 |
| CloudWatch Logs | 10GB/month | - | $5 |
| Data Transfer | - | - | $20 |
| **Total** | | | **~$1,263/month** |

**Optional:**
- FTDv EC2 (c5.xlarge): $124/month
- Splunk EC2 (c5.2xlarge): $248/month

---

## Parameters Required

### Mandatory
1. **AWS Account ID** - Your new AWS account
2. **AWS Region** - Default: ap-south-1
3. **Environment** - dev/staging/prod
4. **FTD Credentials** - If using FTDv integration

### Optional
1. **VPC CIDR** - Default: 10.0.0.0/16
2. **Instance Types** - Defaults provided
3. **Desired Task Count** - Default: 2

---

## Rollback Plan

If deployment fails:

```bash
# Delete infrastructure stack
aws cloudformation delete-stack \
  --stack-name pc-prod-infrastructure \
  --region ap-south-1

# Delete ECR images (optional)
aws ecr batch-delete-image \
  --repository-name parental-control \
  --region ap-south-1 \
  --image-ids imageTag=latest

# Delete ECR repository
aws cloudformation delete-stack \
  --stack-name pc-prod-ecr \
  --region ap-south-1
```

---

## Security Considerations

1. **Secrets Management**
   - FTD credentials passed via parameters (encrypted)
   - Consider using AWS Secrets Manager for production

2. **Network Security**
   - All services in private subnets
   - No public IPs on ECS tasks
   - Security groups with least privilege

3. **Encryption**
   - TLS for Kafka
   - TLS for Redis
   - KMS for MSK
   - DynamoDB encryption at rest

4. **IAM Permissions**
   - Principle of least privilege
   - Separate execution and task roles

---

## Success Criteria

Deployment is successful when:

✅ CloudFormation stack status: CREATE_COMPLETE
✅ All 5 ECS services running
✅ All services have 2/2 tasks healthy
✅ MSK cluster ACTIVE
✅ Redis cluster available
✅ DynamoDB tables created
✅ CloudWatch logs streaming
✅ No errors in service logs

---

## Next Steps After Deployment

1. **Initialize Data**
   - Seed application registry table
   - Create sample parental policies

2. **Configure FTDv** (if deployed)
   - SSH to FTDv
   - Configure syslog to Splunk
   - Enable logging on ACLs

3. **Deploy Splunk** (optional)
   - Follow SPLUNK-DEPLOYMENT-GUIDE.md

4. **Testing**
   - Run test-ftd-integration.sh
   - Verify end-to-end flow

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Preparation** | 10 min | Review, configure parameters |
| **ECR Setup** | 2 min | Create repository |
| **Docker Build** | 15 min | Build all 5 images |
| **Stack Deployment** | 45 min | MSK is the bottleneck |
| **Verification** | 5 min | Check services |
| **Total** | **~75 min** | End-to-end |

---

## Risk Mitigation

1. **MSK Deployment Timeout**
   - Risk: MSK can take 30-40 minutes
   - Mitigation: Use CloudFormation wait conditions

2. **Image Build Failures**
   - Risk: Docker build errors
   - Mitigation: Pre-validate Dockerfiles

3. **IAM Permission Issues**
   - Risk: Insufficient permissions
   - Mitigation: Validate prerequisites script

4. **Resource Limits**
   - Risk: AWS account limits
   - Mitigation: Check service quotas

---

## Decision Points

Before proceeding, confirm:

1. **Target AWS Region:** ap-south-1 (Mumbai)?
2. **Environment Name:** prod, staging, or dev?
3. **Include FTDv:** Yes or No?
4. **Cost Approval:** ~$1,263/month acceptable?
5. **Splunk Deployment:** Now or later?

---

## Files to Create Summary

```
infrastructure/
├── cloudformation/
│   ├── infrastructure.yaml          [EXISTS - 1,654 lines]
│   ├── ftd-deployment.yaml          [EXISTS]
│   ├── ecr-repository.yaml          [NEW - To Create]
│   ├── parameters-dev.json          [NEW - To Create]
│   ├── parameters-staging.json      [NEW - To Create]
│   └── parameters-prod.json         [NEW - To Create]
├── scripts/
│   ├── deploy.sh                    [NEW - Master script]
│   ├── build-and-push.sh            [NEW - Docker builds]
│   ├── validate-prerequisites.sh    [NEW - Pre-flight checks]
│   └── verify-deployment.sh         [NEW - Post-deployment]
└── docs/
    └── COMPLETE-DEPLOYMENT-GUIDE.md [NEW - Full documentation]
```

---

## Ready to Proceed?

Once this plan is approved, I will create:

1. ✅ ECR repository CloudFormation template
2. ✅ Build and push script for all Docker images
3. ✅ Master deployment orchestration script
4. ✅ Parameter files for dev/staging/prod
5. ✅ Validation and verification scripts
6. ✅ Complete deployment documentation

**Estimated creation time:** 60-90 minutes
**Deployment time:** 75 minutes
**Total time to production:** ~2.5-3 hours
