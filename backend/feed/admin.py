"""
Django Admin Configuration for Feed Models
"""
from django.contrib import admin
from .models import Post, Comment, Like, KarmaEvent


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'like_count', 'comment_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['like_count', 'comment_count', 'created_at', 'updated_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'author', 'parent', 'depth', 'like_count', 'created_at']
    list_filter = ['created_at', 'depth']
    search_fields = ['content', 'author__username']
    readonly_fields = ['like_count', 'depth', 'created_at', 'updated_at']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_type', 'object_id', 'created_at']
    list_filter = ['content_type', 'created_at']
    search_fields = ['user__username']


@admin.register(KarmaEvent)
class KarmaEventAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'actor', 'event_type', 'karma_delta', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['recipient__username', 'actor__username']
    readonly_fields = ['recipient', 'actor', 'event_type', 'karma_delta', 
                       'content_type', 'object_id', 'created_at']
    
    def has_add_permission(self, request):
        # KarmaEvents should only be created by the system
        return False
    
    def has_change_permission(self, request, obj=None):
        # KarmaEvents are immutable
        return False
    
    def has_delete_permission(self, request, obj=None):
        # KarmaEvents should never be deleted (audit trail)
        return False
