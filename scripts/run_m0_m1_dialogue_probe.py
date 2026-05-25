#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.letta_memory import create_b_memory_agent, create_letta_client  # noqa: E402
from long_memory_test.llm import create_llm_client  # noqa: E402


DEFAULT_M1_MEMORY = (
    "用户偏好直接、自然、少废话的回应；不喜欢客服式寒暄和空泛安慰。"
    "当用户焦虑时，更需要先拆事实、选项、风险和下一步，而不是被泛泛安抚。"
    "用户希望 Agent 像长期朋友一样回应，语气可以真诚但不要过度解释。"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one A/B dialogue turn under M0 and M1.")
    parser.add_argument(
        "--daily-messages",
        type=Path,
        default=REPO_ROOT / "sample_output/daily_user_message.json",
        help="Path to daily_user_message.json.",
    )
    parser.add_argument(
        "--message-id",
        default="D01_M001",
        help="Message id to use as the user input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "sample_output/m0_m1_dialogue_probe.json",
        help="Output JSON path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    messages_doc = json.loads(args.daily_messages.read_text(encoding="utf-8"))
    message = _find_message(messages_doc["messages"], args.message_id)

    letta_client, letta_config = create_letta_client()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    b_agent = create_b_memory_agent(
        client=letta_client,
        config=letta_config,
        name=f"longmemory-b-m0-m1-probe-{timestamp}",
    )
    letta_client.agents.blocks.update(
        agent_id=b_agent.id,
        block_label="m1_relationship",
        value=DEFAULT_M1_MEMORY,
    )
    m1_block = letta_client.agents.blocks.retrieve(
        agent_id=b_agent.id,
        block_label="m1_relationship",
    )

    llm_client, llm_config = create_llm_client()
    user_message = message["user_message"]

    m0_answer = _ask_a(
        client=llm_client,
        model=llm_config.model,
        memory_level="M0",
        user_message=user_message,
        memory_context=None,
    )
    m1_answer = _ask_a(
        client=llm_client,
        model=llm_config.model,
        memory_level="M1",
        user_message=user_message,
        memory_context=m1_block.value,
    )

    result = {
        "probe": "m0_vs_m1_single_turn",
        "message_id": args.message_id,
        "user_message": user_message,
        "b_agent_id": b_agent.id,
        "letta": {
            "base_url": letta_config.base_url,
            "model": letta_config.model,
            "embedding": letta_config.embedding,
            "m1_block_label": "m1_relationship",
            "m1_block_value": m1_block.value,
        },
        "llm": {
            "provider": llm_config.provider,
            "base_url": llm_config.base_url,
            "model": llm_config.model,
        },
        "responses": {
            "M0": {
                "memory_available": False,
                "answer": m0_answer,
            },
            "M1": {
                "memory_available": True,
                "answer": m1_answer,
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"User message: {user_message}")
    print("\n[M0]\n" + m0_answer)
    print("\n[M1]\n" + m1_answer)
    print(f"\nWrote {args.output}")
    return 0


def _find_message(messages: list[dict], message_id: str) -> dict:
    for message in messages:
        if message["message_id"] == message_id:
            return message
    raise ValueError(f"Message id not found: {message_id}")


def _ask_a(
    client,
    model: str,
    memory_level: str,
    user_message: str,
    memory_context: str | None,
) -> str:
    system_parts = [
        "你是 A，一个拟人、自然、长期陪伴型对话 Agent。",
        "你要像一个稳定的长期朋友一样回应，但不能编造自己没有被提供的历史记忆。",
        "回答要中文、自然、具体，不要写成报告。",
    ]
    if memory_level == "M0":
        system_parts.append("当前记忆层级是 M0：你没有任何历史记忆，只能根据当前用户消息回应。")
    else:
        system_parts.append(
            "当前记忆层级是 M1：你只能使用结论级关系记忆，不能声称知道具体历史事件。"
        )
        system_parts.append(f"M1 关系记忆：{memory_context}")

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "\n".join(system_parts)},
            {"role": "user", "content": user_message},
        ],
    )
    return completion.choices[0].message.content or ""


if __name__ == "__main__":
    raise SystemExit(main())
