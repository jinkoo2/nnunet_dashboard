import sqlite3
import os
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS workers (
                id                  TEXT PRIMARY KEY,
                name                TEXT UNIQUE NOT NULL,
                hostname            TEXT,
                cpu_cores           INTEGER,
                gpu_memory_gb       REAL,
                gpu_name            TEXT,
                system_memory_gb    REAL,
                description         TEXT,
                registered_at       TEXT,
                last_heartbeat      TEXT,
                status              TEXT DEFAULT 'offline'
            );

            CREATE TABLE IF NOT EXISTS datasets (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                submitted_by    TEXT,
                submitted_at    TEXT,
                zip_path        TEXT,
                has_plan        INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS training_jobs (
                id              TEXT PRIMARY KEY,
                dataset_id      TEXT NOT NULL REFERENCES datasets(id),
                worker_id       TEXT REFERENCES workers(id),
                configuration   TEXT,
                status          TEXT DEFAULT 'pending',
                created_at      TEXT,
                started_at      TEXT,
                completed_at    TEXT,
                error_message   TEXT
            );

            CREATE TABLE IF NOT EXISTS preprocessing_progress (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id                  TEXT NOT NULL REFERENCES training_jobs(id),
                total_images            INTEGER,
                done_images             INTEGER,
                mean_time_per_image_s   REAL,
                reported_at             TEXT
            );

            CREATE TABLE IF NOT EXISTS training_progress (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id          TEXT NOT NULL REFERENCES training_jobs(id),
                fold            INTEGER,
                epoch           INTEGER,
                learning_rate   REAL,
                train_loss      REAL,
                val_loss        REAL,
                pseudo_dice     TEXT,
                epoch_time_s    REAL,
                reported_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS validation_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id          TEXT NOT NULL REFERENCES training_jobs(id),
                fold            INTEGER,
                summary_json    TEXT,
                reported_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS models (
                id              TEXT PRIMARY KEY,
                job_id          TEXT NOT NULL REFERENCES training_jobs(id),
                dataset_id      TEXT NOT NULL REFERENCES datasets(id),
                zip_path        TEXT,
                status          TEXT DEFAULT 'pending_approval',
                description     TEXT,
                approved_by     TEXT,
                approved_at     TEXT,
                created_at      TEXT
            );

            CREATE TABLE IF NOT EXISTS worker_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id   TEXT,
                worker_name TEXT,
                level       TEXT DEFAULT 'INFO',
                message     TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS uploads (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                submitted_by    TEXT,
                total_chunks    INTEGER NOT NULL,
                total_size      INTEGER,
                received_chunks TEXT DEFAULT '[]',
                created_at      TEXT,
                status          TEXT DEFAULT 'in_progress'
            );
        """)
        conn.commit()
        # Migrations: add columns to existing tables if absent
        try:
            conn.execute("ALTER TABLE workers ADD COLUMN system_memory_gb REAL")
            conn.commit()
            logger.info("Migration: added system_memory_gb to workers")
        except Exception:
            pass  # column already exists
        logger.info("Database initialized successfully")
    finally:
        conn.close()
