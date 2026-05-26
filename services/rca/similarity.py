import math
from services.rca.root_cause import FailureRecord


def _signal_vector(record: FailureRecord) -> dict[str, float]:
    """Flatten signals dict into a float vector — two levels deep."""
    vec = {}
    for k, v in record.signals.items():
        if isinstance(v, (int, float)):
            vec[k] = float(v)
        elif isinstance(v, dict):
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, (int, float)):
                    vec[f"{k}.{sub_k}"] = float(sub_v)
                elif isinstance(sub_v, dict):
                    for sub_sub_k, sub_sub_v in sub_v.items():
                        if isinstance(sub_sub_v, (int, float)):
                            vec[f"{k}.{sub_k}.{sub_sub_k}"] = float(sub_sub_v)
    return vec

def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    keys  = set(a) | set(b)
    dot   = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return round(dot / (mag_a * mag_b), 4)


def nearest_neighbours(
    target:   FailureRecord,
    pool:     list[FailureRecord],
    top_n:    int = 5,
    min_sim:  float = 0.5,
) -> list[dict]:
    """
    Find the top_n most similar failure records to the target
    based on cosine similarity of their signal vectors.
    """
    target_vec = _signal_vector(target)
    scored     = []

    for candidate in pool:
        if candidate.event_id == target.event_id:
            continue
        sim = cosine_similarity(target_vec, _signal_vector(candidate))
        if sim >= min_sim:
            scored.append({
                "event_id":     candidate.event_id,
                "similarity":   sim,
                "failure_type": candidate.failure_type,
                "category":     candidate.category,
                "tier":         candidate.tier,
                "risk_score":   candidate.risk_score,
            })

    return sorted(scored, key=lambda x: -x["similarity"])[:top_n]


def similarity_clusters(
    records:   list[FailureRecord],
    threshold: float = 0.7,
) -> list[list[str]]:
    """
    Greedy clustering: assign each record to the first cluster whose
    centroid is within threshold similarity. Otherwise start a new cluster.
    Returns lists of event_ids per cluster.
    """
    clusters: list[list[FailureRecord]] = []

    for record in records:
        assigned = False
        vec      = _signal_vector(record)

        for cluster in clusters:
            centroid = _centroid(cluster)
            if cosine_similarity(vec, centroid) >= threshold:
                cluster.append(record)
                assigned = True
                break

        if not assigned:
            clusters.append([record])

    return [[r.event_id for r in cluster] for cluster in clusters]


def _centroid(records: list[FailureRecord]) -> dict[str, float]:
    """Mean signal vector across a list of records."""
    keys  = {k for r in records for k in _signal_vector(r)}
    n     = len(records)
    return {
        k: sum(_signal_vector(r).get(k, 0.0) for r in records) / n
        for k in keys
    }