"""
Feed App URL Configuration
(Auth-free demo mode - all actions use demo user)
"""
from django.urls import path
from .views import (
    FeedView,
    PostCreateView,
    PostDetailView,
    CommentCreateView,
    LikeToggleView,
    LikePostView,
    LikeCommentView,
    LeaderboardView,
)

urlpatterns = [
    # Feed
    path('feed/', FeedView.as_view(), name='feed'),
    
    # Posts
    path('posts/', PostCreateView.as_view(), name='post-create'),
    path('posts/<int:post_id>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/comments/', CommentCreateView.as_view(), name='comment-create'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
    
    # Comments
    path('comments/<int:comment_id>/like/', LikeCommentView.as_view(), name='like-comment'),
    
    # Likes (unified endpoint)
    path('likes/toggle/', LikeToggleView.as_view(), name='like-toggle'),
    
    # Leaderboard
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]
