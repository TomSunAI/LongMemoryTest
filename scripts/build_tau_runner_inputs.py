#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAU_CONTRACT = (
    REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json"
)
DEFAULT_NATURALIZED = (
    REPO_ROOT
    / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/"
    "daily_interaction_naturalized_candidates_deepseek_all440.json"
)
DEFAULT_DAILY_OUTPUT = REPO_ROOT / "long_memory_experiment/cache/tau_runner_daily_messages_full.json"
DEFAULT_PROBE_OUTPUT = REPO_ROOT / "long_memory_experiment/cache/tau_runner_probe_questions_full.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert tau=(z,T,L,I,P) into run_dialogue_conditions input JSON files."
    )
    parser.add_argument("--tau-contract", type=Path, default=DEFAULT_TAU_CONTRACT)
    parser.add_argument("--naturalized-dialogues", type=Path, default=DEFAULT_NATURALIZED)
    parser.add_argument("--daily-output", type=Path, default=DEFAULT_DAILY_OUTPUT)
    parser.add_argument("--probe-output", type=Path, default=DEFAULT_PROBE_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tau_contract = _load_json(args.tau_contract)
    naturalized = _load_naturalized(args.naturalized_dialogues)
    bindings = tau_contract.get("message_bindings", {})
    daily_messages = [
        _daily_message_from_unit(unit, naturalized=naturalized, bindings=bindings)
        for unit in tau_contract.get("I", [])
        if isinstance(unit, dict)
    ]
    probe_questions = [
        _probe_question_from_probe(probe, bindings=bindings)
        for probe in tau_contract.get("P", [])
        if isinstance(probe, dict)
    ]
    daily_messages.sort(key=_message_sort_key)
    probe_questions.sort(key=_probe_sort_key)

    daily_doc = {
        "schema_version": "tau_runner_daily_messages_full_v0.1",
        "source_paths": {
            "tau_contract": _display_path(args.tau_contract),
            "naturalized_dialogues": _display_path(args.naturalized_dialogues),
        },
        "messages": daily_messages,
        "summary": {
            "message_count": len(daily_messages),
            "naturalized_message_count": sum(
                1 for item in daily_messages if item.get("naturalized_dialogue_used")
            ),
        },
    }
    probe_doc = {
        "schema_version": "tau_runner_probe_questions_full_v0.1",
        "source_paths": {
            "tau_contract": _display_path(args.tau_contract),
        },
        "probe_questions": probe_questions,
        "summary": {
            "probe_count": len(probe_questions),
            "read_only_probe_count": sum(1 for item in probe_questions if item.get("read_only")),
        },
    }
    _write_json(args.daily_output, daily_doc)
    _write_json(args.probe_output, probe_doc)
    print(
        "Wrote tau runner inputs: "
        f"{len(daily_messages)} daily messages -> {args.daily_output}; "
        f"{len(probe_questions)} probes -> {args.probe_output}"
    )
    return 0


def _daily_message_from_unit(
    unit: dict[str, Any],
    *,
    naturalized: dict[str, dict[str, Any]],
    bindings: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    unit_id = str(unit.get("interaction_unit_id") or "")
    opening = unit.get("scripted_opening", {})
    if not isinstance(opening, dict):
        opening = {}
    naturalized_item = naturalized.get(unit_id, {})
    naturalized_message = str(naturalized_item.get("opening_user_message") or "").strip()
    canonical_message = str(
        opening.get("user_message")
        or opening.get("canonical_surface_event")
        or unit.get("source_timeline_fields", {}).get("surface_event")
        or ""
    ).strip()
    fallback_message = str(
        opening.get("user_message_zh")
        or opening.get("surface_event_zh")
        or unit.get("source_timeline_fields", {}).get("surface_event_zh")
        or canonical_message
    ).strip()
    event_title = unit.get("event_title", {})
    topic = (
        opening.get("topic")
        or (event_title.get("source") if isinstance(event_title, dict) else None)
        or opening.get("topic_zh")
        or _localized_event_title(unit)
    )
    return {
        "message_id": unit_id,
        "day": unit.get("day"),
        "day_group_id": unit.get("day_group_id"),
        "within_day_index": unit.get("within_day_index", 1),
        "turn_type": opening.get("turn_type") or "scripted_opening",
        "topic": topic,
        "topic_zh": opening.get("topic_zh") or _localized_event_title(unit),
        "user_message": naturalized_message or fallback_message,
        "canonical_user_message": canonical_message,
        "naturalized_dialogue_used": bool(naturalized_message),
        "naturalized_dialogue_id": naturalized_item.get("naturalized_dialogue_id"),
        "persona_id": unit.get("persona_id"),
        "interaction_unit_id": unit_id,
        "event_occurrence_id": unit.get("event_occurrence_id"),
        "event_line_id": unit.get("event_line_id"),
        "event_category_id": unit.get("event_category_id"),
        "event_stage": unit.get("event_stage"),
        "tau": dict(bindings.get(unit_id, {})),
        "source_tau": {
            "source": "tau_contract.I",
            "interaction_unit_id": unit_id,
            "scripted_opening_preserved": True,
        },
    }


def _probe_question_from_probe(
    probe: dict[str, Any],
    *,
    bindings: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    message_id = str(probe.get("message_id") or probe.get("probe_id") or "")
    probe_id = str(probe.get("probe_id") or message_id)
    interaction_unit_id = probe.get("interaction_unit_id")
    tom_assessment = dict(probe.get("tom_assessment", {}))
    diagnostic_dimensions = list(probe.get("diagnostic_dimensions", []))
    return {
        "message_id": message_id,
        "probe_id": probe_id,
        "day": probe.get("day"),
        "day_group_id": probe.get("day_group_id"),
        "within_day_index": probe.get("within_day_index", 1),
        "turn_type": probe.get("turn_type") or "targeted_probe",
        "topic": probe.get("topic") or probe.get("ground_truth", {}).get("event_title_zh", ""),
        "user_message": probe.get("user_message") or probe.get("question"),
        "insert_after_message_id": probe.get("insert_after_message_id") or interaction_unit_id,
        "persona_id": probe.get("persona_id"),
        "interaction_unit_id": interaction_unit_id,
        "event_occurrence_id": probe.get("event_occurrence_id"),
        "event_line_id": probe.get("event_line_id"),
        "event_category_id": probe.get("event_category_id"),
        "event_stage": probe.get("event_stage"),
        "probe_type": probe.get("probe_type"),
        "paper_probe_id": probe.get("paper_probe_id"),
        "primary_dimension_id": probe.get("primary_dimension_id"),
        "evaluation_dimension_ids": list(probe.get("evaluation_dimension_ids", [])),
        "target_detail_ids": list(probe.get("target_detail_ids", [])),
        "read_only": True,
        "writeback_policy": "probe_turn_must_not_write_to_memory",
        "tom_dimensions": diagnostic_dimensions,
        "diagnostic_dimensions": diagnostic_dimensions,
        "tom_assessment": tom_assessment,
        "ground_truth": dict(probe.get("ground_truth", {})),
        "tau": dict(bindings.get(message_id, {})),
        "source_tau": {
            "source": "tau_contract.P",
            "probe_id": probe_id,
        },
    }


def _load_naturalized(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    doc = _load_json(path)
    result: dict[str, dict[str, Any]] = {}
    for item in doc.get("naturalized_dialogues", []):
        if not isinstance(item, dict):
            continue
        unit_id = item.get("source_interaction_unit_id") or item.get("source_message_id")
        if unit_id:
            result[str(unit_id)] = item
    return result


def _message_sort_key(message: dict[str, Any]) -> tuple[str, int, str, int, str]:
    return (
        str(message.get("persona_id") or ""),
        int(message.get("day") or 0),
        str(message.get("day_group_id") or ""),
        int(message.get("within_day_index") or 1),
        str(message.get("message_id") or ""),
    )


def _probe_sort_key(probe: dict[str, Any]) -> tuple[str, int, str, int, str]:
    return (
        str(probe.get("persona_id") or ""),
        int(probe.get("day") or 0),
        str(probe.get("day_group_id") or ""),
        int(probe.get("within_day_index") or 1),
        str(probe.get("message_id") or ""),
    )


def _localized_event_title(item: dict[str, Any]) -> str:
    title = item.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or "")
    return str(title or "")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
