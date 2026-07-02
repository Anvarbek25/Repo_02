"""
database.py
Manages MySQL connection pooling for the Bahafix API.
"""

import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
import os

load_dotenv()

# Connection pool — keeps a set of reusable connections open
# so each request doesn't have to open and close a new one
_pool = pooling.MySQLConnectionPool(
    pool_name="bahafix_pool",
    pool_size=5,
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    database=os.getenv("DB_NAME", "bahafix"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    autocommit=False,
    charset="utf8mb4",
)


def get_connection():
    """
    Returns a connection from the pool.
    Always use this inside a 'with' block or try/finally
    to ensure the connection is returned to the pool.

    Usage:
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            ...
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()  # returns to pool, does not actually close
    """
    return _pool.get_connection()
