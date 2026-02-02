"""
PHASE 2: Efficient Query Strategies
====================================

This module contains optimized query functions that avoid N+1 problems.

THE N+1 PROBLEM EXPLAINED:
--------------------------
Naive approach for 50 nested comments:
    post = Post.objects.get(id=1)           # 1 query
    for comment in post.comments.all():     # 1 query
        print(comment.author.username)      # 50 queries (N+1!)
        for reply in comment.replies.all(): # 50 more queries
            ...

Total: 1 + 1 + 50 + 50*replies = DISASTER

OUR APPROACH:
-------------
1. Fetch ALL comments for a post in ONE query
2. Use select_related for author (LEFT JOIN)
3. Build the tree in Python with O(n) single pass

This gives us: 1 query for post + 1 query for all comments = 2 queries total
Regardless of nesting depth!
"""

from typing import Optional
from django.db.models import Prefetch, Q
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from .models import Post, Comment, Like


def get_post_with_author(post_id: int) -> Optional[Post]:
    """
    Fetch a single post with its author.
    
    Query: 1 (with JOIN)
    
    SELECT post.*, user.* 
    FROM post 
    INNER JOIN user ON post.author_id = user.id 
    WHERE post.id = %s
    """
    return (
        Post.objects
        .select_related('author')
        .filter(id=post_id)
        .first()
    )


def get_all_comments_for_post(post_id: int) -> list[Comment]:
    """
    Fetch ALL comments for a post in a SINGLE query.
    
    This is the KEY to avoiding N+1.
    
    Query: 1 (with JOIN for author)
    
    SELECT comment.*, user.* 
    FROM comment 
    INNER JOIN user ON comment.author_id = user.id 
    WHERE comment.post_id = %s 
    ORDER BY comment.created_at
    
    WHY ORDER BY CREATED_AT:
    - Ensures consistent tree building
    - Parent always appears before children (in most cases)
    - Allows chronological display within threads
    """
    return list(
        Comment.objects
        .filter(post_id=post_id)
        .select_related('author')
        .order_by('created_at')
    )


def build_comment_tree(flat_comments: list[Comment]) -> list[dict]:
    """
    Build nested tree structure from flat list.
    
    Algorithm: O(n) single pass with hash map
    
    1. First pass: Create lookup dict {id -> node}
    2. Second pass: Attach children to parents
    
    Trade-off: 
    - Uses O(n) extra memory for the lookup dict
    - But avoids O(n^2) nested loops
    
    Example Input (flat):
        [Comment(id=1, parent=None), Comment(id=2, parent=1), Comment(id=3, parent=1)]
    
    Example Output (nested):
        [
            {
                'comment': Comment(id=1),
                'replies': [
                    {'comment': Comment(id=2), 'replies': []},
                    {'comment': Comment(id=3), 'replies': []}
                ]
            }
        ]
    """
    # Build lookup dict in O(n)
    nodes = {}
    for comment in flat_comments:
        nodes[comment.id] = {
            'comment': comment,
            'replies': []
        }
    
    # Build tree in O(n)
    root_nodes = []
    for comment in flat_comments:
        node = nodes[comment.id]
        if comment.parent_id is None:
            # Top-level comment
            root_nodes.append(node)
        else:
            # Child comment - attach to parent
            parent_node = nodes.get(comment.parent_id)
            if parent_node:
                parent_node['replies'].append(node)
            else:
                # Orphan comment (parent was deleted?) - treat as root
                # This is defensive programming for data integrity issues
                root_nodes.append(node)
    
    return root_nodes


def get_post_with_comment_tree(post_id: int) -> Optional[dict]:
    """
    Main entry point: Get post with fully nested comment tree.
    
    TOTAL QUERIES: 2
    - 1 for post + author
    - 1 for all comments + authors
    
    This function demonstrates the N+1 solution:
    Instead of fetching comments recursively (which would be O(depth) queries),
    we fetch ALL comments in one query and build the tree in Python.
    """
    post = get_post_with_author(post_id)
    if not post:
        return None
    
    flat_comments = get_all_comments_for_post(post_id)
    comment_tree = build_comment_tree(flat_comments)
    
    return {
        'post': post,
        'comments': comment_tree,
        'comment_count': len(flat_comments)
    }


def get_user_liked_items(user_id: int, post_id: int) -> dict:
    """
    Get all items (post + comments) that a user has liked for a given post.
    
    Used to show "liked" state in UI.
    
    Query: 1
    
    Returns: {
        'post_liked': bool,
        'liked_comment_ids': set[int]
    }
    
    WHY A SINGLE QUERY:
    - Fetches all likes for this user on this post's content
    - Frontend can then mark liked items without additional requests
    """
    post_ct = ContentType.objects.get_for_model(Post)
    comment_ct = ContentType.objects.get_for_model(Comment)
    
    # Get all comment IDs for this post
    comment_ids = list(
        Comment.objects
        .filter(post_id=post_id)
        .values_list('id', flat=True)
    )
    
    # Fetch all relevant likes in one query
    likes = Like.objects.filter(
        user_id=user_id
    ).filter(
        Q(content_type=post_ct, object_id=post_id) |
        Q(content_type=comment_ct, object_id__in=comment_ids)
    ).values_list('content_type_id', 'object_id')
    
    post_liked = False
    liked_comment_ids = set()
    
    for ct_id, obj_id in likes:
        if ct_id == post_ct.id and obj_id == post_id:
            post_liked = True
        elif ct_id == comment_ct.id:
            liked_comment_ids.add(obj_id)
    
    return {
        'post_liked': post_liked,
        'liked_comment_ids': liked_comment_ids
    }


def get_feed_posts(cursor=None, limit=20) -> list[Post]:
    """
    Fetch paginated feed posts.
    
    Using cursor pagination (created_at) instead of offset:
    - Offset is O(n) - has to skip rows
    - Cursor is O(1) - direct index seek
    
    Query uses index on (created_at DESC)
    """
    queryset = Post.objects.select_related('author')
    
    if cursor:
        queryset = queryset.filter(created_at__lt=cursor)
    
    return list(queryset[:limit])


# ============================================================================
# QUERY ANALYSIS
# ============================================================================
"""
EXAMPLE: Loading a post with 50 comments

OUR APPROACH (2 queries):
-------------------------
Query 1: SELECT * FROM post JOIN user WHERE post.id = 123
Query 2: SELECT * FROM comment JOIN user WHERE post_id = 123 ORDER BY created_at

Tree building: O(n) in Python

NAIVE APPROACH (potentially 100+ queries):
------------------------------------------
Query 1: SELECT * FROM post WHERE id = 123
Query 2: SELECT * FROM user WHERE id = post.author_id
Query 3: SELECT * FROM comment WHERE post_id = 123 AND parent_id IS NULL
For each comment:
    Query N: SELECT * FROM user WHERE id = comment.author_id
    Query N+1: SELECT * FROM comment WHERE parent_id = comment.id
    ... recursively

WHY WE DON'T USE RECURSIVE CTE:
-------------------------------
PostgreSQL supports recursive CTEs which could build the tree in SQL:

WITH RECURSIVE comment_tree AS (
    SELECT *, 0 as depth FROM comment WHERE post_id = 123 AND parent_id IS NULL
    UNION ALL
    SELECT c.*, ct.depth + 1 
    FROM comment c
    JOIN comment_tree ct ON c.parent_id = ct.id
)
SELECT * FROM comment_tree;

Trade-offs:
- CTE: Single query, but complex SQL, harder to test
- Our approach: 2 queries, simple SQL, easy to understand
- For 50-100 comments, Python tree building is negligible (<1ms)
- Would consider CTE for 10,000+ comments

CONCLUSION:
We chose the simpler approach because:
1. Easier to maintain and debug
2. Works with any database (not just PostgreSQL)
3. Performance is nearly identical for typical use cases
4. The code can be explained in an interview without whiteboard SQL
"""
