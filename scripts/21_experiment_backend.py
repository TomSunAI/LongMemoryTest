#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _backend_common import (  # noqa: E402
    REPO_ROOT,
    display_path,
    now_utc,
    start_background_job,
    write_json_atomic,
)
from _mac_awake import DEFAULT_CAFFEINATE_FLAGS  # noqa: E402


DEFAULT_RUN_ROOT = REPO_ROOT / "long_memory_experiment/outputs"
DEFAULT_DOCS_DIR = REPO_ROOT / "docs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unified backend entry for condition/runtime comparison experiments."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start a detached backend job.")
    _add_common_args(start)

    run = subparsers.add_parser("run", help="Run the backend job in this process.")
    _add_common_args(run)

    status = subparsers.add_parser("status", help="Print compact backend job status.")
    status.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "start":
        return _start(args)
    if args.command == "run":
        return _run(args)
    if args.command == "status":
        return _status(args.run_dir)
    raise ValueError(f"Unsupported command: {args.command}")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--stages", default="generate,evaluate")
    parser.add_argument("--runtime-profile", default="tau_two_person")
    parser.add_argument("--conditions", default="M0,M1,M2,M3")
    parser.add_argument("--daily-messages", type=Path, default=None)
    parser.add_argument("--scene-cards", type=Path, default=None)
    parser.add_argument("--probe-questions", type=Path, default=None)
    parser.add_argument("--no-probe-questions", action="store_true")
    parser.add_argument("--memory-conditions", type=Path, default=None)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Trajectory data directory used by reports for persona/profile metadata.",
    )
    parser.add_argument("--all-message-ids", action="store_true", default=True)
    parser.add_argument("--message-ids", default=None)
    parser.add_argument("--condition-workers", type=int, default=4)
    parser.add_argument("--llm-timeout", type=float, default=900.0)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--print-progress", action="store_true", default=True)
    parser.add_argument("--generation-max-attempts", type=int, default=0)
    parser.add_argument("--generation-retry-sleep", type=float, default=30.0)
    parser.add_argument("--personas", default="P0001,P0002")
    parser.add_argument("--judge-workers", type=int, default=4)
    parser.add_argument("--judge-provider", default="deepseek")
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--eval-max-attempts", type=int, default=1)
    parser.add_argument("--eval-retry-sleep", type=float, default=30.0)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--no-caffeinate", action="store_true")
    parser.add_argument("--caffeinate-flags", default=DEFAULT_CAFFEINATE_FLAGS)


def _start(args: argparse.Namespace) -> int:
    run_dir = args.run_dir or _default_run_dir(args.conditions)
    command = [
        sys.executable,
        "scripts/21_experiment_backend.py",
        "run",
        *_common_cli_args(args, run_dir=run_dir),
    ]
    return start_background_job(
        command=command,
        run_dir=run_dir,
        log_file=run_dir / "backend_supervisor.log",
        pid_file=run_dir / "backend_supervisor.pid.json",
        schema_version="experiment_backend_pid_v1",
        job_label="experiment backend",
        command_label="backend_command",
        no_caffeinate=args.no_caffeinate,
        caffeinate_flags_value=args.caffeinate_flags,
        extra_payload={
            "runtime_profile": args.runtime_profile,
            "conditions": _conditions(args.conditions),
            "stages": _stages(args.stages),
            "docs_dir": display_path(args.docs_dir),
        },
    )


def _run(args: argparse.Namespace) -> int:
    run_dir = args.run_dir or _default_run_dir(args.conditions)
    run_dir.mkdir(parents=True, exist_ok=True)
    job_path = run_dir / "backend_job.json"
    stages = _stages(args.stages)
    _write_job(
        job_path,
        args,
        run_dir=run_dir,
        status="running",
        active_stage=None,
    )
    try:
        if "generate" in stages:
            cmd = _generation_supervisor_cmd(args, run_dir)
            _write_job(job_path, args, run_dir=run_dir, status="generating", active_stage="generate", command=cmd)
            _run_checked(cmd)
            _write_job(job_path, args, run_dir=run_dir, status="generation_complete", active_stage=None)
        if "evaluate" in stages:
            cmd = _evaluation_supervisor_cmd(args, run_dir)
            _write_job(job_path, args, run_dir=run_dir, status="evaluating", active_stage="evaluate", command=cmd)
            _run_checked(cmd)
        _write_job(job_path, args, run_dir=run_dir, status="complete", active_stage=None)
        return 0
    except subprocess.CalledProcessError as exc:
        _write_job(
            job_path,
            args,
            run_dir=run_dir,
            status="failed",
            active_stage=None,
            command=list(exc.cmd) if isinstance(exc.cmd, list) else [str(exc.cmd)],
            error=f"return_code={exc.returncode}",
        )
        return int(exc.returncode)


def _status(run_dir: Path) -> int:
    paths = {
        "backend": run_dir / "backend_job.json",
        "generation": run_dir / "dialogue_supervisor_status.json",
        "evaluation": run_dir / "eval_status.json",
        "postprocess": run_dir / "two_person_postprocess_status.json",
    }
    payload = {
        key: _load_json(path)
        for key, path in paths.items()
        if path.exists()
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _generation_supervisor_cmd(args: argparse.Namespace, run_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/12_supervise_dialogue_conditions.py",
        "--run-dir",
        str(run_dir),
        "--max-attempts",
        str(args.generation_max_attempts),
        "--retry-sleep",
        str(args.generation_retry_sleep),
        "--conditions",
        args.conditions,
        "--condition-workers",
        str(args.condition_workers),
        "--llm-timeout",
        str(args.llm_timeout),
    ]
    _append_path_arg(cmd, "--daily-messages", args.daily_messages)
    _append_path_arg(cmd, "--scene-cards", args.scene_cards)
    _append_path_arg(cmd, "--probe-questions", args.probe_questions)
    _append_path_arg(cmd, "--memory-conditions", args.memory_conditions)
    if args.no_probe_questions:
        cmd.append("--no-probe-questions")
    if args.message_ids:
        cmd.extend(["--message-ids", args.message_ids])
    elif args.all_message_ids:
        cmd.append("--all-message-ids")
    if args.temperature is not None:
        cmd.extend(["--temperature", str(args.temperature)])
    if args.top_p is not None:
        cmd.extend(["--top-p", str(args.top_p)])
    if args.max_tokens is not None:
        cmd.extend(["--max-tokens", str(args.max_tokens)])
    if args.print_progress:
        cmd.append("--print-progress")
    if args.no_caffeinate:
        cmd.append("--no-caffeinate")
    elif args.caffeinate_flags != DEFAULT_CAFFEINATE_FLAGS:
        cmd.extend(["--caffeinate-flags", args.caffeinate_flags])
    return cmd


def _evaluation_supervisor_cmd(args: argparse.Namespace, run_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/20_supervise_two_person_postprocess.py",
        "--run-dir",
        str(run_dir),
        "--max-attempts",
        str(args.eval_max_attempts),
        "--retry-sleep",
        str(args.eval_retry_sleep),
        "--personas",
        args.personas,
        "--judge-workers",
        str(args.judge_workers),
        "--judge-provider",
        args.judge_provider,
        "--variants",
        args.conditions,
        "--poll-seconds",
        str(args.poll_seconds),
        "--docs-dir",
        str(args.docs_dir),
    ]
    _append_path_arg(cmd, "--data-dir", args.data_dir)
    if args.no_caffeinate:
        cmd.append("--no-caffeinate")
    elif args.caffeinate_flags != DEFAULT_CAFFEINATE_FLAGS:
        cmd.extend(["--caffeinate-flags", args.caffeinate_flags])
    return cmd


def _common_cli_args(args: argparse.Namespace, *, run_dir: Path) -> list[str]:
    cli = [
        "--run-dir",
        str(run_dir),
        "--stages",
        args.stages,
        "--runtime-profile",
        args.runtime_profile,
        "--conditions",
        args.conditions,
        "--condition-workers",
        str(args.condition_workers),
        "--llm-timeout",
        str(args.llm_timeout),
        "--generation-max-attempts",
        str(args.generation_max_attempts),
        "--generation-retry-sleep",
        str(args.generation_retry_sleep),
        "--personas",
        args.personas,
        "--judge-workers",
        str(args.judge_workers),
        "--judge-provider",
        args.judge_provider,
        "--eval-max-attempts",
        str(args.eval_max_attempts),
        "--eval-retry-sleep",
        str(args.eval_retry_sleep),
        "--poll-seconds",
        str(args.poll_seconds),
    ]
    _append_path_arg(cli, "--daily-messages", args.daily_messages)
    _append_path_arg(cli, "--scene-cards", args.scene_cards)
    _append_path_arg(cli, "--probe-questions", args.probe_questions)
    _append_path_arg(cli, "--memory-conditions", args.memory_conditions)
    _append_path_arg(cli, "--data-dir", args.data_dir)
    _append_path_arg(cli, "--docs-dir", args.docs_dir)
    if args.no_probe_questions:
        cli.append("--no-probe-questions")
    if args.message_ids:
        cli.extend(["--message-ids", args.message_ids])
    if args.temperature is not None:
        cli.extend(["--temperature", str(args.temperature)])
    if args.top_p is not None:
        cli.extend(["--top-p", str(args.top_p)])
    if args.max_tokens is not None:
        cli.extend(["--max-tokens", str(args.max_tokens)])
    if args.print_progress:
        cli.append("--print-progress")
    if args.no_caffeinate:
        cli.append("--no-caffeinate")
    elif args.caffeinate_flags != DEFAULT_CAFFEINATE_FLAGS:
        cli.extend(["--caffeinate-flags", args.caffeinate_flags])
    return cli


def _write_job(
    path: Path,
    args: argparse.Namespace,
    *,
    run_dir: Path,
    status: str,
    active_stage: str | None,
    command: list[str] | None = None,
    error: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema_version": "experiment_backend_job_v1",
        "status": status,
        "active_stage": active_stage,
        "updated_at": now_utc(),
        "run_dir": display_path(run_dir),
        "runtime_profile": args.runtime_profile,
        "conditions": _conditions(args.conditions),
        "stages": _stages(args.stages),
        "status_files": {
            "generation": display_path(run_dir / "dialogue_supervisor_status.json"),
            "evaluation": display_path(run_dir / "eval_status.json"),
            "postprocess": display_path(run_dir / "two_person_postprocess_status.json"),
        },
        "artifacts": {
            "responses_by_condition": display_path(run_dir / "responses_by_condition.json"),
            "conversation_log": display_path(run_dir / "conversation_log.json"),
            "run_config": display_path(run_dir / "run_config.json"),
            "llm_judge": display_path(run_dir / "llm_judge_scores_two_person.json"),
            "markdown_report": display_path(run_dir / "two_person_eval_report.md"),
            "html_report": display_path(run_dir / "two_person_eval_report.html"),
            "docs_report_manifest": display_path(run_dir / "final_report_manifest.json"),
            "docs_experiments_root": display_path(args.docs_dir / "experiments"),
            "trajectory_data_dir": display_path(args.data_dir) if args.data_dir else None,
        },
        "policy": {
            "only_runtime_conditions_vary": True,
            "background_first": True,
            "resume_supported_by_generation_supervisor": True,
            "evaluation_waits_for_generation": True,
            "final_reports_grouped_by_experiment_dir": True,
            "final_report_files_include_standard_experiment_name": True,
        },
    }
    if command is not None:
        payload["command"] = command
        payload["command_text"] = shlex.join(command)
    if error:
        payload["error"] = error
    write_json_atomic(path, payload)


def _run_checked(cmd: list[str]) -> None:
    print(shlex.join(cmd), flush=True)
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def _append_path_arg(cmd: list[str], flag: str, value: Path | None) -> None:
    if value is not None:
        cmd.extend([flag, str(value)])


def _stages(value: str) -> list[str]:
    stages = [item.strip() for item in value.split(",") if item.strip()]
    allowed = {"generate", "evaluate"}
    invalid = sorted(set(stages) - allowed)
    if invalid:
        raise ValueError(f"Unsupported stages: {', '.join(invalid)}")
    return stages or ["generate", "evaluate"]


def _conditions(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _default_run_dir(conditions: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    suffix = "_".join(item.lower() for item in _conditions(conditions)) or "conditions"
    return DEFAULT_RUN_ROOT / f"run_{stamp}_{suffix}_backend"


if __name__ == "__main__":
    raise SystemExit(main())
