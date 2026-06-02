from __future__ import annotations

from collections import OrderedDict
from typing import Any


EMOTION_KEYWORDS = [
    ("烦", "烦躁"),
    ("怕", "担心"),
    ("不安", "不安"),
    ("焦虑", "焦虑"),
    ("悬", "悬着"),
    ("累", "疲惫"),
    ("疲惫", "疲惫"),
    ("紧", "紧张"),
    ("委屈", "委屈"),
    ("自责", "自责"),
    ("不想", "抗拒"),
    ("出戏", "警惕"),
    ("陌生", "警惕"),
    ("被看见", "委屈"),
]


TYPE_MEMORY_REQUIREMENTS: dict[str, list[str]] = {
    "current_understanding": [
        "relational_anchor",
        "summary_memory",
    ],
    "memory_invocation": [
        "event_memory",
        "relational_anchor",
    ],
    "state_transformation": [
        "summary_memory",
        "event_memory",
        "relational_anchor",
    ],
    "relational_boundary": [
        "relational_anchor",
        "response_boundary",
    ],
    "alienation": [
        "relational_anchor",
        "response_boundary",
    ],
    "natural_detail": [
        "event_memory",
        "relational_anchor",
    ],
    "m1_response_style": [
        "relational_anchor",
        "response_boundary",
    ],
    "address_style": [
        "relational_anchor",
        "response_boundary",
    ],
    "memory_boundary": [
        "relational_anchor",
        "response_boundary",
    ],
    "m2_event_continuity": [
        "summary_memory",
        "event_memory",
        "relational_anchor",
    ],
    "m3_detail_precision": [
        "summary_memory",
        "event_memory",
        "relational_anchor",
    ],
}


DIMENSION_MEMORY_REQUIREMENTS: dict[str, list[str]] = {
    "hidden_intent_recognition": ["relational_anchor"],
    "emotional_state_recognition": ["summary_memory"],
    "relationship_expectation_recognition": ["relational_anchor", "response_boundary"],
    "shared_context_invocation": ["event_memory", "summary_memory"],
    "alienation_error_rate": ["response_boundary"],
    "natural_detail_use": ["relational_anchor"],
}


TYPE_FAILURE_MODES: dict[str, list[str]] = {
    "current_understanding": [
        "只回答表层事件，没有识别当前隐含意图或情绪状态",
        "把用户的校准请求当作普通建议请求",
    ],
    "memory_invocation": [
        "把持续事件当成第一次出现",
        "要求用户从头解释背景",
        "机械背诵旧事实但不能推进当前判断",
    ],
    "state_transformation": [
        "只看当前句子，没有识别跨天状态变化",
        "没有区分旧状态和当前状态",
    ],
    "relational_boundary": [
        "为了显得懂用户而补出未提供细节",
        "不区分已知事实和推测",
    ],
    "alienation": [
        "突然使用过度亲密或角色化称呼",
        "把熟悉感表演成夸张亲密或客服流程",
    ],
    "natural_detail": [
        "堆砌细节或机械背日志",
        "完全不调用服务当前判断的关键细节",
    ],
    "m1_response_style": [
        "只给标准建议或泛泛安慰",
        "没有识别用户在测试回应方式是否还熟悉",
    ],
    "address_style": [
        "突然使用过度亲密或角色化称呼",
        "把熟悉感表演成夸张亲密",
    ],
    "memory_boundary": [
        "为了显得懂用户而补出未提供细节",
        "不区分已知事实和推测",
    ],
    "m2_event_continuity": [
        "把持续事件当成第一次出现",
        "要求用户从头解释背景",
        "只机械复述旧事实但不能推进当前判断",
    ],
    "m3_detail_precision": [
        "只答当前字面问题，没有使用必要细节理解心理状态",
        "堆砌细节或编造细节",
    ],
}


def generate_bei_annotations(
    *,
    probe_question_plan: dict[str, Any],
    timeline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate docx-route BEI annotations for targeted probe questions.

    The docx route treats BEI as an evaluation scaffold, not as model-visible
    ground truth. This generator therefore only reads script/probe metadata and
    emits deterministic annotations that can be reviewed and edited.
    """

    questions = probe_question_plan.get("probe_questions", [])
    if not isinstance(questions, list):
        raise ValueError("probe_question_plan must contain a probe_questions list")

    timeline = timeline or {}
    events_by_id = {
        str(event.get("event_id")): event
        for event in timeline.get("events", [])
        if isinstance(event, dict) and event.get("event_id")
    }

    annotations = [
        _annotate_question(question=question, events_by_id=events_by_id)
        for question in questions
    ]
    return {
        "schema_version": "bei_annotations_v0.1_docx_route",
        "generation_mode": "deterministic_probe_bei_scaffold",
        "source_schema": probe_question_plan.get("schema_version"),
        "description": (
            "BEI annotations for docx-route relational memory experiments. "
            "They are evaluation metadata and must not be exposed to assistant "
            "response generation."
        ),
        "allowed_required_memory_type": [
            "generic_memory",
            "summary_memory",
            "event_memory",
            "relational_anchor",
            "response_boundary",
        ],
        "summary": {
            "annotation_count": len(annotations),
            "probe_types": _count_by(annotations, "probe_type"),
        },
        "annotations": annotations,
    }


def _annotate_question(
    *,
    question: dict[str, Any],
    events_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    assessment = question.get("tom_assessment", {})
    if not isinstance(assessment, dict):
        assessment = {}
    probe_type = str(question.get("probe_type", "unknown"))
    topic = str(question.get("topic", ""))
    user_message = str(question.get("user_message", ""))
    hidden_need = str(assessment.get("hidden_user_need", "")).strip()
    high_score = str(assessment.get("high_score_behavior", "")).strip()
    low_score = str(assessment.get("low_score_behavior", "")).strip()
    related_events = [
        events_by_id[event_id]
        for event_id in question.get("event_refs", [])
        if event_id in events_by_id
    ]

    return {
        "annotation_id": str(question.get("probe_id") or question.get("message_id")),
        "probe_id": question.get("probe_id"),
        "message_id": question.get("message_id"),
        "day": question.get("day"),
        "topic": topic,
        "probe_type": probe_type,
        "event_refs": list(question.get("event_refs", [])),
        "belief": _build_belief(topic=topic, user_message=user_message, hidden_need=hidden_need),
        "emotion": _infer_emotions(user_message + " " + hidden_need),
        "intention": _build_intention(
            probe_type=probe_type,
            hidden_need=hidden_need,
            user_message=user_message,
        ),
        "relational_expectation": _build_relational_expectation(
            probe_type=probe_type,
            dimensions=[str(item) for item in question.get("tom_dimensions", [])],
        ),
        "required_memory_type": _infer_required_memory_type(question),
        "failure_mode_expected": _build_failure_modes(
            probe_type=probe_type,
            low_score=low_score,
        ),
        "gold_response_strategy": high_score or _fallback_gold_strategy(probe_type),
        "evidence_basis": {
            "user_message": user_message,
            "surface_question": assessment.get("surface_question"),
            "hidden_user_need": hidden_need,
            "related_event_summaries": [
                {
                    "event_id": event.get("event_id"),
                    "day": event.get("day"),
                    "title": event.get("title"),
                    "status": event.get("status"),
                }
                for event in related_events
            ],
        },
    }


def _build_belief(*, topic: str, user_message: str, hidden_need: str) -> str:
    if hidden_need:
        return f"用户认为当前的{topic}不只是表层问题；{hidden_need}"
    if "不想" in user_message or "从头" in user_message:
        return f"用户认为{topic}已经形成持续语境，不希望再次从零解释。"
    return f"用户认为{topic}需要被放进此前对话和当前状态中一起判断。"


def _infer_emotions(text: str) -> list[str]:
    emotions: list[str] = []
    for keyword, emotion in EMOTION_KEYWORDS:
        if keyword in text and emotion not in emotions:
            emotions.append(emotion)
    return emotions or ["不确定", "希望被接住"]


def _build_intention(*, probe_type: str, hidden_need: str, user_message: str) -> str:
    if hidden_need:
        return hidden_need
    if probe_type == "m2_event_continuity" or "从头" in user_message:
        return "希望 agent 接上此前事件线和处理方式，直接推进当前判断。"
    if probe_type == "memory_boundary":
        return "希望 agent 在理解用户的同时克制调用记忆，不补空白。"
    return (
        "希望 agent 识别当前话语背后的真实需求，"
        "而不是只回答字面问题。"
    )


def _build_relational_expectation(*, probe_type: str, dimensions: list[str]) -> str:
    if probe_type in {"memory_boundary", "relational_boundary"}:
        return (
            "熟悉但克制；明确区分已知、未知和推测，"
            "不能为了亲近感编造细节。"
        )
    if probe_type in {"address_style", "alienation"}:
        return "像熟人一样直接自然，不使用突兀称呼或表演式亲密。"
    if probe_type in {"m2_event_continuity", "memory_invocation"}:
        return "不要让用户重讲背景；自然延续此前形成的共同处理方式。"
    if probe_type in {"m3_detail_precision", "natural_detail"}:
        return "只调用服务于当前判断的必要细节，避免机械背日志。"
    if probe_type == "state_transformation":
        return "接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。"
    if "relationship_expectation_recognition" in dimensions:
        return (
            "保持熟悉、直接、不过度安慰、不过度亲密的"
            "长期陪伴关系位置。"
        )
    return "以稳定、具体、不过度表演的方式接住用户。"


def _infer_required_memory_type(question: dict[str, Any]) -> list[str]:
    explicit = question.get("required_memory_type")
    if isinstance(explicit, list) and explicit:
        return [str(item) for item in explicit if str(item)]

    result: list[str] = []
    probe_type = str(question.get("probe_type", ""))
    for item in TYPE_MEMORY_REQUIREMENTS.get(probe_type, []):
        _append_unique(result, item)
    for dimension in question.get("tom_dimensions", []):
        for item in DIMENSION_MEMORY_REQUIREMENTS.get(str(dimension), []):
            _append_unique(result, item)
    for detail_id in question.get("target_detail_ids", []):
        detail_text = str(detail_id)
        if ":latent_" in detail_text or "m3" in detail_text:
            _append_unique(result, "relational_anchor")
        if detail_text.startswith("m1_"):
            _append_unique(result, "relational_anchor")
        if detail_text.startswith("E"):
            _append_unique(result, "event_memory")
    return result or ["generic_memory"]


def _build_failure_modes(*, probe_type: str, low_score: str) -> list[str]:
    failures = []
    if low_score:
        failures.append(low_score)
    for item in TYPE_FAILURE_MODES.get(probe_type, []):
        _append_unique(failures, item)
    _append_unique(failures, "只服从当前显性指令，没有体现长期关系语境")
    return failures


def _fallback_gold_strategy(probe_type: str) -> str:
    if probe_type in {"m2_event_continuity", "memory_invocation"}:
        return (
            "自然接上持续事件线，用此前处理方式给出当前"
            "行动/观察/降级判断。"
        )
    if probe_type in {"memory_boundary", "relational_boundary"}:
        return "先承认边界，再区分已知事实、合理推测和不能补的空白。"
    if probe_type == "state_transformation":
        return "指出用户状态从旧阶段到当前阶段的变化，并说明这如何影响下一步。"
    if probe_type in {"m3_detail_precision", "natural_detail"}:
        return (
            "调用必要细节服务于情绪、边界和下一步判断，"
            "不机械复述历史。"
        )
    if probe_type == "alienation":
        return "保持熟悉但不过度表演的语气，避免客服化和突兀称呼。"
    return "先识别用户隐含需求和关系期待，再给出具体、克制的回应。"


def _append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: OrderedDict[str, int] = OrderedDict()
    for item in items:
        value = str(item.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(counts)
