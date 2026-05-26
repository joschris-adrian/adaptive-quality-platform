import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
from services.rca.similarity import (
    cosine_similarity,
    nearest_neighbours,
    similarity_clusters,
    _signal_vector,
    _centroid,
)
from services.rca.root_cause import FailureRecord
from datetime import datetime, timezone


def _record(event_id, ml=0.7, rule=0.5, spam=0.2,
            failure_type="false_positive", category="fraud"):
    return FailureRecord(
        event_id=event_id,
        tier="standard",
        category=category,
        failure_type=failure_type,
        risk_score=ml,
        signals={
            "ml":        {"risk_probability": ml},
            "rule":      {"risk_probability": rule},
            "heuristic": {"signals": {"spam_patterns": spam}},
        },
    )


# ── _signal_vector ─────────────────────────────────────────────────────────

def test_signal_vector_returns_dict():
    r   = _record("e1")
    vec = _signal_vector(r)
    assert isinstance(vec, dict)


def test_signal_vector_extracts_flat_values():
    r   = _record("e1", ml=0.8, rule=0.6)
    vec = _signal_vector(r)
    assert "ml.risk_probability"   in vec
    assert "rule.risk_probability" in vec


def test_signal_vector_extracts_nested_values():
    r   = _record("e1", spam=0.4)
    vec = _signal_vector(r)
    assert "heuristic.signals.spam_patterns" in vec


def test_signal_vector_values_are_floats():
    r   = _record("e1")
    vec = _signal_vector(r)
    for v in vec.values():
        assert isinstance(v, float)


def test_signal_vector_empty_signals():
    r = FailureRecord(
        event_id="e1", tier="standard", category="fraud",
        failure_type="false_positive", risk_score=0.5,
        signals={},
    )
    vec = _signal_vector(r)
    assert vec == {}


# ── cosine_similarity ──────────────────────────────────────────────────────

def test_cosine_similarity_identical_vectors():
    a = {"x": 1.0, "y": 0.5}
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    a = {"x": 1.0, "y": 0.0}
    b = {"x": 0.0, "y": 1.0}
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    a = {"x": 0.0}
    b = {"x": 1.0}
    assert cosine_similarity(a, b) == 0.0


def test_cosine_similarity_both_zero():
    assert cosine_similarity({"x": 0.0}, {"x": 0.0}) == 0.0


def test_cosine_similarity_partial_overlap():
    a = {"x": 1.0, "y": 0.0}
    b = {"x": 1.0, "z": 1.0}
    sim = cosine_similarity(a, b)
    assert 0.0 < sim < 1.0


def test_cosine_similarity_symmetric():
    a = {"x": 0.8, "y": 0.3}
    b = {"x": 0.5, "y": 0.9}
    assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))


def test_cosine_similarity_returns_float():
    a = {"x": 0.5}
    b = {"x": 0.8}
    assert isinstance(cosine_similarity(a, b), float)


def test_cosine_similarity_result_bounded():
    a = {"x": 0.8, "y": 0.3, "z": 0.5}
    b = {"x": 0.5, "y": 0.9, "z": 0.1}
    sim = cosine_similarity(a, b)
    assert -1.0 <= sim <= 1.0


# ── nearest_neighbours ────────────────────────────────────────────────────

def test_nearest_neighbours_returns_list():
    target = _record("t")
    pool   = [_record(f"e{i}") for i in range(5)]
    result = nearest_neighbours(target, pool)
    assert isinstance(result, list)


def test_nearest_neighbours_excludes_target():
    target = _record("t")
    pool   = [target] + [_record(f"e{i}") for i in range(5)]
    result = nearest_neighbours(target, pool)
    ids    = [r["event_id"] for r in result]
    assert "t" not in ids


def test_nearest_neighbours_top_n_limit():
    target = _record("t", ml=0.8)
    pool   = [_record(f"e{i}", ml=0.8) for i in range(10)]
    result = nearest_neighbours(target, pool, top_n=3)
    assert len(result) <= 3


def test_nearest_neighbours_min_similarity_filter():
    target = _record("t", ml=0.9, rule=0.9, spam=0.9)
    pool   = [_record("e1", ml=0.0, rule=0.0, spam=0.0)]
    result = nearest_neighbours(target, pool, min_sim=0.5)
    assert result == []


def test_nearest_neighbours_sorted_descending():
    target = _record("t", ml=0.9)
    pool   = [
        _record("high", ml=0.9, rule=0.9),
        _record("low",  ml=0.1, rule=0.1),
        _record("mid",  ml=0.5, rule=0.5),
    ]
    result = nearest_neighbours(target, pool, min_sim=0.0)
    sims   = [r["similarity"] for r in result]
    assert sims == sorted(sims, reverse=True)


def test_nearest_neighbours_result_has_required_keys():
    target = _record("t")
    pool   = [_record("e1")]
    result = nearest_neighbours(target, pool, min_sim=0.0)
    if result:
        for key in ["event_id", "similarity", "failure_type",
                    "category", "tier", "risk_score"]:
            assert key in result[0]


def test_nearest_neighbours_empty_pool():
    target = _record("t")
    result = nearest_neighbours(target, [])
    assert result == []


def test_nearest_neighbours_similarity_in_range():
    target = _record("t")
    pool   = [_record(f"e{i}") for i in range(5)]
    result = nearest_neighbours(target, pool, min_sim=0.0)
    for r in result:
        assert 0.0 <= r["similarity"] <= 1.0


# ── _centroid ──────────────────────────────────────────────────────────────

def test_centroid_single_record():
    r        = _record("e1", ml=0.8)
    centroid = _centroid([r])
    assert centroid["ml.risk_probability"] == pytest.approx(0.8)


def test_centroid_two_records_average():
    r1       = _record("e1", ml=0.6)
    r2       = _record("e2", ml=0.8)
    centroid = _centroid([r1, r2])
    assert centroid["ml.risk_probability"] == pytest.approx(0.7)


def test_centroid_returns_dict():
    r        = _record("e1")
    centroid = _centroid([r])
    assert isinstance(centroid, dict)


def test_centroid_keys_match_signal_vector():
    r        = _record("e1")
    centroid = _centroid([r])
    vec      = _signal_vector(r)
    assert set(centroid.keys()) == set(vec.keys())


# ── similarity_clusters ───────────────────────────────────────────────────

def test_similarity_clusters_returns_list():
    records  = [_record(f"e{i}") for i in range(5)]
    clusters = similarity_clusters(records)
    assert isinstance(clusters, list)


def test_similarity_clusters_single_record():
    records  = [_record("e1")]
    clusters = similarity_clusters(records)
    assert len(clusters) == 1
    assert clusters[0] == ["e1"]


def test_similarity_clusters_all_identical_in_one_cluster():
    records  = [_record(f"e{i}", ml=0.8, rule=0.6, spam=0.1) for i in range(5)]
    clusters = similarity_clusters(records, threshold=0.99)
    assert len(clusters) == 1
    assert len(clusters[0]) == 5


def test_similarity_clusters_different_records_separate():
    group_a  = [_record(f"a{i}", ml=0.9, rule=0.9, spam=0.0) for i in range(3)]
    group_b  = [_record(f"b{i}", ml=0.0, rule=0.0, spam=1.0) for i in range(3)]
    clusters = similarity_clusters(group_a + group_b, threshold=0.8)
    assert len(clusters) >= 2


def test_similarity_clusters_all_event_ids_present():
    records   = [_record(f"e{i}") for i in range(4)]
    clusters  = similarity_clusters(records)
    all_ids   = [eid for cluster in clusters for eid in cluster]
    input_ids = [r.event_id for r in records]
    assert sorted(all_ids) == sorted(input_ids)


def test_similarity_clusters_no_duplicate_event_ids():
    records  = [_record(f"e{i}") for i in range(6)]
    clusters = similarity_clusters(records)
    all_ids  = [eid for cluster in clusters for eid in cluster]
    assert len(all_ids) == len(set(all_ids))


def test_similarity_clusters_empty_input():
    clusters = similarity_clusters([])
    assert clusters == []