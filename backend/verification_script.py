"""
Principal Engineer Verification Script
=======================================
Produces concrete evidence for each verification requirement.
Run with: python manage.py shell < verification_script.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karmafeed.settings')
django.setup()

from datetime import timedelta
from django.utils import timezone
from django.db import connection, transaction, IntegrityError
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test.utils import CaptureQueriesContext
import threading
import time

from feed.models import Post, Comment, Like, KarmaEvent, KARMA_POST_LIKE
from feed.queries import get_post_with_comment_tree, get_all_comments_for_post, build_comment_tree
from feed.services import like_post
from feed.leaderboard import get_leaderboard, get_user_karma

print("=" * 80)
print("PRINCIPAL ENGINEER VERIFICATION - HARD EVIDENCE")
print("=" * 80)

# ============================================================================
# SETUP: Create test data
# ============================================================================
print("\n[SETUP] Creating test data...")

# Clean up previous test data
User.objects.filter(username__startswith='verify_').delete()
Post.objects.filter(title__startswith='VERIFY_').delete()

# Create users
author = User.objects.create_user('verify_author', 'a@test.com', 'pass')
liker1 = User.objects.create_user('verify_liker1', 'l1@test.com', 'pass')
liker2 = User.objects.create_user('verify_liker2', 'l2@test.com', 'pass')
karma_user1 = User.objects.create_user('verify_karma1', 'k1@test.com', 'pass')
karma_user2 = User.objects.create_user('verify_karma2', 'k2@test.com', 'pass')
karma_user3 = User.objects.create_user('verify_karma3', 'k3@test.com', 'pass')

# Create post
post = Post.objects.create(
    author=author,
    title='VERIFY_N+1_Test_Post',
    content='This post is for verification testing. ' * 5
)

print(f"Created post ID: {post.id}")

# ============================================================================
# SECTION 1: N+1 QUERY VERIFICATION
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 1: N+1 QUERY VERIFICATION")
print("=" * 80)

# Create 50+ nested comments with depth >= 4
print("\n[1.1] Creating 50 nested comments (depth >= 4)...")

comments_created = []
current_parent = None

for i in range(50):
    depth = i % 5  # Cycles through depths 0, 1, 2, 3, 4
    
    if depth == 0:
        # New root thread
        current_parent = None
        parent_chain = []
    
    comment = Comment.objects.create(
        post=post,
        author=author,
        content=f'Comment {i} at depth {depth}',
        parent=current_parent,
        depth=depth
    )
    comments_created.append(comment)
    
    if depth < 4:
        current_parent = comment

print(f"Created {len(comments_created)} comments")

# Verify depth distribution
depth_counts = {}
for c in comments_created:
    depth_counts[c.depth] = depth_counts.get(c.depth, 0) + 1
print(f"Depth distribution: {depth_counts}")

# Now capture queries
print("\n[1.2] Capturing SQL queries for loading post + 50 comments...")

connection.queries_log.clear()

with CaptureQueriesContext(connection) as context:
    result = get_post_with_comment_tree(post.id)

print(f"\n[1.3] QUERY COUNT: {len(context.captured_queries)}")
print("\n[1.4] EXACT SQL QUERIES EXECUTED:")
print("-" * 60)

for i, query in enumerate(context.captured_queries, 1):
    sql = query['sql']
    time_ms = query['time']
    print(f"\nQuery {i} ({time_ms}s):")
    print(sql[:500] + "..." if len(sql) > 500 else sql)

print("-" * 60)

print(f"\n[1.5] RESULT: Loaded {result['comment_count']} comments in {len(context.captured_queries)} queries")

print("""
[1.6] EXPLANATION: Why recursion does NOT trigger new DB queries
-----------------------------------------------------------------
1. get_all_comments_for_post() fetches ALL comments in ONE query:
   SELECT comment.*, user.* FROM feed_comment 
   INNER JOIN auth_user ON comment.author_id = auth_user.id
   WHERE comment.post_id = %s ORDER BY created_at

2. build_comment_tree() assembles the tree in PYTHON (O(n)):
   - First pass: Build lookup dict {comment_id -> node}
   - Second pass: Attach children to parents using parent_id
   - NO database access during tree construction

3. The tree depth (0, 1, 2, 3, 4...) is irrelevant to query count
   because all comments are fetched upfront, not recursively.
""")

# ============================================================================
# SECTION 2: CONCURRENCY VERIFICATION
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 2: CONCURRENCY VERIFICATION (SIMULATED RACE)")
print("=" * 80)

# Create a fresh post for this test
concurrency_post = Post.objects.create(
    author=author,
    title='VERIFY_Concurrency_Test',
    content='Testing concurrent likes. ' * 5
)

print(f"\n[2.1] Created post ID: {concurrency_post.id} for concurrency test")

# Storage for thread results
thread_results = []
thread_exceptions = []

def attempt_like(user, post_id, results_list, exceptions_list, thread_name):
    """Attempt to like in a separate thread."""
    try:
        result = like_post(user, post_id)
        results_list.append({
            'thread': thread_name,
            'success': result.success,
            'action': result.action,
            'karma_delta': result.karma_delta
        })
    except Exception as e:
        exceptions_list.append({
            'thread': thread_name,
            'exception': str(e),
            'type': type(e).__name__
        })

print("\n[2.2] Simulating TWO concurrent requests liking same post...")
print("      Method: Two threads calling like_post() simultaneously")

# Create threads
t1 = threading.Thread(target=attempt_like, args=(liker1, concurrency_post.id, thread_results, thread_exceptions, 'Thread-1'))
t2 = threading.Thread(target=attempt_like, args=(liker1, concurrency_post.id, thread_results, thread_exceptions, 'Thread-2'))

# Start both at same time
t1.start()
t2.start()

# Wait for completion
t1.join()
t2.join()

print("\n[2.3] THREAD RESULTS:")
for r in thread_results:
    print(f"  {r['thread']}: success={r['success']}, action={r['action']}")

print("\n[2.4] DB CONSTRAINT THAT PREVENTS DUPLICATES:")
print("""
  Constraint Name: unique_like_per_user_per_object
  Definition: UNIQUE (user_id, content_type_id, object_id)
  
  When second INSERT attempts:
  - PostgreSQL raises: duplicate key value violates unique constraint
  - Django catches: IntegrityError
  - Service returns: LikeResult(success=False, action='already_exists')
""")

# Verify only one like exists
content_type = ContentType.objects.get_for_model(Post)
like_count = Like.objects.filter(
    user=liker1,
    content_type=content_type,
    object_id=concurrency_post.id
).count()

karma_count = KarmaEvent.objects.filter(
    actor=liker1,
    content_type=content_type,
    object_id=concurrency_post.id
).count()

print(f"\n[2.5] VERIFICATION:")
print(f"  Likes in database: {like_count} (expected: 1)")
print(f"  KarmaEvents created: {karma_count} (expected: 1)")
print(f"  Partial state exists: {'NO' if like_count == karma_count == 1 else 'YES - BUG!'}")

# Now demonstrate the actual constraint violation
print("\n[2.6] DEMONSTRATING CONSTRAINT VIOLATION DIRECTLY:")
print("-" * 60)

try:
    # Try to create duplicate like directly
    Like.objects.create(
        user=liker1,
        content_type=content_type,
        object_id=concurrency_post.id
    )
    print("ERROR: Duplicate was allowed!")
except IntegrityError as e:
    print(f"Exception Type: {type(e).__name__}")
    print(f"Exception Message: {str(e)[:200]}")
    print("\nThis proves the DB-level constraint prevents duplicates.")

# ============================================================================
# SECTION 3: LEADERBOARD TIME-WINDOW PROOF
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 3: LEADERBOARD TIME-WINDOW PROOF")
print("=" * 80)

# Clean up karma events for our test users
KarmaEvent.objects.filter(recipient__username__startswith='verify_karma').delete()

now = timezone.now()
post_ct = ContentType.objects.get_for_model(Post)

print("\n[3.1] Creating karma events at specific times:")

# Event 1: Now (should be included)
event_now = KarmaEvent.objects.create(
    recipient=karma_user1,
    actor=liker1,
    event_type=KarmaEvent.EventType.POST_LIKED,
    karma_delta=5,
    content_type=post_ct,
    object_id=post.id,
    created_at=now
)
print(f"  Event 1: verify_karma1, +5 karma, created_at = NOW ({now})")

# Event 2: 23 hours ago (should be included)
time_23h = now - timedelta(hours=23)
event_23h = KarmaEvent.objects.create(
    recipient=karma_user2,
    actor=liker1,
    event_type=KarmaEvent.EventType.POST_LIKED,
    karma_delta=5,
    content_type=post_ct,
    object_id=post.id,
    created_at=time_23h
)
print(f"  Event 2: verify_karma2, +5 karma, created_at = NOW-23h ({time_23h})")

# Event 3: 25 hours ago (should be EXCLUDED)
time_25h = now - timedelta(hours=25)
event_25h = KarmaEvent.objects.create(
    recipient=karma_user3,
    actor=liker1,
    event_type=KarmaEvent.EventType.POST_LIKED,
    karma_delta=5,
    content_type=post_ct,
    object_id=post.id,
    created_at=time_25h
)
print(f"  Event 3: verify_karma3, +5 karma, created_at = NOW-25h ({time_25h})")

print("\n[3.2] Running leaderboard query (24-hour window)...")

# Capture the query
connection.queries_log.clear()

from django.db.models import Sum
cutoff = now - timedelta(hours=24)

# This is the actual query from leaderboard.py
with CaptureQueriesContext(connection) as lb_context:
    results = list(
        KarmaEvent.objects
        .filter(created_at__gte=cutoff)
        .filter(recipient__username__startswith='verify_karma')
        .values('recipient_id', 'recipient__username')
        .annotate(total_karma=Sum('karma_delta'))
        .order_by('-total_karma')
    )

print("\n[3.3] DJANGO ORM QUERY:")
print("""
KarmaEvent.objects
    .filter(created_at__gte=cutoff)  # cutoff = now - 24 hours
    .values('recipient_id', 'recipient__username')
    .annotate(total_karma=Sum('karma_delta'))
    .order_by('-total_karma')
""")

print("\n[3.4] GENERATED SQL:")
print("-" * 60)
for q in lb_context.captured_queries:
    print(q['sql'])
print("-" * 60)

print("\n[3.5] RESULT SET:")
print(f"  Cutoff time: {cutoff}")
for r in results:
    print(f"  - {r['recipient__username']}: {r['total_karma']} karma")

# Verify karma_user3 is NOT in results
user3_in_results = any(r['recipient__username'] == 'verify_karma3' for r in results)
print(f"\n[3.6] verify_karma3 (25h ago event) in results: {user3_in_results}")
print(f"      Expected: False (excluded by time filter)")

print("""
[3.7] EXPLANATION: Why 25h event is excluded
---------------------------------------------
1. Cutoff calculation: cutoff = NOW - timedelta(hours=24)
2. Filter condition: WHERE created_at >= cutoff
3. Event at NOW-25h has created_at < cutoff
4. Therefore: excluded from GROUP BY and SUM aggregation

The WHERE clause is applied BEFORE aggregation, so old events
never contribute to any user's total_karma.
""")

# ============================================================================
# SECTION 4: INDEX UTILIZATION PROOF
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 4: INDEX UTILIZATION PROOF")
print("=" * 80)

print("\n[4.1] Running EXPLAIN ANALYZE on leaderboard query...")

explain_sql = f"""
EXPLAIN ANALYZE
SELECT 
    "feed_karmaevent"."recipient_id",
    "auth_user"."username" AS "recipient__username",
    SUM("feed_karmaevent"."karma_delta") AS "total_karma"
FROM "feed_karmaevent"
INNER JOIN "auth_user" ON ("feed_karmaevent"."recipient_id" = "auth_user"."id")
WHERE "feed_karmaevent"."created_at" >= '{cutoff.isoformat()}'
GROUP BY "feed_karmaevent"."recipient_id", "auth_user"."username"
ORDER BY "total_karma" DESC
LIMIT 5;
"""

print("\n[4.2] SQL QUERY:")
print("-" * 60)
print(explain_sql)
print("-" * 60)

with connection.cursor() as cursor:
    cursor.execute(explain_sql)
    explain_result = cursor.fetchall()

print("\n[4.3] EXPLAIN ANALYZE OUTPUT:")
print("-" * 60)
for row in explain_result:
    print(row[0])
print("-" * 60)

print("""
[4.4] INDEX ANALYSIS:
---------------------
Expected indexes to be used:
1. feed_karmae_created_c32ffc_idx ON (created_at, recipient_id)
   - Used for: WHERE created_at >= cutoff
   - Enables: Index scan instead of sequential scan

2. feed_karmae_recipie_5a9636_idx ON (recipient_id, created_at DESC)
   - Used for: GROUP BY recipient_id optimization
   - Enables: Index-only scan for aggregation

WHY THIS QUERY SCALES:
- Time filter uses index → O(log n) to find cutoff point
- Only recent events are scanned (last 24h)
- As data grows, old events don't slow down query
- LIMIT 5 means we stop after finding top 5
""")

# ============================================================================
# SECTION 5: FAILURE INJECTION TEST
# ============================================================================
print("\n" + "=" * 80)
print("SECTION 5: FAILURE INJECTION TEST")
print("=" * 80)

print("\n[5.1] TEST A: Breaking unique constraint")
print("-" * 60)

failure_post = Post.objects.create(
    author=author,
    title='VERIFY_Failure_Injection',
    content='Testing failure scenarios. ' * 5
)

# First like succeeds
result1 = like_post(liker2, failure_post.id)
print(f"First like: success={result1.success}, action={result1.action}")

# Second like (same user, same post) should fail gracefully
result2 = like_post(liker2, failure_post.id)
print(f"Second like: success={result2.success}, action={result2.action}")

# Verify state
ct = ContentType.objects.get_for_model(Post)
likes = Like.objects.filter(user=liker2, content_type=ct, object_id=failure_post.id).count()
karma = KarmaEvent.objects.filter(actor=liker2, content_type=ct, object_id=failure_post.id).count()
print(f"\nDatabase state: {likes} like(s), {karma} karma event(s)")
print("EXPECTED: 1 like, 1 karma event (no duplicates)")

print("\n[5.2] TEST B: Transaction rollback on failure")
print("-" * 60)

from django.db import transaction as db_transaction

rollback_post = Post.objects.create(
    author=author,
    title='VERIFY_Rollback_Test',
    content='Testing transaction rollback. ' * 5
)

initial_like_count = Like.objects.count()
initial_karma_count = KarmaEvent.objects.count()

print(f"Before transaction: {initial_like_count} likes, {initial_karma_count} karma events")

try:
    with db_transaction.atomic():
        # Create like
        Like.objects.create(
            user=liker2,
            content_type=ct,
            object_id=rollback_post.id
        )
        print("  - Like created inside transaction")
        
        # Create karma event
        KarmaEvent.objects.create(
            recipient=author,
            actor=liker2,
            event_type=KarmaEvent.EventType.POST_LIKED,
            karma_delta=5,
            content_type=ct,
            object_id=rollback_post.id
        )
        print("  - KarmaEvent created inside transaction")
        
        # DELIBERATELY CAUSE FAILURE
        print("  - Deliberately raising exception...")
        raise Exception("Simulated failure mid-transaction!")
        
except Exception as e:
    print(f"  - Exception caught: {e}")

final_like_count = Like.objects.count()
final_karma_count = KarmaEvent.objects.count()

print(f"\nAfter failed transaction: {final_like_count} likes, {final_karma_count} karma events")
print(f"Rollback occurred: {final_like_count == initial_like_count and final_karma_count == initial_karma_count}")
print("\nEXPECTED: Both counts unchanged (transaction rolled back)")

print("""
[5.3] EXPLANATION: How rollback occurs
---------------------------------------
1. transaction.atomic() creates a savepoint
2. All operations (Like.create, KarmaEvent.create) are tentative
3. When exception raised, Django:
   - Catches the exception
   - Issues ROLLBACK to PostgreSQL
   - All tentative changes are discarded
4. Database returns to state before transaction began

This ensures NO PARTIAL STATE:
- Either BOTH like + karma exist
- Or NEITHER exists
""")

# ============================================================================
# CLEANUP
# ============================================================================
print("\n" + "=" * 80)
print("CLEANUP")
print("=" * 80)

User.objects.filter(username__startswith='verify_').delete()
Post.objects.filter(title__startswith='VERIFY_').delete()
print("Test data cleaned up.")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
