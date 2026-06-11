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
            "相对 M0 的结论级关系记忆增强条件；使用独立 runtime namespace，"
            "不读取 M0 或其他条件的 payload，只保存重要结论、稳定偏好、"
            "回应风格、关系期待、关键判断和不要做什么。"
        ),
        "can_read": [
            "condition_isolated_conclusion_memory",
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
            "相对 M0/M1 的摘要级关系记忆增强条件；使用独立 runtime namespace，"
            "不读取 M0/M1 的 payload，在自身 namespace 内保存结论级关系记忆"
            "和关键事件线、跨天主题进展、状态变化和处理结果摘要。"
        ),
        "can_read": [
            "condition_isolated_conclusion_memory",
            "condition_isolated_event_line_summary_memory",
            "cross_day_progress",
            "state_change_summary",
            "outcome_summary",
        ],
        "cannot_read": [
            "bei_annotations",
            "gold_response_strategy",
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
            "相对 M0/M1/M2 的细节级关系锚点增强条件；使用独立 runtime namespace，"
            "不读取其他条件的 payload，在自身 namespace 内保存结论级关系记忆、"
            "摘要级事件线记忆、必要细节、共同语言、边界说明和误用风险。"
        ),
        "can_read": [
            "condition_isolated_conclusion_memory",
            "condition_isolated_event_line_summary_memory",
            "condition_isolated_detail_anchor_memory",
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
            "LD-Agent memory-only baseline, not no-memory. M1/M2/M3 are "
            "relational memory enhancement conditions backed by independent "
            "runtime namespaces; M2 writes its own M1-level content, and M3 "
            "writes its own M1+M2-level content, but no condition shares "
            "another condition's runtime payload."
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
            "memory_provider": "condition_isolated_relational_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": False,
            "memory_context": "结论级关系记忆：" + REL_CONCLUSION_MEMORY,
            "source_detail_ids": [
                "m1_response_style_direct",
                "m1_anxiety_fact_first",
            ],
        },
        "M2": {
            "condition_id": "M2",
            "memory_provider": "condition_isolated_relational_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": False,
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
            "memory_provider": "condition_isolated_relational_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": False,
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
            "memory_provider": "condition_isolated_relational_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": False,
            "tau": dict(tau_binding),
            "memory_context": m1_context,
            "source_detail_ids": [
                "m1_response_style_direct",
                "m1_anxiety_fact_first",
            ],
        },
        "M2": {
            "condition_id": "M2",
            "memory_provider": "condition_isolated_relational_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": False,
            "tau": dict(tau_binding),
            "memory_context": m2_context,
            "source_detail_ids": _source_detail_ids(related_events, max_level="M2"),
        },
        "M3": {
            "condition_id": "M3",
            "memory_provider": "condition_isolated_relational_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": False,
            "tau": dict(tau_binding),
            "memory_context": m3_context,
            "source_detail_ids": _source_detail_ids(related_events, max_level="M3"),
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


def _unique_strings(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value)
        if text not in seen:
            result.append(text)
            seen.add(text)
    return result
