"""Database connection helper for pipeline-worker."""
import psycopg2
from worker.config import DATABASE_URL


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)
