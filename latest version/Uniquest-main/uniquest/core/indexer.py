"""
File Indexer for Uniquest.
- Computes SHA-256 fingerprint of each file
- Caches text chunks + image hashes per unique file
- On re-import: skips extraction, restores from cache
- If file changes (edit, resave) → hash changes → re-extracts
"""

import hashlib
from pathlib import Path
from database.db import get_connection


BUFFER_SIZE = 1024 * 1024   # 1 MB


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 of file bytes. Returns hex string (64 chars)."""
    sha = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return ""


def lookup_cached_file(content_hash: str) -> dict | None:
    """
    Look up a file by its content hash in the index.
    Returns dict with index metadata or None.
    """
    if not content_hash:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM file_index WHERE content_hash = ?",
            (content_hash,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def register_file_in_index(
    content_hash: str,
    file_name:    str,
    file_type:    str,
    file_size:    int,
) -> int:
    """Create a new file_index entry. Returns the index_id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO file_index
               (content_hash, file_name, file_type, file_size)
               VALUES (?, ?, ?, ?)""",
            (content_hash, file_name, file_type, file_size)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def bump_index_usage(index_id: int) -> None:
    """Update last_used_at and increment use_count."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE file_index
               SET use_count = use_count + 1,
                   last_used_at = datetime('now')
               WHERE id = ?""",
            (index_id,)
        )
        conn.commit()
    finally:
        conn.close()


def save_cached_chunks(index_id: int, chunks: list) -> None:
    """
    Save extracted text chunks to the cache.
    chunks: list of objects with .chunk_index, .content, .page_number,
                                  .chunk_type, and word count via split.
    """
    if not chunks:
        return
    rows = [
        (index_id, ch.chunk_index, ch.content,
         ch.page_number, ch.chunk_type,
         len(ch.content.split()))
        for ch in chunks
    ]
    conn = get_connection()
    try:
        conn.executemany(
            """INSERT INTO cached_text_chunks
               (file_index_id, chunk_index, content,
                page_number, chunk_type, word_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            rows
        )
        conn.execute(
            """UPDATE file_index SET text_chunk_count = (
                   SELECT COUNT(*) FROM cached_text_chunks WHERE file_index_id = ?
               ) WHERE id = ?""",
            (index_id, index_id)
        )
        conn.commit()
    finally:
        conn.close()


def save_cached_images(index_id: int, images: list) -> None:
    """
    Save extracted image data to the cache.
    images: list of objects with .image_index, .image_path, .page_number,
                                  .width, .height, .phash, .ahash, .dhash.
    """
    if not images:
        return
    rows = [
        (index_id, img.image_index, img.image_path,
         img.page_number, img.width, img.height,
         img.phash, img.ahash, img.dhash)
        for img in images
    ]
    conn = get_connection()
    try:
        conn.executemany(
            """INSERT INTO cached_images
               (file_index_id, image_index, stored_path,
                page_number, width, height,
                phash, ahash, dhash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows
        )
        conn.execute(
            """UPDATE file_index SET image_count = (
                   SELECT COUNT(*) FROM cached_images WHERE file_index_id = ?
               ) WHERE id = ?""",
            (index_id, index_id)
        )
        conn.commit()
    finally:
        conn.close()


def restore_chunks_to_project(
    index_id:   int,
    file_id:    int,
    project_id: int,
) -> list[int]:
    """
    Copy cached chunks to the project's text_chunks table.
    Returns list of new chunk_ids.
    """
    conn = get_connection()
    new_ids = []
    try:
        cached = conn.execute(
            """SELECT chunk_index, content, page_number, chunk_type, word_count
               FROM cached_text_chunks
               WHERE file_index_id = ?
               ORDER BY chunk_index""",
            (index_id,)
        ).fetchall()

        if not cached:
            return []

        rows = [
            (file_id, project_id,
             r["chunk_index"], r["content"],
             r["page_number"], r["chunk_type"],
             r["word_count"])
            for r in cached
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
            new_ids = list(range(first_id, last_id + 1))
    finally:
        conn.close()
    return new_ids


def restore_images_to_project(
    index_id:   int,
    file_id:    int,
    project_id: int,
) -> int:
    """
    Copy cached images to the project's extracted_images table.
    Returns count of images restored.
    """
    conn = get_connection()
    try:
        cached = conn.execute(
            """SELECT image_index, stored_path, page_number,
                      width, height, phash, ahash, dhash
               FROM cached_images
               WHERE file_index_id = ?
               ORDER BY image_index""",
            (index_id,)
        ).fetchall()

        if not cached:
            return 0

        rows = [
            (file_id, project_id,
             r["image_index"], r["stored_path"],
             r["page_number"], r["width"], r["height"],
             r["phash"], r["ahash"], r["dhash"], 0)
            for r in cached
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
        return len(rows)
    finally:
        conn.close()


def get_index_stats() -> dict:
    """Return statistics about the index."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COUNT(*)               AS total_files,
                      COALESCE(SUM(text_chunk_count), 0) AS total_chunks,
                      COALESCE(SUM(image_count), 0)      AS total_images,
                      COALESCE(SUM(file_size), 0)        AS total_bytes,
                      COALESCE(SUM(use_count - 1), 0)    AS cache_hits
               FROM file_index"""
        ).fetchone()
        return {
            "total_files":  row["total_files"]  if row else 0,
            "total_chunks": row["total_chunks"] if row else 0,
            "total_images": row["total_images"] if row else 0,
            "total_bytes":  row["total_bytes"]  if row else 0,
            "cache_hits":   row["cache_hits"]   if row else 0,
        }
    finally:
        conn.close()


def clear_index() -> None:
    """Delete the entire file index (cache)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM cached_text_chunks")
        conn.execute("DELETE FROM cached_images")
        conn.execute("DELETE FROM file_index")
        conn.commit()
    finally:
        conn.close()