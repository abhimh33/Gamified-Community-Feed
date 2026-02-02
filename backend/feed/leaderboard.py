"""
PHASE 4: Leaderboard Query
===========================

This module contains the leaderboard calculation logic.

REQUIREMENTS:
- Top 5 users by karma earned in last 24 hours
- Post like = +5 karma
- Comment like = +1 karma
- Computed dynamically from KarmaEvent (NOT stored on User)

QUERY STRATEGY:
---------------
1. Filter KarmaEvent by created_at > NOW() - 24 hours
2. Group by recipient (user who earned karma)
3. Sum karma_delta for each recipient
4. Order by sum descending
5. Limit to 5

This leverages the index: (created_at, recipient)
"""

from datetime import timedelta
from typing import List, TypedDict
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib.auth.models import User

from .models import KarmaEvent


class LeaderboardEntry(TypedDict):
    """Type hint for leaderboard entries."""
    user_id: int
    username: str
    total_karma: int
    rank: int


def get_leaderboard(hours: int = 24, limit: int = 5) -> List[LeaderboardEntry]:
    """
    Get the top users by karma earned in the specified time window.
    
    DJANGO ORM QUERY:
    -----------------
    KarmaEvent.objects
        .filter(created_at__gte=cutoff)
        .values('recipient')
        .annotate(total_karma=Sum('karma_delta'))
        .order_by('-total_karma')[:5]
    
    EQUIVALENT SQL:
    ---------------
    SELECT 
        recipient_id,
        auth_user.username,
        SUM(karma_delta) AS total_karma
    FROM feed_karmaevent
    INNER JOIN auth_user ON feed_karmaevent.recipient_id = auth_user.id
    WHERE created_at >= NOW() - INTERVAL '24 hours'
    GROUP BY recipient_id, auth_user.username
    ORDER BY total_karma DESC
    LIMIT 5;
    
    INDEX USAGE:
    ------------
    Uses index on (created_at, recipient_id):
    1. Index scan for created_at >= cutoff (range scan)
    2. Already grouped by recipient_id in index
    3. PostgreSQL can do index-only scan if karma_delta is included
    
    For very high traffic, consider:
    - Materialized view refreshed every minute
    - Redis cache with TTL
    - But for prototype, direct query is fine
    
    PERFORMANCE ANALYSIS:
    ---------------------
    Assuming 10,000 karma events in 24 hours:
    - Without index: Full table scan O(n)
    - With (created_at) index: Range scan + sort
    - With (created_at, recipient_id) index: Range scan + efficient grouping
    
    Query should complete in < 100ms with proper indexes.
    """
    cutoff = timezone.now() - timedelta(hours=hours)
    
    # Query with aggregation
    # Using values() + annotate() for GROUP BY
    leaderboard_qs = (
        KarmaEvent.objects
        .filter(created_at__gte=cutoff)
        .values('recipient_id', 'recipient__username')
        .annotate(total_karma=Sum('karma_delta'))
        .order_by('-total_karma')[:limit]
    )
    
    # Transform to typed response
    result: List[LeaderboardEntry] = []
    for rank, entry in enumerate(leaderboard_qs, start=1):
        result.append({
            'user_id': entry['recipient_id'],
            'username': entry['recipient__username'],
            'total_karma': entry['total_karma'] or 0,
            'rank': rank
        })
    
    return result


def get_user_karma(user_id: int, hours: int = 24) -> int:
    """
    Get a specific user's karma for the time window.
    
    Useful for showing "Your rank" or "Your karma today".
    """
    cutoff = timezone.now() - timedelta(hours=hours)
    
    result = (
        KarmaEvent.objects
        .filter(
            recipient_id=user_id,
            created_at__gte=cutoff
        )
        .aggregate(
            total=Coalesce(Sum('karma_delta'), 0)
        )
    )
    
    return result['total']


def get_user_rank(user_id: int, hours: int = 24) -> int | None:
    """
    Get a specific user's rank in the leaderboard.
    
    Returns None if user has no karma in the time window.
    
    APPROACH:
    ---------
    We can't easily get rank without computing the full leaderboard.
    For a production system with millions of users, this would use:
    1. Redis sorted sets (ZRANK is O(log n))
    2. Or a separate rank table updated periodically
    
    For prototype, we use a subquery approach.
    """
    cutoff = timezone.now() - timedelta(hours=hours)
    
    # Get user's karma
    user_karma = get_user_karma(user_id, hours)
    
    if user_karma == 0:
        return None
    
    # Count users with more karma
    users_ahead = (
        KarmaEvent.objects
        .filter(created_at__gte=cutoff)
        .values('recipient_id')
        .annotate(total=Sum('karma_delta'))
        .filter(total__gt=user_karma)
        .count()
    )
    
    return users_ahead + 1


# ============================================================================
# RAW SQL EQUIVALENT (for documentation/debugging)
# ============================================================================
"""
The Django ORM query above translates to:

SELECT 
    "feed_karmaevent"."recipient_id",
    "auth_user"."username" AS "recipient__username",
    SUM("feed_karmaevent"."karma_delta") AS "total_karma"
FROM "feed_karmaevent"
INNER JOIN "auth_user" 
    ON ("feed_karmaevent"."recipient_id" = "auth_user"."id")
WHERE "feed_karmaevent"."created_at" >= '2024-01-14 10:30:00+00:00'
GROUP BY 
    "feed_karmaevent"."recipient_id",
    "auth_user"."username"
ORDER BY "total_karma" DESC
LIMIT 5;

EXPLAIN ANALYZE output (example with proper indexes):
-----------------------------------------------------
Limit  (cost=100.50..100.52 rows=5 width=24)
  ->  Sort  (cost=100.50..102.00 rows=200 width=24)
        Sort Key: (sum(karma_delta)) DESC
        ->  HashAggregate  (cost=90.00..92.00 rows=200 width=24)
              Group Key: recipient_id
              ->  Index Scan using feed_karmaevent_created_at_idx 
                    on feed_karmaevent  (cost=0.29..75.00 rows=1000 width=12)
                    Index Cond: (created_at >= '2024-01-14 10:30:00+00:00')

This shows:
1. Index scan on created_at (not full table scan)
2. Hash aggregate for grouping (efficient)
3. Sort only on the final result set (small)
"""


# ============================================================================
# ALTERNATIVE: Raw SQL for complex scenarios
# ============================================================================
def get_leaderboard_raw_sql(hours: int = 24, limit: int = 5) -> List[LeaderboardEntry]:
    """
    Raw SQL version of the leaderboard query.
    
    USE WHEN:
    - ORM-generated SQL is suboptimal
    - Need database-specific features (CTEs, window functions)
    - Performance is critical and you've profiled the ORM version
    
    For this case, the ORM version is sufficient and more maintainable.
    This is here for documentation purposes.
    """
    from django.db import connection
    
    sql = """
        SELECT 
            ke.recipient_id AS user_id,
            u.username,
            COALESCE(SUM(ke.karma_delta), 0) AS total_karma,
            ROW_NUMBER() OVER (ORDER BY SUM(ke.karma_delta) DESC) AS rank
        FROM feed_karmaevent ke
        INNER JOIN auth_user u ON ke.recipient_id = u.id
        WHERE ke.created_at >= NOW() - INTERVAL '%s hours'
        GROUP BY ke.recipient_id, u.username
        ORDER BY total_karma DESC
        LIMIT %s;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(sql, [hours, limit])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    
    return [
        LeaderboardEntry(
            user_id=row[0],
            username=row[1],
            total_karma=row[2],
            rank=row[3]
        )
        for row in rows
    ]


# ============================================================================
# WHY WE DON'T STORE DAILY_KARMA ON USER
# ============================================================================
"""
Alternative (INCORRECT) approach:

class User(models.Model):
    daily_karma = models.IntegerField(default=0)  # WRONG!

Problems:
1. Race conditions: Two likes at once → one update lost
2. Time window: When do we reset? Midnight? Rolling 24h?
3. Timezone hell: Midnight in which timezone?
4. Historical queries impossible: "What was the leaderboard yesterday?"
5. Audit trail lost: Can't debug why karma is wrong

Our approach (KarmaEvent log):
1. Atomic: Each event is a separate row
2. Time-accurate: Rolling 24h window with exact timestamps
3. Timezone-safe: All timestamps in UTC
4. Historical: Can query any time range
5. Auditable: Every karma change is logged

The only downside is slightly slower leaderboard queries,
but with proper indexes, this is negligible for our scale.
"""
