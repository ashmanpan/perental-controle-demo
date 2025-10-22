#!/bin/bash

# Script to stop FTDv EC2 instance
# This script stops the Cisco FTDv firewall VM to save costs when not in use

set -e

REGION="ap-south-1"
AWS_PROFILE="new-sept2025-runon"

echo "=== FTDv EC2 Instance Shutdown Script ==="
echo "Region: $REGION"
echo "AWS Profile: $AWS_PROFILE"
echo ""

# Export AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Find FTDv instance by tag
echo "Step 1: Finding FTDv EC2 instance..."
INSTANCE_ID=$(aws ec2 describe-instances --region $REGION \
    --filters "Name=tag:Name,Values=pc-prod-ftdv" "Name=instance-state-name,Values=running,stopped" \
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

if [ "$CURRENT_STATE" == "stopped" ]; then
    echo "✓ Instance is already stopped"
    echo ""
    echo "=== FTDv Instance Details ==="
    echo "Instance ID: $INSTANCE_ID"
    echo "State: $CURRENT_STATE"
    echo ""
    echo "To start the instance, run: ./start-ftd-vm.sh"
    echo ""
    exit 0
fi

if [ "$CURRENT_STATE" != "running" ]; then
    echo "⚠ Warning: Instance is in $CURRENT_STATE state"
    echo "  Cannot stop instance that is not running"
    exit 1
fi

# Get instance details before stopping
PUBLIC_IP=$(aws ec2 describe-instances --region $REGION \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

PRIVATE_IP=$(aws ec2 describe-instances --region $REGION \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)

# Confirmation prompt
echo ""
echo "=== Confirm Shutdown ==="
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "Private IP: $PRIVATE_IP"
echo ""
read -p "Are you sure you want to stop this FTDv instance? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo ""
    echo "Shutdown cancelled"
    exit 0
fi

# Stop the instance
echo ""
echo "Step 3: Stopping FTDv instance..."
aws ec2 stop-instances --region $REGION --instance-ids $INSTANCE_ID > /dev/null
echo "✓ Stop command sent"

# Wait for instance to be stopped
echo ""
echo "Step 4: Waiting for instance to stop (this may take 1-2 minutes)..."
aws ec2 wait instance-stopped --region $REGION --instance-ids $INSTANCE_ID

echo "✓ Instance is now stopped"

echo ""
echo "=== FTDv Instance Stopped Successfully ==="
echo "Instance ID: $INSTANCE_ID"
echo "State: stopped"
echo ""
echo "=== Cost Savings ==="
echo "You are no longer being charged for instance hours (~$0.21/hour)"
echo "You will still be charged for:"
echo "  - EBS storage (~$0.10/GB/month)"
echo "  - Elastic IP (if attached and instance stopped: ~$0.005/hour)"
echo ""
echo "Estimated savings: ~$150/month when stopped"
echo ""
echo "To start the instance again, run: ./start-ftd-vm.sh"
echo ""
