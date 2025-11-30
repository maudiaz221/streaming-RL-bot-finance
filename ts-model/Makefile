# AWS ECR Configuration
AWS_REGION ?= us-east-1
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY ?= $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
ECR_REPOSITORY ?= binance-crypto-api
IMAGE_TAG ?= latest

# Docker Configuration
DOCKER_IMAGE = $(ECR_REPOSITORY):$(IMAGE_TAG)
DOCKER_IMAGE_FULL = $(ECR_REGISTRY)/$(DOCKER_IMAGE)

.PHONY: help
help: ## Display this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## Build the Docker image locally
	@echo "Building Docker image: $(DOCKER_IMAGE)"
	docker build -t $(DOCKER_IMAGE) .
	@echo "✓ Image built successfully"

.PHONY: run
run: ## Run the Docker container locally
	@echo "Running container on http://localhost:8000"
	docker run -p 8000:8000 --rm $(DOCKER_IMAGE)

.PHONY: run-detached
run-detached: ## Run the Docker container in detached mode
	@echo "Running container in detached mode on http://localhost:8000"
	docker run -d -p 8000:8000 --name crypto-api $(DOCKER_IMAGE)

.PHONY: stop
stop: ## Stop the running container
	docker stop crypto-api || true
	docker rm crypto-api || true

.PHONY: ecr-login
ecr-login: ## Login to AWS ECR
	@echo "Logging into ECR registry: $(ECR_REGISTRY)"
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	@echo "✓ Successfully logged in to ECR"

.PHONY: ecr-create-repo
ecr-create-repo: ## Create ECR repository if it doesn't exist
	@echo "Creating ECR repository: $(ECR_REPOSITORY)"
	@aws ecr describe-repositories --repository-names $(ECR_REPOSITORY) --region $(AWS_REGION) >/dev/null 2>&1 || \
	aws ecr create-repository \
		--repository-name $(ECR_REPOSITORY) \
		--region $(AWS_REGION) \
		--image-scanning-configuration scanOnPush=true \
		--encryption-configuration encryptionType=AES256
	@echo "✓ Repository ready"

.PHONY: tag
tag: ## Tag the Docker image for ECR
	@echo "Tagging image: $(DOCKER_IMAGE) -> $(DOCKER_IMAGE_FULL)"
	docker tag $(DOCKER_IMAGE) $(DOCKER_IMAGE_FULL)
	@echo "✓ Image tagged successfully"

.PHONY: push
push: ecr-login tag ## Push the Docker image to ECR
	@echo "Pushing image to ECR: $(DOCKER_IMAGE_FULL)"
	docker push $(DOCKER_IMAGE_FULL)
	@echo "✓ Image pushed successfully"

.PHONY: build-and-push
build-and-push: build push ## Build and push the Docker image to ECR

.PHONY: deploy
deploy: ecr-create-repo build-and-push ## Full deployment: create repo, build, and push
	@echo "=========================================="
	@echo "✓ Deployment complete!"
	@echo "Image URI: $(DOCKER_IMAGE_FULL)"
	@echo "=========================================="

.PHONY: pull
pull: ecr-login ## Pull the image from ECR
	@echo "Pulling image from ECR: $(DOCKER_IMAGE_FULL)"
	docker pull $(DOCKER_IMAGE_FULL)
	@echo "✓ Image pulled successfully"

.PHONY: clean
clean: ## Remove local Docker images
	docker rmi $(DOCKER_IMAGE) || true
	docker rmi $(DOCKER_IMAGE_FULL) || true
	@echo "✓ Local images cleaned"

.PHONY: info
info: ## Display configuration information
	@echo "Configuration:"
	@echo "  AWS Region:        $(AWS_REGION)"
	@echo "  AWS Account ID:    $(AWS_ACCOUNT_ID)"
	@echo "  ECR Registry:      $(ECR_REGISTRY)"
	@echo "  ECR Repository:    $(ECR_REPOSITORY)"
	@echo "  Image Tag:         $(IMAGE_TAG)"
	@echo "  Local Image:       $(DOCKER_IMAGE)"
	@echo "  Full Image URI:    $(DOCKER_IMAGE_FULL)"

