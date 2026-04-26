#!/bin/bash
set -e

echo "Starting development deployment..."

if [[ "$1" == "--rebuild" && "$2" == "--no-cache" ]]; then
    echo "Building development image with no cache..."
    docker compose --profile dev build --no-cache --build-arg ENVIRONMENT=development
elif [[ "$1" == "--rebuild" ]] || ! docker images --format "{{.Repository}}" | grep -qE "(system-app|systemapp)"; then
    echo "Building development image with dev dependencies..."
    docker compose --profile dev build --build-arg ENVIRONMENT=development
else
    echo "Images already exist, skipping build..."
fi

#Development stack (no SSL/nginx by default)
docker compose --profile dev up -d postgres web qcluster tests


#To run, make sure you have permission:
    # chmod +x deploy.dev.sh
    # ./deploy.dev.sh (assuming you're in the root directory)
    
#For force rebuild, run:
    # ./deploy.dev.sh --rebuild

#or (for building without cache):
    # ./deploy.dev.sh --rebuild --no-cache
