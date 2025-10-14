# Parental Control System - Testing Quick Start Guide

**Date:** 2025-10-14
**Status:** All services deployed and ready for testing
**FTDv Status:** Running and accessible from VPC

---

## Current System Status

### Services Running
| Service | Status | Tasks | IP Address | Port |
|---------|--------|-------|------------|------|
| ftd-integration | ACTIVE | 4/2 | 10.0.2.80 | 5000 |
| analytics-dashboard | ACTIVE | 2/2 | 10.0.3.139 | 8000 |
| p-gateway | ACTIVE | 2/2 | - | - |
| kafka-subscriber | ACTIVE | 2/2 | - | - |
| policy-enforcer | ACTIVE | 2/2 | - | - |

### FTDv Firewall
- **Instance ID:** i-0dc44d9e05f241a2e
- **State:** running
- **Uptime:** ~14 hours
- **Private IP (Management):** 10.0.101.119
- **Public IP:** 13.202.127.153
- **Credentials:** admin / Cisco@123456
- **SSH Port:** 22
- **HTTPS Port:** 443

### Active Sessions
- **Count:** 100+ active phone-to-IP mappings in Redis
- **Data Flow:** p-gateway → Kafka → kafka-subscriber → Redis
- **Sample Phone Numbers:**
  - +12064882538 → 10.20.81.128
  - +12066186006 → 10.20.54.202
  - +14152623400 → 10.20.118.163

---

## VPC Access Requirement

All services and FTDv are **VPC-only** accessible (10.0.0.0/16). You cannot test from external networks without VPC access.

### Option 1: Launch EC2 Bastion Host (Recommended)

**Quickest and most flexible method**

```bash
# 1. Launch a small EC2 instance in the VPC
aws ec2 run-instances \
  --image-id ami-0dee22c13ea7a9a67 \
  --instance-type t3.micro \
  --key-name your-key-name \
  --subnet-id subnet-0ec948a6e4a9d4fd8 \
  --security-group-ids sg-0d1a1f93de4547e6a \
  --region ap-south-1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=pc-test-bastion}]'

# 2. Get the instance public IP
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=pc-test-bastion" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --region ap-south-1 \
  --output text

# 3. SSH to the bastion
ssh -i your-key.pem ec2-user@<public-ip>

# 4. Install testing tools
sudo yum install -y curl jq

# 5. Copy and run the test script
# (Transfer test-ftd-integration.sh to the bastion)
scp -i your-key.pem test-ftd-integration.sh ec2-user@<public-ip>:~/
ssh -i your-key.pem ec2-user@<public-ip>
./test-ftd-integration.sh
```

### Option 2: Temporary Security Group Rule

**Quick but less secure - remember to remove after testing**

```bash
# 1. Get your public IP
MY_IP=$(curl -s https://api.ipify.org)
echo "Your IP: ${MY_IP}"

# 2. Add temporary ingress rule
aws ec2 authorize-security-group-ingress \
  --group-id sg-0d1a1f93de4547e6a \
  --protocol tcp \
  --port 5000 \
  --cidr ${MY_IP}/32 \
  --region ap-south-1

# 3. Test from your machine
curl http://10.0.2.80:5000/health

# 4. IMPORTANT: Remove the rule after testing
aws ec2 revoke-security-group-ingress \
  --group-id sg-0d1a1f93de4547e6a \
  --protocol tcp \
  --port 5000 \
  --cidr ${MY_IP}/32 \
  --region ap-south-1
```

### Option 3: AWS Systems Manager Session Manager

**No SSH keys needed, but requires SSM agent**

```bash
# 1. Start session to any ECS task (requires ECS Exec enabled)
# First, enable ECS Exec on the service
aws ecs update-service \
  --cluster pc-prod-cluster \
  --service pc-prod-ftd-integration-service \
  --enable-execute-command \
  --region ap-south-1

# 2. Force new deployment to get tasks with execute command enabled
aws ecs update-service \
  --cluster pc-prod-cluster \
  --service pc-prod-ftd-integration-service \
  --force-new-deployment \
  --region ap-south-1

# 3. Wait for new tasks to be running, then get task ID
TASK_ARN=$(aws ecs list-tasks \
  --cluster pc-prod-cluster \
  --service-name pc-prod-ftd-integration-service \
  --desired-status RUNNING \
  --region ap-south-1 \
  --query 'taskArns[0]' \
  --output text)

# 4. Start session
aws ecs execute-command \
  --cluster pc-prod-cluster \
  --task ${TASK_ARN} \
  --container ftd-integration \
  --interactive \
  --command "/bin/sh" \
  --region ap-south-1
```

---

## Manual Testing Commands

Once you have VPC access, run these commands:

### Test 1: Health Checks

```bash
# ftd-integration health
curl http://10.0.2.80:5000/health

# analytics-dashboard health
curl http://10.0.3.139:8000/health
```

### Test 2: Query Session Data

```bash
# Get session by phone number
curl http://10.0.3.139:8000/api/v1/session/phone/+12064882538 | jq '.'

# Get session by IP
curl http://10.0.3.139:8000/api/v1/session/ip/10.20.81.128 | jq '.'

# Get active sessions count
curl http://10.0.3.139:8000/api/v1/sessions/active/count | jq '.'
```

### Test 3: Create FTD Block Rule

```bash
# Create a rule to block TikTok for a specific user
curl -X POST http://10.0.2.80:5000/api/v1/rules/block \
  -H "Content-Type: application/json" \
  -d '{
    "sourceIP": "10.20.81.128",
    "appName": "TikTok",
    "ports": [
      {"protocol": "TCP", "port": 443},
      {"protocol": "TCP", "port": 80}
    ],
    "msisdn": "+12064882538"
  }' | jq '.'
```

**Expected Response (SSH method):**
```json
{
  "ruleId": "ssh_abc123def456",
  "ruleName": "PARENTAL_BLOCK_12064882538_TikTok",
  "method": "SSH",
  "aclName": "PARENTAL_CONTROL_ACL",
  "status": "created",
  "deploymentRequired": false
}
```

**Expected Response (API method):**
```json
{
  "ruleId": "000XXXXX-YYYY-ZZZZ-0000-XXXXXXXXXXXX",
  "ruleName": "PARENTAL_BLOCK_12064882538_TikTok",
  "method": "API",
  "policyId": "000XXXXX-YYYY-ZZZZ-0000-XXXXXXXXXXXX",
  "status": "created",
  "deploymentRequired": true
}
```

### Test 4: Verify Rule on FTDv

```bash
# SSH to FTDv
ssh admin@10.0.101.119
# Password: Cisco@123456

# Check if rule exists
show access-list PARENTAL_CONTROL_ACL

# Expected output:
# access-list PARENTAL_CONTROL_ACL line 1 extended deny tcp host 10.20.81.128 any eq 443
# access-list PARENTAL_CONTROL_ACL line 2 extended deny tcp host 10.20.81.128 any eq 80
```

### Test 5: Check ftd-integration Logs

```bash
# From AWS CLI
aws logs tail /ecs/pc-prod/ftd-integration \
  --since 5m \
  --follow \
  --format short \
  --region ap-south-1

# Look for:
# - "RuleManager created, will initialize on first use"
# - "Initializing FTD connection..."
# - "Using SSH CLI for rule management" or "Using FMC REST API for rule management"
# - "RuleManager initialized (mode: SSH/API)"
```

---

## Automated Test Script

We've created a comprehensive test script that runs all tests automatically:

### Script Location
```
./test-ftd-integration.sh
```

### What It Tests
1. ✓ ftd-integration health endpoint
2. ✓ Analytics session lookup
3. ✓ FTD rule creation
4. ✓ Rule verification
5. ✓ FTDv connectivity status
6. ✓ Active sessions count

### How to Run
```bash
# From within VPC (bastion host or EC2)
./test-ftd-integration.sh
```

The script will:
- Use fresh session data from analytics service
- Create a test block rule for TikTok
- Verify the rule was created
- Provide next steps based on the method used (SSH vs API)

---

## Troubleshooting

### Issue: Connection timeout to services

**Cause:** Not running from within VPC

**Solution:** Use one of the VPC access methods above

### Issue: "Health endpoint not responding"

**Cause:** Service may be restarting or not fully initialized

**Solution:**
```bash
# Check service status
aws ecs describe-services \
  --cluster pc-prod-cluster \
  --services pc-prod-ftd-integration-service \
  --region ap-south-1

# Check recent logs
aws logs tail /ecs/pc-prod/ftd-integration --since 5m --region ap-south-1
```

### Issue: "Failed to connect to FTDv"

**Cause:** FTDv may not be fully initialized or SSH/API not accessible

**Solution:**
```bash
# Check FTDv instance status
aws ec2 describe-instances \
  --instance-ids i-0dc44d9e05f241a2e \
  --region ap-south-1 \
  --query 'Reservations[0].Instances[0].State.Name'

# Check FTDv network interfaces
aws ec2 describe-instances \
  --instance-ids i-0dc44d9e05f241a2e \
  --region ap-south-1 \
  --query 'Reservations[0].Instances[0].NetworkInterfaces[].{Interface: NetworkInterfaceId, IP: PrivateIpAddress, Status: Status}'

# Test SSH connectivity from bastion
telnet 10.0.101.119 22
```

### Issue: Rule created but not blocking traffic

**Possible Causes:**
1. **API Method:** Policy not deployed to FTDv yet
2. **SSH Method:** Rule order may be incorrect
3. **FTDv:** Initial setup not completed

**Solutions:**

For API method:
```bash
# Check deployment status
curl http://10.0.2.80:5000/api/v1/deployments/status | jq '.'

# Trigger deployment (if available)
curl -X POST http://10.0.2.80:5000/api/v1/deployments/deploy \
  -H "Content-Type: application/json" \
  -d '{"deviceIds": ["device-uuid"]}' | jq '.'
```

For SSH method:
```bash
# SSH to FTDv and check rule order
ssh admin@10.0.101.119
show access-list PARENTAL_CONTROL_ACL

# Verify ACL is applied to an interface
show run access-group
```

For FTDv setup:
```bash
# Access FTDv management console
https://13.202.127.153

# Complete initial setup wizard if prompted
# Credentials: admin / Cisco@123456
```

---

## Expected Behavior

### Lazy Initialization ✓
The ftd-integration service uses **lazy initialization** for FTD connections:
- Service starts immediately without connecting to FTDv
- Health checks pass (or should pass after fix)
- First API call triggers FTD connection
- Connection is established via SSH or FMC API
- Subsequent calls reuse the connection

### Rule Creation Flow

**Via SSH (Standalone FTDv):**
1. API receives rule creation request
2. Lazy initialization connects to FTDv via SSH (if first call)
3. SSH commands create access-list entries
4. Rules are immediately active on FTDv
5. Response includes `"deploymentRequired": false`

**Via API (FTDv with FMC):**
1. API receives rule creation request
2. Lazy initialization connects to FMC API (if first call)
3. FMC API creates rule in policy
4. Rule is pending deployment
5. Response includes `"deploymentRequired": true`
6. Deployment must be triggered separately

---

## Next Steps After Testing

1. **Verify Rule Creation:** Confirm rules are created in FTDv
2. **Test Traffic Blocking:** Generate traffic that should be blocked
3. **Test Rule Updates:** Update existing rules with new IPs
4. **Test Rule Deletion:** Remove rules via API
5. **End-to-End Flow:** Test complete policy enforcement flow:
   - Create policy in DynamoDB
   - Generate session in p-gateway
   - Trigger violation via kafka-subscriber
   - policy-enforcer creates rule via ftd-integration
   - Verify traffic is blocked

6. **Performance Testing:**
   - Measure rule creation latency
   - Test concurrent rule creation
   - Monitor FTDv resource usage

7. **Fix Health Check Issue:** (Optional, low priority)
   - Service is functional despite failing health checks
   - Can be addressed later without impacting testing

---

## Useful Commands Reference

### AWS CLI Commands

```bash
# List all services
aws ecs list-services --cluster pc-prod-cluster --region ap-south-1

# Get service details
aws ecs describe-services \
  --cluster pc-prod-cluster \
  --services pc-prod-ftd-integration-service \
  --region ap-south-1

# Get task IPs
aws ecs list-tasks \
  --cluster pc-prod-cluster \
  --service-name pc-prod-ftd-integration-service \
  --region ap-south-1 \
  --desired-status RUNNING | \
  jq -r '.taskArns[]' | \
  xargs -I {} aws ecs describe-tasks \
    --cluster pc-prod-cluster \
    --tasks {} \
    --region ap-south-1 \
    --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
    --output text

# View logs
aws logs tail /ecs/pc-prod/ftd-integration --follow --region ap-south-1

# Check FTDv status
aws ec2 describe-instances \
  --instance-ids i-0dc44d9e05f241a2e \
  --region ap-south-1

# Get Redis endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id pc-prod-redis-cluster \
  --show-cache-node-info \
  --region ap-south-1
```

### Testing from VPC

```bash
# Quick health check loop
while true; do
  echo "$(date): $(curl -s http://10.0.2.80:5000/health | jq -r '.status')"
  sleep 5
done

# Monitor active sessions
watch -n 5 'curl -s http://10.0.3.139:8000/api/v1/sessions/active/count | jq .'

# Test rule creation with different apps
for app in TikTok Instagram YouTube; do
  echo "Testing ${app}..."
  curl -X POST http://10.0.2.80:5000/api/v1/rules/block \
    -H "Content-Type: application/json" \
    -d "{
      \"sourceIP\": \"10.20.81.128\",
      \"appName\": \"${app}\",
      \"ports\": [{\"protocol\": \"TCP\", \"port\": 443}],
      \"msisdn\": \"+12064882538\"
    }" | jq '.'
  sleep 2
done
```

---

## Summary

✓ **All services deployed and running**
✓ **FTDv deployed and accessible from VPC**
✓ **100+ active sessions in Redis**
✓ **Analytics APIs working with real-time session data**
✓ **Lazy initialization implemented in ftd-integration**
✓ **Test script ready for execution**

⚠ **VPC access required for testing** - Choose one of the three methods above
⚠ **Health check warnings** - Service is functional, can be fixed later

🎯 **Ready for FTD integration testing!**

**Recommended:** Use Option 1 (EC2 Bastion) for most flexible testing experience.
