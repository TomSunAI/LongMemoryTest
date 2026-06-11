from __future__ import annotations

import hashlib
import json
import math
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from long_memory_test.memory.schema import MemoryRecord


RELATIONAL_RUNTIME_SCHEMA = "relational_memory_runtime_v1"
RELATIONAL_MEMORY_PROVIDER = "independent_relational_memory_runtime"
RELATIONAL_RETRIEVAL_STRATEGY = "independent_relational_overlap_recency"

CONCLUSION_MEMORY_TYPE = "relationship_conclusion_memory"
EVENT_SUMMARY_MEMORY_TYPE = "event_line_summary_memory"
DETAIL_ANCHOR_MEMORY_TYPE = "detail_anchor_memory"

CONDITION_MEMORY_TYPES = {
    "M1": [CONCLUSION_MEMORY_TYPE],
    "M2": [CONCLUSION_MEMORY_TYPE, EVENT_SUMMARY_MEMORY_TYPE],
    "M3": [
        CONCLUSION_MEMORY_TYPE,
        EVENT_SUMMARY_MEMORY_TYPE,
        DETAIL_ANCHOR_MEMORY_TYPE,
    ],
}

TYPE_LABELS = {
    CONCLUSION_MEMORY_TYPE: "结论级关系记忆",
    EVENT_SUMMARY_MEMORY_TYPE: "摘要级事件线记忆",
    DETAIL_ANCHOR_MEMORY_TYPE: "细节级关系锚点",
}

TYPE_FILENAMES = {
    CONCLUSION_MEMORY_TYPE: "conclusion_memories.jsonl",
    EVENT_SUMMARY_MEMORY_TYPE: "event_line_summaries.jsonl",
    DETAIL_ANCHOR_MEMORY_TYPE: "detail_anchors.jsonl",
}


class RelationalMemoryRuntime:
    """Independent runtime for M1/M2/M3 relational memory conditions.

    M2 and M3 are cumulative in capability, but each condition stores its own
    copy of lower-level memory inside its own namespace. They never read M0 or
    another relational condition's runtime payload.
    """

    def __init__(
        self,
        *,
        condition_id: str,
        top_k: int = 5,
        storage_root: str | Path | None = None,
    ) -> None:
        if condition_id not in CONDITION_MEMORY_TYPES:
            raise ValueError(f"Unsupported relational memory condition: {condition_id}")
        self.condition_id = condition_id
        self.top_k = top_k
        self.enabled_memory_types = list(CONDITION_MEMORY_TYPES[condition_id])
        self.storage_root = Path(storage_root) if storage_root else None
        self.memories: OrderedDict[str, MemoryRecord] = OrderedDict()
        self.actions: list[dict[str, Any]] = []
        self.retrieval_log: list[dict[str, Any]] = []
        self.rendered_payloads: list[dict[str, Any]] = []
        if self.storage_root:
            self.storage_root.mkdir(parents=True, exist_ok=True)
            self._persist()

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, Any] | None,
        *,
        condition_id: str,
        top_k: int | None = None,
        storage_root: str | Path | None = None,
    ) -> "RelationalMemoryRuntime":
        runtime = cls(
            condition_id=condition_id,
            top_k=int(top_k or (snapshot or {}).get("top_k", 5) or 5),
            storage_root=storage_root or (snapshot or {}).get("storage_root"),
        )
        if not snapshot:
            return runtime
        runtime.enabled_memory_types = [
            str(item)
            for item in snapshot.get(
                "enabled_memory_types",
                CONDITION_MEMORY_TYPES[condition_id],
            )
        ]
        runtime.memories = OrderedDict()
        for item in snapshot.get("memories", []):
            if not isinstance(item, dict) or not item.get("memory_id"):
                continue
            memory = MemoryRecord.from_dict(item)
            runtime.memories[memory.memory_id] = memory
        runtime.actions = list(snapshot.get("actions", []))
        runtime.retrieval_log = list(snapshot.get("retrieval_log", []))
        runtime.rendered_payloads = list(snapshot.get("rendered_payloads", []))
        runtime._persist()
        return runtime

    @classmethod
    def from_completed_turns(
        cls,
        turns: list[dict[str, Any]],
        *,
        condition_id: str,
        top_k: int = 5,
        storage_root: str | Path | None = None,
    ) -> "RelationalMemoryRuntime":
        runtime = cls(condition_id=condition_id, top_k=top_k, storage_root=storage_root)
        for turn in turns:
            variants = turn.get("variants", {})
            if not isinstance(variants, dict) or condition_id not in variants:
                continue
            message = dict(turn.get("input", {}))
            answer = str(variants[condition_id].get("assistant_answer", ""))
            runtime.record_completed_turn(
                message=message,
                assistant_answer=answer,
                run_id=str(turn.get("run_id", "")),
            )
        return runtime

    def snapshot(self) -> dict[str, Any]:
        memories_by_type: dict[str, list[dict[str, Any]]] = {
            memory_type: [] for memory_type in self.enabled_memory_types
        }
        for memory in self.memories.values():
            memories_by_type.setdefault(memory.memory_type, []).append(memory.to_dict())
        return {
            "schema_version": RELATIONAL_RUNTIME_SCHEMA,
            "provider": RELATIONAL_MEMORY_PROVIDER,
            "runtime_id": f"{self.condition_id}_independent_relational_memory",
            "condition_id": self.condition_id,
            "storage_backend": "json_files",
            "storage_root": str(self.storage_root) if self.storage_root else None,
            "top_k": self.top_k,
            "enabled_memory_types": list(self.enabled_memory_types),
            "memory_count": len(self.memories),
            "memories": [memory.to_dict() for memory in self.memories.values()],
            "memories_by_type": memories_by_type,
            "actions": list(self.actions),
            "retrieval_log": list(self.retrieval_log),
            "rendered_payloads": list(self.rendered_payloads),
            "config": {
                "namespace_isolation": True,
                "reads_m0_payload": False,
                "reads_other_condition_payloads": False,
                "probe_writeback": False,
                "cumulative_levels_are_copied_within_condition_namespace": True,
                "retrieval_strategy": RELATIONAL_RETRIEVAL_STRATEGY,
            },
        }

    def retrieve_payload(self, message: dict[str, Any]) -> dict[str, Any]:
        query = _query_text(message)
        current_day = _safe_int(message.get("day"))
        hits_by_type = {
            memory_type: self._retrieve_by_type(
                memory_type=memory_type,
                query=query,
                current_day=current_day,
            )
            for memory_type in self.enabled_memory_types
        }
        flat_hits = [
            item
            for memory_type in self.enabled_memory_types
            for item in hits_by_type.get(memory_type, [])
        ]
        lines = [
            f"[Available {self.condition_id} Memory: Independent Relational Memory Runtime]",
            "",
            "Runtime boundary:",
            "- 只使用本条件自己的长期关系记忆 namespace。",
            "- 不读取 M0 payload，也不读取其他 M 条件的 payload。",
            "- probe turn 只读，不写回。",
            "",
        ]
        for memory_type in self.enabled_memory_types:
            lines.append(f"{TYPE_LABELS[memory_type]}:")
            hits = hits_by_type.get(memory_type, [])
            if hits:
                for idx, hit in enumerate(hits, start=1):
                    memory = hit["memory"]
                    lines.append(
                        f"{idx}. {memory['summary']}\n"
                        f"   source_turns={','.join(memory.get('source_turn_ids', []))}; "
                        f"score={hit['score']}; overlap={hit['overlap_score']}; "
                        f"recency={hit['recency_score']}"
                    )
            else:
                lines.append("- 当前没有检索到该层级的可用记忆。")
            lines.append("")
        retrieval = {
            "strategy": RELATIONAL_RETRIEVAL_STRATEGY,
            "top_k": self.top_k,
            "query_text": query,
            "uses_m0_payload": False,
            "uses_other_condition_payloads": False,
            "enabled_memory_types": list(self.enabled_memory_types),
            "memory_count": len(self.memories),
            "hit_count": len(flat_hits),
            "hits_by_type": hits_by_type,
            "hits": flat_hits,
            "zero_hit": len(flat_hits) == 0,
        }
        payload = {
            "condition": self.condition_id,
            "condition_id": self.condition_id,
            "memory_provider": RELATIONAL_MEMORY_PROVIDER,
            "runtime_id": f"{self.condition_id}_independent_relational_memory",
            "memory_unit": "condition_namespace_relational_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": False,
            "storage_backend": "json_files",
            "storage_root": str(self.storage_root) if self.storage_root else None,
            "enabled_memory_types": list(self.enabled_memory_types),
            "memory_context": "\n".join(lines).strip(),
            "source_detail_ids": [hit["memory"]["memory_id"] for hit in flat_hits],
            "tau": dict(message.get("tau", {})) if isinstance(message.get("tau"), dict) else {},
            "memory_composition": {
                "base_condition": None,
                "base_provider": None,
                "base_payload_required": False,
                "base_payload_shared_by": [],
                "overlay_condition": self.condition_id,
                "overlay_source": "independent_relational_memory_runtime",
                "composition_rule": "condition_runtime_namespace_only",
            },
            "search_indexing_policy": {
                "uses_m0_search_indexing": False,
                "m0_retrieval_strategy": None,
                "m0_storage_backend": None,
                "relational_layer_has_independent_generic_search": True,
                "relational_layer_role": "independent_condition_runtime",
            },
            "retrieval": retrieval,
        }
        self.retrieval_log.append(
            {
                "condition_id": self.condition_id,
                "message_id": str(message.get("message_id", "")),
                "day": current_day,
                "query_text": query,
                "source_detail_ids": list(payload["source_detail_ids"]),
                "hit_count": len(flat_hits),
                "strategy": RELATIONAL_RETRIEVAL_STRATEGY,
            }
        )
        self.rendered_payloads.append(
            {
                "condition_id": self.condition_id,
                "message_id": str(message.get("message_id", "")),
                "memory_context": payload["memory_context"],
                "source_detail_ids": list(payload["source_detail_ids"]),
            }
        )
        self._persist()
        return payload

    def record_completed_turn(
        self,
        *,
        message: dict[str, Any],
        assistant_answer: str,
        run_id: str = "",
    ) -> dict[str, Any]:
        message_id = str(message.get("message_id", ""))
        day = _safe_int(message.get("day"))
        if _is_probe_turn(message):
            action = {
                "action": "skip_probe_writeback",
                "memory_provider": RELATIONAL_MEMORY_PROVIDER,
                "condition_id": self.condition_id,
                "message_id": message_id,
                "day": day,
                "reason": "probe_read_only",
                "status": "skipped",
            }
            self.actions.append(action)
            self._persist()
            return action

        created = []
        for memory_type in self.enabled_memory_types:
            memory = self._build_memory_record(
                memory_type=memory_type,
                message=message,
                assistant_answer=assistant_answer,
                run_id=run_id,
            )
            self.memories[memory.memory_id] = memory
            created.append(memory.memory_id)
        action = {
            "action": "upsert_relational_memories",
            "memory_provider": RELATIONAL_MEMORY_PROVIDER,
            "condition_id": self.condition_id,
            "message_id": message_id,
            "day": day,
            "tau": dict(message.get("tau", {})) if isinstance(message.get("tau"), dict) else {},
            "memory_ids": created,
            "memory_types": list(self.enabled_memory_types),
            "status": "success",
        }
        self.actions.append(action)
        self._persist()
        return action

    def _retrieve_by_type(
        self,
        *,
        memory_type: str,
        query: str,
        current_day: int,
    ) -> list[dict[str, Any]]:
        query_tokens = _text_tokens(query)
        scored = []
        for memory in self.memories.values():
            if memory.memory_type != memory_type:
                continue
            memory_tokens = _text_tokens(
                " ".join(
                    [
                        memory.summary,
                        memory.topic,
                        " ".join(memory.domains),
                    ]
                )
            )
            overlap = _overlap_score(query_tokens, memory_tokens)
            recency = _recency_score(current_day=current_day, memory_day=memory.updated_day)
            score = round((overlap * 0.78) + (recency * 0.17) + (memory.importance * 0.01), 4)
            if score <= 0:
                continue
            scored.append(
                {
                    "memory": memory.to_dict(),
                    "score": score,
                    "overlap_score": round(overlap, 4),
                    "recency_score": round(recency, 4),
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: self.top_k]

    def _build_memory_record(
        self,
        *,
        memory_type: str,
        message: dict[str, Any],
        assistant_answer: str,
        run_id: str,
    ) -> MemoryRecord:
        message_id = str(message.get("message_id", ""))
        day = _safe_int(message.get("day"))
        summary = _memory_summary(
            condition_id=self.condition_id,
            memory_type=memory_type,
            message=message,
            assistant_answer=assistant_answer,
        )
        topic = ",".join(_text_tokens(_query_text(message))[:12])
        domains = [str(item) for item in message.get("domains", []) if item]
        memory_id = _stable_memory_id(
            self.condition_id,
            memory_type,
            message_id,
        )
        return MemoryRecord(
            memory_id=memory_id,
            memory_type=memory_type,
            summary=summary,
            raw_dialogue=_raw_dialogue(message, assistant_answer),
            source_session=f"D{day:02d}" if day > 0 else "",
            source_turn_ids=[message_id] if message_id else [],
            timestamp=f"D{day:02d}" if day > 0 else "",
            importance=_importance_for_type(memory_type),
            topic=topic,
            domains=domains,
            available_from_session=f"D{day:02d}" if day > 0 else "",
            created_day=day,
            updated_day=day,
            ld_agent_metadata={
                "condition_id": self.condition_id,
                "provider": RELATIONAL_MEMORY_PROVIDER,
                "memory_type": memory_type,
                "tau": dict(message.get("tau", {})) if isinstance(message.get("tau"), dict) else {},
                "event_line_id": (
                    message.get("tau", {}).get("event_line_id")
                    if isinstance(message.get("tau"), dict)
                    else None
                ),
                "event_stage": (
                    message.get("tau", {}).get("event_stage")
                    if isinstance(message.get("tau"), dict)
                    else None
                ),
                "run_id": run_id,
                "write_policy": "condition_namespace_only",
                "source": "completed_non_probe_turn",
                "uses_m0_payload": False,
                "uses_other_condition_payloads": False,
            },
        )

    def _persist(self) -> None:
        if not self.storage_root:
            return
        self.storage_root.mkdir(parents=True, exist_ok=True)
        snapshot = self.snapshot()
        (self.storage_root / "snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for memory_type in self.enabled_memory_types:
            filename = TYPE_FILENAMES[memory_type]
            items = [
                memory.to_dict()
                for memory in self.memories.values()
                if memory.memory_type == memory_type
            ]
            _write_jsonl(self.storage_root / filename, items)
        _write_jsonl(self.storage_root / "write_log.jsonl", self.actions)
        _write_jsonl(self.storage_root / "retrieval_log.jsonl", self.retrieval_log)
        _write_jsonl(self.storage_root / "rendered_payloads.jsonl", self.rendered_payloads)


def _write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items),
        encoding="utf-8",
    )


def _memory_summary(
    *,
    condition_id: str,
    memory_type: str,
    message: dict[str, Any],
    assistant_answer: str,
) -> str:
    user_brief = _compact_text(str(message.get("user_message", "")), 96)
    answer_brief = _compact_text(assistant_answer, 72)
    if memory_type == CONCLUSION_MEMORY_TYPE:
        return (
            "用户本轮可沉淀的关系结论："
            f"{user_brief}；后续回应应承接已表达的关切，并保持具体、少泛化。"
        )
    if memory_type == EVENT_SUMMARY_MEMORY_TYPE:
        return (
            "事件线进展摘要："
            f"用户表达「{user_brief}」；本轮回应处理为「{answer_brief}」。"
        )
    if memory_type == DETAIL_ANCHOR_MEMORY_TYPE:
        return (
            "细节级关系锚点："
            f"用户原话中的可复用具体线索是「{user_brief}」；"
            "使用时只能作为对话承接线索，不能扩展成未说出的事实、诊断或承诺。"
        )
    raise ValueError(f"Unsupported relational memory type: {memory_type}")


def _raw_dialogue(message: dict[str, Any], assistant_answer: str) -> str:
    return "\n".join(
        [
            "User: " + str(message.get("user_message", "")),
            "Agent: " + str(assistant_answer),
        ]
    )


def _query_text(message: dict[str, Any]) -> str:
    parts = [
        str(message.get("user_message", "")),
        str(message.get("topic", "")),
        str(message.get("intent", "")),
        str(message.get("memory_relevance", "")),
        " ".join(str(item) for item in message.get("domains", []) if item),
    ]
    return " ".join(part for part in parts if part)


def _compact_text(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _text_tokens(text: str) -> list[str]:
    lowered = text.lower()
    tokens: list[str] = []
    tokens.extend(
        item
        for item in re.findall(r"[a-z0-9_]{2,}", lowered)
        if item not in {"the", "and", "with"}
    )
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    for size in (2, 3):
        for idx in range(0, max(0, len(chinese_chars) - size + 1)):
            token = "".join(chinese_chars[idx : idx + size])
            if token not in {"这个", "那个", "就是", "一下", "还是"}:
                tokens.append(token)
    return _unique(tokens)


def _overlap_score(query_tokens: list[str], memory_tokens: list[str]) -> float:
    if not query_tokens or not memory_tokens:
        return 0.0
    query_set = set(query_tokens)
    memory_set = set(memory_tokens)
    overlap = len(query_set & memory_set)
    return overlap / max(1, min(len(query_set), len(memory_set)))


def _recency_score(*, current_day: int, memory_day: int) -> float:
    if current_day <= 0 or memory_day <= 0:
        return 0.5
    delta = max(0, current_day - memory_day)
    return math.exp(-delta / 14.0)


def _importance_for_type(memory_type: str) -> int:
    return {
        CONCLUSION_MEMORY_TYPE: 4,
        EVENT_SUMMARY_MEMORY_TYPE: 5,
        DETAIL_ANCHOR_MEMORY_TYPE: 4,
    }[memory_type]


def _stable_memory_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return "_".join([parts[0], parts[1].replace("_memory", ""), digest])


def _is_probe_turn(message: dict[str, Any]) -> bool:
    turn_type = str(message.get("turn_type", ""))
    message_id = str(message.get("message_id", ""))
    return turn_type == "targeted_probe" or "_P" in message_id


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
