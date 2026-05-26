import pytest
from unittest.mock import AsyncMock, patch
from services.detection.pipeline import DetectionPipeline


@pytest.fixture
def pipeline():
    return DetectionPipeline()


@pytest.fixture
def base_event():
    return {
        "event_id":      "evt-001",
        "event_type":    "user_action",
        "source_system": "web",
        "payload": {
            "user_id":   "user-abc",
            "risk_hint": 0.5,
            "category":  "normal",
        },
        "timestamp": "2026-01-01T00:00:00",
    }


def test_aggregate_weighted_score(pipeline, base_event):
    ml        = {"risk_probability": 0.8, "category": "fraud",  "detector": "ml_classifier"}
    rule      = {"risk_probability": 0.6, "category": "clean",  "detector": "rule_engine",  "rules_triggered": []}
    heuristic = {"risk_probability": 0.4, "category": "clean",  "detector": "heuristics",   "signals": {}}

    result   = pipeline._aggregate(base_event, ml, rule, heuristic)
    expected = 0.8 * 0.5 + 0.6 * 0.3 + 0.4 * 0.2
    assert abs(result["risk_probability"] - expected) < 1e-4


def test_aggregate_rule_overrides_category(pipeline, base_event):
    ml        = {"risk_probability": 0.9, "category": "spam",  "detector": "ml_classifier"}
    rule      = {"risk_probability": 0.7, "category": "fraud", "detector": "rule_engine", "rules_triggered": ["blocklisted_user"]}
    heuristic = {"risk_probability": 0.1, "category": "clean", "detector": "heuristics",  "signals": {}}

    result = pipeline._aggregate(base_event, ml, rule, heuristic)
    assert result["category"] == "fraud"


def test_aggregate_heuristic_overrides_category(pipeline, base_event):
    ml        = {"risk_probability": 0.5, "category": "clean", "detector": "ml_classifier"}
    rule      = {"risk_probability": 0.0, "category": "clean", "detector": "rule_engine",  "rules_triggered": []}
    heuristic = {"risk_probability": 0.8, "category": "spam",  "detector": "heuristics",   "signals": {}}

    result = pipeline._aggregate(base_event, ml, rule, heuristic)
    assert result["category"] == "spam"


def test_aggregate_preserves_signals(pipeline, base_event):
    ml        = {"risk_probability": 0.5, "category": "clean", "detector": "ml_classifier"}
    rule      = {"risk_probability": 0.0, "category": "clean", "detector": "rule_engine",  "rules_triggered": []}
    heuristic = {"risk_probability": 0.2, "category": "clean", "detector": "heuristics",   "signals": {}}

    result = pipeline._aggregate(base_event, ml, rule, heuristic)
    assert "ml"        in result["signals"]
    assert "rule"      in result["signals"]
    assert "heuristic" in result["signals"]


def test_aggregate_score_capped_at_one(pipeline, base_event):
    ml        = {"risk_probability": 1.0, "category": "fraud", "detector": "ml_classifier"}
    rule      = {"risk_probability": 1.0, "category": "fraud", "detector": "rule_engine",  "rules_triggered": []}
    heuristic = {"risk_probability": 1.0, "category": "fraud", "detector": "heuristics",   "signals": {}}

    result = pipeline._aggregate(base_event, ml, rule, heuristic)
    assert result["risk_probability"] <= 1.0


@pytest.mark.asyncio
async def test_pipeline_run_returns_scored_event(pipeline, base_event):
    with patch.object(pipeline.classifier,  "detect", new=AsyncMock(return_value={"risk_probability": 0.7, "category": "fraud",  "detector": "ml_classifier"})), \
         patch.object(pipeline.rule_engine, "detect", new=AsyncMock(return_value={"risk_probability": 0.5, "category": "clean",  "detector": "rule_engine",  "rules_triggered": []})), \
         patch.object(pipeline.heuristics,  "detect", new=AsyncMock(return_value={"risk_probability": 0.3, "category": "clean",  "detector": "heuristics",   "signals": {}})):

        result = await pipeline.run(base_event)

    assert result["event_id"]        == "evt-001"
    assert "risk_probability"         in result
    assert "category"                 in result
    assert "signals"                  in result


@pytest.mark.asyncio
async def test_pipeline_run_calls_all_detectors(pipeline, base_event):
    ml_mock   = AsyncMock(return_value={"risk_probability": 0.5, "category": "clean", "detector": "ml_classifier"})
    rule_mock = AsyncMock(return_value={"risk_probability": 0.0, "category": "clean", "detector": "rule_engine",  "rules_triggered": []})
    heur_mock = AsyncMock(return_value={"risk_probability": 0.1, "category": "clean", "detector": "heuristics",   "signals": {}})

    with patch.object(pipeline.classifier,  "detect", new=ml_mock), \
         patch.object(pipeline.rule_engine, "detect", new=rule_mock), \
         patch.object(pipeline.heuristics,  "detect", new=heur_mock):

        await pipeline.run(base_event)

    ml_mock.assert_called_once_with(base_event)
    rule_mock.assert_called_once_with(base_event)
    heur_mock.assert_called_once_with(base_event)