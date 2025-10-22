# Local Container Testing Guide

**Purpose:** Test all containers locally before pushing to ECR and deploying to AWS
**Date:** 2025-10-19

---

## 🎯 Why Local Testing First?

**Problem:** Containers are failing health checks in AWS, but we don't know why
**Solution:** Run containers locally with Docker Compose to see actual errors

**Benefits:**
- ✅ Instant feedback (no 2-hour CloudFormation wait)
- ✅ Full access to logs
- ✅ Can debug and fix quickly
- ✅ Test entire system end-to-end
- ✅ Verify before pushing to AWS

---

## 📋 What's Included in Docker Compose

### Infrastructure Services
1. **Zookeeper** - Kafka coordination (port 2181)
2. **Kafka** - Message broker (ports 9092, 29092)
3. **Redis** - Session cache (port 6379)
4. **DynamoDB Local** - Local database (port 8000)

### Application Services
5. **p-gateway-simulator** - Simulates network traffic
6. **kafka-subscriber** - Consumes traffic, stores in Redis/DynamoDB
7. **policy-enforcer** - Applies parental control policies
8. **ftd-integration** - Integrates with Cisco FTD (port 5000)
9. **analytics-dashboard** - REST API for analytics (port 8000)

### Admin/Monitoring Services
10. **DynamoDB Admin** - Web UI for DynamoDB (port 8001)
11. **Redis Commander** - Web UI for Redis (port 8081)
12. **Kafka UI** - Web UI for Kafka (port 8080)

---

## 🚀 Quick Start

### Step 1: Navigate to Docker Directory

```bash
cd /home/kpanse/wsl-myprojects/parental-control-demo/parental-control-backend/deployment/docker
```

### Step 2: Build All Images

```bash
docker-compose build
```

**Expected:** Builds 5 application images:
- p-gateway-simulator
- kafka-subscriber
- policy-enforcer
- ftd-integration
- analytics-dashboard

### Step 3: Start All Services

```bash
docker-compose up -d
```

**Expected:** Starts all 12 containers

### Step 4: Check Container Status

```bash
docker-compose ps
```

**Expected Output:**
```
NAME                        STATUS
pc-p-gateway-simulator      Up
pc-kafka-subscriber         Up
pc-policy-enforcer          Up
pc-ftd-integration          Up (healthy)
pc-analytics-dashboard      Up
pc-kafka                    Up (healthy)
pc-redis                    Up (healthy)
pc-dynamodb-local           Up
... etc
```

### Step 5: Check Logs for Errors

```bash
# Check all services
docker-compose logs -f

# Check specific service
docker-compose logs -f kafka-subscriber

# Check for errors only
docker-compose logs | grep -i error
docker-compose logs | grep -i exception
```

---

## 🔍 Debugging Containers

### Check if Process is Running

```bash
# Enter container
docker exec -it pc-kafka-subscriber bash

# Check processes
ps aux | grep python
ps aux | grep consumer.py

# Check Python can run
python --version
python3 --version

# Try running app manually
cd /app
python consumer.py
```

### Check Environment Variables

```bash
docker exec pc-kafka-subscriber env | grep KAFKA
docker exec pc-kafka-subscriber env | grep REDIS
docker exec pc-kafka-subscriber env | grep DYNAMODB
```

### Check Network Connectivity

```bash
# Can container reach Kafka?
docker exec pc-kafka-subscriber ping kafka

# Can container reach Redis?
docker exec pc-kafka-subscriber redis-cli -h redis ping

# Check DNS resolution
docker exec pc-kafka-subscriber nslookup kafka
```

### Check Application Logs

```bash
# Real-time logs
docker-compose logs -f kafka-subscriber

# Last 100 lines
docker-compose logs --tail=100 kafka-subscriber

# Since 5 minutes ago
docker-compose logs --since=5m kafka-subscriber
```

---

## 🧪 Test End-to-End Flow

### 1. Check P-Gateway is Generating Traffic

```bash
docker-compose logs p-gateway-simulator | tail -20
```

**Expected:** See session data being generated

### 2. Check Kafka has Topics and Messages

**Web UI:**
Open http://localhost:8080

**CLI:**
```bash
# List topics
docker exec pc-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check messages in session-data topic
docker exec pc-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic session-data \
  --from-beginning \
  --max-messages 10
```

### 3. Check Redis has Session Data

**Web UI:**
Open http://localhost:8081

**CLI:**
```bash
# Connect to Redis
docker exec -it pc-redis redis-cli

# Check keys
KEYS *

# Get a session
GET session:+1234567890
```

### 4. Check DynamoDB has Data

**Web UI:**
Open http://localhost:8001

**CLI:**
```bash
# List tables
docker exec pc-dynamodb-local \
  aws dynamodb list-tables \
  --endpoint-url http://localhost:8000 \
  --region ap-south-1

# Scan enforcement history
docker exec pc-dynamodb-local \
  aws dynamodb scan \
  --table-name EnforcementHistory \
  --endpoint-url http://localhost:8000 \
  --region ap-south-1
```

### 5. Test Analytics API

```bash
# Health check
curl http://localhost:8000/health

# Get blocked requests
curl http://localhost:8000/api/v1/blocked-requests

# Get enforcement history
curl http://localhost:8000/api/v1/enforcement-history
```

### 6. Test FTD Integration API

```bash
# Health check
curl http://localhost:5000/health

# Create a block rule
curl -X POST http://localhost:5000/api/v1/block-rule \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "ip_address": "192.168.1.100",
    "destination": "badwebsite.com",
    "reason": "Parental Control"
  }'
```

---

## 🛠️ Common Issues and Fixes

### Issue 1: Container Exits Immediately

**Symptom:**
```bash
docker-compose ps
# Shows: Exited (1) or Restarting
```

**Debug:**
```bash
# Check exit logs
docker-compose logs kafka-subscriber

# Common causes:
- Python import error (missing dependency)
- Cannot connect to Kafka/Redis
- Environment variable missing
- Syntax error in code
```

**Fix:**
```bash
# Rebuild with no cache
docker-compose build --no-cache kafka-subscriber

# Check Dockerfile
cat ../../services/kafka-subscriber/Dockerfile
```

### Issue 2: Cannot Connect to Kafka

**Symptom:**
```
Error: NoBrokersAvailable
Error: Connection refused to kafka:29092
```

**Debug:**
```bash
# Check if Kafka is healthy
docker-compose ps kafka

# Check Kafka logs
docker-compose logs kafka | grep -i error

# Wait for Kafka to be ready
docker-compose up -d kafka
sleep 30
docker-compose up -d kafka-subscriber
```

### Issue 3: Cannot Connect to Redis

**Symptom:**
```
Error: Connection refused to redis:6379
redis.exceptions.ConnectionError
```

**Debug:**
```bash
# Check if Redis is healthy
docker-compose ps redis

# Test Redis manually
docker exec pc-redis redis-cli ping
```

### Issue 4: DynamoDB Table Not Found

**Symptom:**
```
ResourceNotFoundException: Table 'EnforcementHistory' not found
```

**Fix:**
```bash
# Tables need to be created first
# Check if initialization script exists
ls ../../services/*/init*.py

# Or create tables manually
docker exec pc-dynamodb-local aws dynamodb create-table \
  --table-name EnforcementHistory \
  --attribute-definitions \
    AttributeName=id,AttributeType=S \
  --key-schema \
    AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://localhost:8000 \
  --region ap-south-1
```

### Issue 5: Health Check Failing

**Symptom:**
```
Health: starting → unhealthy
```

**Debug:**
```bash
# Check what health check command is
docker inspect pc-kafka-subscriber | grep -A 5 Healthcheck

# Run health check manually
docker exec pc-kafka-subscriber ps aux | grep consumer.py

# If process not found:
docker exec pc-kafka-subscriber ps aux
# See what processes ARE running
```

---

## ✅ Success Criteria

Before pushing to ECR, verify:

1. ✅ **All containers start and stay running**
   ```bash
   docker-compose ps
   # All should show "Up" or "Up (healthy)"
   ```

2. ✅ **No errors in logs**
   ```bash
   docker-compose logs | grep -i error
   # Should be empty or only expected errors
   ```

3. ✅ **P-Gateway generates traffic**
   ```bash
   docker-compose logs p-gateway-simulator | grep "Published"
   ```

4. ✅ **Kafka has messages**
   ```bash
   docker exec pc-kafka kafka-topics --list --bootstrap-server localhost:9092
   # Should show: session-data, blocked-requests
   ```

5. ✅ **Redis has sessions**
   ```bash
   docker exec pc-redis redis-cli DBSIZE
   # Should show > 0
   ```

6. ✅ **DynamoDB has data**
   ```bash
   # Open http://localhost:8001 and check tables
   ```

7. ✅ **APIs respond**
   ```bash
   curl http://localhost:5000/health  # FTD Integration
   curl http://localhost:8000/health  # Analytics Dashboard
   ```

8. ✅ **Health checks pass for at least 2 minutes**
   ```bash
   watch -n 10 'docker-compose ps'
   ```

---

## 📤 Push to ECR After Testing

Once everything works locally:

```bash
# Tag images for ECR
docker tag pc-p-gateway-simulator:latest \
  567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:p-gateway-simulator

docker tag pc-kafka-subscriber:latest \
  567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:kafka-subscriber

docker tag pc-policy-enforcer:latest \
  567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:policy-enforcer

docker tag pc-ftd-integration:latest \
  567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:ftd-integration

docker tag pc-analytics-dashboard:latest \
  567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:analytics-dashboard

# Login to ECR
aws ecr get-login-password --region ap-south-1 --profile new-sept2025-runon | \
  docker login --username AWS --password-stdin \
  567097740753.dkr.ecr.ap-south-1.amazonaws.com

# Push all images
docker push 567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:p-gateway-simulator
docker push 567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:kafka-subscriber
docker push 567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:policy-enforcer
docker push 567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:ftd-integration
docker push 567097740753.dkr.ecr.ap-south-1.amazonaws.com/parental-control:analytics-dashboard
```

---

## 🎯 Next Steps

1. ✅ **Test locally** (this guide)
2. 🔧 **Fix any errors** found in local testing
3. 📤 **Push working images to ECR**
4. 🚀 **Deploy to AWS** with confidence
5. 🎉 **Services should work** this time!

---

**Location:** `/home/kpanse/wsl-myprojects/parental-control-demo/parental-control-backend/deployment/docker`
**Start Command:** `docker-compose up -d`
**Stop Command:** `docker-compose down`
**Clean Up:** `docker-compose down -v` (removes volumes too)
