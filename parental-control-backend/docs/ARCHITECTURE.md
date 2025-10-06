# Parental Control Backend - System Architecture

## Overview
The Parental Control Backend is a cloud-native, event-driven system that integrates with 5G networks and Cisco Firepower Threat Defense (FTD) to provide real-time application blocking for child devices based on parental policies.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AWS Cloud Environment                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────┐         ┌──────────────────┐                      │
│  │  P-Gateway       │         │   Amazon MSK     │                      │
│  │  Simulator       │────────▶│   (Kafka)        │                      │
│  │  (5G SA)         │         │                  │                      │
│  │  - CDR Generator │         │  Topic:          │                      │
│  │  - IMSI Mapping  │         │  - session-data  │                      │
│  └──────────────────┘         └────────┬─────────┘                      │
│                                         │                                │
│                                         ▼                                │
│                                ┌─────────────────┐                       │
│                                │  Kafka          │                       │
│                                │  Subscriber     │                       │
│                                │  Service        │                       │
│                                │  (Lambda/ECS)   │                       │
│                                └────────┬────────┘                       │
│                                         │                                │
│                                         ▼                                │
│                                ┌─────────────────┐                       │
│                                │  ElastiCache    │                       │
│                                │  (Redis)        │                       │
│                                │                 │                       │
│  ┌──────────────────┐          │ IMSI → IP       │                       │
│  │  DynamoDB        │          │ PhoneNum → IP   │                       │
│  │  Policy DB       │          │ Session TTL     │                       │
│  │                  │          └────────┬────────┘                       │
│  │  - Child Policies│                   │                                │
│  │  - App Rules     │                   │                                │
│  │  - Time Windows  │                   │                                │
│  └────────┬─────────┘                   │                                │
│           │                             │                                │
│           │         ┌───────────────────┴─────────────────┐              │
│           │         │                                     │              │
│           └────────▶│  Policy Enforcement Service         │              │
│                     │  (ECS Fargate)                      │              │
│                     │                                     │              │
│                     │  - Policy Monitor                   │              │
│                     │  - IP Change Detector               │              │
│                     │  - Rule Synchronizer                │              │
│                     └──────────┬──────────────────────────┘              │
│                                │                                         │
│                                ▼                                         │
│                     ┌──────────────────────┐                             │
│                     │  FTD Integration     │                             │
│                     │  Service             │                             │
│                     │                      │                             │
│                     │  - FTD API Client    │                             │
│                     │  - SSH Client        │                             │
│                     │  - Rule Manager      │                             │
│                     └──────────┬───────────┘                             │
│                                │                                         │
└────────────────────────────────┼─────────────────────────────────────────┘
                                 │
                                 ▼
                        ┌────────────────────┐
                        │  Cisco FTD         │
                        │  Firewall          │
                        │                    │
                        │  - Access Rules    │
                        │  - Port Blocking   │
                        │  - IP Filtering    │
                        └────────────────────┘
```

## AWS Services Used

### 1. **Amazon MSK (Managed Streaming for Kafka)**
- **Purpose**: Message bus for P-Gateway CDR (Call Detail Records) streaming
- **Configuration**:
  - 3 broker cluster for high availability
  - Topic: `session-data` with 6 partitions
  - Retention: 7 days
  - Auto-scaling enabled
- **Data Format**: JSON CDR records

### 2. **Amazon ElastiCache (Redis)**
- **Purpose**: Real-time session tracking (IMSI to IP mapping)
- **Configuration**:
  - Cluster mode enabled
  - 2 shards with 1 replica each
  - Instance type: cache.r6g.large
- **Data Structure**:
  ```
  Key: imsi:{IMSI}           → Value: {privateIP, publicIP, timestamp}
  Key: phone:{phoneNumber}   → Value: {privateIP, publicIP, IMSI}
  Key: ip:{privateIP}        → Value: {IMSI, phoneNumber, sessionId}
  TTL: 24 hours (auto-refresh on activity)
  ```

### 3. **Amazon DynamoDB**
- **Purpose**: Policy database for parental controls
- **Tables**:

  **Table: ParentalPolicies**
  ```
  PK: childPhoneNumber
  SK: policyId
  Attributes:
    - childName
    - parentEmail
    - blockedApps: [{ appName, ports, protocol }]
    - timeWindows: [{ startTime, endTime, days }]
    - status: active|inactive
    - createdAt, updatedAt
  ```

  **Table: ApplicationRegistry**
  ```
  PK: appName
  Attributes:
    - appCategory
    - defaultPorts: [{ port, protocol }]
    - domains: []
    - ipRanges: []
  ```

  **Table: EnforcementHistory**
  ```
  PK: childPhoneNumber
  SK: timestamp
  Attributes:
    - action: block|unblock
    - appName
    - privateIP
    - ruleId
    - status: success|failed
  ```

### 4. **AWS Lambda**
- **Kafka Consumer Function**: Processes Kafka messages and updates Redis
- **DynamoDB Streams Function**: Triggers on policy changes
- **Scheduled Functions**: IP lease expiration checks

### 5. **Amazon ECS (Fargate)**
- **Policy Enforcement Service**: Long-running microservice
  - Auto-scaling based on DynamoDB stream backlog
  - Min: 2 tasks, Max: 10 tasks

- **P-Gateway Simulator**: Containerized simulator
  - Generates realistic 5G session data

- **FTD Integration Service**: Manages firewall rules
  - Connection pooling for FTD SSH sessions
  - API retry logic with exponential backoff

### 6. **Amazon CloudWatch**
- Metrics, Logs, and Alarms
- Custom metrics for:
  - Policy enforcement latency
  - FTD API success rate
  - IP mapping cache hit rate

### 7. **AWS Secrets Manager**
- Stores:
  - FTD SSH credentials
  - FTD API tokens
  - Redis connection strings
  - Kafka authentication

### 8. **Amazon VPC**
- Private subnets for services
- NAT Gateway for outbound traffic
- VPC Endpoints for AWS services
- Security groups for service isolation

### 9. **AWS EventBridge**
- Scheduled rules for:
  - Periodic policy synchronization
  - IP lease cleanup
  - Health checks

### 10. **Amazon ECR**
- Docker image repository for all microservices

## Data Flow

### 1. Session Establishment Flow
```
1. P-Gateway creates new session
2. P-Gateway publishes to Kafka: {IMSI, privateIP, publicIP, phoneNumber, timestamp}
3. Kafka Subscriber receives message
4. Subscriber updates Redis:
   - SET imsi:{IMSI} → {IP data}
   - SET phone:{phoneNumber} → {IP data}
   - SET ip:{privateIP} → {session data}
   - EXPIRE keys after 24h
5. Subscriber checks DynamoDB for existing policies for phoneNumber
6. If policy exists → Trigger Policy Enforcer
```

### 2. Policy Enforcement Flow
```
1. Policy Enforcer receives new policy or IP mapping
2. Fetch policy from DynamoDB
3. Lookup current IP from Redis (phone:{phoneNumber})
4. If IP found:
   a. Call FTD Integration Service
   b. Generate firewall rules for blocked apps
   c. Apply rules via FTD API or SSH CLI
   d. Log to EnforcementHistory table
5. If IP not found:
   a. Queue for retry (wait for session establishment)
```

### 3. IP Change Detection Flow
```
1. Kafka Subscriber detects new IP for existing IMSI
2. Fetch old IP from Redis
3. Update Redis with new IP
4. Notify Policy Enforcer of IP change
5. Policy Enforcer:
   a. Remove old firewall rules (old IP)
   b. Apply new firewall rules (new IP)
   c. Update EnforcementHistory
```

### 4. Policy Update Flow
```
1. Parent updates policy via web app → API Gateway → DynamoDB
2. DynamoDB Streams trigger Lambda
3. Lambda invokes Policy Enforcer
4. Policy Enforcer:
   a. Fetch current IP from Redis
   b. Calculate rule diff (added/removed apps)
   c. Update FTD rules accordingly
   d. Log changes
```

## Microservices Details

### P-Gateway Simulator Service
**Technology**: Node.js / Python
**Purpose**: Simulate 5G SA P-Gateway behavior
**Features**:
- Generate realistic CDR records
- Simulate DHCP IP allocation
- IMSI to phone number mapping
- Configurable session duration
- IP address pool management

**Kafka Message Format**:
```json
{
  "eventType": "SESSION_START|SESSION_END|IP_CHANGE",
  "timestamp": "2025-10-03T10:30:00Z",
  "imsi": "310150123456789",
  "msisdn": "+15551234567",
  "privateIP": "10.20.30.40",
  "publicIP": "203.0.113.50",
  "sessionId": "sess_abc123",
  "apn": "internet",
  "ratType": "NR"
}
```

### Kafka Subscriber Service
**Technology**: Python (confluent-kafka)
**Purpose**: Consume Kafka messages and update Redis
**Features**:
- Consumer group management
- Offset management
- Batch processing
- Error handling and dead-letter queue
- Redis connection pooling

### Policy Enforcement Service
**Technology**: Python (asyncio)
**Purpose**: Core orchestrator for policy enforcement
**Components**:
- **Policy Monitor**: Watches DynamoDB for policy changes
- **IP Change Detector**: Monitors Redis for IP updates
- **Rule Synchronizer**: Ensures FTD rules match policies
- **Scheduler**: Handles time-based policy enforcement

### FTD Integration Service
**Technology**: Python (paramiko, requests)
**Purpose**: Interface with Cisco FTD
**Features**:
- FTD REST API client (FMC - Firepower Management Center)
- SSH CLI fallback
- Rule templating
- Transaction management
- Idempotency checks

**FTD Rule Structure**:
```python
{
  "name": f"PARENTAL_BLOCK_{phoneNumber}_{appName}",
  "action": "BLOCK",
  "enabled": True,
  "source": {
    "networks": [{"value": privateIP}]
  },
  "destination": {
    "ports": [{"protocol": "TCP", "port": "443"}]
  },
  "priority": 100
}
```

## Scalability Considerations

1. **Kafka Partitioning**: 6 partitions allow parallel processing
2. **Redis Clustering**: Horizontal scaling for high throughput
3. **ECS Auto-scaling**: Based on CPU/memory and custom metrics
4. **DynamoDB On-Demand**: Auto-scales with traffic
5. **Connection Pooling**: Reuse FTD API/SSH connections

## High Availability

1. **Multi-AZ Deployment**: All services across 3 AZs
2. **MSK Replication**: 3 brokers with replication factor 3
3. **Redis Replicas**: 1 replica per shard
4. **ECS Tasks**: Min 2 instances per service
5. **Health Checks**: Automated failover

## Security

1. **Encryption**:
   - In-transit: TLS 1.3 for all services
   - At-rest: KMS encryption for DynamoDB, Redis, MSK
2. **Authentication**:
   - IAM roles for service-to-service
   - Secrets Manager for credentials
3. **Network Isolation**:
   - Private subnets for all services
   - Security groups with least privilege
4. **Audit**:
   - CloudTrail for API calls
   - CloudWatch Logs for all services

## Monitoring & Observability

### Key Metrics
1. **Kafka Lag**: Consumer group lag
2. **Redis Cache Hit Rate**: IP lookup efficiency
3. **Policy Enforcement Latency**: Time from policy update to FTD rule applied
4. **FTD API Success Rate**: API call success percentage
5. **IP Mapping Accuracy**: Correct IMSI-to-IP mappings

### Alarms
1. Kafka consumer lag > 1000 messages
2. Redis memory > 80%
3. Policy enforcement failures > 5% in 5 minutes
4. FTD API errors > 10% in 5 minutes

## Disaster Recovery

1. **RTO**: 15 minutes
2. **RPO**: 5 minutes
3. **Backup Strategy**:
   - DynamoDB PITR (Point-in-Time Recovery)
   - Redis daily snapshots
   - Kafka message retention: 7 days
4. **Failover**:
   - Automated cross-region replication (optional)
   - Runbook for manual failover

## Performance Requirements

1. **Kafka Throughput**: 10,000 messages/second
2. **Redis Operations**: 100,000 ops/second
3. **DynamoDB**: 5,000 read/write capacity units
4. **Policy Enforcement**: < 2 seconds end-to-end
5. **FTD Rule Application**: < 500ms per rule

## Cost Optimization

1. **Spot Instances**: Use for P-Gateway simulator
2. **Reserved Capacity**: ElastiCache and MSK
3. **DynamoDB On-Demand**: Only pay for usage
4. **S3 Lifecycle**: Archive logs after 30 days
5. **Lambda**: Serverless for event-driven tasks
