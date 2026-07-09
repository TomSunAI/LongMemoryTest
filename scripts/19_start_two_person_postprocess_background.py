#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _mac_awake import (  # noqa: E402
    DEFAULT_CAFFEINATE_FLAGS,
)
from _backend_common import start_background_job  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=(
            "Start two-person postprocess/evaluation in the background. "
            "Unknown arguments are forwarded to 20_supervise_two_person_postprocess.py."
        )
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--log-file", type=Path, default=None)
    parser.add_argument("--pid-file", type=Path, default=None)
    parser.add_argument("--no-caffeinate", action="store_true")
    parser.add_argument("--caffeinate-flags", default=DEFAULT_CAFFEINATE_FLAGS)
    return parser.parse_known_args()


def main() -> int:
    args, passthrough = parse_args()
    run_dir = args.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = args.log_file or run_dir / "eval_supervisor.log"
    pid_file = args.pid_file or run_dir / "eval_supervisor.pid.json"
    cmd = [
        sys.executable,
        "scripts/20_supervise_two_person_postprocess.py",
        "--run-dir",
        str(run_dir),
        *passthrough,
    ]
    return start_background_job(
        command=cmd,
        run_dir=run_dir,
        log_file=log_file,
        pid_file=pid_file,
        schema_version="two_person_eval_background_pid_v1",
        job_label="two-person evaluation",
        command_label="supervisor_command",
        no_caffeinate=args.no_caffeinate,
        caffeinate_flags_value=args.caffeinate_flags,
    )


if __name__ == "__main__":
    raise SystemExit(main())
