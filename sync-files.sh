#!/bin/bash
# sync-files.sh - Git-based with options

set -e

SERVICES=("web" "qcluster" "postgres-backup")
COMPARE_WITH=${1:-HEAD~1}    #default: previous commit (but can be overridden)

echo "Identifying file changes..."
echo ""

CHANGED_FILES=$(git diff --name-only $COMPARE_WITH HEAD 2>/dev/null)

if [ -z "$CHANGED_FILES" ]; then
    echo "No changes detected. Exiting..."
    exit 0
fi

echo "Changed files:"
echo "$CHANGED_FILES" | sed 's/^/  - /'
echo ""

for service in "${SERVICES[@]}"; do
    CONTAINER="systemapp-$service"
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        echo "Syncing files to $CONTAINER..."
        
        echo "$CHANGED_FILES" | while read -r file; do
            if [ -f "$file" ]; then
                docker cp "$file" "$CONTAINER:/app/$file" 2>/dev/null && echo "  > $file"
            fi
        done
        
        docker restart "$CONTAINER" > /dev/null
        echo "Done"
        echo ""
    fi
done

echo "Files sync complete!"
echo ""
echo ""


#HOW TO USE (examples):
 # Sync changes from last commit only (default)
 # ./sync-files.sh

 # Sync changes from last 3 commits
 # ./sync-files.sh HEAD~3

 # Sync from specific commit
 # ./sync-files.sh abc1234

