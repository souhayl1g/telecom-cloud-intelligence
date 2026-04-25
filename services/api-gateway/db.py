import psycopg2
from contextlib import contextmanager
from config import DATABASE_URL


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)


@contextmanager
def _db():
    """Open a psycopg2 connection, commit on success, rollback on error, always close."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
