#!/bin/bash

# Script to delete pc-prod VPC and all its dependencies
# Run this script after NAT Gateways finish deleting (takes ~5 minutes)

set -e

VPC_ID="vpc-01c0dbaf4ba865d8a"
REGION="ap-south-1"

echo "=== Starting VPC Deletion Process ==="
echo "VPC ID: $VPC_ID"
echo "Region: $REGION"
echo ""

# Wait for NAT Gateways to be deleted
echo "Step 1: Waiting for NAT Gateways to be deleted..."
while true; do
    NAT_COUNT=$(aws ec2 describe-nat-gateways --region $REGION \
        --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=pending,available,deleting" \
        --query 'NatGateways[].NatGatewayId' --output text | wc -w)

    if [ "$NAT_COUNT" -eq 0 ]; then
        echo "✓ All NAT Gateways deleted"
        break
    fi
    echo "  Waiting... ($NAT_COUNT NAT Gateways still deleting)"
    sleep 30
done

# Release Elastic IPs
echo ""
echo "Step 2: Releasing Elastic IPs..."
EIP_IDS=$(aws ec2 describe-addresses --region $REGION \
    --filters "Name=domain,Values=vpc" \
    --query "Addresses[?contains(Tags[?Key=='Name'].Value | [0], 'pc-prod')].AllocationId" --output text)

if [ -n "$EIP_IDS" ]; then
    for eip in $EIP_IDS; do
        echo "  Releasing EIP: $eip"
        aws ec2 release-address --allocation-id $eip --region $REGION || true
    done
    echo "✓ Elastic IPs released"
else
    echo "  No Elastic IPs found"
fi

# Detach and delete Internet Gateway
echo ""
echo "Step 3: Deleting Internet Gateways..."
IGW_IDS=$(aws ec2 describe-internet-gateways --region $REGION \
    --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
    --query 'InternetGateways[].InternetGatewayId' --output text)

if [ -n "$IGW_IDS" ]; then
    for igw in $IGW_IDS; do
        echo "  Detaching IGW: $igw"
        aws ec2 detach-internet-gateway --internet-gateway-id $igw --vpc-id $VPC_ID --region $REGION || true
        echo "  Deleting IGW: $igw"
        aws ec2 delete-internet-gateway --internet-gateway-id $igw --region $REGION || true
    done
    echo "✓ Internet Gateways deleted"
else
    echo "  No Internet Gateways found"
fi

# Delete Subnets
echo ""
echo "Step 4: Deleting Subnets..."
SUBNET_IDS=$(aws ec2 describe-subnets --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[].SubnetId' --output text)

if [ -n "$SUBNET_IDS" ]; then
    for subnet in $SUBNET_IDS; do
        echo "  Deleting Subnet: $subnet"
        aws ec2 delete-subnet --subnet-id $subnet --region $REGION || true
    done
    echo "✓ Subnets deleted"
else
    echo "  No Subnets found"
fi

# Delete Route Tables (except main)
echo ""
echo "Step 5: Deleting Route Tables..."
RT_IDS=$(aws ec2 describe-route-tables --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'RouteTables[?Associations[0].Main != `true`].RouteTableId' --output text)

if [ -n "$RT_IDS" ]; then
    for rt in $RT_IDS; do
        echo "  Deleting Route Table: $rt"
        aws ec2 delete-route-table --route-table-id $rt --region $REGION || true
    done
    echo "✓ Route Tables deleted"
else
    echo "  No custom Route Tables found"
fi

# Delete Security Groups (except default)
echo ""
echo "Step 6: Deleting Security Groups..."
SG_IDS=$(aws ec2 describe-security-groups --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[?GroupName != `default`].GroupId' --output text)

if [ -n "$SG_IDS" ]; then
    for sg in $SG_IDS; do
        echo "  Deleting Security Group: $sg"
        aws ec2 delete-security-group --group-id $sg --region $REGION || true
    done
    echo "✓ Security Groups deleted"
else
    echo "  No custom Security Groups found"
fi

# Delete VPC
echo ""
echo "Step 7: Deleting VPC..."
aws ec2 delete-vpc --vpc-id $VPC_ID --region $REGION
echo "✓ VPC deleted successfully!"

echo ""
echo "=== VPC Deletion Complete ==="
