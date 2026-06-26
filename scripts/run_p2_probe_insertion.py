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

from long_memory_test.sampling.probe_constructor import (  # noqa: E402
    ProbeConstructionConfig,
    construct_probe_plan_for_timeline,
)


DEFAULT_P0_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DEFAULT_SAMPLING_CONFIG = REPO_ROOT / "long_memory_experiment/data/sampling/sampling_config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Insert targeted probes into the demo timeline.")
    parser.add_argument("--p0-dir", type=Path, default=DEFAULT_P0_DIR)
    parser.add_argument("--timeline", type=Path, default=None)
    parser.add_argument("--sampling-config", type=Path, default=DEFAULT_SAMPLING_CONFIG)
    parser.add_argument("--probe-output", type=Path, default=None)
    parser.add_argument("--timeline-output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timeline_path = args.timeline or (args.p0_dir / "timeline.json")
    probe_output = args.probe_output or (args.p0_dir / "probe_plan.json")
    timeline_output = args.timeline_output or timeline_path
    payload = construct_probe_plan_for_timeline(
        timeline_batch=_load_json(timeline_path),
        config=_config_from_sampling_config(_load_json(args.sampling_config)),
    )
    _write_json(probe_output, payload["probe_plan"])
    _write_json(timeline_output, payload["timeline_with_probes"])
    summary = payload["probe_plan"]["summary"]
    validation = payload["probe_plan"]["validation"]
    print(
        "P2 probe insertion "
        f"status={validation['status']} "
        f"probes={summary['probe_count']} "
        f"personas={summary['persona_count']} "
        f"per_persona={summary['probes_per_persona_min']}-{summary['probes_per_persona_max']} "
        f"probe_output={probe_output} "
        f"timeline_output={timeline_output}"
    )
    return 0 if validation["status"] == "pass" else 1


def _config_from_sampling_config(data: dict[str, Any]) -> ProbeConstructionConfig:
    probes = _dict_value(data, "probes_per_persona")
    return ProbeConstructionConfig(
        random_seed=int(data.get("random_seed", 20260701)),
        probes_per_persona_min=int(probes.get("min", 12)),
        probes_per_persona_max=int(probes.get("max", 18)),
    )


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


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
