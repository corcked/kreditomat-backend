FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first
COPY pyproject.toml ./
COPY requirements.txt ./

# Update pip and setuptools
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies from requirements.txt instead of editable install
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
# Copy README.md if it exists
COPY README.md* ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Set environment variable for port
ENV PORT=8000

# Run database migrations and start the application
CMD ["./scripts/start.sh"]