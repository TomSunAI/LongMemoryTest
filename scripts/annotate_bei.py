#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents.bei_annotator import generate_bei_annotations  # noqa: E402
from long_memory_test.agents.event_stream_generator import load_json, write_json  # noqa: E402
from long_memory_test.experiment_cache import (  # noqa: E402
    BEI_ANNOTATIONS_PATH,
    CACHE_TIMELINE_EVENTS_PATH,
    PROBE_QUESTION_PLAN_PATH,
    update_cache_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate BEI annotations for docx-route ToM probes."
    )
    parser.add_argument(
        "--probe-questions",
        type=Path,
        default=PROBE_QUESTION_PLAN_PATH,
        help="Path to probe_question_plan.json.",
    )
    parser.add_argument(
        "--timeline",
        type=Path,
        default=CACHE_TIMELINE_EVENTS_PATH,
        help="Path to cached event-level timeline.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BEI_ANNOTATIONS_PATH,
        help="Output path for bei_annotations.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    annotations = generate_bei_annotations(
        probe_question_plan=load_json(args.probe_questions),
        timeline=load_json(args.timeline),
    )
    annotations["source_paths"] = {
        "probe_questions": _display_path(args.probe_questions),
        "timeline": _display_path(args.timeline),
    }
    write_json(args.output, annotations)
    update_cache_manifest(
        {
            "event_timeline_cache": args.timeline,
            "probe_question_plan": args.probe_questions,
            "bei_annotations": args.output,
        },
        note="BEI annotations refreshed",
    )
    print(
        f"Wrote {annotations['summary']['annotation_count']} BEI annotations to {args.output}"
    )
    return 0


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
