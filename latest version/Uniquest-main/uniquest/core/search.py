"""
Live search engine for Uniquest.
- Text search: TF-IDF + fuzzy against all text_chunks
- Image search: multi-hash + color against all extracted_images
- Trademark search: phonetic + fuzzy against trademark registry
"""

from difflib import SequenceMatcher
from database.db import get_connection

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False


# ═════════════════════════════════════════════
# TEXT SEARCH
# ═════════════════════════════════════════════

def search_text(
    query:      str,
    project_id: int | None = None,
    limit:      int = 50,
    min_score:  float = 0.30,
) -> list[dict]:
    """
    Search for text similar to the query.

    Args:
        query:      the search text
        project_id: if None → search across ALL projects
        limit:      max number of results
        min_score:  minimum similarity to include

    Returns:
        list of dicts with content, score, file_name, page_number, project_name
    """
    query = (query or "").strip()
    if not query:
        return []

    conn = get_connection()
    try:
        if project_id:
            rows = conn.execute(
                """SELECT tc.id, tc.content, tc.page_number, tc.chunk_type,
                          tc.file_id, tc.project_id,
                          f.file_name, p.name AS project_name
                   FROM text_chunks tc
                   JOIN files    f ON f.id = tc.file_id
                   JOIN projects p ON p.id = tc.project_id
                   WHERE tc.project_id = ?""",
                (project_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT tc.id, tc.content, tc.page_number, tc.chunk_type,
                          tc.file_id, tc.project_id,
                          f.file_name, p.name AS project_name
                   FROM text_chunks tc
                   JOIN files    f ON f.id = tc.file_id
                   JOIN projects p ON p.id = tc.project_id"""
            ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    documents = [r["content"] or "" for r in rows]
    scores    = []

    query_lower = query.lower()
    query_words = len(query.split())

    # ── TF-IDF for longer queries ───────────────────────────
    if query_words >= 3 and SKLEARN_OK:
        try:
            vec = TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=10000,
                lowercase=True,
            )
            matrix = vec.fit_transform([query] + documents)
            sim = cosine_similarity(matrix[0:1], matrix[1:])[0]
            scores = [float(s) for s in sim]
        except Exception:
            scores = []

    if not scores:
        # Fallback: substring + SequenceMatcher
        for doc in documents:
            doc_lower = (doc or "").lower()
            if not doc_lower:
                scores.append(0.0)
                continue
            if query_lower in doc_lower:
                scores.append(1.0)
            else:
                s = SequenceMatcher(None, query_lower, doc_lower[:500]).ratio()
                scores.append(s)

    # Boost exact substring matches
    for i, doc in enumerate(documents):
        if query_lower and query_lower in (doc or "").lower():
            scores[i] = max(scores[i], 0.95)

    # Build results
    results = []
    for r, sc in zip(rows, scores):
        if sc >= min_score:
            content = r["content"] or ""
            snippet = _make_snippet(content, query_lower, 200)
            results.append({
                "chunk_id":     r["id"],
                "score":        round(float(sc), 4),
                "content":      content,
                "snippet":      snippet,
                "page_number":  r["page_number"],
                "chunk_type":   r["chunk_type"],
                "file_id":      r["file_id"],
                "file_name":    r["file_name"],
                "project_id":   r["project_id"],
                "project_name": r["project_name"],
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def _make_snippet(content: str, query: str, size: int = 200) -> str:
    """Create a preview snippet centered on the first match of query."""
    if not content:
        return ""
    if not query:
        return content[:size]

    lower = content.lower()
    idx = lower.find(query)
    if idx == -1:
        return content[:size].replace("\n", " ")

    start = max(0, idx - size // 2)
    end   = min(len(content), start + size)
    snippet = content[start:end].replace("\n", " ")
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."
    return snippet


# ═════════════════════════════════════════════
# IMAGE SEARCH
# ═════════════════════════════════════════════

def search_image(
    image_path: str,
    project_id: int | None = None,
    limit:      int = 50,
    min_score:  float = 0.75,
) -> list[dict]:
    """
    Search for images similar to the provided image file.

    Args:
        image_path: path to the query image
        project_id: if None → search across ALL projects
        limit:      max number of results
        min_score:  minimum similarity (0.0 - 1.0)

    Returns:
        list of dicts with image data + score
    """
    from core.similarity import _hamming_distance, _color_fingerprint, _color_similar

    try:
        import imagehash
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        q_phash = str(imagehash.phash(img))
        q_ahash = str(imagehash.average_hash(img))
        q_dhash = str(imagehash.dhash(img))
        q_color = _color_fingerprint(image_path)
        q_w, q_h = img.size
    except Exception as e:
        print(f"Query image error: {e}")
        return []

    conn = get_connection()
    try:
        if project_id:
            rows = conn.execute(
                """SELECT ei.id, ei.file_id, ei.project_id,
                          ei.stored_path, ei.page_number,
                          ei.width, ei.height,
                          ei.phash, ei.ahash, ei.dhash,
                          f.file_name, p.name AS project_name
                   FROM extracted_images ei
                   JOIN files    f ON f.id = ei.file_id
                   JOIN projects p ON p.id = ei.project_id
                   WHERE ei.project_id = ?""",
                (project_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT ei.id, ei.file_id, ei.project_id,
                          ei.stored_path, ei.page_number,
                          ei.width, ei.height,
                          ei.phash, ei.ahash, ei.dhash,
                          f.file_name, p.name AS project_name
                   FROM extracted_images ei
                   JOIN files    f ON f.id = ei.file_id
                   JOIN projects p ON p.id = ei.project_id"""
            ).fetchall()
    finally:
        conn.close()

    results = []

    for r in rows:
        if not r["phash"]:
            continue

        # Aspect ratio filter
        rw = r["width"] or 0
        rh = r["height"] or 0
        if q_w and q_h and rw and rh:
            asp_q = q_w / q_h
            asp_r = rw / rh
            if asp_q > 0 and asp_r > 0:
                ratio = min(asp_q, asp_r) / max(asp_q, asp_r)
                if ratio < 0.75:
                    continue

        p_dist = _hamming_distance(q_phash, r["phash"])
        if p_dist > 12:
            continue

        a_dist = _hamming_distance(q_ahash, r["ahash"]) if r["ahash"] else p_dist
        d_dist = _hamming_distance(q_dhash, r["dhash"]) if r["dhash"] else p_dist

        # Color check
        r_color = _color_fingerprint(r["stored_path"]) if r["stored_path"] else None
        if not _color_similar(q_color, r_color):
            continue

        avg_dist = (p_dist + a_dist + d_dist) / 3.0
        score = 1.0 - (avg_dist / 64.0)

        if score >= min_score:
            results.append({
                "image_id":     r["id"],
                "score":        round(score, 4),
                "distance":     int(p_dist),
                "stored_path":  r["stored_path"],
                "page_number":  r["page_number"],
                "width":        rw,
                "height":       rh,
                "file_id":      r["file_id"],
                "file_name":    r["file_name"],
                "project_id":   r["project_id"],
                "project_name": r["project_name"],
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


# ═════════════════════════════════════════════
# TRADEMARK SEARCH
# ═════════════════════════════════════════════

def search_trademark(
    query:      str,
    nice_class: int | None = None,
    limit:      int = 50,
    min_score:  float = 0.50,
) -> list[dict]:
    """
    Search the trademark registry for names similar to the query.

    Args:
        query:      trademark name to check
        nice_class: filter by Nice class (or None for all classes)
        limit:      max number of results
        min_score:  minimum score

    Returns:
        list of dicts with trademark info + score + verdict
    """
    query = (query or "").strip()
    if not query:
        return []

    try:
        from core.phonetic import phonetic_similarity, get_verdict
        PHONETIC_OK = True
    except ImportError:
        PHONETIC_OK = False

    conn = get_connection()
    try:
        # Check if trademarks table exists (IP mode may not be initialized)
        try:
            if nice_class is not None:
                rows = conn.execute(
                    """SELECT * FROM trademarks WHERE nice_class = ?""",
                    (nice_class,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM trademarks").fetchall()
        except Exception:
            return []
    finally:
        conn.close()

    if not rows:
        return []

    results = []
    q_lower = query.lower()

    for r in rows:
        tm_name = r["trademark_name"] or ""
        tm_lower = tm_name.lower()

        # Base text score
        if q_lower == tm_lower:
            text_score = 1.0
        elif q_lower in tm_lower or tm_lower in q_lower:
            text_score = 0.90
        else:
            text_score = SequenceMatcher(None, q_lower, tm_lower).ratio()

        # Phonetic
        if PHONETIC_OK:
            ph = phonetic_similarity(query, tm_name)
            phonetic_score = ph["combined"]
        else:
            phonetic_score = text_score

        overall = (text_score * 0.5) + (phonetic_score * 0.5)

        if overall >= min_score:
            verdict = get_verdict(overall) if PHONETIC_OK else _simple_verdict(overall)
            results.append({
                "trademark_id":        r["id"],
                "trademark_name":      tm_name,
                "registration_number": r["registration_number"],
                "owner_name":          r["owner_name"] or "",
                "nice_class":          r["nice_class"],
                "status":              r["status"] or "",
                "text_score":          round(text_score, 4),
                "phonetic_score":      round(phonetic_score, 4),
                "overall_score":       round(overall, 4),
                "verdict":             verdict,
            })

    results.sort(key=lambda x: x["overall_score"], reverse=True)
    return results[:limit]


def _simple_verdict(score: float) -> str:
    if score >= 0.90:
        return "IDENTICAL"
    if score >= 0.70:
        return "CONFUSINGLY SIMILAR"
    if score >= 0.50:
        return "SIMILAR"
    return "DISTINCT"