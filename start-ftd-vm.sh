#!/bin/bash

# Script to start FTDv EC2 instance
# This script starts the Cisco FTDv firewall VM when needed

set -e

REGION="ap-south-1"
AWS_PROFILE="new-sept2025-runon"

echo "=== FTDv EC2 Instance Startup Script ==="
echo "Region: $REGION"
echo "AWS Profile: $AWS_PROFILE"
echo ""

# Export AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Find FTDv instance by tag
echo "Step 1: Finding FTDv EC2 instance..."
INSTANCE_ID=$(aws ec2 describe-instances --region $REGION \
    --filters "Name=tag:Name,Values=pc-prod-ftdv" "Name=instance-state-name,Values=stopped,running" \
    --query 'Reservations[0].Instances[0].InstanceId' --output text)

if [ "$INSTANCE_ID" == "None" ] || [ -z "$INSTANCE_ID" ]; then
    echo "❌ Error: FTDv instance not found"
    echo "   Make sure the instance is deployed with tag Name=pc-prod-ftdv"
    exit 1
fi

echo "✓ Found FTDv instance: $INSTANCE_ID"

# Check current state
echo ""
echo "Step 2: Checking current instance state..."
CURRENT_STATE=$(aws ec2 describe-instances --region $REGION \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].State.Name' --output text)

echo "  Current state: $CURRENT_STATE"

if [ "$CURRENT_STATE" == "running" ]; then
    echo "✓ Instance is already running"

    # Get instance details
    PUBLIC_IP=$(aws ec2 describe-instances --region $REGION \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

    PRIVATE_IP=$(aws ec2 describe-instances --region $REGION \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)

    echo ""
    echo "=== FTDv Instance Details ==="
    echo "Instance ID: $INSTANCE_ID"
    echo "State: $CURRENT_STATE"
    echo "Public IP: $PUBLIC_IP"
    echo "Private IP: $PRIVATE_IP"
    echo ""
    echo "Management Access:"
    echo "  HTTPS: https://$PUBLIC_IP"
    echo "  SSH:   ssh admin@$PUBLIC_IP"
    echo ""
    exit 0
fi

# Start the instance
echo ""
echo "Step 3: Starting FTDv instance..."
aws ec2 start-instances --region $REGION --instance-ids $INSTANCE_ID > /dev/null
echo "✓ Start command sent"

# Wait for instance to be running
echo ""
echo "Step 4: Waiting for instance to start (this may take 2-3 minutes)..."
aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID

echo "✓ Instance is now running"

# Wait additional time for FTDv to boot up
echo ""
echo "Step 5: Waiting for FTDv services to initialize (30 seconds)..."
sleep 30
echo "✓ FTDv should be ready"

# Get instance details
PUBLIC_IP=$(aws ec2 describe-instances --region $REGION \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

PRIVATE_IP=$(aws ec2 describe-instances --region $REGION \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)

echo ""
echo "=== FTDv Instance Started Successfully ==="
echo "Instance ID: $INSTANCE_ID"
echo "State: running"
echo "Public IP: $PUBLIC_IP"
echo "Private IP: $PRIVATE_IP"
echo ""
echo "Management Access:"
echo "  HTTPS: https://$PUBLIC_IP"
echo "  SSH:   ssh admin@$PUBLIC_IP"
echo ""
echo "Default Credentials:"
echo "  Username: admin"
echo "  Password: Admin123!"
echo ""
echo "Note: It may take an additional 2-3 minutes for FTDv web interface to be fully responsive"
echo ""
echo "=== Cost Information ==="
echo "Instance Type: c5.xlarge"
echo "Hourly Cost: ~$0.21/hour"
echo "Daily Cost (if left running): ~$5.04/day"
echo ""
echo "Remember to run ./stop-ftd-vm.sh when done to save costs!"
echo ""
