#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.evaluation.llm_tom_judge import (  # noqa: E402
    LLMJudgeError,
    evaluate_files_with_llm_judge,
    preflight_llm_judge,
    summarize_llm_diagnostic,
)
from long_memory_test.experiment_cache import latest_run_dir  # noqa: E402
from long_memory_test.llm import create_llm_client, get_llm_config  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM-as-judge review for a run.")
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--variants", default=None)
    parser.add_argument("--judge-timeout", type=float, default=120.0)
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument(
        "--judge-workers",
        type=int,
        default=1,
        help="Number of parallel LLM judge requests. Use 1 for serial scoring.",
    )
    parser.add_argument("--print-progress", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--allow-partial-judge-failures", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir or latest_run_dir()
    llm_config = get_llm_config(provider=args.provider)
    client, llm_config = create_llm_client(llm_config)
    if not args.skip_preflight:
        try:
            preflight_llm_judge(
                client=client,
                llm_config=llm_config,
                timeout_seconds=min(args.judge_timeout, 30.0),
            )
        except LLMJudgeError as exc:
            print("LLM judge preflight failed.", file=sys.stderr)
            print(summarize_llm_diagnostic(exc.diagnostic), file=sys.stderr)
            return 1
    variants = (
        [item.strip() for item in args.variants.split(",") if item.strip()]
        if args.variants
        else None
    )
    try:
        evaluation = evaluate_files_with_llm_judge(
            conversation_log_path=run_dir / "conversation_log.json",
            output_json_path=run_dir / "llm_judge_scores.json",
            output_markdown_path=run_dir / "llm_judge_scores.md",
            client=client,
            llm_config=llm_config,
            limit=args.limit,
            variants=variants,
            max_output_tokens=args.max_output_tokens,
            timeout_seconds=args.judge_timeout,
            judge_workers=args.judge_workers,
            print_progress=args.print_progress,
            allow_partial_failures=args.allow_partial_judge_failures,
        )
    except LLMJudgeError as exc:
        print("LLM judge failed; no score file was written.", file=sys.stderr)
        print(summarize_llm_diagnostic(exc.diagnostic), file=sys.stderr)
        return 1
    print(f"Wrote {run_dir / 'llm_judge_scores.json'}")
    for variant_name, item in sorted(evaluation["summary"]["variants"].items()):
        print(f"{variant_name}: avg_tom_score={item['average_tom_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
