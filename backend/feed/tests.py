"""
Tests for KarmaFeed

Focus areas:
1. Leaderboard correctness (time-windowed karma)
2. Like concurrency (no duplicates)
3. Comment tree building (no N+1)
"""

from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext

from .models import Post, Comment, Like, KarmaEvent, KARMA_POST_LIKE, KARMA_COMMENT_LIKE
from .services import like_post, like_comment, unlike_post
from .leaderboard import get_leaderboard, get_user_karma
from .queries import get_all_comments_for_post, build_comment_tree, get_post_with_comment_tree


class LeaderboardTestCase(TestCase):
    """
    Test the leaderboard calculation.
    
    CRITICAL: These tests verify that:
    1. Only karma from the last 24 hours counts
    2. Post likes = +5 karma, Comment likes = +1 karma
    3. Ordering is correct
    """
    
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user('user1', 'u1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'u2@test.com', 'pass')
        self.user3 = User.objects.create_user('user3', 'u3@test.com', 'pass')
        self.liker = User.objects.create_user('liker', 'l@test.com', 'pass')
        
        # Create a post for each user
        self.post1 = Post.objects.create(author=self.user1, title='Post 1', content='Content ' * 10)
        self.post2 = Post.objects.create(author=self.user2, title='Post 2', content='Content ' * 10)
        self.post3 = Post.objects.create(author=self.user3, title='Post 3', content='Content ' * 10)
    
    def test_leaderboard_empty_when_no_karma(self):
        """Leaderboard should be empty if no likes exist."""
        leaderboard = get_leaderboard()
        self.assertEqual(len(leaderboard), 0)
    
    def test_post_like_gives_5_karma(self):
        """Liking a post should give author +5 karma."""
        like_post(self.liker, self.post1.id)
        
        karma = get_user_karma(self.user1.id)
        self.assertEqual(karma, KARMA_POST_LIKE)  # Should be 5
    
    def test_comment_like_gives_1_karma(self):
        """Liking a comment should give author +1 karma."""
        comment = Comment.objects.create(
            post=self.post1,
            author=self.user2,
            content='Test comment'
        )
        like_comment(self.liker, comment.id)
        
        karma = get_user_karma(self.user2.id)
        self.assertEqual(karma, KARMA_COMMENT_LIKE)  # Should be 1
    
    def test_leaderboard_ordering(self):
        """
        Users should be ordered by total karma descending.
        
        Setup:
        - user1: 2 post likes = 10 karma
        - user2: 1 post like = 5 karma
        - user3: 0 likes = 0 karma
        """
        # user1 gets 2 post likes (10 karma)
        like_post(self.liker, self.post1.id)
        
        # Create another post for user1
        post1b = Post.objects.create(author=self.user1, title='Post 1b', content='C' * 20)
        like_post(self.user2, post1b.id)
        
        # user2 gets 1 post like (5 karma)
        like_post(self.liker, self.post2.id)
        
        leaderboard = get_leaderboard()
        
        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[0]['username'], 'user1')
        self.assertEqual(leaderboard[0]['total_karma'], 10)
        self.assertEqual(leaderboard[1]['username'], 'user2')
        self.assertEqual(leaderboard[1]['total_karma'], 5)
    
    def test_old_karma_not_counted(self):
        """
        Karma older than 24 hours should not count.
        
        This is THE critical test for the time window requirement.
        """
        # Create a karma event in the past (25 hours ago)
        old_time = timezone.now() - timedelta(hours=25)
        
        # We need to manually create the KarmaEvent with old timestamp
        # (normally this happens through like_post)
        from django.contrib.contenttypes.models import ContentType
        post_ct = ContentType.objects.get_for_model(Post)
        
        KarmaEvent.objects.create(
            recipient=self.user1,
            actor=self.liker,
            event_type=KarmaEvent.EventType.POST_LIKED,
            karma_delta=KARMA_POST_LIKE,
            content_type=post_ct,
            object_id=self.post1.id,
            created_at=old_time  # 25 hours ago
        )
        
        # Old karma should NOT be counted
        karma = get_user_karma(self.user1.id, hours=24)
        self.assertEqual(karma, 0)
        
        # But should be counted with larger window
        karma_48h = get_user_karma(self.user1.id, hours=48)
        self.assertEqual(karma_48h, KARMA_POST_LIKE)
    
    def test_leaderboard_limit(self):
        """Leaderboard should respect the limit parameter."""
        # Create 10 users with karma
        for i in range(10):
            user = User.objects.create_user(f'test{i}', f't{i}@test.com', 'pass')
            post = Post.objects.create(author=user, title=f'P{i}', content='C' * 20)
            like_post(self.liker, post.id)
        
        leaderboard = get_leaderboard(limit=5)
        self.assertEqual(len(leaderboard), 5)
    
    def test_self_like_no_karma(self):
        """Liking your own content should not give karma."""
        # user1 likes their own post
        like_post(self.user1, self.post1.id)
        
        karma = get_user_karma(self.user1.id)
        self.assertEqual(karma, 0)  # No karma for self-like


class LikeConcurrencyTestCase(TransactionTestCase):
    """
    Test like concurrency protection.
    
    These tests verify that:
    1. Duplicate likes are prevented
    2. IntegrityError is handled gracefully
    """
    
    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.author = User.objects.create_user('author', 'a@test.com', 'pass')
        self.post = Post.objects.create(author=self.author, title='Test', content='Content ' * 10)
    
    def test_cannot_like_twice(self):
        """Second like on same post should fail gracefully."""
        result1 = like_post(self.user, self.post.id)
        result2 = like_post(self.user, self.post.id)
        
        self.assertEqual(result1.action, 'created')
        self.assertEqual(result2.action, 'already_exists')
        self.assertFalse(result2.success)
        
        # Only one like should exist
        from django.contrib.contenttypes.models import ContentType
        post_ct = ContentType.objects.get_for_model(Post)
        like_count = Like.objects.filter(
            user=self.user,
            content_type=post_ct,
            object_id=self.post.id
        ).count()
        self.assertEqual(like_count, 1)
    
    def test_like_unlike_like(self):
        """Like → Unlike → Like should work."""
        result1 = like_post(self.user, self.post.id)
        self.assertEqual(result1.action, 'created')
        
        result2 = unlike_post(self.user, self.post.id)
        self.assertEqual(result2.action, 'removed')
        
        result3 = like_post(self.user, self.post.id)
        self.assertEqual(result3.action, 'created')
    
    def test_like_count_updated_atomically(self):
        """Like count should be updated with F() expression."""
        initial_count = self.post.like_count
        
        like_post(self.user, self.post.id)
        
        self.post.refresh_from_db()
        self.assertEqual(self.post.like_count, initial_count + 1)
        
        unlike_post(self.user, self.post.id)
        
        self.post.refresh_from_db()
        self.assertEqual(self.post.like_count, initial_count)


class CommentTreeTestCase(TestCase):
    """
    Test comment tree building.
    
    CRITICAL: Verify N+1 prevention.
    """
    
    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.post = Post.objects.create(author=self.user, title='Test', content='Content ' * 10)
    
    def test_tree_building_single_level(self):
        """Flat comments should be returned as separate trees."""
        c1 = Comment.objects.create(post=self.post, author=self.user, content='Comment 1')
        c2 = Comment.objects.create(post=self.post, author=self.user, content='Comment 2')
        
        flat = get_all_comments_for_post(self.post.id)
        tree = build_comment_tree(flat)
        
        self.assertEqual(len(tree), 2)
        self.assertEqual(tree[0]['comment'].id, c1.id)
        self.assertEqual(tree[1]['comment'].id, c2.id)
    
    def test_tree_building_nested(self):
        """Nested comments should be in replies array."""
        c1 = Comment.objects.create(post=self.post, author=self.user, content='Comment 1', depth=0)
        c2 = Comment.objects.create(post=self.post, author=self.user, content='Reply to 1', parent=c1, depth=1)
        c3 = Comment.objects.create(post=self.post, author=self.user, content='Reply to reply', parent=c2, depth=2)
        
        flat = get_all_comments_for_post(self.post.id)
        tree = build_comment_tree(flat)
        
        self.assertEqual(len(tree), 1)  # One root
        self.assertEqual(tree[0]['comment'].id, c1.id)
        self.assertEqual(len(tree[0]['replies']), 1)  # One reply
        self.assertEqual(tree[0]['replies'][0]['comment'].id, c2.id)
        self.assertEqual(len(tree[0]['replies'][0]['replies']), 1)  # Nested reply
    
    def test_no_n_plus_one_queries(self):
        """
        Loading 50 comments must NOT cause 50 queries.
        
        This is THE critical performance test.
        """
        # Create 50 comments (mix of depths)
        parent = None
        for i in range(50):
            if i % 5 == 0:
                # New thread
                parent = Comment.objects.create(
                    post=self.post, 
                    author=self.user, 
                    content=f'Comment {i}',
                    depth=0
                )
            else:
                # Reply
                Comment.objects.create(
                    post=self.post, 
                    author=self.user, 
                    content=f'Reply {i}',
                    parent=parent,
                    depth=1
                )
        
        # Now fetch and count queries
        with CaptureQueriesContext(connection) as context:
            result = get_post_with_comment_tree(self.post.id)
        
        # Should be exactly 2 queries:
        # 1. Post with author
        # 2. All comments with authors
        query_count = len(context)
        
        self.assertLessEqual(query_count, 3, 
            f"Expected ≤3 queries, got {query_count}. Queries: {[q['sql'][:100] for q in context]}")
        
        # Verify we got all comments
        self.assertEqual(result['comment_count'], 50)


class KarmaEventTestCase(TestCase):
    """Test karma event creation."""
    
    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pass')
        self.author = User.objects.create_user('author', 'a@test.com', 'pass')
        self.post = Post.objects.create(author=self.author, title='Test', content='C' * 20)
    
    def test_karma_event_created_on_like(self):
        """Liking should create a KarmaEvent."""
        initial_count = KarmaEvent.objects.count()
        
        like_post(self.user, self.post.id)
        
        self.assertEqual(KarmaEvent.objects.count(), initial_count + 1)
        
        event = KarmaEvent.objects.latest('created_at')
        self.assertEqual(event.recipient, self.author)
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.karma_delta, KARMA_POST_LIKE)
    
    def test_no_karma_event_for_self_like(self):
        """Self-likes should not create karma events."""
        # Author likes their own post
        like_post(self.author, self.post.id)
        
        events = KarmaEvent.objects.filter(recipient=self.author)
        self.assertEqual(events.count(), 0)
