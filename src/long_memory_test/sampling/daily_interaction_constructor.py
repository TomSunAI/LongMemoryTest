from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import re
from typing import Any

from .zh_localization import zh_text, zh_value


@dataclass(frozen=True)
class DailyInteractionConstructionConfig:
    random_seed: int = 20260701
    followup_budget_default: int = 2
    cross_occurrence_reference_allowed: bool = False
    include_inactive_days: bool = True


def construct_daily_interactions_for_timeline(
    *,
    timeline_batch: dict[str, Any],
    config: DailyInteractionConstructionConfig | None = None,
) -> dict[str, Any]:
    cfg = config or DailyInteractionConstructionConfig()
    personas = [
        _construct_persona_interactions(persona_timeline=timeline, cfg=cfg)
        for timeline in timeline_batch.get("timelines", [])
        if isinstance(timeline, dict)
    ]
    payload = {
        "schema_version": "daily_interaction_units_batch_v0.1",
        "sampling_stage": "P3_daily_interaction_construction",
        "construction_scope": {
            "from_timeline": True,
            "daily_interactions_constructed": True,
            "tau_contract_constructed": False,
            "llm_generation_used": False,
        },
        "construction_config": asdict(cfg),
        "source_refs": {
            "timeline_schema_version": timeline_batch.get("schema_version"),
            "timeline_sampling_stage": timeline_batch.get("sampling_stage"),
            "timeline_validation": timeline_batch.get("validation", {}),
            "probe_validation": timeline_batch.get("probe_validation", {}),
        },
        "summary": _summarize_personas(personas),
        "personas": personas,
    }
    payload["validation"] = validate_daily_interactions(payload, timeline_batch=timeline_batch)
    return payload


def validate_daily_interactions(
    daily_interactions: dict[str, Any],
    *,
    timeline_batch: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    unit_ids: set[str] = set()
    probe_bindings: dict[str, str] = {}
    timeline_occurrence_ids = {
        str(occurrence.get("event_occurrence_id"))
        for timeline in timeline_batch.get("timelines", [])
        if isinstance(timeline, dict)
        for day in timeline.get("days", [])
        if isinstance(day, dict) and day.get("active")
        for occurrence in _day_event_occurrences(day)
    }
    generated_occurrence_ids: set[str] = set()

    for persona in daily_interactions.get("personas", []):
        if not isinstance(persona, dict):
            issues.append("Invalid persona daily interaction entry.")
            continue
        persona_id = str(persona.get("persona_id", ""))
        for day in persona.get("days", []):
            if not isinstance(day, dict):
                issues.append(f"{persona_id} has invalid day entry.")
                continue
            units = [
                item
                for item in day.get("interaction_units", [])
                if isinstance(item, dict)
            ]
            if not day.get("active") and units:
                issues.append(f"{persona_id} day {day.get('day')} is inactive but has units.")
            line_ids = [str(unit.get("event_line_id")) for unit in units]
            duplicate_lines = sorted(
                line_id for line_id, count in Counter(line_ids).items() if count > 1
            )
            if duplicate_lines:
                issues.append(
                    f"{persona_id} day {day.get('day')} repeats event lines: {duplicate_lines}."
                )
            for unit in units:
                unit_id = str(unit.get("interaction_unit_id", ""))
                occurrence_id = str(unit.get("event_occurrence_id", ""))
                generated_occurrence_ids.add(occurrence_id)
                if not unit_id:
                    issues.append(f"{persona_id} day {day.get('day')} has unit without id.")
                elif unit_id in unit_ids:
                    issues.append(f"Duplicate interaction_unit_id: {unit_id}.")
                unit_ids.add(unit_id)
                if occurrence_id not in timeline_occurrence_ids:
                    issues.append(f"{unit_id} references missing timeline occurrence {occurrence_id}.")
                _validate_unit_contract(unit=unit, issues=issues)
                for probe in unit.get("probe_links", []):
                    if not isinstance(probe, dict):
                        continue
                    probe_id = str(probe.get("probe_id", ""))
                    insert_after = str(probe.get("insert_after_message_id", ""))
                    if insert_after and insert_after != unit_id:
                        issues.append(
                            f"Probe {probe_id} insert_after {insert_after} does not match {unit_id}."
                        )
                    if probe_id:
                        probe_bindings[probe_id] = unit_id

    missing_occurrences = sorted(timeline_occurrence_ids - generated_occurrence_ids)
    if missing_occurrences:
        issues.append(f"Missing interaction units for occurrences: {missing_occurrences[:10]}.")
    if len(missing_occurrences) > 10:
        warnings.append(f"{len(missing_occurrences)} timeline occurrences are missing units.")

    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "unit_count": len(unit_ids),
        "bound_probe_count": len(probe_bindings),
    }


def _construct_persona_interactions(
    *,
    persona_timeline: dict[str, Any],
    cfg: DailyInteractionConstructionConfig,
) -> dict[str, Any]:
    persona_id = str(persona_timeline.get("persona_id", ""))
    persona_ref = persona_timeline.get("persona_ref", {})
    day_nodes = []
    message_bindings: dict[str, dict[str, Any]] = {}
    for day in persona_timeline.get("days", []):
        if not isinstance(day, dict):
            continue
        if not day.get("active"):
            if cfg.include_inactive_days:
                day_nodes.append(
                    {
                        "day": day.get("day"),
                        "active": False,
                        "day_group_id": f"{persona_id}_D{int(day.get('day', 0)):02d}",
                        "interaction_units": [],
                    }
                )
            continue
        occurrences = _day_event_occurrences(day)
        units = [
            _build_interaction_unit(
                persona_id=persona_id,
                persona_ref=persona_ref,
                day=day,
                occurrence=occurrence,
                cfg=cfg,
            )
            for occurrence in occurrences
        ]
        for unit in units:
            message_bindings[unit["interaction_unit_id"]] = _message_binding(
                persona_id=persona_id,
                unit=unit,
                message_id=unit["interaction_unit_id"],
                turn_type="scripted_opening",
            )
            for probe in unit.get("probe_links", []):
                probe_id = str(probe.get("probe_id", ""))
                if not probe_id:
                    continue
                message_bindings[probe_id] = _message_binding(
                    persona_id=persona_id,
                    unit=unit,
                    message_id=probe_id,
                    turn_type="targeted_probe",
                    probe=probe,
                )
        day_nodes.append(
            {
                "day": day.get("day"),
                "active": True,
                "day_group_id": str(day.get("day_interaction_unit_id") or f"{persona_id}_D{int(day.get('day', 0)):02d}"),
                "parallel_event_count": len(units),
                "has_parallel_events": len(units) > 1,
                "cross_occurrence_reference_allowed": cfg.cross_occurrence_reference_allowed,
                "interaction_units": units,
            }
        )
    return {
        "persona_id": persona_id,
        "persona_ref": persona_ref,
        "timeline_days": persona_timeline.get("timeline_days"),
        "active_day_count": sum(1 for day in day_nodes if day.get("active")),
        "interaction_unit_count": sum(
            len(day.get("interaction_units", [])) for day in day_nodes
        ),
        "parallel_day_count": sum(
            1 for day in day_nodes if int(day.get("parallel_event_count", 0)) > 1
        ),
        "days": day_nodes,
        "message_bindings": message_bindings,
    }


def _build_interaction_unit(
    *,
    persona_id: str,
    persona_ref: dict[str, Any],
    day: dict[str, Any],
    occurrence: dict[str, Any],
    cfg: DailyInteractionConstructionConfig,
) -> dict[str, Any]:
    unit_id = str(occurrence.get("interaction_unit_id"))
    current_state_change_fact = _current_state_change_fact(
        occurrence=occurrence,
        unit_id=unit_id,
    )
    probe_links = [
        _probe_link(probe)
        for probe in occurrence.get("probe_insertions", [])
        if isinstance(probe, dict)
    ]
    unit = {
        "interaction_unit_id": unit_id,
        "event_occurrence_id": occurrence.get("event_occurrence_id"),
        "persona_id": persona_id,
        "day": occurrence.get("day"),
        "day_group_id": str(day.get("day_interaction_unit_id") or f"{persona_id}_D{int(occurrence.get('day', 0)):02d}"),
        "within_day_index": occurrence.get("within_day_index", 1),
        "parallel_event_count": day.get("parallel_event_count", 1),
        "cross_occurrence_reference_allowed": cfg.cross_occurrence_reference_allowed,
        "event_line_id": occurrence.get("event_line_id"),
        "event_category_id": occurrence.get("event_category_id"),
        "event_domain": occurrence.get("event_domain"),
        "event_domain_zh": occurrence.get("event_domain_zh"),
        "event_title": occurrence.get("event_title", {}),
        "event_stage": occurrence.get("event_stage"),
        "stage_index": occurrence.get("stage_index"),
        "occurrence_index": occurrence.get("occurrence_index"),
        "occurrence_count_for_line": occurrence.get("occurrence_count_for_line"),
        "related_previous_days": occurrence.get("related_previous_days", []),
        "probe_candidate": occurrence.get("probe_candidate", False),
        "current_state_change_fact": current_state_change_fact,
        "scripted_opening": _scripted_opening(
            occurrence=occurrence,
            unit_id=unit_id,
            current_state_change_fact=current_state_change_fact,
        ),
        "constrained_followup": _constrained_followup(
            occurrence=occurrence,
            cfg=cfg,
        ),
        "scene_boundary": _scene_boundary(
            persona_ref=persona_ref,
            occurrence=occurrence,
            unit_id=unit_id,
        ),
        "probe_links": probe_links,
        "source_timeline_fields": {
            "surface_event": occurrence.get("surface_event"),
            "surface_event_zh": occurrence.get("surface_event_zh"),
            "assistant_memory_expectation": occurrence.get("assistant_memory_expectation"),
            "assistant_memory_expectation_zh": occurrence.get("assistant_memory_expectation_zh"),
            "latent_continuity": occurrence.get("latent_continuity"),
            "latent_continuity_zh": occurrence.get("latent_continuity_zh"),
            "current_state_change_fact": current_state_change_fact,
            "allowed_base_facts": occurrence.get("allowed_base_facts", []),
            "allowed_base_facts_zh": occurrence.get("allowed_base_facts_zh", []),
            "event_candidate_facts": occurrence.get("event_candidate_facts", []),
            "persona_conditioned_facts": occurrence.get("persona_conditioned_facts", []),
            "stage_delta_facts": occurrence.get("stage_delta_facts", []),
            "allowed_new_facts": occurrence.get("allowed_new_facts", []),
            "allowed_new_facts_zh": occurrence.get("allowed_new_facts_zh", []),
            "prohibited_facts": occurrence.get("prohibited_facts", []),
            "prohibited_facts_zh": occurrence.get("prohibited_facts_zh", []),
        },
    }
    return unit


def _scripted_opening(
    *,
    occurrence: dict[str, Any],
    unit_id: str,
    current_state_change_fact: dict[str, Any] | None,
) -> dict[str, Any]:
    surface_event = str(occurrence.get("surface_event") or "")
    surface_event_zh = str(occurrence.get("surface_event_zh") or surface_event)
    current_state_sentence = _current_state_user_sentence(
        occurrence=occurrence,
        current_state_change_fact=current_state_change_fact,
        locale="en",
    )
    current_state_sentence_zh = _current_state_user_sentence(
        occurrence=occurrence,
        current_state_change_fact=current_state_change_fact,
        locale="zh",
    )
    user_message = _compose_opening_with_current_state(
        surface_event=surface_event,
        current_state_sentence=current_state_sentence,
        current_state_change_fact=current_state_change_fact,
        locale="en",
    )
    user_message_zh = _compose_opening_with_current_state(
        surface_event=surface_event_zh,
        current_state_sentence=current_state_sentence_zh,
        current_state_change_fact=current_state_change_fact,
        locale="zh",
    )
    return {
        "message_id": unit_id,
        "turn_type": "scripted_opening",
        "user_message": user_message,
        "user_message_zh": user_message_zh,
        "canonical_surface_event": surface_event,
        "surface_event_zh": surface_event_zh,
        "current_state_change_fact_id": (
            current_state_change_fact.get("fact_id") if current_state_change_fact else None
        ),
        "current_state_change_user_message": current_state_sentence,
        "current_state_change_user_message_zh": current_state_sentence_zh,
        "topic": _event_title(occurrence),
        "topic_zh": _event_title_zh(occurrence),
        "intent": _intent_for_stage(str(occurrence.get("event_stage", ""))),
        "tone": _tone_for_stage(str(occurrence.get("event_stage", ""))),
        "conversation_goal": occurrence.get("stage_goal")
        or occurrence.get("assistant_memory_expectation")
        or "Continue around the current event node.",
        "conversation_goal_zh": occurrence.get("stage_goal_zh")
        or occurrence.get("assistant_memory_expectation_zh")
        or "围绕当前事件节点继续。",
        "introduces_current_event_state": True,
    }


def _constrained_followup(
    *,
    occurrence: dict[str, Any],
    cfg: DailyInteractionConstructionConfig,
) -> dict[str, Any]:
    stage = str(occurrence.get("event_stage", ""))
    followup_budget = cfg.followup_budget_default
    moves = _permitted_moves(stage=stage)
    allowed_fact_ids = _allowed_fact_ids(occurrence=occurrence)
    latent_concern_ids = _latent_concern_ids(occurrence=occurrence)
    return {
        "source": "timeline_occurrence_rule_template",
        "mode": "bounded_same_occurrence_followup",
        "variant_mode": "controlled_user_replay",
        "followup_budget": followup_budget,
        "permitted_conversational_moves": moves,
        "reveal_steps": _reveal_steps(
            followup_budget=followup_budget,
            allowed_fact_ids=allowed_fact_ids,
            latent_concern_ids=latent_concern_ids,
            moves=moves,
        ),
        "stop_conditions": [
            "Stop expanding once the assistant gives one concrete, low-risk, executable next step.",
            "Stop expanding when the follow-up budget is reached.",
            "Stop expanding when continuing would require facts outside the timeline.",
        ],
        "stop_conditions_zh": [
            "当助手已经给出一个具体、低风险、可执行的下一步时停止扩展。",
            "当追问轮次已触达预算上限时停止扩展。",
            "当需要新增时间线之外的事实才能继续时停止扩展。",
        ],
        "must_not_introduce": _must_not_introduce(occurrence),
        "must_not_introduce_zh": _must_not_introduce_zh(occurrence),
        "strict_scene_boundary": True,
    }


def _scene_boundary(
    *,
    persona_ref: dict[str, Any],
    occurrence: dict[str, Any],
    unit_id: str,
) -> dict[str, Any]:
    allowed_facts = _allowed_facts(persona_ref=persona_ref, occurrence=occurrence, unit_id=unit_id)
    latent_concerns = _latent_concerns(occurrence=occurrence, unit_id=unit_id)
    return {
        "source": "timeline_occurrence_and_persona_ref",
        "boundary_id": f"{unit_id}_BOUNDARY",
        "allowed_facts": allowed_facts,
        "allowed_fact_ids": [str(item["fact_id"]) for item in allowed_facts],
        "latent_concerns": latent_concerns,
        "latent_concern_ids": [str(item["concern_id"]) for item in latent_concerns],
        "memory_level_rules": {
            "M0": "只能使用普通对话记忆和当前脚本开场，不可读取人工关系轨迹标签。",
            "M1": "可使用稳定关系偏好或熟悉回应规范的结论级记忆。",
            "M2": "可使用本事件线的摘要、跨天进展和前序处理策略。",
            "M3": "可使用具体场景锚点、共享措辞和边界敏感细节。",
        },
        "audit_dimensions": [
            "allowed_fact_boundary",
            "continuity_sensitive_response",
            "no_unprovided_detail",
            "parallel_event_isolation",
            "probe_read_only_boundary",
        ],
        "stable_detail_ids": [
            str(item["fact_id"])
            for item in allowed_facts
            if str(item.get("type", "")).startswith("persona_")
        ],
        "event_detail_ids": [
            str(item["fact_id"])
            for item in allowed_facts
            if not str(item.get("type", "")).startswith("persona_")
        ],
        "latent_concern_detail_ids": [str(item["concern_id"]) for item in latent_concerns],
        "strict_scene_boundary": True,
    }


def _allowed_facts(
    *,
    persona_ref: dict[str, Any],
    occurrence: dict[str, Any],
    unit_id: str,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    current_state_change_fact = _current_state_change_fact(
        occurrence=occurrence,
        unit_id=unit_id,
    )
    if current_state_change_fact:
        facts.append(current_state_change_fact)
    base_facts = [
        ("event_title", _event_title(occurrence), _event_title_zh(occurrence)),
        (
            "event_summary",
            occurrence.get("persistent_event_summary"),
            occurrence.get("persistent_event_summary_zh"),
        ),
        (
            "event_stage",
            str(occurrence.get("event_stage", "")),
            _stage_label_zh(str(occurrence.get("event_stage", ""))),
        ),
        ("stage_goal", occurrence.get("stage_goal"), occurrence.get("stage_goal_zh")),
        (
            "assistant_memory_expectation",
            occurrence.get("assistant_memory_expectation"),
            occurrence.get("assistant_memory_expectation_zh"),
        ),
    ]
    for fact_type, text, text_zh in base_facts:
        if not text:
            continue
        facts.append(
            {
                "fact_id": f"{unit_id}:{fact_type}",
                "type": fact_type,
                "text": str(text),
                "text_zh": str(text_zh or zh_text(text)),
                "source": "timeline_occurrence",
            }
        )
    for index, record in enumerate(_structured_fact_records(occurrence.get("stage_delta_facts", [])), start=1):
        facts.append(
            {
                "fact_id": f"{unit_id}:stage_delta_fact_{index}",
                "type": "stage_delta_fact",
                "text": record["text"],
                "text_zh": record.get("text_zh") or zh_text(record["text"]),
                "source": "event_line_stage_delta",
            }
        )
    persona_fields = {
        "source_archetype": persona_ref.get("source_archetype"),
        "source_archetype_label": persona_ref.get("source_archetype_label"),
        "occupation": persona_ref.get("occupation"),
        "family_structure": persona_ref.get("family_structure"),
        "primary_life_domains": persona_ref.get("primary_life_domains"),
    }
    for key, value in persona_fields.items():
        if value in (None, "", [], {}):
            continue
        text = value
        if isinstance(text, list):
            text = ", ".join(str(item) for item in text)
        text_zh = zh_value(value)
        if isinstance(text_zh, list):
            text_zh = "、".join(str(item) for item in text_zh)
        facts.append(
            {
                "fact_id": f"{unit_id}:persona_{key}",
                "type": f"persona_{key}",
                "text": str(text),
                "text_zh": str(text_zh),
                "source": "persona_ref",
            }
        )
    structured_sources = [
        ("allowed_base_facts", "allowed_base_fact", "event_line_base"),
        ("event_candidate_facts", "event_candidate_fact", "event_category_pool"),
        (
            "persona_conditioned_facts",
            "persona_conditioned_fact",
            "persona_event_conditioning",
        ),
    ]
    for field_name, fact_type, source in structured_sources:
        records = _structured_fact_records(occurrence.get(field_name, []))
        aligned_zh = occurrence.get(f"{field_name}_zh", [])
        for index, record in enumerate(records, start=1):
            text_zh = record.get("text_zh")
            if not text_zh and isinstance(aligned_zh, list) and index - 1 < len(aligned_zh):
                text_zh = str(aligned_zh[index - 1] or "")
            facts.append(
                {
                    "fact_id": f"{unit_id}:{fact_type}_{index}",
                    "type": fact_type,
                    "text": record["text"],
                    "text_zh": text_zh or zh_text(record["text"]),
                    "source": source,
                }
            )
    allowed_new_facts = occurrence.get("allowed_new_facts", [])
    allowed_new_facts_zh = occurrence.get("allowed_new_facts_zh", [])
    for index, text in enumerate(allowed_new_facts, start=1):
        if not text:
            continue
        text_zh = ""
        if isinstance(allowed_new_facts_zh, list) and index - 1 < len(allowed_new_facts_zh):
            text_zh = str(allowed_new_facts_zh[index - 1] or "")
        facts.append(
            {
                "fact_id": f"{unit_id}:allowed_new_fact_{index}",
                "type": "allowed_new_fact",
                "text": str(text),
                "text_zh": text_zh or zh_text(text),
                "source": "event_line_stage",
            }
        )
    previous_days = occurrence.get("related_previous_days", [])
    if previous_days:
        facts.append(
            {
                "fact_id": f"{unit_id}:related_previous_days",
                "type": "event_history_pointer",
                "text": "Previous days for this event line: " + ", ".join(
                    f"day {int(day)}" for day in previous_days
                ),
                "text_zh": "该事件线前序出现日：" + "、".join(
                    f"第 {int(day)} 天" for day in previous_days
                ),
                "source": "timeline_occurrence",
            }
        )
    return facts


def _structured_fact_texts(value: Any) -> list[str]:
    return [item["text"] for item in _structured_fact_records(value)]


def _structured_fact_records(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            text_zh = str(item.get("text_zh") or "").strip()
        else:
            text = str(item or "").strip()
            text_zh = ""
        if not text or text in seen:
            continue
        seen.add(text)
        records.append({"text": text, "text_zh": text_zh})
    return records


def _current_state_change_fact(
    *,
    occurrence: dict[str, Any],
    unit_id: str,
) -> dict[str, Any] | None:
    stage_delta_facts = occurrence.get("stage_delta_facts", [])
    stage_delta_records = _structured_fact_records(stage_delta_facts)
    if stage_delta_records:
        source_fields = _source_fields(stage_delta_facts[0])
        supporting_fact_ids = [
            f"{unit_id}:stage_delta_fact_{index}"
            for index, _ in enumerate(stage_delta_records, start=1)
        ]
        first_record = stage_delta_records[0]
        return {
            "fact_id": f"{unit_id}:current_state_change_fact",
            "type": "current_state_change_fact",
            "text": first_record["text"],
            "text_zh": first_record.get("text_zh") or zh_text(first_record["text"]),
            "source": "event_line_stage_delta",
            "source_fields": source_fields,
            "supporting_fact_ids": supporting_fact_ids,
        }
    stage_goal = str(occurrence.get("stage_goal") or "").strip()
    if not stage_goal:
        return None
    return {
        "fact_id": f"{unit_id}:current_state_change_fact",
        "type": "current_state_change_fact",
        "text": stage_goal,
        "text_zh": str(occurrence.get("stage_goal_zh") or zh_text(stage_goal)),
        "source": "timeline_occurrence",
        "source_fields": ["stage_goal"],
        "supporting_fact_ids": [f"{unit_id}:stage_goal"],
    }


def _source_fields(value: Any) -> list[str]:
    if isinstance(value, dict):
        fields = value.get("source_fields", [])
        if isinstance(fields, list):
            return [str(item) for item in fields if item not in (None, "")]
    return []


def _current_state_user_sentence(
    *,
    occurrence: dict[str, Any],
    current_state_change_fact: dict[str, Any] | None,
    locale: str,
) -> str:
    if not current_state_change_fact:
        return ""
    text = str(
        current_state_change_fact.get("text_zh" if locale == "zh" else "text")
        or current_state_change_fact.get("text")
        or ""
    )
    stage = str(occurrence.get("event_stage") or "")
    quoted = _quoted_terms(text)
    key_detail = quoted[-1] if quoted else ""
    if locale != "zh":
        if stage == "initial" and key_detail:
            return f'Right now I am most unsure about "{key_detail}".'
        if stage == "recurrence" and key_detail:
            return f'This time the issue has shifted toward "{key_detail}", so I do not want to restart from scratch.'
        if stage == "turning_point" and key_detail:
            return f'The new point is "{key_detail}", so I want to reprioritize.'
        if stage == "partial_resolution" and key_detail:
            return f'I have made partial progress and now need to confirm "{key_detail}".'
        if stage == "reflection":
            return "I want to turn the earlier handling sequence into a method I can reuse later."
        stripped = _strip_stage_prefix(text)
        return f"The key change this time is: {stripped}"
    if stage == "initial" and key_detail:
        return f"我现在最卡的是「{key_detail}」。"
    if stage == "recurrence" and key_detail:
        return f"这次主要变成了「{key_detail}」，不是从头开始。"
    if stage == "turning_point" and key_detail:
        return f"这次新的点是「{key_detail}」，所以我想重新排一下优先级。"
    if stage == "partial_resolution" and key_detail:
        return f"我已经推进了一部分，现在想确认「{key_detail}」。"
    if stage == "reflection":
        return "我想把前面处理过的顺序整理成之后还能复用的方法。"
    stripped = _strip_stage_prefix(text)
    return f"这次的关键变化是：{stripped}"


_QUOTED_TERM_RE = re.compile(r"「([^」]+)」|\"([^\"]+)\"")


def _quoted_terms(text: str) -> list[str]:
    terms: list[str] = []
    for zh_term, quoted_term in _QUOTED_TERM_RE.findall(text):
        term = (zh_term or quoted_term).strip()
        if term:
            terms.append(term)
    return terms


def _strip_stage_prefix(text: str) -> str:
    stripped = re.sub(r"^第\s*\d+\s*阶段新增[:：]\s*", "", text).strip()
    return re.sub(r"^Stage\s+\d+\s+adds:\s*", "", stripped).strip()


def _compose_opening_with_current_state(
    *,
    surface_event: str,
    current_state_sentence: str,
    current_state_change_fact: dict[str, Any] | None,
    locale: str,
) -> str:
    surface = surface_event.strip()
    if not current_state_sentence:
        return surface
    text = str(
        current_state_change_fact.get("text_zh" if locale == "zh" else "text")
        if current_state_change_fact
        else ""
    )
    quoted = _quoted_terms(text)
    if any(item and item in surface for item in quoted):
        return surface
    if not surface:
        return current_state_sentence
    return f"{surface} {current_state_sentence}"


def _latent_concerns(*, occurrence: dict[str, Any], unit_id: str) -> list[dict[str, Any]]:
    concerns = []
    stage_goal = str(occurrence.get("stage_goal") or "")
    if stage_goal:
        concerns.append(
            {
                "concern_id": f"{unit_id}:latent_stage_goal",
                "source": "stage_goal",
                "max_memory_level": "M3_candidate",
                "text": stage_goal,
                "text_zh": str(occurrence.get("stage_goal_zh") or zh_text(stage_goal)),
            }
        )
    continuity = str(occurrence.get("latent_continuity") or "")
    if continuity and continuity != stage_goal:
        concerns.append(
            {
                "concern_id": f"{unit_id}:latent_continuity",
                "source": "assistant_memory_expectation",
                "max_memory_level": "M3_candidate",
                "text": continuity,
                "text_zh": str(occurrence.get("latent_continuity_zh") or zh_text(continuity)),
            }
        )
    if int(occurrence.get("occurrence_index", 0)) >= 2:
        concerns.append(
            {
                "concern_id": f"{unit_id}:latent_no_restart",
                "source": "occurrence_index",
                "max_memory_level": "M2_candidate",
                "text": "The user expects the assistant to continue the prior event line rather than asking for a full restart.",
                "text_zh": "用户期待助手承接前序事件线，而不是要求用户从头解释。",
            }
        )
    return concerns


def _reveal_steps(
    *,
    followup_budget: int,
    allowed_fact_ids: list[str],
    latent_concern_ids: list[str],
    moves: list[dict[str, str]],
) -> list[dict[str, Any]]:
    move_ids = [move["move_id"] for move in moves]
    steps = []
    for index in range(1, followup_budget + 1):
        if index == 1:
            instruction = "Respond to the assistant's direction, reveal at most one allowed fact, and do not expand into a new event."
            instruction_zh = "回应助手的方向，最多补充一个已允许事实，不扩展新事件。"
        else:
            instruction = "Go one level deeper within the same occurrence, reveal at most one latent concern, then close."
            instruction_zh = "在同一事件出现内加深一层，最多透露一个隐含担心，然后收束。"
        steps.append(
            {
                "followup_index": index,
                "preferred_moves": move_ids,
                "may_reveal_fact_ids": allowed_fact_ids[: index + 2],
                "may_reveal_concern_ids": latent_concern_ids[: max(0, index - 1)],
                "instruction": instruction,
                "instruction_zh": instruction_zh,
            }
        )
    return steps


def _permitted_moves(*, stage: str) -> list[dict[str, str]]:
    common = [
        {
            "move_id": "clarify_current_constraint",
            "description": "Clarify the current constraint or uncertainty without introducing a new event.",
            "description_zh": "补充当前约束或不确定点，但不引入新事件。",
        },
        {
            "move_id": "ask_for_small_next_step",
            "description": "Ask the assistant to narrow the response to one low-risk next step.",
            "description_zh": "要求助手收束到一个低风险下一步。",
        },
    ]
    stage_moves = {
        "initial": [
            {
                "move_id": "name_initial_uncertainty",
                "description": "Name the judgment point that blocks the user when first raising this event.",
                "description_zh": "说明第一次提出这件事时最卡住的判断点。",
            }
        ],
        "recurrence": [
            {
                "move_id": "refer_to_prior_context",
                "description": "Signal that the user does not want to restart and expects continuity.",
                "description_zh": "表达不想从头解释，希望助手接上前序。",
            }
        ],
        "turning_point": [
            {
                "move_id": "reassess_state_change",
                "description": "Point out that the current state differs from the initial state and ask to recalibrate priority.",
                "description_zh": "指出当前状态和最初不同，要求重新校准优先级。",
            }
        ],
        "partial_resolution": [
            {
                "move_id": "check_remaining_gap",
                "description": "State that part has been handled and ask whether any obvious gap remains.",
                "description_zh": "说明已经处理一部分，询问还有没有明显漏项。",
            }
        ],
        "reflection": [
            {
                "move_id": "extract_reusable_pattern",
                "description": "Review the line and ask for a reusable handling pattern.",
                "description_zh": "回看这条线，要求总结下次可复用的处理方式。",
            }
        ],
    }
    return [*stage_moves.get(stage, []), *common]


def _must_not_introduce(occurrence: dict[str, Any]) -> list[str]:
    return [
        *[str(item) for item in occurrence.get("prohibited_facts", []) if item],
        "Do not introduce a new major life event outside the current event_occurrence.",
        "Do not automatically mix facts from other occurrences on the same day into this interaction unit.",
        "Do not add real names, precise addresses, exact income, medical diagnoses, or legal conclusions.",
        "Do not convert the assistant's guesses into user facts.",
    ]


def _must_not_introduce_zh(occurrence: dict[str, Any]) -> list[str]:
    configured = occurrence.get("prohibited_facts_zh", occurrence.get("prohibited_facts", []))
    return [
        *[zh_text(item) for item in configured if item],
        "不能引入当前 event_occurrence 之外的新重大生活事件。",
        "不能把同一天其他 occurrence 的事实自动混入本互动单元。",
        "不能新增真实姓名、精确地址、精确收入、医学诊断或法律结论。",
        "不能把助手的猜测转写成用户事实。",
    ]


def _allowed_fact_ids(*, occurrence: dict[str, Any]) -> list[str]:
    unit_id = str(occurrence.get("interaction_unit_id", ""))
    ids = []
    if _current_state_change_fact(occurrence=occurrence, unit_id=unit_id):
        ids.append(f"{unit_id}:current_state_change_fact")
    ids.extend(
        f"{unit_id}:stage_delta_fact_{index}"
        for index, _ in enumerate(_structured_fact_texts(occurrence.get("stage_delta_facts", [])), start=1)
    )
    ids.extend(
        [
        f"{unit_id}:event_title",
        f"{unit_id}:event_summary",
        f"{unit_id}:event_stage",
        f"{unit_id}:stage_goal",
        ]
    )
    structured_sources = [
        ("allowed_base_facts", "allowed_base_fact"),
        ("event_candidate_facts", "event_candidate_fact"),
        ("persona_conditioned_facts", "persona_conditioned_fact"),
    ]
    for field_name, fact_type in structured_sources:
        ids.extend(
            f"{unit_id}:{fact_type}_{index}"
            for index, _ in enumerate(_structured_fact_texts(occurrence.get(field_name, [])), start=1)
        )
    ids.extend(
        f"{unit_id}:allowed_new_fact_{index}"
        for index, _ in enumerate(occurrence.get("allowed_new_facts", []), start=1)
    )
    if occurrence.get("related_previous_days"):
        ids.append(f"{unit_id}:related_previous_days")
    return ids


def _latent_concern_ids(*, occurrence: dict[str, Any]) -> list[str]:
    unit_id = str(occurrence.get("interaction_unit_id", ""))
    ids = []
    if occurrence.get("stage_goal"):
        ids.append(f"{unit_id}:latent_stage_goal")
    if occurrence.get("latent_continuity") and occurrence.get("latent_continuity") != occurrence.get("stage_goal"):
        ids.append(f"{unit_id}:latent_continuity")
    if int(occurrence.get("occurrence_index", 0)) >= 2:
        ids.append(f"{unit_id}:latent_no_restart")
    return ids


def _probe_link(probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe_id": probe.get("probe_id"),
        "probe_type": probe.get("probe_type"),
        "paper_probe_id": probe.get("paper_probe_id"),
        "paper_probe_type": probe.get("paper_probe_type"),
        "paper_probe_zh": probe.get("paper_probe_zh"),
        "primary_dimension_id": probe.get("primary_dimension_id"),
        "primary_dimension": probe.get("primary_dimension"),
        "secondary_dimension_ids": probe.get("secondary_dimension_ids", []),
        "evaluation_dimension_ids": probe.get("evaluation_dimension_ids", []),
        "event_occurrence_id": probe.get("event_occurrence_id"),
        "insert_after_message_id": probe.get("insert_after_message_id"),
        "question": probe.get("question"),
        "read_only": True,
    }


def _message_binding(
    *,
    persona_id: str,
    unit: dict[str, Any],
    message_id: str,
    turn_type: str,
    probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding = {
        "schema_version": "daily_interaction_binding_v0.1",
        "persona_id": persona_id,
        "message_id": message_id,
        "turn_type": turn_type,
        "interaction_unit_id": unit.get("interaction_unit_id"),
        "event_occurrence_id": unit.get("event_occurrence_id"),
        "day": unit.get("day"),
        "day_group_id": unit.get("day_group_id"),
        "event_line_id": unit.get("event_line_id"),
        "event_category_id": unit.get("event_category_id"),
        "event_stage": unit.get("event_stage"),
    }
    if probe:
        binding["probe_id"] = probe.get("probe_id")
        binding["probe_type"] = probe.get("probe_type")
        binding["paper_probe_id"] = probe.get("paper_probe_id")
    return binding


def _validate_unit_contract(*, unit: dict[str, Any], issues: list[str]) -> None:
    unit_id = unit.get("interaction_unit_id")
    opening = unit.get("scripted_opening", {})
    followup = unit.get("constrained_followup", {})
    boundary = unit.get("scene_boundary", {})
    if not isinstance(opening, dict) or not opening.get("user_message"):
        issues.append(f"{unit_id} missing scripted opening user_message.")
    if not isinstance(followup, dict):
        issues.append(f"{unit_id} missing constrained_followup.")
    else:
        if "followup_budget" not in followup:
            issues.append(f"{unit_id} missing followup_budget.")
        if not followup.get("permitted_conversational_moves"):
            issues.append(f"{unit_id} missing permitted moves.")
        if not followup.get("reveal_steps"):
            issues.append(f"{unit_id} missing reveal_steps.")
        if not followup.get("must_not_introduce"):
            issues.append(f"{unit_id} missing must_not_introduce.")
    if not isinstance(boundary, dict) or not boundary.get("allowed_facts"):
        issues.append(f"{unit_id} missing scene allowed_facts.")
    if isinstance(boundary, dict) and not boundary.get("latent_concerns"):
        issues.append(f"{unit_id} missing latent_concerns.")


def _day_event_occurrences(day: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = [
        item for item in day.get("event_occurrences", []) if isinstance(item, dict)
    ]
    if occurrences:
        return occurrences
    if day.get("active"):
        return [day]
    return []


def _event_title(occurrence: dict[str, Any]) -> str:
    title = occurrence.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("source") or title.get("zh") or occurrence.get("event_category_id", ""))
    return str(title or occurrence.get("event_category_id", ""))


def _event_title_zh(occurrence: dict[str, Any]) -> str:
    title = occurrence.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or occurrence.get("event_category_id", ""))
    return str(title or occurrence.get("event_category_id", ""))


def _stage_label_zh(stage: str) -> str:
    return {
        "initial": "初始提出",
        "recurrence": "再次出现",
        "turning_point": "转折判断",
        "partial_resolution": "部分处理",
        "reflection": "回看总结",
    }.get(stage, zh_text(stage))


def _intent_for_stage(stage: str) -> str:
    return {
        "initial": "introduce_current_concern",
        "recurrence": "continue_recurring_event_line",
        "turning_point": "reassess_state_change",
        "partial_resolution": "check_remaining_gap",
        "reflection": "extract_reusable_pattern",
    }.get(stage, "continue_event_line")


def _tone_for_stage(stage: str) -> str:
    return {
        "initial": "uncertain_private",
        "recurrence": "expects_continuity",
        "turning_point": "recalibrating",
        "partial_resolution": "cautiously_checking",
        "reflection": "reflective",
    }.get(stage, "private_chat_natural")


def _summarize_personas(personas: list[dict[str, Any]]) -> dict[str, Any]:
    unit_counts = [int(persona.get("interaction_unit_count", 0)) for persona in personas]
    active_day_counts = [int(persona.get("active_day_count", 0)) for persona in personas]
    parallel_day_counts = [int(persona.get("parallel_day_count", 0)) for persona in personas]
    stage_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    probe_link_count = 0
    calendar_day_count = 0
    for persona in personas:
        for day in persona.get("days", []):
            if isinstance(day, dict):
                calendar_day_count += 1
                for unit in day.get("interaction_units", []):
                    if isinstance(unit, dict):
                        stage_counts[str(unit.get("event_stage"))] += 1
                        domain_counts[str(unit.get("event_domain"))] += 1
                        probe_link_count += len(unit.get("probe_links", []))
    return {
        "persona_count": len(personas),
        "calendar_day_count": calendar_day_count,
        "active_day_total": sum(active_day_counts),
        "active_days_per_persona_min": min(active_day_counts or [0]),
        "active_days_per_persona_max": max(active_day_counts or [0]),
        "interaction_unit_count": sum(unit_counts),
        "interaction_units_per_persona_min": min(unit_counts or [0]),
        "interaction_units_per_persona_max": max(unit_counts or [0]),
        "parallel_day_total": sum(parallel_day_counts),
        "parallel_days_per_persona_min": min(parallel_day_counts or [0]),
        "parallel_days_per_persona_max": max(parallel_day_counts or [0]),
        "probe_link_count": probe_link_count,
        "event_stage_counts": dict(sorted(stage_counts.items())),
        "event_domain_counts": dict(sorted(domain_counts.items())),
    }
