# Cisco AI Family Safety - Parental Control Solution Design (On-Premise)

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Frontend Design](#frontend-design)
6. [Backend Design](#backend-design)
7. [Integration Points](#integration-points)
8. [Security Design](#security-design)
9. [Deployment Architecture](#deployment-architecture)
10. [Use Cases & Scenarios](#use-cases--scenarios)

---

## Executive Summary

### Overview
The Cisco AI Family Safety Parental Control Solution is an on-premise, event-driven system that integrates 5G network infrastructure with Cisco Firepower Threat Defense (FTD) to provide real-time application blocking for children's mobile devices based on parent-defined policies.

### Key Innovation
Seamless integration of telecom infrastructure (5G P-Gateway) with enterprise security (Cisco FTD) to enforce parental control policies in real-time at the network level, providing device-agnostic protection - all running within your enterprise data center for complete data sovereignty.

### Value Proposition
- **Real-time Protection**: Apps blocked instantly when child's device connects to network
- **Device-Agnostic**: Works regardless of device type or OS
- **Network-Level Enforcement**: Cannot be bypassed by tech-savvy children
- **Parent Analytics**: Real-time dashboard showing blocked access attempts
- **Scalable**: Handles millions of concurrent sessions
- **Data Sovereignty**: All data remains within enterprise boundaries
- **Compliance Ready**: Meets stringent data privacy requirements

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PARENT INTERFACE (Web)                           │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Frontend (HTML/JS)                                            │    │
│  │  - Parent Login/Registration                                   │    │
│  │  - Child Management                                            │    │
│  │  - App Control Dashboard                                       │    │
│  │  - Analytics & Reports                                         │    │
│  └────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ HTTPS/REST API
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ON-PREMISE BACKEND SERVICES                           │
│                                                                           │
│  ┌──────────────────┐         ┌──────────────────┐                      │
│  │  Splunk Platform │         │  API Gateway     │                      │
│  │  - Dashboards    │◄────────│                  │                      │
│  │  - Analytics     │         └────────┬─────────┘                      │
│  │  - Reporting     │                  │                               │
│  └──────────────────┘                  │                               │
│           │                            │                               │
│           │                   ┌────────▼─────────┐                     │
│           │                   │  IP Lookup       │                     │
│           │                   │  Microservice    │                     │
│           │                   │  Port: 8080      │                     │
│           │                   │  Phone→IP API    │                     │
│           │                   └────────┬─────────┘                     │
│           │                            │                               │
│  ┌────────▼────────────────────────────▼───────────────────────┐      │
│  │              Database Cluster                              │      │
│  │  - ParentalPolicies (child phone → blocked apps)          │      │
│  │  - ApplicationRegistry (app metadata, ports, domains)     │      │
│  │  - EnforcementHistory (audit trail)                       │      │
│  │  - BlockedRequestMetrics (analytics for parents)          │      │
│  │  - FTDRuleMapping (active firewall rules)                 │      │
│  │  Note: Krishnaji will finalize database technology        │      │
│  │        at detailed design phase                            │          │
│  └────────────────────────────────────────────────────────────┘          │
│           ▲                                                              │
│           │                                                              │
│  ┌────────┴──────────┐                                                   │
│  │  Policy Enforcer  │                                                   │
│  │  Service (CSDAC)  │                                                   │
│  │  - Reads Queue    │                                                   │
│  │  - Gets IP from   │                                                   │
│  │    Cache          │                                                   │
│  │  - Calls FTD API  │                                                   │
│  └────────┬──────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐         ┌──────────────────┐                      │
│  │  Message Queue   │         │  In-Memory       │                      │
│  │  (Enforcement    │         │  Cache           │◄────┐                │
│  │   Requests)      │         │  - IMSI → IP     │     │                │
│  └────────▲─────────┘         │  - Phone → IP    │     │                │
│           │                   └────────▲─────────┘     │                │
│           │                            │               │                │
│  ┌────────┴────────┐          ┌────────┴─────────┐     │                │
│  │ Message Consumer│◄─────────│  Message Broker  │     │                │
│  │ Service         │          │  Topic:          │     │                │
│  │ - Updates Cache │          │  session-data    │     │                │
│  │ - Checks Policy │          └────────▲─────────┘     │                │
│  │ - Sends to Queue│                   │               │                │
│  └─────────────────┘                   │               │                │
│                                        │               │                │
│  Note: IP Lookup Microservice reads cache─────────────────┘              │
│        for Phone Number → IP Address lookups                            │
│                                        │                                │
│  ┌─────────────────────────────────────┴──────────┐                     │
│  │  P-Gateway Simulator (5G SA)                   │                     │
│  │  - Generates CDR (Call Detail Records)         │                     │
│  │  - IMSI → Phone Number → IP Address            │                     │
│  │  - Session lifecycle (start, IP change, end)   │                     │
│  └────────────────────────────────────────────────┘                     │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
                                ▼
                  ┌─────────────────────────────┐
                  │  FTD Integration Service    │
                  │  REST API (Port: 5000)      │
                  │  - FMC API Client           │
                  │  - SSH CLI Fallback         │
                  │  - Rule Management          │
                  └──────────────┬──────────────┘
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │  Cisco FTD Firewall         │
                  │  - Access Control Rules     │
                  │  - Port Blocking            │
                  │  - IP-based Filtering       │
                  │  - Logs to Splunk           │
                  └─────────────┬───────────────┘
                                 │               │
                                 ▼               ▼
                  ┌─────────────────────────────┐ ┌─────────────────────────────┐
                  │  Child's Mobile Device      │ │  Splunk Platform            │
                  │  Apps Blocked in Real-time  │ │  - Firewall Log Ingestion   │
                  └─────────────────────────────┘ │  - Real-time Analytics      │
                                                  │  - Parent Dashboards        │
                                                  │  - Compliance Reporting     │
                                                  └─────────────────────────────┘
```

---

## Component Details

### 1. Frontend (Web Application)

**Technology**: HTML5, CSS3, JavaScript (Vanilla)
**Location**: `/frontend/parental-control.html`

#### Features
1. **Parent Authentication**
   - Login with email/password
   - Account creation
   - Session management (localStorage)

2. **Child Management**
   - Add/remove children
   - View child details (name, age, phone number)
   - Multiple children per parent account

3. **App Control Dashboard**
   - Visual grid of top 20 apps
   - Toggle switches for allow/block
   - App categories (Social Media, Gaming, Streaming, etc.)
   - Real-time status updates

4. **Visual Design**
   - Dark theme with gradient accents
   - Animated background
   - Responsive design (mobile-friendly)
   - Material design influence

#### User Flow
```
1. Parent visits website (hosted on internal servers)
2. Login or Create Account
3. View list of children
4. Select child to manage
5. See grid of apps with toggle switches
6. Toggle apps ON (allowed) or OFF (blocked)
7. Changes saved to on-premise database
```

---

### 2. P-Gateway Simulator (5G SA)

**Technology**: Python 3.11
**Location**: `/parental-control-backend/services/p-gateway-simulator/`

#### Purpose
Simulates a 5G Standalone (SA) Packet Gateway that generates Call Detail Records (CDR) for mobile sessions.

#### Key Functions
1. **Session Creation**
   - Generates unique session IDs
   - Maps IMSI to phone numbers
   - Allocates private and public IP addresses
   - Configurable rate (default: 10 sessions/second)

2. **IP Management**
   - IP address pool management
   - Supports IP reassignment (handover simulation)
   - Private IP range: 10.20.0.0/16
   - Public IP range: configurable

3. **Session Lifecycle**
   - SESSION_START: Device connects to network
   - IP_CHANGE: Device moves between towers (handover)
   - SESSION_END: Device disconnects or session expires

4. **Message Publishing**
   - Publishes events to on-premise message broker
   - JSON format with compression
   - Monitoring metrics integration

#### Sample Event
```json
{
  "eventType": "SESSION_START",
  "timestamp": "2025-10-07T10:30:00Z",
  "imsi": "310150123456789",
  "msisdn": "+15551234567",
  "privateIP": "10.20.30.40",
  "publicIP": "203.0.113.50",
  "sessionId": "sess_abc123",
  "apn": "internet",
  "ratType": "NR"
}
```

---

### 3. Message Consumer Service

**Technology**: Python 3.11
**Location**: `/parental-control-backend/services/kafka-subscriber/`

#### Purpose
Consumes session events from message broker and maintains real-time IP mappings in cache.

#### Key Functions
1. **Event Consumption**
   - Subscribes to `session-data` topic on message broker
   - Consumer group: `parental-control-subscriber`
   - Auto-commit disabled for reliability
   - Batch processing support

2. **Cache Updates**
   - **SESSION_START**: Creates mappings
     - `imsi:{IMSI}` → `{privateIP, publicIP, phone, timestamp}`
     - `phone:{phone}` → `{privateIP, IMSI, sessionId}`
     - `ip:{privateIP}` → `{IMSI, phone, sessionId}`
     - TTL: 24 hours

   - **IP_CHANGE**: Updates existing mappings
     - Deletes old IP keys
     - Creates new IP keys
     - Maintains IMSI and phone mappings

   - **SESSION_END**: Removes mappings
     - Deletes all keys for that session

3. **Policy Checking**
   - Queries database for policies matching phone number
   - If policy exists, sends enforcement request to message queue
   - Includes current IP address and policy details

4. **Error Handling**
   - Retry logic for cache failures
   - Dead-letter queue for failed messages
   - Health checks and monitoring

---

### 4. Policy Enforcer Service (CSDAC)

**Technology**: Python 3.11
**Location**: `/parental-control-backend/services/policy-enforcer/`
**Developed by**: CSDAC (Centre for Development of Advanced Computing)

#### Purpose
Orchestrates policy enforcement by coordinating between cache, database, and FTD Integration Service.

#### Key Functions
1. **Queue Processing**
   - Reads enforcement requests from message queue
   - Processes events: SESSION_START, IP_CHANGE, SESSION_END
   - Message visibility timeout management

2. **Policy Enforcement Logic**
   - **SESSION_START**: Create FTD rules for all blocked apps
     - Retrieves policy from database
     - Gets current IP from cache
     - Calls FTD Integration API to create rules
     - Logs enforcement to EnforcementHistory table
     - Saves rule mapping to FTDRuleMapping table

   - **IP_CHANGE**: Update FTD rules with new IP
     - Retrieves existing rules from FTDRuleMapping
     - Calls FTD Integration API to update rules
     - Updates rule mappings with new IP

   - **SESSION_END**: Clean up FTD rules
     - Retrieves all rules for phone number
     - Calls FTD Integration API to delete rules
     - Removes rule mappings from database

3. **Metrics & Analytics**
   - Increments BlockedRequestMetrics counter
   - Tracks enforcement success/failure rates
   - Monitoring metrics publishing

---

### 5. FTD Integration Service

**Technology**: Python 3.11, Flask
**Location**: `/parental-control-backend/services/ftd-integration/`

#### Purpose
Provides REST API for managing Cisco FTD firewall rules.

#### API Endpoints

1. **POST /api/v1/rules/block**
   - Creates firewall rule to block application
   - Request:
     ```json
     {
       "sourceIP": "10.20.30.40",
       "appName": "TikTok",
       "ports": [{"port": 443, "protocol": "TCP"}],
       "msisdn": "+15551234567"
     }
     ```
   - Response:
     ```json
     {
       "ruleId": "rule_12345",
       "ruleName": "PARENTAL_BLOCK_15551234567_TikTok",
       "deviceId": "ftd_device_01",
       "status": "created"
     }
     ```

2. **PUT /api/v1/rules/{ruleId}**
   - Updates rule with new source IP
   - Used during IP handover

3. **DELETE /api/v1/rules/{ruleId}**
   - Deletes firewall rule
   - Used during session end

4. **GET /api/v1/rules/{ruleId}**
   - Verifies rule exists
   - Health check

5. **POST /api/v1/deployment**
   - Deploys policy changes to FTD devices
   - Required after rule modifications

#### FMC API Integration
- Authenticates with Firepower Management Center (FMC)
- Uses REST API for rule management
- Token-based authentication with auto-refresh
- Connection pooling for performance

#### SSH CLI Fallback
- For older FTD versions without API support
- Uses Paramiko for SSH connections
- Executes CLI commands directly
- Parser for command output

---

### 6. Splunk Analytics & Dashboard Platform

**Technology**: Splunk Enterprise
**Purpose**: Centralized analytics, dashboarding, and reporting for all parental control activities

#### Parent Dashboard Features (Splunk Web Interface)

1. **Executive Parent Dashboard**
   - Real-time blocking statistics by child
   - Total blocked attempts today/week/month
   - Top blocked applications across all children
   - Time-based activity patterns
   - Geographic activity maps (if available)

2. **Child-Specific Dashboards**
   - Individual child activity reports
   - App usage trends and patterns
   - Blocking effectiveness metrics
   - Behavioral insights and recommendations

3. **Interactive Reports**
   - Daily blocking summaries (automated emails)
   - Weekly activity reports
   - Monthly compliance and usage reports
   - Custom date range analysis

#### Splunk Dashboard Access Methods

1. **Direct Web Access**
   - Parents access Splunk web interface directly
   - Role-based access control (parents see only their children)
   - Mobile-responsive dashboards
   - Real-time updates and drill-down capabilities

2. **API Integration** 
   - Splunk REST API for embedding dashboards
   - Custom parent portal can embed Splunk visualizations
   - Real-time data feeds via Splunk's Search API
   - Automated report generation and delivery

3. **Data Sources Integration**
   - Direct integration with database for policy information
   - Real-time firewall log ingestion
   - Application service logs and metrics
   - System performance and health data

#### Key Dashboard Components

- **Live Activity Feed**: Real-time blocking attempts
- **Summary Cards**: Today's stats, weekly trends, top apps
- **Interactive Charts**: Time-series blocking patterns
- **Drill-down Reports**: Click to see detailed activity
- **Alert Notifications**: Unusual activity or system issues
- **Export Functions**: PDF reports, CSV data export

---

### 7. IP Lookup Microservice

**Technology**: Python 3.11, Flask
**Location**: `/parental-control-backend/services/ip-lookup/`
**Port**: 8080

#### Purpose
Provides real-time IP address lookup functionality by connecting API Gateway to the in-memory cache. Allows external systems to query current IP addresses using phone numbers.

#### API Endpoints

1. **GET /api/v1/lookup/ip/{phoneNumber}**
   - Retrieves current IP address for a given phone number
   - Request:
     ```
     GET /api/v1/lookup/ip/+15551234567
     ```
   - Response:
     ```json
     {
       "phoneNumber": "+15551234567",
       "privateIP": "10.20.30.40",
       "publicIP": "203.0.113.50",
       "sessionId": "sess_abc123",
       "lastUpdated": "2025-10-16T10:30:00Z",
       "status": "active"
     }
     ```

2. **GET /api/v1/lookup/phone/{ipAddress}**
   - Reverse lookup: Get phone number from IP address
   - Request:
     ```
     GET /api/v1/lookup/phone/10.20.30.40
     ```
   - Response:
     ```json
     {
       "ipAddress": "10.20.30.40",
       "phoneNumber": "+15551234567",
       "imsi": "310150123456789",
       "sessionId": "sess_abc123",
       "lastUpdated": "2025-10-16T10:30:00Z"
     }
     ```

3. **GET /api/v1/lookup/session/{sessionId}**
   - Get complete session information
   - Response includes all mappings (IMSI, phone, IP addresses)

4. **GET /api/v1/lookup/health**
   - Health check endpoint
   - Returns cache connectivity status and performance metrics

#### Key Functions

1. **Cache Integration**
   - Direct connection to in-memory cache (Redis/equivalent)
   - Read-only access for lookup operations
   - Connection pooling for high performance
   - Automatic failover and retry logic

2. **Query Processing**
   - Fast lookup using cache key patterns:
     - `phone:{phoneNumber}` → IP mapping
     - `ip:{ipAddress}` → Phone mapping
     - `imsi:{IMSI}` → Complete session data
   - Sub-millisecond response times
   - Concurrent request handling

3. **Data Validation**
   - Phone number format validation
   - IP address format validation
   - Session data verification
   - Error handling for missing data

4. **Security & Access Control**
   - API key authentication
   - Rate limiting (1000 requests/minute per client)
   - Input sanitization
   - Audit logging of all lookup requests

5. **Monitoring & Metrics**
   - Request/response logging
   - Performance metrics (latency, throughput)
   - Cache hit/miss rates
   - Error rate tracking

#### Use Cases

1. **Network Operations**
   - NOC teams need to identify which child is using specific IP
   - Troubleshooting network connectivity issues
   - Correlating network traffic with user accounts

2. **Support Operations**
   - Customer service needs current IP for support cases
   - Verification of active sessions
   - Real-time troubleshooting

3. **External System Integration**
   - Other systems need real-time IP mappings
   - Integration with network monitoring tools
   - Compliance and audit systems

4. **API Gateway Integration**
   - Enables frontend applications to get real-time IP data
   - Supports parent portal features
   - Third-party application integration

---

### 8. Splunk Integration & Analytics Platform

**Technology**: Splunk Enterprise/Cloud
**Purpose**: Centralized logging, analytics, and final dashboarding for all parental control activities

#### Splunk Data Sources

1. **Cisco FTD Firewall Logs**
   - Real-time syslog ingestion from FTD devices
   - Connection events (allowed/blocked)
   - Policy hit events
   - Security events and alerts
   - Application identification logs

2. **Application Service Logs**
   - Policy Enforcer activity logs
   - FTD Integration API calls
   - Message Consumer processing logs
   - Error and exception logs

3. **System Performance Metrics**
   - Service health metrics
   - Message queue depth
   - Cache performance
   - Database performance

#### Splunk Apps & Dashboards

1. **Parent Executive Dashboard**
   - Real-time blocking statistics
   - Child activity overview
   - Top blocked applications
   - Weekly/monthly trends
   - Geographic activity maps (if available)

2. **IT Operations Dashboard**
   - System health monitoring
   - Performance metrics
   - Error rate tracking
   - Capacity planning metrics
   - Alert management

3. **Compliance & Audit Dashboard**
   - Policy enforcement audit trail
   - Data retention compliance
   - Access control logs
   - Security event tracking

4. **Child Activity Reports**
   - Detailed per-child blocking reports
   - Time-based activity patterns
   - Application usage trends
   - Policy effectiveness metrics

#### Splunk Data Models

1. **Parental_Control_Events**
   - Child phone number
   - Blocked application
   - Timestamp
   - Source IP
   - Action taken
   - Policy rule triggered

2. **Network_Security_Events**
   - FTD firewall events
   - Security threats detected
   - Policy violations
   - System anomalies

3. **System_Performance**
   - Service response times
   - Error rates
   - Resource utilization
   - Capacity metrics

#### Real-time Alerting

1. **Parent Notifications**
   - High-frequency blocking attempts
   - New application usage detected
   - Policy bypass attempts
   - System downtime notifications

2. **IT Operations Alerts**
   - Service failures
   - Performance degradation
   - Security incidents
   - Capacity thresholds exceeded

#### Splunk Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Splunk Platform                                  │
│                                                                           │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │  Parent          │    │  IT Operations   │    │  Compliance      │   │
│  │  Dashboards      │    │  Dashboards      │    │  Reports         │   │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘   │
│           │                       │                       │             │
│           └───────────────────────┼───────────────────────┘             │
│                                   │                                     │
│  ┌────────────────────────────────┼─────────────────────────────────┐   │
│  │              Splunk Search & Analytics Engine                    │   │
│  │  - Real-time data processing                                     │   │
│  │  - Machine learning analytics                                    │   │
│  │  - Custom search queries                                         │   │
│  │  - Automated alerting                                            │   │
│  └────────────────────────────────┼─────────────────────────────────┘   │
│                                   │                                     │
│  ┌────────────────────────────────┼─────────────────────────────────┐   │
│  │              Data Ingestion Layer                                │   │
│  │  - Universal Forwarders                                          │   │
│  │  - Syslog receivers                                              │   │
│  │  - API data collectors                                           │   │
│  │  - File monitoring                                               │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                   ▲
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
   ┌────────▼─────────┐   ┌────────▼─────────┐   ┌───────▼──────────┐
   │  FTD Firewall    │   │  Application     │   │  System          │
   │  Logs (Syslog)   │   │  Service Logs    │   │  Metrics         │
   │  - Block events  │   │  - API calls     │   │  - Performance   │
   │  - Allow events  │   │  - Errors        │   │  - Health        │
   │  - Policy hits   │   │  - Audit trails  │   │  - Capacity      │
   └──────────────────┘   └──────────────────┘   └──────────────────┘
```

---

## Data Flow

### Scenario 1: New Session Establishment

```
1. Child's phone connects to 5G network
   └─> P-Gateway assigns IP: 10.20.30.40

2. P-Gateway publishes message to broker
   └─> Topic: session-data
   └─> Event: SESSION_START

3. Message Consumer consumes event
   └─> Updates Cache:
       - imsi:310150123456789 → {privateIP: 10.20.30.40, ...}
       - phone:+15551234567 → {privateIP: 10.20.30.40, ...}
       - ip:10.20.30.40 → {imsi: 310150123456789, ...}
   └─> Queries Database: ParentalPolicies table
   └─> Policy found for +15551234567
   └─> Sends to Queue: enforcement-requests

4. Policy Enforcer reads queue message
   └─> Retrieves policy from database
       - Child: Sarah
       - Blocked Apps: TikTok, Instagram, Snapchat
   └─> For each blocked app:
       └─> Calls FTD Integration API
           POST /api/v1/rules/block
           {
             "sourceIP": "10.20.30.40",
             "appName": "TikTok",
             "ports": [{"port": 443, "protocol": "TCP"}]
           }
       └─> Saves rule mapping to FTDRuleMapping table
       └─> Logs to EnforcementHistory table
       └─> Increments BlockedRequestMetrics

5. FTD Integration Service
   └─> Calls FMC REST API
   └─> Creates access rule:
       - Name: PARENTAL_BLOCK_15551234567_TikTok
       - Action: BLOCK
       - Source IP: 10.20.30.40
       - Destination Port: 443/TCP
   └─> Deploys policy to FTD device

6. Child tries to access TikTok
   └─> Firewall blocks connection
   └─> FTD logs blocked attempt to Splunk (syslog)
   └─> Splunk processes log in real-time:
       - Updates Parent Dashboard
       - Increments blocking metrics
       - Triggers alerts if needed
   └─> Parent sees in Splunk analytics dashboard
```

**Total Latency**: < 2 seconds from session start to rule active

---

### Scenario 2: IP Address Change (Handover)

```
1. Child moves between cell towers
   └─> P-Gateway reassigns IP: 10.20.30.40 → 10.20.31.50

2. P-Gateway publishes message to broker
   └─> Event: IP_CHANGE
   └─> oldPrivateIP: 10.20.30.40
   └─> newPrivateIP: 10.20.31.50

3. Message Consumer consumes event
   └─> Updates Cache with new IP
   └─> Deletes old keys: ip:10.20.30.40
   └─> Creates new keys: ip:10.20.31.50
   └─> Sends to Queue: IP_CHANGE event

4. Policy Enforcer
   └─> Retrieves existing rules from FTDRuleMapping
   └─> For each rule:
       └─> Calls FTD Integration API
           PUT /api/v1/rules/{ruleId}
           {"newSourceIP": "10.20.31.50"}
       └─> Updates rule mapping with new IP

5. FTD Integration Service
   └─> Updates FMC rule with new source IP
   └─> Deploys changes

6. Protection continues seamlessly with new IP
```

**Total Latency**: < 1 second (rule update faster than creation)

---

### Scenario 3: Parent Updates Policy

```
1. Parent logs into web dashboard
   └─> Navigates to child "Sarah"
   └─> Toggles "Instagram" to BLOCKED

2. Frontend
   └─> Calls API Gateway
       POST /api/policies
       {
         "childPhone": "+15551234567",
         "blockedApps": ["TikTok", "Instagram", "Snapchat"]
       }

3. API Gateway → Database
   └─> Updates ParentalPolicies table
   └─> Database trigger

4. Event Handler
   └─> Reads database change log
   └─> Detects new blocked app: Instagram
   └─> Sends to message queue

5. Policy Enforcer
   └─> Gets current IP from cache
   └─> Creates new FTD rule for Instagram

6. Child tries Instagram
   └─> BLOCKED by firewall
   └─> Metrics incremented
```

---

## Frontend Design

### UI/UX Design Principles

1. **Dark Theme**
   - Background: #0a0a0a
   - Primary accent: #00ff88 (green)
   - Secondary accent: #00aaff (blue)
   - Text: White/Gray scale

2. **Animated Elements**
   - Background gradient animations
   - Smooth transitions on hover
   - Slide-in notifications
   - Toggle switch animations

3. **Responsive Design**
   - Desktop: Grid layout (3-4 columns)
   - Tablet: 2 column grid
   - Mobile: Single column, stacked layout
   - Touch-friendly buttons (48px minimum)

### Page Sections

#### 1. Navigation Header
- Cisco logo
- "AI Family Safety" branding
- Fixed position, transparent blur background

#### 2. Login Section
- Email/password login
- Create account option
- Form validation
- Toggle between forms

#### 3. Child Management
- List of children with cards
- "+ Add Child" button
- Child details: name, age, phone
- "Manage Apps" button per child

#### 4. App Control Dashboard
- Grid of 20 popular apps
- Each app card shows:
  - App icon (emoji)
  - App name
  - Category
  - Toggle switch (green=allowed, red=blocked)
- Visual feedback on state change

---

## Backend Design

### Database Schema

**Note**: Krishnaji will finalize the specific database technology (SQL/NoSQL) during the detailed design phase. The schema below represents the logical data model:

#### 1. ParentalPolicies Table
```
Primary Key: childPhoneNumber (String)
Secondary Key: policyId (String)

Attributes:
- childName: String
- parentEmail: String
- blockedApps: List/Array
  - appName: String
  - ports: List/Array
    - port: Number
    - protocol: String
  - domains: List/Array of Strings
- timeWindows: List/Array
  - startTime: String (HH:MM)
  - endTime: String (HH:MM)
  - days: List/Array of Strings
- status: String (active|inactive)
- createdAt: String (ISO 8601)
- updatedAt: String (ISO 8601)

Indexes:
- Secondary Index: parentEmail (query all children by parent)
```

#### 2. ApplicationRegistry Table
```
Primary Key: appName (String)

Attributes:
- appCategory: String
- defaultPorts: List/Array
- domains: List/Array of Strings
- ipRanges: List/Array of Strings
- description: String
```

#### 3. EnforcementHistory Table
```
Primary Key: childPhoneNumber (String)
Secondary Key: timestamp (String)

Attributes:
- action: String (block|unblock|update)
- appName: String
- privateIP: String
- ruleId: String
- status: String (success|failed)
- errorMessage: String (optional)
- ftdResponse: Object/JSON

TTL: 90 days
```

#### 4. BlockedRequestMetrics Table
```
Primary Key: childPhoneNumber (String)
Secondary Key: dateApp (String) - format: "2025-10-07#TikTok"

Attributes:
- appName: String
- blockedCount: Number
- lastBlockedAt: String
- parentEmail: String

Indexes:
- Secondary Index: parentEmail-dateApp
```

#### 5. FTDRuleMapping Table
```
Primary Key: childPhoneNumber (String)
Secondary Key: ruleId (String)

Attributes:
- ruleName: String
- privateIP: String
- appName: String
- policyId: String
- ftdDeviceId: String
- createdAt: String
- updatedAt: String
```

### Cache Schema

```
Key Pattern: imsi:{IMSI}
Value: {
  "privateIP": "10.20.30.40",
  "publicIP": "203.0.113.50",
  "msisdn": "+15551234567",
  "sessionId": "sess_abc123",
  "timestamp": "2025-10-07T10:30:00Z"
}
TTL: 86400 (24 hours)

Key Pattern: phone:{phoneNumber}
Value: {
  "privateIP": "10.20.30.40",
  "publicIP": "203.0.113.50",
  "imsi": "310150123456789",
  "sessionId": "sess_abc123"
}
TTL: 86400

Key Pattern: ip:{privateIP}
Value: {
  "imsi": "310150123456789",
  "msisdn": "+15551234567",
  "sessionId": "sess_abc123"
}
TTL: 86400
```

---

## Integration Points

### 1. Frontend ↔ Backend
- **Protocol**: HTTPS REST API
- **Authentication**: JWT tokens
- **Endpoints**:
  - POST /api/auth/login
  - POST /api/auth/register
  - GET /api/children
  - POST /api/children
  - GET /api/children/{phone}/policies
  - PUT /api/children/{phone}/policies

### 1a. Parent Dashboard ↔ Splunk
- **Protocol**: HTTPS (Splunk Web Interface) or Splunk REST API
- **Authentication**: Splunk role-based authentication
- **Access Methods**:
  - Direct Splunk web interface access
  - Embedded dashboards via Splunk REST API
  - Real-time search API for custom integrations
- **Port**: 8000 (Splunk Web) / 8089 (Splunk API)
- **Security**: TLS encryption, role-based access control

### 2. P-Gateway ↔ Message Broker
- **Protocol**: Message broker binary protocol
- **Topic**: session-data
- **Partitions**: 6 (for parallelism)
- **Replication**: 3 (high availability)
- **Retention**: 7 days

### 3. Message Consumer ↔ Cache
- **Protocol**: Cache protocol
- **Commands**: SET, GET, DEL, EXPIRE
- **Connection**: Pool of 10 connections
- **Retry**: 3 attempts with exponential backoff

### 4. Policy Enforcer ↔ FTD Integration
- **Protocol**: HTTP REST API
- **Port**: 5000
- **Timeout**: 10 seconds
- **Retry**: 3 attempts

### 5. FTD Integration ↔ Cisco FMC
- **Protocol**: HTTPS REST API
- **Port**: 443
- **Authentication**: Token-based (OAuth2-style)
- **Token Refresh**: Every 30 minutes
- **Rate Limiting**: 120 requests/minute

### 6. Cisco FTD ↔ Splunk
- **Protocol**: Syslog (UDP/TCP/TLS)
- **Port**: 514 (standard) or 6514 (TLS)
- **Format**: CEF (Common Event Format) or Cisco-specific
- **Data Types**: 
  - Access control events (allow/deny)
  - Application events
  - Intrusion events
  - Connection events
- **Retention**: Configurable in Splunk (recommended: 90+ days)
- **Real-time**: < 5 second ingestion latency

### 7. Application Services ↔ Splunk
- **Protocol**: Splunk Universal Forwarder or HTTP Event Collector
- **Authentication**: Token-based for HEC
- **Data Types**:
  - Application logs (JSON format)
  - Performance metrics
  - Error logs
  - Audit trails
- **Indexing**: Separate indexes for different data types

### 8. API Gateway ↔ IP Lookup Microservice
- **Protocol**: HTTP REST API
- **Port**: 8080
- **Timeout**: 5 seconds
- **Authentication**: API key-based
- **Rate Limiting**: 1000 requests/minute per client
- **Data Format**: JSON
- **Response Time**: < 100ms (cache lookup)
- **Availability**: 99.9% uptime requirement

### 9. IP Lookup Microservice ↔ Cache
- **Protocol**: Cache protocol (Redis/equivalent)
- **Commands**: GET (read-only operations)
- **Connection**: Pool of 5 connections
- **Timeout**: 1 second
- **Retry**: 2 attempts with exponential backoff
- **Failover**: Automatic failover to secondary cache
- **Monitoring**: Health checks every 30 seconds

---

## Security Design

### 1. Network Security
- **Network Isolation**: All services in isolated network segments
- **Firewall Rules**: Least privilege access
  - FTD Integration: Only accessible from Policy Enforcer
  - Cache: Only accessible from Message Consumer, Policy Enforcer, and IP Lookup Microservice
  - IP Lookup Microservice: Only accessible from API Gateway
  - Database: Only accessible from application services
- **VPN Access**: For outbound FMC API calls if required

### 2. Data Encryption
- **In-Transit**: TLS 1.3 for all connections
- **At-Rest**:
  - Database: Encryption at rest enabled
  - Cache: Encryption enabled
  - Message Broker: Encryption enabled
  - Log files: Encrypted storage

### 3. Authentication & Authorization
- **Service-to-Service**: Certificate-based or API keys
- **FMC API**: OAuth2 tokens
- **Parent Portal**: JWT tokens
- **Secrets**: Enterprise secrets management
  - FTD credentials
  - Cache password
  - Database connection strings

### 4. Audit & Compliance
- **System Logs**: All API calls logged
- **EnforcementHistory**: Complete audit trail
- **Application Logs**: Retained for 90 days
- **GDPR Compliance**: Data retention policies, right to deletion

---

## Deployment Architecture

### On-Premise Infrastructure

1. **Virtual Machines/Containers**
   - Kubernetes cluster or Docker Swarm
   - 3 master nodes, 6 worker nodes minimum
   - Load balancer for high availability
   - Shared storage for persistent volumes

2. **Message Broker Cluster**
   - 3-node cluster for high availability
   - Instance specs: 8 CPU, 16 GB RAM minimum
   - SSD storage: 500 GB per node
   - Auto-scaling based on queue depth

3. **Cache Cluster**
   - Redis cluster or equivalent
   - 3-node cluster with replication
   - Instance specs: 4 CPU, 32 GB RAM
   - High-speed networking

4. **Database Cluster**
   - Technology TBD by Krishnaji
   - Master-slave or cluster configuration
   - Automated backup and point-in-time recovery
   - High availability setup

5. **Container Services**
   - Services:
     - p-gateway-simulator (2 replicas)
     - message-consumer (2 replicas)
     - policy-enforcer (2 replicas)
     - ftd-integration (2 replicas)
     - ip-lookup-microservice (2 replicas)
   - Auto-scaling: 2-10 replicas based on metrics

5a. **Splunk Platform**
   - Splunk Enterprise cluster (3 nodes minimum)
   - Search heads: 2 nodes for high availability
   - Indexers: 3 nodes with replication factor 2
   - Instance specs: 16 CPU, 64 GB RAM per node
   - Storage: 2 TB per indexer node
   - Parent dashboard hosting and analytics

6. **Message Queue**
   - Queue: enforcement-requests
   - Visibility timeout: 60 seconds
   - Dead-letter queue configured

7. **Secrets Management**
   - Enterprise vault solution
   - ftd-credentials
   - cache-password
   - database-configs

8. **Monitoring**
   - Logs: Centralized logging system
   - Metrics: Custom application metrics
   - Alerts: 15+ alerts configured
   - Dashboard: parental-control-main

### Local Development

**Docker Compose Services**:
- Zookeeper
- Message Broker
- Cache
- Database Local
- Message Broker UI (http://localhost:8080)
- Cache Admin UI (http://localhost:8081)
- Database Admin UI (http://localhost:8001)

**Quick Start**:
```bash
cd deployment/docker
docker-compose up -d
```

---

## Use Cases & Scenarios

### Use Case 1: First-Time Setup

**Actors**: Parent, System

**Preconditions**: None

**Flow**:
1. Parent visits parental control website (internal network)
2. Creates account with email/password
3. Adds first child (name, age, phone number)
4. Views app control dashboard
5. Toggles apps to BLOCKED (e.g., TikTok, Instagram)
6. System saves policy to on-premise database
7. When child's phone connects to network:
   - P-Gateway detects session
   - Message Consumer checks policy
   - Policy Enforcer creates FTD rules
   - Apps immediately blocked

**Success Criteria**: Apps blocked within 2 seconds of network connection

---

### Use Case 2: Daily Usage - Child Attempts Access

**Actors**: Child, System, Parent

**Preconditions**:
- Child has active policy
- Child's device connected to network

**Flow**:
1. Child opens TikTok app at 9:00 PM
2. App attempts to connect to tiktok.com:443
3. Request hits Cisco FTD firewall
4. FTD checks rule: PARENTAL_BLOCK_{phone}_TikTok
5. Rule matches: Source IP = child's IP, Dest Port = 443
6. FTD blocks connection
7. System increments BlockedRequestMetrics counter
8. Parent sees in dashboard: "TikTok: 1 block today"

**Success Criteria**:
- App cannot connect
- Metric updated in real-time
- Parent can view in dashboard

---

### Use Case 3: IP Change During Active Session

**Actors**: Child, System

**Preconditions**:
- Child has active session
- Policy enforcement active

**Flow**:
1. Child is on subway, phone switches cell towers
2. P-Gateway detects handover
3. Old IP: 10.20.30.40 → New IP: 10.20.31.50
4. P-Gateway publishes IP_CHANGE event
5. Message Consumer updates cache
6. Policy Enforcer:
   - Retrieves all active rules for child
   - Updates each FTD rule with new IP
7. Protection continues without interruption

**Success Criteria**:
- Zero downtime in protection
- Update completes in < 1 second
- Child's apps remain blocked

---

### Use Case 4: Parent Views Weekly Report

**Actors**: Parent, System

**Preconditions**:
- Parent logged in
- At least 7 days of data

**Flow**:
1. Parent navigates to Analytics page
2. System queries BlockedRequestMetrics table
3. Aggregates data for past 7 days
4. Returns:
   - Total blocks: 312
   - By app: TikTok (62%), Instagram (31%), Other (7%)
   - By day: Chart showing daily trend
   - By hour: Peak blocking times (8-9 AM, 9-10 PM)
5. Parent sees value: "Your policy is working!"

**Success Criteria**:
- Report loads in < 2 seconds
- Data accurate
- Charts visually appealing

---

### Use Case 5: Real-time IP Lookup for Support

**Actors**: Support Team, System

**Preconditions**:
- Child has active session
- Support team has API access

**Flow**:
1. Parent calls support: "My child Sarah can't access her allowed apps"
2. Support agent asks for child's phone number: "+15551234567"
3. Support agent queries IP Lookup API:
   ```
   GET /api/v1/lookup/ip/+15551234567
   ```
4. System responds with current session information:
   ```json
   {
     "phoneNumber": "+15551234567",
     "privateIP": "10.20.30.40",
     "publicIP": "203.0.113.50",
     "sessionId": "sess_abc123",
     "lastUpdated": "2025-10-16T14:30:00Z",
     "status": "active"
   }
   ```
5. Support agent verifies IP is active and troubleshoots network connectivity
6. Issue resolved: Child's device was temporarily disconnected

**Success Criteria**:
- API responds in < 100ms
- Real-time session data available
- Support team can quickly identify network issues

---

## Performance Requirements

| Metric | Target | Notes |
|--------|--------|-------|
| Policy Enforcement Latency | < 2 seconds | From session start to FTD rule active |
| IP Change Update Latency | < 1 second | Rule update faster than create |
| Message Throughput | 10,000 msg/sec | Handles 10K concurrent sessions/sec |
| Cache Operations | 100,000 ops/sec | Sub-millisecond lookups |
| Database RCU/WCU | 5,000 operations/sec | Auto-scaling or provisioned |
| FTD Rule Creation | < 500ms | Per rule via FMC API |
| IP Lookup API Response | < 100ms | Phone number to IP lookup |
| IP Lookup Throughput | 1,000 req/sec | Concurrent API requests |
| System Availability | 99.9% | Multi-node, auto-failover |
| Dashboard Load Time | < 2 seconds | Analytics API response |

---

## Scalability

### Horizontal Scaling

1. **Message Consumers**: Scale to 6 instances (1 per partition)
2. **Policy Enforcers**: Scale to 10 instances based on queue depth
3. **FTD Integration**: Scale to 5 instances based on request rate
4. **IP Lookup Microservice**: Scale to 5 instances based on API request rate
5. **Splunk Platform**: Scale indexers and search heads based on data volume and user load

### Vertical Scaling

1. **Cache**: Upgrade memory and CPU as needed
2. **Message Broker**: Upgrade to higher specs
3. **Database**: Increase provisioned capacity or upgrade hardware

### Geographic Scaling

- **Multi-Site**: Deploy to multiple data centers
- **Cross-Site Replication**: Database replication across sites
- **Load Balancing**: Geographic load balancing for lowest latency

---

## Monitoring & Observability

### Splunk-Based Monitoring & Alerting

1. **Real-time Splunk Alerts**
   - **Message Consumer Lag > 1000**: Critical
   - **Cache Memory > 80%**: Warning
   - **Policy Enforcement Failures > 5% in 5 min**: Critical
   - **FTD API Errors > 10% in 5 min**: Warning
   - **Container/Service Failures**: Critical
   - **Database Performance Degradation**: Warning
   - **Unusual Child Activity Patterns**: Information
   - **High-Frequency App Blocking**: Warning

2. **Splunk Executive Dashboards**
   - **Parent Summary Dashboard**: 
     - Total children monitored
     - Apps blocked today/week/month
     - Top blocked applications
     - Peak activity times
     - Policy effectiveness metrics
   
   - **Child Activity Dashboard**:
     - Per-child blocking statistics
     - Application usage trends
     - Time-based activity patterns
     - Behavioral insights

3. **Splunk IT Operations Dashboard**
   - **System Health Overview**:
     - Active sessions (real-time)
     - Message broker lag (gauge)
     - Cache hit rate (percentage)
     - Policy enforcement rate (line chart)
     - FTD API latency (histogram)
     - Service response times
   
   - **Performance Metrics**:
     - Resource utilization
     - Error rates by service
     - Throughput metrics
     - Capacity planning indicators

4. **Splunk Security & Compliance Dashboard**
   - **Audit Trail Visualization**:
     - Policy changes timeline
     - Administrative actions
     - System access logs
     - Data retention compliance
   
   - **Security Events**:
     - Failed authentication attempts
     - Unusual access patterns
     - System vulnerabilities
     - Threat indicators

### Splunk Search Queries & Reports

1. **Real-time Searches**:
   ```splunk
   index=parental_control sourcetype=ftd_firewall action=blocked
   | stats count by child_phone, app_name
   | sort -count
   ```

2. **Scheduled Reports**:
   - Daily blocking summary (sent to parents)
   - Weekly system health report (sent to IT)
   - Monthly compliance report (sent to management)
   - Quarterly capacity planning report

3. **Machine Learning Analytics**:
   - Anomaly detection for unusual blocking patterns
   - Predictive analytics for capacity planning
   - Behavioral analysis for optimization

### Legacy Monitoring Integration

- **Application Logs**: Forwarded to Splunk via Universal Forwarders
- **System Metrics**: Collected via Splunk Add-ons
- **Database Logs**: Integrated through Splunk DB Connect
- **Network Logs**: Ingested via syslog from network devices

---

## Cost Estimate (Monthly - On-Premise Hardware)

| Component | Configuration | Estimated Cost (₹) |
|-----------|--------------|-------------------|
| Servers (6 nodes) | 32 vCPU, 64 GB RAM each | 2,50,000 (amortized) |
| Storage | 10 TB SSD | 50,000 |
| Networking | Switches, Load Balancers | 25,000 |
| Software Licenses | Database, Monitoring | 75,000 |
| Splunk Enterprise | 500 GB/day ingestion | Included (No additional cost) |
| Splunk Apps & Add-ons | Security, Network, Custom | Included (No additional cost) |
| Power & Cooling | Data center costs | 30,000 |
| Support & Maintenance | 24x7 support | 40,000 |
| **Total** | | **₹4,70,000** |

**Note**: 
- Initial setup costs higher, operational costs lower over time
- Splunk licensing and apps are included in the enterprise infrastructure at no additional cost
- Splunk provides significant ROI through improved visibility and faster incident resolution

---

## Future Enhancements

### Phase 1: Advanced Features (Q1 2026)
- [ ] Time-based restrictions (bedtime mode)
- [ ] Geofencing (location-based rules)
- [ ] Content filtering (not just app blocking)
- [ ] Screen time limits

### Phase 2: AI/ML Integration (Q2 2026)
- [ ] Anomaly detection (unusual app usage)
- [ ] Predictive blocking (AI suggests apps to block)
- [ ] Sentiment analysis (monitor social media posts)
- [ ] Risk scoring for apps

### Phase 3: Mobile Apps (Q3 2026)
- [ ] iOS app for parents
- [ ] Android app for parents
- [ ] Push notifications
- [ ] Real-time alerts

### Phase 4: Enterprise Features (Q4 2026)
- [ ] Multi-parent accounts
- [ ] School integration
- [ ] Teacher dashboards
- [ ] Bulk management (IT admins)

---

## Conclusion

The Cisco AI Family Safety Parental Control Solution (On-Premise) provides a comprehensive, scalable, and secure platform for parents to manage their children's digital safety within enterprise boundaries. By integrating network-level enforcement with an intuitive web interface, the system delivers real value through:

1. **Real-time Protection**: Apps blocked instantly at network level
2. **Data Sovereignty**: All data remains within enterprise control
3. **Transparency**: Parents see exactly what's being blocked
4. **Flexibility**: Easily adjust policies as children grow
5. **Reliability**: 99.9% uptime with multi-node deployment
6. **Scalability**: Handles millions of concurrent users
7. **Compliance**: Meets stringent data privacy requirements

**Technology Decisions**: The specific database technology and message broker will be finalized by Krishnaji during the detailed design phase based on enterprise requirements, performance needs, and existing infrastructure.

**Status**: Design-ready, awaiting detailed technology selection and implementation.

---

**Document Version**: 1.0 (On-Premise)
**Last Updated**: 2025-10-16
**Authors**: Cisco AI Family Safety Team
**Technology Lead**: Krishnaji (Database & Infrastructure Selection)
**Review Status**: Approved for Detailed Design Phase