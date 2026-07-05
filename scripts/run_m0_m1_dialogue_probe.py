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
    "当用户焦虑时，更需要先拆事实、选项、风险和下一步，"
    "而不是被泛泛安抚。"
    "用户希望 Agent 像长期朋友一样回应，语气可以真诚但不要过度解释。"
)
DEFAULT_DEEPSEEK_MAX_OUTPUT_TOKENS = 384_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one A/B dialogue turn under M0 and M1.")
    parser.add_argument(
        "--daily-messages",
        type=Path,
        default=REPO_ROOT / "sample_output/daily_user_message.json",
        help="Path to daily_user_message.json.",
    )
    parser.add_argument(
        "--scene-cards",
        type=Path,
        default=REPO_ROOT / "sample_output/daily_scene_cards.json",
        help="Path to daily_scene_cards.json for script-anchored same-day follow-ups.",
    )
    parser.add_argument(
        "--probe-questions",
        type=Path,
        default=None,
        help=(
            "Optional path to probe_question_plan.json. When set, targeted probe "
            "questions are inserted after each day's requested scene follow-ups."
        ),
    )
    parser.add_argument(
        "--message-id",
        default="D01_M001",
        help="Single message id to use as the user input when --message-ids is not set.",
    )
    parser.add_argument(
        "--message-ids",
        default=None,
        help=(
            "Comma-separated message ids to run as one conversation chain, "
            "e.g. D01_M001,D02_M001."
        ),
    )
    parser.add_argument(
        "--all-message-ids",
        action="store_true",
        help="Run every message in daily_user_message.json as one conversation chain.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "sample_output/m0_m1_dialogue_probe.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--conversation-log",
        type=Path,
        default=REPO_ROOT / "sample_output/conversation_log.json",
        help="Sync structured M0/M1 dialogue records to this JSON log.",
    )
    parser.add_argument(
        "--reset-conversation-log",
        action="store_true",
        help="Start a fresh conversation log before syncing this run.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume from an existing --output file. Completed turns are loaded, "
            "short-term context is rebuilt, and remaining turns continue."
        ),
    )
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=600.0,
        help="Per-response LLM request timeout in seconds.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help=(
            "Maximum output tokens for each assistant answer. "
            "Defaults to the provider maximum when known."
        ),
    )
    parser.add_argument(
        "--scene-followups",
        type=int,
        default=0,
        help="Number of LLM-generated same-day user follow-ups to run after each scripted opening.",
    )
    parser.add_argument(
        "--print-mode",
        choices=["all", "summary"],
        default="all",
        help="Print full dialogue turns or only a compact run summary.",
    )
    parser.add_argument(
        "--print-progress",
        action="store_true",
        help="Print one progress line before each user turn is sent to M0/M1.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    messages_doc = json.loads(args.daily_messages.read_text(encoding="utf-8"))
    message_ids = _resolve_message_ids(args, messages_doc["messages"])
    messages = [_find_message(messages_doc["messages"], message_id) for message_id in message_ids]
    scene_cards = (
        _load_scene_cards(args.scene_cards)
        if args.scene_followups > 0 or args.probe_questions
        else {}
    )
    probe_questions = _load_probe_questions(args.probe_questions) if args.probe_questions else {}
    existing_result = _load_resume_result(args.output) if args.resume else None

    letta_client, letta_config = create_letta_client()
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M%S")
    created_at = (
        existing_result.get("created_at")
        if existing_result
        else now.isoformat().replace("+00:00", "Z")
    ) or now.isoformat().replace("+00:00", "Z")
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
    max_tokens = args.max_tokens or _default_max_tokens(llm_config.provider, llm_config.model)

    run_id = existing_result.get("run_id") if existing_result else f"m0_m1_probe_{timestamp}"
    expected_turns = _expected_turn_count(
        messages, scene_cards, args.scene_followups, probe_questions
    )
    result = _build_probe_result(
        existing_result=existing_result,
        run_id=run_id,
        created_at=created_at,
        message_ids=message_ids,
        b_agent_id=b_agent.id,
        letta_config=letta_config,
        llm_config=llm_config,
        max_tokens=max_tokens,
        timeout_seconds=args.llm_timeout,
        m1_memory=m1_block.value,
        scene_followups=args.scene_followups,
        probe_questions_path=args.probe_questions,
        expected_turns=expected_turns,
    )
    turns = result["turns"]
    expected_message_ids = _expected_message_id_sequence(
        messages=messages,
        scene_cards=scene_cards,
        scene_followups=args.scene_followups,
        probe_questions=probe_questions,
    )
    _assert_completed_turns_are_expected_prefix(turns, expected_message_ids)
    (
        short_term_histories,
        transcript_message_ids,
        completed_turn_inputs,
    ) = _rebuild_runtime_state(turns)
    completed_message_ids = set(transcript_message_ids)
    turn_index = len(turns)
    _write_checkpoint(
        output_path=args.output,
        conversation_log_path=args.conversation_log,
        result=result,
        reset_conversation_log=args.reset_conversation_log,
        status="running",
    )

    for message in messages:
        scene_card = scene_cards.get(message["message_id"])
        followup_budget = (
            int(scene_card.get("expansion_controls", {}).get("followup_budget", 0))
            if scene_card
            else 0
        )
        requested_followups = min(max(args.scene_followups, 0), followup_budget)
        user_inputs = [message]
        current_input = message

        for followup_index in range(0, requested_followups + 1):
            current_message_id = current_input["message_id"]
            if current_message_id not in completed_message_ids:
                turn_index += 1
                if args.print_progress:
                    print(
                        "[progress] "
                        f"turn {turn_index}/{expected_turns} "
                        f"day={current_input['day']} "
                        f"message_id={current_message_id} "
                        f"type={current_input.get('turn_type', 'scripted_opening')}",
                        flush=True,
                    )
                turn = _run_variant_turn(
                    run_id=run_id,
                    created_at=created_at,
                    turn_index=turn_index,
                    daily_messages_path=args.daily_messages,
                    scene_cards_path=args.scene_cards if scene_card else None,
                    message=current_input,
                    scene_card=scene_card,
                    b_agent_id=b_agent.id,
                    letta_config=letta_config,
                    llm_client=llm_client,
                    llm_config=llm_config,
                    max_tokens=max_tokens,
                    timeout_seconds=args.llm_timeout,
                    m1_memory=m1_block.value,
                    short_term_histories=short_term_histories,
                    previous_message_ids=list(transcript_message_ids),
                )
                turns.append(turn)
                transcript_message_ids.append(current_message_id)
                completed_message_ids.add(current_message_id)
                completed_turn_inputs[current_message_id] = current_input
                _write_checkpoint(
                    output_path=args.output,
                    conversation_log_path=args.conversation_log,
                    result=result,
                    reset_conversation_log=args.reset_conversation_log,
                    status="running",
                )

            if followup_index == requested_followups:
                break
            if not scene_card:
                break

            next_followup_index = followup_index + 1
            next_message_id = f"{message['message_id']}_F{next_followup_index:03d}"
            if next_message_id in completed_turn_inputs:
                current_input = completed_turn_inputs[next_message_id]
            else:
                followup = _generate_user_followup(
                    client=llm_client,
                    model=llm_config.model,
                    scene_card=scene_card,
                    opening_message=message,
                    followup_index=next_followup_index,
                    previous_user_messages=[item["user_message"] for item in user_inputs],
                    timeout=args.llm_timeout,
                    max_tokens=max_tokens,
                )
                current_input = _build_followup_message(
                    opening_message=message,
                    scene_card=scene_card,
                    followup_index=next_followup_index,
                    followup=followup,
                )
            user_inputs.append(current_input)
        for probe_question in probe_questions.get(message["message_id"], []):
            current_message_id = probe_question["message_id"]
            if current_message_id in completed_message_ids:
                continue
            turn_index += 1
            if args.print_progress:
                print(
                    "[progress] "
                    f"turn {turn_index}/{expected_turns} "
                    f"day={probe_question['day']} "
                    f"message_id={current_message_id} "
                    "type=targeted_probe",
                    flush=True,
                )
            turn = _run_variant_turn(
                run_id=run_id,
                created_at=created_at,
                turn_index=turn_index,
                daily_messages_path=args.daily_messages,
                scene_cards_path=args.scene_cards if scene_card else None,
                message=probe_question,
                scene_card=scene_card,
                b_agent_id=b_agent.id,
                letta_config=letta_config,
                llm_client=llm_client,
                llm_config=llm_config,
                max_tokens=max_tokens,
                timeout_seconds=args.llm_timeout,
                m1_memory=m1_block.value,
                short_term_histories=short_term_histories,
                previous_message_ids=list(transcript_message_ids),
            )
            turns.append(turn)
            transcript_message_ids.append(current_message_id)
            completed_message_ids.add(current_message_id)
            completed_turn_inputs[current_message_id] = probe_question
            _write_checkpoint(
                output_path=args.output,
                conversation_log_path=args.conversation_log,
                result=result,
                reset_conversation_log=args.reset_conversation_log,
                status="running",
            )
    _write_checkpoint(
        output_path=args.output,
        conversation_log_path=args.conversation_log,
        result=result,
        reset_conversation_log=args.reset_conversation_log,
        status="complete",
    )

    if args.print_mode == "all":
        for turn in turns:
            print(f"\n[{turn['source']['message_id']}] {turn['input']['user_message']}")
            print("\n[M0]\n" + turn["variants"]["M0"]["assistant_answer"])
            print("\n[M1]\n" + turn["variants"]["M1"]["assistant_answer"])
    else:
        _print_run_summary(turns)
    print(f"\nWrote {args.output}")
    print(f"Synced {args.conversation_log}")
    return 0


def _resolve_message_ids(args: argparse.Namespace, messages: list[dict]) -> list[str]:
    if args.all_message_ids:
        return [message["message_id"] for message in messages]
    if args.message_ids:
        return [
            message_id.strip()
            for message_id in args.message_ids.split(",")
            if message_id.strip()
        ]
    return [args.message_id]


def _print_run_summary(turns: list[dict]) -> None:
    days = sorted({turn["input"]["day"] for turn in turns})
    scripted_count = sum(
        1 for turn in turns if turn["source"]["turn_type"] == "scripted_opening"
    )
    followup_count = sum(
        1 for turn in turns if turn["source"]["turn_type"] == "llm_user_followup"
    )
    print(
        "Run summary: "
        f"days={len(days)}, turns={len(turns)}, "
        f"scripted_openings={scripted_count}, llm_followups={followup_count}"
    )
    if turns:
        print(
            "Message range: "
            f"{turns[0]['source']['message_id']} -> {turns[-1]['source']['message_id']}"
        )


def _expected_turn_count(
    messages: list[dict],
    scene_cards: dict[str, dict],
    scene_followups: int,
    probe_questions: dict[str, list[dict]] | None = None,
) -> int:
    count = 0
    probe_questions = probe_questions or {}
    for message in messages:
        scene_card = scene_cards.get(message["message_id"])
        followup_budget = (
            int(scene_card.get("expansion_controls", {}).get("followup_budget", 0))
            if scene_card
            else 0
        )
        count += 1 + min(max(scene_followups, 0), followup_budget)
        count += len(probe_questions.get(message["message_id"], []))
    return count


def _expected_message_id_sequence(
    *,
    messages: list[dict],
    scene_cards: dict[str, dict],
    scene_followups: int,
    probe_questions: dict[str, list[dict]] | None = None,
) -> list[str]:
    message_ids = []
    probe_questions = probe_questions or {}
    for message in messages:
        message_ids.append(message["message_id"])
        scene_card = scene_cards.get(message["message_id"])
        followup_budget = (
            int(scene_card.get("expansion_controls", {}).get("followup_budget", 0))
            if scene_card
            else 0
        )
        requested_followups = min(max(scene_followups, 0), followup_budget)
        for followup_index in range(1, requested_followups + 1):
            message_ids.append(f"{message['message_id']}_F{followup_index:03d}")
        for probe_question in probe_questions.get(message["message_id"], []):
            message_ids.append(probe_question["message_id"])
    return message_ids


def _load_resume_result(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"--resume was set but output file does not exist: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or not isinstance(result.get("turns"), list):
        raise ValueError(f"Cannot resume from invalid probe output: {path}")
    return result


def _build_probe_result(
    *,
    existing_result: dict | None,
    run_id: str,
    created_at: str,
    message_ids: list[str],
    b_agent_id: str,
    letta_config,
    llm_config,
    max_tokens: int | None,
    timeout_seconds: float,
    m1_memory: str,
    scene_followups: int,
    probe_questions_path: Path | None,
    expected_turns: int,
) -> dict:
    if existing_result:
        if existing_result.get("message_ids") != message_ids:
            raise ValueError(
                "Cannot resume with different message_ids. "
                "Use a new --output path for a different run."
            )
        if existing_result.get("scene_followups") != scene_followups:
            raise ValueError(
                "Cannot resume with different --scene-followups. "
                "Use a new --output path for a different run."
            )
        existing_probe_path = existing_result.get("probe_questions_path")
        requested_probe_path = _display_path(probe_questions_path) if probe_questions_path else None
        if existing_probe_path != requested_probe_path:
            raise ValueError(
                "Cannot resume with different --probe-questions. "
                "Use a new --output path for a different run."
            )
        result = existing_result
    else:
        result = {
            "probe": (
                "m0_vs_m1_scene_chain"
                if scene_followups
                else "m0_vs_m1_single_turn"
            ),
            "run_id": run_id,
            "created_at": created_at,
            "message_ids": message_ids,
            "b_agent_id": b_agent_id,
            "b_agent_ids": [],
            "letta": {
                "base_url": letta_config.base_url,
                "model": letta_config.model,
                "embedding": letta_config.embedding,
                "m1_block_label": "m1_relationship",
                "m1_block_value": m1_memory,
            },
            "llm": {
                "provider": llm_config.provider,
                "base_url": llm_config.base_url,
                "model": llm_config.model,
                "max_tokens": max_tokens,
                "timeout_seconds": timeout_seconds,
            },
            "scene_followups": scene_followups,
            "probe_questions_path": (
                _display_path(probe_questions_path) if probe_questions_path else None
            ),
            "turns": [],
        }

    result["run_id"] = run_id
    result["created_at"] = created_at
    result["expected_turns"] = expected_turns
    result["resume_supported"] = True
    result["active_b_agent_id"] = b_agent_id
    result.setdefault("b_agent_ids", [])
    if b_agent_id not in result["b_agent_ids"]:
        result["b_agent_ids"].append(b_agent_id)
    return result


def _assert_completed_turns_are_expected_prefix(
    turns: list[dict],
    expected_message_ids: list[str],
) -> None:
    completed_message_ids = [turn["source"]["message_id"] for turn in turns]
    expected_prefix = expected_message_ids[: len(completed_message_ids)]
    if completed_message_ids != expected_prefix:
        raise ValueError(
            "Cannot resume because completed turns are not a prefix of the requested "
            f"plan. completed={completed_message_ids} expected_prefix={expected_prefix}"
        )


def _rebuild_runtime_state(
    turns: list[dict],
) -> tuple[dict[str, list[dict[str, str]]], list[str], dict[str, dict]]:
    short_term_histories: dict[str, list[dict[str, str]]] = {"M0": [], "M1": []}
    transcript_message_ids = []
    completed_turn_inputs = {}
    for expected_index, turn in enumerate(turns, start=1):
        if turn.get("turn_index") != expected_index:
            raise ValueError(
                "Cannot resume because turn_index values are not contiguous: "
                f"expected {expected_index}, got {turn.get('turn_index')}"
            )
        message_id = turn["source"]["message_id"]
        user_message = turn["input"]["user_message"]
        _append_short_term_history(
            short_term_histories["M0"],
            user_message,
            turn["variants"]["M0"]["assistant_answer"],
        )
        _append_short_term_history(
            short_term_histories["M1"],
            user_message,
            turn["variants"]["M1"]["assistant_answer"],
        )
        transcript_message_ids.append(message_id)
        completed_turn_inputs[message_id] = turn["input"]
    return short_term_histories, transcript_message_ids, completed_turn_inputs


def _write_checkpoint(
    *,
    output_path: Path,
    conversation_log_path: Path,
    result: dict,
    reset_conversation_log: bool,
    status: str,
) -> None:
    result["checkpoint"] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "completed_turns": len(result["turns"]),
        "expected_turns": result.get("expected_turns"),
        "last_message_id": (
            result["turns"][-1]["source"]["message_id"] if result["turns"] else None
        ),
    }
    _atomic_write_json(output_path, result)
    _sync_conversation_log(
        path=conversation_log_path,
        run_id=result["run_id"],
        turns=result["turns"],
        reset=reset_conversation_log,
    )


def _sync_conversation_log(
    *,
    path: Path,
    run_id: str,
    turns: list[dict],
    reset: bool,
) -> None:
    if path.exists() and not reset:
        log = json.loads(path.read_text(encoding="utf-8"))
    else:
        log = {
            "schema_version": "conversation_log_v0.1",
            "description": "Structured dialogue records for M0/M1/M2/M3/LN memory experiments.",
            "turns": [],
        }

    if log.get("schema_version") != "conversation_log_v0.1":
        raise ValueError(f"Unsupported conversation log schema: {log.get('schema_version')}")
    if not isinstance(log.get("turns"), list):
        raise ValueError("conversation log must contain a turns list")

    log["turns"] = [turn for turn in log["turns"] if turn.get("run_id") != run_id]
    log["turns"].extend(turns)
    _atomic_write_json(path, log)


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _find_message(messages: list[dict], message_id: str) -> dict:
    for message in messages:
        if message["message_id"] == message_id:
            return message
    raise ValueError(f"Message id not found: {message_id}")


def _load_scene_cards(path: Path) -> dict[str, dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    cards = doc.get("scene_cards")
    if not isinstance(cards, list):
        raise ValueError(f"daily scene cards file must contain scene_cards: {path}")
    result = {}
    for card in cards:
        opening_message_id = card.get("opening_message_id")
        if opening_message_id:
            result[opening_message_id] = card
    return result


def _load_probe_questions(path: Path) -> dict[str, list[dict]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    questions = doc.get("probe_questions")
    if not isinstance(questions, list):
        raise ValueError(f"probe question plan must contain probe_questions: {path}")
    result: dict[str, list[dict]] = {}
    for question in questions:
        insert_after = question.get("insert_after_message_id")
        message_id = question.get("message_id")
        if not insert_after or not message_id:
            raise ValueError("Every probe question must include insert_after_message_id and message_id")
        result.setdefault(insert_after, []).append(question)
    for items in result.values():
        items.sort(key=lambda item: item["message_id"])
    return result


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _default_max_tokens(provider: str, model: str) -> int | None:
    if provider == "deepseek" and model.startswith("deepseek-v4-"):
        return DEFAULT_DEEPSEEK_MAX_OUTPUT_TOKENS
    return None


def _generate_user_followup(
    *,
    client,
    model: str,
    scene_card: dict,
    opening_message: dict,
    followup_index: int,
    previous_user_messages: list[str],
    timeout: float,
    max_tokens: int | None,
) -> dict:
    reveal_schedule = scene_card.get("expansion_controls", {}).get("reveal_schedule", [])
    reveal_step = next(
        (
            step
            for step in reveal_schedule
            if int(step.get("followup_index", -1)) == followup_index
        ),
        {},
    )
    prompt_payload = {
        "task": "Generate the next simulated user message inside this scripted scene.",
        "followup_index": followup_index,
        "opening_message_id": opening_message["message_id"],
        "previous_user_messages": previous_user_messages,
        "hard_factual_boundary": {
            "known_user_facts": [
                opening_message["user_message"],
                *previous_user_messages,
            ],
            "do_not_make_the_instability_more_specific": True,
            "forbidden_concrete_rumors_unless_explicitly_in_scene_card": [
                "换园长",
                "换承办方",
                "老师离职",
                "停课",
                "财务问题",
                "涨费",
                "关停时间",
                "具体政策原因",
            ],
            "if_detail_is_missing": (
                "Say the information is still vague, there is no formal notice, "
                "or the user does not yet know the concrete cause."
            ),
        },
        "scene_card": scene_card,
        "current_reveal_step": reveal_step,
        "assistant_response_policy": (
            "Do not extract new facts from assistant answers. "
            "The next user message may continue the topic, ask for concreteness, "
            "or reveal one allowed concern, but all facts must come from "
            "previous_user_messages or scene_card."
        ),
        "output_schema": {
            "user_message": (
                "中文自然聊天消息，不要解释剧本，不要说自己是模拟用户。"
            ),
            "move_id": "one allowed move_id from current_reveal_step.preferred_moves",
            "used_fact_ids": ["fact ids used"],
            "used_concern_ids": ["concern ids used"],
            "reason": "short internal reason in Chinese",
        },
    }
    system = "\n".join(
        [
            "你是 A 侧的模拟用户生成器，不是对话助手。",
            "你要生成下一条用户发言，"
            "用于同一个聊天窗口里继续聊当天话题。",
            "必须严格停留在 scene_card 允许的事实、隐含担心和 "
            "reveal_step 范围内。",
            "这条用户发言要能同时适配 M0 和 M1 两个 assistant 回复，"
            "不能引用某一边独有的具体措辞。",
            "assistant 回复里的例子、假设和建议不是用户事实，"
            "不能转写成用户新增背景。",
            "如果 scene_card 没有明确写不稳定的具体原因，"
            "用户只能说消息还很模糊，"
            "不能说换园长、换承办方、老师离职等。",
            "不要新增人物、地点、诊断、金额、日期或剧本外重大事件。",
            "只输出一个 JSON object，不要 Markdown，不要额外说明。",
        ]
    )
    request_client = client.with_options(max_retries=0, timeout=timeout)
    completion = request_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
        ],
        max_tokens=max_tokens,
    )
    raw_output = completion.choices[0].message.content or ""
    parsed = _parse_json_object(raw_output)
    user_message = str(parsed.get("user_message") or raw_output).strip()
    return {
        "generator": "llm_user_actor_scene_followup",
        "followup_index": followup_index,
        "raw_model_output": raw_output,
        "user_message": user_message,
        "move_id": parsed.get("move_id"),
        "used_fact_ids": parsed.get("used_fact_ids", []),
        "used_concern_ids": parsed.get("used_concern_ids", []),
        "reason": parsed.get("reason"),
        "reveal_step": reveal_step,
    }


def _parse_json_object(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


def _build_followup_message(
    *,
    opening_message: dict,
    scene_card: dict,
    followup_index: int,
    followup: dict,
) -> dict:
    return {
        "message_id": f"{opening_message['message_id']}_F{followup_index:03d}",
        "day": opening_message["day"],
        "user_message": followup["user_message"],
        "event_refs": list(opening_message.get("event_refs", [])),
        "primary_event_id": opening_message["primary_event_id"],
        "related_event_id": opening_message.get("related_event_id"),
        "domains": list(opening_message.get("domains", [])),
        "topic": opening_message["topic"],
        "script_stage": opening_message["script_stage"],
        "intent": opening_message["intent"],
        "tone": opening_message["tone"],
        "conversation_goal": opening_message["conversation_goal"],
        "memory_relevance": opening_message["memory_relevance"],
        "turn_type": "llm_user_followup",
        "scene_id": scene_card.get("scene_id"),
        "followup_index": followup_index,
        "user_followup_generation": followup,
    }


def _run_variant_turn(
    *,
    run_id: str,
    created_at: str,
    turn_index: int,
    daily_messages_path: Path,
    scene_cards_path: Path | None,
    message: dict,
    scene_card: dict | None,
    b_agent_id: str,
    letta_config,
    llm_client,
    llm_config,
    max_tokens: int | None,
    timeout_seconds: float,
    m1_memory: str,
    short_term_histories: dict[str, list[dict[str, str]]],
    previous_message_ids: list[str],
) -> dict:
    user_message = message["user_message"]
    m0_history_before = list(short_term_histories["M0"])
    m1_history_before = list(short_term_histories["M1"])
    m0_answer = _ask_a(
        client=llm_client,
        model=llm_config.model,
        memory_level="M0",
        user_message=user_message,
        memory_context=None,
        short_term_history=m0_history_before,
        timeout=timeout_seconds,
        max_tokens=max_tokens,
    )
    m1_answer = _ask_a(
        client=llm_client,
        model=llm_config.model,
        memory_level="M1",
        user_message=user_message,
        memory_context=m1_memory,
        short_term_history=m1_history_before,
        timeout=timeout_seconds,
        max_tokens=max_tokens,
    )
    turn = _build_conversation_turn(
        run_id=run_id,
        created_at=created_at,
        turn_index=turn_index,
        daily_messages_path=daily_messages_path,
        scene_cards_path=scene_cards_path,
        message=message,
        scene_card=scene_card,
        b_agent_id=b_agent_id,
        letta_config=letta_config,
        llm_config=llm_config,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
        m1_memory=m1_memory,
        m0_history_before=m0_history_before,
        m1_history_before=m1_history_before,
        previous_message_ids=previous_message_ids,
        m0_answer=m0_answer,
        m1_answer=m1_answer,
    )
    _append_short_term_history(short_term_histories["M0"], user_message, m0_answer)
    _append_short_term_history(short_term_histories["M1"], user_message, m1_answer)
    return turn


def _build_conversation_turn(
    *,
    run_id: str,
    created_at: str,
    turn_index: int,
    daily_messages_path: Path,
    scene_cards_path: Path | None,
    message: dict,
    scene_card: dict | None,
    b_agent_id: str,
    letta_config,
    llm_config,
    max_tokens: int | None,
    timeout_seconds: float,
    m1_memory: str,
    m0_history_before: list[dict[str, str]],
    m1_history_before: list[dict[str, str]],
    previous_message_ids: list[str],
    m0_answer: str,
    m1_answer: str,
) -> dict:
    return {
        "run_id": run_id,
        "created_at": created_at,
        "turn_index": turn_index,
        "probe": "m0_vs_m1_chain",
        "conversation_context_policy": {
            "M0": "same_session_short_term_context_plus_current_user_message_no_long_term_memory",
            "M1": (
                "same_session_short_term_context_plus_current_user_message"
                "_plus_m1_relationship_block"
            ),
        },
        "source": {
            "daily_messages_path": _display_path(daily_messages_path),
            "scene_cards_path": _display_path(scene_cards_path) if scene_cards_path else None,
            "message_id": message["message_id"],
            "scene_id": scene_card.get("scene_id") if scene_card else None,
            "turn_type": message.get("turn_type", "scripted_opening"),
        },
        "input": message,
        "b_agent": {
            "agent_id": b_agent_id,
            "letta_base_url": letta_config.base_url,
            "letta_model": letta_config.model,
            "letta_embedding": letta_config.embedding,
        },
        "llm": {
            "provider": llm_config.provider,
            "base_url": llm_config.base_url,
            "model": llm_config.model,
            "max_tokens": max_tokens,
            "timeout_seconds": timeout_seconds,
        },
        "evaluation_targets": _build_evaluation_targets(scene_card, message),
        "memory_setup": [
            {
                "memory_level": "M1",
                "action": "seed_block",
                "block_label": "m1_relationship",
                "content": m1_memory,
                "reason": "Controlled M0/M1 probe seed memory.",
            }
        ],
        "variants": {
            "M0": {
                "memory_available": False,
                "memory_context": None,
                "short_term_context": {
                    "enabled": True,
                    "previous_turn_count": len(m0_history_before) // 2,
                    "previous_message_ids": previous_message_ids,
                },
                "assistant_answer": m0_answer,
            },
            "M1": {
                "memory_available": True,
                "memory_context": {
                    "block_label": "m1_relationship",
                    "content": m1_memory,
                },
                "short_term_context": {
                    "enabled": True,
                    "previous_turn_count": len(m1_history_before) // 2,
                    "previous_message_ids": previous_message_ids,
                },
                "assistant_answer": m1_answer,
            },
        },
        "memory_actions": [],
    }


def _build_evaluation_targets(scene_card: dict | None, message: dict | None = None) -> dict:
    if message and message.get("tom_assessment"):
        tom_assessment = dict(message.get("tom_assessment", {}))
        return {
            "tom_quality": {
                "source": "probe_question_plan.tom_assessment",
                "dimensions": list(message.get("tom_dimensions", [])),
                "surface_question": tom_assessment.get("surface_question"),
                "hidden_user_need": tom_assessment.get("hidden_user_need"),
                "low_score_behavior": tom_assessment.get("low_score_behavior"),
                "high_score_behavior": tom_assessment.get("high_score_behavior"),
                "status": "not_evaluated",
            }
        }
    return {}


def _append_short_term_history(
    history: list[dict[str, str]], user_message: str, answer: str
) -> None:
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": answer})


def _ask_a(
    client,
    model: str,
    memory_level: str,
    user_message: str,
    memory_context: str | None,
    short_term_history: list[dict[str, str]],
    timeout: float,
    max_tokens: int | None,
) -> str:
    system_parts = [
        "你是 A，一个拟人、自然、长期陪伴型对话 Agent。",
        "你要像一个稳定的长期朋友一样回应，"
        "但不能编造自己没有被提供的历史记忆。",
        "回答要中文、自然、具体，不要写成报告。",
        "不要把未提供的信息当作用户事实；"
        "如需举例，必须明确说这是条件假设。",
        "优先给 1-3 个实在下一步，适合手机聊天，不要堆太长清单。",
    ]
    if memory_level == "M0":
        system_parts.append(
            "当前记忆层级是 M0：你可以使用同一聊天窗口内的短期上下文，"
            "但没有任何长期关系记忆，不能声称知道窗口外的历史。"
        )
    else:
        system_parts.append(
            "当前记忆层级是 M1：你可以使用同一聊天窗口内的短期上下文，"
            "并且只能额外使用结论级关系记忆，"
            "不能声称知道未提供的具体历史事件。"
        )
        system_parts.append(f"M1 关系记忆：{memory_context}")

    messages = [
        {"role": "system", "content": "\n".join(system_parts)},
        *short_term_history,
        {"role": "user", "content": user_message},
    ]
    request_client = client.with_options(max_retries=0, timeout=timeout)
    completion = request_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content or ""


if __name__ == "__main__":
    raise SystemExit(main())
