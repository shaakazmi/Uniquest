"""
SQLite database manager for Uniquest.
Bulletproof — includes every function used anywhere in the app.
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


# ═════════════════════════════════════════════
# DATABASE LOCATION
# ═════════════════════════════════════════════

DB_DIR  = Path.home() / ".uniquest"
DB_PATH = DB_DIR / "uniquest.db"


def get_db_path() -> str:
    return str(DB_PATH)


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ═════════════════════════════════════════════
# INITIALIZATION
# ═════════════════════════════════════════════

def init_db() -> None:
    """Create all tables if they don't exist. Safe to run multiple times."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        # ── Core tables (no indexes yet) ──────────────────────────────
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                name                 TEXT NOT NULL,
                description          TEXT DEFAULT '',
                created_at           TEXT DEFAULT (datetime('now')),
                updated_at           TEXT DEFAULT (datetime('now')),
                file_count           INTEGER DEFAULT 0,
                status               TEXT DEFAULT 'active',
                similarity_threshold REAL DEFAULT 0.85,
                storage_mode         TEXT DEFAULT 'reference'
            );

            CREATE TABLE IF NOT EXISTS files (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id       INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                original_path    TEXT,
                stored_path      TEXT,
                file_name        TEXT,
                file_type        TEXT,
                file_size        INTEGER DEFAULT 0,
                storage_mode     TEXT DEFAULT 'reference',
                status           TEXT DEFAULT 'pending',
                added_at         TEXT DEFAULT (datetime('now')),
                processed_at     TEXT,
                text_extracted   INTEGER DEFAULT 0,
                images_extracted INTEGER DEFAULT 0,
                error_message    TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS text_chunks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                project_id  INTEGER NOT NULL,
                chunk_index INTEGER DEFAULT 0,
                content     TEXT,
                page_number INTEGER DEFAULT 0,
                chunk_type  TEXT DEFAULT 'paragraph',
                word_count  INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS extracted_images (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                project_id  INTEGER NOT NULL,
                image_index INTEGER DEFAULT 0,
                stored_path TEXT,
                page_number INTEGER DEFAULT 0,
                width       INTEGER DEFAULT 0,
                height      INTEGER DEFAULT 0,
                phash       TEXT,
                ahash       TEXT,
                dhash       TEXT,
                file_size   INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS text_similarities (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id       INTEGER NOT NULL,
                chunk_id_a       INTEGER NOT NULL,
                chunk_id_b       INTEGER NOT NULL,
                file_id_a        INTEGER NOT NULL,
                file_id_b        INTEGER NOT NULL,
                similarity_score REAL DEFAULT 0.0,
                reviewed         INTEGER DEFAULT 0,
                created_at       TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS image_similarities (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id       INTEGER NOT NULL,
                image_id_a       INTEGER NOT NULL,
                image_id_b       INTEGER NOT NULL,
                file_id_a        INTEGER NOT NULL,
                file_id_b        INTEGER NOT NULL,
                similarity_score REAL DEFAULT 0.0,
                hash_distance    INTEGER DEFAULT 0,
                reviewed         INTEGER DEFAULT 0,
                created_at       TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tags (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name       TEXT,
                color      TEXT DEFAULT '#0078d4',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS analysis_runs (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id               INTEGER NOT NULL,
                started_at               TEXT DEFAULT (datetime('now')),
                completed_at             TEXT,
                status                   TEXT DEFAULT 'running',
                files_processed          INTEGER DEFAULT 0,
                text_similarities_found  INTEGER DEFAULT 0,
                image_similarities_found INTEGER DEFAULT 0,
                error_message            TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS settings (
                key        TEXT PRIMARY KEY,
                value      TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS trademarks (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_number TEXT NOT NULL,
                trademark_name      TEXT NOT NULL,
                logo_path           TEXT,
                nice_class          INTEGER,
                owner_name          TEXT DEFAULT '',
                registration_date   TEXT,
                status              TEXT DEFAULT 'registered',
                country             TEXT DEFAULT '',
                created_at          TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS applications (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                application_number TEXT NOT NULL,
                applicant_name     TEXT DEFAULT '',
                trademark_name     TEXT NOT NULL,
                logo_path          TEXT,
                nice_class         INTEGER,
                filing_date        TEXT DEFAULT (date('now')),
                examiner_notes     TEXT DEFAULT '',
                status             TEXT DEFAULT 'pending',
                created_at         TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS conflicts (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id        INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                trademark_id          INTEGER NOT NULL REFERENCES trademarks(id) ON DELETE CASCADE,
                name_similarity_score REAL DEFAULT 0.0,
                logo_similarity_score REAL DEFAULT 0.0,
                phonetic_score        REAL DEFAULT 0.0,
                overall_score         REAL DEFAULT 0.0,
                verdict               TEXT DEFAULT 'DISTINCT',
                examiner_decision     TEXT DEFAULT 'pending',
                notes                 TEXT DEFAULT '',
                created_at            TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS file_index (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash     TEXT UNIQUE NOT NULL,
                file_name        TEXT,
                file_type        TEXT,
                file_size        INTEGER DEFAULT 0,
                text_chunk_count INTEGER DEFAULT 0,
                image_count      INTEGER DEFAULT 0,
                first_seen_at    TEXT DEFAULT (datetime('now')),
                last_used_at     TEXT DEFAULT (datetime('now')),
                use_count        INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS cached_text_chunks (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                file_index_id INTEGER NOT NULL REFERENCES file_index(id) ON DELETE CASCADE,
                chunk_index   INTEGER DEFAULT 0,
                content       TEXT,
                page_number   INTEGER DEFAULT 0,
                chunk_type    TEXT,
                word_count    INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS cached_images (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                file_index_id INTEGER NOT NULL REFERENCES file_index(id) ON DELETE CASCADE,
                image_index   INTEGER DEFAULT 0,
                stored_path   TEXT,
                page_number   INTEGER DEFAULT 0,
                width         INTEGER DEFAULT 0,
                height        INTEGER DEFAULT 0,
                phash         TEXT,
                ahash         TEXT,
                dhash         TEXT
            );
        """)

        # ── Add content_hash column if missing (backwards compat) ─────
        try:
            cur.execute("ALTER TABLE files ADD COLUMN content_hash TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # ── Create indexes AFTER all tables + columns exist ───────────
        for index_sql in (
            "CREATE INDEX IF NOT EXISTS idx_files_project      ON files(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_files_hash         ON files(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_project     ON text_chunks(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_file        ON text_chunks(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_images_project     ON extracted_images(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_images_file        ON extracted_images(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_textsim_project    ON text_similarities(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_imgsim_project     ON image_similarities(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_trademarks_name    ON trademarks(trademark_name)",
            "CREATE INDEX IF NOT EXISTS idx_trademarks_class   ON trademarks(nice_class)",
            "CREATE INDEX IF NOT EXISTS idx_file_index_hash    ON file_index(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_cached_chunks_idx  ON cached_text_chunks(file_index_id)",
            "CREATE INDEX IF NOT EXISTS idx_cached_images_idx  ON cached_images(file_index_id)",
        ):
            try:
                cur.execute(index_sql)
            except sqlite3.OperationalError:
                pass

        # ── Default settings ──────────────────────────────────────────
        defaults = {
            "theme":                     "light",
            "text_similarity_threshold":  "0.85",
            "image_similarity_threshold": "0.85",
            "default_storage_mode":       "reference",
            "export_path":                str(Path.home() / "Documents"),
            "app_version":                "1.0.0",
            "app_mode":                   "general",
        }
        for key, value in defaults.items():
            cur.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

        conn.commit()
        print(f"Database initialized at: {DB_PATH}")
    finally:
        conn.close()


# Backwards-compat alias
initialize_database = init_db


# ═════════════════════════════════════════════
# SETTINGS
# ═════════════════════════════════════════════

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET
                   value = excluded.value,
                   updated_at = excluded.updated_at""",
            (key, value)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_settings() -> dict:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()


# ═════════════════════════════════════════════
# PROJECTS
# ═════════════════════════════════════════════

def get_all_projects() -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_project(project_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_project_by_id(project_id: int):
    return get_project(project_id)


def create_project(
    name: str,
    description: str = "",
    similarity_threshold: float = 0.85,
    storage_mode: str = "reference",
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO projects
               (name, description, similarity_threshold, storage_mode)
               VALUES (?, ?, ?, ?)""",
            (name, description, similarity_threshold, storage_mode)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_project(
    project_id: int,
    name: str,
    description: str = "",
    similarity_threshold: float = 0.85,
    storage_mode: str = "reference",
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE projects
               SET name = ?, description = ?, similarity_threshold = ?,
                   storage_mode = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (name, description, similarity_threshold, storage_mode, project_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_project(project_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    finally:
        conn.close()


# ═════════════════════════════════════════════
# DASHBOARD STATS
# ═════════════════════════════════════════════

def get_dashboard_stats() -> dict:
    """Overall dashboard statistics."""
    conn = get_connection()
    try:
        projects  = conn.execute("SELECT COUNT(*) as n FROM projects").fetchone()["n"]
        files     = conn.execute("SELECT COUNT(*) as n FROM files").fetchone()["n"]
        text_sim  = conn.execute("SELECT COUNT(*) as n FROM text_similarities").fetchone()["n"]
        image_sim = conn.execute("SELECT COUNT(*) as n FROM image_similarities").fetchone()["n"]
        recent = conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC LIMIT 5"
        ).fetchall()
        return {
            "total_projects":     projects,
            "total_files":        files,
            "text_similarities":  text_sim,
            "image_similarities": image_sim,
            "recent_projects":    [dict(r) for r in recent],
        }
    finally:
        conn.close()


# ═════════════════════════════════════════════
# FILES
# ═════════════════════════════════════════════

def get_files_for_project(project_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM files WHERE project_id = ? ORDER BY added_at DESC",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_project_files(project_id: int) -> list:
    return get_files_for_project(project_id)


def add_files_to_project(
    project_id: int,
    paths: list,
    storage_mode: str = "reference",
) -> list:
    added = []
    project_folder = Path.home() / ".uniquest" / "projects" / str(project_id)
    if storage_mode == "copy":
        project_folder.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    try:
        for path in paths:
            p = Path(path)
            if not p.exists():
                continue

            file_name = p.name
            file_type = p.suffix.lower().lstrip(".")
            try:
                file_size = p.stat().st_size
            except Exception:
                file_size = 0

            original_path = str(p)
            stored_path = original_path
            if storage_mode == "copy":
                dst = project_folder / file_name
                try:
                    shutil.copy2(p, dst)
                    stored_path = str(dst)
                except Exception:
                    stored_path = original_path

            cur = conn.execute(
                """INSERT INTO files
                   (project_id, original_path, stored_path, file_name,
                    file_type, file_size, storage_mode, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                (project_id, original_path, stored_path, file_name,
                 file_type, file_size, storage_mode)
            )
            added.append(cur.lastrowid)

        conn.execute(
            """UPDATE projects
               SET file_count = (SELECT COUNT(*) FROM files WHERE project_id = ?),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (project_id, project_id)
        )
        conn.commit()
    finally:
        conn.close()
    return added


def remove_file_from_project(file_id: int) -> None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT project_id FROM files WHERE id = ?", (file_id,)
        ).fetchone()

        conn.execute("DELETE FROM text_chunks WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM extracted_images WHERE file_id = ?", (file_id,))
        conn.execute(
            "DELETE FROM text_similarities WHERE file_id_a = ? OR file_id_b = ?",
            (file_id, file_id)
        )
        conn.execute(
            "DELETE FROM image_similarities WHERE file_id_a = ? OR file_id_b = ?",
            (file_id, file_id)
        )
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))

        if row:
            pid = row["project_id"]
            conn.execute(
                """UPDATE projects
                   SET file_count = (SELECT COUNT(*) FROM files WHERE project_id = ?),
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (pid, pid)
            )
        conn.commit()
    finally:
        conn.close()


def clear_project_results(project_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM text_similarities WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM image_similarities WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM text_chunks WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM extracted_images WHERE project_id = ?", (project_id,))
        conn.execute(
            """UPDATE files SET status = 'pending',
               text_extracted = 0, images_extracted = 0
               WHERE project_id = ?""",
            (project_id,)
        )
        conn.commit()
    finally:
        conn.close()


def update_file_status(file_id: int, status: str, error_message: str = "") -> None:
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE files
               SET status = ?, error_message = ?, processed_at = datetime('now')
               WHERE id = ?""",
            (status, error_message, file_id)
        )
        conn.commit()
    finally:
        conn.close()


# ═════════════════════════════════════════════
# SIMILARITIES
# ═════════════════════════════════════════════

def mark_similarity_reviewed(sim_id: int, kind: str = "text") -> None:
    table = "text_similarities" if kind == "text" else "image_similarities"
    conn = get_connection()
    try:
        conn.execute(f"UPDATE {table} SET reviewed = 1 WHERE id = ?", (sim_id,))
        conn.commit()
    finally:
        conn.close()


def get_text_similarities(project_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT ts.*,
                      ca.content AS content_a, ca.page_number AS page_a,
                      cb.content AS content_b, cb.page_number AS page_b,
                      fa.file_name AS file_name_a,
                      fb.file_name AS file_name_b
               FROM text_similarities ts
               JOIN text_chunks ca ON ca.id = ts.chunk_id_a
               JOIN text_chunks cb ON cb.id = ts.chunk_id_b
               JOIN files fa ON fa.id = ts.file_id_a
               JOIN files fb ON fb.id = ts.file_id_b
               WHERE ts.project_id = ?
               ORDER BY ts.similarity_score DESC""",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_image_similarities(project_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT ims.*,
                      ia.stored_path AS path_a, ia.page_number AS page_a,
                      ib.stored_path AS path_b, ib.page_number AS page_b,
                      fa.file_name AS file_name_a,
                      fb.file_name AS file_name_b
               FROM image_similarities ims
               JOIN extracted_images ia ON ia.id = ims.image_id_a
               JOIN extracted_images ib ON ib.id = ims.image_id_b
               JOIN files fa ON fa.id = ims.file_id_a
               JOIN files fb ON fb.id = ims.file_id_b
               WHERE ims.project_id = ?
               ORDER BY ims.similarity_score DESC""",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═════════════════════════════════════════════
# TRADEMARK REGISTRY
# ═════════════════════════════════════════════

def insert_trademark(
    registration_number: str,
    trademark_name:      str,
    logo_path:           Optional[str] = None,
    nice_class:          Optional[int] = None,
    owner_name:          str = "",
    registration_date:   Optional[str] = None,
    status:              str = "registered",
    country:             str = "",
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO trademarks
               (registration_number, trademark_name, logo_path, nice_class,
                owner_name, registration_date, status, country)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (registration_number, trademark_name, logo_path, nice_class,
             owner_name, registration_date, status, country)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_all_trademarks(nice_class: Optional[int] = None) -> list:
    conn = get_connection()
    try:
        if nice_class is not None:
            rows = conn.execute(
                "SELECT * FROM trademarks WHERE nice_class = ? ORDER BY trademark_name",
                (nice_class,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trademarks ORDER BY trademark_name"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_trademark_count() -> int:
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as n FROM trademarks").fetchone()
        return row["n"]
    finally:
        conn.close()


def delete_trademark(trademark_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM trademarks WHERE id = ?", (trademark_id,))
        conn.commit()
    finally:
        conn.close()


def clear_all_trademarks() -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM trademarks")
        conn.commit()
    finally:
        conn.close()


# ═════════════════════════════════════════════
# APPLICATIONS
# ═════════════════════════════════════════════

def insert_application(
    application_number: str,
    trademark_name:     str,
    applicant_name:     str = "",
    logo_path:          Optional[str] = None,
    nice_class:         Optional[int] = None,
    filing_date:        Optional[str] = None,
) -> int:
    conn = get_connection()
    try:
        filing = filing_date or datetime.now().strftime("%Y-%m-%d")
        cur = conn.execute(
            """INSERT INTO applications
               (application_number, applicant_name, trademark_name,
                logo_path, nice_class, filing_date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (application_number, applicant_name, trademark_name,
             logo_path, nice_class, filing)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_all_applications() -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_application_status(application_id: int, status: str, notes: str = "") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE applications SET status = ?, examiner_notes = ? WHERE id = ?",
            (status, notes, application_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_application(application_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM applications WHERE id = ?", (application_id,))
        conn.commit()
    finally:
        conn.close()


# ═════════════════════════════════════════════
# CONFLICTS
# ═════════════════════════════════════════════

def save_conflict(
    application_id:        int,
    trademark_id:          int,
    name_similarity_score: float,
    logo_similarity_score: float,
    phonetic_score:        float,
    overall_score:         float,
    verdict:               str,
    notes:                 str = "",
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO conflicts
               (application_id, trademark_id, name_similarity_score,
                logo_similarity_score, phonetic_score, overall_score,
                verdict, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (application_id, trademark_id, name_similarity_score,
             logo_similarity_score, phonetic_score, overall_score,
             verdict, notes)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_conflicts_for_application(application_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT c.*,
                      t.trademark_name     AS tm_name,
                      t.registration_number,
                      t.owner_name,
                      t.nice_class         AS tm_class,
                      t.status             AS tm_status,
                      t.logo_path          AS tm_logo_path
               FROM conflicts c
               JOIN trademarks t ON t.id = c.trademark_id
               WHERE c.application_id = ?
               ORDER BY c.overall_score DESC""",
            (application_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_examiner_decision(conflict_id: int, decision: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE conflicts SET examiner_decision = ? WHERE id = ?",
            (decision, conflict_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_ip_dashboard_stats() -> dict:
    conn = get_connection()
    try:
        tm_total = conn.execute("SELECT COUNT(*) as n FROM trademarks").fetchone()["n"]
        app_total = conn.execute("SELECT COUNT(*) as n FROM applications").fetchone()["n"]
        app_pending = conn.execute(
            "SELECT COUNT(*) as n FROM applications WHERE status = 'pending'"
        ).fetchone()["n"]
        conflicts_total = conn.execute("SELECT COUNT(*) as n FROM conflicts").fetchone()["n"]
        conflicts_high = conn.execute(
            """SELECT COUNT(*) as n FROM conflicts
               WHERE verdict IN ('IDENTICAL', 'CONFUSINGLY SIMILAR')"""
        ).fetchone()["n"]
        return {
            "trademarks_total":     tm_total,
            "applications_total":   app_total,
            "applications_pending": app_pending,
            "conflicts_total":      conflicts_total,
            "conflicts_high":       conflicts_high,
        }
    finally:
        conn.close()