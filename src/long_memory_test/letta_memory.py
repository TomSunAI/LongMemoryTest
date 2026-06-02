from __future__ import annotations

import os
from dataclasses import dataclass
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


@dataclass(frozen=True)
class LettaConfig:
    base_url: str
    model: str
    embedding: str


def get_letta_config() -> LettaConfig:
    load_dotenv_local()
    return LettaConfig(
        base_url=os.getenv("LETTA_BASE_URL", DEFAULT_LETTA_BASE_URL),
        model=os.getenv("LETTA_MODEL", DEFAULT_LETTA_MODEL),
        embedding=os.getenv("LETTA_EMBEDDING", DEFAULT_LETTA_EMBEDDING),
    )


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

    message_hits = _safe_message_search(
        client=client,
        agent_id=agent_id,
        query=query,
        search_limit=search_limit,
    )
    passage_hits = _safe_passage_search(
        client=client,
        agent_id=agent_id,
        query=query,
        search_limit=search_limit,
    )

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
        "source_detail_ids": [
            f"letta:block:{item.get('label') or item.get('id')}"
            for item in included_blocks
            if item.get("label") or item.get("id")
        ],
        "retrieval": {
            "core_block_count": len(included_blocks),
            "message_hit_count": len(message_hits),
            "passage_hit_count": len(passage_hits),
            "excluded_block_labels": sorted(set(excluded_labels)),
        },
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
        response = client.passages.search(
            agent_id=agent_id,
            query=query,
            limit=search_limit,
        )
    except Exception:
        return []
    return _extract_search_items(response)


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
