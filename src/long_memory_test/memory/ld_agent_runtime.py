from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any

from long_memory_test.memory.schema import MemoryRecord


LD_AGENT_REFERENCE = {
    "repo": "https://github.com/leolee99/LD-Agent",
    "commit": "af3c15ab63efcb4ab83d635670b316d63977d106",
    "modules": ["Module/EventMemory.py", "Module/Personas.py"],
    "usage": "memory_only_no_generator_or_checkpoint",
}


class LDAgentMemoryRuntime:
    """Local memory-only adapter for the LD-Agent M0 baseline.

    The official LD-Agent memory design keeps a short-term memory bank for the
    current session and writes a summarized session into long-term event memory
    when the session changes. This adapter follows that memory behavior while
    keeping response generation in this repository's controlled base LLM.
    """

    def __init__(
        self,
        *,
        top_k: int = 5,
        short_term_k: int = 5,
        semantic_weight: float = 0.8,
        recency_weight: float = 0.2,
    ) -> None:
        self.top_k = top_k
        self.short_term_k = short_term_k
        self.semantic_weight = semantic_weight
        self.recency_weight = recency_weight
        self.current_session_day: int | None = None
        self.short_term_session: list[dict[str, Any]] = []
        self.memories: OrderedDict[str, MemoryRecord] = OrderedDict()
        self.actions: list[dict[str, Any]] = []

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any] | None) -> "LDAgentMemoryRuntime":
        runtime = cls(
            top_k=int((snapshot or {}).get("top_k", 5) or 5),
            short_term_k=int((snapshot or {}).get("short_term_k", 5) or 5),
        )
        if not snapshot:
            return runtime
        runtime.current_session_day = snapshot.get("current_session_day")
        runtime.short_term_session = list(snapshot.get("short_term_session", []))
        runtime.memories = OrderedDict(
            (str(item.get("memory_id")), MemoryRecord.from_dict(item))
            for item in snapshot.get("memories", [])
            if isinstance(item, dict) and item.get("memory_id")
        )
        runtime.actions = list(snapshot.get("actions", []))
        return runtime

    @classmethod
    def from_completed_turns(
        cls,
        turns: list[dict[str, Any]],
        *,
        top_k: int = 5,
        short_term_k: int = 5,
    ) -> "LDAgentMemoryRuntime":
        runtime = cls(top_k=top_k, short_term_k=short_term_k)
        for turn in turns:
            message = dict(turn.get("input", {}))
            variants = turn.get("variants", {})
            m0_answer = ""
            if isinstance(variants, dict) and "M0" in variants:
                m0_answer = str(variants["M0"].get("assistant_answer", ""))
            runtime.record_completed_turn(
                message=message,
                assistant_answer=m0_answer,
                run_id=str(turn.get("run_id", "")),
            )
        return runtime

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": "ld_agent_memory_runtime_v1",
            "provider": "ld_agent_memory",
            "ld_agent_reference": dict(LD_AGENT_REFERENCE),
            "top_k": self.top_k,
            "short_term_k": self.short_term_k,
            "current_session_day": self.current_session_day,
            "short_term_session": list(self.short_term_session),
            "memories": [memory.to_dict() for memory in self.memories.values()],
            "actions": list(self.actions),
        }

    def retrieve_payload(self, message: dict[str, Any]) -> dict[str, Any]:
        self.prepare_for_turn(message)
        query = self._query_text(message)
        current_day = _safe_int(message.get("day"))
        event_hits = self._retrieve(
            query=query,
            current_day=current_day,
            memory_type="event_memory",
            top_k=self.top_k,
        )
        persona_hits = self._retrieve(
            query=query,
            current_day=current_day,
            memory_type="persona_memory",
            top_k=min(3, self.top_k),
        )
        short_term_lines = self._short_term_lines()
        lines = [
            "LD-Agent memory baseline (memory-only M0).",
            "Reference: leolee99/LD-Agent Module/EventMemory.py and Module/Personas.py; response generator/checkpoints are not used.",
            "Short-term memory bank:",
        ]
        lines.extend(short_term_lines or ["- 当前 session 内暂无更早用户 turn。"])
        lines.append("Retrieved long-term event memories:")
        lines.extend(
            [
                "- "
                + item["memory"]["summary"]
                + f" (source_session={item['memory']['source_session']}, importance={item['memory']['importance']})"
                for item in event_hits
            ]
            or ["- 当前没有检索到相关普通事件记忆。"]
        )
        lines.append("Retrieved persona memories:")
        lines.extend(
            ["- " + item["memory"]["summary"] for item in persona_hits]
            or ["- 当前没有检索到相关普通 persona 记忆。"]
        )
        lines.append("Use memories only when they are relevant. Do not infer relational labels or use probe/gold/judge metadata.")
        return {
            "condition_id": "M0",
            "memory_provider": "ld_agent_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "ld_agent_reference": dict(LD_AGENT_REFERENCE),
            "memory_context": "\n".join(lines),
            "source_detail_ids": [
                item["memory"]["memory_id"] for item in [*event_hits, *persona_hits]
            ],
            "retrieval": {
                "strategy": "ld_agent_topic_overlap_recency",
                "top_k": self.top_k,
                "query": query,
                "event_memory_count": len(event_hits),
                "persona_memory_count": len(persona_hits),
                "event_hits": event_hits,
                "persona_hits": persona_hits,
                "short_term_turn_count": len(self.short_term_session),
            },
        }

    def prepare_for_turn(self, message: dict[str, Any]) -> None:
        day = _safe_int(message.get("day"))
        if day <= 0:
            return
        if self.current_session_day is None:
            self.current_session_day = day
            return
        if day != self.current_session_day:
            self.flush_current_session(reason="day_boundary", next_day=day)
            self.current_session_day = day

    def record_completed_turn(
        self,
        *,
        message: dict[str, Any],
        assistant_answer: str,
        run_id: str = "",
    ) -> dict[str, Any]:
        self.prepare_for_turn(message)
        day = _safe_int(message.get("day"))
        if self.current_session_day is None and day > 0:
            self.current_session_day = day
        turn = {
            "run_id": run_id,
            "message_id": str(message.get("message_id", "")),
            "day": day,
            "topic": str(message.get("topic", "")),
            "turn_type": str(message.get("turn_type", "scripted_opening")),
            "user_message": str(message.get("user_message", "")),
            "assistant_answer": assistant_answer,
            "domains": [str(item) for item in message.get("domains", [])],
            "intent": str(message.get("intent", "")),
            "memory_relevance": str(message.get("memory_relevance", "")),
        }
        self.short_term_session.append(turn)
        action = {
            "action": "ld_agent_short_term_append",
            "memory_provider": "ld_agent_memory",
            "message_id": turn["message_id"],
            "day": day,
            "short_term_turn_count": len(self.short_term_session),
            "status": "success",
        }
        self.actions.append(action)
        return action

    def flush_current_session(self, *, reason: str, next_day: int | None = None) -> list[dict[str, Any]]:
        if not self.short_term_session:
            return []
        day = _safe_int(self.short_term_session[-1].get("day")) or self.current_session_day or 0
        actions = []
        actions.extend(self._write_event_memories(day=day, reason=reason))
        actions.extend(self._write_persona_memories(day=day, reason=reason))
        self.short_term_session = []
        if next_day is not None:
            self.current_session_day = next_day
        self.actions.extend(actions)
        return actions

    def _write_event_memories(self, *, day: int, reason: str) -> list[dict[str, Any]]:
        actions = []
        for topic, turns in _group_by_topic(self.short_term_session).items():
            if not topic:
                topic = "普通对话主题"
            summary = _build_event_summary(topic=topic, turns=turns)
            raw_dialogue = _build_raw_dialogue(turns)
            source_turn_ids = [str(turn.get("message_id")) for turn in turns if turn.get("message_id")]
            memory_id = self._stable_memory_id("event_memory", topic)
            existing = self.memories.get(memory_id)
            if existing:
                existing.summary = _merge_summary(existing.summary, summary)
                existing.raw_dialogue = _merge_raw_dialogue(existing.raw_dialogue, raw_dialogue)
                existing.source_turn_ids = _unique([*existing.source_turn_ids, *source_turn_ids])
                existing.source_session = _merge_source_session(existing.source_session, f"D{day:02d}")
                existing.timestamp = f"D{day:02d}"
                existing.updated_day = day
                existing.importance = max(existing.importance, _importance_from_turns(turns))
                action_name = "ld_agent_event_memory_update"
            else:
                self.memories[memory_id] = MemoryRecord(
                    memory_id=memory_id,
                    memory_type="event_memory",
                    summary=summary,
                    raw_dialogue=raw_dialogue,
                    source_session=f"D{day:02d}",
                    source_turn_ids=source_turn_ids,
                    timestamp=f"D{day:02d}",
                    importance=_importance_from_turns(turns),
                    topic=topic,
                    created_day=day,
                    updated_day=day,
                )
                action_name = "ld_agent_event_memory_add"
            actions.append(
                {
                    "action": action_name,
                    "memory_provider": "ld_agent_memory",
                    "memory_id": memory_id,
                    "memory_type": "event_memory",
                    "source_session": f"D{day:02d}",
                    "source_turn_ids": source_turn_ids,
                    "reason": reason,
                    "status": "success",
                }
            )
        return actions

    def _write_persona_memories(self, *, day: int, reason: str) -> list[dict[str, Any]]:
        traits = _extract_generic_persona_traits(self.short_term_session)
        actions = []
        for trait in traits:
            memory_id = self._stable_memory_id("persona_memory", trait)
            existing = self.memories.get(memory_id)
            if existing:
                existing.updated_day = day
                existing.timestamp = f"D{day:02d}"
                action_name = "ld_agent_persona_memory_update"
            else:
                self.memories[memory_id] = MemoryRecord(
                    memory_id=memory_id,
                    memory_type="persona_memory",
                    summary=trait,
                    source_session=f"D{day:02d}",
                    source_turn_ids=[
                        str(turn.get("message_id"))
                        for turn in self.short_term_session
                        if turn.get("message_id")
                    ],
                    timestamp=f"D{day:02d}",
                    importance=3,
                    topic="persona",
                    created_day=day,
                    updated_day=day,
                )
                action_name = "ld_agent_persona_memory_add"
            actions.append(
                {
                    "action": action_name,
                    "memory_provider": "ld_agent_memory",
                    "memory_id": memory_id,
                    "memory_type": "persona_memory",
                    "source_session": f"D{day:02d}",
                    "reason": reason,
                    "status": "success",
                }
            )
        return actions

    def _retrieve(
        self,
        *,
        query: str,
        current_day: int,
        memory_type: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        scored = []
        for memory in self.memories.values():
            if memory.memory_type != memory_type:
                continue
            relevance = _jaccard(query_tokens, _tokens(memory.summary + " " + memory.topic))
            if memory.topic and memory.topic in query:
                relevance = max(relevance, 0.35)
            recency = _recency_score(current_day=current_day, memory_day=memory.updated_day)
            score = self.semantic_weight * relevance + self.recency_weight * recency
            if score <= 0:
                continue
            scored.append((score, relevance, recency, memory))
        scored.sort(key=lambda item: (item[0], item[3].importance, item[3].updated_day), reverse=True)
        return [
            {
                "score": round(score, 4),
                "semantic_relevance": round(relevance, 4),
                "recency": round(recency, 4),
                "memory": memory.to_dict(),
            }
            for score, relevance, recency, memory in scored[:top_k]
        ]

    def _query_text(self, message: dict[str, Any]) -> str:
        recent = " ".join(
            str(turn.get("user_message", ""))
            for turn in self.short_term_session[-self.short_term_k :]
        )
        return " ".join(
            item
            for item in [
                str(message.get("user_message", "")),
                str(message.get("topic", "")),
                recent,
            ]
            if item
        )

    def _short_term_lines(self) -> list[str]:
        lines = []
        for turn in self.short_term_session[-self.short_term_k :]:
            message_id = turn.get("message_id", "")
            text = _truncate(str(turn.get("user_message", "")), 120)
            if text:
                lines.append(f"- {message_id}: 用户说：{text}")
        return lines

    def _stable_memory_id(self, memory_type: str, key: str) -> str:
        digest = hashlib.sha1(f"{memory_type}:{key}".encode("utf-8")).hexdigest()[:12]
        return f"m0_ld_agent:{memory_type}:{digest}"


def _group_by_topic(turns: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = OrderedDict()
    for turn in turns:
        topic = str(turn.get("topic", ""))
        grouped.setdefault(topic, []).append(turn)
    return grouped


def _build_event_summary(*, topic: str, turns: list[dict[str, Any]]) -> str:
    snippets = [
        _truncate(str(turn.get("user_message", "")).strip(), 90)
        for turn in turns
        if str(turn.get("user_message", "")).strip()
    ]
    if snippets:
        return f"用户讨论过「{topic}」相关情况：" + "；".join(snippets[:3])
    return f"用户讨论过「{topic}」相关情况。"


def _build_raw_dialogue(turns: list[dict[str, Any]]) -> str:
    lines = []
    for turn in turns:
        if turn.get("user_message"):
            lines.append(f"User({turn.get('message_id')}): {turn.get('user_message')}")
        if turn.get("assistant_answer"):
            lines.append(
                f"Assistant(M0): {_truncate(str(turn.get('assistant_answer')), 200)}"
            )
    return "\n".join(lines)


def _extract_generic_persona_traits(turns: list[dict[str, Any]]) -> list[str]:
    text = "\n".join(str(turn.get("user_message", "")) for turn in turns)
    traits = []
    domains = _unique(
        str(domain)
        for turn in turns
        for domain in turn.get("domains", [])
        if domain
    )
    topics = _unique(str(turn.get("topic", "")) for turn in turns if turn.get("topic"))
    if domains:
        traits.append("用户近期讨论领域包括：" + "、".join(domains) + "。")
    elif topics:
        traits.append("用户近期讨论主题包括：" + "、".join(topics[:4]) + "。")
    if any(marker in text for marker in ["实在一点", "标准答案", "别先安慰", "少废话"]):
        traits.append("用户偏好直接、具体、少空泛安慰的回应。")
    if any(marker in text for marker in ["下一步", "优先级", "处理思路", "判断一下"]):
        traits.append("用户在压力场景中常希望先拆事实、选项和下一步。")
    return _unique(traits)


def _importance_from_turns(turns: list[dict[str, Any]]) -> int:
    text = " ".join(str(turn.get("memory_relevance", "")) for turn in turns)
    if any(marker in text for marker in ["shared_event", "long_term", "probe"]):
        return 4
    if len(turns) >= 3:
        return 4
    return 3


def _merge_summary(existing: str, new: str) -> str:
    if new in existing:
        return existing
    return _truncate(existing + "；" + new, 600)


def _merge_raw_dialogue(existing: str, new: str) -> str:
    if not existing:
        return new
    return _truncate(existing + "\n" + new, 2400)


def _merge_source_session(existing: str, new: str) -> str:
    parts = _unique([item.strip() for item in (existing + "," + new).split(",") if item.strip()])
    return ", ".join(parts)


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    latin = re.findall(r"[a-z0-9_]+", lowered)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    return set(latin + cjk)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _recency_score(*, current_day: int, memory_day: int) -> float:
    if current_day <= 0 or memory_day <= 0:
        return 0.0
    gap = max(0, current_day - memory_day)
    return 1.0 / (1.0 + gap)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _unique(values) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value)
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result
