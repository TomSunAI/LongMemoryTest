from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from letta_client import Letta

from long_memory_test.llm import load_dotenv_local


DEFAULT_LETTA_BASE_URL = "http://127.0.0.1:8283"
DEFAULT_LETTA_MODEL = "openai-proxy/deepseek-v4-pro"
DEFAULT_LETTA_EMBEDDING = "letta/letta-free"
CURATED_RELATIONAL_BLOCK_LABELS = {
    "m1_relationship",
    "m2_shared_events",
    "m3_event_details",
}
M0_CONVERSATION_BLOCK_LABEL = "m0_conversation_history"
M0_LETTA_WRITEBACK_TAGS = ("long_memory_experiment", "m0_default_memory")
M0_CORE_BLOCK_CHAR_LIMIT = 18000


@dataclass(frozen=True)
class LettaConfig:
    base_url: str
    model: str
    embedding: str


def get_letta_config() -> LettaConfig:
    _load_letta_env()
    return LettaConfig(
        base_url=os.getenv("LETTA_BASE_URL", DEFAULT_LETTA_BASE_URL),
        model=os.getenv("LETTA_MODEL", DEFAULT_LETTA_MODEL),
        embedding=os.getenv("LETTA_EMBEDDING", DEFAULT_LETTA_EMBEDDING),
    )


def _load_letta_env() -> None:
    load_dotenv_local()
    letta_env_path = Path(".env.letta.local")
    if not letta_env_path.exists():
        return
    for raw_line in letta_env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip("'").strip('"')


def create_letta_client(config: LettaConfig | None = None) -> tuple[Letta, LettaConfig]:
    resolved = config or get_letta_config()
    return Letta(base_url=resolved.base_url), resolved


def create_b_memory_agent(client: Letta, config: LettaConfig, name: str):
    return client.agents.create(
        name=name,
        model=config.model,
        embedding=config.embedding,
        memory_blocks=[
            {
                "label": "persona",
                "value": "B is the memory policy and memory management agent for LongMemoryTest.",
                "description": "Stable role definition for the B memory agent.",
                "read_only": True,
                "limit": 2000,
            },
            {
                "label": "m1_relationship",
                "value": "No stable relationship-level memory has been written yet.",
                "description": "M1 conclusion-level memory: user preferences, communication style, stable pressure sources.",
                "limit": 5000,
            },
            {
                "label": "m2_shared_events",
                "value": "No shared event-level memory has been written yet.",
                "description": "M2 shared event memory: important ongoing events discussed with the agent and their status.",
                "limit": 8000,
            },
            {
                "label": "m3_event_details",
                "value": "No high-salience event-detail memory has been written yet.",
                "description": "M3 event-detail memory: emotional reasons, triggers, deeper concerns, and follow-up points.",
                "limit": 8000,
            },
        ],
        include_base_tools=True,
    )


def create_m0_default_memory_agent(client: Letta, config: LettaConfig, name: str):
    """Create a Letta default-memory baseline agent.

    This agent intentionally does not attach the handcrafted M1/M2/M3
    relational-memory blocks. It is meant to represent generic Letta memory:
    default core memory, ordinary summaries/retrieval, and same-session state.
    """

    return client.agents.create(
        name=name,
        model=config.model,
        embedding=config.embedding,
        include_base_tools=True,
        include_default_source=True,
        memory_blocks=[
            {
                "label": "persona",
                "value": (
                    "A is a normal long-running assistant using Letta's default "
                    "memory management. It has no handcrafted relational memory "
                    "policy for this experiment."
                ),
                "description": "Generic assistant persona for the M0 Letta baseline.",
                "limit": 2000,
            },
            {
                "label": "human",
                "value": (
                    "The user may discuss parenting, work collaboration, papers, "
                    "family coordination, sleep, and social fatigue over time. "
                    "No curated event timeline or BEI labels are available."
                ),
                "description": "Generic user profile for Letta default memory.",
                "limit": 3000,
            },
            {
                "label": M0_CONVERSATION_BLOCK_LABEL,
                "value": "No M0 conversation turns have been written yet.",
                "description": (
                    "M0 generic conversation history written by the controlled "
                    "experiment runner. This is ordinary Letta core memory, not "
                    "handcrafted relational memory."
                ),
                "limit": 20000,
            },
        ],
    )


def read_m0_letta_memory_payload(
    *,
    client: Letta,
    agent_id: str,
    query: str,
    search_limit: int = 5,
) -> dict[str, Any]:
    """Read the runtime M0 memory payload from Letta.

    M0 is allowed to use generic Letta memory, but it must not read the
    handcrafted relational-memory blocks used by M1/M2/M3.
    """

    if not agent_id:
        raise ValueError("M0 Letta baseline requires a Letta agent id.")

    blocks = list(client.agents.blocks.list(agent_id=agent_id, limit=100))
    included_blocks = []
    excluded_labels = []
    for block in blocks:
        block_data = _model_to_dict(block)
        label = str(block_data.get("label") or "")
        if label in CURATED_RELATIONAL_BLOCK_LABELS:
            excluded_labels.append(label)
            continue
        included_blocks.append(block_data)

    message_hits = (
        _safe_message_search(
            client=client,
            agent_id=agent_id,
            query=query,
            search_limit=search_limit,
        )
        if _m0_message_search_enabled()
        else []
    )
    passage_hits = (
        _safe_passage_search(
            client=client,
            agent_id=agent_id,
            query=query,
            search_limit=search_limit,
        )
        if _m0_passage_search_enabled()
        else []
    )
    block_source_ids = [
        f"letta:block:{item.get('label') or item.get('id')}"
        for item in included_blocks
        if item.get("label") or item.get("id")
    ]
    message_hit_ids = [_hit_id(hit) for hit in message_hits]
    passage_hit_ids = [_hit_id(hit) for hit in passage_hits]

    lines = [
        "Letta 默认记忆基线：以下内容来自运行时 Letta agent 的普通记忆，"
        "不包含手工整理的关系记忆、事件轨迹、人工评测标注或关系锚点。"
    ]
    if included_blocks:
        lines.append("Core memory blocks:")
        for block in included_blocks:
            label = block.get("label") or block.get("id") or "unknown"
            value = str(block.get("value") or "").strip()
            if value:
                lines.append(f"- {label}: {value}")
    else:
        lines.append("Core memory blocks: none returned by Letta.")

    if message_hits:
        lines.append("普通历史检索片段:")
        for hit in message_hits:
            text = _hit_text(hit)
            if text:
                lines.append(f"- {text}")
    if passage_hits:
        lines.append("普通 archival/passages 检索片段:")
        for hit in passage_hits:
            text = _hit_text(hit)
            if text:
                lines.append(f"- {text}")
    if excluded_labels:
        lines.append(
            "已排除 handcrafted relational memory blocks: "
            + ", ".join(sorted(set(excluded_labels)))
        )

    return {
        "condition_id": "M0",
        "memory_provider": "letta",
        "letta_agent_id": agent_id,
        "memory_context": "\n".join(lines),
        "source_detail_ids": (
            block_source_ids
            + [f"letta:message:{item}" for item in message_hit_ids if item]
            + [f"letta:passage:{item}" for item in passage_hit_ids if item]
        ),
        "retrieval": {
            "core_block_count": len(included_blocks),
            "message_hit_count": len(message_hits),
            "passage_hit_count": len(passage_hits),
            "message_hit_ids": [item for item in message_hit_ids if item],
            "passage_hit_ids": [item for item in passage_hit_ids if item],
            "excluded_block_labels": sorted(set(excluded_labels)),
        },
    }


def write_m0_letta_turn_memory(
    *,
    client: Letta,
    agent_id: str,
    run_id: str,
    message_id: str,
    day: int | str | None,
    topic: str | None,
    turn_type: str | None,
    user_message: str,
    assistant_answer: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Store the completed M0 turn in Letta archival memory.

    The experiment keeps the responder LLM controlled across M0/M1/M2/M3, so
    this writeback does not ask Letta to generate the answer. It stores only the
    M0 branch's ordinary dialogue record in a generic Letta core-memory block.
    """

    if not agent_id:
        raise ValueError("M0 Letta writeback requires a Letta agent id.")
    text = _format_m0_turn_memory_text(
        run_id=run_id,
        message_id=message_id,
        day=day,
        topic=topic,
        turn_type=turn_type,
        user_message=user_message,
        assistant_answer=assistant_answer,
    )
    block = _ensure_m0_conversation_block(
        client=client,
        agent_id=agent_id,
    )
    block_value = str(block.get("value") or "")
    block_id = block.get("id")
    if _m0_block_contains_turn(block_value, run_id=run_id, message_id=message_id):
        return {
            "action": "m0_letta_turn_writeback",
            "condition_id": "M0",
            "memory_provider": "letta",
            "method": "agents.blocks.update",
            "status": "skipped_existing",
            "letta_agent_id": agent_id,
            "run_id": run_id,
            "message_id": message_id,
            "block_label": M0_CONVERSATION_BLOCK_LABEL,
            "block_id": block_id,
            "text_char_count": len(text),
        }

    new_value = _append_m0_block_turn(block_value, text)
    response = client.agents.blocks.update(
        M0_CONVERSATION_BLOCK_LABEL,
        agent_id=agent_id,
        value=new_value,
        limit=20000,
    )
    response_data = _model_to_dict(response)
    return {
        "action": "m0_letta_turn_writeback",
        "condition_id": "M0",
        "memory_provider": "letta",
        "method": "agents.blocks.update",
        "status": "success",
        "letta_agent_id": agent_id,
        "run_id": run_id,
        "message_id": message_id,
        "block_label": M0_CONVERSATION_BLOCK_LABEL,
        "block_id": response_data.get("id") or block_id,
        "text_char_count": len(text),
    }


def _ensure_m0_conversation_block(
    *,
    client: Letta,
    agent_id: str,
) -> dict[str, Any]:
    blocks = [_model_to_dict(item) for item in client.agents.blocks.list(agent_id=agent_id, limit=100)]
    for block in blocks:
        if block.get("label") == M0_CONVERSATION_BLOCK_LABEL:
            return block

    block = client.blocks.create(
        label=M0_CONVERSATION_BLOCK_LABEL,
        value="No M0 conversation turns have been written yet.",
        description=(
            "M0 generic conversation history written by the controlled "
            "experiment runner. This is ordinary Letta core memory, not "
            "handcrafted relational memory."
        ),
        limit=20000,
        tags=list(M0_LETTA_WRITEBACK_TAGS),
    )
    block_data = _model_to_dict(block)
    block_id = block_data.get("id")
    if not block_id:
        raise RuntimeError("Created M0 conversation block did not return an id.")
    client.agents.blocks.attach(
        str(block_id),
        agent_id=agent_id,
    )
    return block_data


def _m0_block_contains_turn(block_value: str, *, run_id: str, message_id: str) -> bool:
    return f"run_id: {run_id}" in block_value and f"message_id: {message_id}" in block_value


def _append_m0_block_turn(block_value: str, turn_text: str) -> str:
    existing = block_value.strip()
    if not existing or existing == "No M0 conversation turns have been written yet.":
        combined = turn_text.strip()
    else:
        combined = f"{existing}\n\n---\n\n{turn_text.strip()}"
    if len(combined) <= M0_CORE_BLOCK_CHAR_LIMIT:
        return combined
    return "[older M0 conversation turns trimmed]\n" + combined[-M0_CORE_BLOCK_CHAR_LIMIT:]


def _m0_passage_search_enabled() -> bool:
    return os.getenv("M0_LETTA_ENABLE_PASSAGE_SEARCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _m0_message_search_enabled() -> bool:
    return os.getenv("M0_LETTA_ENABLE_MESSAGE_SEARCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _safe_message_search(
    *,
    client: Letta,
    agent_id: str,
    query: str,
    search_limit: int,
) -> list[dict[str, Any]]:
    try:
        response = client.messages.search(
            agent_id=agent_id,
            query=query,
            limit=search_limit,
            search_mode="hybrid",
        )
    except Exception:
        return []
    return _extract_search_items(response)


def _safe_passage_search(
    *,
    client: Letta,
    agent_id: str,
    query: str,
    search_limit: int,
) -> list[dict[str, Any]]:
    try:
        response = client.agents.passages.search(
            agent_id=agent_id,
            query=query,
            top_k=search_limit,
        )
    except Exception:
        try:
            response = client.passages.search(
                agent_id=agent_id,
                query=query,
                limit=search_limit,
            )
        except Exception:
            return []
    return _extract_search_items(response)


def _format_m0_turn_memory_text(
    *,
    run_id: str,
    message_id: str,
    day: int | str | None,
    topic: str | None,
    turn_type: str | None,
    user_message: str,
    assistant_answer: str,
) -> str:
    lines = [
        "M0 Letta default-memory dialogue turn.",
        f"run_id: {run_id}",
        f"message_id: {message_id}",
    ]
    if day is not None:
        lines.append(f"day: {day}")
    if topic:
        lines.append(f"topic: {topic}")
    if turn_type:
        lines.append(f"turn_type: {turn_type}")
    lines.extend(
        [
            "",
            "user_message:",
            user_message.strip(),
            "",
            "m0_assistant_answer:",
            assistant_answer.strip(),
        ]
    )
    return "\n".join(lines)


def _extract_search_items(response: Any) -> list[dict[str, Any]]:
    data = _model_to_dict(response)
    for key in ["results", "items", "messages", "passages", "data"]:
        value = data.get(key)
        if isinstance(value, list):
            return [_model_to_dict(item) for item in value]
    if isinstance(response, list):
        return [_model_to_dict(item) for item in response]
    return []


def _hit_text(hit: dict[str, Any]) -> str:
    for key in ["text", "content", "message", "value"]:
        value = hit.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = _hit_text(value)
            if nested:
                return nested
    return ""


def _hit_id(hit: dict[str, Any]) -> str:
    for key in ["id", "message_id", "passage_id"]:
        value = hit.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ["message", "passage", "metadata"]:
        value = hit.get(key)
        if isinstance(value, dict):
            nested = _hit_id(value)
            if nested:
                return nested
    return ""


def _model_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    for method in ["model_dump", "dict"]:
        dumper = getattr(value, method, None)
        if callable(dumper):
            try:
                dumped = dumper()
            except TypeError:
                dumped = dumper
            if isinstance(dumped, dict):
                return dumped
    result = {}
    for key in ["id", "label", "value", "description", "text", "content"]:
        if hasattr(value, key):
            result[key] = getattr(value, key)
    return result
