#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents.event_stream_generator import (  # noqa: E402
    DEFAULT_TIMELINE_DAYS,
    GeneratorConfig,
    generate_timeline,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic user life-event timeline."
    )
    parser.add_argument(
        "--persona",
        type=Path,
        default=REPO_ROOT / "data/config/persona.json",
        help="Path to persona.json.",
    )
    parser.add_argument(
        "--life-domains",
        type=Path,
        default=REPO_ROOT / "data/config/life_domains.json",
        help="Path to life_domains.json.",
    )
    parser.add_argument(
        "--event-templates",
        type=Path,
        default=REPO_ROOT / "data/config/event_templates.json",
        help="Path to event_templates.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "sample_output/timeline.json",
        help="Output path for timeline.json.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_TIMELINE_DAYS,
        help="Number of simulated days.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = GeneratorConfig(
        persona_path=args.persona,
        life_domains_path=args.life_domains,
        event_templates_path=args.event_templates,
        timeline_days=args.days,
        seed=args.seed,
    )
    timeline = generate_timeline(config)
    write_json(args.output, timeline)
    print(f"Wrote {len(timeline['events'])} events to {args.output}")


if __name__ == "__main__":
    main()
