#!/bin/bash

# Set environment variables for user permissions using current user's ID
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

# Use DOCKER_UID/DOCKER_GID instead of UID/GID to avoid readonly variable issues
export DOCKER_UID=$CURRENT_UID
export DOCKER_GID=$CURRENT_GID

# Check if requirements.txt has changed since last build
REQUIREMENTS_HASH_FILE=".requirements.hash"
CURRENT_HASH=$(md5sum requirements.txt | awk '{ print $1 }')
STORED_HASH=""

if [ -f "$REQUIREMENTS_HASH_FILE" ]; then
    STORED_HASH=$(cat "$REQUIREMENTS_HASH_FILE")
fi

if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
    echo "Requirements have changed. Rebuilding Docker image..."
    docker-compose build --no-cache
    echo "$CURRENT_HASH" > "$REQUIREMENTS_HASH_FILE"
fi

# Run the scanner with passed arguments
docker-compose run --rm docs-scanner "$@"