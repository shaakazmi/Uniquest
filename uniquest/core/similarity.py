import os
import numpy as np
from typing import List, Tuple, Dict
from pathlib import Path
from difflib import SequenceMatcher

from database.db import get_connection
from database.models import TextSimilarity, ImageSimilarity


# ─────────────────────────────────────────────
#  TEXT SIMILARITY ENGINE
# ─────────────────────────────────────────────
class TextSimilarityEngine:
    """
    Finds similar text chunks using:
      - TF-IDF + Cosine Similarity (for long text)
      - Fuzzy string matching (for short text like table cells)
    Detects duplicates BOTH within-file AND across-files.
    """

    def __init__(self, project_id: int, threshold: float = 0.70):
        self.project_id = project_id
        self.threshold  = threshold

    def load_chunks(self) -> Tuple[List[int], List[int], List[str], List[str]]:
        """Load all text chunks. Returns (ids, file_ids, contents, types)"""
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_id, content, chunk_type
            FROM text_chunks
            WHERE project_id = ?
            ORDER BY file_id, chunk_index
        """, (self.project_id,))
        rows = cursor.fetchall()
        conn.close()

        chunk_ids = [r["id"]         for r in rows]
        file_ids  = [r["file_id"]    for r in rows]
        contents  = [r["content"]    for r in rows]
        types     = [r["chunk_type"] for r in rows]
        return chunk_ids, file_ids, contents, types

    def _fuzzy_ratio(self, a: str, b: str) -> float:
        """String similarity ratio (0.0 - 1.0)"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def compute(self, progress_callback=None) -> List[TextSimilarity]:
        """
        Compute similarity between all chunks.
        Uses TF-IDF for long text and fuzzy matching for short entries.
        Detects duplicates within-file AND across-file.
        """
        chunk_ids, file_ids, contents, types = self.load_chunks()

        if len(contents) < 2:
            print("  Not enough text chunks to compare.")
            return []

        print(f"  Analyzing {len(contents)} text chunks...")

        # ── Separate long text from short entries ──
        long_indices  = []
        short_indices = []
        for i, content in enumerate(contents):
            wc = len(content.split())
            if wc >= 6:
                long_indices.append(i)
            else:
                short_indices.append(i)

        results: List[TextSimilarity] = []
        seen_pairs: set = set()   # avoid duplicate pairs

        def add_result(idx_a: int, idx_b: int, score: float):
            """Add a result, avoiding duplicates"""
            # Normalize pair order
            if idx_a > idx_b:
                idx_a, idx_b = idx_b, idx_a
            key = (chunk_ids[idx_a], chunk_ids[idx_b])
            if key in seen_pairs:
                return
            seen_pairs.add(key)
            results.append(TextSimilarity(
                project_id       = self.project_id,
                chunk_id_a       = chunk_ids[idx_a],
                chunk_id_b       = chunk_ids[idx_b],
                file_id_a        = file_ids[idx_a],
                file_id_b        = file_ids[idx_b],
                similarity_score = score,
            ))

        # ── STAGE 1: TF-IDF for long text ──
        if len(long_indices) >= 2:
            print(f"  Stage 1: TF-IDF on {len(long_indices)} long chunks...")
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity

                long_contents = [contents[i] for i in long_indices]
                vectorizer = TfidfVectorizer(
                    min_df=1,
                    stop_words="english",
                    ngram_range=(1, 2),
                    max_features=10000,
                )
                try:
                    tfidf_matrix = vectorizer.fit_transform(long_contents)
                    n = tfidf_matrix.shape[0]

                    batch_size = 100
                    for i in range(0, n, batch_size):
                        batch = tfidf_matrix[i:i + batch_size]
                        sim_matrix = cosine_similarity(batch, tfidf_matrix)

                        for local_i, row in enumerate(sim_matrix):
                            global_i = i + local_i
                            orig_i   = long_indices[global_i]
                            for j in range(global_i + 1, n):
                                score = float(row[j])
                                if score >= self.threshold:
                                    orig_j = long_indices[j]
                                    add_result(orig_i, orig_j, score)

                        if progress_callback:
                            pct = min(int((i + batch_size) / n * 40), 40)
                            progress_callback(pct)
                except Exception as e:
                    print(f"  TF-IDF error: {e}")
            except ImportError:
                print("  scikit-learn not available")

        # ── STAGE 2: Fuzzy matching for short text ──
        # Short-to-short comparison
        if len(short_indices) >= 2:
            print(f"  Stage 2: Fuzzy matching on {len(short_indices)} short entries...")
            # Use slightly lower threshold for short strings
            short_threshold = max(0.75, self.threshold)

            n = len(short_indices)
            for i in range(n):
                orig_i = short_indices[i]
                content_i = contents[orig_i]

                for j in range(i + 1, n):
                    orig_j = short_indices[j]
                    content_j = contents[orig_j]

                    # Quick length check — skip if too different
                    len_ratio = min(len(content_i), len(content_j)) / \
                                max(len(content_i), len(content_j), 1)
                    if len_ratio < 0.5:
                        continue

                    score = self._fuzzy_ratio(content_i, content_j)
                    if score >= short_threshold:
                        add_result(orig_i, orig_j, score)

                if progress_callback and i % 50 == 0:
                    pct = 40 + int((i / n) * 30)
                    progress_callback(min(pct, 70))

        # ── STAGE 3: Short-to-long substring matches ──
        # (Find short entries that appear inside long text)
        if short_indices and long_indices:
            print(f"  Stage 3: Cross matching short vs long...")
            for si in short_indices:
                short_txt = contents[si].lower().strip()
                if len(short_txt) < 4:
                    continue

                for li in long_indices:
                    long_txt = contents[li].lower()
                    if short_txt in long_txt:
                        # Substring match — strong signal
                        add_result(si, li, 0.85)

        print(f"  Found {len(results)} similar pairs (threshold={self.threshold:.0%})")
        return results

    def save_results(self, results: List[TextSimilarity]) -> int:
        if not results:
            return 0

        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM text_similarities WHERE project_id = ?
        """, (self.project_id,))

        saved = 0
        for r in results:
            try:
                cursor.execute("""
                    INSERT INTO text_similarities
                        (project_id, chunk_id_a, chunk_id_b,
                         file_id_a, file_id_b, similarity_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    r.project_id, r.chunk_id_a, r.chunk_id_b,
                    r.file_id_a,  r.file_id_b,  r.similarity_score,
                ))
                saved += 1
            except Exception as e:
                print(f"  Save text sim error: {e}")

        conn.commit()
        conn.close()
        return saved


# ─────────────────────────────────────────────
#  IMAGE SIMILARITY ENGINE
# ─────────────────────────────────────────────
class ImageSimilarityEngine:
    """
    Finds similar images using perceptual hash (pHash).
    Detects within-file AND across-file duplicates.
    """

    def __init__(
        self,
        project_id: int,
        threshold: float = 0.85,
        max_distance: int = 10,
    ):
        self.project_id   = project_id
        self.threshold    = threshold
        self.max_distance = max_distance

    def load_images(self) -> List[Dict]:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_id, stored_path, phash, ahash, dhash
            FROM extracted_images
            WHERE project_id = ?
            AND phash IS NOT NULL
        """, (self.project_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _hash_distance(self, hash_a: str, hash_b: str) -> int:
        try:
            import imagehash
            h1 = imagehash.hex_to_hash(hash_a)
            h2 = imagehash.hex_to_hash(hash_b)
            return h1 - h2
        except Exception:
            return 999

    def _distance_to_score(self, distance: int) -> float:
        max_d = 64.0
        score = 1.0 - (distance / max_d)
        return max(0.0, min(1.0, score))

    def compute(self, progress_callback=None) -> List[ImageSimilarity]:
        images = self.load_images()

        if len(images) < 2:
            print("  Not enough images to compare.")
            return []

        print(f"  Analyzing {len(images)} images...")

        results = []
        n = len(images)
        seen_pairs = set()

        for i in range(n):
            img_a = images[i]
            for j in range(i + 1, n):
                img_b = images[j]

                if not img_a["phash"] or not img_b["phash"]:
                    continue

                distance = self._hash_distance(img_a["phash"], img_b["phash"])
                score = self._distance_to_score(distance)

                if score >= self.threshold:
                    key = (img_a["id"], img_b["id"])
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)

                    results.append(ImageSimilarity(
                        project_id       = self.project_id,
                        image_id_a       = img_a["id"],
                        image_id_b       = img_b["id"],
                        file_id_a        = img_a["file_id"],
                        file_id_b        = img_b["file_id"],
                        similarity_score = score,
                        hash_distance    = distance,
                    ))

            if progress_callback:
                pct = int((i + 1) / n * 100)
                progress_callback(pct)

        print(f"  Found {len(results)} similar image pairs (threshold={self.threshold:.0%})")
        return results

    def save_results(self, results: List[ImageSimilarity]) -> int:
        if not results:
            return 0

        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM image_similarities WHERE project_id = ?
        """, (self.project_id,))

        saved = 0
        for r in results:
            try:
                cursor.execute("""
                    INSERT INTO image_similarities
                        (project_id, image_id_a, image_id_b,
                         file_id_a, file_id_b,
                         similarity_score, hash_distance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.project_id, r.image_id_a, r.image_id_b,
                    r.file_id_a,  r.file_id_b,
                    r.similarity_score, r.hash_distance,
                ))
                saved += 1
            except Exception as e:
                print(f"  Save image sim error: {e}")

        conn.commit()
        conn.close()
        return saved


# ─────────────────────────────────────────────
#  CLUSTER BUILDER — TEXT
# ─────────────────────────────────────────────
def build_text_clusters(project_id: int) -> List[List[Dict]]:
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ts.id,
            ts.chunk_id_a,
            ts.chunk_id_b,
            ts.file_id_a,
            ts.file_id_b,
            ts.similarity_score,
            ts.reviewed,
            fa.file_name  AS file_name_a,
            fb.file_name  AS file_name_b,
            ca.content    AS content_a,
            cb.content    AS content_b,
            ca.page_number AS page_a,
            cb.page_number AS page_b,
            ca.chunk_type  AS type_a,
            cb.chunk_type  AS type_b
        FROM text_similarities ts
        JOIN files fa ON fa.id = ts.file_id_a
        JOIN files fb ON fb.id = ts.file_id_b
        JOIN text_chunks ca ON ca.id = ts.chunk_id_a
        JOIN text_chunks cb ON cb.id = ts.chunk_id_b
        WHERE ts.project_id = ?
        ORDER BY ts.similarity_score DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()

    # Union-Find clustering
    parent: Dict[int, int] = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    pair_data = []
    for row in rows:
        union(row["chunk_id_a"], row["chunk_id_b"])
        pair_data.append(dict(row))

    clusters: Dict[int, List[Dict]] = {}
    seen_chunks = set()

    for pair in pair_data:
        root = find(pair["chunk_id_a"])
        if root not in clusters:
            clusters[root] = []

        if pair["chunk_id_a"] not in seen_chunks:
            clusters[root].append({
                "chunk_id":  pair["chunk_id_a"],
                "file_id":   pair["file_id_a"],
                "file_name": pair["file_name_a"],
                "content":   pair["content_a"],
                "page":      pair["page_a"],
                "type":      pair["type_a"],
                "score":     pair["similarity_score"],
                "pair_id":   pair["id"],
                "reviewed":  pair["reviewed"],
            })
            seen_chunks.add(pair["chunk_id_a"])

        if pair["chunk_id_b"] not in seen_chunks:
            clusters[root].append({
                "chunk_id":  pair["chunk_id_b"],
                "file_id":   pair["file_id_b"],
                "file_name": pair["file_name_b"],
                "content":   pair["content_b"],
                "page":      pair["page_b"],
                "type":      pair["type_b"],
                "score":     pair["similarity_score"],
                "pair_id":   pair["id"],
                "reviewed":  pair["reviewed"],
            })
            seen_chunks.add(pair["chunk_id_b"])

    return list(clusters.values())


# ─────────────────────────────────────────────
#  CLUSTER BUILDER — IMAGES
# ─────────────────────────────────────────────
def build_image_clusters(project_id: int) -> List[List[Dict]]:
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ims.id,
            ims.image_id_a,
            ims.image_id_b,
            ims.file_id_a,
            ims.file_id_b,
            ims.similarity_score,
            ims.hash_distance,
            ims.reviewed,
            fa.file_name   AS file_name_a,
            fb.file_name   AS file_name_b,
            ia.stored_path AS image_path_a,
            ib.stored_path AS image_path_b,
            ia.width       AS width_a,
            ia.height      AS height_a,
            ib.width       AS width_b,
            ib.height      AS height_b
        FROM image_similarities ims
        JOIN files fa ON fa.id = ims.file_id_a
        JOIN files fb ON fb.id = ims.file_id_b
        JOIN extracted_images ia ON ia.id = ims.image_id_a
        JOIN extracted_images ib ON ib.id = ims.image_id_b
        WHERE ims.project_id = ?
        ORDER BY ims.similarity_score DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()

    parent: Dict[int, int] = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    pair_data = []
    for row in rows:
        union(row["image_id_a"], row["image_id_b"])
        pair_data.append(dict(row))

    clusters: Dict[int, List[Dict]] = {}
    seen_images = set()

    for pair in pair_data:
        root = find(pair["image_id_a"])
        if root not in clusters:
            clusters[root] = []

        if pair["image_id_a"] not in seen_images:
            clusters[root].append({
                "image_id":  pair["image_id_a"],
                "file_id":   pair["file_id_a"],
                "file_name": pair["file_name_a"],
                "img_path":  pair["image_path_a"],
                "width":     pair["width_a"],
                "height":    pair["height_a"],
                "score":     pair["similarity_score"],
                "distance":  pair["hash_distance"],
                "pair_id":   pair["id"],
                "reviewed":  pair["reviewed"],
                "type":      "image",
            })
            seen_images.add(pair["image_id_a"])

        if pair["image_id_b"] not in seen_images:
            clusters[root].append({
                "image_id":  pair["image_id_b"],
                "file_id":   pair["file_id_b"],
                "file_name": pair["file_name_b"],
                "img_path":  pair["image_path_b"],
                "width":     pair["width_b"],
                "height":    pair["height_b"],
                "score":     pair["similarity_score"],
                "distance":  pair["hash_distance"],
                "pair_id":   pair["id"],
                "reviewed":  pair["reviewed"],
                "type":      "image",
            })
            seen_images.add(pair["image_id_b"])

    return list(clusters.values())


# ─────────────────────────────────────────────
#  MARK AS REVIEWED
# ─────────────────────────────────────────────
def mark_text_pair_reviewed(pair_id: int, reviewed: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE text_similarities SET reviewed = ? WHERE id = ?
    """, (1 if reviewed else 0, pair_id))
    conn.commit()
    conn.close()


def mark_image_pair_reviewed(pair_id: int, reviewed: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE image_similarities SET reviewed = ? WHERE id = ?
    """, (1 if reviewed else 0, pair_id))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  STATS HELPERS
# ─────────────────────────────────────────────
def get_similarity_stats(project_id: int) -> Dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*)                                    AS total_text,
            SUM(CASE WHEN reviewed=1 THEN 1 ELSE 0 END) AS reviewed_text,
            AVG(similarity_score)                       AS avg_text_score,
            MAX(similarity_score)                       AS max_text_score
        FROM text_similarities WHERE project_id = ?
    """, (project_id,))
    text_row = cursor.fetchone()

    cursor.execute("""
        SELECT
            COUNT(*)                                    AS total_img,
            SUM(CASE WHEN reviewed=1 THEN 1 ELSE 0 END) AS reviewed_img,
            AVG(similarity_score)                       AS avg_img_score,
            MAX(similarity_score)                       AS max_img_score
        FROM image_similarities WHERE project_id = ?
    """, (project_id,))
    img_row = cursor.fetchone()
    conn.close()

    return {
        "text_total":    text_row["total_text"]    or 0,
        "text_reviewed": text_row["reviewed_text"] or 0,
        "text_avg":      round(text_row["avg_text_score"] or 0, 3),
        "text_max":      round(text_row["max_text_score"] or 0, 3),
        "img_total":     img_row["total_img"]      or 0,
        "img_reviewed":  img_row["reviewed_img"]   or 0,
        "img_avg":       round(img_row["avg_img_score"] or 0, 3),
        "img_max":       round(img_row["max_img_score"] or 0, 3),
        "grand_total":   (text_row["total_text"] or 0) + (img_row["total_img"] or 0),
    }