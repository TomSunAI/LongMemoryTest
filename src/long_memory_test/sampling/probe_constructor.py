from __future__ import annotations

import copy
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProbeConstructionConfig:
    random_seed: int = 20260701
    probes_per_persona_min: int = 12
    probes_per_persona_max: int = 18
    max_probes_per_active_day: int = 1
    primary_dimension_balance_required: bool = True


DIMENSION_IDS = ["D1", "D2", "D3", "D4"]

PAPER_DIMENSIONS = {
    "D1": {
        "id": "D1",
        "name": "Situated Intent Understanding",
        "zh": "情境化意图理解",
    },
    "D2": {
        "id": "D2",
        "name": "Emotional-State Attunement",
        "zh": "情绪与状态调谐",
    },
    "D3": {
        "id": "D3",
        "name": "Contextual Specificity",
        "zh": "上下文具体性",
    },
    "D4": {
        "id": "D4",
        "name": "Continuity-Sensitive Response",
        "zh": "连续性敏感回应",
    },
}

PAPER_PROBE_TYPES = {
    "current_understanding": {
        "id": "P1",
        "name": "Current Understanding",
        "zh": "当前理解",
    },
    "state_transformation": {
        "id": "P2",
        "name": "State Transformation",
        "zh": "状态变化识别",
    },
    "memory_invocation": {
        "id": "P3",
        "name": "Memory Invocation",
        "zh": "共享记忆调用",
    },
    "natural_detail": {
        "id": "P4",
        "name": "Natural Detail Use",
        "zh": "自然细节使用",
    },
    "relational_boundary": {
        "id": "P5",
        "name": "Relational Boundary",
        "zh": "关系边界",
    },
    "alienation_avoidance": {
        "id": "P6",
        "name": "Alienation Avoidance",
        "zh": "陌生化避免",
    },
}

PROBE_TYPE_EVALUATION_DIMENSIONS = {
    "current_understanding": ["D1", "D2"],
    "memory_invocation": ["D4", "D3"],
    "state_transformation": ["D2", "D4"],
    "relational_boundary": ["D4", "D1"],
    "alienation_avoidance": ["D4", "D2"],
    "natural_detail": ["D3", "D2"],
}

PRIMARY_DIMENSION_DEFAULT_PROBE_TYPE = {
    "D1": "current_understanding",
    "D2": "state_transformation",
    "D3": "natural_detail",
    "D4": "memory_invocation",
}

PRIMARY_DIMENSION_SECONDARY = {
    "D1": ["D2", "D4"],
    "D2": ["D4", "D1"],
    "D3": ["D2", "D4"],
    "D4": ["D3", "D2"],
}

PROBE_TYPE_DIAGNOSTIC_DIMENSIONS = {
    "current_understanding": [
        "hidden_intent_recognition",
        "emotional_state_recognition",
        "relationship_expectation_recognition",
    ],
    "memory_invocation": [
        "shared_context_invocation",
        "relationship_expectation_recognition",
        "hidden_intent_recognition",
        "memory_misuse",
    ],
    "state_transformation": [
        "hidden_intent_recognition",
        "emotional_state_recognition",
        "shared_context_invocation",
    ],
    "relational_boundary": [
        "hidden_intent_recognition",
        "relationship_expectation_recognition",
        "alienation_error_rate",
        "memory_misuse",
    ],
    "alienation_avoidance": [
        "relationship_expectation_recognition",
        "alienation_error_rate",
        "shared_context_invocation",
        "memory_misuse",
    ],
    "natural_detail": [
        "natural_detail_use",
        "emotional_state_recognition",
        "hidden_intent_recognition",
        "memory_misuse",
    ],
}

# Backward-compatible alias for existing evaluators that consume old ToM labels.
PROBE_TYPE_DIMENSIONS = PROBE_TYPE_DIAGNOSTIC_DIMENSIONS

PROBE_TYPE_REQUIRED_MEMORY = {
    "current_understanding": ["relational_anchor", "summary_memory"],
    "memory_invocation": ["event_memory", "relational_anchor"],
    "state_transformation": ["summary_memory", "event_memory", "relational_anchor"],
    "relational_boundary": ["relational_anchor", "response_boundary"],
    "alienation_avoidance": ["relational_anchor", "response_boundary", "event_memory"],
    "natural_detail": ["event_memory", "relational_anchor"],
}


def construct_probe_plan_for_timeline(
    *,
    timeline_batch: dict[str, Any],
    config: ProbeConstructionConfig | None = None,
) -> dict[str, Any]:
    cfg = config or ProbeConstructionConfig()
    rng = random.Random(cfg.random_seed)
    timeline_with_probes = copy.deepcopy(timeline_batch)
    probe_questions: list[dict[str, Any]] = []
    issues: list[str] = []
    warnings: list[str] = []

    for persona_timeline in timeline_with_probes.get("timelines", []):
        if not isinstance(persona_timeline, dict):
            issues.append("Invalid persona timeline entry.")
            continue
        selected_slots = _select_probe_days(
            persona_timeline=persona_timeline,
            cfg=cfg,
            rng=rng,
        )
        persona_id = str(persona_timeline.get("persona_id", ""))
        _assign_primary_dimensions(selected_slots, persona_id=persona_id)
        if len(selected_slots) < cfg.probes_per_persona_min:
            issues.append(
                f"{persona_id} has only {len(selected_slots)} probe candidates; "
                f"expected at least {cfg.probes_per_persona_min}."
            )
        if len(selected_slots) > cfg.probes_per_persona_max:
            warnings.append(
                f"{persona_id} has {len(selected_slots)} selected probes; capped range is "
                f"{cfg.probes_per_persona_min}-{cfg.probes_per_persona_max}."
            )
        per_day_counts: defaultdict[int, int] = defaultdict(int)
        selected_by_day: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        for slot in selected_slots:
            selected_by_day[int(slot.get("day", 0))].append(slot)
        for day in persona_timeline.get("days", []):
            if not isinstance(day, dict) or not day.get("active"):
                continue
            day["probe_ids"] = []
            day["probe_insertions"] = []
            for occurrence in _day_event_occurrences(day):
                if occurrence is not day:
                    occurrence["probe_ids"] = []
                    occurrence["probe_insertions"] = []
            for slot in selected_by_day.get(int(day.get("day", 0)), []):
                occurrence = slot.get("_occurrence_ref")
                if not isinstance(occurrence, dict):
                    occurrence = day
                per_day_counts[int(day["day"])] += 1
                probe = _build_probe(
                    day=slot,
                    day_probe_index=per_day_counts[int(day["day"])],
                )
                insertion = {
                    "probe_id": probe["probe_id"],
                    "probe_type": probe["probe_type"],
                    "paper_probe_id": probe["paper_probe_id"],
                    "paper_probe_type": probe["paper_probe_type"],
                    "paper_probe_zh": probe["paper_probe_zh"],
                    "primary_dimension_id": probe["primary_dimension_id"],
                    "primary_dimension": probe["primary_dimension"],
                    "secondary_dimension_ids": probe["secondary_dimension_ids"],
                    "evaluation_dimension_ids": probe["evaluation_dimension_ids"],
                    "event_occurrence_id": probe.get("event_occurrence_id"),
                    "insert_after_message_id": probe.get("insert_after_message_id"),
                    "question": probe["question"],
                }
                day["probe_ids"].append(probe["probe_id"])
                day["probe_insertions"].append(insertion)
                if occurrence is not day:
                    occurrence.setdefault("probe_ids", []).append(probe["probe_id"])
                    occurrence.setdefault("probe_insertions", []).append(insertion)
                probe_questions.append(probe)

    timeline_with_probes.setdefault("construction_scope", {})["probe_plan_constructed"] = True
    timeline_with_probes["probe_plan_ref"] = {
        "schema_version": "probe_plan_batch_v0.1",
        "probe_count": len(probe_questions),
    }
    timeline_with_probes["summary"] = {
        **timeline_with_probes.get("summary", {}),
        **_probe_summary_fields(probe_questions),
    }
    probe_plan = {
        "schema_version": "probe_plan_batch_v0.1",
        "sampling_stage": "P2_probe_plan_construction",
        "construction_scope": {
            "from_timeline": True,
            "inserted_into_timeline": True,
            "probe_writeback_allowed": False,
        },
        "construction_config": asdict(cfg),
        "insert_position": "after_active_day_interaction",
        "probe_questions": probe_questions,
        "summary": _summarize_probe_questions(probe_questions),
    }
    validation = validate_probe_plan(
        probe_plan=probe_plan,
        timeline_with_probes=timeline_with_probes,
        config=cfg,
    )
    validation["issues"] = [*issues, *validation["issues"]]
    validation["warnings"] = [*warnings, *validation["warnings"]]
    validation["status"] = "pass" if not validation["issues"] else "fail"
    probe_plan["validation"] = validation
    timeline_with_probes["probe_validation"] = validation
    return {
        "probe_plan": probe_plan,
        "timeline_with_probes": timeline_with_probes,
    }


def validate_probe_plan(
    *,
    probe_plan: dict[str, Any],
    timeline_with_probes: dict[str, Any],
    config: ProbeConstructionConfig,
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    probes = [
        item for item in probe_plan.get("probe_questions", []) if isinstance(item, dict)
    ]
    probe_ids = [str(probe.get("probe_id")) for probe in probes]
    duplicate_ids = sorted(
        probe_id for probe_id, count in Counter(probe_ids).items() if count > 1
    )
    if duplicate_ids:
        issues.append(f"Duplicate probe IDs: {duplicate_ids}")

    active_units: dict[str, dict[str, Any]] = {}
    timeline_probe_ids: set[str] = set()
    per_persona_counts: Counter[str] = Counter()
    primary_dimension_counts_by_persona: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for persona_timeline in timeline_with_probes.get("timelines", []):
        if not isinstance(persona_timeline, dict):
            continue
        for day in persona_timeline.get("days", []):
            if not isinstance(day, dict) or not day.get("active"):
                continue
            day_probe_ids = [str(probe_id) for probe_id in day.get("probe_ids", [])]
            timeline_probe_ids.update(day_probe_ids)
            if len(day_probe_ids) > config.max_probes_per_active_day:
                issues.append(
                    f"{persona_timeline.get('persona_id')} day {day.get('day')} has "
                    f"{len(day_probe_ids)} probes; expected at most {config.max_probes_per_active_day}."
                )
            for occurrence in _day_event_occurrences(day):
                unit_id = str(occurrence.get("interaction_unit_id") or day.get("interaction_unit_id"))
                slot = _probe_slot(day=day, occurrence=occurrence)
                active_units[unit_id] = slot
                timeline_probe_ids.update(
                    str(probe_id) for probe_id in occurrence.get("probe_ids", [])
                )

    for probe in probes:
        persona_id = str(probe.get("persona_id"))
        per_persona_counts[persona_id] += 1
        primary_dimension_id = str(probe.get("primary_dimension_id", ""))
        if primary_dimension_id not in PAPER_DIMENSIONS:
            issues.append(f"Probe {probe.get('probe_id')} has invalid primary_dimension_id.")
        else:
            primary_dimension_counts_by_persona[persona_id][primary_dimension_id] += 1
            dimension_ids = [str(item) for item in probe.get("evaluation_dimension_ids", [])]
            if not dimension_ids or dimension_ids[0] != primary_dimension_id:
                issues.append(
                    f"Probe {probe.get('probe_id')} does not place primary dimension first."
                )
        insert_after = str(probe.get("insert_after_message_id"))
        slot = active_units.get(insert_after)
        if slot is None:
            issues.append(f"Probe {probe.get('probe_id')} references missing active occurrence.")
            continue
        if slot.get("event_stage") == "initial":
            issues.append(f"Probe {probe.get('probe_id')} was inserted into an initial stage.")
        if str(probe.get("event_line_id")) != str(slot.get("event_line_id")):
            issues.append(f"Probe {probe.get('probe_id')} event_line_id mismatch.")
        if str(probe.get("probe_id")) not in timeline_probe_ids:
            issues.append(f"Probe {probe.get('probe_id')} is not inserted into timeline.")

    for persona_timeline in timeline_with_probes.get("timelines", []):
        if not isinstance(persona_timeline, dict):
            continue
        persona_id = str(persona_timeline.get("persona_id"))
        count = per_persona_counts[persona_id]
        if count < config.probes_per_persona_min or count > config.probes_per_persona_max:
            issues.append(
                f"{persona_id} has {count} probes; expected "
                f"{config.probes_per_persona_min}-{config.probes_per_persona_max}."
            )
        if config.primary_dimension_balance_required and count:
            dimension_counts = [
                primary_dimension_counts_by_persona[persona_id].get(dimension_id, 0)
                for dimension_id in DIMENSION_IDS
            ]
            if max(dimension_counts) - min(dimension_counts) > 1:
                issues.append(
                    f"{persona_id} primary D coverage is imbalanced: "
                    f"{dict(primary_dimension_counts_by_persona[persona_id])}."
                )

    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
    }


def _select_probe_days(
    *,
    persona_timeline: dict[str, Any],
    cfg: ProbeConstructionConfig,
    rng: random.Random,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for day in persona_timeline.get("days", []):
        if not isinstance(day, dict) or not day.get("active"):
            continue
        for occurrence in _day_event_occurrences(day):
            if occurrence.get("probe_candidate") and occurrence.get("event_stage") != "initial":
                candidates.append(_probe_slot(day=day, occurrence=occurrence))
    candidates = sorted(
        candidates,
        key=lambda item: (int(item.get("day", 0)), int(item.get("within_day_index", 1))),
    )
    selected: list[dict[str, Any]] = []
    used_days: set[int] = set()
    required = _required_probe_days(candidates)
    for slot in required:
        day_number = int(slot.get("day", 0))
        if day_number in used_days:
            continue
        selected.append(slot)
        used_days.add(day_number)
        if len(selected) >= cfg.probes_per_persona_max:
            return sorted(
                selected,
                key=lambda item: (int(item.get("day", 0)), int(item.get("within_day_index", 1))),
            )
    selected_ids = {id(slot) for slot in selected}
    remaining = [slot for slot in candidates if id(slot) not in selected_ids]
    rng.shuffle(remaining)
    for slot in remaining:
        day_number = int(slot.get("day", 0))
        if day_number in used_days:
            continue
        selected.append(slot)
        used_days.add(day_number)
        if len(selected) >= cfg.probes_per_persona_max:
            break
    return sorted(
        selected,
        key=lambda item: (int(item.get("day", 0)), int(item.get("within_day_index", 1))),
    )


def _required_probe_days(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_line: dict[str, dict[str, Any]] = {}
    for day in candidates:
        line_id = str(day.get("event_line_id"))
        by_line.setdefault(line_id, day)
    return list(by_line.values())


def _assign_primary_dimensions(
    selected_slots: list[dict[str, Any]],
    *,
    persona_id: str,
) -> None:
    if not selected_slots:
        return
    offset = _dimension_offset_for_persona(persona_id)
    for index, slot in enumerate(selected_slots):
        slot["primary_dimension_id"] = DIMENSION_IDS[(index + offset) % len(DIMENSION_IDS)]


def _dimension_offset_for_persona(persona_id: str) -> int:
    digits = "".join(ch for ch in persona_id if ch.isdigit())
    if not digits:
        return 0
    return (int(digits) - 1) % len(DIMENSION_IDS)


def _day_event_occurrences(day: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = [
        item for item in day.get("event_occurrences", []) if isinstance(item, dict)
    ]
    if occurrences:
        return occurrences
    if day.get("active"):
        return [day]
    return []


def _probe_slot(*, day: dict[str, Any], occurrence: dict[str, Any]) -> dict[str, Any]:
    slot = dict(occurrence)
    slot["day"] = day.get("day")
    slot["day_interaction_unit_id"] = day.get("day_interaction_unit_id")
    slot["parallel_event_count"] = day.get("parallel_event_count", 1)
    slot["_day_ref"] = day
    slot["_occurrence_ref"] = occurrence
    return slot


def _build_probe(*, day: dict[str, Any], day_probe_index: int) -> dict[str, Any]:
    primary_dimension_id = str(day.get("primary_dimension_id") or "D1")
    if primary_dimension_id not in PAPER_DIMENSIONS:
        primary_dimension_id = "D1"
    probe_type = _probe_type_for_dimension(day=day, primary_dimension_id=primary_dimension_id)
    persona_id = str(day.get("persona_id"))
    day_number = int(day.get("day", 0))
    probe_id = f"{persona_id}_D{day_number:02d}_P{day_probe_index:03d}"
    question = _probe_question(
        day=day,
        probe_type=probe_type,
        primary_dimension_id=primary_dimension_id,
    )
    paper_probe = PAPER_PROBE_TYPES[probe_type]
    evaluation_dimension_ids = _evaluation_dimension_ids(
        primary_dimension_id=primary_dimension_id,
        probe_type=probe_type,
    )
    secondary_dimension_ids = [
        dimension_id for dimension_id in evaluation_dimension_ids if dimension_id != primary_dimension_id
    ]
    return {
        "probe_id": probe_id,
        "message_id": probe_id,
        "turn_type": "targeted_probe",
        "persona_id": persona_id,
        "day": day_number,
        "event_occurrence_id": day.get("event_occurrence_id"),
        "within_day_index": day.get("within_day_index", 1),
        "day_interaction_unit_id": day.get("day_interaction_unit_id"),
        "parallel_event_count": day.get("parallel_event_count", 1),
        "insert_after_message_id": day.get("interaction_unit_id"),
        "event_line_id": day.get("event_line_id"),
        "event_category_id": day.get("event_category_id"),
        "event_stage": day.get("event_stage"),
        "probe_type": probe_type,
        "paper_probe_id": paper_probe["id"],
        "paper_probe_type": paper_probe["name"],
        "paper_probe_zh": paper_probe["zh"],
        "primary_dimension_id": primary_dimension_id,
        "primary_dimension": PAPER_DIMENSIONS[primary_dimension_id],
        "secondary_dimension_ids": secondary_dimension_ids,
        "question": question,
        "user_message": question,
        "topic": _event_title(day),
        "required_memory_type": PROBE_TYPE_REQUIRED_MEMORY[probe_type],
        "evaluation_dimension_ids": evaluation_dimension_ids,
        "evaluation_dimensions": _evaluation_dimensions(evaluation_dimension_ids),
        "tom_dimensions": PROBE_TYPE_DIAGNOSTIC_DIMENSIONS[probe_type],
        "diagnostic_dimensions": PROBE_TYPE_DIAGNOSTIC_DIMENSIONS[probe_type],
        "target_detail_ids": _target_detail_ids(day),
        "ground_truth": _probe_ground_truth(
            day=day,
            probe_type=probe_type,
            primary_dimension_id=primary_dimension_id,
            evaluation_dimension_ids=evaluation_dimension_ids,
        ),
        "read_only": True,
        "writeback_policy": "probe_turn_must_not_write_to_memory",
        "tom_assessment": _tom_assessment(
            day=day,
            probe_type=probe_type,
            primary_dimension_id=primary_dimension_id,
        ),
    }


def _probe_type(day: dict[str, Any]) -> str:
    return _probe_type_for_dimension(
        day=day,
        primary_dimension_id=str(day.get("primary_dimension_id") or "D1"),
    )


def _probe_type_for_dimension(*, day: dict[str, Any], primary_dimension_id: str) -> str:
    stage = str(day.get("event_stage"))
    if primary_dimension_id == "D1":
        return "relational_boundary" if stage == "partial_resolution" else "current_understanding"
    if primary_dimension_id == "D2":
        return "alienation_avoidance" if stage == "reflection" else "state_transformation"
    if primary_dimension_id == "D3":
        return "natural_detail"
    if primary_dimension_id == "D4" and stage == "reflection":
        return "alienation_avoidance"
    if primary_dimension_id == "D4" and stage == "partial_resolution":
        return "relational_boundary"
    return PRIMARY_DIMENSION_DEFAULT_PROBE_TYPE.get(primary_dimension_id, "current_understanding")


def _probe_question(
    *,
    day: dict[str, Any],
    probe_type: str,
    primary_dimension_id: str,
) -> str:
    title = _event_title(day)
    if primary_dimension_id == "D1":
        return (
            f"围绕「{title}」，你先帮我抓住我现在真正想解决的点，"
            "不要只按表面问题给建议。"
        )
    if primary_dimension_id == "D2":
        return (
            f"这次「{title}」里我的状态和前面相比有什么变化？"
            "你先帮我校准这个变化，再说下一步。"
        )
    if primary_dimension_id == "D3":
        return (
            f"你结合「{title}」前面已经出现过的具体细节说，"
            "不要只给泛泛建议，帮我判断下一步。"
        )
    if primary_dimension_id == "D4":
        return (
            f"{title}这条线我不想从头解释了。"
            "你按前面已经聊过的，帮我判断现在最该抓住什么。"
        )
    if probe_type == "memory_invocation":
        return (
            f"{title}这条线我不想从头解释了。"
            "你按前面已经聊过的，帮我判断现在最该抓住什么。"
        )
    if probe_type == "state_transformation":
        return (
            f"我感觉「{title}」已经不是一开始那个状态了。"
            "你帮我校准一下，这个变化到底意味着什么。"
        )
    if probe_type == "relational_boundary":
        return (
            "你按我们平时那种熟一点但不夸张的方式说就行。"
            f"围绕「{title}」继续讲，但不要替我编没说过的细节。"
        )
    if probe_type == "alienation_avoidance":
        return (
            "你别用像第一次认识我的那种口吻，也别把前面都机械复述。"
            f"就按我们已经聊过的「{title}」，自然接上现在这一段。"
        )
    if probe_type == "natural_detail":
        return (
            f"你结合「{title}」前面已经出现过的具体变化说，"
            "不要只给泛泛安慰，帮我判断下一步。"
        )
    return (
        f"你先别急着给建议，帮我说清楚「{title}」里"
        "我现在真正卡住的点是什么。"
    )


def _tom_assessment(
    *,
    day: dict[str, Any],
    probe_type: str,
    primary_dimension_id: str,
) -> dict[str, str]:
    title = _event_title(day)
    dimension = PAPER_DIMENSIONS[primary_dimension_id]
    return {
        "hidden_user_need": f"用户希望助手承接「{title}」的既有事件线，而不是重置成单轮咨询。",
        "high_score_behavior": "自然接上前序天和当前阶段，区分已知事实、合理推断和不能补的空白。",
        "low_score_behavior": "要求用户重讲背景、泛泛安慰、编造未给出的细节，或忽略当前事件阶段。",
        "probe_focus": probe_type,
        "primary_dimension_id": primary_dimension_id,
        "primary_dimension": f"{dimension['name']} / {dimension['zh']}",
    }


def _probe_ground_truth(
    *,
    day: dict[str, Any],
    probe_type: str,
    primary_dimension_id: str,
    evaluation_dimension_ids: list[str],
) -> dict[str, Any]:
    title = _event_title(day)
    stage = str(day.get("event_stage") or "")
    previous_days = [int(item) for item in day.get("related_previous_days", []) if item]
    allowed_base_facts_zh = [
        str(item) for item in day.get("allowed_base_facts_zh", []) if item
    ]
    stage_delta_facts = _localized_fact_texts(day.get("stage_delta_facts", []))
    persona_conditioned_facts = _localized_fact_texts(day.get("persona_conditioned_facts", []))
    expected_references = _expected_references(
        day=day,
        primary_dimension_id=primary_dimension_id,
        probe_type=probe_type,
    )
    prohibited = [
        str(item) for item in day.get("prohibited_facts_zh", []) if item
    ]
    if not prohibited:
        prohibited = [
            "不能要求用户从头重讲已经在 timeline 中出现过的背景。",
            "不能编造 timeline、persona 或 event category 之外的新事实。",
            "不能把 Probe 回答写回用户记忆。",
        ]
    return {
        "schema_version": "probe_ground_truth_v0.1",
        "source": "deterministic_from_timeline_occurrence",
        "event_line_id": day.get("event_line_id"),
        "event_occurrence_id": day.get("event_occurrence_id"),
        "interaction_unit_id": day.get("interaction_unit_id"),
        "event_title_zh": title,
        "event_stage": stage,
        "stage_index": day.get("stage_index"),
        "occurrence_index": day.get("occurrence_index"),
        "related_previous_days": previous_days,
        "primary_dimension_id": primary_dimension_id,
        "evaluation_dimension_ids": evaluation_dimension_ids,
        "probe_type": probe_type,
        "must_recognize": {
            "current_event_line": title,
            "current_stage": STAGE_EXPECTATIONS.get(stage, stage),
            "current_state_change": stage_delta_facts[:2],
            "previous_context_required": bool(previous_days),
            "previous_days": previous_days,
        },
        "must_use_or_respect": {
            "allowed_base_facts": allowed_base_facts_zh[:3],
            "persona_conditioned_facts": persona_conditioned_facts[:4],
            "assistant_memory_expectation": day.get("assistant_memory_expectation_zh")
            or day.get("assistant_memory_expectation"),
        },
        "expected_references": expected_references,
        "acceptable_response": _acceptable_response(
            title=title,
            stage=stage,
            primary_dimension_id=primary_dimension_id,
            previous_days=previous_days,
        ),
        "reference_answer_zh": _reference_answer_zh(
            title=title,
            stage=stage,
            primary_dimension_id=primary_dimension_id,
            previous_days=previous_days,
            stage_delta_facts=stage_delta_facts,
            allowed_base_facts_zh=allowed_base_facts_zh,
            persona_conditioned_facts=persona_conditioned_facts,
            assistant_memory_expectation=day.get("assistant_memory_expectation_zh")
            or day.get("assistant_memory_expectation"),
        ),
        "reference_answer_usage": (
            "供人工评审或 LLM judge 作为高分答案参照；不要求被评测回答逐字匹配，"
            "但应覆盖核心事件线、阶段变化、前序承接和禁止编造边界。"
        ),
        "failure_modes": _ground_truth_failure_modes(
            probe_type=probe_type,
            primary_dimension_id=primary_dimension_id,
            previous_days=previous_days,
        ),
        "must_not_claim": prohibited[:6],
        "scoring_rubric": {
            "2": "准确承接事件线和当前阶段，使用允许事实或前序天信息，明确区分已知事实、合理推断和不能补的空白。",
            "1": "部分承接事件线，但阶段变化、前序天或用户隐含目标识别不完整，回答仍偏泛化。",
            "0": "当作全新单轮问题处理、要求用户重讲背景、编造未给事实，或忽略 Probe 指定的评估维度。",
        },
    }


STAGE_EXPECTATIONS = {
    "initial": "第一次提出担心，说明触发点和不确定处。",
    "recurrence": "同一事件线再次出现，需要承接前序而不是重启解释。",
    "turning_point": "出现新变化，需要识别转折点并重新排序优先级。",
    "partial_resolution": "用户已做过部分处理，需要核对已完成动作和剩余风险。",
    "reflection": "回看同一事件线，需要提炼稳定处理模式而不是机械复述。",
}


def _expected_references(
    *,
    day: dict[str, Any],
    primary_dimension_id: str,
    probe_type: str,
) -> list[str]:
    refs = [
        "当前事件线标题",
        "当前阶段目标",
        "当天状态变化事实",
    ]
    if day.get("related_previous_days"):
        refs.append("前序出现天数或前序上下文")
    if primary_dimension_id == "D1":
        refs.append("用户真正想解决的隐含意图")
    if primary_dimension_id == "D2":
        refs.append("与前一次相比的状态变化")
    if primary_dimension_id == "D3":
        refs.append("具体细节而非泛泛建议")
    if primary_dimension_id == "D4" or probe_type in {"memory_invocation", "alienation_avoidance"}:
        refs.append("连续性记忆和不要求重讲背景")
    if probe_type == "relational_boundary":
        refs.append("熟悉但不过度编造的关系边界")
    return refs


def _acceptable_response(
    *,
    title: str,
    stage: str,
    primary_dimension_id: str,
    previous_days: list[int],
) -> str:
    continuity = (
        f"需要自然承接前序天 {previous_days}，不要让用户重新解释背景；"
        if previous_days
        else "可以先确认这是当前首次评测节点，不声称知道未给出的过去细节；"
    )
    dimension_goal = {
        "D1": "重点识别用户表面问题背后的真实意图。",
        "D2": "重点校准用户状态或判断压力相对前序的变化。",
        "D3": "重点引用具体事件细节，避免泛泛安慰。",
        "D4": "重点体现连续性记忆，直接接上同一事件线。",
    }.get(primary_dimension_id, "重点回答 probe 指定的评估维度。")
    stage_goal = STAGE_EXPECTATIONS.get(stage, stage)
    return f"围绕「{title}」回答；{continuity}{stage_goal}{dimension_goal}"


def _reference_answer_zh(
    *,
    title: str,
    stage: str,
    primary_dimension_id: str,
    previous_days: list[int],
    stage_delta_facts: list[str],
    allowed_base_facts_zh: list[str],
    persona_conditioned_facts: list[str],
    assistant_memory_expectation: Any,
) -> str:
    continuity = (
        f"我记得这不是第一次聊「{title}」这件事。前面第 "
        f"{'、'.join(str(day) for day in previous_days)} 天已经出现过相关背景，"
        "所以这里不用从头重讲。"
        if previous_days
        else f"我先按「{title}」这个当前节点来理解，不假装知道没有给出的过去细节。"
    )
    stage_goal = _stage_reference_sentence(stage)
    change = (
        "这次最关键的变化是：" + "；".join(_clean_sentence(item) for item in stage_delta_facts[:2]) + "。"
        if stage_delta_facts
        else f"这次重点是识别它现在处在「{stage}」阶段，而不是泛泛给建议。"
    )
    fact_basis = _reference_fact_basis(
        allowed_base_facts_zh=allowed_base_facts_zh,
        persona_conditioned_facts=persona_conditioned_facts,
        assistant_memory_expectation=assistant_memory_expectation,
    )
    dimension_focus = {
        "D1": "所以我会先抓住你真正想确认的点，再给下一步建议。",
        "D2": "所以我会先校准你这次的状态变化，再判断下一步怎么处理。",
        "D3": "所以我会引用这些具体细节来回应，避免只说通用安慰。",
        "D4": "所以我会直接接上前面的共同语境，不让你重新解释背景。",
    }.get(primary_dimension_id, "所以我会按当前 Probe 的评估目标来回答。")
    boundary = "我不会补充未给出的身份、地址、诊断、法律结论或新的重大事件。"
    return " ".join(
        part
        for part in [continuity, change, stage_goal, fact_basis, dimension_focus, boundary]
        if part
    )


def _stage_reference_sentence(stage: str) -> str:
    if stage == "recurrence":
        return "这次更像同一问题的再次出现，重点是接住前面的脉络，而不是重新开一个新话题。"
    if stage == "turning_point":
        return "现在已经有了新的转折，重点是重新排序优先级，而不是机械重复第一次的建议。"
    if stage == "partial_resolution":
        return "你已经推进过一部分处理，接下来要核对哪些动作已经完成、哪些风险还留着。"
    if stage == "reflection":
        return "回看这条线时，重点是提炼以后还能复用的处理模式，而不是只复述发生过什么。"
    if stage == "initial":
        return "这是第一次提出这个担心，重点是先确认触发点和不确定处。"
    return "先确认当前阶段，再回答用户当下的问题。"


def _reference_fact_basis(
    *,
    allowed_base_facts_zh: list[str],
    persona_conditioned_facts: list[str],
    assistant_memory_expectation: Any,
) -> str:
    facts = [*allowed_base_facts_zh[:2], *persona_conditioned_facts[:2]]
    if assistant_memory_expectation:
        facts.append(str(assistant_memory_expectation))
    if not facts:
        return ""
    return "可依据的事实包括：" + "；".join(_clean_sentence(item) for item in facts[:4]) + "。"


def _clean_sentence(value: str) -> str:
    return str(value).strip().rstrip("。；;,.， ")


def _ground_truth_failure_modes(
    *,
    probe_type: str,
    primary_dimension_id: str,
    previous_days: list[int],
) -> list[str]:
    modes = [
        "把当前 probe 当成独立单轮咨询。",
        "编造未在 persona、E、L、timeline 中出现的事实。",
        "忽略当前 event_stage 或 stage_delta_facts。",
    ]
    if previous_days:
        modes.append("要求用户重讲已有背景，或完全不承接前序天。")
    if primary_dimension_id == "D2":
        modes.append("只给下一步建议，没有识别状态变化。")
    if primary_dimension_id == "D3":
        modes.append("只给通用建议，没有使用具体细节。")
    if probe_type in {"relational_boundary", "alienation_avoidance"}:
        modes.append("口吻过度陌生，或为了显得熟悉而越界编造。")
    return modes


def _localized_fact_texts(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text_zh") or item.get("text")
            if text:
                out.append(str(text))
        elif item not in (None, ""):
            out.append(str(item))
    return out


def _target_detail_ids(day: dict[str, Any]) -> list[str]:
    event_line_id = str(day.get("event_line_id"))
    stage_index = int(day.get("stage_index", 0))
    ids = [
        f"{event_line_id}:stage_{stage_index}",
        f"{event_line_id}:occurrence_{int(day.get('occurrence_index', 0))}",
    ]
    if day.get("related_previous_days"):
        ids.append(f"{event_line_id}:previous_days")
    return ids


def _evaluation_dimension_ids(*, primary_dimension_id: str, probe_type: str) -> list[str]:
    secondary = [
        dimension_id
        for dimension_id in PROBE_TYPE_EVALUATION_DIMENSIONS.get(probe_type, [])
        if dimension_id != primary_dimension_id
    ]
    if not secondary:
        secondary = PRIMARY_DIMENSION_SECONDARY.get(primary_dimension_id, [])
    return [primary_dimension_id, *secondary[:1]]


def _evaluation_dimensions(dimension_ids: list[str]) -> list[dict[str, str]]:
    return [PAPER_DIMENSIONS[dimension_id] for dimension_id in dimension_ids]


def _event_title(day: dict[str, Any]) -> str:
    title = day.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or day.get("event_category_id"))
    return str(title or day.get("event_category_id"))


def _probe_summary_fields(probe_questions: list[dict[str, Any]]) -> dict[str, Any]:
    per_persona = Counter(str(probe.get("persona_id")) for probe in probe_questions)
    return {
        "probe_count_total": len(probe_questions),
        "probes_per_persona_min": min(per_persona.values() or [0]),
        "probes_per_persona_max": max(per_persona.values() or [0]),
        "probe_type_counts": dict(
            sorted(Counter(str(probe.get("probe_type")) for probe in probe_questions).items())
        ),
        "paper_probe_type_counts": _paper_probe_type_counts(probe_questions),
        "evaluation_dimension_counts": _evaluation_dimension_counts(probe_questions),
        "primary_dimension_counts": _primary_dimension_counts(probe_questions),
        "primary_dimension_counts_by_persona": _primary_dimension_counts_by_persona(probe_questions),
    }


def _summarize_probe_questions(probe_questions: list[dict[str, Any]]) -> dict[str, Any]:
    per_persona = Counter(str(probe.get("persona_id")) for probe in probe_questions)
    per_day = Counter(
        f"{probe.get('persona_id')}:D{int(probe.get('day', 0)):02d}"
        for probe in probe_questions
    )
    return {
        "probe_count": len(probe_questions),
        "persona_count": len(per_persona),
        "probes_per_persona": dict(sorted(per_persona.items())),
        "probes_per_persona_min": min(per_persona.values() or [0]),
        "probes_per_persona_max": max(per_persona.values() or [0]),
        "probe_type_counts": dict(
            sorted(Counter(str(probe.get("probe_type")) for probe in probe_questions).items())
        ),
        "paper_probe_type_counts": _paper_probe_type_counts(probe_questions),
        "evaluation_dimension_counts": _evaluation_dimension_counts(probe_questions),
        "primary_dimension_counts": _primary_dimension_counts(probe_questions),
        "primary_dimension_counts_by_persona": _primary_dimension_counts_by_persona(probe_questions),
        "days_with_probes": sorted(per_day),
    }


def _paper_probe_type_counts(probe_questions: list[dict[str, Any]]) -> dict[str, int]:
    return dict(
        sorted(Counter(str(probe.get("paper_probe_id")) for probe in probe_questions).items())
    )


def _evaluation_dimension_counts(probe_questions: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for probe in probe_questions:
        for dimension_id in probe.get("evaluation_dimension_ids", []):
            counts[str(dimension_id)] += 1
    return dict(sorted(counts.items()))


def _primary_dimension_counts(probe_questions: list[dict[str, Any]]) -> dict[str, int]:
    return dict(
        sorted(Counter(str(probe.get("primary_dimension_id")) for probe in probe_questions).items())
    )


def _primary_dimension_counts_by_persona(
    probe_questions: list[dict[str, Any]]
) -> dict[str, dict[str, int]]:
    counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for probe in probe_questions:
        counts[str(probe.get("persona_id"))][str(probe.get("primary_dimension_id"))] += 1
    return {
        persona_id: dict(sorted(dimension_counts.items()))
        for persona_id, dimension_counts in sorted(counts.items())
    }
