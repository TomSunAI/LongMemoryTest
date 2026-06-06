#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = REPO_ROOT / "long_memory_experiment/outputs"


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=(
            "Start the supervised full long-memory experiment in the background. "
            "Unknown arguments are forwarded to 10_supervise_full_experiment.py and then "
            "to 09_run_full_experiment.py."
        )
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Run directory. Defaults to long_memory_experiment/outputs/run_YYYYMMDD_HHMM_full_background.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Background log path. Defaults to RUN_DIR/background_supervisor.log.",
    )
    parser.add_argument(
        "--pid-file",
        type=Path,
        default=None,
        help="PID metadata path. Defaults to RUN_DIR/background_supervisor.pid.json.",
    )
    return parser.parse_known_args()


def main() -> int:
    args, passthrough = parse_args()
    run_dir = args.run_dir or _default_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = args.log_file or run_dir / "background_supervisor.log"
    pid_file = args.pid_file or run_dir / "background_supervisor.pid.json"
    cmd = [
        sys.executable,
        "scripts/10_supervise_full_experiment.py",
        "--run-dir",
        str(run_dir),
        *passthrough,
    ]
    env = dict(os.environ)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_file.open("ab")
    process = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log_handle.close()
    pid_payload = {
        "schema_version": "full_experiment_background_pid_v1",
        "status": "started",
        "pid": process.pid,
        "run_dir": _display_path(run_dir),
        "log_file": _display_path(log_file),
        "pid_file": _display_path(pid_file),
        "started_at": _now(),
        "command": cmd,
        "command_text": shlex.join(cmd),
    }
    _write_json(pid_file, pid_payload)
    print(f"Started background full experiment supervisor: pid={process.pid}")
    print(f"Run dir: {run_dir}")
    print(f"Log: {log_file}")
    print(f"PID file: {pid_file}")
    return 0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _default_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return DEFAULT_RUN_ROOT / f"run_{stamp}_full_background"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
