"""
Database configuration and connection helper.
Update the credentials below to match your PostgreSQL setup.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "face_recognition_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def get_connection():
    """Return a new psycopg2 connection using the shared config."""
    return psycopg2.connect(**DB_CONFIG)
