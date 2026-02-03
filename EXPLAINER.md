# EXPLAINER.md

Technical deep-dive into the architecture decisions behind KarmaFeed.

---

## 1. Comment Tree Modeling

### Approach: Adjacency List

Each comment stores a reference to its parent via `parent_id`:

```python
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

### Why Adjacency List?

| Pattern | Pros | Cons |
|---------|------|------|
| **Adjacency List** ✓ | Simple schema, O(1) inserts, no tree maintenance | Recursive fetch or Python assembly |
| Materialized Path | Single query tree fetch, subtree queries | String manipulation, recompute on move |
| Nested Set | Fast subtree reads | Expensive writes, rebalancing required |

For a feed app where:
- Comments are written frequently
- Tree depth is typically shallow (3-5 levels)
- Full tree is always fetched per post

**Adjacency List** is ideal—no overhead on writes, tree assembled in Python.

---

## 2. Query Efficiency & N+1 Prevention

### Problem: N+1 Query Trap

Naive nested serializers cause one query per comment:

```python
# ❌ BAD: N+1 queries
for comment in comments:
    replies = comment.replies.all()  # Query per comment!
```

### Solution: Two-Query Assembly

Fetch all comments for a post in **one query**, then assemble the tree in Python:

```python
# ✅ GOOD: O(1) queries regardless of depth
comments = Comment.objects.filter(post=post).select_related('author').order_by('created_at')

# Build lookup dictionary
comment_map = {c.id: {**serializer(c), 'replies': []} for c in comments}

# Assemble tree in single pass
roots = []
for c in comments:
    if c.parent_id:
        comment_map[c.parent_id]['replies'].append(comment_map[c.id])
    else:
        roots.append(comment_map[c.id])
```

### Result

| Depth | Naive Approach | Our Approach |
|-------|---------------|--------------|
| 10 comments | 11 queries | 2 queries |
| 100 comments | 101 queries | 2 queries |
| 1000 comments | 1001 queries | 2 queries |

Fixed at **2 queries** for any tree size: one for comments, one for authors (via `select_related`).

---

## 3. Concurrency & Data Integrity

### Problem: Duplicate Likes

Two simultaneous requests to like the same post could create duplicate like records:

```
Request A: Check if like exists → No
Request B: Check if like exists → No
Request A: Create like → Success
Request B: Create like → Success (DUPLICATE!)
```

### Solution: Database Unique Constraint

```python
class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_post_like')
        ]
```

### Implementation Pattern

```python
def like_post(request, post_id):
    try:
        PostLike.objects.create(post_id=post_id, user=request.user)
        # Award karma via event sourcing
        KarmaEvent.objects.create(
            user=post.author,
            delta=5,
            reason='post_like',
            reference_id=post_id
        )
        return Response({'status': 'liked'}, status=201)
    except IntegrityError:
        # Constraint violation = already liked
        return Response({'error': 'Already liked'}, status=400)
```

### Why Not `get_or_create`?

- `get_or_create` still has a race window between check and create
- Unique constraint is **atomic at the database level**
- Cleaner error handling with explicit `IntegrityError` catch

---

## 4. Karma & Leaderboard Math

### Event Sourcing Pattern

Instead of storing a mutable `karma` field on User, we log immutable events:

```python
class KarmaEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    delta = models.IntegerField()  # +5 for post like, +1 for comment like
    reason = models.CharField(max_length=50)
    reference_id = models.IntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Karma Values

| Action | Karma Awarded |
|--------|---------------|
| Post receives a like | +5 to author |
| Comment receives a like | +1 to author |

### Leaderboard Query

Top 5 users by karma earned in the last 24 hours:

```python
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

def get_leaderboard():
    cutoff = timezone.now() - timedelta(hours=24)
    
    return (
        KarmaEvent.objects
        .filter(created_at__gte=cutoff)
        .values('user__username')
        .annotate(total_karma=Sum('delta'))
        .order_by('-total_karma')[:5]
    )
```

### Why Event Sourcing?

| Approach | Pros | Cons |
|----------|------|------|
| Mutable field | Simple reads | Lost history, concurrent update bugs |
| **Event sourcing** ✓ | Full audit trail, time-windowed queries, no race conditions | Aggregation on read |

For a leaderboard that needs **rolling 24-hour windows**, event sourcing is the natural fit.

---

## 5. Deployment & Docker (Bonus)

### Multi-Stage Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run startup script
CMD ["./start.sh"]
```

### Startup Script (`start.sh`)

```bash
#!/bin/bash
set -e

# Run migrations
python manage.py migrate

# Seed demo data if database is empty
python manage.py shell -c "
from feed.models import Post
if not Post.objects.exists():
    from django.core.management import call_command
    call_command('seed_data')
"

# Start Gunicorn
exec gunicorn karmafeed.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --timeout 120
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | False in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |

---

## 6. AI Audit

### Bug Found by AI: Hardcoded API URL in CreatePost

**Location**: `frontend/src/components/CreatePost.js`

**Original Code (Buggy)**:

```javascript
const response = await fetch('/api/posts/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(postData)
});
```

**Problem**: When deployed to Vercel, the frontend is served from `gamified-community-feed.vercel.app` but the API lives at `karmafeed-backend.onrender.com`. The hardcoded `/api` path causes requests to go to the wrong origin.

**Fix Applied**:

```javascript
const API_BASE = process.env.REACT_APP_API_URL || '';

const response = await fetch(`${API_BASE}/api/posts/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(postData)
});
```

**Why This Matters**: This pattern (environment-based API URL) ensures:
- Local development works with proxy (`REACT_APP_API_URL` unset)
- Production points to the deployed backend
- No code changes needed between environments

---

## Summary

| Concept | Decision | Rationale |
|---------|----------|-----------|
| Comment Tree | Adjacency List | Simple writes, Python assembly is fast enough |
| N+1 Prevention | Two-query fetch + Python tree build | O(1) query complexity |
| Like Safety | Unique constraint + IntegrityError | Database-level atomicity |
| Karma | Event sourcing | Time-windowed leaderboard, audit trail |
| Deployment | Docker + Render + Vercel | Zero-config scaling, managed PostgreSQL |
