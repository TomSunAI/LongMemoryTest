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
from _backend_common import supervise_command_attempts  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = REPO_ROOT / "long_memory_experiment/outputs"


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=(
            "Supervise two-person postprocess/evaluation in a background-safe loop. "
            "Unknown arguments are forwarded to 18_run_two_person_postprocess_after_generation.py."
        )
    )
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--retry-sleep", type=float, default=30.0)
    parser.add_argument("--postprocess-status", type=Path, default=None)
    parser.add_argument("--no-caffeinate", action="store_true")
    parser.add_argument("--caffeinate-flags", default=DEFAULT_CAFFEINATE_FLAGS)
    return parser.parse_known_args()


def main() -> int:
    args, passthrough = parse_args()
    run_dir = args.run_dir or _default_run_dir()
    status_path = args.postprocess_status or run_dir / "two_person_postprocess_status.json"

    return supervise_command_attempts(
        run_dir=run_dir,
        status_path=status_path,
        schema_version="two_person_postprocess_supervisor_v1",
        job_label="Two-person postprocess",
        command_factory=lambda _attempt: _build_postprocess_cmd(
            run_dir=run_dir,
            passthrough=passthrough,
        ),
        max_attempts=args.max_attempts,
        retry_sleep=args.retry_sleep,
        no_caffeinate=args.no_caffeinate,
        caffeinate_flags_value=args.caffeinate_flags,
    )


def _build_postprocess_cmd(*, run_dir: Path, passthrough: list[str]) -> list[str]:
    return [
        sys.executable,
        "scripts/18_run_two_person_postprocess_after_generation.py",
        "--run-dir",
        str(run_dir),
        *passthrough,
    ]


def _default_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return DEFAULT_RUN_ROOT / f"run_{stamp}_two_person_postprocess"


if __name__ == "__main__":
    raise SystemExit(main())
