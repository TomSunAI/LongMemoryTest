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
            "Supervise run_dialogue_conditions.py in a background-safe loop. "
            "Failed attempts are retried with --resume."
        )
    )
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--max-attempts", type=int, default=0)
    parser.add_argument("--retry-sleep", type=float, default=30.0)
    parser.add_argument("--supervisor-status", type=Path, default=None)
    parser.add_argument("--no-caffeinate", action="store_true")
    parser.add_argument("--caffeinate-flags", default=DEFAULT_CAFFEINATE_FLAGS)
    return parser.parse_known_args()


def main() -> int:
    args, passthrough = parse_args()
    run_dir = args.run_dir or _default_run_dir()
    status_path = args.supervisor_status or run_dir / "dialogue_supervisor_status.json"

    def command_factory(_attempt: int) -> list[str]:
        resume = _has_checkpoint(run_dir) or "--resume" in passthrough
        return _build_dialogue_cmd(
            run_dir=run_dir,
            passthrough=passthrough,
            resume=resume,
        )

    return supervise_command_attempts(
        run_dir=run_dir,
        status_path=status_path,
        schema_version="dialogue_conditions_supervisor_v1",
        job_label="Supervised dialogue conditions",
        command_factory=command_factory,
        max_attempts=args.max_attempts,
        retry_sleep=args.retry_sleep,
        no_caffeinate=args.no_caffeinate,
        caffeinate_flags_value=args.caffeinate_flags,
        retry_message=lambda attempt, return_code, retry_sleep: (
            f"\nAttempt {attempt} failed with code {return_code}; "
            f"retrying with --resume in {retry_sleep:g}s."
        )
    )


def _build_dialogue_cmd(
    *,
    run_dir: Path,
    passthrough: list[str],
    resume: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/run_dialogue_conditions.py",
        "--run-dir",
        str(run_dir),
        *passthrough,
    ]
    if resume and "--resume" not in passthrough:
        cmd.append("--resume")
    elif not resume and "--reset-conversation-log" not in passthrough:
        cmd.append("--reset-conversation-log")
    return cmd


def _has_checkpoint(run_dir: Path) -> bool:
    return (run_dir / "responses_by_condition.json").exists()


def _default_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return DEFAULT_RUN_ROOT / f"run_{stamp}_dialogue_supervised"


if __name__ == "__main__":
    raise SystemExit(main())
