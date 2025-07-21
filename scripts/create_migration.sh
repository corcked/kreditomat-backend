#!/bin/bash
# Script to create database migrations

set -e

echo "Creating database migration..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create migration
alembic revision --autogenerate -m "$1"

echo "Migration created successfully!"
echo "To apply migrations, run: alembic upgrade head"