-- ============================================================
-- Bahafix Backend v2.0 — PostgreSQL Schema
-- Run once against your Render PostgreSQL instance to create all tables.
--
-- How to run on Render:
--   psql "<your DATABASE_URL>" -f schema.sql
-- ============================================================

-- Set timezone for this session
SET timezone = 'Australia/Melbourne';

-- ─── blogs ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blogs (
    id         SERIAL       PRIMARY KEY,
    location   VARCHAR(255) NOT NULL,
    subject    VARCHAR(500) NOT NULL,
    text       TEXT         NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─── tags ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tags (
    id   SERIAL       PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    CONSTRAINT uq_tag_name UNIQUE (name)
);

-- ─── blog_tags (junction) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS blog_tags (
    blog_id INTEGER NOT NULL REFERENCES blogs(id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
    PRIMARY KEY (blog_id, tag_id)
);

-- ─── phone_clicks ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phone_clicks (
    id         SERIAL      PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phone_clicks_ip_date
    ON phone_clicks (ip_address, clicked_at);

-- ─── enquiries ───────────────────────────────────────────────
-- Privacy note: No PII stored. Name/phone/email/message are
-- sent via email immediately and never persisted here.
CREATE TABLE IF NOT EXISTS enquiries (
    id           SERIAL      PRIMARY KEY,
    ip_address   VARCHAR(45) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_enquiries_ip_date
    ON enquiries (ip_address, submitted_at);
