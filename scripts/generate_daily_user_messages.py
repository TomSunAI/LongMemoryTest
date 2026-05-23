#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents.daily_message_generator import (  # noqa: E402
    DailyMessageConfig,
    generate_daily_user_messages,
)
from long_memory_test.agents.event_stream_generator import write_json  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate daily natural-language user messages from timeline.json."
    )
    parser.add_argument(
        "--timeline",
        type=Path,
        default=REPO_ROOT / "sample_output/timeline.json",
        help="Path to timeline.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "sample_output/daily_user_message.json",
        help="Output path for daily_user_message.json.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=142,
        help="Random seed for reproducible phrasing diversity.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_daily_user_messages(
        DailyMessageConfig(timeline_path=args.timeline, seed=args.seed)
    )
    write_json(args.output, result)
    print(f"Wrote {len(result['messages'])} daily messages to {args.output}")


if __name__ == "__main__":
    main()
