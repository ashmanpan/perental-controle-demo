## DynamoDB Schema Design

### Table 1: ParentalPolicies

**Purpose**: Store parental control policies for children

**Keys**:
- Partition Key: `childPhoneNumber` (String) - Phone number of the child
- Sort Key: `policyId` (String) - Unique policy identifier

**Attributes**:
```
{
  "childPhoneNumber": "+15551234567",
  "policyId": "policy_20251003_001",
  "childName": "Sarah",
  "parentEmail": "parent@example.com",
  "blockedApps": [
    {
      "appName": "TikTok",
      "ports": [
        {"port": 443, "protocol": "TCP"},
        {"port": 80, "protocol": "TCP"}
      ],
      "domains": ["*.tiktok.com", "*.musical.ly"],
      "ipRanges": ["23.211.0.0/16"]
    },
    {
      "appName": "Instagram",
      "ports": [{"port": 443, "protocol": "TCP"}],
      "domains": ["*.instagram.com", "*.cdninstagram.com"],
      "ipRanges": []
    }
  ],
  "timeWindows": [
    {
      "startTime": "22:00",
      "endTime": "06:00",
      "days": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    },
    {
      "startTime": "08:00",
      "endTime": "15:00",
      "days": ["MON", "TUE", "WED", "THU", "FRI"]
    }
  ],
  "status": "active",
  "createdAt": "2025-10-01T10:00:00Z",
  "updatedAt": "2025-10-03T14:30:00Z",
  "notes": "School and sleep time restrictions"
}
```

**Global Secondary Indexes**:
1. **ParentEmailIndex**
   - Partition Key: `parentEmail`
   - Sort Key: `createdAt`
   - Purpose: Query all policies for a parent

**Access Patterns**:
- Get all policies for a child: Query by `childPhoneNumber`
- Get specific policy: Get by `childPhoneNumber` + `policyId`
- Get all policies for a parent: Query `ParentEmailIndex`
- Update policy: Update by `childPhoneNumber` + `policyId`

---

### Table 2: ApplicationRegistry

**Purpose**: Registry of popular applications with default port/domain information

**Keys**:
- Partition Key: `appName` (String) - Name of the application

**Attributes**:
```json
{
  "appName": "TikTok",
  "appCategory": "Social Media",
  "defaultPorts": [
    {"port": 443, "protocol": "TCP"},
    {"port": 80, "protocol": "TCP"}
  ],
  "domains": [
    "*.tiktok.com",
    "*.tiktokv.com",
    "*.musical.ly",
    "*.tiktokcdn.com"
  ],
  "ipRanges": [
    "23.211.0.0/16",
    "104.16.0.0/12"
  ],
  "description": "Short-form video social media platform",
  "popularity": 1,
  "lastUpdated": "2025-10-01T00:00:00Z"
}
```

**Sample Applications**:
```json
[
  {
    "appName": "YouTube",
    "appCategory": "Video Streaming",
    "defaultPorts": [{"port": 443, "protocol": "TCP"}],
    "domains": ["*.youtube.com", "*.googlevideo.com", "*.ytimg.com"],
    "ipRanges": ["172.217.0.0/16", "142.250.0.0/15"]
  },
  {
    "appName": "Instagram",
    "appCategory": "Social Media",
    "defaultPorts": [{"port": 443, "protocol": "TCP"}],
    "domains": ["*.instagram.com", "*.cdninstagram.com", "*.fbcdn.net"],
    "ipRanges": ["31.13.0.0/16", "157.240.0.0/16"]
  },
  {
    "appName": "Snapchat",
    "appCategory": "Social Media",
    "defaultPorts": [{"port": 443, "protocol": "TCP"}],
    "domains": ["*.snapchat.com", "*.sc-cdn.net"],
    "ipRanges": ["35.184.0.0/13"]
  },
  {
    "appName": "Fortnite",
    "appCategory": "Gaming",
    "defaultPorts": [
      {"port": 443, "protocol": "TCP"},
      {"port": 3478, "protocol": "UDP"},
      {"port": 9000, "protocol": "UDP"},
      {"port": 9001, "protocol": "UDP"}
    ],
    "domains": ["*.epicgames.com", "*.fortnite.com"],
    "ipRanges": []
  }
]
```

**Access Patterns**:
- Get app details: Get by `appName`
- List all apps: Scan (cached)

---

### Table 3: EnforcementHistory

**Purpose**: Track all policy enforcement actions

**Keys**:
- Partition Key: `childPhoneNumber` (String)
- Sort Key: `timestamp` (String) - ISO 8601 format

**Attributes**:
```json
{
  "childPhoneNumber": "+15551234567",
  "timestamp": "2025-10-03T14:30:45Z",
  "action": "block",
  "appName": "TikTok",
  "privateIP": "10.20.30.40",
  "ruleId": "ftd_rule_abc123",
  "status": "success",
  "errorMessage": "",
  "ftdResponse": {
    "ruleId": "005056A7-BF9E-0ed3-0000-004294967296",
    "deviceId": "ftd-device-001"
  },
  "duration_ms": 342
}
```

**Global Secondary Indexes**:
1. **StatusTimestampIndex**
   - Partition Key: `status`
   - Sort Key: `timestamp`
   - Purpose: Query all failed enforcement attempts

**Access Patterns**:
- Get enforcement history for child: Query by `childPhoneNumber`
- Get recent enforcement actions: Query by `childPhoneNumber` + timestamp range
- Get failed actions: Query `StatusTimestampIndex` where status = 'failed'

**TTL**: 90 days (delete old records automatically)

---

### Table 4: BlockedRequestMetrics

**Purpose**: Aggregate metrics of blocked requests for parent dashboard

**Keys**:
- Partition Key: `childPhoneNumber` (String)
- Sort Key: `dateApp` (String) - Format: "YYYY-MM-DD#AppName"

**Attributes**:
```json
{
  "childPhoneNumber": "+15551234567",
  "dateApp": "2025-10-03#TikTok",
  "date": "2025-10-03",
  "appName": "TikTok",
  "parentEmail": "parent@example.com",
  "blockedCount": 47,
  "timestampFirst": "2025-10-03T08:15:23Z",
  "timestampLast": "2025-10-03T14:52:10Z",
  "hourly": {
    "08": 5,
    "09": 12,
    "10": 8,
    "11": 6,
    "12": 4,
    "13": 7,
    "14": 5
  }
}
```

**Global Secondary Indexes**:
1. **ParentEmailDateIndex**
   - Partition Key: `parentEmail`
   - Sort Key: `date`
   - Purpose: Query all metrics for a parent by date

**Access Patterns**:
- Get daily metrics for child: Query by `childPhoneNumber` + date prefix
- Get metrics for parent: Query `ParentEmailDateIndex`
- Get app-specific metrics: Query by `childPhoneNumber` + exact `dateApp`

**Update Pattern**: Use atomic counter increments
```python
dynamodb.update_item(
    Key={'childPhoneNumber': '+15551234567', 'dateApp': '2025-10-03#TikTok'},
    UpdateExpression='ADD blockedCount :inc SET timestampLast = :ts',
    ExpressionAttributeValues={':inc': 1, ':ts': '2025-10-03T14:52:10Z'}
)
```

---

### Table 5: FTDRuleMapping

**Purpose**: Track mapping between policies and FTD rules

**Keys**:
- Partition Key: `childPhoneNumber` (String)
- Sort Key: `ruleId` (String) - FTD rule ID

**Attributes**:
```json
{
  "childPhoneNumber": "+15551234567",
  "ruleId": "ftd_rule_abc123",
  "ruleName": "PARENTAL_BLOCK_+15551234567_TikTok",
  "privateIP": "10.20.30.40",
  "appName": "TikTok",
  "policyId": "policy_20251003_001",
  "ftdDeviceId": "ftd-device-001",
  "accessPolicyId": "005056A7-BF9E-0ed3-0000-123456789",
  "status": "active",
  "createdAt": "2025-10-03T14:30:45Z",
  "lastVerified": "2025-10-03T15:00:00Z"
}
```

**Access Patterns**:
- Get all FTD rules for a child: Query by `childPhoneNumber`
- Get specific rule: Get by `childPhoneNumber` + `ruleId`
- Delete rule when session ends: Delete by `childPhoneNumber` + `ruleId`

**TTL**: Based on session expiration (cleanup old rules)

---

## DynamoDB Capacity Planning

### Read/Write Capacity Units

**ParentalPolicies**:
- Provisioned: 10 RCU, 5 WCU (mostly reads)
- On-Demand: Recommended for unpredictable traffic

**ApplicationRegistry**:
- Provisioned: 5 RCU, 1 WCU (read-heavy, rarely updated)
- Consider caching in Redis

**EnforcementHistory**:
- On-Demand: Write-heavy during peak hours
- Estimated: 100 writes/second during peak

**BlockedRequestMetrics**:
- On-Demand: Frequent atomic updates
- Estimated: 500 writes/second during peak

**FTDRuleMapping**:
- Provisioned: 20 RCU, 20 WCU
- Frequent updates during IP changes

### Cost Optimization

1. **Use On-Demand for variable workloads** (EnforcementHistory, BlockedRequestMetrics)
2. **Use Provisioned for predictable workloads** (ParentalPolicies, ApplicationRegistry)
3. **Enable TTL** for EnforcementHistory and FTDRuleMapping
4. **Use DynamoDB Streams** for triggering policy enforcement
5. **Cache ApplicationRegistry** in Redis/ElastiCache

---

## Sample Seed Data Script

```python
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Seed ApplicationRegistry
app_table = dynamodb.Table('ApplicationRegistry')
apps = [
    {
        'appName': 'TikTok',
        'appCategory': 'Social Media',
        'defaultPorts': [{'port': 443, 'protocol': 'TCP'}],
        'domains': ['*.tiktok.com', '*.musical.ly'],
        'ipRanges': ['23.211.0.0/16']
    },
    {
        'appName': 'Instagram',
        'appCategory': 'Social Media',
        'defaultPorts': [{'port': 443, 'protocol': 'TCP'}],
        'domains': ['*.instagram.com'],
        'ipRanges': ['31.13.0.0/16']
    }
    # ... more apps
]

for app in apps:
    app_table.put_item(Item=app)
```
