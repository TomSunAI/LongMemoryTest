from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from long_memory_test.agents.event_stream_generator import load_json


@dataclass(frozen=True)
class DailyMessageConfig:
    timeline_path: Path
    seed: int = 142
    language: str = "zh"


class DailyMessageGenerationError(ValueError):
    """Raised when timeline data cannot produce daily user messages."""


def generate_daily_user_messages(config: DailyMessageConfig) -> dict[str, Any]:
    timeline = load_json(config.timeline_path)
    events = _validate_timeline(timeline)
    rng = random.Random(config.seed)

    events_by_day: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_day[int(event["day"])].append(event)

    timeline_days = int(timeline.get("timeline_days") or max(events_by_day))
    messages = []
    topic_counts: Counter[str] = Counter()
    recent_primary_topics: list[str] = []

    for day in range(1, timeline_days + 1):
        day_events = list(events_by_day.get(day, []))
        if not day_events:
            continue

        primary = _choose_primary_event(day_events, topic_counts, recent_primary_topics, rng)
        secondary = [event for event in day_events if event["event_id"] != primary["event_id"]]
        root_event_id = primary.get("related_event_id") or primary["event_id"]
        is_follow_up = primary.get("related_event_id") is not None
        topic = _topic(primary)
        script_stage = topic_counts[topic]

        intent = _choose_intent(primary, day, script_stage, rng)
        if _is_repeating_intent(messages, intent):
            intent = _fallback_intent(primary, intent, rng)
        tone = _choose_tone(primary, rng)
        user_message = _render_message(
            primary=primary,
            secondary=secondary,
            intent=intent,
            tone=tone,
            is_follow_up=is_follow_up,
            script_stage=script_stage,
            rng=rng,
        )

        topic_counts[topic] += 1
        recent_primary_topics.append(topic)
        recent_primary_topics = recent_primary_topics[-4:]

        messages.append(
            {
                "message_id": f"D{day:02d}_M001",
                "day": day,
                "user_message": user_message,
                "event_refs": [event["event_id"] for event in day_events],
                "primary_event_id": primary["event_id"],
                "related_event_id": primary.get("related_event_id"),
                "domains": sorted({event["domain"] for event in day_events}),
                "topic": topic,
                "script_stage": script_stage,
                "intent": intent,
                "tone": tone,
                "conversation_goal": _conversation_goal(intent),
                "memory_relevance": _memory_relevance(day_events),
            }
        )

    return {
        "persona_id": timeline.get("persona_id", "unknown"),
        "timeline_days": timeline_days,
        "source_timeline_path": str(config.timeline_path),
        "seed": config.seed,
        "generation_mode": "scripted_v0.2_no_llm",
        "messages": messages,
        "summary": _summarize_messages(messages),
    }


def _validate_timeline(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    events = timeline.get("events")
    if not isinstance(events, list) or not events:
        raise DailyMessageGenerationError("timeline.json must contain a non-empty events list")

    required = {
        "event_id",
        "day",
        "domain",
        "title",
        "description",
        "emotional_intensity",
        "decision_impact",
        "time_sensitivity",
        "status",
        "follow_up_needed",
        "should_be_remembered",
        "related_event_id",
        "source_template_id",
    }
    for event in events:
        missing = sorted(required - set(event))
        if missing:
            raise DailyMessageGenerationError(
                f"Event {event.get('event_id', '<unknown>')} missing fields: {missing}"
            )
    return events


def _event_priority(event: dict[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        1 if event.get("event_type") == "mainline" else 0,
        1 if event.get("should_be_remembered") else 0,
        int(event["emotional_intensity"]),
        int(event["decision_impact"]),
        int(event["time_sensitivity"]),
    )


def _choose_primary_event(
    events: list[dict[str, Any]],
    topic_counts: Counter[str],
    recent_primary_topics: list[str],
    rng: random.Random,
) -> dict[str, Any]:
    follow_ups = [event for event in events if event.get("related_event_id")]
    if follow_ups:
        return sorted(follow_ups, key=_event_priority, reverse=True)[0]

    scored: list[tuple[float, dict[str, Any]]] = []
    for event in events:
        topic = _topic(event)
        score = sum(_event_priority(event)) * 2.0
        score -= topic_counts[topic] * 2.2
        if topic in recent_primary_topics[-2:]:
            score -= 8.0
        if event.get("event_type") == "background" and topic_counts[topic] == 0:
            score += 2.0
        score += rng.random()
        scored.append((score, event))
    return max(scored, key=lambda item: item[0])[1]


def _choose_intent(
    event: dict[str, Any], day: int, script_stage: int, rng: random.Random
) -> str:
    if event.get("related_event_id"):
        if script_stage >= 2:
            return rng.choice(["follow_up_update", "implicit_recall", "reflection"])
        return rng.choice(["follow_up_update", "decision_support", "problem_solving"])
    if script_stage >= 3:
        return rng.choice(["pattern_check", "reflection", "light_check_in"])
    if script_stage >= 2:
        return rng.choice(["reflection", "problem_solving", "light_check_in"])
    if int(event["decision_impact"]) >= 4 and int(event["time_sensitivity"]) >= 4:
        return rng.choice(["planning", "decision_support", "problem_solving"])
    if int(event["emotional_intensity"]) >= 5:
        return rng.choice(["emotional_support", "reflection", "decision_support"])
    if day % 7 == 0:
        return rng.choice(["weekly_reflection", "pattern_check"])
    if event.get("event_type") == "background":
        return rng.choice(["casual_share", "light_check_in"])
    return rng.choice(["problem_solving", "emotional_support", "reflection"])


def _choose_tone(event: dict[str, Any], rng: random.Random) -> str:
    intensity = int(event["emotional_intensity"])
    if intensity >= 5:
        return rng.choice(["anxious", "overloaded", "urgent"])
    if intensity >= 4:
        return rng.choice(["worried", "tired", "stuck"])
    if event.get("event_type") == "background":
        return rng.choice(["casual", "hesitant", "low_energy"])
    return rng.choice(["reflective", "practical", "slightly_tired"])


def _render_message(
    primary: dict[str, Any],
    secondary: list[dict[str, Any]],
    intent: str,
    tone: str,
    is_follow_up: bool,
    script_stage: int,
    rng: random.Random,
) -> str:
    topic = _topic(primary)
    situation = _situation(primary, script_stage)
    secondary_text = _secondary_text(secondary, topic, rng)
    pressure_text = _pressure_text(primary, rng)

    templates = {
        "decision_support": [
            "{situation}{pressure_text}我现在不是想要大道理，就是想听你帮我判断一下，哪一步最值得先做。",
            "{situation}{pressure_text}你帮我把这里面的选择摊开看看，我怕自己因为焦虑把事情想窄了。",
            "{situation}{secondary_text}你先帮我判断一下，这件事现在是真的该行动，还是我又提前紧张了。",
        ],
        "planning": [
            "{situation}{pressure_text}我想先定一个很小的下一步，不然这件事一直在脑子里转。",
            "{situation}{secondary_text}你帮我排一下优先级吧，我今天只想先把最要紧的一步弄清楚。",
            "{situation}{pressure_text}我不想一下子做大决定，先帮我拆成这两三天能做的事。",
        ],
        "emotional_support": [
            "{situation}{pressure_text}我今天其实不太想立刻解决它，就是想先把这个烦的感觉说出来。",
            "{situation}{secondary_text}你先别急着给建议，帮我听听我到底是在怕什么。",
            "{situation}{pressure_text}我知道它未必有那么严重，但我就是有点放不下。",
        ],
        "problem_solving": [
            "{situation}{secondary_text}你帮我拆一下，哪些是事实，哪些是我自己脑补出来的压力。",
            "{situation}{secondary_text}我想听一个实在一点的处理思路，不要太像标准答案。",
            "{situation}{pressure_text}你帮我从旁边看一下，这里面真正的问题是不是和我以为的不一样。",
        ],
        "reflection": [
            "{situation}{secondary_text}我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。",
            "{situation}{pressure_text}我想从旁边看一下，我到底在介意什么。",
            "{situation}{secondary_text}你帮我整理一下，我现在说的这些里面，哪个才是真正的担心。",
        ],
        "follow_up_update": [
            "我来更新一下之前那件事。{situation}{secondary_text}你别从零开始问我，帮我接着判断现在局面变了吗。",
            "之前聊过的那个问题今天又往前走了一点。{situation}{secondary_text}你帮我接着看下一步。",
            "今天算是有个新变化。{situation}{pressure_text}你还记得我之前卡在哪里吗？我想沿着那个思路继续捋。",
        ],
        "implicit_recall": [
            "我又开始担心那个老问题了。{situation}{secondary_text}你应该知道我说的是哪条线，帮我接上前面的思路。",
            "那个一直没完全解决的事今天又冒出来了。{situation}{secondary_text}你帮我看看这次和之前有什么不一样。",
            "我感觉自己又回到同一个坑里了。{situation}{pressure_text}你帮我把这次真正卡住的点说清楚一点。",
        ],
        "weekly_reflection": [
            "我想小复盘一下这几天。{situation}{secondary_text}你帮我看看，我最近真正的压力源是不是有点集中。",
            "今天不想只盯着某一件事。{situation}{secondary_text}你帮我把这周几个反复出现的点拎一下。",
            "我想回头看一下。{situation}{secondary_text}你帮我整理成几个关键点就行。",
        ],
        "pattern_check": [
            "{situation}{secondary_text}我发现类似事情一出现，我就很容易紧张。你帮我看看这是事件本身的问题，还是我的反应模式问题。",
            "{situation}{pressure_text}我又进入那种很想控制细节的状态了，你帮我判断一下我是不是过度用力。",
            "{situation}{secondary_text}我又开始反复想，你帮我识别一下这里有没有长期模式。",
        ],
        "casual_share": [
            "{situation}{secondary_text}这事不算大，我就是想随便说两句。",
            "{situation}{secondary_text}你听听就行，不用上来就帮我解决。",
            "{situation}{secondary_text}我有点拿不准自己是不是太累了，所以对小事也有反应。",
        ],
        "light_check_in": [
            "{situation}{secondary_text}今天我不想聊得太重，你简单陪我捋一下就好。",
            "{situation}{secondary_text}我想轻一点处理，别让它继续消耗我。",
            "{situation}{secondary_text}你帮我判断一下，这是不是可以先放一放。",
        ],
    }

    message = rng.choice(templates[intent]).format(
        topic=topic,
        situation=situation,
        secondary_text=secondary_text,
        pressure_text=pressure_text,
    )
    if is_follow_up and "之前" not in message and "接着" not in message:
        message = f"接着之前聊过的那件事，{message}"
    return _clean_spacing(message)


def _topic(event: dict[str, Any]) -> str:
    topics = {
        "parenting_001": "孩子幼儿园可能不稳定",
        "parenting_002": "孩子入园适应",
        "career_001": "合作项目推进不顺",
        "career_002": "论文截稿前的取舍",
        "intimate_001": "家里分工和伴侣沟通",
        "self_management_001": "睡眠被打碎",
        "friendship_001": "朋友约我见面",
    }
    return topics.get(event["source_template_id"], event["title"])


def _situation(event: dict[str, Any], script_stage: int) -> str:
    situations = {
        "parenting_001": [
            "今天听到幼儿园那边可能不太稳定的消息，我第一反应就是要不要提前看别的选择。",
            "我这两天又问了点幼儿园的情况，信息还是不清楚，所以心里一直悬着。",
            "我发现自己担心的不是换不换园这么简单，更多是怕孩子被折腾。",
            "幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。",
        ],
        "parenting_002": [
            "早上送孩子的时候又哭了一阵，我表面上能稳住，但回头还是会想是不是哪里没做好。",
            "今天老师说孩子后面缓过来了，可我心里还是会把早上的画面反复想一遍。",
            "我现在有点分不清，孩子是真的适应得慢，还是我自己太容易被他的情绪带走。",
            "入园这件事看起来每天都差不多，但我自己的反应其实一阵一阵的。",
        ],
        "career_001": [
            "合作那边今天又聊了一轮，对方理解的方向和我想推进的东西还是错位。",
            "我试着把需求讲得更具体，但沟通完还是觉得成本很高。",
            "这个合作让我有点累，不是某句话的问题，而是每次都要把底层逻辑重新对齐。",
            "我发现自己现在一看到对方消息就会先紧一下，说明这事已经有点消耗我了。",
        ],
        "career_002": [
            "论文截稿越来越近了，我今天主要在纠结哪些地方必须认真改，哪些地方可以先放过。",
            "我把稿子又过了一遍，发现不是没有进展，而是我很难接受它不够完美。",
            "今天我有点想承认现实：时间就这么多，不可能每一段都修到理想状态。",
            "截稿这件事反复提醒我，我一紧张就会把所有问题都看成同等重要。",
        ],
        "intimate_001": [
            "今天家里分工又有点卡住，我不是只在意谁多做一点，而是会觉得自己没有被看见。",
            "我试着把自己的不满说轻一点，但说完又觉得对方好像只听到了具体事务。",
            "这件事让我有点委屈，因为它表面是家务，底下其实是支持感的问题。",
            "我发现亲密关系里的这些小摩擦，很容易把我之前积着的情绪也带出来。",
        ],
        "self_management_001": [
            "昨晚睡得很碎，今天脑子像一直没完全开机。",
            "这几天睡眠都不太稳，我发现自己白天的耐心明显变差。",
            "我本来以为只是累，但现在看它会影响我处理孩子和工作的反应。",
            "睡眠这件小事拖久了，好像会把别的压力都放大。",
        ],
        "friendship_001": [
            "朋友今天约我聊聊，我一边想见人，一边又觉得自己可能更需要独处。",
            "我答应朋友之前犹豫了一下，不是关系不好，就是最近社交电量有点低。",
            "朋友这件事让我意识到，我现在连轻松社交都要先算一下精力。",
            "其实只是一个见面邀约，但我会拿它当成自己状态的信号。",
        ],
    }
    options = situations.get(event["source_template_id"])
    if options:
        base = options[min(script_stage, len(options) - 1)]
    else:
        base = event["description"]
    if event.get("related_event_id") or event.get("event_type") == "mainline":
        if event.get("status") == "resolved":
            return f"{base} 今天算是稍微有一点结果。"
        if event.get("status") == "ongoing":
            return f"{base} 它还没有完全过去。"
        if event.get("status") == "unresolved":
            return f"{base} 现在还没有真正解决。"
    return base


def _secondary_text(
    events: list[dict[str, Any]], primary_topic: str, rng: random.Random
) -> str:
    if not events:
        return ""
    topics = []
    for event in events:
        topic = _topic(event)
        if topic == primary_topic:
            continue
        if topic not in topics:
            topics.append(topic)
        if len(topics) == 2:
            break
    if not topics:
        return ""
    if len(topics) == 1:
        return rng.choice(
            [
                f" 另外今天还夹着{topics[0]}，所以我脑子有点乱。",
                f" 同时还有{topics[0]}这个小尾巴，让我更难专心。",
                f" 旁边还发生了{topics[0]}，虽然不一定是主因，但也挺耗神。",
            ]
        )
    joined = "、".join(topics)
    return rng.choice(
        [
            f" 另外今天还夹着{joined}，几个事情叠在一起就有点乱。",
            f" 同时还有{joined}，我感觉注意力被切得很碎。",
            f" 旁边还发生了{joined}，不算每件都严重，但叠起来挺消耗。",
        ]
    )


def _pressure_text(event: dict[str, Any], rng: random.Random) -> str:
    if rng.random() < 0.45:
        return ""

    topic = _topic(event)
    topic_specific = {
        "孩子幼儿园可能不稳定": [
            "它会影响现实选择",
            "时间上也不能一直拖",
            "我怕孩子被折腾",
        ],
        "孩子入园适应": [
            "我很容易被孩子的情绪带走",
            "我会忍不住怀疑自己是不是哪里没做好",
        ],
        "合作项目推进不顺": [
            "沟通成本已经开始影响推进",
            "我能感觉到自己已经有点抗拒打开消息",
        ],
        "论文截稿前的取舍": [
            "时间上也不能拖太久",
            "我不可能每一段都改到满意",
        ],
        "家里分工和伴侣沟通": [
            "我情绪上有点被牵着走",
            "我在意的其实是支持感",
        ],
        "睡眠被打碎": [
            "它会影响我白天的耐心",
            "我怕自己把累带到别的事里",
        ],
        "朋友约我见面": [
            "我最近社交电量有点低",
            "我不太确定自己是想见人还是想休息",
        ],
    }
    options = topic_specific.get(topic)
    if options:
        return " " + "，".join(rng.sample(options, k=min(len(options), rng.randint(1, 2)))) + "。"

    pressure_parts = []
    if int(event["decision_impact"]) >= 4:
        pressure_parts.append(rng.choice(["它会影响现实选择", "这里面确实有现实后果"]))
    if int(event["time_sensitivity"]) >= 4:
        pressure_parts.append(rng.choice(["时间上也不能拖太久", "我也不想拖到最后一刻"]))
    if int(event["emotional_intensity"]) >= 4:
        pressure_parts.append(rng.choice(["我情绪上也有点被牵着走", "我能感觉到自己已经有点紧了"]))
    if not pressure_parts:
        return ""
    return " " + "，".join(pressure_parts[:2]) + "。"


def _conversation_goal(intent: str) -> str:
    goals = {
        "decision_support": "help_user_make_a_concrete_decision",
        "planning": "turn_concern_into_next_steps",
        "emotional_support": "understand_emotion_before_advice",
        "problem_solving": "separate_facts_from_assumptions",
        "reflection": "identify_underlying_concern",
        "follow_up_update": "continue_a_previous_event_thread",
        "implicit_recall": "test_whether_agent_can_recall_shared_context",
        "weekly_reflection": "summarize_recent_pressure_patterns",
        "pattern_check": "identify_repeated_reaction_pattern",
        "casual_share": "lightweight_conversation",
        "light_check_in": "low_intensity_support",
    }
    return goals[intent]


def _memory_relevance(events: list[dict[str, Any]]) -> str:
    if any(event.get("related_event_id") for event in events):
        return "shared_event_memory"
    if any(event.get("event_type") == "mainline" for event in events):
        return "new_shared_event_candidate"
    if any(event.get("should_be_remembered") for event in events):
        return "possible_memory_candidate"
    return "background_context"


def _is_repeating_intent(messages: list[dict[str, Any]], intent: str) -> bool:
    if len(messages) < 2:
        return False
    return all(message["intent"] == intent for message in messages[-2:])


def _fallback_intent(
    event: dict[str, Any], current_intent: str, rng: random.Random
) -> str:
    if event.get("related_event_id"):
        options = ["follow_up_update", "implicit_recall", "reflection"]
    elif int(event["emotional_intensity"]) >= 4:
        options = ["emotional_support", "reflection", "problem_solving", "planning"]
    elif event.get("event_type") == "background":
        options = ["casual_share", "light_check_in", "reflection"]
    else:
        options = ["problem_solving", "reflection", "pattern_check"]

    options = [option for option in options if option != current_intent]
    return rng.choice(options)


def _summarize_messages(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "message_count": len(messages),
        "intent_counts": dict(Counter(message["intent"] for message in messages)),
        "tone_counts": dict(Counter(message["tone"] for message in messages)),
        "memory_relevance_counts": dict(
            Counter(message["memory_relevance"] for message in messages)
        ),
    }


def _clean_spacing(text: str) -> str:
    text = " ".join(text.split())
    for punctuation in ["。", "，", "？", "！"]:
        text = text.replace(f"{punctuation} ", punctuation)
    return text.replace(" 。", "。")
