#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
DEFAULT_RUN_ROOT = REPO_ROOT / "long_memory_experiment/outputs"


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=(
            "Supervise the full long-memory experiment. If a stage fails, retry "
            "the same run directory with --resume so completed dialogue turns are skipped."
        )
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Run directory. Defaults to long_memory_experiment/outputs/run_YYYYMMDD_HHMM_full_supervised.",
    )
    parser.add_argument(
        "--rebuild-data",
        action="store_true",
        help="Forward --rebuild-data only on the first attempt.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Force --resume on the first attempt.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=0,
        help="Maximum attempts. 0 means retry forever until the full runner exits successfully.",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=30.0,
        help="Seconds to sleep between failed attempts.",
    )
    parser.add_argument(
        "--supervisor-status",
        type=Path,
        default=None,
        help="Status JSON path. Defaults to RUN_DIR/supervisor_status.json.",
    )
    return parser.parse_known_args()


def main() -> int:
    args, passthrough = parse_args()
    run_dir = args.run_dir or _default_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    status_path = args.supervisor_status or run_dir / "supervisor_status.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = _pythonpath(env)

    attempt = 0
    while True:
        attempt += 1
        cmd = _build_full_runner_cmd(
            run_dir=run_dir,
            passthrough=passthrough,
            rebuild_data=args.rebuild_data and attempt == 1,
            resume=args.resume or attempt > 1 or _has_checkpoint(run_dir),
        )
        started_at = _now()
        _write_status(
            status_path,
            {
                "schema_version": "full_experiment_supervisor_v1",
                "status": "running",
                "attempt": attempt,
                "run_dir": _display_path(run_dir),
                "started_at": started_at,
                "command": cmd,
                "command_text": shlex.join(cmd),
                "max_attempts": args.max_attempts,
                "retry_sleep": args.retry_sleep,
            },
        )
        print(f"\n==> supervised attempt {attempt}", flush=True)
        print(shlex.join(cmd), flush=True)
        return_code = subprocess.run(cmd, cwd=REPO_ROOT, env=env).returncode
        ended_at = _now()
        if return_code == 0:
            _write_status(
                status_path,
                {
                    "schema_version": "full_experiment_supervisor_v1",
                    "status": "complete",
                    "attempt": attempt,
                    "run_dir": _display_path(run_dir),
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "return_code": return_code,
                    "command": cmd,
                    "command_text": shlex.join(cmd),
                },
            )
            print(f"\nSupervised full experiment complete: {run_dir}", flush=True)
            return 0

        exhausted = args.max_attempts > 0 and attempt >= args.max_attempts
        _write_status(
            status_path,
            {
                "schema_version": "full_experiment_supervisor_v1",
                "status": "failed" if exhausted else "retry_wait",
                "attempt": attempt,
                "run_dir": _display_path(run_dir),
                "started_at": started_at,
                "ended_at": ended_at,
                "return_code": return_code,
                "command": cmd,
                "command_text": shlex.join(cmd),
                "next_attempt_after_seconds": None if exhausted else args.retry_sleep,
                "max_attempts": args.max_attempts,
            },
        )
        if exhausted:
            print(f"\nSupervised full experiment failed after {attempt} attempts.", flush=True)
            return return_code
        print(
            f"\nAttempt {attempt} failed with code {return_code}; "
            f"retrying with --resume in {args.retry_sleep:g}s.",
            flush=True,
        )
        time.sleep(max(args.retry_sleep, 0.0))


def _build_full_runner_cmd(
    *,
    run_dir: Path,
    passthrough: list[str],
    rebuild_data: bool,
    resume: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/09_run_full_experiment.py",
        "--run-dir",
        str(run_dir),
        *passthrough,
    ]
    if rebuild_data:
        cmd.append("--rebuild-data")
    if resume:
        cmd.append("--resume")
    return cmd


def _has_checkpoint(run_dir: Path) -> bool:
    return (run_dir / "responses_by_condition.json").exists()


def _write_status(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _default_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return DEFAULT_RUN_ROOT / f"run_{stamp}_full_supervised"


def _pythonpath(env: dict[str, str]) -> str:
    existing = env.get("PYTHONPATH")
    if existing:
        return f"{SRC_ROOT}{os.pathsep}{existing}"
    return str(SRC_ROOT)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
