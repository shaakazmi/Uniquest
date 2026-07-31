import os
import numpy as np
from typing import List, Tuple, Dict
from pathlib import Path

from database.db import get_connection
from database.models import TextSimilarity, ImageSimilarity


# ─────────────────────────────────────────────
#  TEXT SIMILARITY ENGINE
# ─────────────────────────────────────────────
class TextSimilarityEngine:
    """
    Uses TF-IDF + Cosine Similarity to find
    similar text chunks across all files in a project.
    """

    def __init__(self, project_id: int, threshold: float = 0.70):
        self.project_id = project_id
        self.threshold  = threshold

    def load_chunks(self) -> Tuple[List[int], List[int], List[str]]:
        """
        Load all text chunks for this project from DB.
        Returns (chunk_ids, file_ids, contents)
        """
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_id, content
            FROM text_chunks
            WHERE project_id = ?
            ORDER BY file_id, chunk_index
        """, (self.project_id,))
        rows = cursor.fetchall()
        conn.close()

        chunk_ids = [r["id"]      for r in rows]
        file_ids  = [r["file_id"] for r in rows]
        contents  = [r["content"] for r in rows]
        return chunk_ids, file_ids, contents

    def compute(
        self,
        progress_callback=None
    ) -> List[TextSimilarity]:
        """
        Compute pairwise cosine similarity between all chunks.
        Only keeps pairs from DIFFERENT files above threshold.
        Returns list of TextSimilarity objects.
        """
        chunk_ids, file_ids, contents = self.load_chunks()

        if len(contents) < 2:
            print("  Not enough text chunks to compare.")
            return []

        print(f"  Computing text similarity for "
              f"{len(contents)} chunks...")

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            print("scikit-learn not installed.")
            return []

        # ── Build TF-IDF matrix ──
        vectorizer = TfidfVectorizer(
            min_df=1,
            stop_words="english",
            ngram_range=(1, 2),   # unigrams + bigrams
            max_features=10000,
        )
        try:
            tfidf_matrix = vectorizer.fit_transform(contents)
        except Exception as e:
            print(f"  TF-IDF error: {e}")
            return []

        n         = tfidf_matrix.shape[0]
        results   = []
        total_pairs = (n * (n - 1)) // 2
        checked     = 0

        # ── Batch cosine similarity (memory efficient) ──
        batch_size = 100
        for i in range(0, n, batch_size):
            batch      = tfidf_matrix[i:i + batch_size]
            sim_matrix = cosine_similarity(batch, tfidf_matrix)

            for local_i, row in enumerate(sim_matrix):
                global_i = i + local_i
                for j in range(global_i + 1, n):
                    checked += 1

                    # Skip same file
                    if file_ids[global_i] == file_ids[j]:
                        continue

                    score = float(row[j])
                    if score >= self.threshold:
                        results.append(TextSimilarity(
                            project_id       = self.project_id,
                            chunk_id_a       = chunk_ids[global_i],
                            chunk_id_b       = chunk_ids[j],
                            file_id_a        = file_ids[global_i],
                            file_id_b        = file_ids[j],
                            similarity_score = score,
                        ))

            # Progress callback every batch
            if progress_callback:
                pct = min(
                    int((i + batch_size) / n * 100), 100
                )
                progress_callback(pct)

        print(f"  ✅ Found {len(results)} similar text pairs "
              f"(threshold={self.threshold:.0%})")
        return results

    def save_results(
        self,
        results: List[TextSimilarity]
    ) -> int:
        """Save text similarity results to DB"""
        if not results:
            return 0

        conn   = get_connection()
        cursor = conn.cursor()

        # Clear old results for this project
        cursor.execute("""
            DELETE FROM text_similarities
            WHERE project_id = ?
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
                    r.project_id,
                    r.chunk_id_a,
                    r.chunk_id_b,
                    r.file_id_a,
                    r.file_id_b,
                    r.similarity_score,
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
    Uses perceptual hashing (pHash) to find
    similar images across all files in a project.
    Hash distance <= max_distance means similar.
    """

    def __init__(
        self,
        project_id: int,
        threshold: float = 0.85,
        max_distance: int = 10
    ):
        self.project_id   = project_id
        self.threshold    = threshold
        # Lower distance = more similar
        # 0  = identical
        # <=6  = very similar
        # <=10 = similar
        self.max_distance = max_distance

    def load_images(self) -> List[Dict]:
        """Load all extracted image records for this project"""
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_id, stored_path,
                   phash, ahash, dhash
            FROM extracted_images
            WHERE project_id = ?
            AND phash IS NOT NULL
        """, (self.project_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _hash_distance(
        self,
        hash_a: str,
        hash_b: str
    ) -> int:
        """
        Compute Hamming distance between two hex hash strings.
        Lower = more similar.
        """
        try:
            import imagehash
            h1 = imagehash.hex_to_hash(hash_a)
            h2 = imagehash.hex_to_hash(hash_b)
            return h1 - h2
        except Exception:
            return 999

    def _distance_to_score(self, distance: int) -> float:
        """
        Convert hash distance to similarity score (0.0 - 1.0).
        distance=0  → score=1.0 (identical)
        distance=64 → score=0.0 (completely different)
        """
        max_d = 64.0
        score = 1.0 - (distance / max_d)
        return max(0.0, min(1.0, score))

    def compute(
        self,
        progress_callback=None
    ) -> List[ImageSimilarity]:
        """
        Compare all image pairs using pHash distance.
        Returns list of ImageSimilarity objects above threshold.
        """
        images = self.load_images()

        if len(images) < 2:
            print("  Not enough images to compare.")
            return []

        print(f"  Computing image similarity for "
              f"{len(images)} images...")

        results = []
        n       = len(images)

        for i in range(n):
            img_a = images[i]
            for j in range(i + 1, n):
                img_b = images[j]

                # Skip same file
                if img_a["file_id"] == img_b["file_id"]:
                    continue

                # Skip if either hash is missing
                if not img_a["phash"] or not img_b["phash"]:
                    continue

                distance = self._hash_distance(
                    img_a["phash"],
                    img_b["phash"]
                )
                score = self._distance_to_score(distance)

                if score >= self.threshold:
                    results.append(ImageSimilarity(
                        project_id       = self.project_id,
                        image_id_a       = img_a["id"],
                        image_id_b       = img_b["id"],
                        file_id_a        = img_a["file_id"],
                        file_id_b        = img_b["file_id"],
                        similarity_score = score,
                        hash_distance    = distance,
                    ))

            # Progress callback
            if progress_callback:
                pct = int((i + 1) / n * 100)
                progress_callback(pct)

        print(f"  ✅ Found {len(results)} similar image pairs "
              f"(threshold={self.threshold:.0%})")
        return results

    def save_results(
        self,
        results: List[ImageSimilarity]
    ) -> int:
        """Save image similarity results to DB"""
        if not results:
            return 0

        conn   = get_connection()
        cursor = conn.cursor()

        # Clear old results
        cursor.execute("""
            DELETE FROM image_similarities
            WHERE project_id = ?
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
                    r.project_id,
                    r.image_id_a,
                    r.image_id_b,
                    r.file_id_a,
                    r.file_id_b,
                    r.similarity_score,
                    r.hash_distance,
                ))
                saved += 1
            except Exception as e:
                print(f"  Save image sim error: {e}")

        conn.commit()
        conn.close()
        return saved


# ─────────────────────────────────────────────
#  CLUSTER BUILDER
# ─────────────────────────────────────────────
def build_text_clusters(
    project_id: int
) -> List[List[Dict]]:
    """
    Group similar text pairs into clusters.
    A cluster = group of chunks that are all similar to each other.
    Returns list of clusters, each cluster is a list of chunk dicts.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    # Load all text similarities with chunk content & file names
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
            cb.page_number AS page_b
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
        ca = row["chunk_id_a"]
        cb = row["chunk_id_b"]
        union(ca, cb)
        pair_data.append(dict(row))

    # Group by cluster root
    clusters: Dict[int, List[Dict]] = {}
    seen_chunks = set()

    for pair in pair_data:
        root = find(pair["chunk_id_a"])
        if root not in clusters:
            clusters[root] = []

        # Add chunk_a
        if pair["chunk_id_a"] not in seen_chunks:
            clusters[root].append({
                "chunk_id":   pair["chunk_id_a"],
                "file_id":    pair["file_id_a"],
                "file_name":  pair["file_name_a"],
                "content":    pair["content_a"],
                "page":       pair["page_a"],
                "score":      pair["similarity_score"],
                "pair_id":    pair["id"],
                "reviewed":   pair["reviewed"],
                "type":       "text",
            })
            seen_chunks.add(pair["chunk_id_a"])

        # Add chunk_b
        if pair["chunk_id_b"] not in seen_chunks:
            clusters[root].append({
                "chunk_id":   pair["chunk_id_b"],
                "file_id":    pair["file_id_b"],
                "file_name":  pair["file_name_b"],
                "content":    pair["content_b"],
                "page":       pair["page_b"],
                "score":      pair["similarity_score"],
                "pair_id":    pair["id"],
                "reviewed":   pair["reviewed"],
                "type":       "text",
            })
            seen_chunks.add(pair["chunk_id_b"])

    return list(clusters.values())


def build_image_clusters(
    project_id: int
) -> List[List[Dict]]:
    """
    Group similar image pairs into clusters.
    Returns list of clusters.
    """
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
        ia = row["image_id_a"]
        ib = row["image_id_b"]
        union(ia, ib)
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
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE text_similarities
        SET reviewed = ?
        WHERE id = ?
    """, (1 if reviewed else 0, pair_id))
    conn.commit()
    conn.close()


def mark_image_pair_reviewed(pair_id: int, reviewed: bool = True):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE image_similarities
        SET reviewed = ?
        WHERE id = ?
    """, (1 if reviewed else 0, pair_id))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  STATS HELPERS
# ─────────────────────────────────────────────
def get_similarity_stats(project_id: int) -> Dict:
    """Get summary stats for a project's similarity results"""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*)                                    AS total_text,
            SUM(CASE WHEN reviewed=1 THEN 1 ELSE 0 END) AS reviewed_text,
            AVG(similarity_score)                       AS avg_text_score,
            MAX(similarity_score)                       AS max_text_score
        FROM text_similarities
        WHERE project_id = ?
    """, (project_id,))
    text_row = cursor.fetchone()

    cursor.execute("""
        SELECT
            COUNT(*)                                    AS total_img,
            SUM(CASE WHEN reviewed=1 THEN 1 ELSE 0 END) AS reviewed_img,
            AVG(similarity_score)                       AS avg_img_score,
            MAX(similarity_score)                       AS max_img_score
        FROM image_similarities
        WHERE project_id = ?
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
        "grand_total":   (text_row["total_text"] or 0)
                       + (img_row["total_img"]   or 0),
    }