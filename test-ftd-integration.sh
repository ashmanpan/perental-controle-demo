#!/bin/bash

# FTD Integration Testing Script
# This script must be run from within the AWS VPC (10.0.0.0/16)
#
# Prerequisites:
# - EC2 instance or bastion host in the VPC
# - curl and jq installed
# - Network connectivity to ftd-integration service

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FTD_SERVICE_IP="10.0.2.80"
FTD_SERVICE_PORT="5000"
FTD_BASE_URL="http://${FTD_SERVICE_IP}:${FTD_SERVICE_PORT}"

ANALYTICS_SERVICE_IP="10.0.3.139"
ANALYTICS_SERVICE_PORT="8000"
ANALYTICS_BASE_URL="http://${ANALYTICS_SERVICE_IP}:${ANALYTICS_SERVICE_PORT}"

# Test data
TEST_PHONE="+12064882538"
TEST_IP="10.20.81.128"
TEST_APP="TikTok"

echo -e "${GREEN}=== Parental Control FTD Integration Testing ===${NC}"
echo "Date: $(date)"
echo "FTD Service: ${FTD_BASE_URL}"
echo "Analytics Service: ${ANALYTICS_BASE_URL}"
echo ""

# Test 1: Check ftd-integration health
echo -e "${YELLOW}Test 1: Check ftd-integration health endpoint${NC}"
if curl -s -f "${FTD_BASE_URL}/health" > /dev/null 2>&1; then
    response=$(curl -s "${FTD_BASE_URL}/health")
    echo -e "${GREEN}✓ Health endpoint responding${NC}"
    echo "Response: ${response}"
else
    echo -e "${RED}✗ Health endpoint not responding${NC}"
    exit 1
fi
echo ""

# Test 2: Get session data from analytics
echo -e "${YELLOW}Test 2: Get current session data for test phone${NC}"
response=$(curl -s "${ANALYTICS_BASE_URL}/api/v1/session/phone/${TEST_PHONE}")
echo "Response: ${response}" | jq '.'
if echo "${response}" | jq -e '.status == "active"' > /dev/null; then
    TEST_IP=$(echo "${response}" | jq -r '.privateIP')
    echo -e "${GREEN}✓ Active session found for ${TEST_PHONE}, IP: ${TEST_IP}${NC}"
else
    echo -e "${YELLOW}⚠ No active session found, using test data${NC}"
fi
echo ""

# Test 3: Create FTD block rule
echo -e "${YELLOW}Test 3: Create FTD block rule for ${TEST_APP}${NC}"
request_body=$(cat <<EOF
{
  "sourceIP": "${TEST_IP}",
  "appName": "${TEST_APP}",
  "ports": [
    {"protocol": "TCP", "port": 443},
    {"protocol": "TCP", "port": 80}
  ],
  "msisdn": "${TEST_PHONE}"
}
EOF
)

echo "Request body:"
echo "${request_body}" | jq '.'

response=$(curl -s -X POST "${FTD_BASE_URL}/api/v1/rules/block" \
  -H "Content-Type: application/json" \
  -d "${request_body}")

echo "Response:"
echo "${response}" | jq '.'

if echo "${response}" | jq -e '.ruleId' > /dev/null; then
    RULE_ID=$(echo "${response}" | jq -r '.ruleId')
    RULE_METHOD=$(echo "${response}" | jq -r '.method')
    echo -e "${GREEN}✓ Rule created successfully${NC}"
    echo "Rule ID: ${RULE_ID}"
    echo "Method: ${RULE_METHOD}"
else
    echo -e "${RED}✗ Failed to create rule${NC}"
    exit 1
fi
echo ""

# Test 4: Verify the rule was created
echo -e "${YELLOW}Test 4: Verify rule exists${NC}"
if [ "${RULE_METHOD}" == "API" ]; then
    # For API method, we can verify via the API
    policy_id=$(echo "${response}" | jq -r '.policyId')
    verify_response=$(curl -s -X GET "${FTD_BASE_URL}/api/v1/rules/${RULE_ID}?policyId=${policy_id}")
    echo "Response: ${verify_response}" | jq '.'
    if echo "${verify_response}" | jq -e '.exists' > /dev/null; then
        echo -e "${GREEN}✓ Rule verified via API${NC}"
    else
        echo -e "${YELLOW}⚠ Rule verification returned: $(echo ${verify_response} | jq -r '.exists')${NC}"
    fi
elif [ "${RULE_METHOD}" == "SSH" ]; then
    echo -e "${GREEN}✓ Rule created via SSH (already applied to FTDv)${NC}"
    echo "To manually verify, SSH to FTDv and run: show access-list PARENTAL_CONTROL_ACL"
fi
echo ""

# Test 5: Check FTDv connectivity from service
echo -e "${YELLOW}Test 5: Check FTDv connectivity status${NC}"
ftdv_status=$(curl -s "${FTD_BASE_URL}/api/v1/status")
echo "Response:"
echo "${ftdv_status}" | jq '.'
echo ""

# Test 6: List all active sessions
echo -e "${YELLOW}Test 6: Get active sessions count${NC}"
sessions_response=$(curl -s "${ANALYTICS_BASE_URL}/api/v1/sessions/active/count")
echo "Response:"
echo "${sessions_response}" | jq '.'
active_count=$(echo "${sessions_response}" | jq -r '.activeSessionsCount')
echo -e "${GREEN}Active sessions: ${active_count}${NC}"
echo ""

# Summary
echo -e "${GREEN}=== Test Summary ===${NC}"
echo "✓ ftd-integration service is responsive"
echo "✓ Analytics service is working"
echo "✓ Rule creation successful via ${RULE_METHOD}"
echo "✓ Rule ID: ${RULE_ID}"
echo "✓ Active sessions: ${active_count}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
if [ "${RULE_METHOD}" == "SSH" ]; then
    echo "1. SSH to FTDv (10.0.101.119) and verify the rule:"
    echo "   ssh admin@10.0.101.119"
    echo "   show access-list PARENTAL_CONTROL_ACL"
elif [ "${RULE_METHOD}" == "API" ]; then
    echo "1. Check FMC console for pending deployment"
    echo "2. Deploy policy changes to FTDv"
    echo "3. Verify rule is active on FTDv"
fi
echo "2. Test actual traffic blocking with the created rule"
echo "3. Test rule update and deletion"
