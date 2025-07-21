web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
release: alembic upgrade head && python scripts/seed_data.py