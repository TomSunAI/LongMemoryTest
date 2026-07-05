from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_tau_dialogue_documents(
    *,
    tau_contract: dict[str, Any],
    naturalized_dialogues: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert a tau contract into runner-style message/probe documents.

    This is an adapter only. It does not generate new dialogue content and it
    does not mutate the tau contract. If a separate naturalization artifact is
    supplied, its candidate text may be selected while preserving the canonical
    interaction unit reference.
    """

    naturalized_by_unit = _naturalized_by_unit_id(naturalized_dialogues or {})
    bindings = {
        str(message_id): dict(binding)
        for message_id, binding in tau_contract.get("message_bindings", {}).items()
        if isinstance(binding, dict)
    }
    messages = [
        _message_from_interaction_unit(
            unit=unit,
            binding=bindings.get(str(unit.get("interaction_unit_id")), {}),
            naturalized=naturalized_by_unit.get(str(unit.get("interaction_unit_id")), {}),
        )
        for unit in tau_contract.get("I", [])
        if isinstance(unit, dict) and unit.get("interaction_unit_id")
    ]
    probes = [
        _message_from_probe(probe=probe, binding=bindings.get(str(probe.get("message_id")), {}))
        for probe in tau_contract.get("P", [])
        if isinstance(probe, dict) and probe.get("message_id")
    ]
    messages.sort(key=_message_sort_key)
    probes.sort(key=_message_sort_key)
    probes_by_insert_after: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for probe in probes:
        probes_by_insert_after[str(probe.get("insert_after_message_id", ""))].append(probe)
    return {
        "schema_version": "tau_dialogue_documents_v0.1",
        "source": {
            "schema_version": tau_contract.get("schema_version"),
            "notation": tau_contract.get("notation"),
            "adapter_role": "tau_contract_to_runner_input_without_generation",
            "naturalized_dialogue_used": bool(naturalized_by_unit),
        },
        "messages": messages,
        "probe_questions": probes,
        "probe_questions_by_insert_after": dict(probes_by_insert_after),
        "summary": {
            "message_count": len(messages),
            "probe_count": len(probes),
            "tau_message_binding_count": len(bindings),
            "naturalized_message_count": sum(
                1 for message in messages if message.get("naturalized_dialogue_used")
            ),
        },
    }


def _message_from_interaction_unit(
    *,
    unit: dict[str, Any],
    binding: dict[str, Any],
    naturalized: dict[str, Any],
) -> dict[str, Any]:
    opening = unit.get("scripted_opening", {})
    if not isinstance(opening, dict):
        opening = {}
    canonical_user_message = str(opening.get("user_message") or "")
    naturalized_message = str(naturalized.get("opening_user_message") or "").strip()
    use_naturalized = bool(naturalized_message)
    message_id = str(unit.get("interaction_unit_id"))
    return {
        "message_id": message_id,
        "day": unit.get("day"),
        "day_group_id": unit.get("day_group_id"),
        "within_day_index": unit.get("within_day_index", 1),
        "turn_type": opening.get("turn_type") or "scripted_opening",
        "topic": opening.get("topic") or _event_title(unit),
        "user_message": naturalized_message if use_naturalized else canonical_user_message,
        "canonical_user_message": canonical_user_message,
        "naturalized_dialogue_used": use_naturalized,
        "naturalized_dialogue_id": naturalized.get("naturalized_dialogue_id"),
        "persona_id": unit.get("persona_id"),
        "interaction_unit_id": message_id,
        "event_occurrence_id": unit.get("event_occurrence_id"),
        "event_line_id": unit.get("event_line_id"),
        "event_category_id": unit.get("event_category_id"),
        "event_stage": unit.get("event_stage"),
        "tau": dict(binding),
        "source_tau": {
            "source": "tau_contract.I",
            "interaction_unit_id": message_id,
            "scripted_opening_preserved": True,
        },
    }


def _message_from_probe(*, probe: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    message_id = str(probe.get("message_id") or probe.get("probe_id"))
    return {
        "message_id": message_id,
        "probe_id": probe.get("probe_id") or message_id,
        "day": probe.get("day"),
        "day_group_id": probe.get("day_group_id"),
        "within_day_index": probe.get("within_day_index", 1),
        "turn_type": "targeted_probe",
        "topic": probe.get("topic") or _event_title(probe),
        "user_message": probe.get("question") or probe.get("user_message"),
        "insert_after_message_id": probe.get("insert_after_message_id")
        or probe.get("interaction_unit_id"),
        "persona_id": probe.get("persona_id"),
        "interaction_unit_id": probe.get("interaction_unit_id"),
        "event_occurrence_id": probe.get("event_occurrence_id"),
        "event_line_id": probe.get("event_line_id"),
        "event_category_id": probe.get("event_category_id"),
        "event_stage": probe.get("event_stage"),
        "probe_type": probe.get("probe_type"),
        "paper_probe_id": probe.get("paper_probe_id"),
        "primary_dimension_id": probe.get("primary_dimension_id"),
        "evaluation_dimension_ids": list(probe.get("evaluation_dimension_ids", [])),
        "target_detail_ids": list(probe.get("target_detail_ids", [])),
        "read_only": probe.get("read_only", True),
        "writeback_policy": probe.get("writeback_policy"),
        "tom_dimensions": list(probe.get("diagnostic_dimensions") or probe.get("tom_dimensions") or []),
        "tom_assessment": dict(probe.get("tom_assessment", {})),
        "tau": dict(binding),
        "source_tau": {
            "source": "tau_contract.P",
            "probe_id": probe.get("probe_id") or message_id,
        },
    }


def _naturalized_by_unit_id(naturalized_dialogues: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    candidates = naturalized_dialogues.get("naturalized_dialogues", [])
    if not isinstance(candidates, list):
        candidates = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        unit_id = str(item.get("source_interaction_unit_id") or "")
        if unit_id:
            result[unit_id] = item
    return result


def _message_sort_key(message: dict[str, Any]) -> tuple[str, int, str, int, int, str]:
    return (
        str(message.get("persona_id", "")),
        int(message.get("day", 0) or 0),
        str(message.get("day_group_id", "")),
        int(message.get("within_day_index", 1) or 1),
        1 if message.get("turn_type") == "targeted_probe" else 0,
        str(message.get("message_id", "")),
    )


def _event_title(item: dict[str, Any]) -> str:
    title = item.get("event_title")
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or "")
    return str(title or "")
