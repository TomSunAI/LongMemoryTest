#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.evaluation.tom_quality_evaluator import evaluate_files  # noqa: E402
from long_memory_test.experiment_cache import latest_run_dir  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write automatic ToM scores for a run.")
    parser.add_argument("--run-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir or latest_run_dir()
    evaluation = evaluate_files(
        conversation_log_path=run_dir / "conversation_log.json",
        output_json_path=run_dir / "automatic_scores.json",
        output_markdown_path=run_dir / "automatic_scores.md",
    )
    print(f"Wrote {run_dir / 'automatic_scores.json'}")
    for variant_name, item in sorted(evaluation["summary"]["variants"].items()):
        print(f"{variant_name}: avg_tom_score={item['average_tom_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
