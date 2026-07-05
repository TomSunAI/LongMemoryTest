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

from long_memory_test.sampling.persona_event_sampler import (  # noqa: E402
    P0SamplingConfig,
    run_p0_persona_event_sampling,
)


DEFAULT_SAMPLING_CONFIG = REPO_ROOT / "long_memory_experiment/data/sampling/sampling_config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run P0 persona-event sampling and compatibility validation."
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
    parser.add_argument("--sampling-config", type=Path, default=DEFAULT_SAMPLING_CONFIG)
    parser.add_argument("--num-personas", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sampling_config = _load_json(args.sampling_config)
    config = _build_p0_config(
        sampling_config=sampling_config,
        num_personas_override=args.num_personas,
        seed_override=args.seed,
    )
    output_dir = args.output_dir or _default_output_dir(config, sampling_config)
    outputs = run_p0_persona_event_sampling(
        archetype_pool=_load_json(args.persona_archetype_pool),
        event_pool=_load_json(args.event_category_pool),
        config=config,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    file_map = {
        "sampled_personas.json": outputs["sampled_personas"],
        "candidate_event_sets.json": outputs["candidate_event_sets"],
        "accepted_persona_event_sets.json": outputs["accepted_persona_event_sets"],
        "compatibility_report.json": outputs["compatibility_report"],
        "realism_validation_report.json": outputs["realism_validation_report"],
        "sampling_run_manifest.json": _build_manifest(
            sampling_config=sampling_config,
            p0_config=outputs["sampled_personas"]["sampling_config"],
            args=args,
        ),
    }
    for filename, payload in file_map.items():
        _write_json(output_dir / filename, payload)

    report = outputs["compatibility_report"]
    summary = report["summary"]
    print(
        "P0 sampling "
        f"status={report['status']} "
        f"personas={summary['persona_count']} "
        f"candidate_events={summary['candidate_events_total']} "
        f"accepted_events={summary['accepted_events_total']} "
        f"issues={summary['realism_issue_count']} "
        f"warnings={summary['realism_warning_count']} "
        f"output_dir={output_dir}"
    )
    return 0 if report["status"] == "pass" else 1


def _build_p0_config(
    *,
    sampling_config: dict[str, Any],
    num_personas_override: int | None,
    seed_override: int | None,
) -> P0SamplingConfig:
    defaults = P0SamplingConfig()
    events_per_persona = _dict_value(sampling_config, "events_per_persona")
    candidate_events = _dict_value(
        sampling_config,
        "candidate_events_before_validation",
    )
    return P0SamplingConfig(
        random_seed=_int_value(seed_override, sampling_config.get("random_seed"), defaults.random_seed),
        num_personas=_int_value(
            num_personas_override,
            sampling_config.get("num_personas"),
            defaults.num_personas,
        ),
        events_per_persona_min=_int_value(
            None,
            events_per_persona.get("min"),
            defaults.events_per_persona_min,
        ),
        events_per_persona_max=_int_value(
            None,
            events_per_persona.get("max"),
            defaults.events_per_persona_max,
        ),
        candidate_events_min=_int_value(
            None,
            candidate_events.get("min"),
            defaults.candidate_events_min,
        ),
        candidate_events_max=_int_value(
            None,
            candidate_events.get("max"),
            defaults.candidate_events_max,
        ),
        min_event_domains_per_persona=_int_value(
            None,
            sampling_config.get("min_event_domains_per_persona"),
            defaults.min_event_domains_per_persona,
        ),
        max_events_per_domain_per_persona=_int_value(
            None,
            sampling_config.get("max_events_per_domain_per_persona"),
            defaults.max_events_per_domain_per_persona,
        ),
    )


def _default_output_dir(config: P0SamplingConfig, sampling_config: dict[str, Any]) -> Path:
    profile = str(sampling_config.get("profile", "")).strip()
    if profile == "demo_first_phase" and config.num_personas == 5:
        suffix = "demo5"
    else:
        suffix = str(config.num_personas)
    return REPO_ROOT / f"long_memory_experiment/data/generated/p0_persona_event_sampling_{suffix}"


def _build_manifest(
    *,
    sampling_config: dict[str, Any],
    p0_config: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    return {
        "schema_version": "sampling_run_manifest_v0.1",
        "stage": "P0_persona_event_sampling",
        "sampling_config_path": _rel(args.sampling_config),
        "persona_archetype_pool": _rel(args.persona_archetype_pool),
        "event_category_pool": _rel(args.event_category_pool),
        "profile": sampling_config.get("profile"),
        "source_document": sampling_config.get("source_document"),
        "p0_sampling_config": p0_config,
        "scale_status": _scale_status(sampling_config, p0_config),
    }


def _scale_status(sampling_config: dict[str, Any], p0_config: dict[str, Any]) -> str:
    num_personas = int(p0_config.get("num_personas", 0))
    if sampling_config.get("profile") == "demo_first_phase" and num_personas == 5:
        return "canonical_docx_first_phase"
    if num_personas == 20:
        return "docx_main_experiment_expansion"
    if num_personas == 100:
        return "non_canonical_stress_test"
    return "custom_run"


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


def _int_value(override: int | None, configured: Any, default: int) -> int:
    if override is not None:
        return int(override)
    if configured is not None:
        return int(configured)
    return default


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


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
