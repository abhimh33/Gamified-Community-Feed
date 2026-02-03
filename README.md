# KarmaFeed

A Community Feed application with nested threaded comments, likes with karma rewards, and a real-time leaderboard.

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React SPA     │────▶│   Django DRF    │────▶│   PostgreSQL    │
│   (Tailwind)    │◀────│   (REST API)    │◀────│   (Database)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Key Features

- **Posts**: Create and view posts
- **Nested Comments**: Reddit-style threaded comments (unlimited depth)
- **Likes**: Like posts (+5 karma) and comments (+1 karma)
- **Leaderboard**: Top 5 users by karma in last 24 hours

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend Setup

```powershell
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env  # Then edit with your DB credentials

# Create database
# In PostgreSQL:
# CREATE DATABASE karmafeed;

# Run migrations
python manage.py migrate

# Create test data (optional)
python manage.py seed_data

# Run server
python manage.py runserver
```

### Frontend Setup

```powershell
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The app will be available at http://localhost:3000

## 🐳 Docker Setup (Alternative)

Run the backend with Docker Compose (includes PostgreSQL):

```powershell
# Build and start containers
docker-compose up --build

# API available at http://localhost:8000
# Demo user: testuser / testpass
```

For production (Render), the Dockerfile uses multi-stage builds with Gunicorn (2 workers, 4 threads).

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/feed/` | Paginated feed of posts |
| POST | `/api/posts/` | Create a post |
| GET | `/api/posts/<id>/` | Post detail with comments |
| POST | `/api/posts/<id>/comments/` | Create comment |
| POST | `/api/posts/<id>/like/` | Like a post |
| DELETE | `/api/posts/<id>/like/` | Unlike a post |
| POST | `/api/comments/<id>/like/` | Like a comment |
| GET | `/api/leaderboard/` | Top 5 karma leaders |

## 🧪 Running Tests

```powershell
# Backend tests
cd backend
python manage.py test

# Specific test
python manage.py test feed.tests.test_leaderboard
```

## 📊 Performance Considerations

### N+1 Query Prevention

Loading 50 nested comments uses **exactly 2 queries**:
1. Post with author (JOIN)
2. All comments for post (single query + Python tree building)

See [EXPLAINER.md](EXPLAINER.md) for details.

### Concurrency

Likes are protected against duplicates via:
- Unique constraint at database level
- `IntegrityError` handling for race conditions

### Leaderboard

Computed dynamically from `KarmaEvent` table:
- No stored counters (correctness > performance)
- Uses index on `(created_at, recipient_id)`
- Time-windowed aggregation

## 📁 Project Structure

```
KarmaFeed/
├── backend/
│   ├── karmafeed/          # Django project
│   │   ├── settings.py
│   │   └── urls.py
│   ├── feed/               # Main app
│   │   ├── models.py       # Data models
│   │   ├── views.py        # API views
│   │   ├── serializers.py  # DRF serializers
│   │   ├── services.py     # Business logic
│   │   ├── queries.py      # Optimized queries
│   │   └── leaderboard.py  # Leaderboard logic
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── api.js          # API client
│   │   └── App.js          # Main component
│   └── package.json
├── README.md
├── EXPLAINER.md
└── docker-compose.yml
```

## 🎯 Design Decisions

| Decision | Choice | Trade-off |
|----------|--------|-----------|
| Comment tree | Adjacency List | Simple ORM, O(n) Python assembly |
| Like storage | ContentType (polymorphic) | Unified karma aggregation |
| Karma tracking | Event log (append-only) | More storage, always correct |
| Pagination | Cursor-based | No random access, but O(1) |

## 📝 License

MIT
