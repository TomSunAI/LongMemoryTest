from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryRecord:
    memory_id: str
    memory_type: str
    summary: str
    raw_dialogue: str = ""
    source_session: str = ""
    source_turn_ids: list[str] = field(default_factory=list)
    timestamp: str = ""
    importance: int = 3
    topic: str = ""
    created_day: int = 0
    updated_day: int = 0
    ld_agent_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "summary": self.summary,
            "raw_dialogue": self.raw_dialogue,
            "source_session": self.source_session,
            "source_turn_ids": list(self.source_turn_ids),
            "timestamp": self.timestamp,
            "importance": self.importance,
            "topic": self.topic,
            "created_day": self.created_day,
            "updated_day": self.updated_day,
            "ld_agent_metadata": dict(self.ld_agent_metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryRecord":
        return cls(
            memory_id=str(data.get("memory_id", "")),
            memory_type=str(data.get("memory_type", "")),
            summary=str(data.get("summary", "")),
            raw_dialogue=str(data.get("raw_dialogue", "")),
            source_session=str(data.get("source_session", "")),
            source_turn_ids=[str(item) for item in data.get("source_turn_ids", [])],
            timestamp=str(data.get("timestamp", "")),
            importance=int(data.get("importance", 3) or 3),
            topic=str(data.get("topic", "")),
            created_day=int(data.get("created_day", 0) or 0),
            updated_day=int(data.get("updated_day", 0) or 0),
            ld_agent_metadata=dict(data.get("ld_agent_metadata", {}) or {}),
        )
