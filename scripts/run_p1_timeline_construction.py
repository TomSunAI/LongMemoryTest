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

from long_memory_test.sampling.timeline_constructor import (  # noqa: E402
    TimelineConstructionConfig,
    construct_timeline_for_batch,
)


DEFAULT_P0_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DEFAULT_SAMPLING_CONFIG = REPO_ROOT / "long_memory_experiment/data/sampling/sampling_config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construct 30-day P1 timelines for demo personas.")
    parser.add_argument("--p0-dir", type=Path, default=DEFAULT_P0_DIR)
    parser.add_argument("--event-lines-batch", type=Path, default=None)
    parser.add_argument("--sampling-config", type=Path, default=DEFAULT_SAMPLING_CONFIG)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    event_lines_batch_path = args.event_lines_batch or (args.p0_dir / "event_lines_batch.json")
    output = args.output or (args.p0_dir / "timeline.json")
    sampling_config = _load_json(args.sampling_config)
    payload = construct_timeline_for_batch(
        event_lines_batch=_load_json(event_lines_batch_path),
        config=_config_from_sampling_config(sampling_config),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output, payload)
    summary = payload["summary"]
    validation = payload["validation"]
    print(
        "P1 timeline construction "
        f"status={validation['status']} "
        f"personas={summary['persona_count']} "
        f"event_lines={summary['event_line_count']} "
        f"active_sessions={summary['active_session_total']} "
        f"output={output}"
    )
    return 0 if validation["status"] == "pass" else 1


def _config_from_sampling_config(data: dict[str, Any]) -> TimelineConstructionConfig:
    active = _dict_value(data, "active_sessions_per_persona")
    occurrences = _dict_value(data, "event_line_occurrences")
    return TimelineConstructionConfig(
        random_seed=int(data.get("random_seed", 20260701)),
        timeline_days=int(data.get("timeline_days", 30)),
        active_sessions_min=int(active.get("min", 15)),
        active_sessions_max=int(active.get("max", 20)),
        event_line_occurrences_min=int(occurrences.get("min", 3)),
        event_line_occurrences_max=int(occurrences.get("max", 6)),
        max_events_per_active_day=int(data.get("max_events_per_active_day", 2)),
        parallel_event_days_min=int(data.get("parallel_event_days_min", 2)),
        probe_candidate_min_per_persona=int(data.get("probe_candidate_min_per_persona", 14)),
        daily_event_count_distribution=_daily_event_count_distribution(
            data.get("daily_event_count_distribution")
        ),
        daily_event_count_median_target=_optional_float(
            data.get("daily_event_count_median_target")
        ),
        allow_stage_reuse_after_sequence=bool(
            data.get("allow_stage_reuse_after_sequence", False)
        ),
    )


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


def _daily_event_count_distribution(value: Any) -> dict[int, int] | None:
    if value in (None, "", {}):
        return None
    if not isinstance(value, dict):
        raise ValueError("daily_event_count_distribution must be an object.")
    return {int(key): int(count) for key, count in value.items()}


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


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
