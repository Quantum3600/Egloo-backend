# Dockerfile

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user and prepare data directory
RUN adduser --disabled-password --gecos "" egloo \
    && mkdir -p /app/data \
    && chown -R egloo:egloo /app
USER egloo

# Expose port
EXPOSE 8000

# Health check for Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command — can be overridden in docker-compose.yml
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1"
