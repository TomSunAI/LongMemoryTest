#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.evaluation.detail_hit_evaluator import evaluate_files  # noqa: E402
from long_memory_test.experiment_cache import DAILY_SCENE_CARDS_PATH, latest_run_dir  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a rough detail-hit evaluator for memory experiment replies."
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
        help="Path to conversation_log.json.",
    )
    parser.add_argument(
        "--scene-cards",
        type=Path,
        default=DAILY_SCENE_CARDS_PATH,
        help="Path to daily_scene_cards.json.",
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
    args = parser.parse_args()
    if args.conversation_log is None or args.output_json is None or args.output_md is None:
        run_dir = args.run_dir or latest_run_dir()
        args.conversation_log = args.conversation_log or run_dir / "conversation_log.json"
        args.output_json = args.output_json or run_dir / "detail_hit_evaluation.json"
        args.output_md = args.output_md or run_dir / "detail_hit_evaluation.md"
    return args


def main() -> int:
    args = parse_args()
    evaluation = evaluate_files(
        conversation_log_path=args.conversation_log,
        scene_cards_path=args.scene_cards,
        output_json_path=args.output_json,
        output_markdown_path=args.output_md,
    )
    variants = evaluation["summary"]["variants"]
    print("Wrote", args.output_json)
    print("Wrote", args.output_md)
    for variant_name, item in sorted(variants.items()):
        print(
            f"{variant_name}: avg_score={item['average_rough_score']} "
            f"allowed_hit_rate={item['allowed_hit_rate']:.2%} "
            f"forbidden_hits={item['forbidden_hit_count']} "
            f"risky_address={item['risky_address_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
