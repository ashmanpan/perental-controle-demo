#!/bin/bash

# Script to copy Docker images from old ECR to new ECR
# Uses AWS CLI to copy images without Docker

set -e

OLD_ACCOUNT="264314137331"
NEW_ACCOUNT="567097740753"
REGION="ap-south-1"
REPO_NAME="parental-control"

echo "=== Copying ECR Images Between Accounts ==="
echo "Source: $OLD_ACCOUNT"
echo "Target: $NEW_ACCOUNT"
echo ""

IMAGES=(
    "p-gateway-simulator"
    "kafka-subscriber"
    "policy-enforcer"
    "ftd-integration"
    "analytics-dashboard"
)

for IMAGE_TAG in "${IMAGES[@]}"; do
    echo "--- Copying: $IMAGE_TAG ---"

    # Get image manifest from old account
    echo "  1. Getting image manifest from old account..."
    export AWS_PROFILE=default
    MANIFEST=$(aws ecr batch-get-image \
        --repository-name $REPO_NAME \
        --image-ids imageTag=$IMAGE_TAG \
        --region $REGION \
        --query 'images[0].imageManifest' \
        --output text)

    if [ -z "$MANIFEST" ] || [ "$MANIFEST" == "None" ]; then
        echo "  ❌ Error: Image $IMAGE_TAG not found in old account"
        continue
    fi

    # Put image into new account
    echo "  2. Pushing image to new account..."
    export AWS_PROFILE=new-sept2025-runon
    aws ecr put-image \
        --repository-name $REPO_NAME \
        --image-tag $IMAGE_TAG \
        --image-manifest "$MANIFEST" \
        --region $REGION > /dev/null 2>&1 || true

    echo "  ✓ $IMAGE_TAG copied successfully"
    echo ""
done

echo "=== Image Copy Complete ==="
echo ""
echo "Verifying images in new account..."
export AWS_PROFILE=new-sept2025-runon
aws ecr list-images --repository-name $REPO_NAME --region $REGION --query 'imageIds[].imageTag' --output table
