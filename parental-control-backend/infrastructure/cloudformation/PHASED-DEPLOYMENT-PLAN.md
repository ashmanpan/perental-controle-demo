# Phased Deployment Plan - Parental Control System

**Account:** 567097740753 (new-sept2025-runon)
**Region:** ap-south-1 (Mumbai)
**Date:** 2025-10-19

---

## 🎯 Problem Statement

**Previous Failures:**
- Deployed full CloudFormation stack with all ECS services
- All 5 services stuck in `CREATE_IN_PROGRESS` for 2+ hours
- CloudFormation waited for service stabilization → TIMEOUT → ROLLBACK
- Added `HealthCheckGracePeriodSeconds: 300` but still failed

**Root Cause:**
- Containers are ACTUALLY failing health checks (not just slow to start)
- Need to isolate and test containers separately before deploying services
- CloudFormation's 2-hour timeout doesn't allow for debugging

---

## 📋 New Strategy: Phased Deployment

### Phase 1: Infrastructure Only (NO ECS Services) ✅ IN PROGRESS
**Goal:** Deploy all infrastructure without ECS services to avoid health check failures

**Resources Deployed:**
```
✅ VPC (VPC ID will be available after deployment)
✅ 3 Public Subnets (ap-south-1a, 1b, 1c)
✅ 3 Private Subnets (ap-south-1a, 1b, 1c)
✅ Internet Gateway
✅ 3 NAT Gateways (one per AZ)
✅ Route Tables (public + 3 private)
✅ Security Groups:
   - ECS Tasks Security Group
   - Redis Security Group
   - MSK Security Group
✅ DynamoDB Tables (5):
   - pc-prod-parental-policies
   - pc-prod-application-registry
   - pc-prod-enforcement-history
   - pc-prod-blocked-request-metrics
   - pc-prod-ftd-rule-mapping
✅ ElastiCache Redis (2-node replication group)
✅ MSK Kafka (3-broker cluster)
✅ ECS Cluster (pc-prod-ecs-cluster)
✅ ECS Task Definitions (5):
   - PGatewayTaskDefinition
   - KafkaSubscriberTaskDefinition
   - PolicyEnforcerTaskDefinition
   - FTDIntegrationTaskDefinition
   - AnalyticsDashboardTaskDefinition
✅ IAM Roles:
   - ECS Task Execution Role
   - ECS Task Role
   - MSK Bootstrap Lambda Role
✅ Service Discovery Namespace
```

**What's NOT Deployed:**
```
❌ PGatewayService
❌ KafkaSubscriberService
❌ PolicyEnforcerService
❌ FTDIntegrationService
❌ AnalyticsDashboardService
```

**Status:**
- Deployment started: 2025-10-19 17:20 UTC (22:50 IST)
- Current progress: 13/64 resources completed
- Slowest resources: MSK Kafka (~25-30 min), NAT Gateways (~5-10 min), Redis (~10-15 min)
- Expected completion: ~17:50 UTC (23:20 IST)

---

### Phase 2: Manual Container Testing ⏳ PENDING
**Goal:** Verify ONE container can start and pass health checks

**Steps:**
1. Get VPC private subnet IDs from CloudFormation outputs
2. Get security group ID for ECS tasks
3. Manually run ONE ECS task (start with simplest: analytics-dashboard)
   ```bash
   aws ecs run-task \
     --cluster pc-prod-ecs-cluster \
     --task-definition pc-prod-analytics-dashboard-task \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
     --region ap-south-1
   ```
4. Check task status every 30 seconds
5. Monitor CloudWatch logs for errors
6. Check health check status

**Expected Outcomes:**
- ✅ **SUCCESS**: Container starts, passes health check → Proceed to Phase 3
- ❌ **FAILURE**: Container fails → Debug logs, fix issues, retry

**Potential Issues to Check:**
- Missing environment variables
- Can't connect to Redis/Kafka/DynamoDB
- Container health check command failing
- Application startup errors
- Network connectivity issues

---

### Phase 3: Fix Container Issues (If Needed) ⏳ PENDING
**Goal:** Resolve any container startup or health check failures

**Common Fixes:**
1. **Environment Variables**: Verify all required env vars are set in task definition
2. **Network Access**: Check security group allows access to Redis/Kafka/DynamoDB
3. **Health Check Command**: Verify health check command is correct
4. **Application Code**: Check if code has bugs or missing dependencies
5. **Connectivity**: Ensure VPC endpoints or NAT gateways allow outbound access

**Debugging Tools:**
```bash
# Check task logs
aws logs tail /aws/ecs/pc-prod-analytics-dashboard --follow --region ap-south-1

# Check task status
aws ecs describe-tasks --cluster pc-prod-ecs-cluster --tasks TASK-ID --region ap-south-1

# Check network interfaces
aws ec2 describe-network-interfaces --filters "Name=description,Values=*TASK-ID*" --region ap-south-1
```

---

### Phase 4: Deploy ECS Services ⏳ PENDING
**Goal:** Add ECS services via CloudFormation stack update once containers are verified stable

**Method:** CloudFormation Stack Update
```bash
# Use full template with services
aws cloudformation update-stack \
  --stack-name pc-prod \
  --template-body file://infrastructure-full.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1
```

**Resources Added:**
```
✅ PGatewayService (DesiredCount: 2, with HealthCheckGracePeriodSeconds: 300)
✅ KafkaSubscriberService (DesiredCount: 2, with HealthCheckGracePeriodSeconds: 300)
✅ PolicyEnforcerService (DesiredCount: 2, with HealthCheckGracePeriodSeconds: 300)
✅ FTDIntegrationService (DesiredCount: 2, with HealthCheckGracePeriodSeconds: 300)
✅ AnalyticsDashboardService (DesiredCount: 2, with HealthCheckGracePeriodSeconds: 300)
```

**Expected Result:**
- Services create tasks using proven-working task definitions
- Tasks start and pass health checks within 5 minutes
- CloudFormation stack update completes successfully
- No rollback!

---

### Phase 5: End-to-End Testing ⏳ PENDING
**Goal:** Verify complete data flow works

**Test Plan:**
1. Deploy FTDv EC2 instance (using start-ftd-vm.sh)
2. Verify all 5 services are RUNNING and HEALTHY
3. Check data flow:
   ```
   P-Gateway → Kafka → Redis
   Kafka → Subscriber → Policy Enforcer → FTD Integration → FTDv
   ```
4. Verify metrics in DynamoDB
5. Test Analytics Dashboard APIs
6. Deploy Splunk (optional, for log analytics)
7. Test Splunk dashboard

---

## 📊 Progress Tracker

| Phase | Status | Start Time | End Time | Duration | Notes |
|-------|--------|------------|----------|----------|-------|
| Phase 1: Infrastructure | 🔄 IN PROGRESS | 17:20 UTC | - | - | 13/64 resources created |
| Phase 2: Manual Test | ⏳ PENDING | - | - | - | Waiting for Phase 1 |
| Phase 3: Fix Issues | ⏳ PENDING | - | - | - | Only if Phase 2 fails |
| Phase 4: Deploy Services | ⏳ PENDING | - | - | - | After containers verified |
| Phase 5: E2E Testing | ⏳ PENDING | - | - | - | Final validation |

---

## 🔧 Files Created

| File | Purpose |
|------|---------|
| `infrastructure-full.yaml` | Full template with ECS services (1659 lines) |
| `infrastructure-phase1.yaml` | Infrastructure only, NO services (1546 lines) |
| `infrastructure.yaml` | Current deployment (Phase 1) |

---

## ✅ Advantages of Phased Approach

1. **Faster Feedback Loop**
   - Phase 1 completes in ~30 minutes vs 2 hours
   - No waiting for service stabilization
   - Can test containers immediately

2. **Better Debugging**
   - Isolate container issues from CloudFormation
   - Direct access to task logs
   - Can fix and retry quickly

3. **No CloudFormation Rollback**
   - Infrastructure stays deployed
   - Only update when containers are proven
   - Incremental progress vs all-or-nothing

4. **Cost Savings**
   - Don't waste 2 hours on failed deployments
   - Test with 1 task vs multiple services
   - Can stop when issues found

5. **Production Ready**
   - Template verified in stages
   - Containers proven stable
   - Confident deployment for customers

---

## 📞 Next Actions

**Immediate (Now):**
- ✅ Monitor Phase 1 deployment (background task running)
- ✅ Wait for MSK Kafka, NAT Gateways, Redis to complete (~25 min remaining)

**After Phase 1 Completes:**
1. Extract subnet IDs and security group IDs from CloudFormation outputs
2. Manually run analytics-dashboard task
3. Monitor task status and logs
4. If successful → Test one more service (p-gateway)
5. If all pass → Update stack to add ECS services

**Final Step:**
- Deploy FTDv and test end-to-end flow
- Deploy Splunk for analytics (optional)
- Documentation and handoff

---

**Background Monitor:** Task ID 168cfe (checks every 60 seconds)
**Expected Phase 1 Completion:** ~17:50 UTC (23:20 IST)
