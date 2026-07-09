#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _mac_awake import (  # noqa: E402
    DEFAULT_CAFFEINATE_FLAGS,
)
from _backend_common import start_background_job  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = REPO_ROOT / "long_memory_experiment/outputs"


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=(
            "Start supervised run_dialogue_conditions.py in the background. "
            "Unknown arguments are forwarded to 12_supervise_dialogue_conditions.py."
        )
    )
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--log-file", type=Path, default=None)
    parser.add_argument("--pid-file", type=Path, default=None)
    parser.add_argument("--no-caffeinate", action="store_true")
    parser.add_argument("--caffeinate-flags", default=DEFAULT_CAFFEINATE_FLAGS)
    return parser.parse_known_args()


def main() -> int:
    args, passthrough = parse_args()
    run_dir = args.run_dir or _default_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = args.log_file or run_dir / "dialogue_supervisor.log"
    pid_file = args.pid_file or run_dir / "dialogue_supervisor.pid.json"
    supervisor_passthrough = list(passthrough)
    if args.no_caffeinate:
        supervisor_passthrough.append("--no-caffeinate")
    elif args.caffeinate_flags != DEFAULT_CAFFEINATE_FLAGS:
        supervisor_passthrough.extend(["--caffeinate-flags", args.caffeinate_flags])
    cmd = [
        sys.executable,
        "scripts/12_supervise_dialogue_conditions.py",
        "--run-dir",
        str(run_dir),
        *supervisor_passthrough,
    ]
    return start_background_job(
        command=cmd,
        run_dir=run_dir,
        log_file=log_file,
        pid_file=pid_file,
        schema_version="dialogue_conditions_background_pid_v1",
        job_label="dialogue supervisor",
        command_label="supervisor_command",
        no_caffeinate=args.no_caffeinate,
        caffeinate_flags_value=args.caffeinate_flags,
    )


def _default_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return DEFAULT_RUN_ROOT / f"run_{stamp}_dialogue_background"


if __name__ == "__main__":
    raise SystemExit(main())
