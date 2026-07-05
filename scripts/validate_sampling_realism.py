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

from long_memory_test.sampling.realism_validator import (  # noqa: E402
    build_realism_validation_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate persona/event sampling pools and optional sampled assignments."
    )
    parser.add_argument(
        "--persona-archetype-pool",
        type=Path,
        default=(
            REPO_ROOT
            / "long_memory_experiment/data/sampling/persona_archetype_pool_v0.1.json"
        ),
    )
    parser.add_argument(
        "--event-category-pool",
        type=Path,
        default=(
            REPO_ROOT
            / "long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json"
        ),
    )
    parser.add_argument("--sampled-personas", type=Path, default=None)
    parser.add_argument("--accepted-event-sets", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            REPO_ROOT
            / "long_memory_experiment/data/generated/realism_validation_report.json"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archetype_pool = _load_json(args.persona_archetype_pool)
    event_pool = _load_json(args.event_category_pool)
    sampled_personas = _load_json(args.sampled_personas) if args.sampled_personas else None
    accepted_event_sets = _load_json(args.accepted_event_sets) if args.accepted_event_sets else None
    report = build_realism_validation_report(
        archetype_pool=archetype_pool,
        event_pool=event_pool,
        sampled_personas=sampled_personas,
        accepted_event_sets=accepted_event_sets,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "realism validation "
        f"status={report['status']} issues={len(report['issues'])} "
        f"warnings={len(report['warnings'])} output={args.output}"
    )
    return 0 if report["status"] == "pass" else 1


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
