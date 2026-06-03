#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
DEFAULT_RUN_ROOT = REPO_ROOT / "long_memory_experiment/outputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full event-first long-memory experiment: optional data rebuild, "
            "M0/M1/M2/M3 dialogue generation, rule triage, LLM judge, and final report."
        )
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Run directory. Defaults to long_memory_experiment/outputs/run_YYYYMMDD_HHMM_full.",
    )
    parser.add_argument(
        "--rebuild-data",
        action="store_true",
        help="Rebuild timeline, probe plan, BEI annotations, and memory conditions before running.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an existing run-dir. Dialogue generation skips completed message ids.",
    )
    parser.add_argument(
        "--message-ids",
        default=None,
        help="Optional comma-separated opening message ids. Omit to run all 30 days.",
    )
    parser.add_argument("--scene-followups", type=int, default=1)
    parser.add_argument("--conditions", default="M0,M1,M2,M3")
    parser.add_argument("--m0-letta-agent-id", default=os.getenv("LETTA_M0_AGENT_ID"))
    parser.add_argument("--m0-letta-search-limit", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--llm-timeout", type=float, default=600.0)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--judge-provider", default="deepseek")
    parser.add_argument("--judge-timeout", type=float, default=600.0)
    parser.add_argument("--judge-max-output-tokens", type=int, default=4096)
    parser.add_argument(
        "--judge-limit",
        type=int,
        default=None,
        help="Limit LLM judge cases for smoke runs. Omit for full judge.",
    )
    parser.add_argument("--review-limit", type=int, default=24)
    parser.add_argument("--skip-dialogue", action="store_true")
    parser.add_argument("--skip-automatic", action="store_true")
    parser.add_argument("--skip-judge", action="store_true")
    parser.add_argument("--skip-report", action="store_true")
    parser.add_argument("--print-mode", choices=["summary", "all"], default="summary")
    parser.add_argument("--no-progress", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir or _default_run_dir()
    env = dict(os.environ)
    env["PYTHONPATH"] = _pythonpath(env)

    if args.rebuild_data:
        _run_stage(
            ["scripts/01_build_timeline.py"],
            env=env,
            label="rebuild timeline/messages/scene cards",
        )
        _run_stage(
            ["scripts/03_generate_probe_plan.py"],
            env=env,
            label="generate probe plan",
        )
        _run_stage(
            ["scripts/02_annotate_bei.py"],
            env=env,
            label="annotate BEI",
        )
        _run_stage(
            ["scripts/04_build_memory_conditions.py"],
            env=env,
            label="build memory conditions",
        )

    if not args.skip_dialogue:
        dialogue_cmd = [
            "scripts/05_run_dialogue_conditions.py",
            "--run-dir",
            str(run_dir),
            "--scene-followups",
            str(args.scene_followups),
            "--conditions",
            args.conditions,
            "--m0-letta-search-limit",
            str(args.m0_letta_search_limit),
            "--llm-timeout",
            str(args.llm_timeout),
            "--temperature",
            str(args.temperature),
            "--top-p",
            str(args.top_p),
            "--max-tokens",
            str(args.max_tokens),
            "--print-mode",
            args.print_mode,
        ]
        if args.message_ids:
            dialogue_cmd.extend(["--message-ids", args.message_ids])
        else:
            dialogue_cmd.append("--all-message-ids")
        if args.m0_letta_agent_id:
            dialogue_cmd.extend(["--m0-letta-agent-id", args.m0_letta_agent_id])
        if args.resume:
            dialogue_cmd.append("--resume")
        else:
            dialogue_cmd.append("--reset-conversation-log")
        if not args.no_progress:
            dialogue_cmd.append("--print-progress")
        _run_stage(dialogue_cmd, env=env, label="run dialogue conditions")

    if not args.skip_automatic:
        _run_stage(
            ["scripts/06_evaluate_tom.py", "--run-dir", str(run_dir)],
            env=env,
            label="rule triage scoring",
        )

    if not args.skip_judge:
        judge_cmd = [
            "scripts/07_judge_review.py",
            "--run-dir",
            str(run_dir),
            "--provider",
            args.judge_provider,
            "--judge-timeout",
            str(args.judge_timeout),
            "--max-output-tokens",
            str(args.judge_max_output_tokens),
        ]
        if args.judge_limit is not None:
            judge_cmd.extend(["--limit", str(args.judge_limit)])
        if not args.no_progress:
            judge_cmd.append("--print-progress")
        _run_stage(judge_cmd, env=env, label="LLM-as-judge scoring")

    if not args.skip_report:
        _run_stage(
            [
                "scripts/08_report_results.py",
                "--run-dir",
                str(run_dir),
                "--review-limit",
                str(args.review_limit),
            ],
            env=env,
            label="report and human review sample",
        )

    print(f"\nFull experiment finished: {run_dir}")
    return 0


def _default_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return DEFAULT_RUN_ROOT / f"run_{stamp}_full"


def _pythonpath(env: dict[str, str]) -> str:
    existing = env.get("PYTHONPATH")
    if existing:
        return f"{SRC_ROOT}{os.pathsep}{existing}"
    return str(SRC_ROOT)


def _run_stage(cmd: list[str], *, env: dict[str, str], label: str) -> None:
    full_cmd = [sys.executable, *cmd]
    print(f"\n==> {label}")
    print(" ".join(str(part) for part in full_cmd), flush=True)
    subprocess.run(full_cmd, cwd=REPO_ROOT, env=env, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
