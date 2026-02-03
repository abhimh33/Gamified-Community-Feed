#!/bin/bash
# =============================================================================
# KarmaFeed Startup Script for Render.com
# =============================================================================
# This script runs before Gunicorn starts:
# 1. Runs database migrations
# 2. Creates demo user if not exists
# 3. Seeds sample data if database is empty
# 4. Starts Gunicorn server

set -e

echo "=== Running database migrations ==="
python manage.py migrate --no-input

echo "=== Creating demo user and seeding data if needed ==="
python manage.py shell -c "
from django.contrib.auth.models import User
from feed.models import Post

# Create demo user if not exists
if not User.objects.filter(username='demo').exists():
    User.objects.create_user('demo', 'demo@karmafeed.local', 'demo')
    print('Demo user created')
else:
    print('Demo user already exists')

# Seed data if no posts exist
if Post.objects.count() == 0:
    print('Database empty - will seed data')
    import subprocess
    subprocess.run(['python', 'manage.py', 'seed_data'])
else:
    print(f'Database has {Post.objects.count()} posts - skipping seed')
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
