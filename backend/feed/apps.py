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
        
        # Auto-create demo user on startup
        # This runs when the app is ready, ensuring demo user always exists
        self._ensure_demo_user()
    
    def _ensure_demo_user(self):
        """
        Create the demo user if it doesn't exist.
        
        This is called on every startup to ensure the demo user exists.
        Safe to call multiple times - uses get_or_create.
        """
        # Avoid running during migrations
        import sys
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
        
        try:
            from django.contrib.auth.models import User
            User.objects.get_or_create(
                username='demo',
                defaults={
                    'email': 'demo@karmafeed.local',
                    'first_name': 'Demo',
                    'last_name': 'User',
                }
            )
        except Exception:
            # Silently fail if database isn't ready yet
            pass
