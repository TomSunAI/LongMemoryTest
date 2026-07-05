#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = REPO_ROOT / "long_memory_experiment/outputs/run_20260628_demo5_tau_full_m0_m3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wait for the two-person dialogue generation, then run evaluation reports."
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--personas", default="P0001,P0002")
    parser.add_argument("--poll-seconds", type=float, default=60.0)
    parser.add_argument("--judge-workers", type=int, default=4)
    parser.add_argument("--judge-provider", default="deepseek")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir
    status_path = run_dir / "dialogue_supervisor_status.json"
    _log(f"waiting for generation status: {status_path}")
    while True:
        status = _load_json(status_path)
        state = str(status.get("status", "missing"))
        _log(f"generation status={state}")
        if state == "complete":
            break
        if state == "failed":
            _log("generation failed; postprocess aborted")
            return 1
        time.sleep(max(args.poll_seconds, 1.0))

    responses = run_dir / "responses_by_condition.json"
    conversation = run_dir / "conversation_log_two_person_eval.json"
    automatic_json = run_dir / "automatic_scores_two_person.json"
    automatic_md = run_dir / "automatic_scores_two_person.md"
    llm_json = run_dir / "llm_judge_scores_two_person.json"
    llm_md = run_dir / "llm_judge_scores_two_person.md"

    _run(
        [
            sys.executable,
            "scripts/15_extract_eval_conversation_log.py",
            "--input",
            str(responses),
            "--output",
            str(conversation),
            "--personas",
            args.personas,
        ]
    )
    _run(
        [
            sys.executable,
            "scripts/evaluate_tom_quality.py",
            "--conversation-log",
            str(conversation),
            "--output-json",
            str(automatic_json),
            "--output-md",
            str(automatic_md),
        ]
    )
    _run(
        [
            sys.executable,
            "scripts/evaluate_tom_quality_llm.py",
            "--conversation-log",
            str(conversation),
            "--output-json",
            str(llm_json),
            "--output-md",
            str(llm_md),
            "--provider",
            args.judge_provider,
            "--variants",
            "M0,M1,M2,M3",
            "--judge-workers",
            str(args.judge_workers),
            "--print-progress",
        ]
    )
    _run(
        [
            sys.executable,
            "scripts/16_generate_two_person_eval_report.py",
            "--run-dir",
            str(run_dir),
        ]
    )
    _run(
        [
            sys.executable,
            "scripts/17_generate_two_person_eval_report_html.py",
            "--run-dir",
            str(run_dir),
        ]
    )
    _log("two-person postprocess complete")
    return 0


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> None:
    _log("running: " + " ".join(cmd))
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def _log(message: str) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    print(f"[{now}] {message}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
