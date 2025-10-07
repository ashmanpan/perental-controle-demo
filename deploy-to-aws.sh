#!/bin/bash

#########################################
# Full AWS Deployment Script
# Cisco AI Family Safety - Parental Control
#########################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_warning "Terraform not installed. Installing..."
        install_terraform
    else
        print_success "Terraform installed"
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured"
        exit 1
    fi
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    REGION=$(aws configure get region)
    print_success "AWS credentials configured (Account: $ACCOUNT_ID, Region: $REGION)"
}

# Install Terraform
install_terraform() {
    print_info "Installing Terraform..."
    cd /tmp
    wget -q https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
    unzip -q terraform_1.6.6_linux_amd64.zip
    sudo mv terraform /usr/local/bin/
    rm terraform_1.6.6_linux_amd64.zip
    print_success "Terraform installed: $(terraform version -json | jq -r .terraform_version)"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_header "Deploying Infrastructure with Terraform"

    cd parental-control-backend/infrastructure/terraform

    # Initialize
    print_info "Initializing Terraform..."
    terraform init

    # Plan
    print_info "Planning infrastructure..."
    terraform plan -out=tfplan

    # Confirm
    echo ""
    print_warning "This will create ~₹1,13,000/month (~\$1,350/month) in AWS resources"
    read -p "Continue with deployment? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        print_error "Deployment cancelled"
        exit 0
    fi

    # Apply
    print_info "Deploying infrastructure (this will take 45-60 minutes)..."
    terraform apply tfplan

    # Save outputs
    terraform output > deployment-outputs.txt
    print_success "Infrastructure deployed! Outputs saved to deployment-outputs.txt"

    cd ../../..
}

# Build and push Docker images
build_and_push_images() {
    print_header "Building and Pushing Docker Images"

    # Get ECR URLs from Terraform
    cd parental-control-backend/infrastructure/terraform
    ECR_P_GATEWAY=$(terraform output -raw ecr_p_gateway_url)
    ECR_KAFKA=$(terraform output -raw ecr_kafka_subscriber_url)
    ECR_ENFORCER=$(terraform output -raw ecr_policy_enforcer_url)
    ECR_FTD=$(terraform output -raw ecr_ftd_integration_url)
    ECR_ANALYTICS=$(terraform output -raw ecr_analytics_dashboard_url)
    cd ../../..

    # Login to ECR
    print_info "Logging into ECR..."
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    print_success "Logged into ECR"

    # Build and push each service
    services=("p-gateway-simulator:$ECR_P_GATEWAY" "kafka-subscriber:$ECR_KAFKA" "policy-enforcer:$ECR_ENFORCER" "ftd-integration:$ECR_FTD" "analytics-dashboard:$ECR_ANALYTICS")

    for service_pair in "${services[@]}"; do
        IFS=':' read -r service ecr_url <<< "$service_pair"

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

    CLUSTER_NAME="pc-prod-cluster"

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

    # Check ECS services
    print_info "Checking ECS services..."
    CLUSTER_NAME="pc-prod-cluster"
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
    aws dynamodb list-tables --region $REGION --query 'TableNames[?contains(@, `Parental`) == `true`]' --output table

    print_success "Deployment verification complete!"
}

# Print summary
print_summary() {
    print_header "Deployment Summary"

    cd parental-control-backend/infrastructure/terraform

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
    echo "   - ECS Cluster: pc-prod-cluster"
    echo ""
    echo "💰 Estimated Monthly Cost: ~₹1,13,000 (~\$1,350)"
    echo ""
    echo "📖 Next Steps:"
    echo "   1. Deploy Cisco FTD from AWS Marketplace"
    echo "   2. Configure FTD with management IP"
    echo "   3. Update terraform.tfvars with FTD details"
    echo "   4. Run: terraform apply -auto-approve"
    echo "   5. Add test policies to DynamoDB"
    echo "   6. Monitor CloudWatch logs"
    echo ""
    echo "📚 Documentation:"
    echo "   - Deployment Guide: DEPLOYMENT_GUIDE.md"
    echo "   - Design Document: DESIGN.md"
    echo "   - Architecture: parental-control-backend/docs/ARCHITECTURE.md"
    echo ""
    echo "🔗 Useful Commands:"
    echo "   - View logs: aws logs tail /ecs/pc-prod/p-gateway --follow"
    echo "   - List services: aws ecs list-services --cluster pc-prod-cluster"
    echo "   - Check costs: aws ce get-cost-and-usage --time-period Start=2025-10-01,End=2025-10-08 --granularity DAILY --metrics BlendedCost"
    echo ""

    cd ../../..
}

# Main execution
main() {
    print_header "Cisco AI Family Safety - Full AWS Deployment"
    echo ""
    print_info "Starting deployment process..."
    echo ""

    check_prerequisites
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
