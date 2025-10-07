# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Start Local Environment

```bash
cd Agentic-AI-demos/parental-control-backend/deployment/docker
docker-compose up -d
```

**What this does:**
- Starts Kafka (message bus)
- Starts Redis (session cache)
- Starts DynamoDB Local (database)
- Starts management UIs

**Access UIs:**
- Kafka UI: http://localhost:8080
- Redis Commander: http://localhost:8081
- DynamoDB Admin: http://localhost:8001

---

### Step 2: Verify Services

```bash
# Check all services are running
docker-compose ps

# Expected output:
# pc-kafka            Up
# pc-redis            Up
# pc-dynamodb-local   Up
# pc-zookeeper        Up
```

---

### Step 3: Run P-Gateway Simulator

```bash
cd ../../services/p-gateway-simulator

# Install dependencies
pip install -r requirements.txt

# Run simulator
python src/generator.py
```

**What you'll see:**
```
2025-10-03 10:30:00 - INFO - P-Gateway Simulator initialized
2025-10-03 10:30:01 - INFO - Session created: sess_abc123 for +15551234567 (IP: 10.20.30.40)
2025-10-03 10:30:02 - INFO - Session created: sess_def456 for +15559876543 (IP: 10.20.30.41)
```

---

### Step 4: Run Kafka Subscriber

Open a new terminal:

```bash
cd services/kafka-subscriber

# Set environment variables
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export REDIS_HOST=localhost
export DYNAMODB_ENDPOINT=http://localhost:8000
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export AWS_REGION=ap-south-1

# Install dependencies
pip install -r requirements.txt

# Run subscriber
python src/consumer.py
```

**What you'll see:**
```
2025-10-03 10:30:00 - INFO - Starting Kafka consumer...
2025-10-03 10:30:01 - INFO - Subscribing to topic: session-data
2025-10-03 10:30:05 - DEBUG - Processing SESSION_START event for +15551234567
2025-10-03 10:30:05 - DEBUG - Session started: +15551234567 -> 10.20.30.40
```

---

### Step 5: Verify Data Flow

#### Check Kafka Messages
1. Go to http://localhost:8080
2. Click "Topics" → "session-data"
3. Click "Messages"
4. You should see SESSION_START events

#### Check Redis Data
1. Go to http://localhost:8081
2. You should see keys:
   - `phone:+15551234567`
   - `imsi:310150123456789`
   - `ip:10.20.30.40`

#### Check DynamoDB (if policies exist)
1. Go to http://localhost:8001
2. Click on "ParentalPolicies" table
3. Add a test policy (optional)

---

## 📊 Test the Full Flow

### Create a Test Policy

```python
import boto3

# Connect to local DynamoDB
dynamodb = boto3.resource('dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='ap-south-1',
    aws_access_key_id='dummy',
    aws_secret_access_key='dummy'
)

table = dynamodb.Table('ParentalPolicies')

# Create policy for test phone number
policy = {
    'childPhoneNumber': '+15551234567',
    'policyId': 'policy_test_001',
    'childName': 'Test Child',
    'parentEmail': 'parent@test.com',
    'blockedApps': [
        {
            'appName': 'TikTok',
            'ports': [{'port': 443, 'protocol': 'TCP'}],
            'domains': ['*.tiktok.com']
        }
    ],
    'timeWindows': [
        {
            'startTime': '22:00',
            'endTime': '06:00',
            'days': ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        }
    ],
    'status': 'active',
    'createdAt': '2025-10-03T10:00:00Z',
    'updatedAt': '2025-10-03T10:00:00Z'
}

table.put_item(Item=policy)
print("✅ Policy created!")
```

---

## 🎯 Expected Results

After running all services, you should see:

1. **P-Gateway Simulator Console**:
   ```
   Stats - Active: 47, Created: 150, Terminated: 103
   ```

2. **Kafka Subscriber Console**:
   ```
   Stats - Processed: 150, Redis Success: 150, Active Sessions: 47
   ```

3. **Kafka UI** (http://localhost:8080):
   - Topic: `session-data` with messages
   - Consumer group: `parental-control-subscriber` with no lag

4. **Redis** (http://localhost:8081):
   - Multiple keys for active sessions
   - Each key has TTL of 24 hours

---

## 🛑 Stop Everything

```bash
# Stop services (Ctrl+C in each terminal)

# Stop Docker containers
cd deployment/docker
docker-compose down
```

---

## 🚢 Deploy to AWS

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for AWS deployment instructions.

**Quick AWS Deploy:**
```bash
# 1. Configure AWS CLI
aws configure
# Region: ap-south-1 (Mumbai)

# 2. Deploy infrastructure
cd infrastructure/cloudformation
cloudformation init
cloudformation apply

# 3. Build and push Docker images
./scripts/build-and-push.sh

# 4. Deploy services
./scripts/deploy-services.sh prod
```

---

## 📚 Documentation

- **Full Documentation**: [README.md](README.md)
- **System Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Deployment Guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Database Schema**: [docs/DYNAMODB_SCHEMA.md](docs/DYNAMODB_SCHEMA.md)
- **Project Summary**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

---

## ❓ Troubleshooting

### Kafka not starting
```bash
# Check logs
docker logs pc-kafka

# Restart
docker-compose restart kafka
```

### Redis connection refused
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli -h localhost -p 6379 ping
```

### Python dependencies error
```bash
# Use virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🎉 Success!

You now have a fully functional local development environment for the Parental Control backend!

**Next Steps:**
1. Explore the code in `services/`
2. Modify simulator settings in `services/p-gateway-simulator/config/simulator.yaml`
3. Add more test policies
4. Build the Policy Enforcer service
5. Integrate with Cisco FTD

---

**Questions?** Check [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) or raise an issue on GitHub.
