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

from long_memory_test.sampling.daily_interaction_constructor import (  # noqa: E402
    DailyInteractionConstructionConfig,
    construct_daily_interactions_for_timeline,
)


DEFAULT_P0_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DEFAULT_SAMPLING_CONFIG = REPO_ROOT / "long_memory_experiment/data/sampling/sampling_config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construct P3 daily interaction units from the demo timeline."
    )
    parser.add_argument("--p0-dir", type=Path, default=DEFAULT_P0_DIR)
    parser.add_argument("--timeline", type=Path, default=None)
    parser.add_argument("--sampling-config", type=Path, default=DEFAULT_SAMPLING_CONFIG)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timeline_path = args.timeline or (args.p0_dir / "timeline.json")
    output = args.output or (args.p0_dir / "daily_interaction_units.json")
    payload = construct_daily_interactions_for_timeline(
        timeline_batch=_load_json(timeline_path),
        config=_config_from_sampling_config(_load_json(args.sampling_config)),
    )
    _write_json(output, payload)
    summary = payload["summary"]
    validation = payload["validation"]
    print(
        "P3 daily interaction construction "
        f"status={validation['status']} "
        f"personas={summary['persona_count']} "
        f"calendar_days={summary['calendar_day_count']} "
        f"active_days={summary['active_day_total']} "
        f"interaction_units={summary['interaction_unit_count']} "
        f"parallel_days={summary['parallel_day_total']} "
        f"probe_links={summary['probe_link_count']} "
        f"output={output}"
    )
    return 0 if validation["status"] == "pass" else 1


def _config_from_sampling_config(data: dict[str, Any]) -> DailyInteractionConstructionConfig:
    return DailyInteractionConstructionConfig(
        random_seed=int(data.get("random_seed", 20260701)),
        followup_budget_default=int(data.get("followup_budget_default", 2)),
        cross_occurrence_reference_allowed=bool(
            data.get("cross_occurrence_reference_allowed", False)
        ),
        include_inactive_days=bool(data.get("include_inactive_days", True)),
    )


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
