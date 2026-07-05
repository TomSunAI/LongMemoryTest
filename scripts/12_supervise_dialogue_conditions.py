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


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _mac_awake import (  # noqa: E402
    DEFAULT_CAFFEINATE_FLAGS,
    awake_guard_metadata,
    mark_caffeinate_disabled,
    maybe_reexec_under_awake_guard,
    parse_caffeinate_flags,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
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
    caffeinate_flags = parse_caffeinate_flags(args.caffeinate_flags)
    reexec_code = maybe_reexec_under_awake_guard(
        sys.argv,
        disabled=args.no_caffeinate,
        flags=caffeinate_flags,
    )
    if reexec_code is not None:
        return reexec_code

    run_dir = args.run_dir or _default_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    status_path = args.supervisor_status or run_dir / "dialogue_supervisor_status.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = _pythonpath(env)
    if args.no_caffeinate:
        mark_caffeinate_disabled(env)
    awake_guard = awake_guard_metadata(
        disabled=args.no_caffeinate,
        flags=caffeinate_flags,
    )

    attempt = 0
    while True:
        attempt += 1
        resume = _has_checkpoint(run_dir) or "--resume" in passthrough
        cmd = _build_dialogue_cmd(
            run_dir=run_dir,
            passthrough=passthrough,
            resume=resume,
        )
        started_at = _now()
        _write_status(
            status_path,
            {
                "schema_version": "dialogue_conditions_supervisor_v1",
                "status": "running",
                "attempt": attempt,
                "run_dir": _display_path(run_dir),
                "started_at": started_at,
                "command": cmd,
                "command_text": shlex.join(cmd),
                "max_attempts": args.max_attempts,
                "retry_sleep": args.retry_sleep,
                "awake_guard": awake_guard,
            },
        )
        print(f"\n==> dialogue supervised attempt {attempt}", flush=True)
        print(shlex.join(cmd), flush=True)
        return_code = subprocess.run(cmd, cwd=REPO_ROOT, env=env).returncode
        ended_at = _now()
        if return_code == 0:
            _write_status(
                status_path,
                {
                    "schema_version": "dialogue_conditions_supervisor_v1",
                    "status": "complete",
                    "attempt": attempt,
                    "run_dir": _display_path(run_dir),
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "return_code": return_code,
                    "command": cmd,
                    "command_text": shlex.join(cmd),
                    "awake_guard": awake_guard,
                },
            )
            print(f"\nSupervised dialogue conditions complete: {run_dir}", flush=True)
            return 0

        exhausted = args.max_attempts > 0 and attempt >= args.max_attempts
        _write_status(
            status_path,
            {
                "schema_version": "dialogue_conditions_supervisor_v1",
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
                "awake_guard": awake_guard,
            },
        )
        if exhausted:
            print(f"\nSupervised dialogue conditions failed after {attempt} attempts.", flush=True)
            return return_code
        print(
            f"\nAttempt {attempt} failed with code {return_code}; "
            f"retrying with --resume in {args.retry_sleep:g}s.",
            flush=True,
        )
        time.sleep(max(args.retry_sleep, 0.0))


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


def _write_status(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _default_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return DEFAULT_RUN_ROOT / f"run_{stamp}_dialogue_supervised"


def _pythonpath(env: dict[str, str]) -> str:
    existing = env.get("PYTHONPATH")
    if existing:
        return f"{SRC_ROOT}{os.pathsep}{existing}"
    return str(SRC_ROOT)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
