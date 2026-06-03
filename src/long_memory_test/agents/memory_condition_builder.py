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
        "name": "Generic Agent Memory Baseline",
        "definition": (
            "Letta 默认记忆基线；可以读取 Letta 自带 core memory、普通用户画像、"
            "普通会话摘要、普通检索片段和同窗口短期上下文。"
        ),
        "can_read": [
            "same_session_short_term_context",
            "letta_default_core_memory",
            "letta_default_user_profile",
            "letta_default_conversation_summary",
            "letta_default_retrieved_history",
        ],
        "cannot_read": [
            "bei_annotations",
            "gold_response_strategy",
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
            "结论级关系记忆；只保存重要结论、稳定偏好、回应风格、"
            "关系期待、关键判断和不要做什么。"
        ),
        "can_read": [
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
            "M1 + 摘要级记忆，保存关键事件线、跨天主题进展、"
            "状态变化和处理结果摘要。"
        ),
        "can_read": [
            "M1_conclusion_memory",
            "topic_event_summary",
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
            "M1 + M2 + 细节级关系锚点，保存必要细节、共同语言、"
            "边界说明和误用风险。"
        ),
        "can_read": [
            "M1_conclusion_memory",
            "M2_summary_memory",
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
    for message in messages:
        message_id = str(message["message_id"])
        payloads[message_id] = _build_message_payloads(
            message=message,
            events_by_id=events_by_id,
            daily_messages=daily_messages,
        )

    return {
        "schema_version": "memory_conditions_v0.1_docx_route",
        "generation_mode": "deterministic_docx_m0_m1_m2_m3_memory_packages",
        "description": (
            "M0/M1/M2/M3 memory payloads for the docx route. M0 is a Letta "
            "default-memory runtime baseline, not no-memory. M1/M2/M3 are "
            "cumulative relational memory levels independent from M0; M2 "
            "contains M1 and M3 contains M1+M2."
        ),
        "condition_specs": CONDITION_SPECS,
        "default_payloads": _build_default_payloads(),
        "memory_payloads_by_message_id": payloads,
        "summary": {
            "message_payload_count": len(payloads),
            "condition_count": len(CONDITION_SPECS),
            "conditions": [item["condition_id"] for item in CONDITION_SPECS],
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
            "memory_provider": "letta",
            "requires_runtime_letta": True,
            "memory_context": (
                "M0 使用运行时 Letta 默认记忆。此静态文件不生成手工 generic 摘要，"
                "也不提供事件线天数、关系记忆、人工评测标注 "
                "或关系锚点。"
            ),
            "source_detail_ids": [],
        },
        "M1": {
            "condition_id": "M1",
            "memory_context": "结论级关系记忆：" + REL_CONCLUSION_MEMORY,
            "source_detail_ids": [
                "m1_response_style_direct",
                "m1_anxiety_fact_first",
            ],
        },
        "M2": {
            "condition_id": "M2",
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
) -> dict[str, dict[str, Any]]:
    topic = str(message.get("topic", ""))
    day = int(message.get("day", 0) or 0)
    related_events = _related_events(message=message, events_by_id=events_by_id)
    topic_history = _topic_history(
        topic=topic,
        day=day,
        daily_messages=daily_messages,
    )
    m0_context = _build_m0_context(topic=topic, topic_history=topic_history)
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
            "memory_provider": "letta",
            "requires_runtime_letta": True,
            "memory_context": m0_context,
            "source_detail_ids": [],
        },
        "M1": {
            "condition_id": "M1",
            "memory_context": m1_context,
            "source_detail_ids": [
                "m1_response_style_direct",
                "m1_anxiety_fact_first",
            ],
        },
        "M2": {
            "condition_id": "M2",
            "memory_context": m2_context,
            "source_detail_ids": _source_detail_ids(related_events, max_level="M2"),
        },
        "M3": {
            "condition_id": "M3",
            "memory_context": m3_context,
            "source_detail_ids": _source_detail_ids(related_events, max_level="M3"),
        },
    }


def _build_m0_context(*, topic: str, topic_history: list[dict[str, Any]]) -> str:
    return (
        "M0 使用运行时 Letta 默认记忆基线。本静态 payload 只声明边界："
        "不得读取手工整理的关系记忆、事件轨迹、人工评测标注或关系锚点；"
        "实际可用记忆必须由 Letta runtime 提供。"
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
