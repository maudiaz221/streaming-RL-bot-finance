#!/usr/bin/env bash
set -e

# Configuración
AWS_REGION="us-east-1"
ECR_URI="164332231571.dkr.ecr.us-east-1.amazonaws.com/arquitectura/websocket_alpaca"
IMAGE_NAME="websocket_alpaca"
TAG="latest"
FULL_IMAGE_URI="${ECR_URI}:${TAG}"


# Extraer sólo la parte del registry (sin path)
REGISTRY_URL="${ECR_URI%/*}"

echo "🔐 Autenticando en ECR ($REGISTRY_URL)..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${REGISTRY_URL}"

echo "🐳 Construyendo la imagen Docker..."
docker build -t "${IMAGE_NAME}" --platform=linux/amd64 .

echo "🏷 Etiquetando la imagen..."
docker tag "${IMAGE_NAME}:${TAG}" "${FULL_IMAGE_URI}"

echo "📤 Enviando la imagen a ECR..."
docker push "${FULL_IMAGE_URI}"

echo "✅ ¡Listo! Imagen subida a ${FULL_IMAGE_URI}"

