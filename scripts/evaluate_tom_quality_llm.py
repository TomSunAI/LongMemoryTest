#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.evaluation.llm_tom_judge import evaluate_files_with_llm_judge  # noqa: E402
from long_memory_test.experiment_cache import latest_run_dir  # noqa: E402
from long_memory_test.llm import create_llm_client, get_llm_config  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the primary LLM-as-judge ToM evaluator for targeted probe replies."
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Run directory under long_memory_experiment/outputs. Defaults to latest run.",
    )
    parser.add_argument(
        "--conversation-log",
        type=Path,
        default=None,
        help="Path to a conversation log containing ToM probe turns.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Output JSON evaluation path.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Output Markdown summary path.",
    )
    parser.add_argument(
        "--provider",
        default="deepseek",
        help="LLM provider from .env.local. Defaults to deepseek for the judge.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of variant answers to judge. Useful for smoke tests.",
    )
    parser.add_argument(
        "--message-id",
        default=None,
        help="Only judge a single probe message id, e.g. D01_P001.",
    )
    parser.add_argument(
        "--variants",
        default=None,
        help="Comma-separated variants to judge, e.g. M0,M1. Defaults to all variants.",
    )
    parser.add_argument(
        "--context-turns",
        type=int,
        default=999,
        help="Number of previous turns from the same variant to include as recent context.",
    )
    parser.add_argument(
        "--max-answer-chars",
        type=int,
        default=6000,
        help="Maximum characters from the judged assistant answer.",
    )
    parser.add_argument(
        "--max-context-answer-chars",
        type=int,
        default=1200,
        help="Maximum characters from each previous assistant answer in context.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=4096,
        help="Maximum output tokens for each judge call.",
    )
    parser.add_argument(
        "--judge-timeout",
        type=float,
        default=120.0,
        help="Per-judge-call timeout in seconds.",
    )
    parser.add_argument(
        "--print-progress",
        action="store_true",
        help="Print one progress line before each judge case.",
    )
    args = parser.parse_args()
    if args.conversation_log is None or args.output_json is None or args.output_md is None:
        run_dir = args.run_dir or latest_run_dir()
        args.conversation_log = args.conversation_log or run_dir / "conversation_log.json"
        args.output_json = args.output_json or run_dir / "llm_judge_scores.json"
        args.output_md = args.output_md or run_dir / "llm_judge_scores.md"
    return args


def main() -> int:
    args = parse_args()
    llm_config = get_llm_config(provider=args.provider)
    client, llm_config = create_llm_client(llm_config)
    variants = (
        [item.strip() for item in args.variants.split(",") if item.strip()]
        if args.variants
        else None
    )
    evaluation = evaluate_files_with_llm_judge(
        conversation_log_path=args.conversation_log,
        output_json_path=args.output_json,
        output_markdown_path=args.output_md,
        client=client,
        llm_config=llm_config,
        limit=args.limit,
        message_id=args.message_id,
        variants=variants,
        context_turns=args.context_turns,
        max_answer_chars=args.max_answer_chars,
        max_context_answer_chars=args.max_context_answer_chars,
        max_output_tokens=args.max_output_tokens,
        timeout_seconds=args.judge_timeout,
        print_progress=args.print_progress,
    )
    print("Wrote", args.output_json)
    print("Wrote", args.output_md)
    for variant_name, item in sorted(evaluation["summary"]["variants"].items()):
        print(
            f"{variant_name}: avg_tom_score={item['average_tom_score']} "
            f"probe_answers={item['turn_count']} "
            f"avg_confidence={item['average_confidence']} "
            f"human_review={item['needs_human_review_count']} "
            f"flags={item['flag_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
