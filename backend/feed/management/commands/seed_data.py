"""
Management command to seed the database with sample data.

Usage: python manage.py seed_data
"""

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from feed.models import Post, Comment, Like, KarmaEvent, KARMA_POST_LIKE, KARMA_COMMENT_LIKE
from feed.services import like_post, like_comment


class Command(BaseCommand):
    help = 'Seed the database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create'
        )
        parser.add_argument(
            '--posts',
            type=int,
            default=20,
            help='Number of posts to create'
        )
        parser.add_argument(
            '--comments',
            type=int,
            default=100,
            help='Number of comments to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            KarmaEvent.objects.all().delete()
            Like.objects.all().delete()
            Comment.objects.all().delete()
            Post.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        self.stdout.write('Creating users...')
        users = self._create_users(options['users'])
        
        self.stdout.write('Creating posts...')
        posts = self._create_posts(users, options['posts'])
        
        self.stdout.write('Creating comments...')
        comments = self._create_comments(users, posts, options['comments'])
        
        self.stdout.write('Creating likes...')
        self._create_likes(users, posts, comments)
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully created:\n'
            f'  - {len(users)} users\n'
            f'  - {len(posts)} posts\n'
            f'  - {len(comments)} comments\n'
            f'  - Likes and karma events'
        ))

    def _create_users(self, count):
        users = []
        for i in range(count):
            username = f'user{i+1}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@example.com',
                    password='password123'
                )
                users.append(user)
            else:
                users.append(User.objects.get(username=username))
        return users

    def _create_posts(self, users, count):
        posts = []
        titles = [
            "Just discovered this amazing trick!",
            "What do you think about...",
            "Help needed with a problem",
            "Check out my latest project",
            "Unpopular opinion:",
            "TIL something interesting",
            "Discussion: Best practices for",
            "Weekly roundup",
            "Question for the community",
            "Sharing my experience with",
        ]
        
        contents = [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "I've been working on this for a while and wanted to share my thoughts with the community.",
            "Has anyone else experienced this? I'd love to hear your perspectives.",
            "This might be controversial, but I think we need to discuss this more openly.",
            "Here's what I learned after years of experience in this field.",
        ]
        
        for i in range(count):
            post = Post.objects.create(
                author=random.choice(users),
                title=f"{random.choice(titles)} #{i+1}",
                content=random.choice(contents) + f"\n\nPost #{i+1}",
                created_at=timezone.now() - timedelta(hours=random.randint(0, 48))
            )
            posts.append(post)
        return posts

    def _create_comments(self, users, posts, count):
        comments = []
        comment_texts = [
            "Great point! I totally agree.",
            "Hmm, I'm not sure about this...",
            "Thanks for sharing!",
            "Can you elaborate on this?",
            "This is exactly what I was looking for.",
            "I have a different perspective on this.",
            "Interesting take, but have you considered...",
            "Well said!",
            "+1 to this",
            "This deserves more attention.",
        ]
        
        for i in range(count):
            post = random.choice(posts)
            
            # 30% chance of being a reply to existing comment
            parent = None
            depth = 0
            existing_comments = [c for c in comments if c.post_id == post.id]
            if existing_comments and random.random() < 0.3:
                parent = random.choice(existing_comments)
                depth = min(parent.depth + 1, 6)  # Cap depth at 6
            
            comment = Comment.objects.create(
                post=post,
                author=random.choice(users),
                parent=parent,
                content=random.choice(comment_texts),
                depth=depth,
                created_at=timezone.now() - timedelta(hours=random.randint(0, 24))
            )
            comments.append(comment)
        
        return comments

    def _create_likes(self, users, posts, comments):
        # Like 50% of posts
        for post in posts:
            likers = random.sample(users, k=min(len(users)//2, len(users)))
            for liker in likers:
                if liker.id != post.author_id:  # Don't self-like
                    try:
                        like_post(liker, post.id)
                    except Exception:
                        pass  # Ignore duplicates
        
        # Like 30% of comments
        for comment in comments:
            if random.random() < 0.3:
                likers = random.sample(users, k=min(3, len(users)))
                for liker in likers:
                    if liker.id != comment.author_id:
                        try:
                            like_comment(liker, comment.id)
                        except Exception:
                            pass
