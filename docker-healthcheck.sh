#!/bin/bash

# Docker health check script
# This script is used by Docker to verify the container is healthy

set -e

# Check if the API is responding
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/health || echo "000")

if [ "$response" = "200" ]; then
    exit 0
else
    echo "Health check failed with status: $response"
    exit 1
fi
