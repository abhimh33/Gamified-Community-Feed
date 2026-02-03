"""
AUDIT TEST SCRIPT
=================
Verifies all karma and like logic for Playto submission.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karmafeed.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext
from datetime import timedelta
from django.utils import timezone
from feed.models import Post, Comment, Like, KarmaEvent, KARMA_POST_LIKE, KARMA_COMMENT_LIKE
from feed.services import like_post, unlike_post, like_comment, unlike_comment, toggle_like
from feed.leaderboard import get_leaderboard, get_user_karma
from feed.queries import get_all_comments_for_post, build_comment_tree

# ============================================================================
# SETUP
# ============================================================================
print("=" * 60)
print("AUDIT TEST: KARMAFEED")
print("=" * 60)

# Clear test data
KarmaEvent.objects.filter(recipient__username__startswith='test').delete()
Like.objects.filter(user__username__startswith='test').delete()
Comment.objects.filter(author__username__startswith='test').delete()
Post.objects.filter(author__username__startswith='test').delete()
User.objects.filter(username__startswith='test').delete()

# Create test users
author = User.objects.create_user('testauthor', 'author@test.com', 'pass123')
liker = User.objects.create_user('testliker', 'liker@test.com', 'pass123')
print(f"Created users: {author.username} (id={author.id}), {liker.username} (id={liker.id})")

# ============================================================================
# TEST 1: POST CREATION - 0 KARMA
# ============================================================================
print("\n" + "=" * 60)
print("TEST 1: POST CREATION - Should create 0 KarmaEvents")
print("=" * 60)

karma_before = KarmaEvent.objects.count()
post = Post.objects.create(
    author=author,
    title='Test Post Title',
    content='This is test content for the post'
)
karma_after = KarmaEvent.objects.count()

print(f"Post created: id={post.id}, author={author.username}")
print(f"KarmaEvents before: {karma_before}, after: {karma_after}")
result1 = karma_after == karma_before
print(f"RESULT: {'PASS' if result1 else 'FAIL'}")

# ============================================================================
# TEST 2: COMMENT CREATION - 0 KARMA
# ============================================================================
print("\n" + "=" * 60)
print("TEST 2: COMMENT CREATION - Should create 0 KarmaEvents")
print("=" * 60)

karma_before = KarmaEvent.objects.count()
comment = Comment.objects.create(
    post=post,
    author=liker,
    content='This is a test comment'
)
karma_after = KarmaEvent.objects.count()

print(f"Comment created: id={comment.id}, author={liker.username}")
print(f"KarmaEvents before: {karma_before}, after: {karma_after}")
result2 = karma_after == karma_before
print(f"RESULT: {'PASS' if result2 else 'FAIL'}")

# ============================================================================
# TEST 3: POST LIKE - +5 KARMA TO AUTHOR
# ============================================================================
print("\n" + "=" * 60)
print("TEST 3: POST LIKE - Should create 1 KarmaEvent (+5 to author)")
print("=" * 60)

karma_before = KarmaEvent.objects.count()
likes_before = Like.objects.count()

result = like_post(liker, post.id)

karma_after = KarmaEvent.objects.count()
likes_after = Like.objects.count()

print(f"like_post result: success={result.success}, action={result.action}")
print(f"Likes before: {likes_before}, after: {likes_after}")
print(f"KarmaEvents before: {karma_before}, after: {karma_after}")

# Verify karma event details
karma_event = KarmaEvent.objects.filter(
    recipient=author,
    event_type=KarmaEvent.EventType.POST_LIKED
).last()

if karma_event:
    print(f"KarmaEvent: recipient={karma_event.recipient.username}, actor={karma_event.actor.username}, delta={karma_event.karma_delta}")
    result3 = (
        likes_after == likes_before + 1 and
        karma_after == karma_before + 1 and
        karma_event.recipient_id == author.id and
        karma_event.actor_id == liker.id and
        karma_event.karma_delta == KARMA_POST_LIKE
    )
else:
    print("ERROR: No KarmaEvent created!")
    result3 = False

print(f"RESULT: {'PASS' if result3 else 'FAIL'}")

# ============================================================================
# TEST 4: DOUBLE-LIKE PROTECTION
# ============================================================================
print("\n" + "=" * 60)
print("TEST 4: DOUBLE-LIKE - Should fail, no new KarmaEvent")
print("=" * 60)

karma_before = KarmaEvent.objects.count()
likes_before = Like.objects.count()

result = like_post(liker, post.id)  # Try to like again

karma_after = KarmaEvent.objects.count()
likes_after = Like.objects.count()

print(f"like_post result: success={result.success}, action={result.action}")
print(f"Likes before: {likes_before}, after: {likes_after}")
print(f"KarmaEvents before: {karma_before}, after: {karma_after}")

result4 = (
    result.success == False and
    result.action == 'already_exists' and
    likes_after == likes_before and
    karma_after == karma_before
)
print(f"RESULT: {'PASS' if result4 else 'FAIL'}")

# ============================================================================
# TEST 5: COMMENT LIKE - +1 KARMA TO COMMENT AUTHOR
# ============================================================================
print("\n" + "=" * 60)
print("TEST 5: COMMENT LIKE - Should create 1 KarmaEvent (+1 to comment author)")
print("=" * 60)

karma_before = KarmaEvent.objects.count()
likes_before = Like.objects.count()

# Author likes liker's comment
result = like_comment(author, comment.id)

karma_after = KarmaEvent.objects.count()
likes_after = Like.objects.count()

print(f"like_comment result: success={result.success}, action={result.action}")
print(f"Likes before: {likes_before}, after: {likes_after}")
print(f"KarmaEvents before: {karma_before}, after: {karma_after}")

karma_event = KarmaEvent.objects.filter(
    recipient=liker,
    event_type=KarmaEvent.EventType.COMMENT_LIKED
).last()

if karma_event:
    print(f"KarmaEvent: recipient={karma_event.recipient.username}, actor={karma_event.actor.username}, delta={karma_event.karma_delta}")
    result5 = (
        likes_after == likes_before + 1 and
        karma_after == karma_before + 1 and
        karma_event.recipient_id == liker.id and  # Comment author gets karma
        karma_event.actor_id == author.id and      # Post author is the liker
        karma_event.karma_delta == KARMA_COMMENT_LIKE
    )
else:
    print("ERROR: No KarmaEvent created!")
    result5 = False

print(f"RESULT: {'PASS' if result5 else 'FAIL'}")

# ============================================================================
# TEST 6: LIKER NEVER RECEIVES KARMA
# ============================================================================
print("\n" + "=" * 60)
print("TEST 6: LIKER NEVER RECEIVES KARMA")
print("=" * 60)

# Check all karma events - liker should never be recipient of likes they gave
liker_karma_as_recipient = KarmaEvent.objects.filter(
    recipient=liker,
    actor=liker
).exclude(event_type__in=[KarmaEvent.EventType.POST_UNLIKED, KarmaEvent.EventType.COMMENT_UNLIKED])

print(f"KarmaEvents where liker is both recipient AND actor: {liker_karma_as_recipient.count()}")
result6 = liker_karma_as_recipient.count() == 0
print(f"RESULT: {'PASS' if result6 else 'FAIL'}")

# ============================================================================
# TEST 7: LEADERBOARD - 24 HOUR WINDOW
# ============================================================================
print("\n" + "=" * 60)
print("TEST 7: LEADERBOARD - Only last 24 hours counted")
print("=" * 60)

# Create an old karma event (25 hours ago)
old_time = timezone.now() - timedelta(hours=25)
old_event = KarmaEvent.objects.create(
    recipient=liker,
    actor=author,
    event_type=KarmaEvent.EventType.POST_LIKED,
    karma_delta=100,  # Large value to detect if included
    content_type=ContentType.objects.get_for_model(Post),
    object_id=post.id
)
# Manually update created_at (override auto_now)
KarmaEvent.objects.filter(id=old_event.id).update(created_at=old_time)

# Get leaderboard
leaderboard = get_leaderboard(hours=24, limit=10)

print(f"Leaderboard entries: {len(leaderboard)}")
for entry in leaderboard:
    print(f"  {entry['username']}: {entry['total_karma']} karma")

# Check liker's karma - should NOT include the +100
liker_entry = next((e for e in leaderboard if e['user_id'] == liker.id), None)
if liker_entry:
    print(f"Liker's karma: {liker_entry['total_karma']} (should be 1, not 101)")
    result7 = liker_entry['total_karma'] == 1  # Only the comment like
else:
    print("Liker not on leaderboard (karma < others)")
    # Check via direct query
    liker_karma = get_user_karma(liker.id, hours=24)
    print(f"Liker's karma via get_user_karma: {liker_karma}")
    result7 = liker_karma == 1

print(f"RESULT: {'PASS' if result7 else 'FAIL'}")

# ============================================================================
# TEST 8: N+1 QUERY PREVENTION - COMMENT TREE
# ============================================================================
print("\n" + "=" * 60)
print("TEST 8: N+1 QUERY PREVENTION - Fetching 50+ comments")
print("=" * 60)

# Create 50 nested comments
print("Creating 50 nested comments...")
prev_comment = None
for i in range(50):
    c = Comment.objects.create(
        post=post,
        author=author if i % 2 == 0 else liker,
        parent=prev_comment,
        content=f'Nested comment {i+1}',
        depth=i
    )
    prev_comment = c

# Count queries when fetching all comments
reset_queries()
connection.queries_log.clear()

with CaptureQueriesContext(connection) as context:
    flat_comments = get_all_comments_for_post(post.id)
    tree = build_comment_tree(flat_comments)

query_count = len(context.captured_queries)
print(f"Comments fetched: {len(flat_comments)}")
print(f"Queries executed: {query_count}")

# Show actual queries
for q in context.captured_queries[:5]:
    print(f"  Query: {q['sql'][:100]}...")

result8 = query_count <= 3  # 1-2 for comments + author, maybe 1 for content type
print(f"RESULT: {'PASS' if result8 else 'FAIL'} (expected <= 3 queries)")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 60)
print("AUDIT SUMMARY")
print("=" * 60)

tests = [
    ("Post creation creates 0 karma", result1),
    ("Comment creation creates 0 karma", result2),
    ("Post like creates +5 karma to author", result3),
    ("Double-like fails, no duplicate karma", result4),
    ("Comment like creates +1 karma to comment author", result5),
    ("Liker never receives karma", result6),
    ("Leaderboard only counts last 24 hours", result7),
    ("N+1 prevented: O(1) queries for comments", result8),
]

passed = sum(1 for _, r in tests if r)
failed = len(tests) - passed

for name, result in tests:
    status = "PASS" if result else "FAIL"
    print(f"  [{status}] {name}")

print()
print(f"TOTAL: {passed}/{len(tests)} passed")

if failed == 0:
    print("\n✅ ALL TESTS PASSED - READY FOR SUBMISSION")
else:
    print(f"\n❌ {failed} TESTS FAILED - NOT READY FOR SUBMISSION")

# Cleanup
print("\nCleaning up test data...")
KarmaEvent.objects.filter(recipient__username__startswith='test').delete()
Like.objects.filter(user__username__startswith='test').delete()
Comment.objects.filter(author__username__startswith='test').delete()
Post.objects.filter(author__username__startswith='test').delete()
User.objects.filter(username__startswith='test').delete()
print("Done.")
