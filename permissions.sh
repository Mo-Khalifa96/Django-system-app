#!/bin/sh

set -e

#Grant executable permissions to the other scripts
echo "Setting permissions..."
chmod +x /app/wait-for-it.sh
chmod +x /app/database-backup.sh
chmod +x /app/database-backup-cron.sh
chmod +x /app/docker-entrypoint.dev.sh
chmod +x /app/docker-entrypoint.prod.sh
chmod +x /app/renew-certs.sh
chmod +x /app/sync-files.sh
chmod +x /app/watch-sync.sh
chmod 755 /app/logs

#Set permissions for /backups by postgres-backup service only
if [ "$SERVICE" = "postgres-backup" ]; then
    chmod 700 /backups
else
    echo "Skipping backup permissions for service: ${SERVICE:-unknown}"
fi

#Execute the command passed to the script (the CMD from Dockerfile or command from docker-compose)
echo "Executing command: $@"
exec "$@"