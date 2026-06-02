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

from long_memory_test.letta_memory import (  # noqa: E402
    create_letta_client,
    create_m0_default_memory_agent,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Letta default-memory agent for the M0 baseline."
    )
    parser.add_argument(
        "--name-prefix",
        default="longmemory-m0-letta",
        help="Prefix for the Letta baseline agent name.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client, config = create_letta_client()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    agent_name = f"{args.name_prefix}-{timestamp}"
    agent = create_m0_default_memory_agent(
        client=client,
        config=config,
        name=agent_name,
    )
    print(f"Letta base URL: {config.base_url}")
    print(f"Letta model: {config.model}")
    print(f"Letta embedding: {config.embedding}")
    print(f"M0 Letta baseline agent: {agent.name}")
    print(f"LETTA_M0_AGENT_ID={agent.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
