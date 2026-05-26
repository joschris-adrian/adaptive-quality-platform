import sys
import os

# ensure project root is on sys.path when running as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import asyncio
import statistics
from services.detection.pipeline   import DetectionPipeline
from services.risk_scoring.scorer  import RiskScorer
from services.routing.engine       import RoutingEngine

def _event(i: int) -> dict:
    return {
        "event_id":      f"bench-{i:06d}",
        "event_type":    "transaction",
        "source_system": "api",
        "payload":       {"user_id": f"u{i}", "risk_hint": 0.6, "category": "fraud"},
        "timestamp":     "2026-01-01T00:00:00",
    }


def _scored(i: int) -> dict:
    return {
        "event_id":         f"bench-{i:06d}",
        "risk_probability": 0.75,
        "category":         "fraud",
        "signals": {
            "ml":        {"risk_probability": 0.80},
            "rule":      {"risk_probability": 0.60, "rules_triggered": []},
            "heuristic": {"risk_probability": 0.40, "signals": {}},
        },
        "source_event": {"event_type": "transaction", "source_system": "api"},
    }


# ── cold-start latency ─────────────────────────────────────────────────────

def bench_cold_start(n: int = 5) -> dict:
    latencies = []
    for _ in range(n):
        t0 = time.perf_counter()
        DetectionPipeline()
        RiskScorer()
        RoutingEngine()
        latencies.append((time.perf_counter() - t0) * 1000)

    return {
        "cold_start_ms": {
            "mean":   round(statistics.mean(latencies),   2),
            "median": round(statistics.median(latencies), 2),
            "min":    round(min(latencies),               2),
            "max":    round(max(latencies),               2),
        }
    }

async def bench_detection(n: int = 500) -> dict:
    pipeline = DetectionPipeline()
    events   = [_event(i) for i in range(n)]

    t0      = time.perf_counter()
    await asyncio.gather(*[pipeline.run(e) for e in events])
    elapsed = time.perf_counter() - t0

    return {
        "detection": {
            "n":          n,
            "elapsed_s":  round(elapsed, 6),        # was 3
            "throughput": round(n / elapsed, 1),
        }
    }


def bench_risk_scoring(n: int = 1000) -> dict:
    scorer = RiskScorer()
    events = [_scored(i) for i in range(n)]

    t0      = time.perf_counter()
    for e in events:
        scorer.score(e)
    elapsed = time.perf_counter() - t0

    return {
        "risk_scoring": {
            "n":          n,
            "elapsed_s":  round(elapsed, 6),        # was 3
            "throughput": round(n / elapsed, 1),
        }
    }


def bench_routing(n: int = 1000) -> dict:
    engine = RoutingEngine()
    risk_events = [
        {
            "event_id":   f"bench-{i:06d}",
            "priority":   "high",
            "risk_score": 0.75,
            "category":   "fraud",
            "components": {"likelihood": 0.9, "severity": 1.0, "exposure": 0.85},
            "risk_metadata": {
                "rules_triggered":   [],
                "heuristic_signals": {},
                "requires_review":   True,
                "auto_actioned":     False,
            },
        }
        for i in range(n)
    ]

    t0      = time.perf_counter()
    for e in risk_events:
        engine.route(e)
    elapsed = time.perf_counter() - t0

    return {
        "routing": {
            "n":          n,
            "elapsed_s":  round(elapsed, 6),        # was 3
            "throughput": round(n / elapsed, 1),
        }
    }


async def bench_batch_vs_single(n: int = 100) -> dict:
    pipeline = DetectionPipeline()
    events   = [_event(i) for i in range(n)]

    t0 = time.perf_counter()
    for e in events:
        await pipeline.run(e)
    single_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    await asyncio.gather(*[pipeline.run(e) for e in events])
    batch_ms = (time.perf_counter() - t0) * 1000

    # compute speedup from raw values before rounding either
    speedup = single_ms / batch_ms

    return {
        "batch_vs_single": {
            "n":          n,
            "single_ms":  round(single_ms, 2),
            "batch_ms":   round(batch_ms,  2),
            "speedup":    round(speedup,   2),
        }
    }


async def bench_batch_sizes(sizes: list[int] = None) -> list[dict]:
    sizes    = sizes or [1, 10, 50, 100, 200, 500]
    pipeline = DetectionPipeline()
    results  = []

    for n in sizes:
        events  = [_event(i) for i in range(n)]
        t0      = time.perf_counter()
        await asyncio.gather(*[pipeline.run(e) for e in events])
        elapsed = time.perf_counter() - t0

        # derive all reported values from raw elapsed, not from each other
        results.append({
            "batch_size":           n,
            "elapsed_ms":           round(elapsed * 1000, 2),
            "throughput":           round(n / elapsed, 1),
            "latency_per_event_ms": round(elapsed * 1000 / n, 3),
        })

    return results








async def bench_batch_sizes(sizes: list[int] = None) -> list[dict]:
    sizes    = sizes or [1, 10, 50, 100, 200, 500]
    pipeline = DetectionPipeline()
    results  = []

    for n in sizes:
        events  = [_event(i) for i in range(n)]
        t0      = time.perf_counter()
        await asyncio.gather(*[pipeline.run(e) for e in events])
        elapsed = time.perf_counter() - t0
        results.append({
            "batch_size":             n,
            "elapsed_ms":             round(elapsed * 1000, 2),
            "throughput":             round(n / elapsed, 1),
            "latency_per_event_ms":   round(elapsed * 1000 / n, 3),
        })

    return results

# ── main ───────────────────────────────────────────────────────────────────

async def main():
    print("Running scaling benchmarks...\n")

    results = {}
    results.update(bench_cold_start())
    results.update(await bench_detection())
    results.update(bench_risk_scoring())
    results.update(bench_routing())
    results.update(await bench_batch_vs_single())

    print(f"Cold start (mean):        {results['cold_start_ms']['mean']} ms")
    print(f"Detection throughput:     {results['detection']['throughput']} events/s")
    print(f"Risk scoring throughput:  {results['risk_scoring']['throughput']} events/s")
    print(f"Routing throughput:       {results['routing']['throughput']} events/s")
    print(f"Batch speedup:            {results['batch_vs_single']['speedup']}x")
    return results


if __name__ == "__main__":
    asyncio.run(main())