import sqlite3
import os
from pathlib import Path


def get_db_path():
    """Get the database path in user's app data folder"""
    app_data = Path.home() / ".uniquest"
    app_data.mkdir(exist_ok=True)
    return str(app_data / "uniquest.db")


def get_connection():
    """Get a database connection"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # Better performance
    return conn


def initialize_database():
    """Create all tables if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()

    # Projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'idle',
            similarity_threshold REAL DEFAULT 0.70,
            storage_mode TEXT DEFAULT 'reference'
        )
    """)

    # Files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            original_path TEXT NOT NULL,
            stored_path TEXT,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            storage_mode TEXT DEFAULT 'reference',
            status TEXT DEFAULT 'pending',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            text_extracted INTEGER DEFAULT 0,
            images_extracted INTEGER DEFAULT 0,
            error_message TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Extracted text chunks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS text_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            chunk_index INTEGER DEFAULT 0,
            content TEXT NOT NULL,
            page_number INTEGER DEFAULT 0,
            chunk_type TEXT DEFAULT 'paragraph',
            word_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        )
    """)

    # Extracted images table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extracted_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            image_index INTEGER DEFAULT 0,
            stored_path TEXT NOT NULL,
            page_number INTEGER DEFAULT 0,
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            phash TEXT,
            ahash TEXT,
            dhash TEXT,
            file_size INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        )
    """)

    # Text similarity results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS text_similarities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            chunk_id_a INTEGER NOT NULL,
            chunk_id_b INTEGER NOT NULL,
            file_id_a INTEGER NOT NULL,
            file_id_b INTEGER NOT NULL,
            similarity_score REAL NOT NULL,
            reviewed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (chunk_id_a) REFERENCES text_chunks(id) ON DELETE CASCADE,
            FOREIGN KEY (chunk_id_b) REFERENCES text_chunks(id) ON DELETE CASCADE
        )
    """)

    # Image similarity results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_similarities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            image_id_a INTEGER NOT NULL,
            image_id_b INTEGER NOT NULL,
            file_id_a INTEGER NOT NULL,
            file_id_b INTEGER NOT NULL,
            similarity_score REAL NOT NULL,
            hash_distance INTEGER DEFAULT 0,
            reviewed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (image_id_a) REFERENCES extracted_images(id) ON DELETE CASCADE,
            FOREIGN KEY (image_id_b) REFERENCES extracted_images(id) ON DELETE CASCADE
        )
    """)

    # Tags table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#4A9EFF',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Analysis runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT DEFAULT 'running',
            files_processed INTEGER DEFAULT 0,
            text_similarities_found INTEGER DEFAULT 0,
            image_similarities_found INTEGER DEFAULT 0,
            error_message TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert default settings
    default_settings = [
        ("theme", "dark"),
        ("text_similarity_threshold", "0.70"),
        ("image_similarity_threshold", "0.85"),
        ("default_storage_mode", "reference"),
        ("export_path", str(Path.home() / "Documents")),
        ("app_version", "1.0.0"),
    ]

    for key, value in default_settings:
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
        """, (key, value))

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at: {get_db_path()}")


def get_setting(key: str, default=None):
    """Get a setting value"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    """Set a setting value"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (key, value))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_database()