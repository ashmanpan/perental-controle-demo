# Parental Control Backend System

## 🎯 Project Overview

A cloud-native, event-driven backend system that integrates 5G network infrastructure with Cisco Firepower Threat Defense (FTD) to provide real-time parental control enforcement. The system monitors mobile device sessions, maps IMSI/phone numbers to IP addresses, and automatically configures firewall rules to block applications based on parent-defined policies.

## 🏗️ Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system architecture, AWS services, and data flows.

### High-Level Components

1. **P-Gateway Simulator (5G SA)**: Simulates 5G Standalone P-Gateway generating session CDRs
2. **Kafka Message Bus**: Streams session data in real-time
3. **Redis Cache**: Maintains IMSI-to-IP mappings with TTL
4. **DynamoDB Policy Store**: Stores parental control policies
5. **Policy Enforcement Engine**: Orchestrates rule application
6. **Cisco FTD Integration**: Manages firewall rules via API/SSH

## 📁 Project Structure

```
parental-control-backend/
├── services/
│   ├── p-gateway-simulator/       # 5G P-Gateway simulator
│   │   ├── src/
│   │   │   ├── generator.py       # CDR generator
│   │   │   ├── kafka_producer.py  # Kafka producer
│   │   │   ├── session_manager.py # Session lifecycle
│   │   │   └── config.py
│   │   ├── config/
│   │   │   └── simulator.yaml
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── kafka-subscriber/          # Kafka consumer service
│   │   ├── src/
│   │   │   ├── consumer.py        # Kafka consumer
│   │   │   ├── redis_updater.py   # Redis operations
│   │   │   ├── policy_checker.py  # Check for policies
│   │   │   └── config.py
│   │   ├── config/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── policy-enforcer/           # Policy enforcement service
│   │   ├── src/
│   │   │   ├── enforcer.py        # Main orchestrator
│   │   │   ├── policy_monitor.py  # DynamoDB streams handler
│   │   │   ├── ip_monitor.py      # IP change detector
│   │   │   ├── rule_sync.py       # Rule synchronizer
│   │   │   └── scheduler.py       # Time-based policies
│   │   ├── config/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── ftd-integration/           # Cisco FTD integration
│       ├── src/
│       │   ├── ftd_api_client.py  # REST API client
│       │   ├── ftd_ssh_client.py  # SSH CLI client
│       │   ├── rule_manager.py    # Rule CRUD operations
│       │   └── templates/         # Rule templates
│       ├── config/
│       ├── Dockerfile
│       └── requirements.txt
│
├── shared/                        # Shared libraries
│   ├── models/
│   │   ├── session.py            # Session data model
│   │   ├── policy.py             # Policy data model
│   │   └── firewall_rule.py      # FTD rule model
│   ├── utils/
│   │   ├── logger.py
│   │   ├── aws_clients.py        # AWS SDK wrappers
│   │   └── validators.py
│   └── config/
│       └── common.yaml
│
├── infrastructure/                # Infrastructure as Code
│   ├── cloudformation/
│   │   ├── main.yaml
│   │   ├── vpc.yaml
│   │   ├── msk.yaml                # Kafka cluster
│   │   ├── redis.yaml              # ElastiCache
│   │   ├── dynamodb.yaml           # DynamoDB tables
│   │   ├── ecs.yaml                # ECS services
│   │   ├── lambda.yaml             # Lambda functions
│   │   ├── iam.yaml                # IAM roles
│   │   ├── security_groups.yaml
│   │   ├── cloudwatch.yaml
│   │   └── variables.yaml
│   │
│   └── cloudformation/
│       ├── master-stack.yaml
│       ├── network-stack.yaml
│       ├── data-stack.yaml
│       └── compute-stack.yaml
│
├── deployment/
│   ├── docker/
│   │   └── docker-compose.yml    # Local development
│   └── kubernetes/                # K8s manifests (optional)
│       ├── deployments/
│       └── services/
│
├── scripts/
│   ├── setup-aws.sh              # AWS resource setup
│   ├── deploy-services.sh        # Deploy all services
│   ├── seed-data.sh              # Seed test data
│   └── cleanup.sh                # Resource cleanup
│
├── config/
│   ├── dev.env
│   ├── staging.env
│   └── prod.env
│
├── tests/
│   ├── integration/
│   ├── unit/
│   └── e2e/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md                    # API documentation
│   ├── DEPLOYMENT.md             # Deployment guide
│   ├── MONITORING.md             # Monitoring setup
│   └── TROUBLESHOOTING.md
│
├── .gitignore
├── README.md
└── LICENSE
```

## 🚀 Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- Docker & Docker Compose
- AWS CLI configured
- Python 3.11+
- AWS CLI configured
- Cisco FTD/FMC access credentials

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd parental-control-backend
   ```

2. **Set up environment variables**
   ```bash
   cp config/dev.env.example config/dev.env
   # Edit config/dev.env with your values
   ```

3. **Start local services (Kafka, Redis)**
   ```bash
   cd deployment/docker
   docker-compose up -d
   ```

4. **Run services locally**
   ```bash
   # Terminal 1: P-Gateway Simulator
   cd services/p-gateway-simulator
   pip install -r requirements.txt
   python src/generator.py

   # Terminal 2: Kafka Subscriber
   cd services/kafka-subscriber
   pip install -r requirements.txt
   python src/consumer.py

   # Terminal 3: Policy Enforcer
   cd services/policy-enforcer
   pip install -r requirements.txt
   python src/enforcer.py
   ```

### AWS Deployment

1. **Initialize Terraform**
   ```bash
   cd infrastructure/terraform
   terraform init
   ```

2. **Plan infrastructure**
   ```bash
   terraform plan -var-file=../../config/dev.yamlvars
   ```

3. **Apply infrastructure**
   ```bash
   terraform apply -var-file=../../config/dev.yamlvars
   ```

4. **Deploy services**
   ```bash
   cd ../../scripts
   ./deploy-services.sh dev
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `MSK_BOOTSTRAP_SERVERS` | Kafka brokers | - |
| `REDIS_ENDPOINT` | Redis endpoint | - |
| `DYNAMODB_TABLE_POLICIES` | Policy table name | `ParentalPolicies` |
| `FTD_HOST` | FTD/FMC hostname | - |
| `FTD_USERNAME` | FTD username | - |
| `FTD_PASSWORD_SECRET` | Secrets Manager ARN | - |
| `LOG_LEVEL` | Logging level | `INFO` |

### P-Gateway Simulator Configuration

Edit `services/p-gateway-simulator/config/simulator.yaml`:

```yaml
simulation:
  sessions_per_second: 10
  session_duration_min: 300  # 5 minutes
  session_duration_max: 3600 # 1 hour

imsi_pool:
  prefix: "310150"
  range_start: 100000000
  range_end: 199999999

ip_pool:
  private_subnet: "10.20.0.0/16"
  public_subnet: "203.0.113.0/24"

kafka:
  topic: "session-data"
  batch_size: 100
  compression: "gzip"
```

## 📊 Data Models

### Session Event (Kafka Message)

```python
{
  "eventType": "SESSION_START",
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

### Redis Schema

```python
# IMSI to IP mapping
key: "imsi:310150123456789"
value: {
  "privateIP": "10.20.30.40",
  "publicIP": "203.0.113.50",
  "msisdn": "+15551234567",
  "sessionId": "sess_abc123",
  "timestamp": "2025-10-03T10:30:00Z"
}
ttl: 86400  # 24 hours

# Phone to IP mapping
key: "phone:+15551234567"
value: {
  "privateIP": "10.20.30.40",
  "imsi": "310150123456789",
  "sessionId": "sess_abc123"
}
ttl: 86400
```

### DynamoDB Policy Schema

```python
{
  "childPhoneNumber": "+15551234567",  # Partition Key
  "policyId": "policy_001",            # Sort Key
  "childName": "Sarah",
  "parentEmail": "parent@example.com",
  "blockedApps": [
    {
      "appName": "TikTok",
      "ports": [{"port": 443, "protocol": "TCP"}],
      "domains": ["*.tiktok.com"]
    }
  ],
  "timeWindows": [
    {
      "startTime": "22:00",
      "endTime": "06:00",
      "days": ["MON", "TUE", "WED", "THU", "FRI"]
    }
  ],
  "status": "active",
  "createdAt": "2025-10-01T10:00:00Z",
  "updatedAt": "2025-10-03T10:30:00Z"
}
```

## 🔐 Security

1. **Secrets Management**: All credentials stored in AWS Secrets Manager
2. **Encryption**: TLS 1.3 in-transit, KMS encryption at-rest
3. **IAM Roles**: Least privilege access for each service
4. **Network Isolation**: Private subnets, security groups
5. **Audit Logging**: CloudTrail + CloudWatch Logs

## 📈 Monitoring

### Key Metrics

- Kafka consumer lag
- Redis cache hit rate
- DynamoDB read/write capacity
- FTD API latency and error rate
- Policy enforcement success rate
- IP mapping accuracy

### Dashboards

- CloudWatch Dashboard: `parental-control-main`
- Grafana (optional): Import dashboard from `docs/grafana-dashboard.json`

### Alarms

- Consumer lag > 1000 messages
- Redis memory utilization > 80%
- Policy enforcement failures > 5% in 5 min
- FTD API errors > 10% in 5 min

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/ --env=staging
```

## 🐛 Troubleshooting

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues and solutions.

## 📝 API Documentation

See [API.md](docs/API.md) for detailed API documentation.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## 📄 License

[MIT License](LICENSE)

## 👥 Support

For issues and questions:
- GitHub Issues: [Create an issue]
- Email: support@example.com
- Slack: #parental-control-support

## 🗺️ Roadmap

- [ ] Phase 1: Core infrastructure and P-Gateway simulator
- [ ] Phase 2: Kafka subscriber and Redis integration
- [ ] Phase 3: Policy enforcement engine
- [ ] Phase 4: FTD integration (API + SSH)
- [ ] Phase 5: Monitoring and alerting
- [ ] Phase 6: Web dashboard integration
- [ ] Phase 7: Multi-region support
- [ ] Phase 8: Advanced analytics and reporting

## 📚 Related Documentation

- [AWS MSK Documentation](https://docs.aws.amazon.com/msk/)
- [Cisco FTD REST API](https://www.cisco.com/c/en/us/td/docs/security/firepower/api/REST/)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
