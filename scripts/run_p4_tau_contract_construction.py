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

from long_memory_test.sampling.tau_contract_constructor import (  # noqa: E402
    construct_tau_contract_for_batch,
)


DEFAULT_P0_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construct the demo5 tau=(z,T,L,I,P) contract."
    )
    parser.add_argument("--p0-dir", type=Path, default=DEFAULT_P0_DIR)
    parser.add_argument("--timeline", type=Path, default=None)
    parser.add_argument("--daily-interactions", type=Path, default=None)
    parser.add_argument("--probe-plan", type=Path, default=None)
    parser.add_argument("--sampled-personas", type=Path, default=None)
    parser.add_argument("--event-lines-batch", type=Path, default=None)
    parser.add_argument("--accepted-event-sets", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timeline_path = args.timeline or (args.p0_dir / "timeline.json")
    daily_path = args.daily_interactions or (args.p0_dir / "daily_interaction_units.json")
    probe_path = args.probe_plan or (args.p0_dir / "probe_plan.json")
    sampled_path = args.sampled_personas or (args.p0_dir / "sampled_personas.json")
    event_lines_path = args.event_lines_batch or (args.p0_dir / "event_lines_batch.json")
    accepted_path = args.accepted_event_sets or (args.p0_dir / "accepted_persona_event_sets.json")
    output = args.output or (args.p0_dir / "tau_contract.json")

    contract = construct_tau_contract_for_batch(
        timeline_batch=_load_json(timeline_path),
        daily_interactions=_load_json(daily_path),
        probe_plan=_load_json(probe_path),
        sampled_personas=_load_optional_json(sampled_path),
        event_lines_batch=_load_optional_json(event_lines_path),
        accepted_event_sets=_load_optional_json(accepted_path),
        source_paths={
            "timeline": _display_path(timeline_path),
            "daily_interaction_units": _display_path(daily_path),
            "probe_plan": _display_path(probe_path),
            "sampled_personas": _display_path(sampled_path) if sampled_path.exists() else None,
            "event_lines_batch": _display_path(event_lines_path) if event_lines_path.exists() else None,
            "accepted_event_sets": _display_path(accepted_path) if accepted_path.exists() else None,
        },
    )
    _write_json(output, contract)
    summary = contract["summary"]
    validation = contract["validation"]
    print(
        "P4 tau contract construction "
        f"status={validation['status']} "
        f"personas={summary['persona_count']} "
        f"themes={summary['theme_count']} "
        f"event_lines={summary['event_line_count']} "
        f"interaction_units={summary['interaction_unit_count']} "
        f"probes={summary['targeted_probe_count']} "
        f"bindings={summary['message_binding_count']} "
        f"output={output}"
    )
    return 0 if validation["status"] == "pass" else 1


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
