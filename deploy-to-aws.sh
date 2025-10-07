#!/bin/bash

#########################################
# Full AWS Deployment Script (CloudFormation)
# Cisco AI Family Safety - Parental Control
#########################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="parental-control-prod"
TEMPLATE_FILE="parental-control-backend/infrastructure/cloudformation/infrastructure.yaml"
PARAMETERS_FILE="parental-control-backend/infrastructure/cloudformation/parameters.json"
REGION="ap-south-1"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not installed"
        exit 1
    fi
    print_success "AWS CLI installed"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not installed"
        exit 1
    fi
    print_success "Docker installed"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured"
        exit 1
    fi
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_success "AWS credentials configured (Account: $ACCOUNT_ID, Region: $REGION)"
}

# Validate CloudFormation template
validate_template() {
    print_header "Validating CloudFormation Template"

    print_info "Validating template syntax..."
    aws cloudformation validate-template \
        --template-body file://$TEMPLATE_FILE \
        --region $REGION \
        --no-cli-pager > /dev/null

    print_success "Template validation successful"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_header "Deploying Infrastructure with CloudFormation"

    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION &> /dev/null; then
        print_info "Stack exists. Updating stack..."
        OPERATION="update"
    else
        print_info "Stack does not exist. Creating new stack..."
        OPERATION="create"
    fi

    # Confirm
    echo ""
    print_warning "This will create ~₹1,13,000/month (~\$1,350/month) in AWS resources"
    read -p "Continue with deployment? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        print_error "Deployment cancelled"
        exit 0
    fi

    # Deploy
    if [ "$OPERATION" == "create" ]; then
        print_info "Creating CloudFormation stack (this will take 45-60 minutes)..."
        aws cloudformation create-stack \
            --stack-name $STACK_NAME \
            --template-body file://$TEMPLATE_FILE \
            --parameters file://$PARAMETERS_FILE \
            --capabilities CAPABILITY_NAMED_IAM \
            --region $REGION \
            --no-cli-pager

        print_info "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete \
            --stack-name $STACK_NAME \
            --region $REGION
    else
        print_info "Updating CloudFormation stack..."
        aws cloudformation update-stack \
            --stack-name $STACK_NAME \
            --template-body file://$TEMPLATE_FILE \
            --parameters file://$PARAMETERS_FILE \
            --capabilities CAPABILITY_NAMED_IAM \
            --region $REGION \
            --no-cli-pager || true

        print_info "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete \
            --stack-name $STACK_NAME \
            --region $REGION || true
    fi

    # Get outputs
    print_info "Retrieving stack outputs..."
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs' \
        --output table > deployment-outputs.txt

    print_success "Infrastructure deployed! Outputs saved to deployment-outputs.txt"
}

# Get stack outputs
get_output() {
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
        --output text
}

# Build and push Docker images
build_and_push_images() {
    print_header "Building and Pushing Docker Images"

    # Get ECR URLs from CloudFormation outputs
    ECR_P_GATEWAY=$(get_output "PGatewayECRUrl")
    ECR_KAFKA=$(get_output "KafkaSubscriberECRUrl")
    ECR_ENFORCER=$(get_output "PolicyEnforcerECRUrl")
    ECR_FTD=$(get_output "FTDIntegrationECRUrl")
    ECR_ANALYTICS=$(get_output "AnalyticsDashboardECRUrl")

    # Login to ECR
    print_info "Logging into ECR..."
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    print_success "Logged into ECR"

    # Build and push each service
    declare -A services=(
        ["p-gateway-simulator"]="$ECR_P_GATEWAY"
        ["kafka-subscriber"]="$ECR_KAFKA"
        ["policy-enforcer"]="$ECR_ENFORCER"
        ["ftd-integration"]="$ECR_FTD"
        ["analytics-dashboard"]="$ECR_ANALYTICS"
    )

    for service in "${!services[@]}"; do
        ecr_url="${services[$service]}"

        print_info "Building $service..."
        cd parental-control-backend/services/$service
        docker build -t $ecr_url:latest . --no-cache

        print_info "Pushing $service to ECR..."
        docker push $ecr_url:latest
        print_success "$service image pushed"

        cd ../../..
    done
}

# Update ECS services
update_ecs_services() {
    print_header "Updating ECS Services"

    CLUSTER_NAME=$(get_output "ECSClusterName")

    services=("p-gateway" "kafka-subscriber" "policy-enforcer" "ftd-integration" "analytics-dashboard")

    for service in "${services[@]}"; do
        print_info "Updating $service service..."
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service pc-prod-$service-service \
            --force-new-deployment \
            --region $REGION \
            --no-cli-pager > /dev/null
        print_success "$service service updated"
    done

    print_info "Waiting for services to stabilize (this may take 5-10 minutes)..."
    for service in "${services[@]}"; do
        aws ecs wait services-stable \
            --cluster $CLUSTER_NAME \
            --services pc-prod-$service-service \
            --region $REGION
    done
    print_success "All ECS services are running"
}

# Deploy frontend to Amplify
deploy_frontend() {
    print_header "Deploying Frontend to AWS Amplify"

    # Check if Amplify CLI is installed
    if ! command -v amplify &> /dev/null; then
        print_warning "Amplify CLI not installed. Installing..."
        npm install -g @aws-amplify/cli
    fi

    cd frontend

    # Initialize Amplify (if not already initialized)
    if [ ! -d "amplify" ]; then
        print_info "Initializing Amplify project..."
        amplify init --yes
    fi

    # Add hosting if not already added
    if ! amplify status | grep -q "Hosting"; then
        print_info "Adding Amplify hosting..."
        amplify add hosting
    fi

    # Publish
    print_info "Publishing frontend to Amplify..."
    amplify publish --yes

    print_success "Frontend deployed to Amplify"

    cd ..
}

# Verification
verify_deployment() {
    print_header "Verifying Deployment"

    CLUSTER_NAME=$(get_output "ECSClusterName")

    # Check ECS services
    print_info "Checking ECS services..."
    aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services pc-prod-p-gateway-service \
        --region $REGION \
        --query 'services[0].{Name:serviceName,Running:runningCount,Desired:desiredCount}' \
        --output table

    # Check MSK
    print_info "Checking MSK cluster..."
    aws kafka list-clusters --region $REGION --query 'ClusterInfoList[0].{Name:ClusterName,State:State}' --output table

    # Check Redis
    print_info "Checking Redis..."
    aws elasticache describe-replication-groups \
        --region $REGION \
        --query 'ReplicationGroups[0].{Id:ReplicationGroupId,Status:Status}' \
        --output table

    # Check DynamoDB
    print_info "Checking DynamoDB tables..."
    aws dynamodb list-tables --region $REGION --query 'TableNames[?contains(@, `pc-prod`) == `true`]' --output table

    print_success "Deployment verification complete!"
}

# Print summary
print_summary() {
    print_header "Deployment Summary"

    echo ""
    echo -e "${GREEN}🎉 Deployment Successful!${NC}"
    echo ""
    echo "📊 Resources Created:"
    echo "   - VPC with 3 AZs"
    echo "   - Amazon MSK (Kafka)"
    echo "   - ElastiCache (Redis)"
    echo "   - 5 DynamoDB tables"
    echo "   - SQS queue"
    echo "   - 5 ECS Fargate services"
    echo "   - AWS Amplify frontend"
    echo ""
    echo "📝 Important Information:"
    echo "   - Account ID: $ACCOUNT_ID"
    echo "   - Region: $REGION"
    echo "   - Stack Name: $STACK_NAME"
    echo "   - ECS Cluster: $(get_output 'ECSClusterName')"
    echo ""
    echo "💰 Estimated Monthly Cost: ~₹1,13,000 (~\$1,350)"
    echo ""
    echo "📖 Next Steps:"
    echo "   1. Deploy Cisco FTD from AWS Marketplace"
    echo "   2. Configure FTD with management IP"
    echo "   3. Update parameters.json with FTD details"
    echo "   4. Redeploy: ./deploy-to-aws-cloudformation.sh"
    echo "   5. Add test policies to DynamoDB"
    echo "   6. Monitor CloudWatch logs"
    echo ""
    echo "📚 Documentation:"
    echo "   - Deployment Guide: DEPLOYMENT_GUIDE.md"
    echo "   - Design Document: DESIGN.md"
    echo "   - Architecture: parental-control-backend/docs/ARCHITECTURE.md"
    echo ""
    echo "🔗 Useful Commands:"
    echo "   - View logs: aws logs tail /ecs/pc-prod/p-gateway --follow --region $REGION"
    echo "   - List services: aws ecs list-services --cluster $(get_output 'ECSClusterName') --region $REGION"
    echo "   - Stack status: aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION"
    echo "   - Delete stack: aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
    echo ""
}

# Main execution
main() {
    print_header "Cisco AI Family Safety - Full AWS Deployment (CloudFormation)"
    echo ""
    print_info "Starting deployment process..."
    echo ""

    check_prerequisites
    echo ""

    validate_template
    echo ""

    deploy_infrastructure
    echo ""

    build_and_push_images
    echo ""

    update_ecs_services
    echo ""

    deploy_frontend
    echo ""

    verify_deployment
    echo ""

    print_summary
}

# Run main function
main
