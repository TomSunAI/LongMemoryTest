#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.letta_memory import create_b_memory_agent, create_letta_client  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test Letta-backed B memory blocks.")
    parser.add_argument(
        "--name-prefix",
        default="longmemory-b-smoke",
        help="Prefix for the temporary Letta agent name.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client, config = create_letta_client()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    agent_name = f"{args.name_prefix}-{timestamp}"

    agent = create_b_memory_agent(client=client, config=config, name=agent_name)
    agent_id = agent.id

    initial = client.agents.blocks.retrieve(
        agent_id=agent_id,
        block_label="m2_shared_events",
    )

    updated_value = (
        "User is tracking the child's kindergarten instability as an ongoing shared event. "
        "Current state: the user is considering alternatives and wants practical next steps."
    )
    client.agents.blocks.update(
        agent_id=agent_id,
        block_label="m2_shared_events",
        value=updated_value,
    )
    updated = client.agents.blocks.retrieve(
        agent_id=agent_id,
        block_label="m2_shared_events",
    )

    print(f"Letta base URL: {config.base_url}")
    print(f"Letta model: {config.model}")
    print(f"Letta embedding: {config.embedding}")
    print(f"Created B memory agent: {agent.name} ({agent_id})")
    print(f"Initial M2 block: {initial.value}")
    print(f"Updated M2 block: {updated.value}")
    print("Letta memory block update: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
