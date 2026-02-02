"""
PHASE 5: DRF Views
==================

API endpoints for the feed application.

AUTHENTICATION NOTE:
--------------------
For simplicity, we're using session authentication for the prototype.
Production would use JWT or OAuth2.

For testing without authentication, we simulate a logged-in user.
"""

from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from .models import Post, Comment
from .serializers import (
    PostListSerializer,
    PostCreateSerializer,
    PostDetailSerializer,
    CommentCreateSerializer,
    LeaderboardEntrySerializer,
    LikeActionSerializer
)
from .queries import (
    get_post_with_author,
    get_all_comments_for_post,
    build_comment_tree,
    get_user_liked_items
)
from .services import toggle_like, like_post, like_comment, unlike_post, unlike_comment
from .leaderboard import get_leaderboard, get_user_karma


class FeedPagination(CursorPagination):
    """
    Cursor pagination for the feed.
    
    WHY CURSOR PAGINATION:
    - Offset pagination: SELECT ... LIMIT 20 OFFSET 1000 → scans 1020 rows
    - Cursor pagination: SELECT ... WHERE created_at < cursor → index seek
    
    Trade-off: Can't jump to arbitrary page, but O(1) vs O(n).
    Perfect for infinite scroll feeds.
    """
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'


class FeedView(generics.ListAPIView):
    """
    GET /api/feed/
    
    Returns paginated list of posts, newest first.
    
    Query: 1 (with author JOIN)
    """
    serializer_class = PostListSerializer
    pagination_class = FeedPagination
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Post.objects.select_related('author').order_by('-created_at')


class PostCreateView(generics.CreateAPIView):
    """
    POST /api/posts/
    
    Create a new post. Requires authentication.
    """
    serializer_class = PostCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Author is set from authenticated user, not from request body
        serializer.save(author=self.request.user)


class PostDetailView(APIView):
    """
    GET /api/posts/<id>/
    
    Returns post with full nested comment tree.
    
    QUERY COUNT: 2-3
    1. Post with author
    2. All comments with authors
    3. (Optional) User's likes if authenticated
    
    Tree building happens in Python, not in DB.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, post_id):
        # Query 1: Get post
        post = get_post_with_author(post_id)
        if not post:
            return Response(
                {'error': 'Post not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Query 2: Get all comments and build tree
        flat_comments = get_all_comments_for_post(post_id)
        comment_tree = build_comment_tree(flat_comments)
        
        # Query 3: Get user's likes (if authenticated)
        user_liked_data = {}
        if request.user.is_authenticated:
            user_liked_data = get_user_liked_items(request.user.id, post_id)
        
        # Serialize with pre-built tree in context
        serializer = PostDetailSerializer(
            post,
            context={
                'comment_tree': comment_tree,
                'user_liked_data': user_liked_data,
                'request': request
            }
        )
        
        return Response(serializer.data)


class CommentCreateView(generics.CreateAPIView):
    """
    POST /api/posts/<post_id>/comments/
    
    Create a comment on a post. Requires authentication.
    
    Body:
    {
        "content": "Comment text",
        "parent": 123  // optional, for replies
    }
    """
    serializer_class = CommentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['post_id'] = self.kwargs['post_id']
        return context
    
    def perform_create(self, serializer):
        post = get_object_or_404(Post, id=self.kwargs['post_id'])
        serializer.save(
            author=self.request.user,
            post=post
        )


class LikeToggleView(APIView):
    """
    POST /api/likes/toggle/
    
    Toggle like on a post or comment.
    
    Body:
    {
        "target_type": "post" | "comment",
        "target_id": 123
    }
    
    Returns:
    {
        "action": "created" | "removed",
        "success": true | false
    }
    
    CONCURRENCY:
    - Uses atomic transactions
    - Unique constraint prevents duplicates
    - IntegrityError handled gracefully
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = LikeActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        target_type = serializer.validated_data['target_type']
        target_id = serializer.validated_data['target_id']
        
        try:
            result = toggle_like(request.user, target_type, target_id)
            return Response({
                'success': result.success,
                'action': result.action,
                'karma_delta': result.karma_delta
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


class LikePostView(APIView):
    """
    POST /api/posts/<post_id>/like/
    
    Like a specific post.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        try:
            result = like_post(request.user, post_id)
            return Response({
                'success': result.success,
                'action': result.action
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, post_id):
        """Unlike a post."""
        result = unlike_post(request.user, post_id)
        return Response({
            'success': result.success,
            'action': result.action
        })


class LikeCommentView(APIView):
    """
    POST /api/comments/<comment_id>/like/
    
    Like a specific comment.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, comment_id):
        try:
            result = like_comment(request.user, comment_id)
            return Response({
                'success': result.success,
                'action': result.action
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, comment_id):
        """Unlike a comment."""
        from .services import unlike_comment
        result = unlike_comment(request.user, comment_id)
        return Response({
            'success': result.success,
            'action': result.action
        })


class LeaderboardView(APIView):
    """
    GET /api/leaderboard/
    
    Returns top 5 users by karma in last 24 hours.
    
    Query params:
    - hours: Time window (default 24)
    - limit: Number of results (default 5, max 100)
    
    QUERY:
    Single aggregation query with index on (created_at, recipient_id)
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        # Parse query params with defaults and limits
        try:
            hours = min(int(request.query_params.get('hours', 24)), 168)  # Max 1 week
            limit = min(int(request.query_params.get('limit', 5)), 100)  # Max 100
        except ValueError:
            hours = 24
            limit = 5
        
        leaderboard = get_leaderboard(hours=hours, limit=limit)
        
        # Add current user's stats if authenticated
        user_stats = None
        if request.user.is_authenticated:
            user_karma = get_user_karma(request.user.id, hours=hours)
            user_stats = {
                'user_id': request.user.id,
                'username': request.user.username,
                'karma': user_karma
            }
        
        return Response({
            'leaderboard': LeaderboardEntrySerializer(leaderboard, many=True).data,
            'time_window_hours': hours,
            'user_stats': user_stats
        })


# ============================================================================
# DEVELOPMENT/TESTING HELPERS
# ============================================================================

class MockAuthView(APIView):
    """
    POST /api/auth/mock-login/
    
    DEVELOPMENT ONLY: Quick login for testing without full auth flow.
    Creates user if doesn't exist.
    
    Body: { "username": "testuser" }
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        username = request.data.get('username', 'testuser')
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'}
        )
        
        # Log the user in (session-based)
        from django.contrib.auth import login
        login(request, user)
        
        return Response({
            'user_id': user.id,
            'username': user.username,
            'created': created
        })


class WhoAmIView(APIView):
    """
    GET /api/auth/whoami/
    
    Returns current authenticated user info.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        if request.user.is_authenticated:
            return Response({
                'authenticated': True,
                'user_id': request.user.id,
                'username': request.user.username
            })
        return Response({
            'authenticated': False,
            'user_id': None,
            'username': None
        })
