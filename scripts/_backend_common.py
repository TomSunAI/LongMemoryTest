from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _mac_awake import (
    awake_guard_metadata,
    mark_caffeinate_disabled,
    mark_caffeinated,
    maybe_reexec_under_awake_guard,
    parse_caffeinate_flags,
    wrap_command_for_awake,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def env_with_src_path(*, no_caffeinate: bool) -> dict[str, str]:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{existing}" if existing else str(SRC_ROOT)
    if no_caffeinate:
        mark_caffeinate_disabled(env)
    return env


def start_background_job(
    *,
    command: list[str],
    run_dir: Path,
    log_file: Path,
    pid_file: Path,
    schema_version: str,
    job_label: str,
    command_label: str,
    no_caffeinate: bool,
    caffeinate_flags_value: str,
    extra_payload: dict[str, Any] | None = None,
) -> int:
    run_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    caffeinate_flags = parse_caffeinate_flags(caffeinate_flags_value)
    if no_caffeinate:
        mark_caffeinate_disabled(env)
    launch_cmd, awake_guard = wrap_command_for_awake(
        command,
        disabled=no_caffeinate,
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
    payload = {
        "schema_version": schema_version,
        "status": "started",
        "pid": process.pid,
        "run_dir": display_path(run_dir),
        "log_file": display_path(log_file),
        "pid_file": display_path(pid_file),
        "started_at": now_utc(),
        "command": launch_cmd,
        "command_text": shlex.join(launch_cmd),
        command_label: command,
        f"{command_label}_text": shlex.join(command),
        "awake_guard": awake_guard,
        **(extra_payload or {}),
    }
    write_json_atomic(pid_file, payload)
    print(f"Started background {job_label}: pid={process.pid}")
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


def supervise_command_attempts(
    *,
    run_dir: Path,
    status_path: Path,
    schema_version: str,
    job_label: str,
    command_factory: Callable[[int], list[str]],
    max_attempts: int,
    retry_sleep: float,
    no_caffeinate: bool,
    caffeinate_flags_value: str,
    retry_message: Callable[[int, int, float], str] | None = None,
) -> int:
    caffeinate_flags = parse_caffeinate_flags(caffeinate_flags_value)
    reexec_code = maybe_reexec_under_awake_guard(
        sys.argv,
        disabled=no_caffeinate,
        flags=caffeinate_flags,
    )
    if reexec_code is not None:
        return reexec_code

    run_dir.mkdir(parents=True, exist_ok=True)
    env = env_with_src_path(no_caffeinate=no_caffeinate)
    awake_guard = awake_guard_metadata(
        disabled=no_caffeinate,
        flags=caffeinate_flags,
    )
    attempt = 0
    while True:
        attempt += 1
        cmd = command_factory(attempt)
        started_at = now_utc()
        write_json_atomic(
            status_path,
            {
                "schema_version": schema_version,
                "status": "running",
                "attempt": attempt,
                "run_dir": display_path(run_dir),
                "started_at": started_at,
                "command": cmd,
                "command_text": shlex.join(cmd),
                "max_attempts": max_attempts,
                "retry_sleep": retry_sleep,
                "awake_guard": awake_guard,
            },
        )
        print(f"\n==> {job_label} attempt {attempt}", flush=True)
        print(shlex.join(cmd), flush=True)
        return_code = subprocess.run(cmd, cwd=REPO_ROOT, env=env).returncode
        ended_at = now_utc()
        if return_code == 0:
            write_json_atomic(
                status_path,
                {
                    "schema_version": schema_version,
                    "status": "complete",
                    "attempt": attempt,
                    "run_dir": display_path(run_dir),
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "return_code": return_code,
                    "command": cmd,
                    "command_text": shlex.join(cmd),
                    "awake_guard": awake_guard,
                },
            )
            print(f"\n{job_label} complete: {run_dir}", flush=True)
            return 0

        exhausted = max_attempts > 0 and attempt >= max_attempts
        write_json_atomic(
            status_path,
            {
                "schema_version": schema_version,
                "status": "failed" if exhausted else "retry_wait",
                "attempt": attempt,
                "run_dir": display_path(run_dir),
                "started_at": started_at,
                "ended_at": ended_at,
                "return_code": return_code,
                "command": cmd,
                "command_text": shlex.join(cmd),
                "next_attempt_after_seconds": None if exhausted else retry_sleep,
                "max_attempts": max_attempts,
                "awake_guard": awake_guard,
            },
        )
        if exhausted:
            print(f"\n{job_label} failed after {attempt} attempts.", flush=True)
            return return_code
        message = (
            retry_message(attempt, return_code, retry_sleep)
            if retry_message
            else (
                f"\nAttempt {attempt} failed with code {return_code}; "
                f"retrying in {retry_sleep:g}s."
            )
        )
        print(message, flush=True)
        time.sleep(max(retry_sleep, 0.0))
