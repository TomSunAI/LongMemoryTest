from __future__ import annotations

import os
from dataclasses import dataclass

from letta_client import Letta

from long_memory_test.llm import load_dotenv_local


DEFAULT_LETTA_BASE_URL = "http://127.0.0.1:8283"
DEFAULT_LETTA_MODEL = "openai-proxy/gpt-5.2"
DEFAULT_LETTA_EMBEDDING = "openai/text-embedding-3-small"


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
