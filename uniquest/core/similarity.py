import difflib
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ═════════════════════════════════════════════════════════════
#  TEXT SIMILARITY
# ═════════════════════════════════════════════════════════════
def find_similar_text_batched(
    rows: list,
    threshold: float = 0.75
) -> list[dict]:
    if len(rows) < 2:
        return []

    long_rows  = [r for r in rows if len(r[1].split()) >= 6]
    short_rows = [r for r in rows if len(r[1].split()) <  6]

    pairs = []
    pairs.extend(_tfidf_pairs(long_rows, threshold))
    pairs.extend(_fuzzy_pairs(short_rows, threshold))
    pairs.extend(_cross_pairs(short_rows, long_rows, threshold))
    return pairs


def _tfidf_pairs(rows: list, threshold: float) -> list[dict]:
    if len(rows) < 2:
        return []

    ids      = [r[0] for r in rows]
    texts    = [r[1] for r in rows]
    file_ids = [r[2] for r in rows]

    try:
        vec = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
        )
        matrix = vec.fit_transform(texts)
    except Exception:
        return []

    pairs = []
    n = len(rows)
    SUB = 200

    for i in range(0, n, SUB):
        block = matrix[i: i + SUB]
        sims  = cosine_similarity(block, matrix)

        for local_i, global_i in enumerate(range(i, min(i + SUB, n))):
            for j in range(global_i + 1, n):
                score = float(sims[local_i, j])
                if score >= threshold:
                    pairs.append({
                        "chunk_id_a": ids[global_i],
                        "chunk_id_b": ids[j],
                        "file_id_a":  file_ids[global_i],
                        "file_id_b":  file_ids[j],
                        "score":      round(score, 4),
                    })

    return pairs


def _fuzzy_pairs(rows: list, threshold: float) -> list[dict]:
    pairs  = []
    thresh = max(0.75, threshold)
    n      = len(rows)

    for i in range(n):
        for j in range(i + 1, n):
            a = rows[i][1].lower()
            b = rows[j][1].lower()

            if not a or not b:
                continue
            if min(len(a), len(b)) / max(len(a), len(b)) < 0.5:
                continue

            score = difflib.SequenceMatcher(None, a, b).ratio()
            if score >= thresh:
                pairs.append({
                    "chunk_id_a": rows[i][0],
                    "chunk_id_b": rows[j][0],
                    "file_id_a":  rows[i][2],
                    "file_id_b":  rows[j][2],
                    "score":      round(score, 4),
                })

    return pairs


def _cross_pairs(short_rows: list, long_rows: list, threshold: float) -> list[dict]:
    pairs = []
    for sr in short_rows:
        short_text = sr[1].lower()
        if len(short_text) < 4:
            continue
        for lr in long_rows:
            if short_text in lr[1].lower():
                pairs.append({
                    "chunk_id_a": sr[0],
                    "chunk_id_b": lr[0],
                    "file_id_a":  sr[2],
                    "file_id_b":  lr[2],
                    "score":      0.85,
                })
    return pairs


# ═════════════════════════════════════════════════════════════
#  IMAGE SIMILARITY
# ═════════════════════════════════════════════════════════════
def find_similar_images_batched(
    images: list,
    threshold: float = 0.85
) -> list[dict]:
    pairs = []
    n = len(images)

    for i in range(n):
        for j in range(i + 1, n):
            id_a, file_id_a, hash_a = images[i][0], images[i][1], images[i][2]
            id_b, file_id_b, hash_b = images[j][0], images[j][1], images[j][2]

            if not hash_a or not hash_b:
                continue

            try:
                dist  = _hamming(hash_a, hash_b)
                score = 1.0 - (dist / 64.0)
                if score >= threshold:
                    pairs.append({
                        "image_id_a": id_a,
                        "image_id_b": id_b,
                        "file_id_a":  file_id_a,
                        "file_id_b":  file_id_b,
                        "score":      round(score, 4),
                        "distance":   dist,
                    })
            except Exception:
                continue

    return pairs


def _hamming(hash_a: str, hash_b: str) -> int:
    try:
        a = int(hash_a, 16)
        b = int(hash_b, 16)
        return bin(a ^ b).count("1")
    except Exception:
        return 64