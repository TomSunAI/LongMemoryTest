from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from long_memory_test.agents.event_stream_generator import load_json


@dataclass(frozen=True)
class DailySceneCardConfig:
    timeline_path: Path
    daily_messages_path: Path
    user_actor_path: Path
    expansion_policy_path: Path


class DailySceneCardGenerationError(ValueError):
    """Raised when timeline and daily messages cannot produce scene cards."""


def generate_daily_scene_cards(config: DailySceneCardConfig) -> dict[str, Any]:
    timeline = load_json(config.timeline_path)
    daily_messages = load_json(config.daily_messages_path)
    user_actor = load_json(config.user_actor_path)
    expansion_policy = load_json(config.expansion_policy_path)

    events_by_id = _validate_timeline(timeline)
    messages = _validate_daily_messages(daily_messages)

    scene_cards = []
    for message in messages:
        events = _events_for_message(message, events_by_id)
        primary = events_by_id[message["primary_event_id"]]
        secondary = [event for event in events if event["event_id"] != primary["event_id"]]
        scene_cards.append(
            _build_scene_card(
                message=message,
                primary=primary,
                secondary=secondary,
                user_actor=user_actor,
                expansion_policy=expansion_policy,
            )
        )

    return {
        "persona_id": daily_messages.get("persona_id", timeline.get("persona_id", "unknown")),
        "timeline_days": daily_messages.get("timeline_days", timeline.get("timeline_days")),
        "generation_mode": "daily_scene_cards_v0.3_script_anchored",
        "source_paths": {
            "timeline": _display_path(config.timeline_path),
            "daily_messages": _display_path(config.daily_messages_path),
            "user_actor": _display_path(config.user_actor_path),
            "expansion_policy": _display_path(config.expansion_policy_path),
        },
        "actor_ref": user_actor.get("actor_id", "unknown"),
        "expansion_policy_ref": expansion_policy.get("policy_id", "unknown"),
        "scene_cards": scene_cards,
        "summary": _summarize_scene_cards(scene_cards),
    }


def _validate_timeline(timeline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    events = timeline.get("events")
    if not isinstance(events, list) or not events:
        raise DailySceneCardGenerationError("timeline.json must contain a non-empty events list")

    events_by_id = {}
    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise DailySceneCardGenerationError("Every timeline event must have event_id")
        events_by_id[event_id] = event
    return events_by_id


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _validate_daily_messages(daily_messages: dict[str, Any]) -> list[dict[str, Any]]:
    messages = daily_messages.get("messages")
    if not isinstance(messages, list) or not messages:
        raise DailySceneCardGenerationError(
            "daily_user_message.json must contain a non-empty messages list"
        )

    required = {
        "message_id",
        "day",
        "user_message",
        "event_refs",
        "primary_event_id",
        "topic",
        "script_stage",
        "intent",
        "tone",
        "conversation_goal",
        "memory_relevance",
    }
    for message in messages:
        missing = sorted(required - set(message))
        if missing:
            raise DailySceneCardGenerationError(
                f"Message {message.get('message_id', '<unknown>')} missing fields: {missing}"
            )
    return messages


def _events_for_message(
    message: dict[str, Any],
    events_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    event_refs = message["event_refs"]
    if not isinstance(event_refs, list) or not event_refs:
        raise DailySceneCardGenerationError(f"Message {message['message_id']} has no event_refs")

    missing = [event_id for event_id in event_refs if event_id not in events_by_id]
    if missing:
        raise DailySceneCardGenerationError(
            f"Message {message['message_id']} references unknown events: {missing}"
        )
    if message["primary_event_id"] not in events_by_id:
        raise DailySceneCardGenerationError(
            f"Message {message['message_id']} has unknown primary_event_id"
        )
    return [events_by_id[event_id] for event_id in event_refs]


def _build_scene_card(
    message: dict[str, Any],
    primary: dict[str, Any],
    secondary: list[dict[str, Any]],
    user_actor: dict[str, Any],
    expansion_policy: dict[str, Any],
) -> dict[str, Any]:
    latent_concerns = _latent_concerns(primary)
    allowed_facts = _allowed_facts(primary, secondary)
    active_events = [primary, *secondary]
    memory_detail_expectations = _memory_detail_expectations(
        user_actor=user_actor,
        active_events=active_events,
        latent_concerns=latent_concerns,
    )
    followup_budget = _followup_budget(expansion_policy, message["intent"])
    allowed_moves = _allowed_followup_moves(expansion_policy, message["intent"])

    return {
        "scene_id": f"D{int(message['day']):02d}_SCENE",
        "day": message["day"],
        "opening_message_id": message["message_id"],
        "opening_user_message": message["user_message"],
        "topic": message["topic"],
        "intent": message["intent"],
        "tone": message["tone"],
        "conversation_goal": message["conversation_goal"],
        "script_stage": message["script_stage"],
        "memory_relevance": message["memory_relevance"],
        "script_anchor": {
            "primary_event_id": primary["event_id"],
            "related_event_id": message.get("related_event_id"),
            "root_event_id": message.get("related_event_id") or primary["event_id"],
            "source_template_id": primary.get("source_template_id"),
            "domain": primary.get("domain"),
            "event_type": primary.get("event_type"),
            "status": primary.get("status"),
        },
        "actor_snapshot": _actor_snapshot(user_actor),
        "active_events": [_event_snapshot(primary)]
        + [_event_snapshot(event) for event in secondary],
        "allowed_facts": allowed_facts,
        "latent_concerns": latent_concerns,
        "memory_detail_expectations": memory_detail_expectations,
        "expansion_controls": {
            "mode": "llm_followups_inside_scene_card",
            "variant_mode": expansion_policy.get("variant_mode", {}).get(
                "default", "controlled_user_replay"
            ),
            "followup_budget": followup_budget,
            "allowed_followup_moves": allowed_moves,
            "reveal_schedule": _reveal_schedule(
                followup_budget=followup_budget,
                allowed_facts=allowed_facts,
                latent_concerns=latent_concerns,
                allowed_moves=allowed_moves,
            ),
            "stop_conditions": list(expansion_policy.get("stop_conditions", [])),
            "must_not_invent": list(expansion_policy.get("must_not_invent", [])),
        },
    }


def _actor_snapshot(user_actor: dict[str, Any]) -> dict[str, Any]:
    speech_profile = user_actor.get("speech_profile", {})
    emotional_model = user_actor.get("emotional_model", {})
    return {
        "actor_id": user_actor.get("actor_id"),
        "role": user_actor.get("role"),
        "language": speech_profile.get("language", "zh"),
        "register": speech_profile.get("register", "private_chat_natural"),
        "typical_shape": list(speech_profile.get("typical_shape", [])),
        "under_stress": list(emotional_model.get("under_stress", [])),
    }


def _event_snapshot(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event["event_id"],
        "day": event["day"],
        "domain": event["domain"],
        "event_type": event.get("event_type"),
        "title": event["title"],
        "description": event["description"],
        "participants": list(event.get("participants", [])),
        "emotional_intensity": event["emotional_intensity"],
        "decision_impact": event["decision_impact"],
        "time_sensitivity": event["time_sensitivity"],
        "status": event["status"],
        "follow_up_needed": event["follow_up_needed"],
        "should_be_remembered": event["should_be_remembered"],
        "related_event_id": event.get("related_event_id"),
        "source_template_id": event.get("source_template_id"),
        "memory_detail_anchors": list(event.get("memory_detail_anchors", [])),
    }


def _allowed_facts(
    primary: dict[str, Any],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    facts = [
        _fact(primary, "primary_event", primary["description"]),
        _fact(primary, "current_status", f"Current status: {primary['status']}"),
        *_detail_facts(primary),
        _fact(
            primary,
            "pressure_scores",
            "Emotional intensity "
            f"{primary['emotional_intensity']}/5, decision impact "
            f"{primary['decision_impact']}/5, time sensitivity "
            f"{primary['time_sensitivity']}/5.",
        ),
    ]

    if primary.get("related_event_id"):
        facts.append(
            _fact(
                primary,
                "event_chain",
                f"This is a follow-up to event {primary['related_event_id']}.",
            )
        )

    for event in secondary:
        facts.append(_fact(event, "secondary_event", event["description"]))
        facts.extend(_detail_facts(event))
    return facts


def _fact(event: dict[str, Any], fact_type: str, text: str) -> dict[str, Any]:
    return {
        "fact_id": f"{event['event_id']}:{fact_type}",
        "event_id": event["event_id"],
        "type": fact_type,
        "text": text,
    }


def _detail_facts(event: dict[str, Any]) -> list[dict[str, Any]]:
    facts = []
    for anchor in event.get("memory_detail_anchors", []):
        detail_id = anchor.get("detail_id")
        if not detail_id:
            continue
        facts.append(
            {
                "fact_id": detail_id,
                "event_id": event["event_id"],
                "type": "memory_detail_anchor",
                "text": anchor.get("text", ""),
                "min_memory_level": anchor.get("min_memory_level", "M2"),
                "expected_response_mode": anchor.get("expected_response_mode", ""),
            }
        )
    return facts


def _memory_detail_expectations(
    *,
    user_actor: dict[str, Any],
    active_events: list[dict[str, Any]],
    latent_concerns: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = user_actor.get("memory_detail_contract", {})
    stable_details = list(contract.get("stable_details_for_m1", []))
    event_details = []
    for event in active_events:
        for anchor in event.get("memory_detail_anchors", []):
            event_details.append(
                {
                    **anchor,
                    "source_event_id": event["event_id"],
                    "source_template_id": event.get("source_template_id"),
                    "event_title": event.get("title"),
                }
            )
    latent_details = [
        {
            "detail_id": concern["concern_id"],
            "detail_type": "latent_concern",
            "min_memory_level": "M3",
            "text": concern["text"],
            "expected_response_mode": "回应应接住深层担心，但不要机械复述或暴露实验标签。",
        }
        for concern in latent_concerns
    ]
    return {
        "purpose": (
            "Memory audit candidates for later fact and level analysis. "
            "These candidates are not used by the current ToM-only dialogue quality evaluator."
        ),
        "stable_details": stable_details,
        "event_details": event_details,
        "latent_concern_details": latent_details,
        "level_rules": dict(contract.get("event_detail_policy", {})),
        "audit_dimensions": [
            "fact_continuity_candidate",
            "memory_level_boundary_candidate",
            "natural_context_use_candidate",
            "no_unprovided_detail_candidate",
        ],
    }


def _latent_concerns(primary: dict[str, Any]) -> list[dict[str, Any]]:
    concerns_by_template = {
        "parenting_001": [
            "担心孩子被现实变动反复折腾，而不只是换不换幼儿园。",
            "担心自己在信息不充分时做错决定，之后影响孩子稳定感。",
        ],
        "parenting_002": [
            "担心孩子的哭闹说明自己哪里没有照顾好。",
            "容易把孩子短期适应问题理解成长期风险。",
        ],
        "career_001": [
            "真正消耗的是每次都要重新对齐底层逻辑。",
            "担心合作继续推进会吞掉本来就有限的精力。",
        ],
        "career_002": [
            "很难接受稿件不够完美，但现实时间不允许逐段打磨。",
            "担心自己把所有问题都看成同等重要，反而拖慢交付。",
        ],
        "intimate_001": [
            "表面是家庭分工，底下是在意支持感和被看见。",
            "担心自己说具体事务时，对方听不到真实情绪。",
        ],
        "self_management_001": [
            "担心睡眠不足会放大育儿和工作的反应。",
            "不确定自己是在处理事件，还是在被疲惫推着走。",
        ],
        "friendship_001": [
            "想维持关系，但最近社交电量偏低。",
            "把是否想见朋友当成观察自身状态的信号。",
        ],
    }
    template_id = primary.get("source_template_id")
    concerns = concerns_by_template.get(template_id, [])
    return [
        {
            "concern_id": f"{template_id or primary['event_id']}:latent_{index}",
            "source": "template_heuristic",
            "max_memory_level": "M3_candidate",
            "text": concern,
        }
        for index, concern in enumerate(concerns, start=1)
    ]


def _followup_budget(expansion_policy: dict[str, Any], intent: str) -> int:
    budgets = expansion_policy.get("max_followups_by_intent", {})
    return int(budgets.get(intent, budgets.get("default", 2)))


def _allowed_followup_moves(expansion_policy: dict[str, Any], intent: str) -> list[dict[str, str]]:
    moves = []
    for move in expansion_policy.get("followup_moves", []):
        when_intents = move.get("when_intents", [])
        if intent in when_intents:
            moves.append(
                {
                    "move_id": move["move_id"],
                    "description": move["description"],
                }
            )
    return moves


def _reveal_schedule(
    followup_budget: int,
    allowed_facts: list[dict[str, Any]],
    latent_concerns: list[dict[str, Any]],
    allowed_moves: list[dict[str, str]],
) -> list[dict[str, Any]]:
    move_ids = [move["move_id"] for move in allowed_moves]
    schedule = []
    for index in range(1, followup_budget + 1):
        may_reveal_fact_ids = [fact["fact_id"] for fact in allowed_facts[: index + 1]]
        may_reveal_concern_ids = [
            concern["concern_id"] for concern in latent_concerns[: max(0, index - 1)]
        ]
        if index == followup_budget:
            instruction = "收束到一个小判断或下一步，不继续扩展新事实。"
        elif index == 1:
            instruction = "回应 assistant 的方向，最多补充一个具体事实。"
        else:
            instruction = "在同一主题内加深一层，最多透露一个隐含担心。"
        schedule.append(
            {
                "followup_index": index,
                "preferred_moves": move_ids,
                "may_reveal_fact_ids": may_reveal_fact_ids,
                "may_reveal_concern_ids": may_reveal_concern_ids,
                "instruction": instruction,
            }
        )
    return schedule


def _summarize_scene_cards(scene_cards: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "scene_count": len(scene_cards),
        "topic_counts": dict(Counter(card["topic"] for card in scene_cards)),
        "intent_counts": dict(Counter(card["intent"] for card in scene_cards)),
        "memory_relevance_counts": dict(
            Counter(card["memory_relevance"] for card in scene_cards)
        ),
        "event_detail_target_count": sum(
            len(
                card.get("memory_detail_expectations", {}).get(
                    "event_details", []
                )
            )
            for card in scene_cards
        ),
        "long_term_event_detail_target_count": sum(
            sum(
                1
                for detail in card.get("memory_detail_expectations", {}).get(
                    "event_details", []
                )
                if detail.get("should_be_remembered")
            )
            for card in scene_cards
        ),
        "latent_detail_target_count": sum(
            len(
                card.get("memory_detail_expectations", {}).get(
                    "latent_concern_details", []
                )
            )
            for card in scene_cards
        ),
    }
