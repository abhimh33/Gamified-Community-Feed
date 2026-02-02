"""
Django Signals for maintaining denormalized counters.

Trade-off Discussion:
---------------------
We use signals to update like_count and comment_count on Post/Comment.

PROS:
- Automatic - no need to remember to update counts
- Centralized logic

CONS:
- Implicit behavior (can be surprising)
- Signals fire on every save (even bulk operations... wait, no they don't!)

IMPORTANT: Signals do NOT fire on:
- bulk_create()
- bulk_update()
- QuerySet.update()
- QuerySet.delete()

Our services.py uses QuerySet.update(like_count=F(...)) directly,
so these signals are NOT used for like counts (which is correct!).

These signals ARE used for:
- Comment creation (to update post.comment_count)
- Comment deletion (to update post.comment_count)
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F

from .models import Comment


@receiver(post_save, sender=Comment)
def increment_comment_count(sender, instance, created, **kwargs):
    """
    When a new comment is created, increment the post's comment count.
    
    NOTE: This uses a separate query, which is fine because:
    1. Comment creation is less frequent than reads
    2. The update is atomic (F() expression)
    """
    if created:
        from .models import Post
        Post.objects.filter(id=instance.post_id).update(
            comment_count=F('comment_count') + 1
        )


@receiver(post_delete, sender=Comment)
def decrement_comment_count(sender, instance, **kwargs):
    """
    When a comment is deleted, decrement the post's comment count.
    
    NOTE: This doesn't handle cascade deletes properly.
    If a parent comment is deleted, its children are also deleted,
    but this signal fires for each child.
    
    For production, might need to:
    1. Use soft deletes instead
    2. Or recalculate count periodically
    3. Or handle in the delete view explicitly
    
    For this prototype, we accept the trade-off.
    """
    from .models import Post
    Post.objects.filter(id=instance.post_id).update(
        comment_count=F('comment_count') - 1
    )
