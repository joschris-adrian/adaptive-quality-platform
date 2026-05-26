import pytest
import random
from unittest.mock import patch
from scripts.run_ab_experiment import (
    run_ab_experiment,
    build_metrics,
    VARIANTS,
    METRICS,
    N_EVENTS,
)


@pytest.fixture
def ab_result():
    return run_ab_experiment()


# ── build_metrics ──────────────────────────────────────────────────────────

def test_build_metrics_control_keys():
    m = build_metrics("control")
    assert "precision"     in m
    assert "cost_per_event" in m
    assert "reversal_rate"  in m


def test_build_metrics_treatment_keys():
    m = build_metrics("treatment")
    assert "precision"      in m
    assert "cost_per_event" in m
    assert "reversal_rate"  in m


def test_build_metrics_control_precision_range():
    # run many times to check range stays plausible
    for _ in range(20):
        m = build_metrics("control")
        assert 0.0 <= m["precision"] <= 1.0


def test_build_metrics_treatment_precision_range():
    for _ in range(20):
        m = build_metrics("treatment")
        assert 0.0 <= m["precision"] <= 1.0


def test_build_metrics_treatment_higher_precision_on_average():
    control_mean   = sum(build_metrics("control")["precision"]   for _ in range(100)) / 100
    treatment_mean = sum(build_metrics("treatment")["precision"] for _ in range(100)) / 100
    assert treatment_mean > control_mean


def test_build_metrics_treatment_higher_cost_on_average():
    control_mean   = sum(build_metrics("control")["cost_per_event"]   for _ in range(100)) / 100
    treatment_mean = sum(build_metrics("treatment")["cost_per_event"] for _ in range(100)) / 100
    assert treatment_mean > control_mean


def test_build_metrics_treatment_lower_reversal_on_average():
    control_mean   = sum(build_metrics("control")["reversal_rate"]   for _ in range(100)) / 100
    treatment_mean = sum(build_metrics("treatment")["reversal_rate"] for _ in range(100)) / 100
    assert treatment_mean < control_mean


def test_build_metrics_unknown_variant_returns_dict():
    m = build_metrics("unknown_variant")
    assert isinstance(m, dict)


# ── run_ab_experiment ──────────────────────────────────────────────────────

def test_run_ab_experiment_returns_dict(ab_result):
    assert isinstance(ab_result, dict)


def test_run_ab_experiment_has_experiment_id(ab_result):
    assert "experiment_id" in ab_result


def test_run_ab_experiment_has_status(ab_result):
    assert ab_result["status"] == "completed"


def test_run_ab_experiment_has_variants(ab_result):
    assert "variants" in ab_result


def test_run_ab_experiment_has_both_variants(ab_result):
    for v in VARIANTS:
        assert v in ab_result["variants"]


def test_run_ab_experiment_has_winner(ab_result):
    assert "winner" in ab_result
    assert ab_result["winner"] in VARIANTS


def test_run_ab_experiment_has_relative_lifts(ab_result):
    assert "relative_lifts" in ab_result


def test_run_ab_experiment_total_observations(ab_result):
    assert ab_result["total_observations"] == N_EVENTS


def test_run_ab_experiment_variant_stats_have_n(ab_result):
    for variant, stats in ab_result["variants"].items():
        assert "n" in stats


def test_run_ab_experiment_variant_stats_have_metrics(ab_result):
    for variant, stats in ab_result["variants"].items():
        for metric in METRICS:
            assert metric in stats


def test_run_ab_experiment_variant_means_not_none(ab_result):
    for variant, stats in ab_result["variants"].items():
        for metric in METRICS:
            assert stats[metric]["mean"] is not None


def test_run_ab_experiment_variant_std_not_none(ab_result):
    for variant, stats in ab_result["variants"].items():
        for metric in METRICS:
            assert stats[metric]["std"] is not None


def test_run_ab_experiment_precision_means_in_range(ab_result):
    for variant, stats in ab_result["variants"].items():
        mean = stats["precision"]["mean"]
        assert 0.0 <= mean <= 1.0


def test_run_ab_experiment_cost_means_positive(ab_result):
    for variant, stats in ab_result["variants"].items():
        assert stats["cost_per_event"]["mean"] > 0