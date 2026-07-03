"""
create_tables.py
Run this ONCE to create all database tables in your PostgreSQL instance.

Local:
    python create_tables.py

On Render (via Shell tab in your web service dashboard):
    python create_tables.py
"""

import os
from dotenv import load_dotenv
from database import get_connection

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS blogs (
    id         SERIAL       PRIMARY KEY,
    location   VARCHAR(255) NOT NULL,
    subject    VARCHAR(500) NOT NULL,
    text       TEXT         NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tags (
    id   SERIAL       PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    CONSTRAINT uq_tag_name UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS blog_tags (
    blog_id INTEGER NOT NULL REFERENCES blogs(id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
    PRIMARY KEY (blog_id, tag_id)
);

CREATE TABLE IF NOT EXISTS phone_clicks (
    id         SERIAL      PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phone_clicks_ip_date
    ON phone_clicks (ip_address, clicked_at);

CREATE TABLE IF NOT EXISTS enquiries (
    id           SERIAL      PRIMARY KEY,
    ip_address   VARCHAR(45) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_enquiries_ip_date
    ON enquiries (ip_address, submitted_at);
"""

def create_tables():
    print("Connecting to database...")
    conn = get_connection()
    try:
        cur = conn.cursor()
        print("Creating tables...")
        cur.execute(SQL)
        conn.commit()
        print("Done. All tables created successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_tables()
