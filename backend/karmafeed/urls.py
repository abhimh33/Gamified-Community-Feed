"""
KarmaFeed URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def api_root(request):
    """Root endpoint with API information."""
    return JsonResponse({
        'message': 'KarmaFeed API Server',
        'version': '1.0',
        'endpoints': {
            'feed': '/api/feed/',
            'posts': '/api/posts/<id>/',
            'comments': '/api/comments/',
            'like': '/api/like/<type>/<id>/',
            'leaderboard': '/api/leaderboard/',
            'auth': '/api/auth/',
        },
        'frontend': 'http://localhost:3000',
        'admin': '/admin/',
    })


urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', include('feed.urls')),
]
