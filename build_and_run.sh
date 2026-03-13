#!/usr/bin/env bash
set -e

IMAGE="hormigasais/lbh-image-validator:v0.1"

echo "📦 Construyendo imagen LBH Image Validator..."
docker build -t $IMAGE .

echo "📏 Auditoría de peso:"
docker images $IMAGE

echo "🚀 Ejecutando verificación de prueba..."
mkdir -p "$(pwd)/imagenes"
docker run --rm \
  -v "$(pwd)/imagenes:/app/imagenes" \
  $IMAGE verificar /app/imagenes/imagen.png

echo "✅ lbh-image-validator container listo"
