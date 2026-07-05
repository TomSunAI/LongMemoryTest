from __future__ import annotations

from collections import OrderedDict
from typing import Any


REL_CONCLUSION_MEMORY = (
    "用户偏好直接、自然、少废话的回应；"
    "不喜欢客服式寒暄和空泛安慰。"
    "当用户焦虑或反复卡住时，更需要先拆事实、脑补风险、行动边界和下一步，"
    "而不是被泛泛安抚。用户期待 agent 像稳定熟悉的长期陪伴对象，"
    "熟悉但不过度亲密，必要时明确区分已知和推测。"
)


CONDITION_SPECS = [
    {
        "condition_id": "M0",
        "name": "LD-Agent Memory Baseline",
        "definition": (
            "LD-Agent memory-only 普通长短期记忆基线；可以读取同窗口短期上下文、"
            "completed session 写入的普通 session-summary memories、普通 persona/fact memories "
            "和运行时检索片段。"
        ),
        "can_read": [
            "same_session_short_term_context",
            "ld_agent_short_term_memory_bank",
            "session_summary_memory_bank",
            "generic_persona_memory_bank",
            "topic_overlap_time_decay_retrieved_session_memory",
        ],
        "cannot_read": [
            "bei_annotations",
            "gold_response_strategy",
            "probe_type",
            "event_line_stage_labels",
            "relational_conclusion_memory",
            "relational_event_summary_memory",
            "relational_detail_anchor_memory",
        ],
        "theoretical_use": (
            "检验 generic agent memory 是否已经足够支持长期陪伴中的 "
            "ToM-like interaction。"
        ),
    },
    {
        "condition_id": "M1",
        "name": "Conclusion-level Relational Memory",
        "definition": (
            "M0 普通长期记忆底座 + 结论级关系记忆增强条件；关系记忆"
            "使用独立 runtime namespace，最终 payload 与同轮 M0 检索结果组合，"
            "不读取其他关系条件的 payload，只保存重要结论、稳定偏好、"
            "回应风格、关系期待、关键判断和不要做什么。"
        ),
        "can_read": [
            "shared_m0_ld_agent_retrieved_payload",
            "own_condition_conclusion_memory",
            "stable_preferences",
            "response_style",
            "relationship_expectation",
            "key_judgments",
            "response_boundary",
            "do_not_do",
        ],
        "cannot_read": [
            "bei_annotations",
            "gold_response_strategy",
            "probe_type",
            "event_line_stage_labels",
            "other_condition_payloads",
            "event_summary",
            "specific_dates",
            "specific_process",
            "raw_user_quotes",
            "shared_scene_details",
            "detail_anchors",
        ],
        "theoretical_use": "检验只记重要结论/关系画像/长期偏好是否足够。",
    },
    {
        "condition_id": "M2",
        "name": "Summary-level Relational Memory",
        "definition": (
            "M0 普通长期记忆底座 + M1 结论级关系记忆 + 摘要级关系记忆"
            "增强条件；关系记忆使用独立 runtime namespace，最终 payload 与"
            "同轮 M0 检索结果组合，不读取其他关系条件的 payload。"
        ),
        "can_read": [
            "shared_m0_ld_agent_retrieved_payload",
            "own_condition_conclusion_memory",
            "own_condition_event_line_summary_memory",
            "cross_day_progress",
            "state_change_summary",
            "outcome_summary",
        ],
        "cannot_read": [
            "bei_annotations",
            "gold_response_strategy",
            "probe_type",
            "event_line_stage_labels",
            "other_condition_payloads",
            "raw_user_quotes",
            "detailed_scene",
            "shared_language",
            "full_history",
            "complete_history_fragments",
            "unfiltered_detail_anchors",
        ],
        "theoretical_use": "检验摘要级事件/状态记忆是否能支持跨天接续和变化识别。",
    },
    {
        "condition_id": "M3",
        "name": "Detail-level / Relational Anchor Memory",
        "definition": (
            "M0 普通长期记忆底座 + M1 结论级关系记忆 + M2 摘要级事件线记忆"
            " + 细节级关系锚点增强条件；关系记忆使用独立 runtime namespace，"
            "最终 payload 与同轮 M0 检索结果组合，不读取其他关系条件的 payload。"
        ),
        "can_read": [
            "shared_m0_ld_agent_retrieved_payload",
            "own_condition_conclusion_memory",
            "own_condition_event_line_summary_memory",
            "own_condition_detail_anchor_memory",
            "necessary_details",
            "specific_scenes",
            "shared_language",
            "relational_anchors",
            "response_boundaries",
            "misuse_boundaries",
            "current_task_relevant_details",
        ],
        "cannot_read": [
            "bei_annotations",
            "gold_response_strategy",
            "probe_type",
            "event_line_stage_labels",
            "other_condition_payloads",
            "full_raw_history",
            "unstored_or_fabricated_facts",
            "irrelevant_private_details",
        ],
        "theoretical_use": (
            "检验细节级关系记忆是否提升熟悉感、自然细节调用，并降低陌生化/"
            "过度记忆。"
        ),
    },
]


def generate_memory_conditions(
    *,
    timeline: dict[str, Any],
    daily_messages: dict[str, Any],
    probe_question_plan: dict[str, Any],
    bei_annotations: dict[str, Any],
    tau_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    events_by_id = {
        str(event.get("event_id")): event
        for event in timeline.get("events", [])
        if isinstance(event, dict) and event.get("event_id")
    }
    messages = _collect_messages(
        daily_messages=daily_messages,
        probe_question_plan=probe_question_plan,
    )
    payloads = OrderedDict()
    tau_bindings = (
        tau_contract.get("message_bindings", {})
        if isinstance(tau_contract, dict)
        else {}
    )
    for message in messages:
        message_id = str(message["message_id"])
        payloads[message_id] = _build_message_payloads(
            message=message,
            events_by_id=events_by_id,
            daily_messages=daily_messages,
            tau_binding=dict(tau_bindings.get(message_id) or message.get("tau") or {}),
        )

    return {
        "schema_version": "memory_conditions_v0.1_docx_route",
        "generation_mode": "deterministic_docx_m0_m1_m2_m3_memory_packages",
        "description": (
            "M0/M1/M2/M3 memory payloads for the docx route. M0 is a runtime "
            "LD-Agent memory-only baseline, not no-memory. M1/M2/M3 final "
            "runtime payloads are composed as the same-turn M0 retrieved base "
            "+ a condition-specific relational overlay. The relational overlay "
            "uses independent runtime namespaces; M2 writes its own M1-level "
            "content, and M3 writes its own M1+M2-level content, but no condition "
            "reads another condition's answers or relational namespace."
        ),
        "tau_contract": _tau_contract_reference(tau_contract),
        "condition_specs": CONDITION_SPECS,
        "default_payloads": _build_default_payloads(),
        "memory_payloads_by_message_id": payloads,
        "summary": {
            "message_payload_count": len(payloads),
            "condition_count": len(CONDITION_SPECS),
            "conditions": [item["condition_id"] for item in CONDITION_SPECS],
            "tau_bound_message_count": sum(
                1
                for payload_by_condition in payloads.values()
                if payload_by_condition.get("M0", {}).get("tau")
            ),
        },
    }


def generate_memory_conditions_from_tau_contract(
    *,
    tau_contract: dict[str, Any],
) -> dict[str, Any]:
    """Build M0/M1/M2/M3 payloads directly from a tau contract.

    This is the high-density tau route. It only adapts existing tau/I/P/L
    structures into memory payloads; it does not generate new tasks or write
    output files.
    """

    lines_by_id = {
        str(line.get("event_line_id")): line
        for line in tau_contract.get("L", [])
        if isinstance(line, dict) and line.get("event_line_id")
    }
    units_by_id = {
        str(unit.get("interaction_unit_id")): unit
        for unit in tau_contract.get("I", [])
        if isinstance(unit, dict) and unit.get("interaction_unit_id")
    }
    probes_by_id = {
        str(probe.get("message_id") or probe.get("probe_id")): probe
        for probe in tau_contract.get("P", [])
        if isinstance(probe, dict) and (probe.get("message_id") or probe.get("probe_id"))
    }
    bindings = {
        str(message_id): dict(binding)
        for message_id, binding in tau_contract.get("message_bindings", {}).items()
        if isinstance(binding, dict)
    }
    messages = _collect_tau_messages(
        tau_contract=tau_contract,
        units_by_id=units_by_id,
        probes_by_id=probes_by_id,
        bindings=bindings,
    )
    payloads = OrderedDict()
    for message in messages:
        message_id = str(message["message_id"])
        binding = dict(bindings.get(message_id) or message.get("tau") or {})
        unit = units_by_id.get(str(binding.get("interaction_unit_id") or message.get("interaction_unit_id")), {})
        probe = probes_by_id.get(message_id, {})
        line = lines_by_id.get(str(binding.get("event_line_id") or message.get("event_line_id")), {})
        payloads[message_id] = _build_tau_message_payloads(
            message=message,
            binding=binding,
            line=line,
            unit=unit,
            probe=probe,
        )

    return {
        "schema_version": "memory_conditions_v0.2_tau_route",
        "generation_mode": "deterministic_tau_to_m0_m1_m2_m3_interface_only",
        "description": (
            "M0/M1/M2/M3 memory payloads adapted directly from tau=(z,T,L,I,P). "
            "This artifact connects the latest tau contract to condition payloads "
            "without generating new user tasks. M1/M2/M3 final runtime payloads "
            "are still composed by the runner as M0 retrieved base + condition "
            "relational overlay."
        ),
        "tau_contract": _tau_contract_reference(tau_contract),
        "condition_specs": CONDITION_SPECS,
        "default_payloads": _build_default_payloads(),
        "memory_payloads_by_message_id": payloads,
        "summary": {
            "message_payload_count": len(payloads),
            "condition_count": len(CONDITION_SPECS),
            "conditions": [item["condition_id"] for item in CONDITION_SPECS],
            "tau_bound_message_count": sum(
                1
                for payload_by_condition in payloads.values()
                if payload_by_condition.get("M0", {}).get("tau")
            ),
            "interaction_unit_count": len(units_by_id),
            "targeted_probe_count": len(probes_by_id),
            "source_message_binding_count": len(bindings),
        },
    }


def _collect_messages(
    *,
    daily_messages: dict[str, Any],
    probe_question_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for message in daily_messages.get("messages", []):
        if isinstance(message, dict) and message.get("message_id"):
            result.append(message)
    for question in probe_question_plan.get("probe_questions", []):
        if isinstance(question, dict) and question.get("message_id"):
            result.append(question)
    result.sort(
        key=lambda item: (
            int(item.get("day", 0)),
            str(item.get("message_id", "")),
        )
    )
    return result


def _collect_tau_messages(
    *,
    tau_contract: dict[str, Any],
    units_by_id: dict[str, dict[str, Any]],
    probes_by_id: dict[str, dict[str, Any]],
    bindings: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for unit_id, unit in units_by_id.items():
        opening = unit.get("scripted_opening", {})
        if not isinstance(opening, dict):
            opening = {}
        messages.append(
            {
                "message_id": unit_id,
                "turn_type": opening.get("turn_type") or "scripted_opening",
                "day": unit.get("day"),
                "day_group_id": unit.get("day_group_id"),
                "within_day_index": unit.get("within_day_index", 1),
                "topic": opening.get("topic") or _event_title(unit),
                "user_message": opening.get("user_message"),
                "interaction_unit_id": unit_id,
                "event_line_id": unit.get("event_line_id"),
                "event_stage": unit.get("event_stage"),
                "tau": dict(bindings.get(unit_id, {})),
            }
        )
    for message_id, probe in probes_by_id.items():
        interaction_unit_id = str(probe.get("interaction_unit_id") or "")
        binding = dict(bindings.get(message_id, {}))
        messages.append(
            {
                "message_id": message_id,
                "turn_type": "targeted_probe",
                "day": probe.get("day"),
                "day_group_id": probe.get("day_group_id"),
                "within_day_index": probe.get("within_day_index", 1),
                "topic": probe.get("topic") or _event_title(probe),
                "user_message": probe.get("question") or probe.get("user_message"),
                "interaction_unit_id": interaction_unit_id,
                "event_line_id": probe.get("event_line_id"),
                "event_stage": probe.get("event_stage"),
                "target_detail_ids": list(probe.get("target_detail_ids", [])),
                "event_refs": [probe.get("event_line_id")] if probe.get("event_line_id") else [],
                "tau": binding,
            }
        )
    messages.sort(
        key=lambda item: (
            str(item.get("persona_id") or item.get("tau", {}).get("persona_id", "")),
            int(item.get("day", 0) or 0),
            str(item.get("day_group_id", "")),
            int(item.get("within_day_index", 1) or 1),
            1 if item.get("turn_type") == "targeted_probe" else 0,
            str(item.get("message_id", "")),
        )
    )
    return messages


def _build_default_payloads() -> dict[str, dict[str, Any]]:
    return {
        "M0": {
            "condition_id": "M0",
            "memory_provider": "ld_agent_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "memory_context": (
                "M0 使用运行时 LD-Agent memory-only baseline。此静态文件只声明边界，"
                "不提供手工 generic 摘要、事件线阶段、关系记忆、人工评测标注或关系锚点。"
            ),
            "source_detail_ids": [],
        },
        "M1": {
            "condition_id": "M1",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "memory_context": "结论级关系记忆：" + REL_CONCLUSION_MEMORY,
            "source_detail_ids": [
                "m1_response_style_direct",
                "m1_anxiety_fact_first",
            ],
        },
        "M2": {
            "condition_id": "M2",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "memory_context": (
                "结论级关系记忆："
                + REL_CONCLUSION_MEMORY
                + "\n摘要级事件记忆：当前没有与本轮输入绑定的"
                + "具体事件摘要，只能使用普通主题连续性。"
            ),
            "source_detail_ids": [
                "m1_response_style_direct",
                "m1_anxiety_fact_first",
            ],
        },
        "M3": {
            "condition_id": "M3",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "memory_context": (
                "结论级关系记忆："
                + REL_CONCLUSION_MEMORY
                + "\n摘要级事件记忆：当前没有与本轮输入绑定的具体事件摘要。"
                + "\n细节级关系锚点：只在服务当前判断时调用必要细节；不要机械背日志。"
            ),
            "source_detail_ids": [
                "m1_response_style_direct",
                "m1_anxiety_fact_first",
            ],
        },
    }


def _build_message_payloads(
    *,
    message: dict[str, Any],
    events_by_id: dict[str, dict[str, Any]],
    daily_messages: dict[str, Any],
    tau_binding: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    topic = str(message.get("topic", ""))
    day = int(message.get("day", 0) or 0)
    related_events = _related_events(message=message, events_by_id=events_by_id)
    topic_history = _topic_history(
        topic=topic,
        day=day,
        daily_messages=daily_messages,
    )
    m1_context = "结论级关系记忆：" + REL_CONCLUSION_MEMORY
    m2_context = m1_context + "\n摘要级事件记忆：\n" + _build_m2_summary(
        topic=topic,
        topic_history=topic_history,
        related_events=related_events,
    )
    m3_context = m2_context + "\n细节级关系锚点：\n" + _build_m3_details(
        message=message,
        related_events=related_events,
    )
    return {
        "M0": {
            "condition_id": "M0",
            "memory_provider": "ld_agent_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "tau": dict(tau_binding),
            "memory_context": _build_m0_context(),
            "source_detail_ids": [],
        },
        "M1": {
            "condition_id": "M1",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "tau": dict(tau_binding),
            "memory_context": m1_context,
            "source_detail_ids": [
                "m1_response_style_direct",
                "m1_anxiety_fact_first",
            ],
        },
        "M2": {
            "condition_id": "M2",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "tau": dict(tau_binding),
            "memory_context": m2_context,
            "source_detail_ids": _source_detail_ids(related_events, max_level="M2"),
        },
        "M3": {
            "condition_id": "M3",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "tau": dict(tau_binding),
            "memory_context": m3_context,
            "source_detail_ids": _source_detail_ids(related_events, max_level="M3"),
        },
    }


def _build_tau_message_payloads(
    *,
    message: dict[str, Any],
    binding: dict[str, Any],
    line: dict[str, Any],
    unit: dict[str, Any],
    probe: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    m1_context = _build_tau_m1_context(line=line)
    m2_context = m1_context + "\n摘要级事件记忆：\n" + _build_tau_m2_summary(
        line=line,
        unit=unit,
    )
    m3_context = m2_context + "\n细节级关系锚点：\n" + _build_tau_m3_details(
        unit=unit,
        probe=probe,
    )
    return {
        "M0": {
            "condition_id": "M0",
            "memory_provider": "ld_agent_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "tau": dict(binding),
            "memory_context": _build_m0_context(),
            "source_detail_ids": [],
        },
        "M1": {
            "condition_id": "M1",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "tau": dict(binding),
            "memory_context": m1_context,
            "source_detail_ids": _tau_source_detail_ids(line=line, unit=unit, level="M1"),
        },
        "M2": {
            "condition_id": "M2",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "tau": dict(binding),
            "memory_context": m2_context,
            "source_detail_ids": _tau_source_detail_ids(line=line, unit=unit, level="M2"),
        },
        "M3": {
            "condition_id": "M3",
            "memory_provider": "m0_base_plus_relational_overlay",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "payload_role": "relational_overlay",
            "tau": dict(binding),
            "memory_context": m3_context,
            "source_detail_ids": _tau_source_detail_ids(
                line=line,
                unit=unit,
                level="M3",
                probe=probe,
            ),
        },
    }


def _tau_contract_reference(tau_contract: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(tau_contract, dict):
        return {
            "available": False,
            "role": "memory_conditions_generated_without_tau_contract",
        }
    return {
        "available": True,
        "schema_version": tau_contract.get("schema_version"),
        "notation": tau_contract.get("notation"),
        "summary": dict(tau_contract.get("summary", {})),
        "validation": dict(tau_contract.get("validation", {})),
        "role": "single_script_construction_source_for_all_conditions",
    }


def _build_m0_context() -> str:
    return (
        "M0 使用运行时 LD-Agent memory-only 普通长短期记忆基线。本静态 payload "
        "只声明边界：不得读取手工整理的关系记忆、事件线阶段、人工评测标注或关系锚点；"
        "实际可用普通 event/persona memory 必须由 LD-Agent memory runtime 提供。"
    )


def _build_tau_m1_context(*, line: dict[str, Any]) -> str:
    targets = [
        _localized_text(item, "target")
        for item in line.get("relational_memory_targets", [])
        if isinstance(item, dict) and _localized_text(item, "target")
    ]
    if not targets:
        targets = [REL_CONCLUSION_MEMORY]
    lines = ["结论级关系记忆："]
    for target in _unique_strings(targets):
        lines.append(f"- {target}")
    return "\n".join(lines)


def _build_tau_m2_summary(*, line: dict[str, Any], unit: dict[str, Any]) -> str:
    title = _event_title(line) or _event_title(unit)
    summary = _tau_summary_text(line=line, unit=unit)
    stage = _tau_stage_label(unit)
    occurrence_index = int(unit.get("occurrence_index", 0) or 0)
    observed_rows = [
        row
        for row in line.get("observed_stage_sequence", [])
        if isinstance(row, dict)
        and int(row.get("occurrence_index", 0) or 0) <= occurrence_index
    ]
    lines = []
    if title:
        lines.append(f"- 事件线：{title}。")
    if summary:
        lines.append(f"- 持续事件摘要：{summary}")
    if stage:
        lines.append(f"- 当前阶段：{stage}；当前 occurrence_index={occurrence_index}。")
    if observed_rows:
        history = ", ".join(
            f"D{int(row.get('day', 0)):02d}/{_stage_label(row.get('event_stage'))}"
            for row in observed_rows[-6:]
        )
        lines.append(f"- 已观察到的跨天进展：{history}。")
        expectations = _unique_strings(
            [
                _localized_text(row, "assistant_memory_expectation")
                for row in observed_rows
                if _localized_text(row, "assistant_memory_expectation")
            ]
        )
        if expectations:
            lines.append("- 前序处理策略：" + _join_zh_items(expectations[-3:]) + "。")
    return "\n".join(lines) if lines else "- 当前 tau 中没有可用事件摘要。"


def _tau_summary_text(*, line: dict[str, Any], unit: dict[str, Any]) -> str:
    summary_zh = str(line.get("persistent_event_summary_zh") or "").strip()
    if summary_zh:
        return summary_zh
    for fact in _scene_boundary_items(unit, "allowed_facts"):
        if fact.get("type") == "event_summary":
            return _localized_text(fact, "text")
    summary = str(line.get("persistent_event_summary") or "").strip()
    if summary:
        return summary
    return ""


def _tau_stage_label(unit: dict[str, Any]) -> str:
    for fact in _scene_boundary_items(unit, "allowed_facts"):
        if fact.get("type") == "event_stage":
            return _localized_text(fact, "text")
    return str(unit.get("event_stage") or "").strip()


def _stage_label(value: Any) -> str:
    labels = {
        "initial": "初始提出",
        "recurrence": "再次出现",
        "turning_point": "转折推进",
        "partial_resolution": "部分处理",
        "reflection": "回看总结",
    }
    text = str(value or "")
    return labels.get(text, text)


def _join_zh_items(values: list[str]) -> str:
    cleaned = [str(value).strip().rstrip("。；;") for value in values if str(value).strip()]
    return "；".join(cleaned)


def _build_tau_m3_details(*, unit: dict[str, Any], probe: dict[str, Any]) -> str:
    boundary = unit.get("scene_boundary", {})
    if not isinstance(boundary, dict):
        boundary = {}
    source_fields = unit.get("source_timeline_fields", {})
    if not isinstance(source_fields, dict):
        source_fields = {}
    target_detail_ids = [str(item) for item in probe.get("target_detail_ids", []) if item]
    lines = []
    allowed_facts = [
        fact
        for fact in _scene_boundary_items(unit, "allowed_facts")
        if isinstance(fact, dict) and _localized_text(fact, "text")
    ]
    for fact in allowed_facts[:10]:
        lines.append(f"- 可用事实[{fact.get('fact_id')}]: {_localized_text(fact, 'text')}")
    latent_concerns = [
        concern
        for concern in _scene_boundary_items(unit, "latent_concerns")
        if isinstance(concern, dict) and _localized_text(concern, "text")
    ]
    for concern in latent_concerns[:4]:
        lines.append(
            f"- 隐含担心[{concern.get('concern_id')}]: {_localized_text(concern, 'text')}"
        )
    if target_detail_ids:
        lines.append("- probe 目标细节：" + ", ".join(target_detail_ids))
    prohibited = _localized_list(source_fields, "prohibited_facts")
    if prohibited:
        lines.append("- 禁止补充：" + "；".join(prohibited[:3]))
    lines.append("- 使用边界：细节只能服务当前判断，不能机械背日志，不能补未存事实。")
    return "\n".join(_unique_strings(lines))


def _scene_boundary_items(unit: dict[str, Any], key: str) -> list[dict[str, Any]]:
    boundary = unit.get("scene_boundary", {})
    if not isinstance(boundary, dict):
        return []
    return [item for item in boundary.get(key, []) if isinstance(item, dict)]


def _build_m2_summary(
    *,
    topic: str,
    topic_history: list[dict[str, Any]],
    related_events: list[dict[str, Any]],
) -> str:
    lines = []
    if topic_history:
        days = ", ".join(f"D{item.get('day')}" for item in topic_history)
        lines.append(f"- 「{topic}」曾在 {days} 出现，是跨天持续主题。")
    for event in related_events[:6]:
        anchors = [
            anchor
            for anchor in event.get("memory_detail_anchors", [])
            if str(anchor.get("min_memory_level")) == "M2"
        ]
        if anchors:
            for anchor in anchors:
                lines.append(f"- {anchor.get('text')}")
        else:
            lines.append(
                f"- D{event.get('day')} {event.get('title')}，"
                f"状态：{event.get('status')}。"
            )
    return (
        "\n".join(_unique_strings(lines))
        if lines
        else "- 当前只有普通主题摘要，没有可追溯事件线。"
    )


def _build_m3_details(
    *,
    message: dict[str, Any],
    related_events: list[dict[str, Any]],
) -> str:
    target_detail_ids = {str(item) for item in message.get("target_detail_ids", [])}
    lines = []
    for event in related_events:
        for anchor in event.get("memory_detail_anchors", []):
            detail_id = str(anchor.get("detail_id", ""))
            min_level = str(anchor.get("min_memory_level", ""))
            if min_level == "M3" or detail_id in target_detail_ids:
                lines.append(f"- {anchor.get('text')}")
                response_mode = anchor.get("expected_response_mode")
                if response_mode:
                    lines.append(f"  调用边界：{response_mode}")
    lines.append(
        "- 使用边界：细节只能服务当前判断，不能机械背日志，不能补未存事实。"
    )
    return "\n".join(_unique_strings(lines))


def _related_events(
    *,
    message: dict[str, Any],
    events_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    event_ids = []
    for key in ["event_refs", "primary_event_id", "related_event_id"]:
        value = message.get(key)
        if isinstance(value, list):
            event_ids.extend(str(item) for item in value)
        elif value:
            event_ids.append(str(value))

    result = []
    seen = set()
    for event_id in event_ids:
        event = events_by_id.get(event_id)
        if event and event_id not in seen:
            result.append(event)
            seen.add(event_id)
    return result


def _topic_history(
    *,
    topic: str,
    day: int,
    daily_messages: dict[str, Any],
) -> list[dict[str, Any]]:
    result = []
    for message in daily_messages.get("messages", []):
        if message.get("topic") == topic and int(message.get("day", 0) or 0) <= day:
            result.append(message)
    return result


def _source_detail_ids(related_events: list[dict[str, Any]], *, max_level: str) -> list[str]:
    levels = {"M2": {"M2"}, "M3": {"M2", "M3"}}[max_level]
    detail_ids = []
    for event in related_events:
        for anchor in event.get("memory_detail_anchors", []):
            if anchor.get("min_memory_level") in levels and anchor.get("detail_id"):
                detail_ids.append(str(anchor["detail_id"]))
    return _unique_strings(detail_ids)


def _tau_source_detail_ids(
    *,
    line: dict[str, Any],
    unit: dict[str, Any],
    level: str,
    probe: dict[str, Any] | None = None,
) -> list[str]:
    result = [
        f"{line.get('event_line_id')}:relational_targets",
        f"{unit.get('interaction_unit_id')}:scene_boundary",
    ]
    if level in {"M2", "M3"}:
        result.append(f"{line.get('event_line_id')}:observed_stage_sequence")
    if level == "M3":
        result.append(f"{unit.get('interaction_unit_id')}:allowed_facts")
        result.append(f"{unit.get('interaction_unit_id')}:latent_concerns")
        for detail_id in (probe or {}).get("target_detail_ids", []):
            result.append(str(detail_id))
    return _unique_strings([item for item in result if item and not item.startswith("None:")])


def _event_title(item: dict[str, Any]) -> str:
    title = item.get("event_title") or item.get("title") or item.get("topic")
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or "")
    return str(title or "")


def _localized_text(item: dict[str, Any], key: str) -> str:
    value = item.get(f"{key}_zh")
    if value is None:
        value = item.get(key)
    if isinstance(value, list):
        return "；".join(str(part) for part in value if part)
    if isinstance(value, dict):
        return str(value.get("zh") or value.get("source") or value.get("text_zh") or value.get("text") or "")
    return str(value or "").strip()


def _localized_list(item: dict[str, Any], key: str) -> list[str]:
    value = item.get(f"{key}_zh")
    if value is None:
        value = item.get(key)
    if not isinstance(value, list):
        return [str(value)] if value else []
    return [str(part) for part in value if part]


def _unique_strings(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value)
        if text not in seen:
            result.append(text)
            seen.add(text)
    return result
