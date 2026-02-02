"""
PHASE 3: Like & Karma Service
==============================

This module handles like operations with:
1. Atomic database operations
2. Race condition prevention
3. Karma event creation

CONCURRENCY STRATEGY:
---------------------
Problem: Two users clicking "like" at exact same moment
Naive: Check if exists → Create if not → RACE CONDITION!

Solution 1: SELECT FOR UPDATE (pessimistic locking)
    - Locks the row during transaction
    - Other transactions wait
    - Guarantees consistency but reduces throughput

Solution 2: Unique Constraint + IntegrityError (optimistic)
    - Try to insert
    - DB rejects duplicate (unique constraint violation)
    - Catch IntegrityError, return appropriate response
    - Higher throughput, simpler code

We use Solution 2 because:
- Likes are high-write, low-conflict
- Unique constraint is already needed for data integrity
- IntegrityError handling is cleaner than locking

TRANSACTION STRATEGY:
--------------------
Like creation and KarmaEvent creation are in the same transaction.
If either fails, both are rolled back → consistent state.
"""

from typing import Tuple, Literal
from django.db import transaction, IntegrityError
from django.db.models import F
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from .models import Post, Comment, Like, KarmaEvent, KARMA_POST_LIKE, KARMA_COMMENT_LIKE


class LikeResult:
    """Result of a like operation with type safety."""
    def __init__(
        self, 
        success: bool, 
        action: Literal['created', 'removed', 'already_exists', 'already_removed'],
        karma_delta: int = 0
    ):
        self.success = success
        self.action = action
        self.karma_delta = karma_delta


def like_post(user: User, post_id: int) -> LikeResult:
    """
    Like a post atomically.
    
    OPERATION:
    1. Get post (verify exists)
    2. Try to create Like (unique constraint prevents duplicates)
    3. If success: Create KarmaEvent, increment counter
    4. If IntegrityError: Like already exists
    
    ATOMICITY:
    All operations in single transaction - either all succeed or all fail.
    
    RETURNS:
    - LikeResult with action taken
    """
    try:
        post = Post.objects.select_related('author').get(id=post_id)
    except Post.DoesNotExist:
        raise ValueError(f"Post {post_id} does not exist")
    
    content_type = ContentType.objects.get_for_model(Post)
    
    try:
        with transaction.atomic():
            # Attempt to create like - will fail if already exists
            Like.objects.create(
                user=user,
                content_type=content_type,
                object_id=post_id
            )
            
            # Create karma event for post author
            # IMPORTANT: Don't give karma for liking your own content
            if post.author_id != user.id:
                KarmaEvent.objects.create(
                    recipient=post.author,
                    actor=user,
                    event_type=KarmaEvent.EventType.POST_LIKED,
                    karma_delta=KARMA_POST_LIKE,
                    content_type=content_type,
                    object_id=post_id
                )
            
            # Update denormalized counter
            # Using F() for atomic increment - prevents race condition
            Post.objects.filter(id=post_id).update(like_count=F('like_count') + 1)
            
            return LikeResult(
                success=True,
                action='created',
                karma_delta=KARMA_POST_LIKE if post.author_id != user.id else 0
            )
            
    except IntegrityError:
        # Like already exists - unique constraint violation
        # This is expected behavior, not an error
        return LikeResult(
            success=False,
            action='already_exists',
            karma_delta=0
        )


def unlike_post(user: User, post_id: int) -> LikeResult:
    """
    Remove a like from a post.
    
    KARMA TRACKING:
    Creates a negative KarmaEvent (-5 karma) to maintain karma sync.
    This ensures like/unlike/re-like doesn't double karma.
    
    ANTI-GAMING:
    Rate limiting should be added for production to prevent
    like/unlike spam attacks on karma system.
    """
    content_type = ContentType.objects.get_for_model(Post)
    
    try:
        post = Post.objects.select_related('author').get(id=post_id)
    except Post.DoesNotExist:
        return LikeResult(success=False, action='already_removed')
    
    with transaction.atomic():
        deleted_count, _ = Like.objects.filter(
            user=user,
            content_type=content_type,
            object_id=post_id
        ).delete()
        
        if deleted_count > 0:
            # Create negative karma event to reverse the original karma
            # IMPORTANT: Only if the post author is not the user (matching like logic)
            if post.author_id != user.id:
                KarmaEvent.objects.create(
                    recipient=post.author,
                    actor=user,
                    event_type=KarmaEvent.EventType.POST_UNLIKED,
                    karma_delta=-KARMA_POST_LIKE,
                    content_type=content_type,
                    object_id=post_id
                )
            
            # Update denormalized counter
            Post.objects.filter(id=post_id).update(like_count=F('like_count') - 1)
            return LikeResult(
                success=True, 
                action='removed',
                karma_delta=-KARMA_POST_LIKE if post.author_id != user.id else 0
            )
        else:
            return LikeResult(success=False, action='already_removed')


def like_comment(user: User, comment_id: int) -> LikeResult:
    """
    Like a comment atomically.
    
    Same pattern as like_post but with +1 karma instead of +5.
    """
    try:
        comment = Comment.objects.select_related('author').get(id=comment_id)
    except Comment.DoesNotExist:
        raise ValueError(f"Comment {comment_id} does not exist")
    
    content_type = ContentType.objects.get_for_model(Comment)
    
    try:
        with transaction.atomic():
            Like.objects.create(
                user=user,
                content_type=content_type,
                object_id=comment_id
            )
            
            # Create karma event for comment author
            if comment.author_id != user.id:
                KarmaEvent.objects.create(
                    recipient=comment.author,
                    actor=user,
                    event_type=KarmaEvent.EventType.COMMENT_LIKED,
                    karma_delta=KARMA_COMMENT_LIKE,
                    content_type=content_type,
                    object_id=comment_id
                )
            
            # Update denormalized counter
            Comment.objects.filter(id=comment_id).update(like_count=F('like_count') + 1)
            
            return LikeResult(
                success=True,
                action='created',
                karma_delta=KARMA_COMMENT_LIKE if comment.author_id != user.id else 0
            )
            
    except IntegrityError:
        return LikeResult(
            success=False,
            action='already_exists',
            karma_delta=0
        )


def unlike_comment(user: User, comment_id: int) -> LikeResult:
    """
    Remove a like from a comment.
    
    Creates negative karma event to maintain karma sync.
    """
    content_type = ContentType.objects.get_for_model(Comment)
    
    try:
        comment = Comment.objects.select_related('author').get(id=comment_id)
    except Comment.DoesNotExist:
        return LikeResult(success=False, action='already_removed')
    
    with transaction.atomic():
        deleted_count, _ = Like.objects.filter(
            user=user,
            content_type=content_type,
            object_id=comment_id
        ).delete()
        
        if deleted_count > 0:
            # Create negative karma event
            if comment.author_id != user.id:
                KarmaEvent.objects.create(
                    recipient=comment.author,
                    actor=user,
                    event_type=KarmaEvent.EventType.COMMENT_UNLIKED,
                    karma_delta=-KARMA_COMMENT_LIKE,
                    content_type=content_type,
                    object_id=comment_id
                )
            
            Comment.objects.filter(id=comment_id).update(like_count=F('like_count') - 1)
            return LikeResult(
                success=True, 
                action='removed',
                karma_delta=-KARMA_COMMENT_LIKE if comment.author_id != user.id else 0
            )
        else:
            return LikeResult(success=False, action='already_removed')


def toggle_like(user: User, target_type: str, target_id: int) -> LikeResult:
    """
    Toggle like on a post or comment.
    
    This is a convenience function for the API - checks current state
    and either creates or removes the like.
    
    IMPORTANT: This is NOT atomic across check-and-toggle!
    A race condition here is benign:
    - Worst case: two toggles become a no-op
    - User can just click again
    - Much simpler than distributed locking
    """
    if target_type == 'post':
        content_type = ContentType.objects.get_for_model(Post)
    elif target_type == 'comment':
        content_type = ContentType.objects.get_for_model(Comment)
    else:
        raise ValueError(f"Invalid target_type: {target_type}")
    
    # Check if like exists
    like_exists = Like.objects.filter(
        user=user,
        content_type=content_type,
        object_id=target_id
    ).exists()
    
    if like_exists:
        if target_type == 'post':
            return unlike_post(user, target_id)
        else:
            return unlike_comment(user, target_id)
    else:
        if target_type == 'post':
            return like_post(user, target_id)
        else:
            return like_comment(user, target_id)


# ============================================================================
# WHY INTEGRITHERROR IS BETTER THAN SELECT_FOR_UPDATE HERE
# ============================================================================
"""
Alternative Implementation with SELECT FOR UPDATE:

def like_post_pessimistic(user: User, post_id: int) -> LikeResult:
    with transaction.atomic():
        # Lock the row (or create an advisory lock)
        existing = Like.objects.select_for_update().filter(
            user=user,
            content_type=content_type,
            object_id=post_id
        ).first()
        
        if existing:
            return LikeResult(success=False, action='already_exists')
        
        Like.objects.create(...)
        # etc.

Problems with this approach:
1. Can't lock a row that doesn't exist yet
2. Would need table-level lock or advisory lock
3. Reduces concurrency significantly
4. More complex code

The IntegrityError approach is:
- Simpler to understand
- Higher throughput (no waiting for locks)
- The constraint is already there for data integrity
- We just leverage it for concurrency control too
"""
