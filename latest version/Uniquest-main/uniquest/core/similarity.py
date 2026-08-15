"""
Similarity engine for Uniquest.

Text: TF-IDF + cosine + fuzzy matching
Image: Multi-hash + color fingerprint verification
Clustering: Union-Find
Statistics: Summary queries
"""

from difflib import SequenceMatcher

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False


# ═════════════════════════════════════════════
# TEXT SIMILARITY (TF-IDF + Fuzzy)
# ═════════════════════════════════════════════

def find_similar_text_batched(
    rows: list,
    threshold: float = 0.75,
) -> list:
    """
    Find similar text pairs from a list of chunks.

    Args:
        rows: list of tuples (chunk_id, content, file_id)
        threshold: minimum similarity score (0.0 - 1.0)

    Returns:
        list of dicts with chunk_id_a, chunk_id_b, file_id_a, file_id_b, score
    """
    if not rows or len(rows) < 2:
        return []

    long_rows  = []
    short_rows = []

    for r in rows:
        chunk_id, content, file_id = r
        if not content:
            continue
        wc = len(content.split())
        if wc >= 6:
            long_rows.append((chunk_id, content, file_id))
        elif wc >= 2:
            short_rows.append((chunk_id, content, file_id))

    pairs = []
    seen = set()

    def _add_pair(a_id, b_id, a_file, b_file, score):
        if a_id == b_id:
            return
        key = (min(a_id, b_id), max(a_id, b_id))
        if key in seen:
            return
        seen.add(key)
        pairs.append({
            "chunk_id_a": min(a_id, b_id),
            "chunk_id_b": max(a_id, b_id),
            "file_id_a":  a_file if a_id < b_id else b_file,
            "file_id_b":  b_file if a_id < b_id else a_file,
            "score":      round(float(score), 4),
        })

    # Long text: TF-IDF cosine
    if long_rows and SKLEARN_OK:
        try:
            texts = [r[1] for r in long_rows]
            vec = TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=10000,
                lowercase=True,
            )
            matrix = vec.fit_transform(texts)
            sim = cosine_similarity(matrix)

            n = len(long_rows)
            for i in range(n):
                for j in range(i + 1, n):
                    score = float(sim[i, j])
                    if score >= threshold:
                        _add_pair(
                            long_rows[i][0], long_rows[j][0],
                            long_rows[i][2], long_rows[j][2],
                            score,
                        )
        except Exception as e:
            print(f"TF-IDF error: {e}")

    elif long_rows:
        n = len(long_rows)
        for i in range(n):
            for j in range(i + 1, n):
                s = SequenceMatcher(
                    None, long_rows[i][1], long_rows[j][1]
                ).ratio()
                if s >= threshold:
                    _add_pair(
                        long_rows[i][0], long_rows[j][0],
                        long_rows[i][2], long_rows[j][2],
                        s,
                    )

    # Short text: fuzzy SequenceMatcher
    short_threshold = max(0.75, threshold)

    if short_rows:
        n = len(short_rows)
        for i in range(n):
            for j in range(i + 1, n):
                a = short_rows[i][1]
                b = short_rows[j][1]
                la, lb = len(a), len(b)
                if la == 0 or lb == 0:
                    continue
                if min(la, lb) / max(la, lb) < 0.5:
                    continue
                s = SequenceMatcher(None, a, b).ratio()
                if s >= short_threshold:
                    _add_pair(
                        short_rows[i][0], short_rows[j][0],
                        short_rows[i][2], short_rows[j][2],
                        s,
                    )

    # Cross-match: short in long
    if short_rows and long_rows:
        for s_id, s_text, s_file in short_rows:
            s_lower = s_text.lower()
            if len(s_lower) < 3:
                continue
            for l_id, l_text, l_file in long_rows:
                if s_lower in l_text.lower():
                    _add_pair(s_id, l_id, s_file, l_file, 0.85)

    return pairs


# ═════════════════════════════════════════════
# IMAGE SIMILARITY (Multi-Hash + Color)
# ═════════════════════════════════════════════

def _hamming_distance(hash_a: str, hash_b: str) -> int:
    """Compute Hamming distance between two hex hash strings."""
    if not hash_a or not hash_b:
        return 64
    try:
        int_a = int(hash_a, 16)
        int_b = int(hash_b, 16)
        return bin(int_a ^ int_b).count("1")
    except Exception:
        if len(hash_a) != len(hash_b):
            return 64
        return sum(c1 != c2 for c1, c2 in zip(hash_a, hash_b))


def _color_fingerprint(image_path: str) -> tuple:
    """
    Returns a color fingerprint: (avg_r, avg_g, avg_b, saturation, is_grayscale).
    Used to distinguish colorful images from black/white text logos.
    """
    try:
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        img = img.resize((32, 32))
        pixels = list(img.getdata())
        n = len(pixels)
        if n == 0:
            return None

        r_sum = g_sum = b_sum = 0
        sat_sum = 0.0
        for r, g, b in pixels:
            r_sum += r
            g_sum += g
            b_sum += b
            mx = max(r, g, b)
            mn = min(r, g, b)
            if mx > 0:
                sat_sum += (mx - mn) / mx

        avg_r = r_sum / n
        avg_g = g_sum / n
        avg_b = b_sum / n
        saturation = sat_sum / n
        is_grayscale = saturation < 0.10

        return (avg_r, avg_g, avg_b, saturation, is_grayscale)
    except Exception:
        return None


def _color_similar(fp_a: tuple, fp_b: tuple) -> bool:
    """Return True if two color fingerprints are similar enough."""
    if fp_a is None or fp_b is None:
        return True  # Can't decide — allow to fall through to hash checks

    r_a, g_a, b_a, sat_a, gray_a = fp_a
    r_b, g_b, b_b, sat_b, gray_b = fp_b

    # One is grayscale, other is colorful → definitely NOT similar
    if gray_a != gray_b:
        return False

    # Color distance in RGB space
    color_dist = ((r_a - r_b) ** 2 + (g_a - g_b) ** 2 + (b_a - b_b) ** 2) ** 0.5
    if color_dist > 90:
        return False

    # Saturation difference too large
    if abs(sat_a - sat_b) > 0.35:
        return False

    return True


def find_similar_images_batched(
    images: list,
    threshold: float = 0.85,
) -> list:
    """
    Find similar image pairs using MULTI-HASH + COLOR verification.
    Prevents false positives on logos, text-on-white, and colorful/BW mixes.

    Args:
        images: list of tuples (image_id, file_id, phash)
        threshold: minimum similarity score (0.0 - 1.0)

    Returns:
        list of dicts with image_id_a, image_id_b, file_id_a, file_id_b,
        score, distance
    """
    if not images or len(images) < 2:
        return []

    # Fetch full image data from DB
    from database.db import get_connection
    image_ids = [img[0] for img in images]
    placeholders = ",".join("?" * len(image_ids))
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT id, file_id, phash, ahash, dhash,
                       width, height, stored_path
                FROM extracted_images
                WHERE id IN ({placeholders})""",
            image_ids
        ).fetchall()
    finally:
        conn.close()

    full_images = [
        {
            "id":      r["id"],
            "file_id": r["file_id"],
            "phash":   r["phash"],
            "ahash":   r["ahash"],
            "dhash":   r["dhash"],
            "width":   r["width"]  or 0,
            "height":  r["height"] or 0,
            "path":    r["stored_path"],
        }
        for r in rows
        if r["phash"]
    ]

    if len(full_images) < 2:
        return []

    # Cache color fingerprints
    color_cache = {}

    def get_color(img):
        if img["id"] in color_cache:
            return color_cache[img["id"]]
        fp = _color_fingerprint(img["path"]) if img["path"] else None
        color_cache[img["id"]] = fp
        return fp

    pairs = []
    seen = set()
    n = len(full_images)

    # Strict thresholds — only near-identical images match
    PHASH_MAX_DIST = 14      # out of 64
    AHASH_MAX_DIST = 10
    DHASH_MAX_DIST = 8

    for i in range(n):
        img_a = full_images[i]
        for j in range(i + 1, n):
            img_b = full_images[j]

            # ── Aspect ratio check ─────────────────────────────
            if img_a["width"] and img_a["height"] and img_b["width"] and img_b["height"]:
                aspect_a = img_a["width"]  / img_a["height"]
                aspect_b = img_b["width"]  / img_b["height"]
                if aspect_a > 0 and aspect_b > 0:
                    ratio = min(aspect_a, aspect_b) / max(aspect_a, aspect_b)
                    if ratio < 0.55:
                        continue

            # ── pHash primary check ────────────────────────────
            p_dist = _hamming_distance(img_a["phash"], img_b["phash"])
            if p_dist > PHASH_MAX_DIST:
                continue

            # ── aHash secondary check ──────────────────────────
            if img_a["ahash"] and img_b["ahash"]:
                a_dist = _hamming_distance(img_a["ahash"], img_b["ahash"])
                if a_dist > AHASH_MAX_DIST:
                    continue
            else:
                a_dist = p_dist

            # ── dHash tertiary check ───────────────────────────
            if img_a["dhash"] and img_b["dhash"]:
                d_dist = _hamming_distance(img_a["dhash"], img_b["dhash"])
                if d_dist > DHASH_MAX_DIST:
                    continue
            else:
                d_dist = p_dist

            # ── COLOR CHECK (kills the logo false-positives) ──
            fp_a = get_color(img_a)
            fp_b = get_color(img_b)
            if not _color_similar(fp_a, fp_b):
                continue

            # ── Combined score ─────────────────────────────────
            avg_dist = (p_dist + a_dist + d_dist) / 3.0
            score = 1.0 - (avg_dist / 64.0)

            if score >= threshold:
                id_a, id_b = img_a["id"], img_b["id"]
                key = (min(id_a, id_b), max(id_a, id_b))
                if key in seen:
                    continue
                seen.add(key)
                pairs.append({
                    "image_id_a": min(id_a, id_b),
                    "image_id_b": max(id_a, id_b),
                    "file_id_a":  img_a["file_id"] if id_a < id_b else img_b["file_id"],
                    "file_id_b":  img_b["file_id"] if id_a < id_b else img_a["file_id"],
                    "score":      round(score, 4),
                    "distance":   int(p_dist),
                })

    return pairs


# ═════════════════════════════════════════════
# CLUSTERING (Union-Find)
# ═════════════════════════════════════════════

class _UnionFind:
    """Simple Union-Find (Disjoint Set) data structure."""

    def __init__(self):
        self.parent = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            return x
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb

    def groups(self) -> list:
        clusters = {}
        for node in list(self.parent.keys()):
            root = self.find(node)
            clusters.setdefault(root, []).append(node)
        return list(clusters.values())


def build_text_clusters(pairs: list) -> list:
    """Group similar text pairs into clusters using Union-Find."""
    if not pairs:
        return []

    uf = _UnionFind()
    for p in pairs:
        a = p.get("chunk_id_a") or p.get("id_a")
        b = p.get("chunk_id_b") or p.get("id_b")
        if a is not None and b is not None:
            uf.union(a, b)

    cluster_map = {}
    for p in pairs:
        a = p.get("chunk_id_a") or p.get("id_a")
        b = p.get("chunk_id_b") or p.get("id_b")
        if a is None or b is None:
            continue
        root = uf.find(a)
        cl = cluster_map.setdefault(root, {"chunk_ids": set(), "pairs": []})
        cl["chunk_ids"].add(a)
        cl["chunk_ids"].add(b)
        cl["pairs"].append(p)

    result = []
    for root, data in cluster_map.items():
        scores = [
            p.get("similarity_score", p.get("score", 0.0))
            for p in data["pairs"]
        ]
        result.append({
            "chunk_ids": sorted(data["chunk_ids"]),
            "pairs":     data["pairs"],
            "size":      len(data["chunk_ids"]),
            "max_score": max(scores) if scores else 0.0,
            "avg_score": (sum(scores) / len(scores)) if scores else 0.0,
        })

    result.sort(key=lambda c: c["max_score"], reverse=True)
    return result


def build_image_clusters(pairs: list) -> list:
    """Group similar image pairs into clusters using Union-Find."""
    if not pairs:
        return []

    uf = _UnionFind()
    for p in pairs:
        a = p.get("image_id_a") or p.get("id_a")
        b = p.get("image_id_b") or p.get("id_b")
        if a is not None and b is not None:
            uf.union(a, b)

    cluster_map = {}
    for p in pairs:
        a = p.get("image_id_a") or p.get("id_a")
        b = p.get("image_id_b") or p.get("id_b")
        if a is None or b is None:
            continue
        root = uf.find(a)
        cl = cluster_map.setdefault(root, {"image_ids": set(), "pairs": []})
        cl["image_ids"].add(a)
        cl["image_ids"].add(b)
        cl["pairs"].append(p)

    result = []
    for root, data in cluster_map.items():
        scores = [
            p.get("similarity_score", p.get("score", 0.0))
            for p in data["pairs"]
        ]
        result.append({
            "image_ids": sorted(data["image_ids"]),
            "pairs":     data["pairs"],
            "size":      len(data["image_ids"]),
            "max_score": max(scores) if scores else 0.0,
            "avg_score": (sum(scores) / len(scores)) if scores else 0.0,
        })

    result.sort(key=lambda c: c["max_score"], reverse=True)
    return result


# ═════════════════════════════════════════════
# STATISTICS
# ═════════════════════════════════════════════

def get_similarity_stats(project_id: int) -> dict:
    """Return summary statistics for a project's similarity results."""
    from database.db import get_connection
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT
                   COUNT(*)                          AS total,
                   COALESCE(SUM(reviewed), 0)        AS reviewed,
                   COALESCE(AVG(similarity_score), 0) AS avg_score,
                   COALESCE(SUM(CASE WHEN similarity_score >= 0.90
                       THEN 1 ELSE 0 END), 0) AS high,
                   COALESCE(SUM(CASE WHEN similarity_score >= 0.70
                       AND similarity_score < 0.90
                       THEN 1 ELSE 0 END), 0) AS medium,
                   COALESCE(SUM(CASE WHEN similarity_score < 0.70
                       THEN 1 ELSE 0 END), 0) AS low
               FROM text_similarities
               WHERE project_id = ?""",
            (project_id,)
        ).fetchone()

        text_total    = row["total"]    if row else 0
        text_reviewed = row["reviewed"] if row else 0
        text_avg      = float(row["avg_score"]) if row and row["avg_score"] else 0.0
        text_high     = row["high"]     if row else 0
        text_medium   = row["medium"]   if row else 0
        text_low      = row["low"]      if row else 0

        row = conn.execute(
            """SELECT
                   COUNT(*)                          AS total,
                   COALESCE(SUM(reviewed), 0)        AS reviewed,
                   COALESCE(AVG(similarity_score), 0) AS avg_score,
                   COALESCE(SUM(CASE WHEN similarity_score >= 0.90
                       THEN 1 ELSE 0 END), 0) AS high,
                   COALESCE(SUM(CASE WHEN similarity_score >= 0.70
                       AND similarity_score < 0.90
                       THEN 1 ELSE 0 END), 0) AS medium,
                   COALESCE(SUM(CASE WHEN similarity_score < 0.70
                       THEN 1 ELSE 0 END), 0) AS low
               FROM image_similarities
               WHERE project_id = ?""",
            (project_id,)
        ).fetchone()

        img_total    = row["total"]    if row else 0
        img_reviewed = row["reviewed"] if row else 0
        img_avg      = float(row["avg_score"]) if row and row["avg_score"] else 0.0
        img_high     = row["high"]     if row else 0
        img_medium   = row["medium"]   if row else 0
        img_low      = row["low"]      if row else 0

        return {
            "text_total":      text_total,
            "text_reviewed":   text_reviewed,
            "text_unreviewed": text_total - text_reviewed,
            "text_avg_score":  round(text_avg, 4),
            "text_high":       text_high,
            "text_medium":     text_medium,
            "text_low":        text_low,
            "img_total":       img_total,
            "img_reviewed":    img_reviewed,
            "img_unreviewed":  img_total - img_reviewed,
            "img_avg_score":   round(img_avg, 4),
            "img_high":        img_high,
            "img_medium":      img_medium,
            "img_low":         img_low,
            "grand_total":     text_total + img_total,
        }
    finally:
        conn.close()