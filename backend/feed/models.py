"""
PHASE 1: Data Models for KarmaFeed
===================================

Design Philosophy:
------------------
1. Comments use Adjacency List pattern (parent_id FK) - simple, works with ORM
   - Trade-off: Tree assembly in Python vs PostgreSQL recursive CTE
   - Chose Python assembly because it's more portable and debuggable
   - For very deep trees (1000+ nodes), would switch to Materialized Path

2. Likes use a polymorphic approach via ContentType
   - Alternative: Separate PostLike/CommentLike tables (more explicit, faster queries)
   - Chose unified Like model for simpler karma aggregation
   - Unique constraint prevents duplicate likes at DB level

3. KarmaEvent is an append-only transaction log
   - NEVER update or delete - only insert
   - Enables time-windowed queries without stored aggregates
   - Trade-off: More storage, but correct-by-construction

4. No denormalized counters on User
   - Leaderboard computed from KarmaEvent with time filter
   - Trade-off: Slightly slower leaderboard, but always consistent

Indexes Strategy:
-----------------
- comment.post_id + comment.created_at: For fetching all comments for a post
- like.content_type + like.object_id + like.user: For uniqueness + lookup
- karmaevent.recipient + karmaevent.created_at: For leaderboard aggregation
- karmaevent.created_at: For time-windowed queries
"""

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinLengthValidator
from django.utils import timezone


class Post(models.Model):
    """
    A feed post. Root-level content that can have comments.
    
    Design Decision: Using Django's built-in User model for simplicity.
    In production, would extend with a Profile model for additional fields.
    """
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        db_index=True  # For fetching user's posts
    )
    title = models.CharField(
        max_length=300,
        validators=[MinLengthValidator(3)]
    )
    content = models.TextField(
        validators=[MinLengthValidator(10)]
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True  # For feed ordering - critical for cursor pagination
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    # Denormalized count for display - updated via signals
    # Trade-off: Slight inconsistency window vs N+1 for counting
    # This is acceptable because like counts don't need to be exact
    like_count = models.PositiveIntegerField(default=0, db_index=True)
    comment_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Composite index for feed queries with author filter
            models.Index(fields=['-created_at', 'author']),
        ]

    def __str__(self):
        return f"{self.title[:50]} by {self.author.username}"


class Comment(models.Model):
    """
    Threaded comment using Adjacency List pattern.
    
    WHY ADJACENCY LIST:
    - Simple to understand and debug
    - Works well with Django ORM
    - Efficient bulk fetch with prefetch_related
    - Tree assembly in Python is O(n) single pass
    
    WHY NOT MATERIALIZED PATH (like '/1/5/12/'):
    - More complex to maintain on moves
    - String manipulation for ancestry queries
    - Would use if we needed subtree queries frequently
    
    WHY NOT NESTED SET (lft/rgt):
    - Expensive writes (rebalancing)
    - This app is write-heavy (new comments often)
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        db_index=True  # Critical: fetching all comments for a post
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        db_index=True  # For tree traversal
    )
    content = models.TextField(
        validators=[MinLengthValidator(1)]
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    # Denormalized for display
    like_count = models.PositiveIntegerField(default=0)
    
    # Depth stored for query optimization and rendering
    # Trade-off: Slight denormalization, but saves recursive depth calculation
    depth = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['created_at']  # Oldest first within a thread
        indexes = [
            # THE critical index: fetch all comments for a post, ordered
            models.Index(fields=['post', 'created_at']),
            # For finding replies to a specific comment
            models.Index(fields=['parent', 'created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post_id}"


class Like(models.Model):
    """
    Polymorphic Like using Django's ContentType framework.
    
    CONCURRENCY STRATEGY:
    - Unique constraint (user, content_type, object_id) enforced at DB level
    - Use get_or_create with select_for_update for atomic check-and-create
    - IntegrityError caught and handled gracefully
    
    WHY CONTENTTYPES:
    - Single table for all likes simplifies karma aggregation
    - Alternative: PostLike + CommentLike tables (faster queries, more code)
    
    Trade-off: ContentType adds a JOIN, but karma query is already aggregating
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    
    # Generic foreign key to Post or Comment
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        # CRITICAL: This constraint prevents duplicate likes at DB level
        # Even if two requests hit simultaneously, only one succeeds
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id'],
                name='unique_like_per_user_per_object'
            )
        ]
        indexes = [
            # For checking if user liked something
            models.Index(fields=['user', 'content_type', 'object_id']),
            # For counting likes on an object
            models.Index(fields=['content_type', 'object_id']),
            # For time-based queries (karma calculation)
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} liked {self.content_type.model} {self.object_id}"


class KarmaEvent(models.Model):
    """
    Append-only transaction log for karma.
    
    CRITICAL DESIGN DECISION:
    - This is an EVENT LOG, not a mutable record
    - NEVER update or delete rows
    - Leaderboard computed by aggregating events with time filter
    
    WHY NOT STORE DAILY_KARMA ON USER:
    - Requirement explicitly forbids it
    - Mutable counters lead to race conditions
    - Time-windowed queries become impossible with pre-aggregated data
    - Event log is the source of truth
    
    KARMA VALUES:
    - Post like received: +5 karma
    - Comment like received: +1 karma
    
    Trade-off: More storage, slower leaderboard query
    Benefit: Always correct, auditable, time-travel queries possible
    """
    
    class EventType(models.TextChoices):
        POST_LIKED = 'POST_LIKED', 'Post Liked'
        COMMENT_LIKED = 'COMMENT_LIKED', 'Comment Liked'
        # Future: POST_UNLIKED, COMMENT_UNLIKED (would be negative karma)
    
    # Who receives the karma (content author)
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='karma_received',
        db_index=True
    )
    
    # Who triggered the karma event (liker)
    actor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='karma_given'
    )
    
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices
    )
    
    # Karma points for this event
    # Stored explicitly so we can change karma values without recomputing history
    karma_delta = models.SmallIntegerField()
    
    # Reference to what was liked (for audit trail)
    # Using ContentType for flexibility
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Immutable timestamp
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        # No unique constraint - multiple events for same object are valid
        # (e.g., if we add unlike/re-like functionality)
        indexes = [
            # THE CRITICAL INDEX for leaderboard query:
            # SELECT recipient, SUM(karma_delta) 
            # WHERE created_at > NOW() - 24h
            # GROUP BY recipient ORDER BY SUM DESC LIMIT 5
            models.Index(fields=['created_at', 'recipient']),
            
            # For user's karma history
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f"{self.recipient.username} +{self.karma_delta} ({self.event_type})"


# ============================================================================
# KARMA CONSTANTS
# ============================================================================
# Centralized for easy adjustment and testing
KARMA_POST_LIKE = 5
KARMA_COMMENT_LIKE = 1
