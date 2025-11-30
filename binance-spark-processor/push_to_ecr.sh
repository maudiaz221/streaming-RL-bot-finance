#!/usr/bin/env bash
set -e

# ==========================================
# ECR Push Script for Binance Spark Processor
# ==========================================
# This script builds and pushes the Docker image to AWS ECR
#
# Usage:
#   ./push_to_ecr.sh [TAG]
#
# Examples:
#   ./push_to_ecr.sh           # Uses 'latest' tag
#   ./push_to_ecr.sh v1.0.0    # Uses 'v1.0.0' tag
#

# Configuration - Update these values for your environment
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="164332231571.dkr.ecr.us-east-1.amazonaws.com/arquitectura/spark-processing"
IMAGE_NAME="binance-spark-processor"
TAG="${1:-latest}"

# Derived variables
FULL_IMAGE_URI="${ECR_REPOSITORY}:${TAG}"
REGISTRY_URL=$(echo "${ECR_REPOSITORY}" | cut -d'/' -f1)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${NC} $1"
}

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI is not installed. Please install it first."
        exit 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install it first."
        exit 1
    fi
}

# Main execution
echo ""
log_info "Starting ECR deployment process..."
echo ""

# Check prerequisites
check_aws_cli
check_docker

# Display configuration
log_info "Configuration:"
echo "  AWS Region: ${AWS_REGION}"
echo "  ECR Repository: ${ECR_REPOSITORY}"
echo "  Image Tag: ${TAG}"
echo "  Full URI: ${FULL_IMAGE_URI}"
echo ""

# Authenticate with ECR
log_info "Authenticating with ECR (${REGISTRY_URL})..."
if aws ecr get-login-password --region "${AWS_REGION}" | \
   docker login --username AWS --password-stdin "${REGISTRY_URL}"; then
    log_success "Successfully authenticated with ECR"
else
    echo "❌ Failed to authenticate with ECR"
    exit 1
fi
echo ""

# Build Docker image
log_info "Building Docker image (platform: linux/amd64)..."
if docker build -t "${IMAGE_NAME}:${TAG}" --platform=linux/amd64 .; then
    log_success "Docker image built successfully"
else
    echo "❌ Failed to build Docker image"
    exit 1
fi
echo ""

# Tag image
log_info "Tagging image for ECR..."
if docker tag "${IMAGE_NAME}:${TAG}" "${FULL_IMAGE_URI}"; then
    log_success "Image tagged successfully"
else
    echo "❌ Failed to tag image"
    exit 1
fi
echo ""

# Push to ECR
log_info "Pushing image to ECR..."
if docker push "${FULL_IMAGE_URI}"; then
    log_success "Image pushed successfully"
else
    echo "❌ Failed to push image to ECR"
    exit 1
fi
echo ""

# Final summary
log_success "Deployment complete!"
echo ""
echo "📦 Image Details:"
echo "  Repository: ${ECR_REPOSITORY}"
echo "  Tag: ${TAG}"
echo "  Full URI: ${FULL_IMAGE_URI}"
echo ""
echo "🚀 Next Steps (on EC2):"
echo "  1. Login to ECR:"
echo "     aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${REGISTRY_URL}"
echo ""
echo "  2. Pull the image:"
echo "     docker pull ${FULL_IMAGE_URI}"
echo ""
echo "  3. Run with docker-compose:"
echo "     docker-compose up -d"
echo ""

