"""
database.py
PostgreSQL connection management for the Bahafix API.

Uses a simple connection-per-request pattern with psycopg2.
Render's managed PostgreSQL requires SSL — handled automatically
via the sslmode=require parameter appended to the DATABASE_URL.

Usage in any endpoint:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT ...")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """
    Returns a new psycopg2 connection to the PostgreSQL database.

    - Reads DATABASE_URL from environment variables.
    - Appends sslmode=require for Render compatibility.
    - Uses RealDictCursor so rows are returned as dicts (column: value)
      rather than tuples — making the code more readable.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    # Render's DATABASE_URL sometimes uses 'postgres://' prefix.
    # psycopg2 requires 'postgresql://' — fix it if needed.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # Append SSL requirement for Render (ignored if already present)
    if "sslmode" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return psycopg2.connect(
        database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
