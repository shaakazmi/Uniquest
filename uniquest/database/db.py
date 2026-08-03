import sqlite3
from pathlib import Path

DB_DIR  = Path.home() / ".uniquest"
DB_PATH = DB_DIR / "uniquest.db"


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")   # 64 MB cache
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def initialize_database():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            name                 TEXT NOT NULL,
            description          TEXT DEFAULT '',
            created_at           TEXT DEFAULT (datetime('now')),
            updated_at           TEXT DEFAULT (datetime('now')),
            file_count           INTEGER DEFAULT 0,
            status               TEXT DEFAULT 'active',
            similarity_threshold REAL DEFAULT 0.75,
            storage_mode         TEXT DEFAULT 'reference'
        );

        CREATE TABLE IF NOT EXISTS files (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id       INTEGER NOT NULL,
            original_path    TEXT NOT NULL,
            stored_path      TEXT DEFAULT '',
            file_name        TEXT NOT NULL,
            file_type        TEXT NOT NULL,
            file_size        INTEGER DEFAULT 0,
            storage_mode     TEXT DEFAULT 'reference',
            status           TEXT DEFAULT 'pending',
            added_at         TEXT DEFAULT (datetime('now')),
            processed_at     TEXT DEFAULT '',
            text_extracted   INTEGER DEFAULT 0,
            images_extracted INTEGER DEFAULT 0,
            error_message    TEXT DEFAULT '',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS text_chunks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id     INTEGER NOT NULL,
            project_id  INTEGER NOT NULL,
            chunk_index INTEGER DEFAULT 0,
            content     TEXT NOT NULL,
            page_number INTEGER DEFAULT 1,
            chunk_type  TEXT DEFAULT 'paragraph',
            word_count  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS extracted_images (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id     INTEGER NOT NULL,
            project_id  INTEGER NOT NULL,
            image_index INTEGER DEFAULT 0,
            stored_path TEXT DEFAULT '',
            page_number INTEGER DEFAULT 1,
            width       INTEGER DEFAULT 0,
            height      INTEGER DEFAULT 0,
            phash       TEXT DEFAULT '',
            ahash       TEXT DEFAULT '',
            dhash       TEXT DEFAULT '',
            file_size   INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS text_similarities (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id       INTEGER NOT NULL,
            chunk_id_a       INTEGER NOT NULL,
            chunk_id_b       INTEGER NOT NULL,
            file_id_a        INTEGER NOT NULL,
            file_id_b        INTEGER NOT NULL,
            similarity_score REAL NOT NULL,
            reviewed         INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS image_similarities (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id       INTEGER NOT NULL,
            image_id_a       INTEGER NOT NULL,
            image_id_b       INTEGER NOT NULL,
            file_id_a        INTEGER NOT NULL,
            file_id_b        INTEGER NOT NULL,
            similarity_score REAL NOT NULL,
            hash_distance    INTEGER DEFAULT 0,
            reviewed         INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tags (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name       TEXT NOT NULL,
            color      TEXT DEFAULT '#1a73e8',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS analysis_runs (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id               INTEGER NOT NULL,
            started_at               TEXT DEFAULT (datetime('now')),
            completed_at             TEXT DEFAULT '',
            status                   TEXT DEFAULT 'running',
            files_processed          INTEGER DEFAULT 0,
            text_similarities_found  INTEGER DEFAULT 0,
            image_similarities_found INTEGER DEFAULT 0,
            error_message            TEXT DEFAULT '',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- indexes for speed
        CREATE INDEX IF NOT EXISTS idx_text_chunks_project
            ON text_chunks(project_id);
        CREATE INDEX IF NOT EXISTS idx_text_chunks_file
            ON text_chunks(file_id);
        CREATE INDEX IF NOT EXISTS idx_images_project
            ON extracted_images(project_id);
        CREATE INDEX IF NOT EXISTS idx_text_sim_project
            ON text_similarities(project_id);
        CREATE INDEX IF NOT EXISTS idx_image_sim_project
            ON image_similarities(project_id);
    """)

    # default settings
    defaults = [
        ("theme",                    "light"),
        ("text_similarity_threshold","0.75"),
        ("image_similarity_threshold","0.85"),
        ("default_storage_mode",     "reference"),
        ("export_path",              str(Path.home() / "Documents")),
        ("app_version",              "1.0.0"),
    ]
    for key, value in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)",
            (key, value)
        )

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
#  Settings helpers
# ─────────────────────────────────────────────────────────────
def get_setting(key: str, default: str = "") -> str:
    try:
        conn = get_connection()
        row  = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return row["value"] if row else default
    except Exception:
        return default


def set_setting(key: str, value: str):
    try:
        conn = get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?,?,datetime('now'))",
            (key, value)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
#  Project helpers
# ─────────────────────────────────────────────────────────────
def get_all_projects() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project(project_id: int) -> dict:
    conn = get_connection()
    row  = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def create_project(name: str, description: str = "",
                   threshold: float = 0.75,
                   storage_mode: str = "reference") -> int:
    conn = get_connection()
    cur  = conn.execute(
        """INSERT INTO projects (name, description, similarity_threshold, storage_mode)
           VALUES (?,?,?,?)""",
        (name, description, threshold, storage_mode)
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def update_project(project_id: int, name: str, description: str,
                   threshold: float, storage_mode: str):
    conn = get_connection()
    conn.execute(
        """UPDATE projects SET name=?, description=?,
           similarity_threshold=?, storage_mode=?,
           updated_at=datetime('now')
           WHERE id=?""",
        (name, description, threshold, storage_mode, project_id)
    )
    conn.commit()
    conn.close()


def delete_project(project_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
#  File helpers
# ─────────────────────────────────────────────────────────────
def add_file_record(project_id: int, original_path: str,
                    file_name: str, file_type: str,
                    file_size: int, storage_mode: str = "reference") -> int:
    conn = get_connection()
    cur  = conn.execute(
        """INSERT INTO files
           (project_id, original_path, file_name, file_type, file_size, storage_mode)
           VALUES (?,?,?,?,?,?)""",
        (project_id, original_path, file_name, file_type, file_size, storage_mode)
    )
    conn.commit()
    fid = cur.lastrowid
    conn.close()
    return fid


def get_project_files(project_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM files WHERE project_id=? ORDER BY added_at",
        (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_file_status(file_id: int, status: str, error: str = ""):
    conn = get_connection()
    conn.execute(
        """UPDATE files SET status=?, error_message=?,
           processed_at=datetime('now') WHERE id=?""",
        (status, error, file_id)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
#  Results helpers
# ─────────────────────────────────────────────────────────────
def get_text_similarities(project_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT ts.*,
                  ca.content   AS content_a,
                  ca.page_number AS page_a,
                  ca.chunk_type  AS type_a,
                  cb.content   AS content_b,
                  cb.page_number AS page_b,
                  cb.chunk_type  AS type_b,
                  fa.file_name AS file_name_a,
                  fb.file_name AS file_name_b
           FROM text_similarities ts
           JOIN text_chunks ca ON ts.chunk_id_a = ca.id
           JOIN text_chunks cb ON ts.chunk_id_b = cb.id
           JOIN files fa       ON ts.file_id_a  = fa.id
           JOIN files fb       ON ts.file_id_b  = fb.id
           WHERE ts.project_id = ?
           ORDER BY ts.similarity_score DESC""",
        (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_image_similarities(project_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT is2.*,
                  ia.stored_path AS path_a,
                  ib.stored_path AS path_b,
                  fa.file_name   AS file_name_a,
                  fb.file_name   AS file_name_b
           FROM image_similarities is2
           JOIN extracted_images ia ON is2.image_id_a = ia.id
           JOIN extracted_images ib ON is2.image_id_b = ib.id
           JOIN files fa            ON is2.file_id_a  = fa.id
           JOIN files fb            ON is2.file_id_b  = fb.id
           WHERE is2.project_id = ?
           ORDER BY is2.similarity_score DESC""",
        (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_similarity_reviewed(sim_id: int, sim_type: str = "text"):
    table = "text_similarities" if sim_type == "text" else "image_similarities"
    conn  = get_connection()
    conn.execute(f"UPDATE {table} SET reviewed=1 WHERE id=?", (sim_id,))
    conn.commit()
    conn.close()

def get_dashboard_stats() -> dict:
    conn  = get_connection()
    stats = {}
    stats["total_projects"]      = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    stats["total_files"]         = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    stats["total_text_matches"]  = conn.execute("SELECT COUNT(*) FROM text_similarities").fetchone()[0]
    stats["total_image_matches"] = conn.execute("SELECT COUNT(*) FROM image_similarities").fetchone()[0]
    stats["recent_projects"]     = [
        dict(r) for r in conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC LIMIT 5"
        ).fetchall()
    ]
    conn.close()
    return stats