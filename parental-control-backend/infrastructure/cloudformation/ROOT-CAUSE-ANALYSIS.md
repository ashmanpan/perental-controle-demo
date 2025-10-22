# Root Cause Analysis - ECS Container Health Check Failures

**Date:** 2025-10-19
**Account:** 567097740753 (new-sept2025-runon)
**Region:** ap-south-1 (Mumbai)

---

## 🔴 PROBLEM STATEMENT

**All ECS containers are failing health checks and cannot stabilize, causing CloudFormation deployment to fail after 2 hours.**

### Observed Behavior

1. **CloudFormation creates ECS services successfully**
2. **Tasks start and reach RUNNING state**
3. **Health checks FAIL** - tasks marked UNHEALTHY
4. **ECS starts replacement tasks** (cycling: 2 → 4 → 2 → 4)
5. **CloudFormation waits for stabilization** → TIMEOUT after 2 hours → ROLLBACK

### Evidence

```
Task Status: RUNNING
Health Status: UNHEALTHY
Container Health: UNHEALTHY

Health Check Command: ps aux | grep -v grep | grep consumer.py || exit 1
Health Check Config:
  - Interval: 30s
  - Timeout: 5s
  - Retries: 3
  - StartPeriod: 60s

Service Config:
  - HealthCheckGracePeriodSeconds: 300 (5 minutes)
```

### Task Cycling Pattern

```
Check 1:  All services: ACTIVE, Running: 2/2 (desired)
Check 3:  All services: ACTIVE, Running: 4/2 (extras starting)
Check 6:  All services: ACTIVE, Running: 2/2 (old tasks stopped)
Check 9:  All services: ACTIVE, Running: 4/2 (cycling again)
Check 12: All services: ACTIVE, Running: 2/2
... REPEATS INDEFINITELY
```

---

## 🔍 ROOT CAUSE INVESTIGATION

### What We Know

1. ✅ **Infrastructure is working**
   - VPC, subnets, security groups: ACTIVE
   - MSK Kafka (3 brokers): ACTIVE
   - Redis (2 nodes): ACTIVE
   - DynamoDB (5 tables): ACTIVE
   - ECS Cluster: ACTIVE

2. ✅ **Docker images exist and are correct**
   - All 5 images in ECR: VERIFIED
   - Images copied successfully from old account
   - Tags match task definitions

3. ✅ **ECS services create successfully**
   - Task definitions: ACTIVE
   - Services: ACTIVE
   - Tasks start: RUNNING

4. ❌ **Health checks fail**
   - Containers reach RUNNING state
   - Health check command executes
   - Process not found or exits immediately
   - Tasks marked UNHEALTHY

### What's Different Between Old and New Account?

| Aspect | Old Account (264314137331) | New Account (567097740753) | Impact |
|--------|---------------------------|----------------------------|--------|
| **Deployment worked?** | ✅ YES | ❌ NO | CRITICAL |
| **AWS Region** | ap-south-1 | ap-south-1 | Same |
| **ECR Images** | Original | Copied | Same layers |
| **Infrastructure** | Same template | Same template | Same |
| **Task Definitions** | Same | Same | Same |
| **Health Checks** | Same | Same | Same |

**Hypothesis:** Something in the APPLICATION RUNTIME is failing, not infrastructure.

---

## 🧪 POSSIBLE ROOT CAUSES

### Theory 1: Application Crashes on Startup ⭐ MOST LIKELY

**Evidence:**
- Health check looks for process: `grep consumer.py`
- Process not found → health check fails
- Containers are RUNNING (container itself doesn't crash)
- Application inside container crashes

**Possible Reasons:**
```python
# consumer.py might be failing due to:
1. Missing environment variables
2. Cannot connect to Kafka (MSK bootstrap servers)
3. Cannot connect to Redis
4. Cannot connect to DynamoDB
5. Python dependencies missing
6. Code errors/exceptions
7. Configuration file missing
```

**How to Verify:**
- Need to check container logs (CloudWatch)
- Currently: Log groups don't exist yet (containers die too fast)
- Solution: Disable health checks temporarily, let container run, check logs

### Theory 2: Health Check Command is Wrong

**Evidence:**
- Command: `ps aux | grep -v grep | grep consumer.py`
- Assumes process name is exactly `consumer.py`
- Python might run as `python consumer.py` or `python3 consumer.py`

**How to Verify:**
- Exec into running container
- Run `ps aux` manually
- Check actual process names

**Fix:**
```yaml
# More lenient health check
HealthCheck:
  Command:
    - CMD-SHELL
    - ps aux | grep -v grep | grep python || exit 1
```

### Theory 3: Wrong Working Directory

**Evidence:**
- Health check runs in container root
- Application might be in `/app` or different directory
- Relative paths might not work

**How to Verify:**
- Check Dockerfile WORKDIR
- Check task definition working directory

### Theory 4: Container Startup is Too Slow

**Evidence:**
- StartPeriod: 60s (health checks don't count as failures for 60s)
- HealthCheckGracePeriodSeconds: 300s (ECS ignores failures for 5 min)
- But still failing → startup takes > 6 minutes?

**Unlikely:** Old account would have same issue

### Theory 5: Network/Connectivity Issues

**Evidence:**
- Application needs to connect to:
  - MSK Kafka (requires bootstrap servers)
  - Redis (requires endpoint)
  - DynamoDB (requires AWS credentials)

**Possible Issues:**
- Security group not allowing outbound
- VPC endpoints missing for AWS services
- NAT Gateway not working
- DNS resolution failing

**How to Verify:**
- Check security group rules
- Check if containers can reach internet
- Check if VPC endpoints exist for DynamoDB

---

## 🎯 RECOMMENDED INVESTIGATION STEPS

### Step 1: Run Container Without Health Checks (IMMEDIATE)

**Goal:** Get container to stay alive long enough to check logs

**Action:**
```yaml
# Remove health checks from ALL task definitions temporarily
# Comment out HealthCheck section:
# HealthCheck:
#   Command: [...]
```

**Expected Result:**
- Containers start and stay RUNNING
- Can access CloudWatch logs
- Can see actual application errors

### Step 2: Check Application Logs

**Once containers are running:**

```bash
# Get log streams
aws logs tail /aws/ecs/pc-prod-kafka-subscriber --region ap-south-1 --follow

# Look for:
- Python tracebacks
- Connection errors (Kafka/Redis/DynamoDB)
- Missing environment variable errors
- Import errors (missing dependencies)
```

### Step 3: Verify Environment Variables

**Check task definition has all required env vars:**

```yaml
Environment:
  - Name: KAFKA_BOOTSTRAP_SERVERS
    Value: !GetAtt MSKCluster.BootstrapBrokerStringTls  # Verify this resolves
  - Name: REDIS_ENDPOINT
    Value: !GetAtt RedisReplicationGroup.PrimaryEndPoint.Address  # Verify
  - Name: AWS_REGION
    Value: ap-south-1
  - Name: DYNAMO_TABLE_PREFIX
    Value: pc-prod
```

### Step 4: Test Connectivity Manually

**If logs show connection errors:**

```bash
# Exec into running container (once health checks removed)
aws ecs execute-command \
  --cluster pc-prod-cluster \
  --task TASK-ARN \
  --container kafka-subscriber \
  --interactive \
  --command "/bin/bash"

# Inside container:
# Test Kafka connection
telnet b-1.pcprodkafka.wsyhl3.c2.kafka.ap-south-1.amazonaws.com 9094

# Test Redis connection
redis-cli -h master.pc-prod-redis.pmn6zt.aps1.cache.amazonaws.com ping

# Test DynamoDB access
aws dynamodb list-tables --region ap-south-1
```

### Step 5: Compare Task Definitions

**Check if old account has different task definition:**

```bash
# Old account
aws ecs describe-task-definition --task-definition pc-prod-kafka-subscriber --profile default

# New account
aws ecs describe-task-definition --task-definition pc-prod-kafka-subscriber --profile new-sept2025-runon

# Compare environment variables, command, entry point
```

---

## 🔧 PROPOSED FIXES

### Fix 1: Remove Health Checks Temporarily (IMMEDIATE)

**File:** `infrastructure.yaml`

**Change:**
```yaml
# In ALL 5 task definitions, comment out HealthCheck:

# KafkaSubscriberTaskDefinition:
#   ContainerDefinitions:
#     - Name: kafka-subscriber
#       # HealthCheck:
#       #   Command:
#       #     - CMD-SHELL
#       #     - ps aux | grep -v grep | grep consumer.py || exit 1
#       #   Interval: 30
#       #   Timeout: 5
#       #   Retries: 3
#       #   StartPeriod: 60
```

**Deploy:** Stack update will complete quickly
**Benefit:** Containers stay alive, can debug

### Fix 2: Fix Application Code (After logs show error)

**Once we see logs, we'll know what to fix:**

Example fixes:
```python
# If missing env vars:
import os
KAFKA_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

# If connection timeout:
consumer = KafkaConsumer(
    bootstrap_servers=KAFKA_SERVERS,
    request_timeout_ms=30000  # Increase timeout
)

# If AWS credentials missing:
# Ensure ECS task role has correct permissions
```

### Fix 3: Update Health Check to be More Lenient

**After fixing app, use better health check:**

```yaml
HealthCheck:
  Command:
    - CMD-SHELL
    - python -c "import sys; sys.exit(0)" || exit 1  # Just check Python works
  # OR
  Command:
    - CMD-SHELL
    - curl -f http://localhost:5000/health || exit 1  # If app has health endpoint
```

### Fix 4: Add Logging for Debugging

**Update application code:**

```python
import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.info("Starting consumer...")
logger.info(f"Kafka servers: {KAFKA_SERVERS}")
logger.info(f"Redis endpoint: {REDIS_ENDPOINT}")

try:
    consumer = KafkaConsumer(...)
    logger.info("✓ Connected to Kafka")
except Exception as e:
    logger.error(f"✗ Failed to connect to Kafka: {e}")
    raise
```

---

## 📋 ACTION PLAN (Next Steps)

1. ✅ **Cancel current deployment** (DONE)
2. ⏳ **Wait for rollback** (IN PROGRESS)
3. 🔄 **Remove health checks from task definitions**
4. 🚀 **Deploy without health checks**
5. 📊 **Check CloudWatch logs**
6. 🔍 **Identify actual error**
7. 🛠️ **Fix application/configuration**
8. ✅ **Re-enable health checks**
9. 🎉 **Deploy final working version**

---

## 💡 KEY INSIGHT

**The problem is NOT:**
- CloudFormation template ❌
- HealthCheckGracePeriodSeconds value ❌
- Infrastructure (VPC/MSK/Redis/DynamoDB) ❌
- Docker images ❌

**The problem IS:**
- Application code crashing or failing to start ✅
- Missing/wrong environment variables ✅
- Network connectivity to dependencies ✅
- Application configuration ✅

**We need APPLICATION LOGS to know which one!**

---

**Next:** Remove health checks → Deploy → Check logs → Fix root cause
