from __future__ import annotations

import hashlib
import importlib
import math
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from long_memory_test.memory.schema import MemoryRecord


LD_AGENT_REFERENCE = {
    "repo": "https://github.com/leolee99/LD-Agent",
    "commit": "af3c15ab63efcb4ab83d635670b316d63977d106",
    "modules": ["Module/EventMemory.py", "Module/Personas.py"],
    "usage": "memory_only_no_generator_or_checkpoint",
}

M0_RUNTIME_ID = "M0_ld_agent_style_session_summary"
M0_MEMORY_UNIT = "session"
M0_RETRIEVAL_STRATEGY = "topic_overlap_time_decay"
SESSION_SUMMARY_MEMORY_TYPE = "session_summary_memory"
PERSONA_MEMORY_TYPE = "persona_memory"

LD_SESSION_SUMMARY_SYSTEM_PROMPT = (
    "You are a user-fact-only long-term dialogue memory summarizer.\n"
    "Summarize the completed user turns into one ordinary session-level memory.\n"
    "Rules:\n"
    "1. Summarize only user-provided content from this session.\n"
    "2. Preserve the user's main topic, concern, preference, or task.\n"
    "3. Do not treat assistant answers, suggestions, examples, or plans as user facts.\n"
    "4. Do not infer persistent event objects.\n"
    "5. Do not decide whether this session updates a previous event.\n"
    "6. Do not create event trajectories.\n"
    "7. Do not include shared handling strategies, relational anchors, "
    "or boundary-sensitive cues.\n"
    "8. Do not use probe labels, gold response strategies, or evaluation annotations.\n"
    "9. Output one concise summary."
)
LD_PERSONA_SYSTEM_PROMPT = (
    "Extract only ordinary user persona, preference, or fact memories. "
    "Do not extract relationship expectations, shared strategies, event trajectories, "
    "or boundary-sensitive cues."
)
LD_PERSONA_EXAMPLES = (
    "If no traits can be extracted in the sentence, you should reply 'NO_TRAIT'. "
    "Given you some format examples of traits extraction, such as:\n"
    "1. No, I have no longer serve in the millitary, I had served up the full term "
    "that I signed up for, and now work outside of the millitary.\n"
    "Extracted Traits: 'I now work elsewhere. I used to be in the military.'\n"
    "2. That must a been some kind of endeavor. Its great that people are aware "
    "of issues that arise in their homes, otherwise it can be very problematic "
    "in the future.\n"
    "'NO_TRAIT'\n"
)


class LDAgentMemoryRuntime:
    """LD-Agent-style session-summary memory runtime for the M0 baseline.

    This keeps the experiment's responder model controlled while reproducing
    the memory-side baseline described as LD-Agent-style event memory while
    operationalizing the long-term unit as completed-session summaries. M0 does
    not perform event detection, event identity resolution, persistent event
    updates, event merging, or event trajectory construction.
    """

    def __init__(
        self,
        *,
        top_k: int = 5,
        short_term_k: int = 5,
        llm_client: Any | None = None,
        llm_model: str | None = None,
        llm_timeout: float = 60.0,
        max_user_personas: int = 5,
        max_agent_personas: int = 5,
        decay_temp: float = 1e-7,
        storage_backend: str = "json",
        chroma_path: str | Path | None = None,
        chroma_collection: str = "ld_agent_m0_session_summary_memory",
    ) -> None:
        self.top_k = top_k
        self.short_term_k = short_term_k
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.llm_timeout = llm_timeout
        self.max_user_personas = max_user_personas
        self.max_agent_personas = max_agent_personas
        self.decay_temp = decay_temp
        self.storage_backend = _normalize_storage_backend(storage_backend)
        self.chroma_path = str(chroma_path) if chroma_path else None
        self.chroma_collection = chroma_collection
        self.current_session_day: int | None = None
        self.short_term_session: list[dict[str, Any]] = []
        self.memories: OrderedDict[str, MemoryRecord] = OrderedDict()
        self.user_traits: list[str] = []
        self.agent_traits: list[str] = []
        self.memory_llm_failures: list[dict[str, Any]] = []
        self.actions: list[dict[str, Any]] = []
        self._chroma_client: Any | None = None
        self._chroma_collection: Any | None = None
        if self.storage_backend == "chroma":
            self._init_chroma()

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, Any] | None,
        *,
        top_k: int | None = None,
        short_term_k: int | None = None,
        llm_client: Any | None = None,
        llm_model: str | None = None,
        llm_timeout: float = 60.0,
        storage_backend: str | None = None,
        chroma_path: str | Path | None = None,
    ) -> "LDAgentMemoryRuntime":
        runtime = cls(
            top_k=int(top_k or (snapshot or {}).get("top_k", 5) or 5),
            short_term_k=int(short_term_k or (snapshot or {}).get("short_term_k", 5) or 5),
            llm_client=llm_client,
            llm_model=llm_model,
            llm_timeout=llm_timeout,
            max_user_personas=int((snapshot or {}).get("max_user_personas", 5) or 5),
            max_agent_personas=int((snapshot or {}).get("max_agent_personas", 5) or 5),
            decay_temp=float((snapshot or {}).get("decay_temp", 1e-7) or 1e-7),
            storage_backend=storage_backend
            or str((snapshot or {}).get("storage_backend", "json")),
            chroma_path=chroma_path or (snapshot or {}).get("chroma_path"),
            chroma_collection=str(
                (snapshot or {}).get(
                    "chroma_collection",
                    "ld_agent_m0_session_summary_memory",
                )
            ),
        )
        if not snapshot:
            return runtime
        runtime.current_session_day = snapshot.get("current_session_day") or _session_day(
            snapshot.get("current_session_id")
        )
        runtime.short_term_session = list(snapshot.get("short_term_session", []))
        memory_items = snapshot.get("memories")
        if not isinstance(memory_items, list):
            memory_items = [
                *snapshot.get("session_summary_memories", []),
                *snapshot.get("persona_memories", []),
            ]
        runtime.memories = OrderedDict()
        for item in memory_items:
            if not isinstance(item, dict) or not item.get("memory_id"):
                continue
            memory = MemoryRecord.from_dict(item)
            _normalize_loaded_m0_memory(memory)
            runtime.memories[memory.memory_id] = memory
        runtime.user_traits = [str(item) for item in snapshot.get("user_traits", []) if item]
        runtime.agent_traits = [str(item) for item in snapshot.get("agent_traits", []) if item]
        runtime.memory_llm_failures = list(
            snapshot.get("memory_llm_failures")
            or snapshot.get("memory_writer_failures", [])
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
        llm_client: Any | None = None,
        llm_model: str | None = None,
        llm_timeout: float = 60.0,
        storage_backend: str = "json",
        chroma_path: str | Path | None = None,
        chroma_collection: str = "ld_agent_m0_session_summary_memory",
    ) -> "LDAgentMemoryRuntime":
        runtime = cls(
            top_k=top_k,
            short_term_k=short_term_k,
            llm_client=llm_client,
            llm_model=llm_model,
            llm_timeout=llm_timeout,
            storage_backend=storage_backend,
            chroma_path=chroma_path,
            chroma_collection=chroma_collection,
        )
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
        session_summary_memories = [
            memory.to_dict()
            for memory in self.memories.values()
            if memory.memory_type == SESSION_SUMMARY_MEMORY_TYPE
        ]
        persona_memories = [
            memory.to_dict()
            for memory in self.memories.values()
            if memory.memory_type == PERSONA_MEMORY_TYPE
        ]
        current_session_id = (
            f"D{self.current_session_day:02d}"
            if self.current_session_day and self.current_session_day > 0
            else None
        )
        return {
            "schema_version": "m0_ld_agent_style_session_summary_runtime_v1",
            "provider": "ld_agent_memory",
            "runtime_id": M0_RUNTIME_ID,
            "compatibility_mode": "ld_agent_style_session_summary_memory_baseline",
            "memory_unit": M0_MEMORY_UNIT,
            "retrieval_strategy": M0_RETRIEVAL_STRATEGY,
            "ld_agent_reference": dict(LD_AGENT_REFERENCE),
            "storage_backend": self.storage_backend,
            "uses_chromadb": self.storage_backend == "chroma",
            "chroma_path": self.chroma_path,
            "chroma_collection": self.chroma_collection,
            "uses_spacy": False,
            "uses_ld_agent_generator": False,
            "uses_ld_agent_checkpoint": False,
            "summary_writer": "llm" if self._has_memory_llm() else "deterministic_fallback",
            "persona_writer": "llm" if self._has_memory_llm() else "deterministic_fallback",
            "top_k": self.top_k,
            "short_term_k": self.short_term_k,
            "max_user_personas": self.max_user_personas,
            "max_agent_personas": self.max_agent_personas,
            "decay_temp": self.decay_temp,
            "current_session_id": current_session_id,
            "current_session_day": self.current_session_day,
            "short_term_session": list(self.short_term_session),
            "session_summary_memories": session_summary_memories,
            "persona_memories": persona_memories,
            "user_traits": list(self.user_traits),
            "agent_traits": list(self.agent_traits),
            "memory_llm_failure_count": len(self.memory_llm_failures),
            "memory_llm_failures": list(self.memory_llm_failures),
            "memory_writer_failures": list(self.memory_llm_failures),
            "memories": [memory.to_dict() for memory in self.memories.values()],
            "actions": list(self.actions),
            "config": {
                "memory_unit": M0_MEMORY_UNIT,
                "retrieval_strategy": M0_RETRIEVAL_STRATEGY,
                "top_k_session_memory": self.top_k,
                "top_k_persona_memory": self.max_user_personas,
                "probe_writeback": False,
                "persona_speaker_policy": "user_only",
            },
        }

    def retrieve_payload(self, message: dict[str, Any]) -> dict[str, Any]:
        self.prepare_for_turn(message)
        query = self._query_text(message)
        query_topics = _ld_topic_tokens(query)
        current_day = _safe_int(message.get("day"))
        session_hits = self._retrieve_session_summary_memories(
            query=query,
            current_day=current_day,
        )
        persona_hits = self._retrieve_persona_memories(query=query)
        short_term_lines = self._short_term_lines()
        lines = [
            "[Available M0 Memory: LD-Agent-style Session-Summary Memory]",
            "",
            "Current short-term session:",
        ]
        lines.extend(short_term_lines or ["- 当前 session 内暂无更早用户 turn。"])
        lines.append("")
        lines.append("Retrieved session summaries:")
        lines.extend(
            [
                f"{idx}. "
                + item["memory"]["summary"]
                + (
                    f"\n   source_session={item['memory']['source_session_id']}; "
                    f"score={item['score']}; overlap={item['overlap_score']}; "
                    f"time_decay={item['time_decay']}"
                )
                for idx, item in enumerate(session_hits, start=1)
            ]
            or ["- 当前没有检索到相关 session summary memory。"]
        )
        lines.append("")
        lines.append("Persona memories:")
        user_trait_lines = [
            "- " + item["memory"]["summary"]
            for item in persona_hits
            if item["memory"].get("ld_agent_metadata", {}).get("speaker") == "user"
        ]
        lines.extend(user_trait_lines or ["- 当前没有可用普通 persona/fact memory。"])
        lines.extend(
            [
                "",
                "Rules:",
                "Use the above memory only when relevant.",
                "Do not infer persistent event objects.",
                "Do not merge session summaries into event trajectories.",
                "Do not use relational anchors, shared handling strategies, or boundary-sensitive cues.",
            ]
        )
        avg_overlap = (
            round(sum(item["overlap_score"] for item in session_hits) / len(session_hits), 4)
            if session_hits
            else 0.0
        )
        retrieval = {
            "strategy": M0_RETRIEVAL_STRATEGY,
            "top_k": self.top_k,
            "query": {
                "text": query,
                "query_topics": query_topics,
            },
            "query_text": query,
            "session_summary_memory_count": len(session_hits),
            "persona_memory_count": len(persona_hits),
            "session_hits": session_hits,
            "persona_hits": persona_hits,
            "short_term_turn_count": len(self.short_term_session),
            "zero_hit": len(session_hits) == 0,
            "avg_overlap_score": avg_overlap,
            # Compatibility aliases for older analysis scripts during migration.
            "event_memory_count": len(session_hits),
            "event_hits": session_hits,
        }
        return {
            "condition": "M0",
            "condition_id": "M0",
            "memory_unit": M0_MEMORY_UNIT,
            "memory_provider": "ld_agent_memory",
            "requires_runtime_letta": False,
            "requires_runtime_ld_agent_memory": True,
            "ld_agent_reference": dict(LD_AGENT_REFERENCE),
            "storage_backend": self.storage_backend,
            "uses_chromadb": self.storage_backend == "chroma",
            "uses_spacy": False,
            "memory_context": "\n".join(lines),
            "source_detail_ids": [
                item["memory"]["memory_id"] for item in [*session_hits, *persona_hits]
            ],
            "retrieval": retrieval,
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
        message_id = str(message.get("message_id", ""))
        if _is_probe_turn(message):
            action = {
                "action": "skip_probe_writeback",
                "memory_provider": "ld_agent_memory",
                "condition_id": "M0",
                "message_id": message_id,
                "session_id": _message_session_id(message),
                "day": day,
                "reason": "probe_read_only",
                "status": "skipped",
            }
            self.actions.append(action)
            return action
        turn_idx = len(self.short_term_session)
        user_message = str(message.get("user_message", ""))
        session_id = _message_session_id(message)
        turn = {
            "run_id": run_id,
            "idx": turn_idx,
            "time": _ld_time(day=day, idx=turn_idx),
            "turn_id": message_id,
            "message_id": message_id,
            "session_id": session_id,
            "day": day,
            "topic": str(message.get("topic", "")),
            "turn_type": str(message.get("turn_type", "scripted_opening")),
            "user_message": user_message,
            "m0_answer": assistant_answer,
            "assistant_answer": assistant_answer,
            "domains": [str(item) for item in message.get("domains", [])],
            "intent": str(message.get("intent", "")),
            "memory_relevance": str(message.get("memory_relevance", "")),
            "tau": dict(message.get("tau", {})) if isinstance(message.get("tau"), dict) else {},
            "timestamp": _ld_time(day=day, idx=turn_idx),
        }
        turn["dialog"] = _format_short_term_turn(turn)
        self.short_term_session.append(turn)
        action = {
            "action": "append_short_term_session",
            "legacy_action": "ld_agent_short_term_append",
            "memory_provider": "ld_agent_memory",
            "condition_id": "M0",
            "turn_id": turn["turn_id"],
            "message_id": message_id,
            "session_id": session_id,
            "day": day,
            "idx": turn_idx,
            "time": turn["time"],
            "short_term_turn_count": len(self.short_term_session),
            "status": "success",
        }
        self.actions.append(action)
        self.actions.extend(
            self._update_personas(
                inquiry=user_message,
                source_turn_id=turn["message_id"],
                day=day,
            )
        )
        return action

    def flush_current_session(
        self,
        *,
        reason: str,
        next_day: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.short_term_session:
            return []
        day = _safe_int(self.short_term_session[-1].get("day")) or self.current_session_day or 0
        actions = self._write_session_summary_memory(
            day=day,
            reason=reason,
            next_day=next_day,
        )
        self.short_term_session = []
        if next_day is not None:
            self.current_session_day = next_day
        self.actions.extend(actions)
        return actions

    def _write_session_summary_memory(
        self,
        *,
        day: int,
        reason: str,
        next_day: int | None,
        ) -> list[dict[str, Any]]:
        user_memory_context = _build_user_memory_dialogue(self.short_term_session)
        context_lines = [line for line in user_memory_context.splitlines() if line.strip()]
        summary = self._context_summarize(user_memory_context, len(context_lines))
        topic_list = _ld_topic_tokens(_session_topic_text(self.short_term_session))
        topics = ",".join(topic_list)
        domains = _unique(
            domain
            for turn in self.short_term_session
            for domain in turn.get("domains", [])
        )
        source_turn_ids = [
            str(turn.get("message_id")) for turn in self.short_term_session if turn.get("message_id")
        ]
        session = f"D{day:02d}"
        available_from_session = (
            f"D{next_day:02d}" if next_day and next_day > 0 else f"D{day + 1:02d}"
        )
        memory_id = self._stable_memory_id(
            SESSION_SUMMARY_MEMORY_TYPE,
            session + ":" + ",".join(source_turn_ids),
        )
        metadata = {
            "memory_name": "event_memory",
            "implementation_unit": "session_summary",
            "write_policy": "user_only_no_assistant_answer_writeback",
            "assistant_answer_writeback": False,
            "fact_layer_sources": [
                "user_message",
                "topic",
                "domains",
                "intent",
                "memory_relevance",
            ],
            "answer_layer_policy": (
                "assistant answers are excluded from M0 long-term memory summary, "
                "raw_dialogue, topics, persona extraction, and retrieval indexing"
            ),
            "idx": self._session_summary_memory_count(),
            "dialog": "",
            "time": _ld_time(day=day, idx=len(self.short_term_session)),
            "topics": topics,
            "datatype": "text",
            "summary": summary,
            "source_session_id": session,
            "available_from_session": available_from_session,
        }
        self.memories[memory_id] = MemoryRecord(
            memory_id=memory_id,
            memory_type=SESSION_SUMMARY_MEMORY_TYPE,
            summary=summary,
            raw_dialogue=user_memory_context,
            source_session=session,
            source_turn_ids=source_turn_ids,
            timestamp=session,
            importance=_importance_from_turns(self.short_term_session),
            topic=topics,
            domains=domains,
            available_from_session=available_from_session,
            created_day=day,
            updated_day=day,
            ld_agent_metadata=metadata,
        )
        self._store_session_summary_in_chroma(
            memory_id=memory_id,
            summary=summary,
            metadata=metadata,
        )
        return [
            {
                "action": "add_session_summary_memory",
                "legacy_action": "ld_agent_event_memory_add",
                "memory_provider": "ld_agent_memory",
                "condition_id": "M0",
                "memory_id": memory_id,
                "memory_type": SESSION_SUMMARY_MEMORY_TYPE,
                "source_session_id": session,
                "source_session": session,
                "source_turn_ids": source_turn_ids,
                "summary": summary,
                "available_from_session": available_from_session,
                "reason": reason,
                "ld_agent_metadata": metadata,
                "status": "success",
            }
        ]

    def _update_personas(
        self,
        *,
        inquiry: str,
        source_turn_id: str,
        day: int,
    ) -> list[dict[str, Any]]:
        actions = []
        user_trait = self._extract_persona_trait(inquiry)
        if _is_valid_trait(user_trait) and user_trait not in self.user_traits:
            self.user_traits.append(user_trait)
            actions.append(
                self._write_persona_memory(
                    speaker="user",
                    trait=user_trait,
                    source_turn_id=source_turn_id,
                    day=day,
                )
            )
        return actions

    def _write_persona_memory(
        self,
        *,
        speaker: str,
        trait: str,
        source_turn_id: str,
        day: int,
    ) -> dict[str, Any]:
        memory_id = self._stable_memory_id(PERSONA_MEMORY_TYPE, speaker + ":" + trait)
        metadata = {
            "speaker": speaker,
            "datatype": "text",
            "summary": trait,
            "source": "M0 ordinary user persona/fact extraction",
            "write_policy": "user_only_no_relational_anchors",
        }
        action_name = "add_persona_memory"
        existing = self.memories.get(memory_id)
        if existing:
            existing.updated_day = day
            existing.timestamp = f"D{day:02d}"
            existing.source_turn_ids = _unique([*existing.source_turn_ids, source_turn_id])
            action_name = "update_persona_memory"
        else:
            self.memories[memory_id] = MemoryRecord(
                memory_id=memory_id,
                memory_type=PERSONA_MEMORY_TYPE,
                summary=trait,
                source_session=f"D{day:02d}",
                source_turn_ids=[source_turn_id],
                timestamp=f"D{day:02d}",
                importance=3,
                topic="persona",
                created_day=day,
                updated_day=day,
                ld_agent_metadata=metadata,
            )
        return {
            "action": action_name,
            "memory_provider": "ld_agent_memory",
            "condition_id": "M0",
            "memory_id": memory_id,
            "memory_type": PERSONA_MEMORY_TYPE,
            "speaker": speaker,
            "source_session": f"D{day:02d}",
            "source_turn_ids": [source_turn_id],
            "status": "success",
        }

    def _retrieve_session_summary_memories(
        self,
        *,
        query: str,
        current_day: int,
    ) -> list[dict[str, Any]]:
        query_topics = _ld_topic_tokens(query)
        current_time = _ld_time(day=current_day, idx=0)
        candidate_ids = self._chroma_candidate_ids(query=query)
        scored = []
        for memory in self.memories.values():
            if memory.memory_type != SESSION_SUMMARY_MEMORY_TYPE:
                continue
            if candidate_ids is not None and memory.memory_id not in candidate_ids:
                continue
            metadata = memory.ld_agent_metadata or {}
            retrieved_topics = [
                item for item in str(metadata.get("topics", memory.topic)).split(",") if item
            ]
            overlap_count = len(set(query_topics) & set(retrieved_topics))
            if not query_topics or not retrieved_topics:
                overlap_score = 0.0
            else:
                overlap_score = 0.5 * (overlap_count / len(query_topics)) + 0.5 * (
                    overlap_count / len(retrieved_topics)
                )
            time_gap = max(0.0, current_time - float(metadata.get("time", 0.0) or 0.0))
            time_decay = math.exp(-self.decay_temp * time_gap)
            overall_score = time_decay * overlap_score
            if overlap_count <= 0:
                continue
            scored.append((overall_score, overlap_score, overlap_count, time_decay, memory))
        scored.sort(key=lambda item: (item[0], item[2], item[4].updated_day), reverse=True)
        return [
            {
                "score": round(score, 4),
                "overlap_score": round(overlap_score, 4),
                "overlap_count": overlap_count,
                "time_decay": round(time_decay, 4),
                "memory": memory.to_dict(),
            }
            for score, overlap_score, overlap_count, time_decay, memory in scored[: self.top_k]
        ]

    def _init_chroma(self) -> None:
        try:
            chromadb = importlib.import_module("chromadb")
        except ImportError as exc:
            raise RuntimeError(
                "ChromaDB backend requested but chromadb is not installed. "
                "Install with `.venv/bin/pip install -e '.[chroma]'`."
            ) from exc
        if self.chroma_path:
            Path(self.chroma_path).mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        else:
            self._chroma_client = chromadb.Client()
        self._chroma_collection = self._chroma_client.get_or_create_collection(
            name=self.chroma_collection,
            embedding_function=_ChromaTopicEmbeddingFunction(),
        )

    def _store_session_summary_in_chroma(
        self,
        *,
        memory_id: str,
        summary: str,
        metadata: dict[str, Any],
    ) -> None:
        if self.storage_backend != "chroma":
            return
        collection = self._chroma_collection
        if collection is None:
            self._init_chroma()
            collection = self._chroma_collection
        chroma_metadata = {
            "memory_id": memory_id,
            "idx": int(metadata.get("idx", 0) or 0),
            "time": float(metadata.get("time", 0.0) or 0.0),
            "topics": str(metadata.get("topics", "")),
            "datatype": str(metadata.get("datatype", "text")),
            "summary": str(metadata.get("summary", summary)),
        }
        try:
            collection.upsert(
                ids=[memory_id],
                documents=[summary],
                metadatas=[chroma_metadata],
            )
        except AttributeError:
            collection.add(
                ids=[memory_id],
                documents=[summary],
                metadatas=[chroma_metadata],
            )

    def _chroma_candidate_ids(self, *, query: str) -> set[str] | None:
        if self.storage_backend != "chroma" or not self.memories:
            return None
        collection = self._chroma_collection
        if collection is None:
            self._init_chroma()
            collection = self._chroma_collection
        n_results = max(self.top_k * 4, self.top_k)
        try:
            results = collection.query(query_texts=[query], n_results=n_results)
        except Exception as exc:
            self.memory_llm_failures.append(
                {
                    "task": "ChromaRetrieve",
                    "reason": f"{type(exc).__name__}: {_truncate(str(exc), 240)}",
                    "fallback_used": True,
                }
            )
            return None
        ids = results.get("ids") or [[]]
        return {str(item) for item in ids[0] if item}

    def _retrieve_persona_memories(self, *, query: str) -> list[dict[str, Any]]:
        query_topics = set(_ld_topic_tokens(query))
        allowed_traits = set(self.user_traits[-self.max_user_personas :])
        hits = []
        for memory in self.memories.values():
            if memory.memory_type != PERSONA_MEMORY_TYPE or memory.summary not in allowed_traits:
                continue
            memory_topics = set(_ld_topic_tokens(memory.summary))
            overlap_count = len(query_topics & memory_topics)
            score = 1.0 if overlap_count else 0.5
            hits.append(
                {
                    "score": score,
                    "overlap_count": overlap_count,
                    "memory": memory.to_dict(),
                }
            )
        hits.sort(key=lambda item: (item["score"], item["overlap_count"]), reverse=True)
        return hits

    def _context_summarize(self, context: str, length: int) -> str:
        if not context.strip():
            return "NO_SUMMARY"
        user_prompt = (
            "#Completed user turns for long-term memory#:\n"
            f"{context}\n\n"
            "Output one concise ordinary session-level memory. Summarize only user-provided "
            "content from this session. Assistant answers, suggestions, examples, and plans "
            "are not user facts and must not be preserved as memory. Do not infer persistent "
            "events, event updates, trajectories, relational anchors, shared handling "
            "strategies, or evaluation labels.\nSUMMARY:"
        )
        fallback = _fallback_session_summary(context, length)
        return self._call_memory_llm(
            task="SessionSummary",
            system_prompt=LD_SESSION_SUMMARY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            fallback=fallback,
            max_tokens=160,
        )

    def _extract_persona_trait(self, sentence: str) -> str:
        if not sentence.strip():
            return "NO_TRAIT"
        user_prompt = (
            LD_PERSONA_EXAMPLES
            + f"Please extract the personal traits who said this sentence "
            f"(no more than 20 words):\n{sentence}\n"
        )
        fallback = _fallback_persona_trait(sentence)
        return self._call_memory_llm(
            task="PersonaExtraction",
            system_prompt=LD_PERSONA_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            fallback=fallback,
            max_tokens=160,
        )

    def _call_memory_llm(
        self,
        *,
        task: str,
        system_prompt: str,
        user_prompt: str,
        fallback: str,
        max_tokens: int,
    ) -> str:
        if not self._has_memory_llm():
            return fallback
        request_client = self.llm_client.with_options(
            max_retries=0,
            timeout=self.llm_timeout,
        )
        last_reason = "empty"
        for attempt, token_limit in enumerate([max_tokens, max(500, max_tokens)], start=1):
            try:
                completion = request_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=token_limit,
                    temperature=0.2,
                )
                content = (completion.choices[0].message.content or "").strip()
                if content:
                    return content
                last_reason = f"empty_response_attempt_{attempt}_max_tokens_{token_limit}"
            except Exception as exc:
                last_reason = f"{type(exc).__name__}: {_truncate(str(exc), 240)}"
                break
        self.memory_llm_failures.append(
            {
                "task": task,
                "reason": last_reason,
                "fallback_used": True,
            }
        )
        return fallback

    def _has_memory_llm(self) -> bool:
        return bool(self.llm_client is not None and self.llm_model)

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
                " ".join(str(item) for item in message.get("domains", []) if item),
                recent,
            ]
            if item
        )

    def _short_term_lines(self) -> list[str]:
        lines = []
        for idx, turn in enumerate(self.short_term_session[-self.short_term_k :], start=1):
            text = _truncate(str(turn.get("dialog") or _format_short_term_turn(turn)), 220)
            if text:
                lines.append(f"- (line {idx}) {text}")
        return lines

    def _session_summary_memory_count(self) -> int:
        return sum(
            1
            for memory in self.memories.values()
            if memory.memory_type == SESSION_SUMMARY_MEMORY_TYPE
        )

    def _stable_memory_id(self, memory_type: str, key: str) -> str:
        digest = hashlib.sha1(f"{memory_type}:{key}".encode("utf-8")).hexdigest()[:12]
        return f"m0_ld_agent:{memory_type}:{digest}"


def _session_topic_text(turns: list[dict[str, Any]]) -> str:
    return " ".join(
        item
        for turn in turns
        for item in [
            str(turn.get("topic", "")),
            str(turn.get("user_message", "")),
            " ".join(str(domain) for domain in turn.get("domains", []) if domain),
        ]
        if item
    )


def _normalize_loaded_m0_memory(memory: MemoryRecord) -> None:
    if memory.memory_type == "event_memory":
        memory.memory_type = SESSION_SUMMARY_MEMORY_TYPE
        metadata = dict(memory.ld_agent_metadata or {})
        metadata.setdefault("memory_name", "event_memory")
        metadata.setdefault("implementation_unit", "session_summary")
        metadata.setdefault("datatype", "text")
        metadata.setdefault("summary", memory.summary)
        metadata.setdefault("topics", memory.topic)
        memory.ld_agent_metadata = metadata
    if memory.memory_type == SESSION_SUMMARY_MEMORY_TYPE:
        if not memory.available_from_session and memory.created_day > 0:
            memory.available_from_session = f"D{memory.created_day + 1:02d}"
        metadata = dict(memory.ld_agent_metadata or {})
        metadata.setdefault("memory_name", "event_memory")
        metadata.setdefault("implementation_unit", "session_summary")
        metadata.setdefault("datatype", "text")
        metadata.setdefault("summary", memory.summary)
        metadata.setdefault("topics", memory.topic)
        metadata.setdefault("source_session_id", memory.source_session)
        if memory.available_from_session:
            metadata.setdefault("available_from_session", memory.available_from_session)
        memory.ld_agent_metadata = metadata


def _message_session_id(message: dict[str, Any]) -> str:
    session_id = str(message.get("session_id") or "").strip()
    if session_id:
        return session_id
    message_id = str(message.get("message_id") or "").strip()
    match = re.match(r"^(D\d+)", message_id)
    if match:
        return match.group(1)
    day = _safe_int(message.get("day"))
    if day > 0:
        return f"D{day:02d}"
    return ""


def _session_day(session_id: Any) -> int | None:
    match = re.match(r"^D(\d+)$", str(session_id or ""))
    if not match:
        return None
    return int(match.group(1))


def _is_probe_turn(message: dict[str, Any]) -> bool:
    turn_type = str(message.get("turn_type", "")).lower()
    message_id = str(message.get("message_id", ""))
    return (
        "probe" in turn_type
        or "_P" in message_id
        or bool(message.get("probe_type"))
        or bool(message.get("target_detail_ids"))
    )


def _format_short_term_turn(turn: dict[str, Any]) -> str:
    parts = []
    user_message = str(turn.get("user_message", "")).strip()
    if user_message:
        parts.append(f"User: {user_message}")
    return " | ".join(parts)


class _ChromaTopicEmbeddingFunction:
    """Small deterministic embedding function to keep Chroma local and auditable."""

    def name(self) -> str:
        return "longmemory_topic_embedding"

    def __call__(self, input: Any) -> list[list[float]]:
        return self._embed(input)

    def embed_query(self, input: Any) -> list[list[float]]:
        return self._embed(input)

    def embed_documents(self, input: Any) -> list[list[float]]:
        return self._embed(input)

    def _embed(self, input: Any) -> list[list[float]]:
        if isinstance(input, str):
            texts = [input]
        else:
            texts = [str(item) for item in input]
        return [_topic_embedding(text) for text in texts]


def _build_user_memory_dialogue(turns: list[dict[str, Any]]) -> str:
    lines = []
    line_no = 1
    for turn in turns:
        if turn.get("user_message"):
            lines.append(f"(line {line_no}) User: {turn.get('user_message')}")
            line_no += 1
    return "\n".join(lines)


def _fallback_session_summary(context: str, length: int) -> str:
    clean = re.sub(r"\s+", " ", context).strip()
    if not clean:
        return "NO_SUMMARY"
    return _truncate(f"User-only session summary from {length} line(s): {clean}", 220)


def _fallback_persona_trait(sentence: str) -> str:
    text = sentence.strip()
    if len(text) < 4:
        return "NO_TRAIT"
    if any(marker in text for marker in ["我", "我的", "我们", "孩子", "工作", "论文"]):
        return _truncate(text, 80)
    if any(marker in text for marker in ["实在一点", "标准答案", "别先安慰", "少废话"]):
        return "用户希望回应更实在，少标准答案。"
    return "NO_TRAIT"


def _importance_from_turns(turns: list[dict[str, Any]]) -> int:
    text = " ".join(str(turn.get("memory_relevance", "")) for turn in turns)
    if any(marker in text for marker in ["shared_event", "long_term", "probe"]):
        return 4
    if len(turns) >= 3:
        return 4
    return 3


def _ld_topic_tokens(text: str) -> list[str]:
    lowered = text.lower()
    tokens = set(re.findall(r"[a-z0-9_]{2,}", lowered))
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if len(chunk) <= 12:
            tokens.add(chunk)
        for size in (2, 3):
            for idx in range(0, max(0, len(chunk) - size + 1)):
                tokens.add(chunk[idx : idx + size])
    return sorted(tokens)


def _topic_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in _ld_topic_tokens(text):
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _ld_time(*, day: int, idx: int) -> float:
    if day <= 0:
        return float(idx)
    return float(day * 24 * 60 * 60 + idx)


def _is_valid_trait(trait: str) -> bool:
    clean = trait.strip()
    if not clean or "NO_TRAIT" in clean or len(clean) <= 3:
        return False
    forbidden = [
        "关系期待",
        "长期陪伴",
        "熟悉",
        "亲密",
        "客服",
        "边界",
        "共同策略",
        "关系锚点",
        "shared handling",
        "relational",
        "anchor",
        "trajectory",
    ]
    return not any(item in clean for item in forbidden)


def _normalize_storage_backend(value: str) -> str:
    backend = str(value or "json").strip().lower()
    if backend not in {"json", "chroma"}:
        raise ValueError(f"Unsupported LD-Agent memory storage backend: {value}")
    return backend


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
