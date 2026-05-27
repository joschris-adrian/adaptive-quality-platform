#!/usr/bin/env python3
"""
Adaptive Quality Platform — cross-platform task runner.
Usage: python run.py <command> [--svc <service>]
"""

import sys
import os
import subprocess
import argparse


COMPOSE_FILE = os.path.join("dashboards", "grafana", "docker-compose.yml")
ENV_FILE     = ".env"
NAMESPACE    = "adaptive-quality"


def compose(*args):
    return ["docker", "compose", "--env-file", ENV_FILE, "-f", COMPOSE_FILE, *args]


def run(cmd, **kwargs):
    print(f"» {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        sys.exit(result.returncode)


def help_text():
    print("""
Adaptive Quality Platform — available commands

  Local stack
    python run.py up                   start Grafana, Postgres, Prometheus
    python run.py down                 stop the stack
    python run.py restart              restart all containers
    python run.py logs                 tail logs from all containers
    python run.py ps                   show container status
    python run.py shell-postgres       open psql shell
    python run.py init-db              apply schema.sql to the database

  Tests
    python run.py test                 run all tests
    python run.py coverage             run tests with coverage report

  Benchmarks
    python run.py bench                run scaling benchmarks

  Scripts
    python run.py api                  start FastAPI server
    python run.py seed                 send 500 synthetic events to the API
    python run.py seed-db              seed PostgreSQL with synthetic data for dashboards
    python run.py simulate-scoring     score two test events end-to-end
    python run.py run-comparison       quality vs cost strategy comparison
    python run.py rca                  run the RCA engine
    python run.py report               generate a platform report
    python run.py ab-experiment        run the A/B routing experiment
    python run.py platform-experiments run all four key experiments
    python run.py mlflow-up            start MLflow tracking server
    python run.py mlflow-down          stop MLflow server
    python run.py train                train classifier and log to MLflow

  Kubernetes
    python run.py k8s-up               deploy all manifests
    python run.py k8s-down             delete the namespace
    python run.py k8s-status           show pods and HPAs
    python run.py k8s-logs --svc <name> tail logs for a service
""")


COMMANDS = {

    # ── local stack ───────────────────────────────────────────────────────
    "up": lambda _: run(compose("up", "-d")),

    "down": lambda _: run(compose("down")),

    "restart": lambda _: run(compose("restart")),

    "logs": lambda _: run(compose("logs", "-f", "--tail", "50")),

    "ps": lambda _: run(compose("ps")),

    "shell-postgres": lambda _: run(
        compose("exec", "postgres", "psql", "-U", "aqp", "-d", "adaptive_quality")
    ),

    "init-db": lambda _: run(
        compose(
            "exec", "postgres", "psql",
            "-U", "aqp",
            "-d", "adaptive_quality",
            "-f", "/docker-entrypoint-initdb.d/schema.sql",
        )
    ),
    
    

    # ── tests ─────────────────────────────────────────────────────────────
    "test": lambda _: run([sys.executable, "-m", "pytest", "-v"]),

    "coverage": lambda _: run([
        sys.executable, "-m", "pytest",
        "--cov=services", "--cov-report=term-missing",
    ]),

    # ── benchmarks ────────────────────────────────────────────────────────
    "bench": lambda _: run(
        [sys.executable, "scripts/scaling_analysis.py"]
    ),

    # ── scripts ───────────────────────────────────────────────────────────
    "api": lambda _: run([
    sys.executable, "-m", "uvicorn",
    "api.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
    ]),
    
    "seed": lambda _: run(
        [sys.executable, "scripts/synthetic_data_generator.py"]
    ),
    
    "seed-db": lambda _: run(
        [sys.executable, "scripts/seed_database.py"]
    ),

    "simulate-scoring": lambda _: run(
        [sys.executable, "scripts/simulate_scoring.py"]
    ),

    "run-comparison": lambda _: run(
        [sys.executable, "scripts/run_comparison.py"]
    ),

    "rca": lambda _: run(
        [sys.executable, "scripts/run_rca.py"]
    ),

    "report": lambda _: run(
        [sys.executable, "scripts/run_report.py"]
    ),

    "ab-experiment": lambda _: run(
        [sys.executable, "scripts/run_ab_experiment.py"]
    ),

    "platform-experiments": lambda _: run(
        [sys.executable, "scripts/run_platform_experiments.py"]
    ),
    
    "mlflow-up": lambda _: run(compose("up", "-d", "mlflow")),

    "mlflow-down": lambda _: run(compose("stop", "mlflow")),

    "train": lambda _: run(
        [sys.executable, "scripts/train_classifier.py"]
    ),

    # ── kubernetes ────────────────────────────────────────────────────────
    "k8s-up": lambda _: [
        run(["kubectl", "apply", "-f", f"k8s/{manifest}"])
        for manifest in [
            "namespace.yaml",
            "configmap.yaml",
            "secret.yaml",
            "postgres.yaml",
            "kafka.yaml",
            "kafka-init-job.yaml",
            "detection.yaml",
            "risk-scoring.yaml",
            "routing.yaml",
            "analytics.yaml",
            "api.yaml",
            "mlflow.yaml",
            "snapshot-cronjob.yaml",
            "keda-scaledobjects.yaml",
        ]
    ],

    "k8s-down": lambda _: run(
        ["kubectl", "delete", "namespace", NAMESPACE]
    ),

    "k8s-status": lambda _: [
        run(["kubectl", "get", "pods", "-n", NAMESPACE]),
        run(["kubectl", "get", "hpa",  "-n", NAMESPACE]),
    ],

    "k8s-logs": lambda args: (
        run(["kubectl", "logs", "-n", NAMESPACE,
             "-l", f"app={args.svc}", "--tail", "50", "-f"])
        if args.svc else
        _exit("k8s-logs requires --svc <service-name>")
    ),

    "help": lambda _: help_text(),
}


def _exit(msg: str):
    print(f"Error: {msg}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Adaptive Quality Platform task runner",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("--svc", default="", help="Service name for k8s-logs")
    args = parser.parse_args()

    cmd = args.command
    if cmd not in COMMANDS:
        print(f"Unknown command: '{cmd}'")
        print("Run 'python run.py help' to see available commands.")
        sys.exit(1)

    COMMANDS[cmd](args)


if __name__ == "__main__":
    main()