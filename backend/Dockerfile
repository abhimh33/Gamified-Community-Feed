# =============================================================================
# KarmaFeed Backend - Production Docker Image
# =============================================================================
# Multi-stage build for smaller final image
# Uses Python slim for minimal footprint (~150MB vs ~900MB for full)

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production - Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies only (libpq for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Collect static files (uses whitenoise in production)
RUN python manage.py collectstatic --no-input

# Switch to non-root user
USER appuser

# Expose port (Render uses $PORT environment variable)
EXPOSE 8000

# Set default port (Render overrides with $PORT)
ENV PORT=8000

# Default command - Gunicorn with production settings
# Uses shell form to expand $PORT variable (Render requirement)
CMD gunicorn karmafeed.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance
