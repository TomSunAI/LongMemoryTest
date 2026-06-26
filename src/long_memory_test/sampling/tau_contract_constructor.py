from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from .zh_localization import zh_value


TAU_CONTRACT_SCHEMA_VERSION = "tau_contract_batch_v0.1"
TAU_BINDING_SCHEMA_VERSION = "tau_binding_batch_v0.1"


@dataclass(frozen=True)
class TauContractConstructionConfig:
    notation: str = "tau=(z,T,L,I,P)"
    llm_generation_used: bool = False


def construct_tau_contract_for_batch(
    *,
    timeline_batch: dict[str, Any],
    daily_interactions: dict[str, Any],
    probe_plan: dict[str, Any],
    sampled_personas: dict[str, Any] | None = None,
    event_lines_batch: dict[str, Any] | None = None,
    accepted_event_sets: dict[str, Any] | None = None,
    source_paths: dict[str, str] | None = None,
    config: TauContractConstructionConfig | None = None,
) -> dict[str, Any]:
    cfg = config or TauContractConstructionConfig()
    timeline_occurrences = _timeline_occurrences_by_id(timeline_batch)
    daily_units = _daily_units_by_id(daily_interactions)
    probes = _probe_questions_by_id(probe_plan)
    persona_refs = _persona_refs_by_id(timeline_batch, daily_interactions)
    sampled_by_persona = _sampled_personas_by_id(sampled_personas or {})
    source_event_lines = _event_lines_by_id(event_lines_batch or {})
    accepted_by_persona = _accepted_event_sets_by_persona(accepted_event_sets or {})

    persona_ids = sorted(
        {
            *_persona_ids_from_timeline(timeline_batch),
            *_persona_ids_from_daily(daily_interactions),
            *_persona_ids_from_probes(probe_plan),
        }
    )
    line_theme_ids: dict[str, str] = {}
    themes: dict[str, dict[str, Any]] = {}
    event_lines: dict[str, dict[str, Any]] = {}
    occurrence_rows_by_line: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for occurrence in sorted(
        timeline_occurrences.values(),
        key=lambda item: (
            str(item.get("persona_id")),
            int(item.get("day", 0) or 0),
            int(item.get("within_day_index", 1) or 1),
        ),
    ):
        persona_id = str(occurrence.get("persona_id") or "")
        event_line_id = str(occurrence.get("event_line_id") or "")
        if not persona_id or not event_line_id:
            continue
        source_line = source_event_lines.get(event_line_id, {})
        theme_id = _theme_id_for_event_line(
            event_line_id=event_line_id,
            persona_id=persona_id,
            event_category_id=str(
                occurrence.get("event_category_id")
                or source_line.get("event_category_id")
                or ""
            ),
        )
        line_theme_ids[event_line_id] = theme_id
        theme = themes.setdefault(
            theme_id,
            _build_theme(
                theme_id=theme_id,
                persona_id=persona_id,
                occurrence=occurrence,
                source_line=source_line,
                accepted_event_sets=accepted_by_persona.get(persona_id, {}),
            ),
        )
        _append_unique(theme["event_line_ids"], event_line_id)
        _append_unique(theme["event_occurrence_ids"], str(occurrence.get("event_occurrence_id")))

        line = event_lines.setdefault(
            event_line_id,
            _build_event_line(
                event_line_id=event_line_id,
                theme_id=theme_id,
                persona_id=persona_id,
                occurrence=occurrence,
                source_line=source_line,
            ),
        )
        occurrence_row = _occurrence_row(occurrence)
        occurrence_rows_by_line[event_line_id].append(occurrence_row)
        _append_unique(line["event_occurrence_ids"], occurrence_row["event_occurrence_id"])
        _append_unique(line["interaction_unit_ids"], str(occurrence.get("interaction_unit_id")))
        for probe_id in occurrence.get("probe_ids", []):
            _append_unique(line["probe_ids"], str(probe_id))

    for event_line_id, line in event_lines.items():
        rows = sorted(
            occurrence_rows_by_line[event_line_id],
            key=lambda item: (int(item.get("day", 0) or 0), int(item.get("within_day_index", 1) or 1)),
        )
        line["observed_stage_sequence"] = rows
        line["occurrence_count"] = len(rows)
        line["first_day"] = rows[0]["day"] if rows else None
        line["last_day"] = rows[-1]["day"] if rows else None

    interaction_units = [
        _build_interaction_unit_contract(
            unit=unit,
            line_theme_ids=line_theme_ids,
            timeline_occurrence=timeline_occurrences.get(str(unit.get("event_occurrence_id")), {}),
        )
        for unit in sorted(
            daily_units.values(),
            key=lambda item: (
                str(item.get("persona_id")),
                int(item.get("day", 0) or 0),
                int(item.get("within_day_index", 1) or 1),
            ),
        )
    ]
    unit_by_id = {str(unit["interaction_unit_id"]): unit for unit in interaction_units}

    targeted_probes = [
        _build_probe_contract(
            probe=probe,
            unit=unit_by_id.get(str(probe.get("insert_after_message_id")), {}),
            line_theme_ids=line_theme_ids,
        )
        for probe in sorted(
            probes.values(),
            key=lambda item: (
                str(item.get("persona_id")),
                int(item.get("day", 0) or 0),
                str(item.get("probe_id")),
            ),
        )
    ]

    for probe in targeted_probes:
        line = event_lines.get(str(probe.get("event_line_id")))
        if line is not None:
            _append_unique(line["probe_ids"], str(probe.get("probe_id")))

    z_nodes = [
        _build_z_contract(
            persona_id=persona_id,
            persona_ref=persona_refs.get(persona_id, {}),
            sampled_persona=sampled_by_persona.get(persona_id, {}),
        )
        for persona_id in persona_ids
    ]

    message_bindings = _build_message_bindings(
        interaction_units=interaction_units,
        targeted_probes=targeted_probes,
    )
    persona_nodes = _build_persona_nodes(
        persona_ids=persona_ids,
        themes=list(themes.values()),
        event_lines=list(event_lines.values()),
        interaction_units=interaction_units,
        targeted_probes=targeted_probes,
    )
    summary = _summarize_contract(
        z_nodes=z_nodes,
        themes=list(themes.values()),
        event_lines=list(event_lines.values()),
        interaction_units=interaction_units,
        targeted_probes=targeted_probes,
        message_bindings=message_bindings,
    )
    contract = {
        "schema_version": TAU_CONTRACT_SCHEMA_VERSION,
        "sampling_stage": "P4_tau_contract_construction",
        "notation": cfg.notation,
        "definition": {
            "z": "采样得到的用户人物；批量模式下是人物合同列表。",
            "T": "每个人物的长期事件主题集合。",
            "L": "把每个长期主题实例化为跨天反复出现的事件线。",
            "I": "从活跃事件出现生成的每日互动单元。",
            "P": "插入在选定互动单元之后的定向关系评测问题。",
        },
        "construction_scope": {
            "from_timeline": True,
            "from_daily_interaction_units": True,
            "from_probe_plan": True,
            "from_sampled_personas": bool(sampled_personas),
            "from_event_lines_batch": bool(event_lines_batch),
            "from_accepted_event_sets": bool(accepted_event_sets),
            "tau_contract_constructed": True,
            "llm_generation_used": cfg.llm_generation_used,
        },
        "source_refs": _source_refs(
            timeline_batch=timeline_batch,
            daily_interactions=daily_interactions,
            probe_plan=probe_plan,
            source_paths=source_paths or {},
        ),
        "z": z_nodes,
        "T": sorted(themes.values(), key=lambda item: str(item.get("theme_id"))),
        "L": sorted(event_lines.values(), key=lambda item: str(item.get("event_line_id"))),
        "I": interaction_units,
        "P": targeted_probes,
        "personas": persona_nodes,
        "message_bindings": message_bindings,
        "summary": summary,
    }
    contract["validation"] = validate_tau_contract(
        contract=contract,
        timeline_batch=timeline_batch,
        daily_interactions=daily_interactions,
        probe_plan=probe_plan,
    )
    return contract


def validate_tau_contract(
    *,
    contract: dict[str, Any],
    timeline_batch: dict[str, Any],
    daily_interactions: dict[str, Any],
    probe_plan: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    if contract.get("schema_version") != TAU_CONTRACT_SCHEMA_VERSION:
        issues.append("Unsupported tau contract schema_version.")
    if contract.get("notation") != "tau=(z,T,L,I,P)":
        issues.append("Unexpected tau notation.")

    for source_name, payload in [
        ("timeline", timeline_batch),
        ("daily_interactions", daily_interactions),
        ("probe_plan", probe_plan),
    ]:
        validation = payload.get("validation", {})
        if isinstance(validation, dict):
            status = validation.get("status")
            if status == "fail":
                issues.append(f"Source {source_name} validation failed.")
            elif status not in {"pass", None}:
                warnings.append(f"Source {source_name} has unknown validation status {status}.")

    z_ids = {str(item.get("persona_id")) for item in _dict_items(contract.get("z"))}
    theme_ids = {str(item.get("theme_id")) for item in _dict_items(contract.get("T"))}
    line_ids = {str(item.get("event_line_id")) for item in _dict_items(contract.get("L"))}
    unit_ids = {str(item.get("interaction_unit_id")) for item in _dict_items(contract.get("I"))}
    probe_ids = {str(item.get("probe_id")) for item in _dict_items(contract.get("P"))}
    if not z_ids:
        issues.append("z must contain at least one persona.")
    if not theme_ids:
        issues.append("T must contain at least one event theme.")
    if not line_ids:
        issues.append("L must contain at least one event line.")
    if not unit_ids:
        issues.append("I must contain at least one interaction unit.")

    _validate_unique_ids("z.persona_id", [item.get("persona_id") for item in _dict_items(contract.get("z"))], issues)
    _validate_unique_ids("T.theme_id", [item.get("theme_id") for item in _dict_items(contract.get("T"))], issues)
    _validate_unique_ids("L.event_line_id", [item.get("event_line_id") for item in _dict_items(contract.get("L"))], issues)
    _validate_unique_ids("I.interaction_unit_id", [item.get("interaction_unit_id") for item in _dict_items(contract.get("I"))], issues)
    _validate_unique_ids("P.probe_id", [item.get("probe_id") for item in _dict_items(contract.get("P"))], issues)

    expected_occurrence_ids = set(_timeline_occurrences_by_id(timeline_batch))
    contract_occurrence_ids = {
        str(item.get("event_occurrence_id"))
        for item in _dict_items(contract.get("I"))
        if item.get("event_occurrence_id")
    }
    if contract_occurrence_ids != expected_occurrence_ids:
        missing = sorted(expected_occurrence_ids - contract_occurrence_ids)
        extra = sorted(contract_occurrence_ids - expected_occurrence_ids)
        if missing:
            issues.append(f"Missing I units for timeline occurrences: {missing[:10]}.")
        if extra:
            issues.append(f"I units reference extra timeline occurrences: {extra[:10]}.")

    expected_unit_ids = set(_daily_units_by_id(daily_interactions))
    if unit_ids != expected_unit_ids:
        missing = sorted(expected_unit_ids - unit_ids)
        extra = sorted(unit_ids - expected_unit_ids)
        if missing:
            issues.append(f"Missing contract I ids from daily interactions: {missing[:10]}.")
        if extra:
            issues.append(f"Contract has extra I ids absent from daily interactions: {extra[:10]}.")

    expected_probe_ids = set(_probe_questions_by_id(probe_plan))
    if probe_ids != expected_probe_ids:
        missing = sorted(expected_probe_ids - probe_ids)
        extra = sorted(probe_ids - expected_probe_ids)
        if missing:
            issues.append(f"Missing contract P ids from probe plan: {missing[:10]}.")
        if extra:
            issues.append(f"Contract has extra P ids absent from probe plan: {extra[:10]}.")

    units_by_id = {str(item.get("interaction_unit_id")): item for item in _dict_items(contract.get("I"))}
    for theme in _dict_items(contract.get("T")):
        if str(theme.get("persona_id")) not in z_ids:
            issues.append(f"Theme {theme.get('theme_id')} references missing persona.")
    for line in _dict_items(contract.get("L")):
        if str(line.get("persona_id")) not in z_ids:
            issues.append(f"Event line {line.get('event_line_id')} references missing persona.")
        if str(line.get("theme_id")) not in theme_ids:
            issues.append(f"Event line {line.get('event_line_id')} references missing theme.")
        if not line.get("observed_stage_sequence"):
            issues.append(f"Event line {line.get('event_line_id')} has no observed stage sequence.")
    for unit in _dict_items(contract.get("I")):
        unit_id = str(unit.get("interaction_unit_id"))
        if str(unit.get("persona_id")) not in z_ids:
            issues.append(f"I {unit_id} references missing persona.")
        if str(unit.get("theme_id")) not in theme_ids:
            issues.append(f"I {unit_id} references missing theme.")
        if str(unit.get("event_line_id")) not in line_ids:
            issues.append(f"I {unit_id} references missing event line.")
        if not unit.get("scripted_opening", {}).get("user_message"):
            issues.append(f"I {unit_id} is missing scripted opening user_message.")
        if not unit.get("scene_boundary", {}).get("allowed_facts"):
            issues.append(f"I {unit_id} is missing scene allowed facts.")
    for probe in _dict_items(contract.get("P")):
        probe_id = str(probe.get("probe_id"))
        unit_id = str(probe.get("interaction_unit_id"))
        unit = units_by_id.get(unit_id)
        if unit is None:
            issues.append(f"Probe {probe_id} references missing I {unit_id}.")
            continue
        if str(probe.get("event_occurrence_id")) != str(unit.get("event_occurrence_id")):
            issues.append(f"Probe {probe_id} event_occurrence_id does not match bound I.")
        if str(probe.get("event_line_id")) != str(unit.get("event_line_id")):
            issues.append(f"Probe {probe_id} event_line_id does not match bound I.")
        if probe.get("read_only") is not True:
            issues.append(f"Probe {probe_id} must be read_only=true.")
        if probe.get("writeback_policy") != "probe_turn_must_not_write_to_memory":
            issues.append(f"Probe {probe_id} has unsafe writeback_policy.")

    probe_links_from_daily = {
        str(link.get("probe_id"))
        for unit in _daily_units_by_id(daily_interactions).values()
        for link in unit.get("probe_links", [])
        if isinstance(link, dict) and link.get("probe_id")
    }
    if probe_links_from_daily != expected_probe_ids:
        missing = sorted(expected_probe_ids - probe_links_from_daily)
        extra = sorted(probe_links_from_daily - expected_probe_ids)
        if missing:
            issues.append(f"Daily I probe_links miss probe plan ids: {missing[:10]}.")
        if extra:
            issues.append(f"Daily I probe_links contain extra probe ids: {extra[:10]}.")

    bindings = contract.get("message_bindings", {})
    if not isinstance(bindings, dict):
        issues.append("message_bindings must be an object.")
        bindings = {}
    expected_message_ids = unit_ids | probe_ids
    binding_ids = set(str(key) for key in bindings)
    if binding_ids != expected_message_ids:
        missing = sorted(expected_message_ids - binding_ids)
        extra = sorted(binding_ids - expected_message_ids)
        if missing:
            issues.append(f"Missing message bindings: {missing[:10]}.")
        if extra:
            issues.append(f"Extra message bindings: {extra[:10]}.")
    for message_id, binding in bindings.items():
        if not isinstance(binding, dict):
            issues.append(f"Message binding {message_id} is invalid.")
            continue
        if str(binding.get("event_line_id")) not in line_ids:
            issues.append(f"Message binding {message_id} references missing event line.")
        if str(binding.get("theme_id")) not in theme_ids:
            issues.append(f"Message binding {message_id} references missing theme.")

    _validate_no_duplicate_event_line_per_day(contract, issues)
    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
    }


def _build_z_contract(
    *,
    persona_id: str,
    persona_ref: dict[str, Any],
    sampled_persona: dict[str, Any],
) -> dict[str, Any]:
    source = sampled_persona or persona_ref
    return {
        "schema_version": "tau_z_persona_v0.1",
        "persona_id": persona_id,
        "source_archetype": source.get("source_archetype") or persona_ref.get("source_archetype"),
        "source_archetype_label": source.get("source_archetype_label"),
        "stable_profile": _drop_empty_values(
            {
                "age_range": source.get("age_range"),
                "occupation": source.get("occupation") or persona_ref.get("occupation"),
                "occupation_status": source.get("occupation_status"),
                "education_background": source.get("education_background"),
                "family_structure": (
                    source.get("family_structure") or persona_ref.get("family_structure")
                ),
                "life_stage": source.get("life_stage"),
                "economic_condition": source.get("economic_condition"),
                "social_support": source.get("social_support"),
                "primary_life_domains": (
                    source.get("primary_life_domains") or persona_ref.get("primary_life_domains")
                ),
            }
        ),
        "long_term_goals": _as_list(source.get("long_term_goals")),
        "communication_style": _as_list(source.get("communication_style")),
        "stress_response": _as_list(source.get("stress_response")),
        "decision_style": _as_list(source.get("decision_style")),
        "memory_relevant_traits": _as_list(source.get("memory_relevant_traits")),
        "sensitive_fields": source.get("sensitive_fields", {}),
        "locale_view_zh": {
            "source_archetype_label": zh_value(source.get("source_archetype_label")),
            "stable_profile": _drop_empty_values(
                {
                    "age_range": zh_value(source.get("age_range")),
                    "occupation": zh_value(source.get("occupation") or persona_ref.get("occupation")),
                    "occupation_status": zh_value(source.get("occupation_status")),
                    "education_background": zh_value(source.get("education_background")),
                    "family_structure": zh_value(
                        source.get("family_structure") or persona_ref.get("family_structure")
                    ),
                    "life_stage": zh_value(source.get("life_stage")),
                    "economic_condition": zh_value(source.get("economic_condition")),
                    "social_support": zh_value(source.get("social_support")),
                    "primary_life_domains": zh_value(
                        source.get("primary_life_domains") or persona_ref.get("primary_life_domains")
                    ),
                }
            ),
            "long_term_goals": zh_value(_as_list(source.get("long_term_goals"))),
            "communication_style": zh_value(_as_list(source.get("communication_style"))),
            "stress_response": zh_value(_as_list(source.get("stress_response"))),
            "decision_style": zh_value(_as_list(source.get("decision_style"))),
            "memory_relevant_traits": zh_value(_as_list(source.get("memory_relevant_traits"))),
            "sensitive_fields": zh_value(source.get("sensitive_fields", {})),
        },
        "source_ref": {
            "sampled_persona_available": bool(sampled_persona),
            "persona_ref_available": bool(persona_ref),
        },
    }


def _build_theme(
    *,
    theme_id: str,
    persona_id: str,
    occurrence: dict[str, Any],
    source_line: dict[str, Any],
    accepted_event_sets: dict[str, Any],
) -> dict[str, Any]:
    accepted_events = {
        str(item.get("event_category_id")): item
        for item in accepted_event_sets.get("accepted_events", [])
        if isinstance(item, dict) and item.get("event_category_id")
    }
    category_id = str(occurrence.get("event_category_id") or source_line.get("event_category_id") or "")
    accepted_event = accepted_events.get(category_id, {})
    return {
        "schema_version": "tau_theme_v0.1",
        "theme_id": theme_id,
        "persona_id": persona_id,
        "event_category_id": category_id,
        "event_domain": occurrence.get("event_domain") or source_line.get("event_domain"),
        "event_domain_zh": occurrence.get("event_domain_zh") or source_line.get("event_domain_zh"),
        "event_type": source_line.get("event_type") or accepted_event.get("event_type"),
        "event_title": occurrence.get("event_title") or source_line.get("event_title"),
        "theme_summary": (
            occurrence.get("persistent_event_summary")
            or source_line.get("persistent_event_summary")
            or accepted_event.get("core_issue")
        ),
        "event_line_ids": [],
        "event_occurrence_ids": [],
        "source_ref": {
            "from_accepted_event_set": bool(accepted_event),
            "from_event_line": bool(source_line),
            "from_timeline_occurrence": True,
        },
    }


def _build_event_line(
    *,
    event_line_id: str,
    theme_id: str,
    persona_id: str,
    occurrence: dict[str, Any],
    source_line: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "tau_event_line_v0.1",
        "event_line_id": event_line_id,
        "theme_id": theme_id,
        "persona_id": persona_id,
        "event_category_id": occurrence.get("event_category_id") or source_line.get("event_category_id"),
        "event_domain": occurrence.get("event_domain") or source_line.get("event_domain"),
        "event_domain_zh": occurrence.get("event_domain_zh") or source_line.get("event_domain_zh"),
        "event_title": occurrence.get("event_title") or source_line.get("event_title"),
        "persistent_event_summary": (
            occurrence.get("persistent_event_summary")
            or source_line.get("persistent_event_summary")
        ),
        "relational_memory_targets": _as_list(source_line.get("relational_memory_targets")),
        "source_stage_sequence": _compact_source_stage_sequence(source_line),
        "observed_stage_sequence": [],
        "event_occurrence_ids": [],
        "interaction_unit_ids": [],
        "probe_ids": [],
        "occurrence_count": 0,
        "first_day": None,
        "last_day": None,
    }


def _build_interaction_unit_contract(
    *,
    unit: dict[str, Any],
    line_theme_ids: dict[str, str],
    timeline_occurrence: dict[str, Any],
) -> dict[str, Any]:
    event_line_id = str(unit.get("event_line_id") or timeline_occurrence.get("event_line_id") or "")
    probe_ids = [
        str(link.get("probe_id"))
        for link in unit.get("probe_links", [])
        if isinstance(link, dict) and link.get("probe_id")
    ]
    return {
        "schema_version": "tau_interaction_unit_v0.1",
        "interaction_unit_id": unit.get("interaction_unit_id"),
        "event_occurrence_id": unit.get("event_occurrence_id"),
        "persona_id": unit.get("persona_id"),
        "day": unit.get("day"),
        "day_group_id": unit.get("day_group_id"),
        "within_day_index": unit.get("within_day_index"),
        "parallel_event_count": unit.get("parallel_event_count", 1),
        "cross_occurrence_reference_allowed": unit.get("cross_occurrence_reference_allowed", False),
        "theme_id": line_theme_ids.get(event_line_id),
        "event_line_id": event_line_id,
        "event_category_id": unit.get("event_category_id"),
        "event_domain": unit.get("event_domain"),
        "event_domain_zh": unit.get("event_domain_zh"),
        "event_title": unit.get("event_title"),
        "event_stage": unit.get("event_stage"),
        "stage_index": unit.get("stage_index"),
        "occurrence_index": unit.get("occurrence_index"),
        "occurrence_count_for_line": unit.get("occurrence_count_for_line"),
        "related_previous_days": unit.get("related_previous_days", []),
        "current_state_change_fact": unit.get("current_state_change_fact"),
        "scripted_opening": unit.get("scripted_opening", {}),
        "constrained_followup": unit.get("constrained_followup", {}),
        "scene_boundary": unit.get("scene_boundary", {}),
        "probe_ids": probe_ids,
        "has_probe": bool(probe_ids),
        "source_timeline_fields": unit.get("source_timeline_fields", {}),
    }


def _build_probe_contract(
    *,
    probe: dict[str, Any],
    unit: dict[str, Any],
    line_theme_ids: dict[str, str],
) -> dict[str, Any]:
    event_line_id = str(probe.get("event_line_id") or unit.get("event_line_id") or "")
    return {
        "schema_version": "tau_targeted_probe_v0.1",
        "probe_id": probe.get("probe_id"),
        "message_id": probe.get("message_id") or probe.get("probe_id"),
        "turn_type": probe.get("turn_type", "targeted_probe"),
        "persona_id": probe.get("persona_id") or unit.get("persona_id"),
        "day": probe.get("day") or unit.get("day"),
        "day_group_id": unit.get("day_group_id") or probe.get("day_interaction_unit_id"),
        "interaction_unit_id": probe.get("insert_after_message_id"),
        "event_occurrence_id": probe.get("event_occurrence_id") or unit.get("event_occurrence_id"),
        "theme_id": line_theme_ids.get(event_line_id) or unit.get("theme_id"),
        "event_line_id": event_line_id,
        "event_category_id": probe.get("event_category_id") or unit.get("event_category_id"),
        "event_stage": probe.get("event_stage") or unit.get("event_stage"),
        "probe_type": probe.get("probe_type"),
        "paper_probe_id": probe.get("paper_probe_id"),
        "paper_probe_type": probe.get("paper_probe_type"),
        "paper_probe_zh": probe.get("paper_probe_zh"),
        "primary_dimension_id": probe.get("primary_dimension_id"),
        "primary_dimension": probe.get("primary_dimension"),
        "secondary_dimension_ids": probe.get("secondary_dimension_ids", []),
        "question": probe.get("question") or probe.get("user_message"),
        "required_memory_type": probe.get("required_memory_type", []),
        "evaluation_dimension_ids": probe.get("evaluation_dimension_ids", []),
        "evaluation_dimensions": probe.get("evaluation_dimensions", []),
        "diagnostic_dimensions": probe.get("diagnostic_dimensions")
        or probe.get("tom_dimensions", []),
        "target_detail_ids": probe.get("target_detail_ids", []),
        "ground_truth": probe.get("ground_truth", {}),
        "read_only": probe.get("read_only", True),
        "writeback_policy": probe.get("writeback_policy"),
        "tom_assessment": probe.get("tom_assessment", {}),
    }


def _build_message_bindings(
    *,
    interaction_units: list[dict[str, Any]],
    targeted_probes: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for unit in interaction_units:
        message_id = str(unit.get("interaction_unit_id"))
        bindings[message_id] = _message_binding(
            message_id=message_id,
            turn_type="scripted_opening",
            persona_id=str(unit.get("persona_id")),
            theme_id=str(unit.get("theme_id")),
            event_line_id=str(unit.get("event_line_id")),
            interaction_unit_id=str(unit.get("interaction_unit_id")),
            event_occurrence_id=str(unit.get("event_occurrence_id")),
            day=unit.get("day"),
            day_group_id=unit.get("day_group_id"),
            event_stage=unit.get("event_stage"),
        )
    for probe in targeted_probes:
        message_id = str(probe.get("message_id") or probe.get("probe_id"))
        bindings[message_id] = {
            **_message_binding(
                message_id=message_id,
                turn_type="targeted_probe",
                persona_id=str(probe.get("persona_id")),
                theme_id=str(probe.get("theme_id")),
                event_line_id=str(probe.get("event_line_id")),
                interaction_unit_id=str(probe.get("interaction_unit_id")),
                event_occurrence_id=str(probe.get("event_occurrence_id")),
                day=probe.get("day"),
                day_group_id=probe.get("day_group_id"),
                event_stage=probe.get("event_stage"),
            ),
            "probe_id": probe.get("probe_id"),
            "probe_type": probe.get("probe_type"),
            "paper_probe_id": probe.get("paper_probe_id"),
        }
    return bindings


def _message_binding(
    *,
    message_id: str,
    turn_type: str,
    persona_id: str,
    theme_id: str,
    event_line_id: str,
    interaction_unit_id: str,
    event_occurrence_id: str,
    day: Any,
    day_group_id: Any,
    event_stage: Any,
) -> dict[str, Any]:
    return {
        "schema_version": TAU_BINDING_SCHEMA_VERSION,
        "message_id": message_id,
        "turn_type": turn_type,
        "persona_id": persona_id,
        "z_id": persona_id,
        "theme_id": theme_id,
        "event_line_id": event_line_id,
        "interaction_unit_id": interaction_unit_id,
        "event_occurrence_id": event_occurrence_id,
        "day": day,
        "day_group_id": day_group_id,
        "event_stage": event_stage,
    }


def _build_persona_nodes(
    *,
    persona_ids: list[str],
    themes: list[dict[str, Any]],
    event_lines: list[dict[str, Any]],
    interaction_units: list[dict[str, Any]],
    targeted_probes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    nodes = []
    for persona_id in persona_ids:
        persona_themes = [item for item in themes if item.get("persona_id") == persona_id]
        persona_lines = [item for item in event_lines if item.get("persona_id") == persona_id]
        persona_units = [item for item in interaction_units if item.get("persona_id") == persona_id]
        persona_probes = [item for item in targeted_probes if item.get("persona_id") == persona_id]
        active_days = sorted({int(item.get("day", 0) or 0) for item in persona_units})
        day_group_counts = Counter(str(item.get("day_group_id")) for item in persona_units)
        nodes.append(
            {
                "persona_id": persona_id,
                "z_id": persona_id,
                "theme_ids": sorted(str(item.get("theme_id")) for item in persona_themes),
                "event_line_ids": sorted(str(item.get("event_line_id")) for item in persona_lines),
                "interaction_unit_ids": [
                    str(item.get("interaction_unit_id")) for item in persona_units
                ],
                "probe_ids": [str(item.get("probe_id")) for item in persona_probes],
                "active_day_count": len(active_days),
                "interaction_unit_count": len(persona_units),
                "probe_count": len(persona_probes),
                "parallel_day_count": sum(1 for count in day_group_counts.values() if count > 1),
            }
        )
    return nodes


def _summarize_contract(
    *,
    z_nodes: list[dict[str, Any]],
    themes: list[dict[str, Any]],
    event_lines: list[dict[str, Any]],
    interaction_units: list[dict[str, Any]],
    targeted_probes: list[dict[str, Any]],
    message_bindings: dict[str, Any],
) -> dict[str, Any]:
    day_group_counts = Counter(str(item.get("day_group_id")) for item in interaction_units)
    per_persona_units = Counter(str(item.get("persona_id")) for item in interaction_units)
    per_persona_probes = Counter(str(item.get("persona_id")) for item in targeted_probes)
    primary_dimension_counts_by_persona: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for probe in targeted_probes:
        primary_dimension_counts_by_persona[str(probe.get("persona_id"))][
            str(probe.get("primary_dimension_id"))
        ] += 1
    return {
        "persona_count": len(z_nodes),
        "theme_count": len(themes),
        "event_line_count": len(event_lines),
        "interaction_unit_count": len(interaction_units),
        "targeted_probe_count": len(targeted_probes),
        "message_binding_count": len(message_bindings),
        "active_day_count": len(day_group_counts),
        "parallel_day_count": sum(1 for count in day_group_counts.values() if count > 1),
        "probed_interaction_unit_count": sum(1 for item in interaction_units if item.get("has_probe")),
        "unprobed_interaction_unit_count": sum(1 for item in interaction_units if not item.get("has_probe")),
        "interaction_units_per_persona": dict(sorted(per_persona_units.items())),
        "probes_per_persona": dict(sorted(per_persona_probes.items())),
        "paper_probe_type_counts": dict(
            sorted(Counter(str(item.get("paper_probe_id")) for item in targeted_probes).items())
        ),
        "primary_dimension_counts": dict(
            sorted(Counter(str(item.get("primary_dimension_id")) for item in targeted_probes).items())
        ),
        "primary_dimension_counts_by_persona": {
            persona_id: dict(sorted(counts.items()))
            for persona_id, counts in sorted(primary_dimension_counts_by_persona.items())
        },
    }


def _source_refs(
    *,
    timeline_batch: dict[str, Any],
    daily_interactions: dict[str, Any],
    probe_plan: dict[str, Any],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    return {
        "timeline": {
            "path": source_paths.get("timeline"),
            "schema_version": timeline_batch.get("schema_version"),
            "sampling_stage": timeline_batch.get("sampling_stage"),
            "validation": timeline_batch.get("validation", {}),
        },
        "daily_interaction_units": {
            "path": source_paths.get("daily_interaction_units"),
            "schema_version": daily_interactions.get("schema_version"),
            "sampling_stage": daily_interactions.get("sampling_stage"),
            "validation": daily_interactions.get("validation", {}),
        },
        "probe_plan": {
            "path": source_paths.get("probe_plan"),
            "schema_version": probe_plan.get("schema_version"),
            "sampling_stage": probe_plan.get("sampling_stage"),
            "validation": probe_plan.get("validation", {}),
        },
        "sampled_personas": {"path": source_paths.get("sampled_personas")},
        "event_lines_batch": {"path": source_paths.get("event_lines_batch")},
        "accepted_event_sets": {"path": source_paths.get("accepted_event_sets")},
    }


def _timeline_occurrences_by_id(timeline_batch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for timeline in timeline_batch.get("timelines", []):
        if not isinstance(timeline, dict):
            continue
        for day in timeline.get("days", []):
            if not isinstance(day, dict) or not day.get("active"):
                continue
            for occurrence in _day_event_occurrences(day):
                occurrence_id = str(occurrence.get("event_occurrence_id") or "")
                if occurrence_id:
                    result[occurrence_id] = occurrence
    return result


def _daily_units_by_id(daily_interactions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for persona in daily_interactions.get("personas", []):
        if not isinstance(persona, dict):
            continue
        for day in persona.get("days", []):
            if not isinstance(day, dict):
                continue
            for unit in day.get("interaction_units", []):
                if not isinstance(unit, dict):
                    continue
                unit_id = str(unit.get("interaction_unit_id") or "")
                if unit_id:
                    result[unit_id] = unit
    return result


def _probe_questions_by_id(probe_plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("probe_id")): item
        for item in probe_plan.get("probe_questions", [])
        if isinstance(item, dict) and item.get("probe_id")
    }


def _event_lines_by_id(event_lines_batch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for persona in event_lines_batch.get("personas", []):
        if not isinstance(persona, dict):
            continue
        for line in persona.get("event_lines", []):
            if isinstance(line, dict) and line.get("event_line_id"):
                result[str(line["event_line_id"])] = line
    return result


def _sampled_personas_by_id(sampled_personas: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("persona_id")): item
        for item in sampled_personas.get("personas", [])
        if isinstance(item, dict) and item.get("persona_id")
    }


def _accepted_event_sets_by_persona(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("persona_id")): item
        for item in data.get("accepted_persona_event_sets", [])
        if isinstance(item, dict) and item.get("persona_id")
    }


def _persona_refs_by_id(
    timeline_batch: dict[str, Any],
    daily_interactions: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result = {}
    for timeline in timeline_batch.get("timelines", []):
        if isinstance(timeline, dict) and timeline.get("persona_id"):
            result[str(timeline["persona_id"])] = timeline.get("persona_ref", {})
    for persona in daily_interactions.get("personas", []):
        if isinstance(persona, dict) and persona.get("persona_id"):
            result.setdefault(str(persona["persona_id"]), persona.get("persona_ref", {}))
    return result


def _persona_ids_from_timeline(timeline_batch: dict[str, Any]) -> set[str]:
    return {
        str(item.get("persona_id"))
        for item in timeline_batch.get("timelines", [])
        if isinstance(item, dict) and item.get("persona_id")
    }


def _persona_ids_from_daily(daily_interactions: dict[str, Any]) -> set[str]:
    return {
        str(item.get("persona_id"))
        for item in daily_interactions.get("personas", [])
        if isinstance(item, dict) and item.get("persona_id")
    }


def _persona_ids_from_probes(probe_plan: dict[str, Any]) -> set[str]:
    return {
        str(item.get("persona_id"))
        for item in probe_plan.get("probe_questions", [])
        if isinstance(item, dict) and item.get("persona_id")
    }


def _day_event_occurrences(day: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = [
        item for item in day.get("event_occurrences", []) if isinstance(item, dict)
    ]
    if occurrences:
        return occurrences
    if day.get("active"):
        return [day]
    return []


def _theme_id_for_event_line(
    *,
    event_line_id: str,
    persona_id: str,
    event_category_id: str,
) -> str:
    if event_line_id.startswith("L_"):
        return "T_" + event_line_id[2:]
    suffix = "_".join(item for item in [persona_id.lower(), event_category_id.lower()] if item)
    return "T_" + (suffix or event_line_id)


def _occurrence_row(occurrence: dict[str, Any]) -> dict[str, Any]:
    return {
        "day": occurrence.get("day"),
        "within_day_index": occurrence.get("within_day_index", 1),
        "event_occurrence_id": occurrence.get("event_occurrence_id"),
        "interaction_unit_id": occurrence.get("interaction_unit_id"),
        "event_stage": occurrence.get("event_stage"),
        "stage_index": occurrence.get("stage_index"),
        "occurrence_index": occurrence.get("occurrence_index"),
        "related_previous_days": occurrence.get("related_previous_days", []),
        "probe_ids": [str(item) for item in occurrence.get("probe_ids", [])],
        "surface_event": occurrence.get("surface_event"),
        "surface_event_zh": occurrence.get("surface_event_zh"),
        "assistant_memory_expectation": occurrence.get("assistant_memory_expectation"),
        "assistant_memory_expectation_zh": occurrence.get("assistant_memory_expectation_zh"),
        "allowed_base_facts": occurrence.get("allowed_base_facts", []),
        "allowed_base_facts_zh": occurrence.get("allowed_base_facts_zh", []),
        "event_candidate_facts": occurrence.get("event_candidate_facts", []),
        "persona_conditioned_facts": occurrence.get("persona_conditioned_facts", []),
        "stage_delta_facts": occurrence.get("stage_delta_facts", []),
        "allowed_new_facts": occurrence.get("allowed_new_facts", []),
        "allowed_new_facts_zh": occurrence.get("allowed_new_facts_zh", []),
    }


def _compact_source_stage_sequence(source_line: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for stage in source_line.get("stage_sequence", []):
        if not isinstance(stage, dict):
            continue
        rows.append(
            {
                "stage_index": stage.get("stage_index"),
                "event_stage": stage.get("event_stage"),
                "stage_goal": stage.get("stage_goal"),
                "stage_goal_zh": stage.get("stage_goal_zh"),
                "allowed_base_facts": stage.get("allowed_base_facts", []),
                "allowed_base_facts_zh": stage.get("allowed_base_facts_zh", []),
                "event_candidate_facts": stage.get("event_candidate_facts", []),
                "persona_conditioned_facts": stage.get("persona_conditioned_facts", []),
                "stage_delta_facts": stage.get("stage_delta_facts", []),
                "allowed_new_facts": stage.get("allowed_new_facts", []),
                "allowed_new_facts_zh": stage.get("allowed_new_facts_zh", []),
                "assistant_memory_expectation": stage.get("assistant_memory_expectation"),
                "assistant_memory_expectation_zh": stage.get("assistant_memory_expectation_zh"),
            }
        )
    return rows


def _validate_unique_ids(label: str, ids: list[Any], issues: list[str]) -> None:
    string_ids = [str(item) for item in ids if item not in (None, "")]
    duplicates = sorted(item for item, count in Counter(string_ids).items() if count > 1)
    if duplicates:
        issues.append(f"Duplicate {label}: {duplicates[:10]}.")


def _validate_no_duplicate_event_line_per_day(
    contract: dict[str, Any],
    issues: list[str],
) -> None:
    grouped: defaultdict[tuple[str, int], list[str]] = defaultdict(list)
    for unit in _dict_items(contract.get("I")):
        persona_id = str(unit.get("persona_id"))
        day = int(unit.get("day", 0) or 0)
        if persona_id and day:
            grouped[(persona_id, day)].append(str(unit.get("event_line_id")))
    for (persona_id, day), line_ids in grouped.items():
        duplicates = sorted(line_id for line_id, count in Counter(line_ids).items() if count > 1)
        if duplicates:
            issues.append(f"{persona_id} day {day} repeats event lines in I: {duplicates}.")


def _dict_items(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _drop_empty_values(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in data.items()
        if value is not None and value != [] and value != {}
    }


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)
