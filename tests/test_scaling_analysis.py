import pytest
import asyncio
from scripts.scaling_analysis import (
    bench_cold_start,
    bench_detection,
    bench_risk_scoring,
    bench_routing,
    bench_batch_vs_single,
    bench_batch_sizes,
)


# ── bench_cold_start ───────────────────────────────────────────────────────

def test_cold_start_returns_stats():
    result = bench_cold_start(n=2)
    stats  = result["cold_start_ms"]
    assert "mean"   in stats
    assert "median" in stats
    assert "min"    in stats
    assert "max"    in stats


def test_cold_start_mean_positive():
    result = bench_cold_start(n=2)
    assert result["cold_start_ms"]["mean"] > 0


def test_cold_start_min_lte_max():
    result = bench_cold_start(n=3)
    stats  = result["cold_start_ms"]
    assert stats["min"] <= stats["max"]


def test_cold_start_min_lte_mean():
    result = bench_cold_start(n=3)
    stats  = result["cold_start_ms"]
    assert stats["min"] <= stats["mean"]


def test_cold_start_mean_lte_max():
    result = bench_cold_start(n=3)
    stats  = result["cold_start_ms"]
    assert stats["mean"] <= stats["max"]


def test_cold_start_single_run():
    result = bench_cold_start(n=1)
    stats  = result["cold_start_ms"]
    # with one run min == mean == median == max
    assert stats["min"] == stats["max"]


# ── bench_detection ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detection_throughput_positive():
    result = await bench_detection(n=10)
    assert result["detection"]["throughput"] > 0


@pytest.mark.asyncio
async def test_detection_returns_correct_n():
    result = await bench_detection(n=10)
    assert result["detection"]["n"] == 10


@pytest.mark.asyncio
async def test_detection_elapsed_positive():
    result = await bench_detection(n=10)
    assert result["detection"]["elapsed_s"] > 0


@pytest.mark.asyncio
async def test_detection_larger_batch_completes():
    result = await bench_detection(n=50)
    assert result["detection"]["n"] == 50
    assert result["detection"]["throughput"] > 0


# ── bench_risk_scoring ────────────────────────────────────────────────────

def test_risk_scoring_throughput_positive():
    result = bench_risk_scoring(n=20)
    assert result["risk_scoring"]["throughput"] > 0


def test_risk_scoring_returns_correct_n():
    result = bench_risk_scoring(n=20)
    assert result["risk_scoring"]["n"] == 20


def test_risk_scoring_elapsed_positive():
    result = bench_risk_scoring(n=20)
    assert result["risk_scoring"]["elapsed_s"] > 0


def test_risk_scoring_single_event():
    result = bench_risk_scoring(n=1)
    assert result["risk_scoring"]["n"] == 1
    assert result["risk_scoring"]["throughput"] > 0


# ── bench_routing ─────────────────────────────────────────────────────────

def test_routing_throughput_positive():
    result = bench_routing(n=20)
    assert result["routing"]["throughput"] > 0


def test_routing_returns_correct_n():
    result = bench_routing(n=20)
    assert result["routing"]["n"] == 20


def test_routing_elapsed_positive():
    result = bench_routing(n=20)
    assert result["routing"]["elapsed_s"] > 0


def test_routing_single_event():
    result = bench_routing(n=1)
    assert result["routing"]["n"] == 1
    assert result["routing"]["throughput"] > 0


# ── bench_batch_vs_single ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_vs_single_both_complete():
    result = await bench_batch_vs_single(n=50)
    bvs    = result["batch_vs_single"]
    assert bvs["batch_ms"]  > 0
    assert bvs["single_ms"] > 0
    assert bvs["speedup"]   > 0


@pytest.mark.asyncio
async def test_batch_vs_single_speedup_positive():
    result = await bench_batch_vs_single(n=50)
    assert result["batch_vs_single"]["speedup"] > 0
    
    
@pytest.mark.asyncio
async def test_batch_vs_single_returns_correct_n():
    result = await bench_batch_vs_single(n=10)
    assert result["batch_vs_single"]["n"] == 10


@pytest.mark.asyncio
async def test_batch_vs_single_both_times_positive():
    result = await bench_batch_vs_single(n=10)
    bvs    = result["batch_vs_single"]
    assert bvs["batch_ms"]  > 0
    assert bvs["single_ms"] > 0


# ── bench_batch_sizes ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_sizes_returns_one_row_per_size():
    sizes  = [1, 5, 10]
    result = await bench_batch_sizes(sizes)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_batch_sizes_has_required_keys():
    result = await bench_batch_sizes([5])
    row    = result[0]
    assert "batch_size"           in row
    assert "elapsed_ms"           in row
    assert "throughput"           in row
    assert "latency_per_event_ms" in row


@pytest.mark.asyncio
async def test_batch_sizes_batch_size_matches_input():
    sizes  = [1, 10, 50]
    result = await bench_batch_sizes(sizes)
    returned_sizes = [r["batch_size"] for r in result]
    assert returned_sizes == sizes


@pytest.mark.asyncio
async def test_batch_sizes_throughput_positive():
    result = await bench_batch_sizes([10])
    assert result[0]["throughput"] > 0


@pytest.mark.asyncio
async def test_batch_sizes_elapsed_positive():
    result = await bench_batch_sizes([10])
    assert result[0]["elapsed_ms"] > 0


@pytest.mark.asyncio
async def test_batch_sizes_latency_per_event_positive():
    result = await bench_batch_sizes([10])
    assert result[0]["latency_per_event_ms"] > 0

@pytest.mark.asyncio
async def test_detection_elapsed_positive():
    result = await bench_detection(n=10)
    assert result["detection"]["elapsed_s"] > 0.0


@pytest.mark.asyncio
async def test_detection_elapsed_has_precision():
    # 6 decimal places means sub-millisecond timing is preserved
    result  = await bench_detection(n=10)
    elapsed = result["detection"]["elapsed_s"]
    assert elapsed > 1e-6


def test_risk_scoring_elapsed_positive():
    result = bench_risk_scoring(n=20)
    assert result["risk_scoring"]["elapsed_s"] > 1e-6


def test_routing_elapsed_positive():
    result = bench_routing(n=20)
    assert result["routing"]["elapsed_s"] > 1e-6


@pytest.mark.asyncio
async def test_batch_sizes_larger_batches_higher_throughput():
    result     = await bench_batch_sizes([1, 10, 50])
    throughputs = [r["throughput"] for r in result]
    # throughput should generally increase with batch size
    assert throughputs[-1] > throughputs[0]


@pytest.mark.asyncio
async def test_batch_sizes_larger_batches_lower_latency_per_event():
    result   = await bench_batch_sizes([1, 50])
    latencies = [r["latency_per_event_ms"] for r in result]
    # per-event latency should drop as batch size grows
    assert latencies[-1] < latencies[0]


@pytest.mark.asyncio
async def test_batch_sizes_single_event():
    result = await bench_batch_sizes([1])
    assert result[0]["batch_size"] == 1
    assert result[0]["throughput"] > 0


@pytest.mark.asyncio
async def test_batch_sizes_default_sizes():
    # calling with no args should use the default size list
    result = await bench_batch_sizes()
    assert len(result) == 6   # [1, 10, 50, 100, 200, 500]


# ── combined run ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_benchmarks_return_positive_throughput():
    cold   = bench_cold_start(n=2)
    det    = await bench_detection(n=10)
    risk   = bench_risk_scoring(n=10)
    route  = bench_routing(n=10)
    batch  = await bench_batch_vs_single(n=10)
    sizes  = await bench_batch_sizes([1, 10])

    assert cold["cold_start_ms"]["mean"]      > 0
    assert det["detection"]["throughput"]      > 0
    assert risk["risk_scoring"]["throughput"]  > 0
    assert route["routing"]["throughput"]      > 0
    assert batch["batch_vs_single"]["speedup"] > 0
    assert all(r["throughput"] > 0 for r in sizes)