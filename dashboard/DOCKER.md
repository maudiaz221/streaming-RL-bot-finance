# Docker & AWS ECR Deployment Guide

This guide explains how to dockerize and deploy the dashboard to AWS ECR.

## Prerequisites

- Docker installed and running
- AWS CLI configured with appropriate credentials
- AWS account with ECR permissions

## Quick Start

### 1. Build and Run Locally

```bash
# Build the Docker image
make build

# Run the container
make run

# Or run in detached mode
make run-detached

# Stop the container
make stop
```

Visit http://localhost:3000 to view the application.

### 2. Deploy to AWS ECR

```bash
# Option 1: Full deployment (recommended for first time)
make deploy

# Option 2: Step by step
make ecr-create-repo  # Create ECR repository
make build            # Build Docker image
make push             # Push to ECR
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make help` | Display all available commands |
| `make build` | Build the Docker image locally |
| `make run` | Run the container locally (foreground) |
| `make run-detached` | Run the container in background |
| `make stop` | Stop and remove the running container |
| `make ecr-login` | Login to AWS ECR |
| `make ecr-create-repo` | Create ECR repository if it doesn't exist |
| `make tag` | Tag the image for ECR |
| `make push` | Push the image to ECR |
| `make build-and-push` | Build and push in one command |
| `make deploy` | Full deployment (create repo + build + push) |
| `make pull` | Pull the image from ECR |
| `make clean` | Remove local Docker images |
| `make info` | Display current configuration |

## Configuration

You can override default values using environment variables:

```bash
# Change AWS region
make deploy AWS_REGION=us-west-2

# Use a specific image tag
make deploy IMAGE_TAG=v1.0.0

# Specify AWS account ID explicitly
make deploy AWS_ACCOUNT_ID=123456789012

# Use a different repository name
make deploy ECR_REPOSITORY=my-custom-dashboard
```

## Docker Image Details

The Dockerfile uses a multi-stage build with three stages:

1. **deps**: Installs dependencies
2. **builder**: Builds the Next.js application
3. **runner**: Creates minimal production image

### Image Size Optimization

- Uses Alpine Linux (minimal base image)
- Multi-stage build reduces final image size
- Only production dependencies included
- Standalone output mode for Next.js

### Security Features

- Runs as non-root user (nextjs:nodejs)
- Minimal attack surface with Alpine
- ECR image scanning enabled on push

## Production Deployment

### Deploy with specific version

```bash
# Tag and deploy a specific version
make deploy IMAGE_TAG=v1.2.3
```

### Pull and run from ECR

```bash
# Pull the latest image
make pull

# Run the ECR image
docker run -p 3000:3000 \
  $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/binance-crypto-dashboard:latest
```

## Troubleshooting

### ECR Login Issues

```bash
# Manually login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com
```

### Check AWS Configuration

```bash
# View current configuration
make info

# Verify AWS credentials
aws sts get-caller-identity
```

### Build Issues

```bash
# Clean and rebuild
make clean
make build
```

### View container logs

```bash
# If running in detached mode
docker logs dashboard

# Follow logs
docker logs -f dashboard
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy to ECR

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy to ECR
        run: |
          cd dashboard
          make deploy IMAGE_TAG=${{ github.sha }}
```

## Environment Variables

You can pass environment variables to the container:

```bash
docker run -p 3000:3000 \
  -e NODE_ENV=production \
  -e API_URL=https://api.example.com \
  binance-crypto-dashboard:latest
```

## Additional Resources

- [Next.js Docker Documentation](https://nextjs.org/docs/deployment#docker-image)
- [AWS ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

