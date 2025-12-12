#!/bin/bash
set -euo pipefail

#Set DJANGO_SETTINGS_MODULE as development settings (works for the duration of the script's execution only!)
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-SystemApp.settings.dev}

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting files..."
python manage.py collectstatic --noinput

#Run scheduled-task setup once
echo "Setting up system's scheduled tasks..."
python manage.py setup_scheduled_tasks || true


ROLE="${SERVICE:-web}"

if [ "$ROLE" = "qcluster" ]; then
  echo "Starting Django-Q2 qcluster (dev)..."
  exec python manage.py qcluster
fi

if [ ! -f "/app/.seeded" ]; then
  echo "Creating dummy data..."
  python seed.py
  touch /app/.seeded
fi 


# #Identify number of CPU cores on system
# CPU_CORES=$(nproc --all)

# #Rule of thumb: (2 * cores) + 1
# WORKERS=$(( 2 * CPU_CORES + 1 ))


#Start Gunicorn server
echo "Starting Gunicorn (dev) on 0.0.0.0:8000..."
exec gunicorn SystemApp.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${WORKERS:-3}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  --log-level info


