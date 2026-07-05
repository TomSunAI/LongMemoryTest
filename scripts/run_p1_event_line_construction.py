#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.sampling.event_line_constructor import (  # noqa: E402
    EventLineConstructionConfig,
    construct_event_lines_for_persona,
)


DEFAULT_P0_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DEFAULT_EVENT_POOL = (
    REPO_ROOT / "long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "long_memory_experiment/data/generated/json_sourced_instance_p0001"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construct P1 event lines for a sampled persona.")
    parser.add_argument("--persona-id", default="P0001")
    parser.add_argument("--p0-dir", type=Path, default=DEFAULT_P0_DIR)
    parser.add_argument("--event-category-pool", type=Path, default=DEFAULT_EVENT_POOL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = construct_event_lines_for_persona(
        sampled_personas=_load_json(args.p0_dir / "sampled_personas.json"),
        accepted_event_sets=_load_json(args.p0_dir / "accepted_persona_event_sets.json"),
        event_pool=_load_json(args.event_category_pool),
        config=EventLineConstructionConfig(persona_id=args.persona_id),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "event_lines.json"
    _write_json(output, payload)
    print(
        "P1 event line construction "
        f"persona_id={payload['persona_ref']['persona_id']} "
        f"event_lines={payload['event_line_count']} "
        f"output={output}"
    )
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
