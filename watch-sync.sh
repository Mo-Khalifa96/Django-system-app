#!/bin/bash
# watch-sync.sh

# Requires: inotify-tools
# Install: sudo apt-get install inotify-tools

WATCH_DIR="."
EXCLUDE_DIRS="(.git|__pycache__|*.pyc|logs|backups|static|media)"
SERVICES=("systemapp-web" "systemapp-qcluster")

echo "Watching for file changes in $WATCH_DIR..."
echo "Press Ctrl+C to stop"

inotifywait -m -r -e modify,create,delete \
    --exclude "$EXCLUDE_DIRS" \
    --format '%w%f' "$WATCH_DIR" | while read file
do
    # Ignore certain file types
    if [[ "$file" =~ \.(pyc|swp|tmp)$ ]]; then
        continue
    fi
    
    echo ""
    echo "Change detected: $file"
    
    # Copy to containers
    for service in "${SERVICES[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
            docker cp "$file" "$service:/app/${file#./}" 2>/dev/null && \
                echo "  ✓ Synced to $service"
        fi
    done
    
    #Optional: restart containers
    #docker restart systemapp-web systemapp-qcluster
done



#HOW TO USE:

 # Add permission first
 # chmod +x ./watch-sync.sh

 # Start watching in background
 # ./watch-sync.sh &