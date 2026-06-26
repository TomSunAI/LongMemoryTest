#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.llm import create_llm_client, get_llm_config  # noqa: E402
from long_memory_test.sampling.interaction_naturalizer import (  # noqa: E402
    InteractionNaturalizationConfig,
    naturalize_interaction_unit,
)


DEFAULT_P0_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "P3b: generate non-destructive naturalized dialogue candidates from "
            "existing daily interaction units."
        )
    )
    parser.add_argument(
        "--daily-interactions",
        type=Path,
        default=DEFAULT_P0_DIR / "daily_interaction_units.json",
    )
    parser.add_argument(
        "--probe-plan",
        type=Path,
        default=DEFAULT_P0_DIR / "probe_plan.json",
        help="Optional probe_plan.json; bound probes guide follow-up generation only.",
    )
    parser.add_argument(
        "--no-probe-plan",
        action="store_true",
        help="Disable probe-aware follow-up guidance.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_P0_DIR / "daily_interaction_naturalized_candidates.json",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Naturalize every interaction unit; overrides --limit.",
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse existing candidates in --output and only run missing interaction units.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="When --resume is set, reuse only existing pass candidates and rerun failed ones.",
    )
    parser.add_argument(
        "--force-probed",
        action="store_true",
        help="With --resume, rerun units that have bound probes even if an existing candidate is present.",
    )
    parser.add_argument(
        "--only-probed",
        action="store_true",
        help="Only naturalize units that have bound probes in --probe-plan.",
    )
    parser.add_argument("--checkpoint-every", type=int, default=1)
    parser.add_argument(
        "--one-per-persona",
        action="store_true",
        help="Select the first active interaction unit for each persona before applying --limit.",
    )
    parser.add_argument("--provider", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-tokens", type=int, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    daily = _load_json(args.daily_interactions)
    probe_plan = (
        {}
        if args.no_probe_plan or not args.probe_plan or not args.probe_plan.exists()
        else _load_json(args.probe_plan)
    )
    probes_by_message = _probes_by_message(probe_plan)
    units = _selected_units(
        daily=daily,
        limit=None if args.all else max(0, int(args.limit)),
        one_per_persona=bool(args.one_per_persona),
    )
    if args.only_probed:
        units = [
            unit
            for unit in units
            if str(unit.get("interaction_unit_id") or "") in probes_by_message
        ]
    if args.dry_run:
        print(
            "Dry run only. "
            f"Would naturalize {len(units)} interaction units from {args.daily_interactions}."
        )
        return 0

    llm_config = get_llm_config(args.provider)
    _, llm_config = create_llm_client(llm_config)
    config = InteractionNaturalizationConfig(
        timeout_seconds=args.timeout,
        max_tokens=max(1, int(args.max_tokens)),
    )

    existing = _existing_candidates(args.output, pass_only=bool(args.retry_failed)) if args.resume else {}
    pending_units = []
    for unit in units:
        unit_id = str(unit.get("interaction_unit_id") or "")
        has_bound_probe = unit_id in probes_by_message
        if unit_id not in existing or (args.force_probed and has_bound_probe):
            pending_units.append(unit)
            if args.force_probed and has_bound_probe:
                existing.pop(unit_id, None)
    candidates_by_id = dict(existing)
    started = time.time()
    print(
        "P3b full naturalization "
        f"provider={llm_config.provider} model={llm_config.model} "
        f"total={len(units)} resume_existing={len(existing)} "
        f"pending={len(pending_units)} bound_probe_units={len(probes_by_message)} "
        f"workers={max(1, int(args.workers))} "
        f"output={args.output}",
        flush=True,
    )

    completed_since_checkpoint = 0
    if pending_units:
        with ThreadPoolExecutor(max_workers=max(1, int(args.workers))) as executor:
            futures = {
                executor.submit(
                    _naturalize_one,
                    unit=unit,
                    llm_config=llm_config,
                    bound_probes=probes_by_message.get(str(unit.get("interaction_unit_id") or ""), []),
                    config=config,
                ): unit
                for unit in pending_units
            }
            for index, future in enumerate(as_completed(futures), start=1):
                unit = futures[future]
                unit_id = str(unit.get("interaction_unit_id") or "")
                try:
                    candidate = future.result()
                except Exception as exc:  # keep the batch running and make failure auditable.
                    candidate = _failed_candidate(
                        unit=unit,
                        exc=exc,
                        bound_probes=probes_by_message.get(unit_id, []),
                        config=config,
                    )
                candidates_by_id[unit_id] = candidate
                status = candidate.get("validation", {}).get("status")
                completed_since_checkpoint += 1
                elapsed = time.time() - started
                print(
                    f"[{len(existing) + index}/{len(units)}] {unit_id} status={status} elapsed={elapsed:.1f}s",
                    flush=True,
                )
                if completed_since_checkpoint >= max(1, int(args.checkpoint_every)):
                    _write_output(
                        output_path=args.output,
                        daily_interactions_path=args.daily_interactions,
                        probe_plan_path=None if args.no_probe_plan else args.probe_plan,
                        llm_provider=llm_config.provider,
                        llm_model=llm_config.model,
                        units=units,
                        candidates_by_id=candidates_by_id,
                        completed=False,
                    )
                    completed_since_checkpoint = 0

    _write_output(
        output_path=args.output,
        daily_interactions_path=args.daily_interactions,
        probe_plan_path=None if args.no_probe_plan else args.probe_plan,
        llm_provider=llm_config.provider,
        llm_model=llm_config.model,
        units=units,
        candidates_by_id=candidates_by_id,
        completed=True,
    )
    pass_count = sum(
        1
        for item in candidates_by_id.values()
        if item.get("validation", {}).get("status") == "pass"
    )
    print(
        f"Wrote {len(candidates_by_id)} naturalized candidates "
        f"pass={pass_count} fail={len(candidates_by_id) - pass_count} to {args.output}"
    )
    return 0


def _selected_units(
    *,
    daily: dict[str, Any],
    limit: int | None,
    one_per_persona: bool,
) -> list[dict[str, Any]]:
    if one_per_persona:
        units = _one_unit_per_persona(daily)
    else:
        units = _interaction_units(daily)
    return units if limit is None else units[:limit]


def _naturalize_one(
    *,
    unit: dict[str, Any],
    llm_config: Any,
    bound_probes: list[dict[str, Any]],
    config: InteractionNaturalizationConfig,
) -> dict[str, Any]:
    client, _ = create_llm_client(llm_config)
    return naturalize_interaction_unit(
        interaction_unit=unit,
        client=client,
        model=llm_config.model,
        bound_probes=bound_probes,
        config=config,
    )


def _failed_candidate(
    *,
    unit: dict[str, Any],
    exc: Exception,
    bound_probes: list[dict[str, Any]],
    config: InteractionNaturalizationConfig,
) -> dict[str, Any]:
    unit_id = str(unit.get("interaction_unit_id") or "")
    opening = unit.get("scripted_opening", {}) if isinstance(unit.get("scripted_opening"), dict) else {}
    return {
        "schema_version": "interaction_naturalization_v0.1",
        "naturalized_dialogue_id": f"{unit_id}_NAT001",
        "source_interaction_unit_id": unit_id,
        "source_message_id": opening.get("message_id") or unit_id,
        "llm_generated": False,
        "canonical_opening_user_message": opening.get("user_message"),
        "opening_user_message": "",
        "followup_user_messages": [],
        "fact_ids_used": [],
        "bound_probe_ids": [
            str(probe.get("probe_id")) for probe in bound_probes if probe.get("probe_id")
        ],
        "bound_probe_refs": [
            {
                "probe_id": probe.get("probe_id"),
                "paper_probe_id": probe.get("paper_probe_id"),
                "primary_dimension_id": probe.get("primary_dimension_id"),
                "question": probe.get("question") or probe.get("user_message"),
            }
            for probe in bound_probes
        ],
        "notes": f"P3b naturalization failed: {type(exc).__name__}: {exc}",
        "raw_output": "",
        "construction_config": {
            "max_followups": config.max_followups,
            "max_allowed_facts": config.max_allowed_facts,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "timeout_seconds": config.timeout_seconds,
            "json_response_format": config.json_response_format,
            "retry_on_invalid_json": config.retry_on_invalid_json,
        },
        "non_destructive_policy": {
            "canonical_i_unit_preserved": True,
            "naturalized_text_is_candidate_only": True,
            "must_not_overwrite_scripted_opening": True,
        },
        "validation": {
            "status": "fail",
            "issues": [f"{type(exc).__name__}: {exc}"],
            "allowed_fact_id_count": 0,
        },
    }


def _existing_candidates(path: Path, *, pass_only: bool) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = _load_json(path)
    candidates = {}
    for item in data.get("naturalized_dialogues", []):
        if not isinstance(item, dict):
            continue
        unit_id = str(item.get("source_interaction_unit_id") or "")
        if unit_id:
            if pass_only and item.get("validation", {}).get("status") != "pass":
                continue
            candidates[unit_id] = item
    return candidates


def _write_output(
    *,
    output_path: Path,
    daily_interactions_path: Path,
    probe_plan_path: Path | None,
    llm_provider: str,
    llm_model: str,
    units: list[dict[str, Any]],
    candidates_by_id: dict[str, dict[str, Any]],
    completed: bool,
) -> None:
    ordered_candidates = [
        candidates_by_id[str(unit.get("interaction_unit_id") or "")]
        for unit in units
        if str(unit.get("interaction_unit_id") or "") in candidates_by_id
    ]
    output = {
        "schema_version": "interaction_naturalization_batch_v0.1",
        "source_daily_interactions": _display_path(daily_interactions_path),
        "source_probe_plan": _display_path(probe_plan_path) if probe_plan_path else None,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "construction_scope": {
            "from_daily_interaction_units": True,
            "probe_aware_followup_generation": probe_plan_path is not None,
            "probe_guidance_applies_to_followups_only": True,
            "canonical_i_units_preserved": True,
            "naturalized_text_is_candidate_only": True,
            "completed": completed,
        },
        "naturalized_dialogues": ordered_candidates,
        "summary": {
            "target_count": len(units),
            "candidate_count": len(ordered_candidates),
            "pass_count": sum(
                1
                for item in ordered_candidates
                if item.get("validation", {}).get("status") == "pass"
            ),
            "fail_count": sum(
                1
                for item in ordered_candidates
                if item.get("validation", {}).get("status") == "fail"
            ),
            "bound_probe_candidate_count": sum(
                1 for item in ordered_candidates if item.get("bound_probe_ids")
            ),
        },
    }
    _write_json(output_path, output)


def _one_unit_per_persona(daily: dict[str, Any]) -> list[dict[str, Any]]:
    units = []
    for persona in daily.get("personas", []):
        if not isinstance(persona, dict):
            continue
        for day in persona.get("days", []):
            if not isinstance(day, dict):
                continue
            day_units = [unit for unit in day.get("interaction_units", []) if isinstance(unit, dict)]
            if day_units:
                units.append(day_units[0])
                break
    return units


def _interaction_units(daily: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        unit
        for persona in daily.get("personas", [])
        if isinstance(persona, dict)
        for day in persona.get("days", [])
        if isinstance(day, dict)
        for unit in day.get("interaction_units", [])
        if isinstance(unit, dict)
    ]


def _probes_by_message(probe_plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for probe in probe_plan.get("probe_questions", []):
        if not isinstance(probe, dict):
            continue
        unit_id = str(probe.get("insert_after_message_id") or "")
        if not unit_id:
            continue
        result.setdefault(unit_id, []).append(probe)
    return result


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
