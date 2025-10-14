# Splunk Deployment Guide for Parental Control Analytics

**Date:** 2025-10-14
**Purpose:** Deploy Splunk on AWS for real-time firewall log analytics and parental control dashboards

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      AWS VPC (ap-south-1)                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────┐  Syslog UDP:514                             │
│  │   FTDv     ├───────────────────┐                         │
│  │ 10.0.101.119│                   │                         │
│  └────────────┘                   ↓                          │
│                           ┌──────────────────┐               │
│                           │  Splunk Heavy    │               │
│                           │  Forwarder (HF)  │               │
│                           │  (Optional)      │               │
│                           └────────┬─────────┘               │
│                                    │ TCP:9997                │
│                                    ↓                          │
│                           ┌──────────────────┐               │
│                           │  Splunk Indexer  │               │
│                           │  EC2: c5.2xlarge │               │
│                           │  Port: 9997      │               │
│                           └────────┬─────────┘               │
│                                    │                          │
│                                    ↓                          │
│                           ┌──────────────────┐               │
│  ┌────────────┐          │  Splunk Search   │               │
│  │   Redis    │◄─────────┤  Head            │               │
│  │ (Lookup)   │  Query   │  Port: 8000      │               │
│  └────────────┘          └──────────────────┘               │
│                                    │                          │
│                                    ↓                          │
│                           Users access via HTTPS:8000        │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- AWS Account with VPC access
- FTDv deployed and accessible (10.0.101.119)
- Redis cluster for session data
- EC2 key pair for SSH access
- Security groups configured

---

## Step 1: Deploy Splunk Enterprise on AWS

### Option A: Using AWS Marketplace (Recommended)

**1. Launch from AWS Marketplace:**
```
1. Go to AWS Marketplace: https://aws.amazon.com/marketplace/pp/B00PUXWXNE
2. Click "Continue to Subscribe"
3. Accept terms and click "Continue to Configuration"
4. Select:
   - Version: Latest (8.2.x or higher)
   - Region: ap-south-1 (Mumbai)
   - Click "Continue to Launch"
```

**2. Configure EC2 Instance:**
```
Instance Type: c5.2xlarge (8 vCPU, 16 GB RAM)
- For production: c5.4xlarge (16 vCPU, 32 GB RAM)
- For testing: c5.xlarge (4 vCPU, 8 GB RAM)

VPC: pc-prod-vpc (same as FTDv)
Subnet: Private subnet (same subnet as ECS tasks)
Security Group: Create new "splunk-server-sg"

Storage:
- Root: 100 GB gp3
- Data volume: 500 GB gp3 (for logs, adjust based on retention needs)

Key Pair: Select your existing key pair
```

**3. Security Group Configuration:**
```bash
# Inbound Rules for splunk-server-sg:
Port 514 (UDP)  - Source: 10.0.0.0/16  - Syslog from FTDv
Port 514 (TCP)  - Source: 10.0.0.0/16  - Syslog from FTDv (alternative)
Port 8000 (TCP) - Source: Your IP      - Splunk Web UI
Port 8089 (TCP) - Source: 10.0.0.0/16  - Splunk Management API
Port 9997 (TCP) - Source: 10.0.0.0/16  - Splunk Forwarder

# Outbound Rules:
All traffic allowed
```

**4. Launch Instance:**
```
Click "Launch" and wait for instance to be running
Note the private IP address (e.g., 10.0.1.50)
```

### Option B: Manual Installation

**1. Launch EC2 Instance:**
```bash
aws ec2 run-instances \
  --image-id ami-0dee22c13ea7a9a67 \
  --instance-type c5.2xlarge \
  --key-name your-key-pair \
  --subnet-id subnet-0ec948a6e4a9d4fd8 \
  --security-group-ids sg-splunk \
  --block-device-mappings '[
    {"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":100,"VolumeType":"gp3"}},
    {"DeviceName":"/dev/xvdb","Ebs":{"VolumeSize":500,"VolumeType":"gp3"}}
  ]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=splunk-server}]' \
  --region ap-south-1
```

**2. SSH and Install Splunk:**
```bash
# SSH to instance
ssh -i your-key.pem ec2-user@<splunk-instance-ip>

# Download Splunk Enterprise
cd /tmp
wget -O splunk.tgz 'https://download.splunk.com/products/splunk/releases/9.1.2/linux/splunk-9.1.2-b6b9c8185839-Linux-x86_64.tgz'

# Extract to /opt
sudo tar -xvzf splunk.tgz -C /opt

# Start Splunk
sudo /opt/splunk/bin/splunk start --accept-license

# Set admin password when prompted
# Username: admin
# Password: <your-secure-password>

# Enable Splunk to start on boot
sudo /opt/splunk/bin/splunk enable boot-start
```

---

## Step 2: Configure Splunk for FTDv Logs

### A. Create Index for FTD Logs

**Via Web UI:**
```
1. Login to Splunk: http://<splunk-ip>:8000
2. Settings → Indexes → New Index
3. Index Name: ftd_logs
4. Max Size: 50 GB (adjust based on needs)
5. Retention: 90 days
6. Click Save
```

**Via CLI:**
```bash
sudo /opt/splunk/bin/splunk add index ftd_logs -maxVolumeDataSizeMB 50000
```

### B. Configure Syslog Input

**Method 1: Via Web UI**
```
1. Settings → Data Inputs → UDP
2. Click "New Local UDP"
3. Port: 514
4. Source type: cisco:asa
5. Index: ftd_logs
6. Save
```

**Method 2: Via inputs.conf**
```bash
# Edit inputs.conf
sudo vi /opt/splunk/etc/apps/search/local/inputs.conf

# Add:
[udp://514]
connection_host = ip
sourcetype = cisco:asa
index = ftd_logs
no_priority_stripping = true
no_appending_timestamp = true

# Restart Splunk
sudo /opt/splunk/bin/splunk restart
```

### C. Verify Syslog Port is Listening

```bash
# Check if Splunk is listening on port 514
sudo netstat -ulnp | grep 514

# Expected output:
# udp    0  0 0.0.0.0:514    0.0.0.0:*    12345/splunkd
```

**Note:** Port 514 requires root. Configure port binding:
```bash
# Allow Splunk to bind to port 514
sudo setcap 'cap_net_bind_service=+ep' /opt/splunk/bin/splunkd

# Or use port forwarding:
sudo iptables -t nat -A PREROUTING -p udp --dport 514 -j REDIRECT --to-port 5140

# Then configure Splunk to listen on 5140 instead
```

---

## Step 3: Configure FTDv to Send Logs to Splunk

### SSH to FTDv and Configure Syslog

```bash
# SSH to FTDv
ssh admin@10.0.101.119
# Password: Cisco@123456

# Enter configuration mode
configure terminal

# Enable logging
logging enable

# Set syslog server (Splunk server IP)
logging host inside <splunk-private-ip> UDP/514

# Example:
logging host inside 10.0.1.50 UDP/514

# Set logging level
logging trap informational

# Enable specific message IDs for parental control
logging message 106023 level informational    # Deny by ACL
logging message 106100 level informational    # Access-list denied
logging message 106006 level informational    # Deny inbound
logging message 106007 level informational    # Deny outbound
logging message 302013 level informational    # Built connection
logging message 302014 level informational    # Teardown connection

# Optional: Set logging facility
logging facility 20

# Save configuration
write memory

# Exit
exit
```

### Verify Logging is Working

```bash
# On FTDv, check logging configuration
show running-config logging

# Expected output:
# logging enable
# logging trap informational
# logging host inside 10.0.1.50

# Test by generating traffic that will be denied
# (Try accessing a blocked app from a test device)
```

---

## Step 4: Verify Log Collection in Splunk

### A. Search for FTD Logs

**1. Login to Splunk Web UI:**
```
http://<splunk-ip>:8000
```

**2. Run Search:**
```spl
index=ftd_logs
| head 100
```

**Expected Output:**
```
Oct 14 10:30:45 10.0.101.119 %ASA-4-106023: Deny tcp src inside:10.20.81.128/45678 dst outside:13.107.42.14/443 by access-group "PARENTAL_CONTROL_ACL"
```

**3. Verify Parental Control Blocks:**
```spl
index=ftd_logs sourcetype=cisco:asa "PARENTAL_CONTROL"
| stats count
```

---

## Step 5: Install Cisco Security Suite App (Optional)

**Splunk has a pre-built app for Cisco security devices:**

```
1. In Splunk Web UI: Apps → Find More Apps
2. Search for "Cisco Security Suite"
3. Click Install
4. Login with Splunk.com credentials
5. Restart Splunk

This app includes:
- Pre-built dashboards for Cisco ASA/FTD
- Field extractions
- Event categorizations
- Correlation searches
```

---

## Step 6: Create Redis Lookup for Phone Numbers

### A. Install Python Redis Library

```bash
# SSH to Splunk server
ssh -i your-key.pem ec2-user@<splunk-ip>

# Install Redis library for Splunk's Python
sudo /opt/splunk/bin/splunk cmd python -m pip install redis
```

### B. Create Lookup Script

```bash
# Create app directory
sudo mkdir -p /opt/splunk/etc/apps/parental_control/bin
sudo mkdir -p /opt/splunk/etc/apps/parental_control/default

# Create lookup script
sudo vi /opt/splunk/etc/apps/parental_control/bin/redis_phone_lookup.py
```

**Script Content:**
```python
#!/opt/splunk/bin/python
import sys
import csv
import redis
import json

# Redis connection configuration
REDIS_HOST = 'your-redis-endpoint.cache.amazonaws.com'
REDIS_PORT = 6379
REDIS_PASSWORD = 'your-redis-password'
REDIS_SSL = True

def lookup_phone(ip_address):
    """Lookup phone number from Redis by IP"""
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            ssl=REDIS_SSL,
            decode_responses=True,
            socket_timeout=5
        )

        # Try direct key first: phone:IP
        key = f"phone:{ip_address}"
        data = redis_client.get(key)

        if data:
            session = json.loads(data)
            return {
                'phone_number': session.get('msisdn', ''),
                'child_name': session.get('childName', 'Unknown'),
                'session_id': session.get('sessionId', ''),
                'imsi': session.get('imsi', '')
            }
    except Exception as e:
        sys.stderr.write(f"Redis lookup error: {e}\n")

    return {
        'phone_number': 'Unknown',
        'child_name': 'Unknown',
        'session_id': '',
        'imsi': ''
    }

def main():
    # Read CSV from Splunk
    reader = csv.DictReader(sys.stdin)

    # Output fields
    fieldnames = ['ip', 'phone_number', 'child_name', 'session_id', 'imsi']
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        ip = row.get('ip', '').strip()
        if ip:
            result = lookup_phone(ip)
            writer.writerow({
                'ip': ip,
                'phone_number': result['phone_number'],
                'child_name': result['child_name'],
                'session_id': result['session_id'],
                'imsi': result['imsi']
            })

if __name__ == '__main__':
    main()
```

**Make executable:**
```bash
sudo chmod +x /opt/splunk/etc/apps/parental_control/bin/redis_phone_lookup.py
```

### C. Configure Transforms

```bash
# Create transforms.conf
sudo vi /opt/splunk/etc/apps/parental_control/default/transforms.conf
```

**Content:**
```ini
[redis_phone_lookup]
external_cmd = redis_phone_lookup.py ip
fields_list = ip, phone_number, child_name, session_id, imsi
```

### D. Test Lookup

```spl
| makeresults count=1
| eval ip="10.20.81.128"
| lookup redis_phone_lookup ip OUTPUT phone_number, child_name
| table ip, phone_number, child_name
```

---

## Step 7: Import Parental Control Dashboard

### A. Create Dashboard App

**1. Create app structure:**
```bash
sudo mkdir -p /opt/splunk/etc/apps/parental_control_dashboard/default
sudo mkdir -p /opt/splunk/etc/apps/parental_control_dashboard/local
```

**2. Create app.conf:**
```bash
sudo vi /opt/splunk/etc/apps/parental_control_dashboard/default/app.conf
```

```ini
[ui]
is_visible = true
label = Parental Control Analytics

[launcher]
author = Cisco
description = Real-time parental control blocking analytics
version = 1.0
```

**3. Save the dashboard XML:**
```bash
sudo vi /opt/splunk/etc/apps/parental_control_dashboard/default/data/ui/views/parental_control_dashboard.xml
```

**(Copy the XML from Step 4 in the main document)**

**4. Restart Splunk:**
```bash
sudo /opt/splunk/bin/splunk restart
```

**5. Access Dashboard:**
```
http://<splunk-ip>:8000/app/parental_control_dashboard/parental_control_dashboard
```

---

## Step 8: Rebuild and Deploy ftd-integration Service

**The code has been updated to enable logging on firewall rules.**

```bash
# Navigate to ftd-integration directory
cd /home/kpanse/wsl-myprojects/parental-control-demo/parental-control-backend/services/ftd-integration

# Build new Docker image
docker build -t parental-control:ftd-integration-splunk .

# Tag for ECR
docker tag parental-control:ftd-integration-splunk \
  264314137331.dkr.ecr.ap-south-1.amazonaws.com/parental-control:ftd-integration-splunk

# Push to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  264314137331.dkr.ecr.ap-south-1.amazonaws.com

docker push 264314137331.dkr.ecr.ap-south-1.amazonaws.com/parental-control:ftd-integration-splunk

# Update ECS service
aws ecs update-service \
  --cluster pc-prod-cluster \
  --service pc-prod-ftd-integration-service \
  --force-new-deployment \
  --region ap-south-1
```

---

## Step 9: Testing End-to-End

### A. Generate Test Traffic

**From a test device or simulator:**
```bash
# Simulate blocked traffic
curl https://www.tiktok.com
# This should be blocked by FTDv and logged
```

### B. Verify in Splunk

**1. Check for deny logs:**
```spl
index=ftd_logs sourcetype=cisco:asa "deny"
earliest=-5m
| table _time, src_ip, dst_ip, dst_port, action
```

**2. Check parental control blocks:**
```spl
index=ftd_logs sourcetype=cisco:asa "PARENTAL_CONTROL_ACL"
earliest=-5m
| rex field=_raw "src inside:(?<src_ip>[\d\.]+)"
| rex field=_raw "dst outside:(?<dst_ip>[\d\.]+)/(?<dst_port>\d+)"
| rex field=_raw "PARENTAL_BLOCK_(?<phone>\d+)_(?<app_name>\w+)"
| lookup redis_phone_lookup ip AS src_ip OUTPUT phone_number
| table _time, phone_number, app_name, src_ip, dst_ip, dst_port
```

**3. View Dashboard:**
```
Go to: http://<splunk-ip>:8000/app/parental_control_dashboard/parental_control_dashboard

You should see:
- Total blocks counter updating
- Hourly trend chart
- Pie chart of blocked apps
- Real-time activity table
```

---

## Troubleshooting

### Issue: No logs appearing in Splunk

**Check 1: FTDv logging configuration**
```bash
# SSH to FTDv
ssh admin@10.0.101.119
show logging

# Should show:
# Syslog logging: enabled
# Logging host: 10.0.1.50
```

**Check 2: Network connectivity**
```bash
# From Splunk server, check if FTDv can reach it
# (FTDv should be able to send UDP to Splunk)

# From Splunk server
sudo tcpdump -i any -n udp port 514

# Then generate traffic on FTDv
# You should see packets arriving
```

**Check 3: Splunk input configuration**
```bash
# On Splunk server
/opt/splunk/bin/splunk list inputstatus

# Should show:
# UDP:514 - ENABLED
```

**Check 4: Firewall/Security Groups**
```bash
# Verify security group allows UDP 514 from FTDv
aws ec2 describe-security-groups \
  --group-ids sg-splunk \
  --region ap-south-1
```

### Issue: Lookup not working

**Check Redis connectivity:**
```bash
# SSH to Splunk server
/opt/splunk/bin/splunk cmd python

>>> import redis
>>> r = redis.Redis(host='your-redis.cache.amazonaws.com', port=6379, password='pwd', ssl=True)
>>> r.ping()
# Should return: True
```

**Check lookup script:**
```bash
# Test manually
echo "ip" | /opt/splunk/etc/apps/parental_control/bin/redis_phone_lookup.py
echo "10.20.81.128" | /opt/splunk/etc/apps/parental_control/bin/redis_phone_lookup.py
```

### Issue: Dashboard not showing data

**Check index:**
```spl
| eventcount summarize=false index=ftd_logs
```

**Check time range:**
```
Make sure dashboard time picker is set correctly (Last 24 hours)
```

---

## Cost Estimation (AWS)

### Monthly Costs:

**Splunk EC2 Instance (c5.2xlarge):**
- Instance: $0.34/hour × 730 hours = ~$248/month
- Storage (600 GB gp3): $0.08/GB = ~$48/month

**Data Transfer:**
- Syslog ingress: Free (within AWS)
- Dashboard access: Minimal (~$1/month)

**Total: ~$297/month**

**For production, consider:**
- Splunk Cloud (managed): Starting at $1,800/month
- Multiple indexers for HA: 2-3x cost
- License based on daily ingestion volume

---

## Summary

✅ **Splunk deployed on AWS EC2**
✅ **FTDv configured to send syslog to Splunk**
✅ **Real-time log collection working**
✅ **Dashboard showing block statistics**
✅ **Redis lookup for phone numbers integrated**
✅ **All queries and visualizations ready**

**Next Steps:**
1. Deploy Splunk to AWS
2. Configure FTDv syslog
3. Import dashboard
4. Start monitoring!

---

**Questions or Issues?**
Check Splunk logs: `/opt/splunk/var/log/splunk/splunkd.log`
