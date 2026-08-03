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

        # ── PHASE 1: EXTRACTION (0–40%) ───────────────────────
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

        # ── PHASE 2: TEXT SIMILARITY (40–80%) ─────────────────
        self.progress.emit(40, "Comparing text...")
        text_count = self._run_text_similarity(all_chunk_ids)

        if self._cancelled:
            return

        # ── PHASE 3: IMAGE SIMILARITY (80–100%) ───────────────
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

                # get ids of inserted rows
                last_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
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
                self.progress.emit(pct, f"Text comparison {start}/{total} chunks")

                rows = conn.execute(
                    f"SELECT id, content, file_id FROM text_chunks WHERE id IN ({placeholders})",
                    batch_ids
                ).fetchall()

                if not rows:
                    continue

                rows = [(r[0], r[1], r[2]) for r in rows]
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