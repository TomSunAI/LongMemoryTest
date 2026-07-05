#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.llm import LLMConfigError, create_llm_client  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test the configured OpenAI-compatible LLM API."
    )
    parser.add_argument(
        "--prompt",
        default="用一句话说明你已连接成功。",
        help="Prompt to send to the configured model.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        client, config = create_llm_client()
    except LLMConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    completion = client.chat.completions.create(
        model=config.model,
        messages=[
            {"role": "system", "content": "You are a concise test assistant."},
            {"role": "user", "content": args.prompt},
        ],
    )
    print(completion.choices[0].message.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
