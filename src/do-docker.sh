#!/bin/bash

# Check existing buildx builders
echo "Checking Docker buildx builders..."
sudo docker buildx ls

# Ensure mybuilder supports ARM64 and set it as the active builder
echo "Ensuring mybuilder supports ARM64..."
sudo docker buildx use mybuilder
sudo docker buildx inspect --bootstrap

# If ARM64 support isn't present, recreate the builder with ARM64
if ! sudo docker buildx ls | grep -q "linux/arm64"; then
    echo "ARM64 support not found for mybuilder. Creating a new builder with ARM64 support..."
    sudo docker buildx create --name mybuilder --platform linux/amd64,linux/arm64 --use
    sudo docker buildx inspect --bootstrap
else
    echo "ARM64 support is already available for mybuilder."
fi

# Ensure Docker login is done (if not already logged in)
echo "Logging into Docker..."
sudo docker login

# Build and push the image for ARM64 platform
echo "Building and pushing the image for ARM64..."
sudo docker buildx build --platform linux/arm64 --push -t landixbtw987/verify_arm:latest .
