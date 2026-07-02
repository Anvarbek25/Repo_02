-- ============================================================
-- Bahafix Backend — MySQL Database Schema
-- Run this file once to set up all tables
-- ============================================================

CREATE DATABASE IF NOT EXISTS bahafix
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE bahafix;

-- ─── Blogs ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Blogs (
    id         INT          NOT NULL AUTO_INCREMENT,
    location   VARCHAR(255) NOT NULL,
    subject    VARCHAR(500) NOT NULL,
    text       LONGTEXT     NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT (CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne')),
    updated_at DATETIME     NOT NULL DEFAULT (CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne'))
                                     ON UPDATE (CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne')),
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- ─── Tags ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Tags (
    id   INT          NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tag_name (name)
) ENGINE=InnoDB;

-- ─── BlogTags (junction) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS BlogTags (
    blog_id INT NOT NULL,
    tag_id  INT NOT NULL,
    PRIMARY KEY (blog_id, tag_id),
    CONSTRAINT fk_blogtags_blog FOREIGN KEY (blog_id) REFERENCES Blogs(id) ON DELETE CASCADE,
    CONSTRAINT fk_blogtags_tag  FOREIGN KEY (tag_id)  REFERENCES Tags(id)  ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─── PhoneClicks ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS PhoneClicks (
    id         INT         NOT NULL AUTO_INCREMENT,
    ip_address VARCHAR(45) NOT NULL,
    clicked_at DATETIME    NOT NULL DEFAULT (CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne')),
    PRIMARY KEY (id),
    INDEX idx_phoneclicks_ip_date (ip_address, clicked_at)
) ENGINE=InnoDB;

-- ─── Enquiries ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Enquiries (
    id           INT          NOT NULL AUTO_INCREMENT,
    name         VARCHAR(255) NOT NULL,
    phone        VARCHAR(50)  NOT NULL,
    email        VARCHAR(255) NOT NULL,
    message      VARCHAR(400) NOT NULL,
    ip_address   VARCHAR(45)  NOT NULL,
    submitted_at DATETIME     NOT NULL DEFAULT (CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne')),
    sent_at      DATETIME     NULL,
    PRIMARY KEY (id),
    INDEX idx_enquiries_sent    (sent_at),
    INDEX idx_enquiries_ip_date (ip_address, submitted_at)
) ENGINE=InnoDB;
