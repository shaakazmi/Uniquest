from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from core.extractor import extract_text_streaming, extract_images_streaming
from core.similarity import find_similar_text_batched, find_similar_images_batched
from database.db import get_connection


class AnalysisWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, project_id: int, file_records: list, threshold: float = 0.75):
        super().__init__()
        self.project_id   = project_id
        self.file_records = file_records
        self.threshold    = threshold
        self._cancelled   = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self._run_pipeline()
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")

    def _run_pipeline(self):
        total_files   = len(self.file_records)
        all_chunk_ids = []

        for idx, file_rec in enumerate(self.file_records):
            if self._cancelled:
                return

            file_id   = file_rec["id"]
            file_path = file_rec["path"]
            file_name = Path(file_path).name

            pct = int((idx / total_files) * 40)
            self.progress.emit(pct, f"Extracting {file_name}...")

            chunk_ids = self._extract_and_store_text(file_id, file_path)
            all_chunk_ids.extend(chunk_ids)
            self._extract_and_store_images(file_id, file_path)

            pct = int(((idx + 1) / total_files) * 40)
            self.progress.emit(pct, f"Extracted {file_name}")

        if self._cancelled:
            return

        self.progress.emit(40, "Comparing text...")
        text_count = self._run_text_similarity(all_chunk_ids)

        if self._cancelled:
            return

        self.progress.emit(80, "Comparing images...")
        image_count = self._run_image_similarity()

        self.progress.emit(100, "Complete")
        self.finished.emit({
            "text_similarities":  text_count,
            "image_similarities": image_count,
            "chunks_processed":   len(all_chunk_ids),
        })

    def _extract_and_store_text(self, file_id: int, file_path: str) -> list:
        chunk_ids = []
        conn = get_connection()
        try:
            for batch in extract_text_streaming(file_path):
                if self._cancelled:
                    break

                rows = [
                    (file_id, self.project_id,
                     chunk.chunk_index, chunk.content,
                     chunk.page_number, chunk.chunk_type,
                     len(chunk.content.split()))
                    for chunk in batch
                ]

                with conn:
                    conn.executemany(
                        """INSERT INTO text_chunks
                           (file_id, project_id, chunk_index, content,
                            page_number, chunk_type, word_count)
                           VALUES (?,?,?,?,?,?,?)""",
                        rows
                    )

                last_id  = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                first_id = last_id - len(rows) + 1
                chunk_ids.extend(range(first_id, last_id + 1))
        finally:
            conn.close()
        return chunk_ids

    def _extract_and_store_images(self, file_id: int, file_path: str):
        conn = get_connection()
        try:
            for batch in extract_images_streaming(file_path, self.project_id):
                if self._cancelled:
                    break
                rows = [
                    (file_id, self.project_id,
                     img.image_index, img.image_path,
                     img.page_number, img.width, img.height,
                     img.phash, img.ahash, img.dhash, 0)
                    for img in batch
                ]
                with conn:
                    conn.executemany(
                        """INSERT INTO extracted_images
                           (file_id, project_id, image_index, stored_path,
                            page_number, width, height,
                            phash, ahash, dhash, file_size)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        rows
                    )
        finally:
            conn.close()

    def _run_text_similarity(self, chunk_ids: list) -> int:
        if not chunk_ids:
            return 0

        conn  = get_connection()
        total = len(chunk_ids)
        saved = 0
        BATCH = 500

        try:
            for start in range(0, total, BATCH):
                if self._cancelled:
                    break

                batch_ids    = chunk_ids[start: start + BATCH]
                placeholders = ",".join("?" * len(batch_ids))
                pct = 40 + int((start / max(total, 1)) * 40)
                self.progress.emit(pct, f"Text comparison {start}/{total}")

                rows = conn.execute(
                    f"SELECT id, content, file_id FROM text_chunks WHERE id IN ({placeholders})",
                    batch_ids
                ).fetchall()

                if not rows:
                    continue

                rows  = [(r[0], r[1], r[2]) for r in rows]
                pairs = find_similar_text_batched(rows, self.threshold)

                if pairs:
                    with conn:
                        conn.executemany(
                            """INSERT OR IGNORE INTO text_similarities
                               (project_id, chunk_id_a, chunk_id_b,
                                file_id_a, file_id_b, similarity_score, reviewed)
                               VALUES (?,?,?,?,?,?,0)""",
                            [(self.project_id,
                              p["chunk_id_a"], p["chunk_id_b"],
                              p["file_id_a"],  p["file_id_b"],
                              p["score"])
                             for p in pairs]
                        )
                    saved += len(pairs)
        finally:
            conn.close()
        return saved

    def _run_image_similarity(self) -> int:
        conn  = get_connection()
        saved = 0
        try:
            images = conn.execute(
                "SELECT id, file_id, phash FROM extracted_images WHERE project_id=?",
                (self.project_id,)
            ).fetchall()
            images = [(r[0], r[1], r[2]) for r in images]
            pairs  = find_similar_images_batched(images, self.threshold)

            if pairs:
                with conn:
                    conn.executemany(
                        """INSERT OR IGNORE INTO image_similarities
                           (project_id, image_id_a, image_id_b,
                            file_id_a, file_id_b,
                            similarity_score, hash_distance, reviewed)
                           VALUES (?,?,?,?,?,?,?,0)""",
                        [(self.project_id,
                          p["image_id_a"], p["image_id_b"],
                          p["file_id_a"],  p["file_id_b"],
                          p["score"],      p["distance"])
                         for p in pairs]
                    )
                saved = len(pairs)
        finally:
            conn.close()
        return saved
        # ─────────────────────────────────────────────
# PROJECT CRUD FUNCTIONS
# ─────────────────────────────────────────────

def get_all_projects() -> list:
    """Return all projects ordered by most recently updated."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_project_by_id(project_id: int):
    """Return one project by ID or None if not found."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_project(
    name: str,
    description: str = "",
    similarity_threshold: float = 0.85,
    storage_mode: str = "reference",
) -> int:
    """Create a new project. Returns the new project ID."""
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
    """Update an existing project."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE projects
               SET name = ?,
                   description = ?,
                   similarity_threshold = ?,
                   storage_mode = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (name, description, similarity_threshold, storage_mode, project_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_project(project_id: int) -> None:
    """Delete a project and all its associated data (cascades)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    finally:
        conn.close()


def get_dashboard_stats() -> dict:
    """Return summary statistics for the dashboard page."""
    conn = get_connection()
    try:
        projects = conn.execute(
            "SELECT COUNT(*) as n FROM projects"
        ).fetchone()["n"]

        files = conn.execute(
            "SELECT COUNT(*) as n FROM files"
        ).fetchone()["n"]

        text_sim = conn.execute(
            "SELECT COUNT(*) as n FROM text_similarities"
        ).fetchone()["n"]

        image_sim = conn.execute(
            "SELECT COUNT(*) as n FROM image_similarities"
        ).fetchone()["n"]

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


# ─────────────────────────────────────────────
# FILE CRUD FUNCTIONS
# ─────────────────────────────────────────────

def get_files_for_project(project_id: int) -> list:
    """Return all files for a given project."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM files WHERE project_id = ? ORDER BY added_at DESC",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_file_to_project(
    project_id: int,
    original_path: str,
    stored_path: str,
    file_name: str,
    file_type: str,
    file_size: int = 0,
    storage_mode: str = "reference",
) -> int:
    """Add one file to a project. Returns the file ID."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO files
               (project_id, original_path, stored_path, file_name,
                file_type, file_size, storage_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, original_path, stored_path, file_name,
             file_type, file_size, storage_mode)
        )
        # Update file_count in projects
        conn.execute(
            """UPDATE projects
               SET file_count = (SELECT COUNT(*) FROM files WHERE project_id = ?),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (project_id, project_id)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_file(file_id: int) -> None:
    """Delete a file record from the database."""
    conn = get_connection()
    try:
        # Get project_id first
        row = conn.execute(
            "SELECT project_id FROM files WHERE id = ?", (file_id,)
        ).fetchone()

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
    """Clear all analysis results (text/image similarities + chunks) for a project."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM text_similarities WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM image_similarities WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM text_chunks WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM extracted_images WHERE project_id = ?", (project_id,))
        conn.commit()
    finally:
        conn.close()
        # ─────────────────────────────────────────────
# ALIASES & EXTRA HELPERS
# ─────────────────────────────────────────────

def get_project(project_id: int):
    """Alias for get_project_by_id."""
    return get_project_by_id(project_id)


def get_project_files(project_id: int) -> list:
    """Alias for get_files_for_project."""
    return get_files_for_project(project_id)


def update_file_status(file_id: int, status: str, error_message: str = "") -> None:
    """Update the status of a file (pending / processing / done / error)."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE files
               SET status = ?,
                   error_message = ?,
                   processed_at = datetime('now')
               WHERE id = ?""",
            (status, error_message, file_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_text_similarities(project_id: int) -> list:
    """Get all text similarity pairs for a project."""
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
    """Get all image similarity pairs for a project."""
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


def mark_similarity_reviewed(sim_id: int, kind: str = "text") -> None:
    """Mark a text or image similarity pair as reviewed."""
    table = "text_similarities" if kind == "text" else "image_similarities"
    conn = get_connection()
    try:
        conn.execute(f"UPDATE {table} SET reviewed = 1 WHERE id = ?", (sim_id,))
        conn.commit()
    finally:
        conn.close()