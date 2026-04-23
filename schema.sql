-- ============================================================
-- Face Recognition System — Database Schema
-- ============================================================
-- Run this AFTER creating the database:
--   CREATE DATABASE face_recognition_db;
--   \c face_recognition_db
-- Then execute this file:
--   \i schema.sql
-- ============================================================

DROP TABLE IF EXISTS user_profiles;
CREATE TABLE user_profiles (
    id                      SERIAL PRIMARY KEY,

    -- Personal Info
    full_name               VARCHAR(150)    NOT NULL,
    date_of_birth           DATE,
    gender                  VARCHAR(20),
    blood_group             VARCHAR(10),
    nationality             VARCHAR(50),

    -- ID Card Info
    national_id             VARCHAR(50)     UNIQUE,
    employee_id             VARCHAR(50)     UNIQUE,

    -- Organization
    designation             VARCHAR(100),
    department              VARCHAR(100),

    -- Contact
    phone                   VARCHAR(20),
    email                   VARCHAR(150)    UNIQUE,
    address                 TEXT,

    -- Emergency Contact
    emergency_contact_name  VARCHAR(150),
    emergency_contact_phone VARCHAR(20),

    -- Media
    profile_photo_path      TEXT,

    -- Biometric (128-d face encoding vector)
    face_encoding           DOUBLE PRECISION[] NOT NULL,

    -- Timestamps
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_employee_id ON user_profiles(employee_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_national_id ON user_profiles(national_id);

CREATE TABLE IF NOT EXISTS threat_events (
    id              SERIAL PRIMARY KEY,
    detected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    threat_type     VARCHAR(50) NOT NULL,        -- 'knife', 'scissors'
    confidence      DECIMAL(5,4),                -- detection confidence
    user_profile_id INTEGER REFERENCES user_profiles(id), -- NULL if unknown
    person_name     VARCHAR(150),                -- 'Unknown' if not identified
    snapshot_path   TEXT,                         -- path to saved image
    alert_sent      BOOLEAN DEFAULT FALSE,       -- was WhatsApp alert sent?
    notes           TEXT
);
