"""
Feed App Configuration
"""
from django.apps import AppConfig


class FeedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'feed'
    
    def ready(self):
        # Import signals when app is ready
        import feed.signals  # noqa
