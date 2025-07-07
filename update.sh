#!/bin/bash

# Seamless Docker Compose Update Script
# This script updates Docker containers with minimal downtime

set -e  # Exit on any error

echo "🔄 Starting seamless update process..."

# Step 1: Pull latest images
echo "📥 Pulling latest Docker images..."
docker compose pull

# Step 2: Check if containers are running
if docker compose ps -q | grep -q .; then
    echo "🔄 Updating running containers..."
    
    # Step 3: Rolling update - recreate containers with new images
    docker compose up -d --force-recreate --no-deps
    
    # Step 4: Wait for services to be healthy
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    
    # Step 5: Check if services are running
    if docker compose ps | grep -q "Up"; then
        echo "✅ Update completed successfully!"
        echo "📊 Current status:"
        docker compose ps
    else
        echo "❌ Update failed - services are not running properly"
        exit 1
    fi
else
    echo "🚀 No containers running, starting fresh..."
    docker compose up -d
fi

# Step 6: Clean up old images
echo "🧹 Cleaning up old Docker images..."
docker image prune -f

echo "🎉 Update process completed!"
