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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _mac_awake import (
    DEFAULT_CAFFEINATE_FLAGS,
    mark_caffeinate_disabled,
    mark_caffeinated,
    parse_caffeinate_flags,
    wrap_command_for_awake,
)


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
    parser.add_argument(
        "--no-caffeinate",
        action="store_true",
        help=(
            "Disable the macOS caffeinate awake guard. By default the background "
            "supervisor prevents system sleep while allowing display sleep."
        ),
    )
    parser.add_argument(
        "--caffeinate-flags",
        default=DEFAULT_CAFFEINATE_FLAGS,
        help=(
            "Flags passed to caffeinate on macOS. Default '-i -m -s' prevents "
            "idle system sleep and disk sleep without preventing display sleep."
        ),
    )
    return parser.parse_known_args()


def main() -> int:
    args, passthrough = parse_args()
    run_dir = args.run_dir or _default_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = args.log_file or run_dir / "background_supervisor.log"
    pid_file = args.pid_file or run_dir / "background_supervisor.pid.json"
    supervisor_passthrough = list(passthrough)
    if args.no_caffeinate:
        supervisor_passthrough.append("--no-caffeinate")
    elif args.caffeinate_flags != DEFAULT_CAFFEINATE_FLAGS:
        supervisor_passthrough.extend(["--caffeinate-flags", args.caffeinate_flags])
    cmd = [
        sys.executable,
        "scripts/10_supervise_full_experiment.py",
        "--run-dir",
        str(run_dir),
        *supervisor_passthrough,
    ]
    env = dict(os.environ)
    caffeinate_flags = parse_caffeinate_flags(args.caffeinate_flags)
    if args.no_caffeinate:
        mark_caffeinate_disabled(env)
    launch_cmd, awake_guard = wrap_command_for_awake(
        cmd,
        disabled=args.no_caffeinate,
        flags=caffeinate_flags,
    )
    if awake_guard["enabled"]:
        mark_caffeinated(env)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_file.open("ab")
    process = subprocess.Popen(
        launch_cmd,
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
        "command": launch_cmd,
        "command_text": shlex.join(launch_cmd),
        "supervisor_command": cmd,
        "supervisor_command_text": shlex.join(cmd),
        "awake_guard": awake_guard,
    }
    _write_json(pid_file, pid_payload)
    print(f"Started background full experiment supervisor: pid={process.pid}")
    print(f"Run dir: {run_dir}")
    print(f"Log: {log_file}")
    print(f"PID file: {pid_file}")
    print(
        "Awake guard: "
        + (
            f"enabled via caffeinate {' '.join(caffeinate_flags)} "
            "(display may sleep)"
            if awake_guard["enabled"]
            else f"not enabled ({awake_guard['reason']})"
        )
    )
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
