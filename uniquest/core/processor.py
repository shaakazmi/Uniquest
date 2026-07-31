import os
import shutil
from pathlib import Path
from typing import List, Optional, Callable

from PyQt6.QtCore import QThread, pyqtSignal

from database.db import get_connection
from database.models import get_file_type, is_supported
from core.extractor import process_file_extraction
from core.similarity import (
    TextSimilarityEngine,
    ImageSimilarityEngine,
)


# ─────────────────────────────────────────────
#  FILE IMPORT HELPERS
# ─────────────────────────────────────────────
def get_project_copy_dir(project_id: int) -> Path:
    """Folder where copied files are stored"""
    from database.db import get_db_path
    base = Path(get_db_path()).parent / "projects" / str(project_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def add_files_to_project(
    project_id: int,
    file_paths: List[str],
    storage_mode: str = "reference",
) -> List[int]:
    """
    Register files into the DB for a project.
    storage_mode:
        'reference' → store original path only
        'copy'      → copy file into app folder first
    Returns list of new file IDs.
    """
    conn    = get_connection()
    cursor  = conn.cursor()
    new_ids = []

    for fp in file_paths:
        fp = str(fp)
        if not os.path.isfile(fp):
            print(f"  Skipping (not found): {fp}")
            continue

        if not is_supported(fp):
            print(f"  Skipping (unsupported): {fp}")
            continue

        file_name = Path(fp).name
        file_type = get_file_type(fp)
        file_size = os.path.getsize(fp)

        # Check for duplicate in this project
        cursor.execute("""
            SELECT id FROM files
            WHERE project_id = ? AND original_path = ?
        """, (project_id, fp))
        if cursor.fetchone():
            print(f"  Already added: {file_name}")
            continue

        stored_path = None

        # Copy file if needed
        if storage_mode == "copy":
            try:
                dest_dir    = get_project_copy_dir(project_id)
                stored_path = str(dest_dir / file_name)
                # Avoid name collision
                counter = 1
                base    = Path(file_name).stem
                ext     = Path(file_name).suffix
                while os.path.exists(stored_path):
                    stored_path = str(
                        dest_dir / f"{base}_{counter}{ext}"
                    )
                    counter += 1
                shutil.copy2(fp, stored_path)
            except Exception as e:
                print(f"  Copy error [{file_name}]: {e}")
                stored_path = None

        try:
            cursor.execute("""
                INSERT INTO files
                    (project_id, original_path, stored_path,
                     file_name, file_type, file_size,
                     storage_mode, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                project_id,
                fp,
                stored_path,
                file_name,
                file_type,
                file_size,
                storage_mode,
            ))
            new_id = cursor.lastrowid
            new_ids.append(new_id)
            print(f"  Added: {file_name} (id={new_id})")
        except Exception as e:
            print(f"  DB insert error [{file_name}]: {e}")

    # Update project file count
    cursor.execute("""
        UPDATE projects SET
            file_count = (
                SELECT COUNT(*) FROM files
                WHERE project_id = ?
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (project_id, project_id))

    conn.commit()
    conn.close()
    return new_ids


def remove_file_from_project(file_id: int) -> bool:
    """
    Remove a file from a project.
    If storage_mode is 'copy', delete the copied file too.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT project_id, stored_path, storage_mode, file_name
        FROM files WHERE id = ?
    """, (file_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    project_id   = row["project_id"]
    stored_path  = row["stored_path"]
    storage_mode = row["storage_mode"]

    # Delete copied file from disk
    if storage_mode == "copy" and stored_path:
        try:
            if os.path.exists(stored_path):
                os.remove(stored_path)
        except Exception as e:
            print(f"  File delete error: {e}")

    # Delete from DB (CASCADE removes chunks, images, similarities)
    cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))

    # Update project file count
    cursor.execute("""
        UPDATE projects SET
            file_count = (
                SELECT COUNT(*) FROM files
                WHERE project_id = ?
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (project_id, project_id))

    conn.commit()
    conn.close()
    return True


def get_files_for_project(project_id: int) -> List[dict]:
    """Get all files for a project"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM files
        WHERE project_id = ?
        ORDER BY added_at DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_files(project_id: int) -> List[dict]:
    """Get files that haven't been processed yet"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM files
        WHERE project_id = ? AND status = 'pending'
        ORDER BY added_at ASC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  PROJECT CRUD HELPERS
# ─────────────────────────────────────────────
def create_project(
    name: str,
    description: str = "",
    similarity_threshold: float = 0.70,
    storage_mode: str = "reference",
) -> int:
    """Create a new project. Returns new project ID."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projects
            (name, description, similarity_threshold, storage_mode)
        VALUES (?, ?, ?, ?)
    """, (name, description, similarity_threshold, storage_mode))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"✅ Project created: '{name}' (id={new_id})")
    return new_id


def update_project(
    project_id: int,
    name: str,
    description: str = "",
    similarity_threshold: float = 0.70,
    storage_mode: str = "reference",
) -> bool:
    """Update project details"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE projects SET
            name                 = ?,
            description          = ?,
            similarity_threshold = ?,
            storage_mode         = ?,
            updated_at           = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        name, description,
        similarity_threshold,
        storage_mode,
        project_id,
    ))
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def delete_project(project_id: int) -> bool:
    """
    Delete a project and all related data.
    Also removes copied files and extracted images from disk.
    """
    from database.db import get_db_path

    conn   = get_connection()
    cursor = conn.cursor()

    # Get all copied file paths
    cursor.execute("""
        SELECT stored_path, storage_mode
        FROM files
        WHERE project_id = ? AND storage_mode = 'copy'
    """, (project_id,))
    rows = cursor.fetchall()

    # Delete copied files from disk
    for row in rows:
        if row["stored_path"] and os.path.exists(row["stored_path"]):
            try:
                os.remove(row["stored_path"])
            except Exception:
                pass

    # Delete project copy directory
    copy_dir = get_project_copy_dir(project_id)
    if copy_dir.exists():
        try:
            shutil.rmtree(copy_dir)
        except Exception:
            pass

    # Delete extracted images directory
    base = Path(get_db_path()).parent
    img_dir = base / "extracted_images" / str(project_id)
    if img_dir.exists():
        try:
            shutil.rmtree(img_dir)
        except Exception:
            pass

    # Delete from DB (CASCADE handles children)
    cursor.execute(
        "DELETE FROM projects WHERE id = ?",
        (project_id,)
    )
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def get_all_projects() -> List[dict]:
    """Get all projects ordered by most recent"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.*,
            (SELECT COUNT(*) FROM text_similarities ts
             WHERE ts.project_id = p.id) AS text_sim_count,
            (SELECT COUNT(*) FROM image_similarities ims
             WHERE ims.project_id = p.id) AS img_sim_count,
            (SELECT COUNT(*) FROM analysis_runs ar
             WHERE ar.project_id = p.id
             AND ar.status = 'done') AS run_count
        FROM projects p
        ORDER BY p.updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project(project_id: int) -> Optional[dict]:
    """Get single project by ID"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM projects WHERE id = ?
    """, (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────
#  ANALYSIS RUN HELPERS
# ─────────────────────────────────────────────
def start_analysis_run(project_id: int) -> int:
    """Create a new analysis run record. Returns run ID."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO analysis_runs (project_id, status)
        VALUES (?, 'running')
    """, (project_id,))
    run_id = cursor.lastrowid

    # Set project status to scanning
    cursor.execute("""
        UPDATE projects SET status = 'scanning',
        updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (project_id,))

    conn.commit()
    conn.close()
    return run_id


def finish_analysis_run(
    run_id: int,
    project_id: int,
    text_found: int,
    img_found: int,
    files_processed: int,
    status: str = "done",
    error: Optional[str] = None,
):
    """Mark analysis run as complete"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE analysis_runs SET
            status                    = ?,
            completed_at              = CURRENT_TIMESTAMP,
            files_processed           = ?,
            text_similarities_found   = ?,
            image_similarities_found  = ?,
            error_message             = ?
        WHERE id = ?
    """, (
        status, files_processed,
        text_found, img_found,
        error, run_id,
    ))

    # Update project status
    cursor.execute("""
        UPDATE projects SET
            status     = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, project_id))

    conn.commit()
    conn.close()


def clear_project_results(project_id: int):
    """Clear all analysis results for a project (not files)"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM text_similarities WHERE project_id = ?
    """, (project_id,))
    cursor.execute("""
        DELETE FROM image_similarities WHERE project_id = ?
    """, (project_id,))
    cursor.execute("""
        DELETE FROM text_chunks WHERE project_id = ?
    """, (project_id,))
    cursor.execute("""
        DELETE FROM extracted_images WHERE project_id = ?
    """, (project_id,))
    # Reset file statuses
    cursor.execute("""
        UPDATE files SET
            status           = 'pending',
            text_extracted   = 0,
            images_extracted = 0,
            processed_at     = NULL,
            error_message    = NULL
        WHERE project_id = ?
    """, (project_id,))
    # Update project status
    cursor.execute("""
        UPDATE projects SET
            status     = 'idle',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (project_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  BACKGROUND WORKER THREAD
# ─────────────────────────────────────────────
class AnalysisWorker(QThread):
    """
    Runs the full analysis pipeline in a background thread:
      1. Extract text & images from all files
      2. Compute text similarity
      3. Compute image similarity
      4. Save results
      5. Emit signals for UI updates
    """

    # ── Signals ──
    progress_changed  = pyqtSignal(int, str)   # (percent, message)
    file_processed    = pyqtSignal(str, bool)   # (file_name, success)
    stage_changed     = pyqtSignal(str)          # stage label
    finished_ok       = pyqtSignal(int, int, int) # (files, text, img)
    finished_error    = pyqtSignal(str)           # error message
    log_message       = pyqtSignal(str)           # log line

    def __init__(
        self,
        project_id: int,
        text_threshold: float  = 0.70,
        image_threshold: float = 0.85,
        parent=None,
    ):
        super().__init__(parent)
        self.project_id      = project_id
        self.text_threshold  = text_threshold
        self.image_threshold = image_threshold
        self._cancelled      = False
        self.run_id          = None

    def cancel(self):
        """Request cancellation"""
        self._cancelled = True
        self.log_message.emit("⚠️ Cancellation requested...")

    def _log(self, msg: str):
        print(msg)
        self.log_message.emit(msg)

    def run(self):
        """Main worker entry point"""
        try:
            self._run_pipeline()
        except Exception as e:
            self.finished_error.emit(str(e))

    def _run_pipeline(self):
        project_id = self.project_id

        # ── Start run record ──
        self.run_id = start_analysis_run(project_id)
        self._log(f"🚀 Analysis started (run_id={self.run_id})")

        # ── Stage 1: Extract ──
        self.stage_changed.emit("Extracting files...")
        self.progress_changed.emit(0, "Loading files...")

        files = get_files_for_project(project_id)
        if not files:
            finish_analysis_run(
                self.run_id, project_id,
                0, 0, 0, "error",
                "No files in project."
            )
            self.finished_error.emit("No files in project.")
            return

        total         = len(files)
        files_done    = 0
        extract_errors = 0

        for i, file_row in enumerate(files):
            if self._cancelled:
                finish_analysis_run(
                    self.run_id, project_id,
                    0, 0, files_done,
                    "cancelled",
                )
                self.finished_error.emit("Analysis cancelled.")
                return

            file_id   = file_row["id"]
            file_name = file_row["file_name"]
            file_type = file_row["file_type"]

            # Use stored path if available, else original
            file_path = (
                file_row["stored_path"]
                if file_row["stored_path"]
                else file_row["original_path"]
            )

            # Skip if file no longer exists
            if not os.path.isfile(file_path):
                self._log(f"  ⚠️ File not found: {file_name}")
                self.file_processed.emit(file_name, False)
                extract_errors += 1
                continue

            pct = int((i / total) * 40)  # 0-40%
            self.progress_changed.emit(
                pct,
                f"Extracting {i+1}/{total}: {file_name}"
            )
            self._log(f"  [{i+1}/{total}] {file_name}")

            text_c, img_c = process_file_extraction(
                file_id, project_id, file_path, file_type
            )

            files_done += 1
            self.file_processed.emit(file_name, True)

        if self._cancelled:
            return

        # ── Stage 2: Text Similarity ──
        self.stage_changed.emit("Computing text similarity...")
        self.progress_changed.emit(40, "Analyzing text...")
        self._log("🔍 Computing text similarity...")

        def text_prog(pct):
            if self._cancelled:
                return
            mapped = 40 + int(pct * 0.25)   # 40-65%
            self.progress_changed.emit(
                mapped, f"Text similarity: {pct}%"
            )

        text_engine  = TextSimilarityEngine(
            project_id, self.text_threshold
        )
        text_results = text_engine.compute(
            progress_callback=text_prog
        )
        text_saved   = text_engine.save_results(text_results)
        self._log(f"  📝 {text_saved} text similarities saved")

        if self._cancelled:
            return

        # ── Stage 3: Image Similarity ──
        self.stage_changed.emit("Computing image similarity...")
        self.progress_changed.emit(65, "Analyzing images...")
        self._log("🖼️ Computing image similarity...")

        def img_prog(pct):
            if self._cancelled:
                return
            mapped = 65 + int(pct * 0.30)   # 65-95%
            self.progress_changed.emit(
                mapped, f"Image similarity: {pct}%"
            )

        img_engine  = ImageSimilarityEngine(
            project_id, self.image_threshold
        )
        img_results = img_engine.compute(
            progress_callback=img_prog
        )
        img_saved   = img_engine.save_results(img_results)
        self._log(f"  🖼️ {img_saved} image similarities saved")

        # ── Stage 4: Finish ──
        self.progress_changed.emit(100, "Complete!")
        self.stage_changed.emit("Done")

        finish_analysis_run(
            self.run_id,
            project_id,
            text_found       = text_saved,
            img_found        = img_saved,
            files_processed  = files_done,
            status           = "done",
        )

        self._log(
            f"✅ Analysis complete: "
            f"{files_done} files, "
            f"{text_saved} text matches, "
            f"{img_saved} image matches"
        )
        self.finished_ok.emit(files_done, text_saved, img_saved)


# ─────────────────────────────────────────────
#  DASHBOARD STATS
# ─────────────────────────────────────────────
def get_dashboard_stats() -> dict:
    """Get overall stats for the dashboard"""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS c FROM projects")
    total_projects = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM files")
    total_files = cursor.fetchone()["c"]

    cursor.execute(
        "SELECT COUNT(*) AS c FROM text_similarities"
    )
    total_text_sim = cursor.fetchone()["c"]

    cursor.execute(
        "SELECT COUNT(*) AS c FROM image_similarities"
    )
    total_img_sim = cursor.fetchone()["c"]

    cursor.execute("""
        SELECT COUNT(*) AS c FROM analysis_runs
        WHERE status = 'done'
    """)
    total_runs = cursor.fetchone()["c"]

    cursor.execute("""
        SELECT p.name, p.updated_at,
               p.file_count,
               p.status
        FROM projects p
        ORDER BY p.updated_at DESC
        LIMIT 5
    """)
    recent = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "total_projects":  total_projects,
        "total_files":     total_files,
        "total_text_sim":  total_text_sim,
        "total_img_sim":   total_img_sim,
        "total_runs":      total_runs,
        "grand_total_sim": total_text_sim + total_img_sim,
        "recent_projects": recent,
    }