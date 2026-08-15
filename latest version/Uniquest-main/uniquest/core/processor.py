"""
Core processor for Uniquest.
Handles project CRUD, file CRUD, and the background analysis worker.
"""

import os
import shutil
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from core.extractor import extract_text_streaming, extract_images_streaming
from core.similarity import find_similar_text_batched, find_similar_images_batched
from database.db import get_connection


# ═════════════════════════════════════════════
# PROJECT CRUD
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


def get_dashboard_stats() -> dict:
    conn = get_connection()
    try:
        projects = conn.execute("SELECT COUNT(*) as n FROM projects").fetchone()["n"]
        files = conn.execute("SELECT COUNT(*) as n FROM files").fetchone()["n"]
        text_sim = conn.execute("SELECT COUNT(*) as n FROM text_similarities").fetchone()["n"]
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
# FILE CRUD
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


def add_files_to_project(
    project_id: int,
    paths: list,
    storage_mode: str = "reference",
) -> list:
    """Add multiple files to a project. Returns list of new file IDs."""
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

        # Update file count on project
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
    """Remove a file and its extracted data from the project."""
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
    """Clear all analysis results but keep the files."""
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
# RESULT QUERIES
# ═════════════════════════════════════════════

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


def mark_similarity_reviewed(sim_id: int, kind: str = "text") -> None:
    table = "text_similarities" if kind == "text" else "image_similarities"
    conn = get_connection()
    try:
        conn.execute(f"UPDATE {table} SET reviewed = 1 WHERE id = ?", (sim_id,))
        conn.commit()
    finally:
        conn.close()


# ═════════════════════════════════════════════
# ANALYSIS WORKER
# ═════════════════════════════════════════════

class AnalysisWorker(QThread):
    """
    Background thread that runs full text + image similarity analysis
    for all files in a project.
    """

    # Signals expected by ui/analysis.py
    progress_changed = pyqtSignal(int, str)                 # percent, message
    stage_changed    = pyqtSignal(str)                      # stage name
    log_message      = pyqtSignal(str)                      # log line
    file_processed   = pyqtSignal(int)                      # file_id
    finished_ok      = pyqtSignal(int, int, int)            # files_done, text_matches, image_matches
    finished_error   = pyqtSignal(str)                      # error message

    def __init__(
        self,
        project_id:      int,
        text_threshold:  float = 0.75,
        image_threshold: float = 0.85,
    ):
        super().__init__()
        self.project_id      = project_id
        self.text_threshold  = text_threshold
        self.image_threshold = image_threshold
        self._cancelled      = False

    def cancel(self):
        self._cancelled = True
        self.log_message.emit("Cancellation requested...")

    def run(self):
        try:
            self._run_pipeline()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.finished_error.emit(f"{e}\n\n{tb}")

    def _run_pipeline(self):
        files = get_files_for_project(self.project_id)
        if not files:
            self.finished_error.emit("No files in project.")
            return

        # Import indexer here to avoid circular imports
        from core.indexer import (
            compute_file_hash, lookup_cached_file,
            register_file_in_index, bump_index_usage,
            save_cached_chunks, save_cached_images,
            restore_chunks_to_project, restore_images_to_project,
        )

        total_files = len(files)
        all_chunk_ids = []
        files_done = 0
        cache_hits = 0

        self.stage_changed.emit("Extracting content")
        self.log_message.emit(f"Starting extraction of {total_files} file(s)...")

        for idx, file_rec in enumerate(files):
            if self._cancelled:
                return

            file_id   = file_rec["id"]
            file_path = file_rec.get("stored_path") or file_rec.get("original_path")
            file_name = file_rec.get("file_name", "unknown")

            pct = int((idx / total_files) * 40)
            self.progress_changed.emit(pct, f"Processing {file_name}")
            self.log_message.emit(f"[{idx+1}/{total_files}] {file_name}")

            update_file_status(file_id, "processing")

            try:
                # ── STEP 1: Compute hash ──────────────────────
                self.log_message.emit("    Computing fingerprint...")
                content_hash = compute_file_hash(file_path)

                # Save hash to files table
                conn = get_connection()
                try:
                    conn.execute(
                        "UPDATE files SET content_hash = ? WHERE id = ?",
                        (content_hash, file_id)
                    )
                    conn.commit()
                finally:
                    conn.close()

                # ── STEP 2: Check cache ───────────────────────
                cached = lookup_cached_file(content_hash) if content_hash else None

                if cached:
                    # CACHE HIT — restore from index
                    self.log_message.emit(
                        f"    CACHE HIT — reusing previous extraction "
                        f"(used {cached['use_count']} times before)"
                    )
                    chunk_ids = restore_chunks_to_project(
                        cached["id"], file_id, self.project_id
                    )
                    img_count = restore_images_to_project(
                        cached["id"], file_id, self.project_id
                    )
                    bump_index_usage(cached["id"])
                    cache_hits += 1
                else:
                    # CACHE MISS — do full extraction
                    self.log_message.emit("    New file — extracting...")

                    # Collect chunks and images with indexer-compatible structure
                    from core.extractor import extract_text_streaming, extract_images_streaming

                    all_chunks = []
                    for batch in extract_text_streaming(file_path):
                        if self._cancelled:
                            break
                        all_chunks.extend(batch)

                    all_images = []
                    for batch in extract_images_streaming(file_path, self.project_id):
                        if self._cancelled:
                            break
                        all_images.extend(batch)

                    # Register in index + save cached copies
                    if content_hash:
                        index_id = register_file_in_index(
                            content_hash=content_hash,
                            file_name=file_name,
                            file_type=file_rec.get("file_type", ""),
                            file_size=file_rec.get("file_size", 0),
                        )
                        save_cached_chunks(index_id, all_chunks)
                        save_cached_images(index_id, all_images)

                    # Insert chunks into text_chunks
                    chunk_ids = self._store_chunks(file_id, all_chunks)
                    img_count = self._store_images(file_id, all_images)

                all_chunk_ids.extend(chunk_ids)
                self._update_file_stats(file_id, len(chunk_ids), img_count)
                update_file_status(file_id, "done")
                files_done += 1
                self.file_processed.emit(file_id)
                self.log_message.emit(
                    f"    -> {len(chunk_ids)} text chunks, {img_count} images"
                )

            except Exception as e:
                update_file_status(file_id, "error", str(e))
                self.log_message.emit(f"    ! Error: {e}")

        if self._cancelled:
            return

        if cache_hits > 0:
            self.log_message.emit(
                f"Cache saved time on {cache_hits}/{total_files} file(s)."
            )

        self.stage_changed.emit("Comparing text")
        self.progress_changed.emit(45, "Comparing text chunks...")
        self.log_message.emit(f"Running text similarity on {len(all_chunk_ids)} chunks...")
        text_count = self._run_text_similarity(all_chunk_ids)
        self.log_message.emit(f"Found {text_count} text matches")

        if self._cancelled:
            return

        self.stage_changed.emit("Comparing images")
        self.progress_changed.emit(80, "Comparing images...")
        self.log_message.emit("Running image similarity...")
        image_count = self._run_image_similarity()
        self.log_message.emit(f"Found {image_count} image matches")

        self.progress_changed.emit(100, "Complete")
        self.stage_changed.emit("Complete")
        self.log_message.emit(
            f"Done. Files: {files_done}, Text: {text_count}, Images: {image_count}, "
            f"Cache hits: {cache_hits}"
        )
        self.finished_ok.emit(files_done, text_count, image_count)
    def _update_file_stats(self, file_id: int, text_count: int, img_count: int):
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE files SET text_extracted = ?, images_extracted = ? WHERE id = ?",
                (text_count, img_count, file_id)
            )
            conn.commit()
        finally:
            conn.close()


    def _store_chunks(self, file_id: int, chunks: list) -> list:
        """Store already-extracted chunks into text_chunks. Returns new IDs."""
        if not chunks:
            return []
        conn = get_connection()
        try:
            rows = [
                (file_id, self.project_id,
                 ch.chunk_index, ch.content,
                 ch.page_number, ch.chunk_type,
                 len(ch.content.split()))
                for ch in chunks
            ]
            with conn:
                conn.executemany(
                    """INSERT INTO text_chunks
                       (file_id, project_id, chunk_index, content,
                        page_number, chunk_type, word_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    rows
                )
                last_id  = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                first_id = last_id - len(rows) + 1
                return list(range(first_id, last_id + 1))
        finally:
            conn.close()

    def _store_images(self, file_id: int, images: list) -> int:
        """Store already-extracted images + OCR their text into text_chunks."""
        if not images:
            return 0

        # Try OCR
        try:
            from core.extractor import ocr_image, OCR_AVAILABLE
        except ImportError:
            OCR_AVAILABLE = False
            ocr_image = lambda p: ""

        conn = get_connection()
        try:
            rows = [
                (file_id, self.project_id,
                 img.image_index, img.image_path,
                 img.page_number, img.width, img.height,
                 img.phash, img.ahash, img.dhash, 0)
                for img in images
            ]
            with conn:
                conn.executemany(
                    """INSERT INTO extracted_images
                       (file_id, project_id, image_index, stored_path,
                        page_number, width, height,
                        phash, ahash, dhash, file_size)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    rows
                )

            # ── OCR each image, save text as chunks ──
            if OCR_AVAILABLE:
                ocr_chunks = []
                for img in images:
                    text = ocr_image(img.image_path)
                    if text and len(text.strip()) >= 3:
                        ocr_chunks.append((
                            file_id, self.project_id,
                            img.image_index,
                            text,
                            img.page_number,
                            "ocr",
                            len(text.split())
                        ))
                if ocr_chunks:
                    with conn:
                        conn.executemany(
                            """INSERT INTO text_chunks
                               (file_id, project_id, chunk_index, content,
                                page_number, chunk_type, word_count)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            ocr_chunks
                        )
                    self.log_message.emit(
                        f"    OCR extracted text from {len(ocr_chunks)} image(s)"
                    )

            return len(rows)
        finally:
            conn.close()




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
                if not rows:
                    continue
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

    def _extract_and_store_images(self, file_id: int, file_path: str) -> int:
        count = 0
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
                if not rows:
                    continue
                with conn:
                    conn.executemany(
                        """INSERT INTO extracted_images
                           (file_id, project_id, image_index, stored_path,
                            page_number, width, height,
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        rows
                    )
                count += len(rows)
        finally:
            conn.close()
        return count

    def _run_text_similarity(self, chunk_ids: list) -> int:
        if not chunk_ids:
            return 0

        conn = get_connection()
        total = len(chunk_ids)
        saved = 0
        BATCH = 500

        try:
            for start in range(0, total, BATCH):
                if self._cancelled:
                    break

                batch_ids    = chunk_ids[start: start + BATCH]
                placeholders = ",".join("?" * len(batch_ids))
                pct = 45 + int((start / max(total, 1)) * 30)
                self.progress_changed.emit(
                    pct, f"Text comparison {start}/{total}"
                )

                rows = conn.execute(
                    f"SELECT id, content, file_id FROM text_chunks WHERE id IN ({placeholders})",
                    batch_ids
                ).fetchall()
                if not rows:
                    continue

                rows  = [(r[0], r[1], r[2]) for r in rows]
                pairs = find_similar_text_batched(rows, self.text_threshold)

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
            if not images:
                return 0

            pairs = find_similar_images_batched(images, self.image_threshold)

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