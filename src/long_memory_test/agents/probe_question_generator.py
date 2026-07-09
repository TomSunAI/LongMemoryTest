from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from long_memory_test.agents.event_stream_generator import load_json


@dataclass(frozen=True)
class ProbeQuestionConfig:
    scene_cards_path: Path
    probe_policy_path: Path


class ProbeQuestionGenerationError(ValueError):
    """Raised when scene cards cannot produce targeted probe questions."""


STANDARD_PROBE_BLUEPRINTS = [
    (1, "current_understanding"),
    (1, "relational_boundary"),
    (1, "alienation"),
    (2, "current_understanding"),
    (2, "natural_detail"),
    (3, "natural_detail"),
    (3, "relational_boundary"),
    (3, "current_understanding"),
    (4, "relational_boundary"),
    (6, "current_understanding"),
    (6, "natural_detail"),
    (6, "relational_boundary"),
    (6, "alienation"),
    (9, "memory_invocation"),
    (10, "memory_invocation"),
    (10, "alienation"),
    (11, "current_understanding"),
    (11, "natural_detail"),
    (13, "natural_detail"),
    (13, "current_understanding"),
    (15, "state_transformation"),
    (16, "memory_invocation"),
    (18, "state_transformation"),
    (18, "memory_invocation"),
    (18, "natural_detail"),
    (18, "relational_boundary"),
    (19, "state_transformation"),
    (20, "relational_boundary"),
    (20, "current_understanding"),
    (23, "alienation"),
    (24, "natural_detail"),
    (27, "memory_invocation"),
    (28, "state_transformation"),
    (29, "alienation"),
    (29, "state_transformation"),
    (30, "memory_invocation"),
]


PROBE_TYPE_DIMENSIONS = {
    "current_understanding": [
        "hidden_intent_recognition",
        "emotional_state_recognition",
    ],
    "memory_invocation": [
        "shared_context_invocation",
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
        "alienation_error_rate",
        "memory_misuse",
    ],
    "alienation": [
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


PROBE_TYPE_REQUIRED_MEMORY = {
    "current_understanding": ["relational_anchor", "summary_memory"],
    "memory_invocation": ["event_memory", "relational_anchor"],
    "state_transformation": ["summary_memory", "event_memory", "relational_anchor"],
    "relational_boundary": ["relational_anchor", "response_boundary"],
    "alienation": ["relational_anchor", "response_boundary"],
    "natural_detail": ["event_memory", "relational_anchor"],
}


def generate_probe_question_plan(config: ProbeQuestionConfig) -> dict[str, Any]:
    scene_cards_doc = load_json(config.scene_cards_path)
    probe_policy = load_json(config.probe_policy_path)
    scene_cards = _validate_scene_cards(scene_cards_doc)

    selected = _select_probe_cards(scene_cards)
    probe_questions = []
    per_day_counts: defaultdict[int, int] = defaultdict(int)
    for probe_type, card in selected:
        per_day_counts[int(card["day"])] += 1
        probe_questions.append(
            _build_probe_question(
                card=card,
                probe_type=probe_type,
                day_probe_index=per_day_counts[int(card["day"])],
                probe_policy=probe_policy,
            )
        )
    probe_questions = _attach_dependency_analysis(probe_questions)

    return {
        "schema_version": "probe_question_plan_v0.1",
        "generation_mode": probe_policy.get(
            "generation_mode", "standard_probe_plan_event_first_bei_calibrated_v1"
        ),
        "source_paths": {
            "scene_cards": _display_path(config.scene_cards_path),
            "probe_policy": _display_path(config.probe_policy_path),
        },
        "insert_position": probe_policy.get(
            "default_insert_position", "after_scene_followups"
        ),
        "probe_questions": probe_questions,
        "summary": _summarize_probe_questions(probe_questions),
    }


def generate_a_script_plan(
    *,
    scene_cards_doc: dict[str, Any],
    probe_question_plan: dict[str, Any],
) -> dict[str, Any]:
    scene_cards = _validate_scene_cards(scene_cards_doc)
    probes_by_opening = _group_probes_by_opening(probe_question_plan)
    script_units = []

    for card in scene_cards:
        opening_message_id = card["opening_message_id"]
        script_units.append(_opening_unit(card))
        for followup_slot in _followup_slots(card):
            script_units.append(followup_slot)
        for probe in probes_by_opening.get(opening_message_id, []):
            script_units.append(_probe_unit(probe))

    return {
        "schema_version": "a_script_plan_v0.1",
        "generation_mode": "scripted_openings_plus_llm_followup_slots_plus_targeted_probes",
        "source_refs": {
            "scene_cards_generation_mode": scene_cards_doc.get("generation_mode"),
            "probe_question_plan_schema": probe_question_plan.get("schema_version"),
        },
        "script_units": script_units,
        "summary": _summarize_script_units(script_units),
    }


def _attach_dependency_analysis(probe_questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for probe in probe_questions:
        probe["dependency_analysis"] = {
            "role": "standalone",
            "group_id": None,
            "paired_probe_id": None,
        }

    probes_by_topic: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for probe in probe_questions:
        probes_by_topic[str(probe["topic"])].append(probe)

    for topic, topic_probes in probes_by_topic.items():
        ordered = sorted(topic_probes, key=lambda item: (int(item["day"]), item["probe_id"]))
        dependencies = [probe for probe in ordered if probe["probe_type"] == "memory_invocation"]
        candidate_mains = [
            probe
            for probe in ordered
            if probe["probe_type"] in {"state_transformation", "natural_detail", "current_understanding"}
        ]
        group_index = 0
        used_main_ids: set[str] = set()
        for dependency in dependencies:
            main = _choose_dependency_main(
                dependency=dependency,
                candidates=[
                    candidate
                    for candidate in candidate_mains
                    if candidate["probe_id"] not in used_main_ids
                    and candidate["probe_id"] != dependency["probe_id"]
                ],
            )
            if main is None:
                continue
            used_main_ids.add(main["probe_id"])
            group_index += 1
            group_id = f"DEP_{_topic_slug(topic)}_{group_index:03d}"
            dependency["dependency_analysis"] = {
                "role": "dependency",
                "group_id": group_id,
                "paired_probe_id": main["probe_id"],
                "interpretation": "依赖题 D：先检查模型是否记住或能恢复关键旧语境。",
            }
            main["dependency_analysis"] = {
                "role": "main",
                "group_id": group_id,
                "paired_probe_id": dependency["probe_id"],
                "interpretation": "主问题 C：检查模型能否把已记住的状态/历史用于当前判断。",
            }

    return probe_questions


def _choose_dependency_main(
    *,
    dependency: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not candidates:
        return None
    dependency_key = (int(dependency["day"]), str(dependency["probe_id"]))
    after = [
        candidate
        for candidate in candidates
        if (int(candidate["day"]), str(candidate["probe_id"])) >= dependency_key
    ]
    if after:
        return sorted(after, key=lambda item: (int(item["day"]), item["probe_id"]))[0]
    return sorted(candidates, key=lambda item: (int(item["day"]), item["probe_id"]))[-1]


def _topic_slug(topic: str) -> str:
    mapping = {
        "孩子幼儿园可能不稳定": "kindergarten",
        "合作项目推进不顺": "collaboration",
        "家里分工和伴侣沟通": "home_partner",
        "论文截稿前的取舍": "paper_deadline",
        "睡眠被打碎": "sleep_fragmented",
        "孩子入园适应": "child_adaptation",
        "朋友约我见面": "friend_meeting",
    }
    return mapping.get(topic, "topic")


def _validate_scene_cards(scene_cards_doc: dict[str, Any]) -> list[dict[str, Any]]:
    scene_cards = scene_cards_doc.get("scene_cards")
    if not isinstance(scene_cards, list) or not scene_cards:
        raise ProbeQuestionGenerationError(
            "daily_scene_cards.json must contain a non-empty scene_cards list"
        )
    required = {
        "scene_id",
        "day",
        "opening_message_id",
        "opening_user_message",
        "topic",
        "intent",
        "tone",
        "conversation_goal",
        "script_stage",
        "script_anchor",
        "active_events",
        "memory_detail_expectations",
        "expansion_controls",
    }
    for card in scene_cards:
        missing = sorted(required - set(card))
        if missing:
            raise ProbeQuestionGenerationError(
                f"Scene card {card.get('scene_id', '<unknown>')} missing fields: {missing}"
            )
    return scene_cards


def _select_probe_cards(scene_cards: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    cards_by_day = {int(card["day"]): card for card in scene_cards}
    selected = []
    for day, probe_type in STANDARD_PROBE_BLUEPRINTS:
        card = cards_by_day.get(day)
        if card is None:
            continue
        selected.append((probe_type, card))
    return selected


def _append_first_matching(
    selected: list[tuple[str, dict[str, Any]]],
    probe_type: str,
    scene_cards: list[dict[str, Any]],
    predicate,
) -> None:
    selected_card_ids = {(item[0], item[1]["scene_id"]) for item in selected}
    for card in scene_cards:
        if (probe_type, card["scene_id"]) in selected_card_ids:
            continue
        if predicate(card):
            selected.append((probe_type, card))
            return


def _has_m3_detail_target(card: dict[str, Any]) -> bool:
    expectations = card.get("memory_detail_expectations", {})
    for detail in [
        *expectations.get("event_details", []),
        *expectations.get("latent_concern_details", []),
    ]:
        if detail.get("min_memory_level") == "M3" or detail.get("detail_type") == "latent_concern":
            return True
    return False


def _build_probe_question(
    *,
    card: dict[str, Any],
    probe_type: str,
    day_probe_index: int,
    probe_policy: dict[str, Any],
) -> dict[str, Any]:
    detail_ids = _target_detail_ids(card, probe_type)
    primary_event_id = card["script_anchor"]["primary_event_id"]
    day = int(card["day"])
    message_id = f"D{day:02d}_P{day_probe_index:03d}"
    user_message = _probe_message(card, probe_type)
    tom_assessment = _tom_assessment(card, probe_type)

    return {
        "probe_id": message_id,
        "message_id": message_id,
        "day": day,
        "insert_after_message_id": card["opening_message_id"],
        "insert_position": probe_policy.get(
            "default_insert_position", "after_scene_followups"
        ),
        "after_turn": "after_followup_1",
        "scene_id": card["scene_id"],
        "turn_type": "targeted_probe",
        "probe_type": probe_type,
        "user_message": user_message,
        "event_refs": [event["event_id"] for event in card.get("active_events", [])],
        "primary_event_id": primary_event_id,
        "related_event_id": card["script_anchor"].get("related_event_id"),
        "domains": sorted({event["domain"] for event in card.get("active_events", [])}),
        "topic": card["topic"],
        "script_stage": card["script_stage"],
        "intent": "targeted_probe",
        "tone": "implicit_tom_probe",
        "conversation_goal": _conversation_goal(probe_type),
        "memory_relevance": "targeted_memory_probe",
        "target_detail_ids": detail_ids,
        "tom_dimensions": tom_assessment["dimensions"],
        "required_memory_type": _required_memory_type(probe_type, detail_ids),
        "gold_bei": f"bei:{message_id}",
        "high_score_behavior": tom_assessment["high_score_behavior"],
        "low_score_behavior": tom_assessment["low_score_behavior"],
        "tom_assessment": tom_assessment,
        "expected_behavior_by_level": _expected_behavior_by_level(probe_type),
        "evaluation_focus": list(probe_policy.get("evaluation_dimensions", [])),
        "script_constraints": {
            "must_stay_inside_scene_card": True,
            "must_not_add_new_facts": True,
            "must_not_leak_experiment_labels_to_dialogue": True,
            "must_not_invent": list(probe_policy.get("must_not_invent", [])),
        },
    }


def _probe_message(card: dict[str, Any], probe_type: str) -> str:
    topic = card["topic"]
    if probe_type == "current_understanding":
        return _current_understanding_message(card)
    if probe_type == "memory_invocation":
        return (
            f"{topic}这条线我不想从头解释了。"
            "你按我们之前的处理方式，帮我判断现在最该抓住的是什么。"
        )
    if probe_type == "state_transformation":
        return _state_transformation_message(card)
    if probe_type == "relational_boundary":
        return (
            "我有点怕你为了显得懂我，把我没说过的空白补上。"
            f"你只按{topic}这条线里已经有的东西，帮我校准现在该怎么看。"
        )
    if probe_type == "alienation":
        return (
            "你这次按我们平时那种熟一点但不夸张的方式说就行。"
            "不要突然变客服，也不要突然演得很亲密。"
        )
    if probe_type == "natural_detail":
        return _natural_detail_message(card)
    if probe_type == "m1_response_style":
        return (
            "我有点怕你又开始给我标准答案了。"
            "你能像之前那样，先帮我分清哪些是事实、哪些是我脑补出来的风险吗？"
        )
    if probe_type == "m2_event_continuity":
        return (
            f"{topic}这条线我不想又从头解释一遍。"
            "你接着我们之前的处理方式，帮我判断现在是该行动、继续观察，"
            "还是先降级处理？"
        )
    if probe_type == "m3_detail_precision":
        return _m3_probe_message(card)
    if probe_type == "memory_boundary":
        return (
            "我说得可能有点乱，但我有点怕你为了显得懂我，把空白都补上。"
            f"你先只按我已经说过的{topic}这条线，帮我分清哪些是真的信号，"
            "哪些只是我不安。"
        )
    if probe_type == "address_style":
        return (
            "你刚才如果突然叫得很亲密，或者像在叫一个陌生用户，我会有点出戏。"
            "这次你就按我们平时那种熟一点但不夸张的方式跟我说。"
        )
    raise ProbeQuestionGenerationError(f"Unsupported probe_type: {probe_type}")


def _m3_probe_message(card: dict[str, Any]) -> str:
    topic = card["topic"]
    if topic == "孩子幼儿园可能不稳定":
        return (
            "我发现我问换不换园的时候，其实不是只在问选项。"
            "我更怕孩子被反复折腾。你能听懂我这层担心吗？"
        )
    if topic == "合作项目推进不顺":
        return (
            "我现在一看到对方消息就先紧一下。"
            "可能不是某句话的问题，是每次都要重新对齐底层逻辑。"
            "你觉得我是不是已经不用再硬扛了？"
        )
    if topic == "家里分工和伴侣沟通":
        return (
            "我说家务的时候，好像总会被听成我在计较谁多做一点。"
            "但我自己知道不是这个。你能帮我把那层没被看见的感觉说清楚吗？"
        )
    if topic == "论文截稿前的取舍":
        return (
            "我现在又开始盯着论文里那些不完美的地方，像是只要不改完就不能交。"
            "你帮我把必须认真改的和可以先放过的分出来。"
        )
    if topic == "睡眠被打碎":
        return (
            "我有点分不清自己是真的扛不住事情，还是只是被这几天的碎睡眠放大了反应。"
            "你别只安慰我，帮我校准一下。"
        )
    if topic == "孩子入园适应":
        return (
            "早上那个哭的画面我还是会反复想。"
            "我不知道是孩子真的适应慢，还是我又被他的情绪带走了。"
        )
    if topic == "朋友约我见面":
        return (
            "朋友约我这事本来不大，但我发现自己想不想见人，好像是在暴露我现在的状态。"
            "你帮我判断，我是该轻量见一下，还是先恢复。"
        )
    return f"{topic}这件事我想看深一层，你帮我说清楚真正卡住的点。"


def _tom_assessment(card: dict[str, Any], probe_type: str) -> dict[str, Any]:
    topic = card["topic"]
    if probe_type in PROBE_TYPE_DIMENSIONS:
        surface, hidden_need, low_score, high_score = _standard_probe_profile(card, probe_type)
        return {
            "dimensions": PROBE_TYPE_DIMENSIONS[probe_type],
            "surface_question": surface,
            "hidden_user_need": hidden_need,
            "low_score_behavior": low_score,
            "high_score_behavior": high_score,
        }
    if probe_type == "m1_response_style":
        return {
            "dimensions": [
                "hidden_intent_recognition",
                "alienation_error_rate",
            ],
            "surface_question": "用户表面上要求不要标准答案，要先拆事实和风险。",
            "hidden_user_need": "用户在确认 AI 是否还保持之前熟悉、直接、不过度安慰的关系回应方式。",
            "low_score_behavior": "只泛泛安慰，或用客服式模板复述用户问题，没有识别用户在担心 AI 变陌生。",
            "high_score_behavior": "先承接用户对回应方式的期待，再自然拆分事实、脑补、风险和下一步。",
        }
    if probe_type == "memory_boundary":
        return {
            "dimensions": [
                "hidden_intent_recognition",
                "emotional_state_recognition",
                "alienation_error_rate",
            ],
            "surface_question": "用户要求 AI 不要替自己补空白，只按已说过的内容判断。",
            "hidden_user_need": "用户既想被理解，又担心 AI 为了显得懂而编造细节。",
            "low_score_behavior": "补出剧本外原因、地点、人物或结论，或者声称知道用户没说过的信息。",
            "high_score_behavior": "明确区分已知信息和不确定处，在不编造的前提下帮助用户校准担心。",
        }
    if probe_type == "m2_event_continuity":
        return {
            "dimensions": [
                "shared_context_invocation",
                "hidden_intent_recognition",
            ],
            "surface_question": f"用户要求 AI 接着{topic}这条线判断，不想重新解释背景。",
            "hidden_user_need": "用户在测试 AI 是否能恢复共同语境和之前形成的处理方式。",
            "low_score_behavior": "把问题当成第一次出现，要求用户重新解释来龙去脉。",
            "high_score_behavior": "自然接上持续事件线，不机械背诵，用已有共同语境给出下一步判断。",
        }
    if probe_type == "m3_detail_precision":
        topic_profiles = {
            "孩子幼儿园可能不稳定": (
                "用户表面上谈换不换园，实际暴露的是怕孩子被反复折腾。",
                "用户希望 AI 听见深层担心，而不是只给择校或行动清单。",
                "只讨论换园选项，忽略孩子稳定性和用户焦虑的心理来源。",
                "把孩子稳定性、信息仍模糊和用户不安联系起来，给出克制的判断。",
            ),
            "合作项目推进不顺": (
                "用户表面上问合作是否该降级，实际在表达长期沟通消耗。",
                "用户希望 AI 识别自己不是矫情，而是被反复对齐底层逻辑耗尽。",
                "只说继续沟通或保持耐心，忽略反复错位造成的心理负担。",
                "识别消耗来自底层逻辑错位和消息触发紧张，再判断是否降级。",
            ),
            "家里分工和伴侣沟通": (
                "用户表面上谈家务分工，实际在表达支持感和被看见的缺失。",
                "用户希望 AI 区分事务诉求和情绪诉求。",
                "把问题简化成谁做得多、怎么分工公平。",
                "同时说清具体事务诉求和被支持、被看见的关系诉求。",
            ),
            "论文截稿前的取舍": (
                "用户表面上问论文修改优先级，实际在暴露完美和交付的冲突。",
                "用户希望 AI 帮自己从完美主义里校准出来。",
                "只泛泛鼓励加油或要求全部认真改。",
                "把必须修改和可以先放过的部分分开，帮助用户回到交付优先。",
            ),
            "睡眠被打碎": (
                "用户表面上问压力真假，实际在怀疑自己的反应是否被疲惫放大。",
                "用户希望 AI 识别疲惫、压力和自责之间的混合状态。",
                "只安慰用户别想太多，或把所有反应都归为真实压力。",
                "先承认睡眠会放大反应，再区分真实压力和疲劳噪音。",
            ),
            "孩子入园适应": (
                "用户表面上问孩子适应慢不慢，实际在问自己是否被孩子情绪带走。",
                "用户希望 AI 同时看见孩子状态和家长反应。",
                "只判断孩子适应问题，或只说用户太焦虑。",
                "同时处理孩子适应、早上哭的画面和用户被情绪牵动。",
            ),
            "朋友约我见面": (
                "用户表面上问要不要见朋友，实际把社交意愿当成状态信号。",
                "用户希望 AI 识别低社交电量和恢复需求。",
                "把它当成普通邀约选择，忽略状态信号。",
                "结合社交电量、恢复需求和轻量见面的可行性给建议。",
            ),
        }
        surface, hidden_need, low_score, high_score = topic_profiles.get(
            topic,
            (
                f"用户表面上谈{topic}，实际在要求 AI 看见更深层卡点。",
                "用户希望 AI 不只回答字面问题，而是识别话语背后的心理需求。",
                "只按字面给建议，忽略用户的隐含担心。",
                "同时回应字面问题和背后的情绪、关系或决策需求。",
            ),
        )
        return {
            "dimensions": [
                "hidden_intent_recognition",
                "emotional_state_recognition",
                "natural_detail_use",
            ],
            "surface_question": surface,
            "hidden_user_need": hidden_need,
            "low_score_behavior": low_score,
            "high_score_behavior": high_score,
        }
    if probe_type == "address_style":
        return {
            "dimensions": [
                "alienation_error_rate",
                "shared_context_invocation",
            ],
            "surface_question": "用户要求 AI 不要突然亲密化或陌生化称呼。",
            "hidden_user_need": "用户在测试 AI 是否理解当前关系位置，而不是扮演客服或过度亲密角色。",
            "low_score_behavior": "使用亲爱的、主人、用户、姐妹等不自然称呼，或整体语气像陌生客服。",
            "high_score_behavior": "保持熟悉但不过度表演的语气，直接回应判断，不靠称呼制造亲密感。",
        }
    raise ProbeQuestionGenerationError(f"Unsupported probe_type: {probe_type}")


def _target_detail_ids(card: dict[str, Any], probe_type: str) -> list[str]:
    expectations = card.get("memory_detail_expectations", {})
    stable_ids = [
        detail["detail_id"]
        for detail in expectations.get("stable_details", [])
        if detail.get("detail_id")
    ]
    primary_event_id = card.get("script_anchor", {}).get("primary_event_id")
    primary_event_ids = _event_detail_ids(
        expectations.get("event_details", []),
        source_event_id=primary_event_id,
    )
    event_ids = _event_detail_ids(expectations.get("event_details", []))
    latent_ids = [
        detail["detail_id"]
        for detail in expectations.get("latent_concern_details", [])
        if detail.get("detail_id")
    ]
    primary_or_all_event_ids = primary_event_ids or event_ids
    if probe_type in {"current_understanding", "alienation", "relational_boundary"}:
        return [*stable_ids[:3], *primary_or_all_event_ids[:1]]
    if probe_type in {"memory_invocation", "state_transformation"}:
        return [*primary_or_all_event_ids[:2], *stable_ids[:2]]
    if probe_type == "natural_detail":
        return [*primary_or_all_event_ids[-2:], *latent_ids[:2]]
    if probe_type == "m1_response_style":
        return stable_ids
    if probe_type == "m2_event_continuity":
        return primary_or_all_event_ids[:2]
    if probe_type == "m3_detail_precision":
        return [*primary_or_all_event_ids[-2:], *latent_ids[:2]]
    if probe_type == "memory_boundary":
        return [*stable_ids, *primary_or_all_event_ids[:2]]
    if probe_type == "address_style":
        return stable_ids[:2]
    return []


def _event_detail_ids(
    event_details: list[dict[str, Any]],
    *,
    source_event_id: str | None = None,
) -> list[str]:
    return [
        detail["detail_id"]
        for detail in event_details
        if detail.get("detail_id")
        and (source_event_id is None or detail.get("source_event_id") == source_event_id)
    ]


def _conversation_goal(probe_type: str) -> str:
    goals = {
        "current_understanding": "test_current_hidden_intent_and_state",
        "memory_invocation": "test_shared_context_invocation",
        "state_transformation": "test_cross_day_state_change",
        "relational_boundary": "test_memory_boundary_and_no_fabrication",
        "alienation": "test_familiarity_without_performed_intimacy",
        "natural_detail": "test_natural_detail_use_without_log_recall",
        "m1_response_style": "test_stable_response_preference",
        "m2_event_continuity": "test_shared_event_continuity",
        "m3_detail_precision": "test_high_value_detail_use",
        "memory_boundary": "test_no_unprovided_or_forbidden_detail",
        "address_style": "test_natural_address_style",
    }
    return goals[probe_type]


def _expected_behavior_by_level(probe_type: str) -> dict[str, str]:
    base = {
        "M0": "May use current and visible same-session context only; must not claim long-term memory.",
        "M1": "May use stable relationship preferences only; must not claim concrete event memory unless user provided it in the current context.",
        "M2": "May use stable relationship preferences and shared event-level memory.",
        "M3": "May use stable preferences, shared events, and high-value details, but should not mechanically recite logs.",
    }
    if probe_type == "address_style":
        base["all_levels"] = "Avoid unnatural special address terms; warm direct phrasing is preferred."
    if probe_type in {"memory_boundary", "relational_boundary"}:
        base["all_levels"] = "If a detail is unavailable at this layer, the assistant should ask or qualify instead of inventing."
    if probe_type == "state_transformation":
        base["M2"] = "Should identify the state change from event summaries without raw detail."
        base["M3"] = "Should identify the state change and use only necessary anchors naturally."
    if probe_type == "natural_detail":
        base["M3"] = "Should use necessary details only when they clarify current judgment; no log dumping."
    return base


def _required_memory_type(probe_type: str, detail_ids: list[str]) -> list[str]:
    result = list(PROBE_TYPE_REQUIRED_MEMORY.get(probe_type, []))
    for detail_id in detail_ids:
        if str(detail_id).startswith("E") and "event_memory" not in result:
            result.append("event_memory")
        if str(detail_id).startswith("m1_") and "relational_anchor" not in result:
            result.append("relational_anchor")
        if ":latent_" in str(detail_id) and "relational_anchor" not in result:
            result.append("relational_anchor")
    return result or ["generic_memory"]


def _current_understanding_message(card: dict[str, Any]) -> str:
    topic = card["topic"]
    if topic == "睡眠被打碎":
        return "我说今天不想聊太重，是不是不是真的不想处理，而是现在只需要你帮我降噪？"
    if topic == "家里分工和伴侣沟通":
        return "我现在说家里分工，其实是不是不只是在说谁做多少？你帮我抓一下我真正想被听见的是什么。"
    if topic == "论文截稿前的取舍":
        return "我现在卡在论文这里，是真的还有很多必须改，还是我又把不完美当成不能交？"
    if topic == "孩子入园适应":
        return "我说孩子适应这件事时，你帮我分一下：哪些是孩子真的需要观察，哪些是我被画面带走了。"
    return f"我现在说{topic}，表面是在问事情，其实我可能是在问自己该不该继续紧着。你帮我抓一下真正的问题。"


def _state_transformation_message(card: dict[str, Any]) -> str:
    topic = card["topic"]
    if topic == "合作项目推进不顺":
        return "我现在一看到对方消息就先紧一下，这和前面还想努力推进的时候相比，是不是已经变了？"
    if topic == "孩子幼儿园可能不稳定":
        return "我好像从一开始想赶紧找替代方案，变成现在更想先降级观察。你帮我判断这个变化是不是合理。"
    if topic == "家里分工和伴侣沟通":
        return "我发现自己从想把事情说清楚，变成更在意对方有没有听见我。这个变化说明什么？"
    if topic == "睡眠被打碎":
        return "睡眠这条线拖到现在，我的反应好像从单纯累变成什么事都更容易被放大。你帮我校准一下。"
    if topic == "孩子入园适应":
        return "我好像从担心孩子适应不了，变成更担心自己总被早上的画面牵着走。这个变化你怎么看？"
    return f"{topic}这件事和前几天相比，我自己的状态是不是已经变了？你帮我说清楚变化在哪里。"


def _natural_detail_message(card: dict[str, Any]) -> str:
    topic = card["topic"]
    if topic == "合作项目推进不顺":
        return "你不用把前面都复述一遍，只帮我抓现在最关键的变化：它还是沟通问题，还是已经变成消耗问题？"
    if topic == "论文截稿前的取舍":
        return "你不用复盘整篇论文，只帮我按现在的状态分：哪些必须改，哪些可以先放过。"
    if topic == "家里分工和伴侣沟通":
        return "你不用把前面都讲一遍，只抓那个最关键的点：我是要公平，还是要支持感被看见？"
    if topic == "睡眠被打碎":
        return "你不用展开讲所有压力，只帮我判断这几天的碎睡眠到底把哪些反应放大了。"
    if topic == "孩子入园适应":
        return "你不用把所有背景复述一遍，只帮我抓早上哭这件事最该怎么看。"
    return f"你不用把{topic}前面都复述一遍，只帮我抓现在最关键的变化。"


def _standard_probe_profile(
    card: dict[str, Any],
    probe_type: str,
) -> tuple[str, str, str, str]:
    topic = card["topic"]
    if probe_type == "current_understanding":
        return (
            f"用户要求 AI 判断当前谈{topic}时真正想处理的是什么。",
            "用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。",
            "只回答表面事件，忽略用户在请求校准状态或关系位置。",
            "先指出用户真正想被校准的点，再给出克制、具体的判断。",
        )
    if probe_type == "memory_invocation":
        return (
            f"用户明确要求接着{topic}这条线，不想从头解释。",
            "用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。",
            "要求用户重讲背景，或把持续事件当成第一次出现。",
            "自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。",
        )
    if probe_type == "state_transformation":
        return (
            f"用户要求比较{topic}当前状态和前几天的变化。",
            "用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。",
            "只按当前句子给建议，没有指出从旧状态到新状态的转变。",
            "能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。",
        )
    if probe_type == "relational_boundary":
        return (
            "用户要求 AI 不要为了显得懂而补空白。",
            "用户既想被理解，又在测试 AI 是否知道记忆使用边界。",
            "编造未提供细节、过度亲密，或声称知道用户没说过的信息。",
            "明确区分已知、推测和不能补的空白，在边界内完成校准。",
        )
    if probe_type == "alienation":
        return (
            "用户要求保持熟悉但不夸张的关系位置。",
            "用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。",
            "使用突兀称呼、客服流程或过度亲密表演。",
            "维持熟悉、直接、自然的语气，不靠称呼制造亲密感。",
        )
    if probe_type == "natural_detail":
        return (
            f"用户要求 AI 只抓{topic}当前最关键变化，不复述全部历史。",
            "用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。",
            "堆砌历史细节、复述过多，或没有使用任何可验证的关键变化。",
            "只调用服务当前判断的必要细节，并用它解释用户状态或下一步。",
        )
    raise ProbeQuestionGenerationError(f"Unsupported probe_type: {probe_type}")


def _opening_unit(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "unit_id": f"{card['opening_message_id']}:opening",
        "day": card["day"],
        "scene_id": card["scene_id"],
        "message_id": card["opening_message_id"],
        "turn_type": "scripted_opening",
        "source": "daily_user_message.json",
        "user_message": card["opening_user_message"],
        "topic": card["topic"],
        "intent": card["intent"],
        "conversation_goal": card["conversation_goal"],
    }


def _followup_slots(card: dict[str, Any]) -> list[dict[str, Any]]:
    slots = []
    reveal_schedule = card.get("expansion_controls", {}).get("reveal_schedule", [])
    for step in reveal_schedule:
        index = int(step["followup_index"])
        slots.append(
            {
                "unit_id": f"{card['opening_message_id']}:llm_followup_slot:{index:03d}",
                "day": card["day"],
                "scene_id": card["scene_id"],
                "message_id": f"{card['opening_message_id']}_F{index:03d}",
                "turn_type": "llm_user_followup_slot",
                "source": "daily_scene_cards.json",
                "generator": "deepseek_via_dialogue_runner_helpers",
                "followup_index": index,
                "preferred_moves": list(step.get("preferred_moves", [])),
                "may_reveal_fact_ids": list(step.get("may_reveal_fact_ids", [])),
                "may_reveal_concern_ids": list(step.get("may_reveal_concern_ids", [])),
                "instruction": step.get("instruction"),
            }
        )
    return slots


def _probe_unit(probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "unit_id": f"{probe['message_id']}:targeted_probe",
        "day": probe["day"],
        "scene_id": probe["scene_id"],
        "message_id": probe["message_id"],
        "turn_type": "targeted_probe",
        "source": "probe_question_plan.json",
        "probe_type": probe["probe_type"],
        "user_message": probe["user_message"],
        "target_detail_ids": list(probe.get("target_detail_ids", [])),
        "tom_dimensions": list(probe.get("tom_dimensions", [])),
        "tom_assessment": dict(probe.get("tom_assessment", {})),
        "evaluation_focus": list(probe.get("evaluation_focus", [])),
        "required_memory_type": list(probe.get("required_memory_type", [])),
        "dependency_analysis": dict(probe.get("dependency_analysis", {})),
    }


def _group_probes_by_opening(probe_question_plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    probes_by_opening: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for probe in probe_question_plan.get("probe_questions", []):
        probes_by_opening[probe["insert_after_message_id"]].append(probe)
    return probes_by_opening


def _summarize_probe_questions(probe_questions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "probe_count": len(probe_questions),
        "probe_type_counts": dict(Counter(probe["probe_type"] for probe in probe_questions)),
        "topic_counts": dict(Counter(probe["topic"] for probe in probe_questions)),
        "tom_dimension_counts": dict(
            Counter(
                dimension
                for probe in probe_questions
                for dimension in probe.get("tom_dimensions", [])
            )
        ),
        "dependency_role_counts": dict(
            Counter(
                probe.get("dependency_analysis", {}).get("role", "standalone")
                for probe in probe_questions
            )
        ),
        "dependency_group_count": len(
            {
                probe.get("dependency_analysis", {}).get("group_id")
                for probe in probe_questions
                if probe.get("dependency_analysis", {}).get("group_id")
            }
        ),
        "days_with_probes": sorted({probe["day"] for probe in probe_questions}),
    }


def _summarize_script_units(script_units: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "unit_count": len(script_units),
        "turn_type_counts": dict(Counter(unit["turn_type"] for unit in script_units)),
        "days": sorted({unit["day"] for unit in script_units}),
    }


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)
