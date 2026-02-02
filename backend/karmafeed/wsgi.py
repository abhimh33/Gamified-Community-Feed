"""
WSGI config for karmafeed project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karmafeed.settings')
application = get_wsgi_application()
