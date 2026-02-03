#!/usr/bin/env bash
# Render Build Script for Django
# This runs during each deployment

set -o errexit  # Exit on any error

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Running database migrations ==="
python manage.py migrate

echo "=== Creating demo user if not exists ==="
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='demo').exists():
    User.objects.create_user('demo', 'demo@karmafeed.local', 'demo')
    print('Demo user created')
else:
    print('Demo user already exists')
"

echo "=== Build complete ==="
