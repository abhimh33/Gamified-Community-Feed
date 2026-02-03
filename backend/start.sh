#!/bin/bash
# =============================================================================
# KarmaFeed Startup Script for Render.com
# =============================================================================
# This script runs before Gunicorn starts:
# 1. Runs database migrations
# 2. Creates demo user if not exists
# 3. Starts Gunicorn server

set -e

echo "=== Running database migrations ==="
python manage.py migrate --no-input

echo "=== Creating demo user if not exists ==="
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='demo').exists():
    User.objects.create_user('demo', 'demo@karmafeed.local', 'demo')
    print('Demo user created')
else:
    print('Demo user already exists')
"

echo "=== Starting Gunicorn ==="
exec gunicorn karmafeed.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance
