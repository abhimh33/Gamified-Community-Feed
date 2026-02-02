"""
PHASE 5: DRF Serializers
=========================

Serializers handle:
1. Validation of incoming data
2. Transformation of model instances to JSON
3. Nested comment tree serialization

DESIGN DECISIONS:
-----------------
1. Separate serializers for list vs detail views (performance)
2. RecursiveField for nested comments
3. Read-only serializers for computed fields
"""

from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Post, Comment

# Maximum depth for nested comments (prevents infinite nesting)
MAX_COMMENT_DEPTH = 10


class UserSerializer(serializers.ModelSerializer):
    """Minimal user representation for embedding in other objects."""
    
    class Meta:
        model = User
        fields = ['id', 'username']
        read_only_fields = fields


class PostListSerializer(serializers.ModelSerializer):
    """
    Serializer for feed list view.
    
    Optimized for list performance - no nested comments.
    Uses select_related('author') in the view.
    """
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 
            'title', 
            'content', 
            'author',
            'like_count', 
            'comment_count',
            'created_at'
        ]
        read_only_fields = ['like_count', 'comment_count', 'created_at']


class PostCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating posts.
    
    Author is set from request.user in the view, not from input.
    This prevents users from creating posts as other users.
    """
    
    class Meta:
        model = Post
        fields = ['title', 'content']
    
    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters.")
        return value.strip()
    
    def validate_content(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Content must be at least 10 characters.")
        return value.strip()


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for individual comments.
    
    NOTE: This does NOT include nested replies!
    Tree structure is handled by CommentTreeSerializer.
    """
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = [
            'id',
            'content',
            'author',
            'parent',
            'depth',
            'like_count',
            'created_at'
        ]
        read_only_fields = ['depth', 'like_count', 'created_at']


class CommentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating comments.
    
    Validates that:
    1. Parent comment (if provided) belongs to same post
    2. Content is not empty
    """
    
    class Meta:
        model = Comment
        fields = ['content', 'parent']
    
    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment cannot be empty.")
        return value.strip()
    
    def validate(self, attrs):
        """
        Validate parent comment belongs to same post.
        
        Post ID comes from the view (URL parameter).
        """
        parent = attrs.get('parent')
        post_id = self.context.get('post_id')
        
        if parent and parent.post_id != post_id:
            raise serializers.ValidationError({
                'parent': 'Parent comment must belong to the same post.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create comment with proper depth calculation.
        
        Depth = parent.depth + 1 (or 0 for root comments)
        Maximum depth is enforced to prevent infinite nesting.
        """
        parent = validated_data.get('parent')
        if parent:
            if parent.depth >= MAX_COMMENT_DEPTH:
                raise serializers.ValidationError({
                    'parent': f'Maximum reply depth ({MAX_COMMENT_DEPTH}) reached. Cannot nest deeper.'
                })
            validated_data['depth'] = parent.depth + 1
        else:
            validated_data['depth'] = 0
        
        return super().create(validated_data)


class CommentTreeSerializer(serializers.Serializer):
    """
    Serializer for nested comment tree.
    
    This is NOT a ModelSerializer because it serializes
    the pre-built tree structure from build_comment_tree().
    
    Structure:
    {
        "comment": { ...comment data... },
        "replies": [ ...nested CommentTreeSerializer... ]
    }
    """
    comment = CommentSerializer()
    replies = serializers.SerializerMethodField()
    
    def get_replies(self, obj):
        """Recursively serialize replies."""
        # obj['replies'] is already a list of tree nodes
        return CommentTreeSerializer(obj['replies'], many=True).data


class PostDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for post detail view with nested comments.
    
    Comments are passed as pre-built tree in context.
    """
    author = UserSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    user_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'author',
            'like_count',
            'comment_count',
            'created_at',
            'updated_at',
            'comments',
            'user_liked'
        ]
    
    def get_comments(self, obj):
        """
        Get nested comment tree from context.
        
        The tree is pre-built by the view using queries.build_comment_tree()
        to avoid N+1 queries during serialization.
        """
        comment_tree = self.context.get('comment_tree', [])
        return CommentTreeSerializer(comment_tree, many=True).data
    
    def get_user_liked(self, obj):
        """Check if current user has liked this post."""
        liked_data = self.context.get('user_liked_data', {})
        return liked_data.get('post_liked', False)


class LeaderboardEntrySerializer(serializers.Serializer):
    """Serializer for leaderboard entries."""
    rank = serializers.IntegerField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    total_karma = serializers.IntegerField()


class LikeActionSerializer(serializers.Serializer):
    """
    Serializer for like/unlike actions.
    
    Validates target type and ID.
    """
    target_type = serializers.ChoiceField(choices=['post', 'comment'])
    target_id = serializers.IntegerField(min_value=1)
    
    def validate(self, attrs):
        """Validate that target exists."""
        target_type = attrs['target_type']
        target_id = attrs['target_id']
        
        if target_type == 'post':
            if not Post.objects.filter(id=target_id).exists():
                raise serializers.ValidationError({
                    'target_id': f'Post {target_id} does not exist.'
                })
        elif target_type == 'comment':
            if not Comment.objects.filter(id=target_id).exists():
                raise serializers.ValidationError({
                    'target_id': f'Comment {target_id} does not exist.'
                })
        
        return attrs
