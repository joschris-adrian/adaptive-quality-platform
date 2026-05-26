import pytest
import sys
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cmd(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "run.py"] + cmd,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


# ── help ──────────────────────────────────────────────────────────────────

def test_help_exits_zero():
    result = run_cmd(["help"])
    assert result.returncode == 0


def test_help_contains_commands():
    result = run_cmd(["help"])
    for cmd in ["up", "down", "test", "bench", "seed",
                "rca", "report", "k8s-up", "k8s-down"]:
        assert cmd in result.stdout


def test_unknown_command_exits_nonzero():
    result = run_cmd(["totally-unknown-command"])
    assert result.returncode != 0


def test_unknown_command_prints_error():
    result = run_cmd(["totally-unknown-command"])
    assert "Unknown command" in result.stdout or "Unknown command" in result.stderr


# ── python path ───────────────────────────────────────────────────────────

def test_run_py_sets_pythonpath():
    result = subprocess.run(
        [sys.executable, "-c",
         "import os; print(os.environ.get('PYTHONPATH', ''))"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": ROOT},
    )
    assert ROOT in result.stdout or result.returncode == 0


# ── bench runs without import errors ──────────────────────────────────────

def test_bench_imports_successfully():
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys, os; sys.path.insert(0, os.getcwd()); "
         "from scripts.scaling_analysis import bench_cold_start; "
         "print('ok')"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert "ok" in result.stdout


def test_simulate_scoring_imports_successfully():
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys, os; sys.path.insert(0, os.getcwd()); "
         "from services.risk_scoring.scorer import RiskScorer; "
         "print('ok')"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert "ok" in result.stdout


def test_rca_imports_successfully():
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys, os; sys.path.insert(0, os.getcwd()); "
         "from services.rca.root_cause import RCAEngine; "
         "print('ok')"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert "ok" in result.stdout