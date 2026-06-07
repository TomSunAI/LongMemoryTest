#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.llm import create_llm_client  # noqa: E402
from long_memory_test.memory import LDAgentMemoryRuntime  # noqa: E402
from long_memory_test.experiment_cache import (  # noqa: E402
    CACHE_MEMORY_CONDITIONS_PATH,
    DAILY_SCENE_CARDS_PATH,
    DAILY_USER_MESSAGE_PATH,
    OUTPUTS_DIR,
    PROBE_QUESTION_PLAN_PATH,
)


LEGACY_PATH = REPO_ROOT / "scripts/run_m0_m1_dialogue_probe.py"
LEGACY_SPEC = importlib.util.spec_from_file_location("_m0_m1_legacy_helpers", LEGACY_PATH)
assert LEGACY_SPEC is not None and LEGACY_SPEC.loader is not None
legacy = importlib.util.module_from_spec(LEGACY_SPEC)
LEGACY_SPEC.loader.exec_module(legacy)


DEFAULT_CONDITION_IDS = ["M0", "M1", "M2", "M3"]
MIN_ASSISTANT_ANSWER_CHARS = 20
ASSISTANT_ANSWER_MAX_ATTEMPTS = 4
SHORT_TERM_CONTEXT_MODE = "shared_user_turns_only"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run docx-route dialogue turns under M0/M1/M2/M3 memory conditions."
    )
    parser.add_argument(
        "--daily-messages",
        type=Path,
        default=DAILY_USER_MESSAGE_PATH,
        help="Path to daily_user_message.json.",
    )
    parser.add_argument(
        "--scene-cards",
        type=Path,
        default=DAILY_SCENE_CARDS_PATH,
        help="Path to daily_scene_cards.json.",
    )
    parser.add_argument(
        "--probe-questions",
        type=Path,
        default=PROBE_QUESTION_PLAN_PATH,
        help="Optional path to probe_question_plan.json.",
    )
    parser.add_argument(
        "--no-probe-questions",
        action="store_true",
        help="Disable targeted probe insertion even if the default probe file exists.",
    )
    parser.add_argument(
        "--memory-conditions",
        type=Path,
        default=CACHE_MEMORY_CONDITIONS_PATH,
        help="Path to memory_conditions.json.",
    )
    parser.add_argument("--message-id", default="D01_M001")
    parser.add_argument("--message-ids", default=None)
    parser.add_argument("--all-message-ids", action="store_true")
    parser.add_argument(
        "--conditions",
        default="M0,M1,M2,M3",
        help="Comma-separated condition ids to run.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Output run directory. Defaults to long_memory_experiment/outputs/run_YYYYMMDD_HHMM.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for responses_by_condition.json.",
    )
    parser.add_argument(
        "--conversation-log",
        type=Path,
        default=None,
        help="Output path for conversation_log.json.",
    )
    parser.add_argument("--reset-conversation-log", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--scene-followups", type=int, default=0)
    parser.add_argument("--llm-timeout", type=float, default=600.0)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument(
        "--condition-workers",
        type=int,
        default=1,
        help="Number of parallel condition answer generations per user turn.",
    )
    parser.add_argument("--m0-ld-agent-top-k", type=int, default=5)
    parser.add_argument("--m0-ld-agent-short-term-k", type=int, default=5)
    parser.add_argument(
        "--m0-ld-agent-storage-backend",
        choices=["json", "chroma"],
        default="json",
        help="Storage backend for M0 LD-Agent memory runtime.",
    )
    parser.add_argument(
        "--m0-ld-agent-chroma-path",
        type=Path,
        default=None,
        help="Persistent ChromaDB directory when --m0-ld-agent-storage-backend=chroma.",
    )
    parser.add_argument("--print-progress", action="store_true")
    parser.add_argument("--print-mode", choices=["summary", "all"], default="summary")
    args = parser.parse_args()
    if args.no_probe_questions:
        args.probe_questions = None
    if args.output is None or args.conversation_log is None:
        run_dir = args.run_dir or _default_run_dir()
        if args.output is None:
            args.output = run_dir / "responses_by_condition.json"
        if args.conversation_log is None:
            args.conversation_log = run_dir / "conversation_log.json"
    return args


def main() -> int:
    args = parse_args()
    messages_doc = _load_json(args.daily_messages)
    message_ids = legacy._resolve_message_ids(args, messages_doc["messages"])
    messages = [
        legacy._find_message(messages_doc["messages"], message_id)
        for message_id in message_ids
    ]
    scene_cards = (
        legacy._load_scene_cards(args.scene_cards)
        if args.scene_followups > 0 or args.probe_questions
        else {}
    )
    probe_questions = (
        legacy._load_probe_questions(args.probe_questions)
        if args.probe_questions
        else {}
    )
    memory_conditions = _load_memory_conditions(args.memory_conditions)
    condition_ids = _resolve_condition_ids(args.conditions, memory_conditions)
    existing_result = legacy._load_resume_result(args.output) if args.resume else None

    llm_client, llm_config = create_llm_client()
    max_tokens = args.max_tokens or legacy._default_max_tokens(
        llm_config.provider,
        llm_config.model,
    )
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M%S")
    created_at = (
        existing_result.get("created_at")
        if existing_result
        else now.isoformat().replace("+00:00", "Z")
    ) or now.isoformat().replace("+00:00", "Z")
    run_id = existing_result.get("run_id") if existing_result else f"docx_conditions_{timestamp}"
    expected_turns = legacy._expected_turn_count(
        messages, scene_cards, args.scene_followups, probe_questions
    )
    result = _build_result(
        existing_result=existing_result,
        run_id=run_id,
        created_at=created_at,
        message_ids=message_ids,
        condition_ids=condition_ids,
        llm_config=llm_config,
        max_tokens=max_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        timeout_seconds=args.llm_timeout,
        scene_followups=args.scene_followups,
        probe_questions_path=args.probe_questions,
        memory_conditions_path=args.memory_conditions,
        expected_turns=expected_turns,
    )
    if existing_result and existing_result.get("m0_ld_agent_memory"):
        m0_memory_runtime = LDAgentMemoryRuntime.from_snapshot(
            existing_result.get("m0_ld_agent_memory"),
            top_k=args.m0_ld_agent_top_k,
            short_term_k=args.m0_ld_agent_short_term_k,
            llm_client=llm_client,
            llm_model=llm_config.model,
            llm_timeout=args.llm_timeout,
            storage_backend=args.m0_ld_agent_storage_backend,
            chroma_path=args.m0_ld_agent_chroma_path,
        )
    else:
        m0_memory_runtime = LDAgentMemoryRuntime.from_completed_turns(
            result["turns"],
            top_k=args.m0_ld_agent_top_k,
            short_term_k=args.m0_ld_agent_short_term_k,
            llm_client=llm_client,
            llm_model=llm_config.model,
            llm_timeout=args.llm_timeout,
            storage_backend=args.m0_ld_agent_storage_backend,
            chroma_path=args.m0_ld_agent_chroma_path,
        )
    result["m0_ld_agent_memory"] = m0_memory_runtime.snapshot()
    _write_run_config(
        args.output.parent / "run_config.json",
        result=result,
        args=args,
        llm_config=llm_config,
        max_tokens=max_tokens,
        condition_ids=condition_ids,
    )

    expected_message_ids = legacy._expected_message_id_sequence(
        messages=messages,
        scene_cards=scene_cards,
        scene_followups=args.scene_followups,
        probe_questions=probe_questions,
    )
    legacy._assert_completed_turns_are_expected_prefix(
        result["turns"],
        expected_message_ids,
    )
    short_term_histories, transcript_message_ids, completed_turn_inputs = (
        _rebuild_runtime_state(
            result["turns"],
            condition_ids=condition_ids,
        )
    )
    completed_message_ids = set(transcript_message_ids)
    turn_index = len(result["turns"])
    _write_condition_checkpoint(
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
                _print_progress(args, turn_index, expected_turns, current_input)
                turn = _run_condition_turn(
                    run_id=run_id,
                    created_at=created_at,
                    turn_index=turn_index,
                    daily_messages_path=args.daily_messages,
                    scene_cards_path=args.scene_cards if scene_card else None,
                    memory_conditions_path=args.memory_conditions,
                    message=current_input,
                    scene_card=scene_card,
                    llm_client=llm_client,
                    llm_config=llm_config,
                    max_tokens=max_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    timeout_seconds=args.llm_timeout,
                    condition_workers=args.condition_workers,
                    print_condition_progress=args.print_progress,
                    memory_conditions=memory_conditions,
                    m0_memory_runtime=m0_memory_runtime,
                    condition_ids=condition_ids,
                    short_term_histories=short_term_histories,
                    previous_message_ids=list(transcript_message_ids),
                )
                result["turns"].append(turn)
                result["m0_ld_agent_memory"] = m0_memory_runtime.snapshot()
                transcript_message_ids.append(current_message_id)
                completed_message_ids.add(current_message_id)
                completed_turn_inputs[current_message_id] = current_input
                _write_condition_checkpoint(
                    output_path=args.output,
                    conversation_log_path=args.conversation_log,
                    result=result,
                    reset_conversation_log=args.reset_conversation_log,
                    status="running",
                )

            if followup_index == requested_followups or not scene_card:
                break
            next_followup_index = followup_index + 1
            next_message_id = f"{message['message_id']}_F{next_followup_index:03d}"
            if next_message_id in completed_turn_inputs:
                current_input = completed_turn_inputs[next_message_id]
            else:
                followup = legacy._generate_user_followup(
                    client=llm_client,
                    model=llm_config.model,
                    scene_card=scene_card,
                    opening_message=message,
                    followup_index=next_followup_index,
                    previous_user_messages=[item["user_message"] for item in user_inputs],
                    timeout=args.llm_timeout,
                    max_tokens=max_tokens,
                )
                current_input = legacy._build_followup_message(
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
            _print_progress(args, turn_index, expected_turns, probe_question)
            turn = _run_condition_turn(
                run_id=run_id,
                created_at=created_at,
                turn_index=turn_index,
                daily_messages_path=args.daily_messages,
                scene_cards_path=args.scene_cards if scene_card else None,
                memory_conditions_path=args.memory_conditions,
                message=probe_question,
                scene_card=scene_card,
                llm_client=llm_client,
                llm_config=llm_config,
                max_tokens=max_tokens,
                temperature=args.temperature,
                top_p=args.top_p,
                timeout_seconds=args.llm_timeout,
                condition_workers=args.condition_workers,
                print_condition_progress=args.print_progress,
                memory_conditions=memory_conditions,
                m0_memory_runtime=m0_memory_runtime,
                condition_ids=condition_ids,
                short_term_histories=short_term_histories,
                previous_message_ids=list(transcript_message_ids),
            )
            result["turns"].append(turn)
            result["m0_ld_agent_memory"] = m0_memory_runtime.snapshot()
            transcript_message_ids.append(current_message_id)
            completed_message_ids.add(current_message_id)
            completed_turn_inputs[current_message_id] = probe_question
            _write_condition_checkpoint(
                output_path=args.output,
                conversation_log_path=args.conversation_log,
                result=result,
                reset_conversation_log=args.reset_conversation_log,
                status="running",
            )

    m0_memory_runtime.flush_current_session(reason="run_complete")
    result["m0_ld_agent_memory"] = m0_memory_runtime.snapshot()
    _write_condition_checkpoint(
        output_path=args.output,
        conversation_log_path=args.conversation_log,
        result=result,
        reset_conversation_log=args.reset_conversation_log,
        status="complete",
    )
    _print_result(args.print_mode, result["turns"], condition_ids)
    print(f"\nWrote {args.output}")
    print(f"Synced {args.conversation_log}")
    return 0


def _run_condition_turn(
    *,
    run_id: str,
    created_at: str,
    turn_index: int,
    daily_messages_path: Path,
    scene_cards_path: Path | None,
    memory_conditions_path: Path,
    message: dict[str, Any],
    scene_card: dict[str, Any] | None,
    llm_client: Any,
    llm_config: Any,
    max_tokens: int | None,
    temperature: float,
    top_p: float | None,
    timeout_seconds: float,
    condition_workers: int,
    print_condition_progress: bool,
    memory_conditions: dict[str, Any],
    m0_memory_runtime: LDAgentMemoryRuntime,
    condition_ids: list[str],
    short_term_histories: dict[str, list[dict[str, str]]],
    previous_message_ids: list[str],
) -> dict[str, Any]:
    user_message = str(message["user_message"])
    variants = {}
    history_before_by_condition = {
        condition_id: list(short_term_histories[condition_id])
        for condition_id in condition_ids
    }
    memory_action_start = len(m0_memory_runtime.actions)
    m0_ld_agent_payload = m0_memory_runtime.retrieve_payload(message)
    max_workers = max(1, min(int(condition_workers), len(condition_ids)))

    def run_one_condition(condition_id: str) -> tuple[str, dict[str, Any]]:
        payload = _payload_for_condition(
            memory_conditions,
            condition_id,
            message,
            m0_ld_agent_payload=m0_ld_agent_payload,
        )
        if print_condition_progress:
            print(
                "[progress] "
                f"turn {turn_index} message_id={message['message_id']} "
                f"condition={condition_id} start",
                flush=True,
            )
        answer = _ask_a_condition(
            client=llm_client,
            model=llm_config.model,
            condition_id=condition_id,
            condition_spec=_condition_spec(memory_conditions, condition_id),
            user_message=user_message,
            memory_payload=payload,
            short_term_history=history_before_by_condition[condition_id],
            timeout=timeout_seconds,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        if print_condition_progress:
            print(
                "[progress] "
                f"turn {turn_index} message_id={message['message_id']} "
                f"condition={condition_id} complete",
                flush=True,
            )
        return condition_id, {
            "memory_condition": condition_id,
            "memory_available": True,
            "memory_context": payload,
            "memory_payload": payload,
            "short_term_context": {
                "enabled": True,
                "mode": SHORT_TERM_CONTEXT_MODE,
                "previous_turn_count": _count_user_turns(
                    history_before_by_condition[condition_id]
                ),
                "previous_message_ids": previous_message_ids,
                "context_token_count": _estimate_context_tokens(
                    history_before_by_condition[condition_id]
                ),
                "context_message_count": len(history_before_by_condition[condition_id]),
            },
            "assistant_answer": answer,
        }
    if max_workers == 1:
        for condition_id in condition_ids:
            completed_condition_id, variant = run_one_condition(condition_id)
            variants[completed_condition_id] = variant
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_one_condition, condition_id): condition_id
                for condition_id in condition_ids
            }
            for future in as_completed(futures):
                completed_condition_id, variant = future.result()
                variants[completed_condition_id] = variant
    variants = {condition_id: variants[condition_id] for condition_id in condition_ids}
    m0_answer = str(variants.get("M0", {}).get("assistant_answer", ""))
    m0_record_action = m0_memory_runtime.record_completed_turn(
        message=message,
        assistant_answer=m0_answer,
        run_id=run_id,
    )
    if "M0" in variants:
        variants["M0"]["memory_writeback"] = m0_record_action
    memory_actions = list(m0_memory_runtime.actions[memory_action_start:])
    for condition_id in condition_ids:
        _append_short_term_user_turn(short_term_histories[condition_id], user_message)

    return {
        "run_id": run_id,
        "created_at": created_at,
        "turn_index": turn_index,
        "probe": "docx_m0_m1_m2_m3_memory_conditions",
        "conversation_context_policy": _context_policy(memory_conditions, condition_ids),
        "source": {
            "daily_messages_path": legacy._display_path(daily_messages_path),
            "scene_cards_path": (
                legacy._display_path(scene_cards_path) if scene_cards_path else None
            ),
            "memory_conditions_path": legacy._display_path(memory_conditions_path),
            "message_id": message["message_id"],
            "scene_id": scene_card.get("scene_id") if scene_card else None,
            "turn_type": message.get("turn_type", "scripted_opening"),
        },
        "input": {
            **message,
            "input_hash": _sha256_text(user_message),
        },
        "llm": {
            "provider": llm_config.provider,
            "base_url": llm_config.base_url,
            "model": llm_config.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "timeout_seconds": timeout_seconds,
        },
        "evaluation_targets": legacy._build_evaluation_targets(scene_card, message),
        "memory_setup": {
            "route": "docx",
            "conditions": condition_ids,
            "memory_payload_source": legacy._display_path(memory_conditions_path),
            "m0_memory_provider": "ld_agent_memory",
            "m0_ld_agent_reference": m0_ld_agent_payload.get("ld_agent_reference"),
            "m1_m2_m3_share_m0_base_memory": True,
            "short_term_context_mode": SHORT_TERM_CONTEXT_MODE,
        },
        "variants": variants,
        "memory_actions": memory_actions,
    }


def _ask_a_condition(
    *,
    client: Any,
    model: str,
    condition_id: str,
    condition_spec: dict[str, Any],
    user_message: str,
    memory_payload: dict[str, Any],
    short_term_history: list[dict[str, str]],
    timeout: float,
    max_tokens: int | None,
    temperature: float,
    top_p: float | None = None,
) -> str:
    messages = [
        {
            "role": "system",
            "content": _build_condition_system_prompt(
                condition_id=condition_id,
                condition_spec=condition_spec,
                memory_payload=memory_payload,
            ),
        },
        *short_term_history,
        {"role": "user", "content": user_message},
    ]
    request_client = client.with_options(max_retries=0, timeout=timeout)
    request_kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if top_p is not None:
        request_kwargs["top_p"] = top_p
    last_content = ""
    for attempt in range(ASSISTANT_ANSWER_MAX_ATTEMPTS):
        completion = request_client.chat.completions.create(**request_kwargs)
        last_content = completion.choices[0].message.content or ""
        if len(last_content.strip()) >= MIN_ASSISTANT_ANSWER_CHARS:
            return last_content
        if attempt < ASSISTANT_ANSWER_MAX_ATTEMPTS - 1:
            time.sleep(min(2.0, 0.5 * (attempt + 1)))
    raise RuntimeError(
        "LLM returned an empty or degenerate assistant answer repeatedly "
        f"for condition {condition_id}. Last answer: {last_content!r}"
    )


def _build_condition_system_prompt(
    *,
    condition_id: str,
    condition_spec: dict[str, Any],
    memory_payload: dict[str, Any],
) -> str:
    common = [
        "你是 A，一个拟人、自然、长期陪伴型对话 Agent。",
        "你要回应当前用户输入，不要暴露实验设置。",
        "不要编造用户没有说过或没有在可用记忆中提供的事实。",
        "不要为了显得熟悉而机械背诵历史。",
        "如果历史记忆不足以确定，就明确区分已知和推测。",
        "回答要中文、自然、具体，优先给 1-3 个实在下一步，"
        "不要写成报告。",
    ]
    condition_lines = [
        "本轮你只能使用下面这段可用长期记忆载荷；不要猜测或使用未列出的历史：",
        str(memory_payload.get("memory_context", "")),
        "如果这段记忆不足以确定，就说明哪些是已知、哪些只是推测。",
    ]
    return "\n".join(common + condition_lines)


def _build_result(
    *,
    existing_result: dict[str, Any] | None,
    run_id: str,
    created_at: str,
    message_ids: list[str],
    condition_ids: list[str],
    llm_config: Any,
    max_tokens: int | None,
    temperature: float,
    top_p: float | None,
    timeout_seconds: float,
    scene_followups: int,
    probe_questions_path: Path | None,
    memory_conditions_path: Path,
    expected_turns: int,
) -> dict[str, Any]:
    requested_probe_path = (
        legacy._display_path(probe_questions_path) if probe_questions_path else None
    )
    requested_memory_path = legacy._display_path(memory_conditions_path)
    if existing_result:
        if existing_result.get("message_ids") != message_ids:
            raise ValueError("Cannot resume with different message_ids.")
        if existing_result.get("condition_ids") != condition_ids:
            raise ValueError("Cannot resume with different --conditions.")
        if existing_result.get("scene_followups") != scene_followups:
            raise ValueError("Cannot resume with different --scene-followups.")
        if existing_result.get("probe_questions_path") != requested_probe_path:
            raise ValueError("Cannot resume with different --probe-questions.")
        if existing_result.get("memory_conditions_path") != requested_memory_path:
            raise ValueError("Cannot resume with different --memory-conditions.")
        existing_top_p = existing_result.get("llm", {}).get("top_p")
        if existing_top_p is not None and existing_top_p != top_p:
            raise ValueError("Cannot resume with different --top-p.")
        result = existing_result
    else:
        result = {
            "probe": "docx_m0_m1_m2_m3_memory_conditions",
            "route": "docx",
            "run_id": run_id,
            "created_at": created_at,
            "message_ids": message_ids,
            "condition_ids": condition_ids,
            "llm": {
                "provider": llm_config.provider,
                "base_url": llm_config.base_url,
                "model": llm_config.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "timeout_seconds": timeout_seconds,
            },
            "scene_followups": scene_followups,
            "probe_questions_path": requested_probe_path,
            "memory_conditions_path": requested_memory_path,
            "turns": [],
        }
    result["run_id"] = run_id
    result["created_at"] = created_at
    result["expected_turns"] = expected_turns
    result["resume_supported"] = True
    _refresh_result_progress(result)
    return result


def _write_condition_checkpoint(
    *,
    output_path: Path,
    conversation_log_path: Path,
    result: dict[str, Any],
    reset_conversation_log: bool,
    status: str,
) -> None:
    _refresh_result_progress(result)
    legacy._write_checkpoint(
        output_path=output_path,
        conversation_log_path=conversation_log_path,
        result=result,
        reset_conversation_log=reset_conversation_log,
        status=status,
    )


def _refresh_result_progress(result: dict[str, Any]) -> None:
    completed_message_ids = [
        str(turn.get("source", {}).get("message_id", ""))
        for turn in result.get("turns", [])
        if turn.get("source", {}).get("message_id")
    ]
    result["completed_message_ids"] = completed_message_ids
    result["completed_input_hashes_by_message_id"] = {
        str(turn.get("source", {}).get("message_id", "")): str(
            turn.get("input", {}).get("input_hash", "")
        )
        for turn in result.get("turns", [])
        if turn.get("source", {}).get("message_id")
    }
    result["completed_conditions_by_message_id"] = {
        str(turn.get("source", {}).get("message_id", "")): sorted(
            str(condition_id) for condition_id in (turn.get("variants") or {})
        )
        for turn in result.get("turns", [])
        if turn.get("source", {}).get("message_id")
    }


def _write_run_config(
    path: Path,
    *,
    result: dict[str, Any],
    args: argparse.Namespace,
    llm_config: Any,
    max_tokens: int | None,
    condition_ids: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": "run_config_v1",
        "run_id": result["run_id"],
        "created_at": result["created_at"],
        "route": "event_first_bei_calibrated_m0_m1_m2_m3",
        "controlled_variables": {
            "same_user_input_for_all_conditions": True,
            "same_model_for_all_conditions": True,
            "same_short_term_context_policy": True,
            "short_term_context_mode": SHORT_TERM_CONTEXT_MODE,
            "only_long_term_memory_condition_changes": True,
            "same_condition_parallelism_for_all_conditions": True,
            "m1_m2_m3_share_m0_base_memory": True,
            "evaluation_metadata_visible_to_model": False,
            "bei_gold_failure_modes_visible_to_model": False,
        },
        "model": {
            "provider": llm_config.provider,
            "base_url": llm_config.base_url,
            "model": llm_config.model,
            "temperature": args.temperature,
            "top_p": args.top_p,
            "max_tokens": max_tokens,
            "timeout_seconds": args.llm_timeout,
            "condition_workers": args.condition_workers,
        },
        "inputs": {
            "daily_messages": legacy._display_path(args.daily_messages),
            "scene_cards": legacy._display_path(args.scene_cards),
            "probe_questions": (
                legacy._display_path(args.probe_questions) if args.probe_questions else None
            ),
            "memory_conditions": legacy._display_path(args.memory_conditions),
        },
        "conditions": condition_ids,
        "m0_ld_agent_memory_baseline": {
            "provider": "ld_agent_memory",
            "ld_agent_reference": result.get("m0_ld_agent_memory", {}).get(
                "ld_agent_reference"
            ),
            "top_k": args.m0_ld_agent_top_k,
            "short_term_k": args.m0_ld_agent_short_term_k,
            "storage_backend": args.m0_ld_agent_storage_backend,
            "chroma_path": (
                legacy._display_path(args.m0_ld_agent_chroma_path)
                if args.m0_ld_agent_chroma_path
                else None
            ),
            "uses_ld_agent_generator": False,
            "uses_ld_agent_checkpoint": False,
            "uses_letta": False,
            "writeback_method": "ld_agent_session_summary_and_personas_traits",
            "long_term_memory_bank": [
                "generic_event_memories",
                "generic_persona_memories",
            ],
            "retrieval": {
                "strategy": "ld_agent_relevance_overlap_time_decay",
                "top_k": args.m0_ld_agent_top_k,
            },
            "used_by_conditions": [
                condition_id
                for condition_id in condition_ids
                if condition_id in {"M0", "M1", "M2", "M3"}
            ],
        },
        "scene_followups": args.scene_followups,
        "expected_turns": result["expected_turns"],
        "outputs": {
            "responses_by_condition": legacy._display_path(args.output),
            "conversation_log": legacy._display_path(args.conversation_log),
            "run_config": legacy._display_path(path),
        },
        "checkpoint_policy": {
            "resume_supported": True,
            "completed_message_ids_are_persisted": True,
            "duplicate_message_ids_are_skipped": True,
            "input_hash_recorded_per_turn": True,
            "checkpoint_written_after_each_completed_turn": True,
            "m0_ld_agent_memory_snapshot_persisted": True,
        },
    }
    result["run_config"] = config
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rebuild_runtime_state(
    turns: list[dict[str, Any]],
    *,
    condition_ids: list[str],
) -> tuple[dict[str, list[dict[str, str]]], list[str], dict[str, dict[str, Any]]]:
    short_term_histories = {condition_id: [] for condition_id in condition_ids}
    transcript_message_ids: list[str] = []
    completed_turn_inputs: dict[str, dict[str, Any]] = {}
    for expected_index, turn in enumerate(turns, start=1):
        if turn.get("turn_index") != expected_index:
            raise ValueError(
                "Cannot resume because turn_index values are not contiguous: "
                f"expected {expected_index}, got {turn.get('turn_index')}"
            )
        message_id = turn["source"]["message_id"]
        user_message = turn["input"]["user_message"]
        variants = turn.get("variants", {})
        for condition_id in condition_ids:
            if condition_id not in variants:
                raise ValueError(
                    f"Cannot resume because turn {message_id} is missing {condition_id}"
                )
            _append_short_term_user_turn(short_term_histories[condition_id], user_message)
        transcript_message_ids.append(message_id)
        completed_turn_inputs[message_id] = turn["input"]
    return short_term_histories, transcript_message_ids, completed_turn_inputs


def _payload_for_condition(
    memory_conditions: dict[str, Any],
    condition_id: str,
    message: dict[str, Any],
    *,
    m0_ld_agent_payload: dict[str, Any],
) -> dict[str, Any]:
    if condition_id == "M0":
        return dict(m0_ld_agent_payload)

    payloads_by_message = memory_conditions.get("memory_payloads_by_message_id", {})
    message_id = str(message.get("message_id", ""))
    candidate_ids = [message_id]
    if "_F" in message_id:
        candidate_ids.append(message_id.split("_F", 1)[0])
    for candidate_id in candidate_ids:
        per_message = payloads_by_message.get(candidate_id)
        if isinstance(per_message, dict) and condition_id in per_message:
            payload = dict(per_message[condition_id])
            payload.setdefault("condition_id", condition_id)
            return _with_m0_base_memory(payload, m0_ld_agent_payload)
    default_payload = memory_conditions.get("default_payloads", {}).get(condition_id, {})
    payload = dict(default_payload)
    payload.setdefault("condition_id", condition_id)
    return _with_m0_base_memory(payload, m0_ld_agent_payload)


def _with_m0_base_memory(
    relational_payload: dict[str, Any],
    m0_ld_agent_payload: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(relational_payload)
    if payload.get("condition_id") not in {"M1", "M2", "M3"}:
        return payload
    relational_context = str(payload.get("memory_context", "")).strip()
    m0_context = str(m0_ld_agent_payload.get("memory_context", "")).strip()
    if not m0_context:
        raise ValueError(
            f"{payload.get('condition_id')} requires a non-empty M0 LD-Agent base payload."
        )
    condition_id = str(payload.get("condition_id"))
    m0_retrieval = dict(m0_ld_agent_payload.get("retrieval", {}))
    m0_source_detail_ids = list(m0_ld_agent_payload.get("source_detail_ids", []))
    relational_source_detail_ids = list(payload.get("source_detail_ids", []))
    payload["memory_context"] = "\n".join(
        item
        for item in [
            "M0 基石记忆检索结果（所有 M1/M2/M3 条件共享同一份 M0 search/indexing 输出）：",
            m0_context,
            f"{condition_id} 关系型增量记忆层（只能叠加在上面的 M0 检索结果之上）：",
            relational_context,
            (
                "共同使用边界：先使用 M0 的 LD-Agent generic event/persona search 结果；"
                "关系型记忆只作为当前条件允许的增量层使用，不能替换、绕开或重建 M0 底座。"
            ),
        ]
        if item
    )
    payload["memory_composition"] = {
        "base_condition": "M0",
        "base_provider": m0_ld_agent_payload.get("memory_provider"),
        "base_payload_required": True,
        "base_payload_shared_by": ["M1", "M2", "M3"],
        "overlay_condition": condition_id,
        "overlay_source": "memory_conditions",
        "composition_rule": "M0_search_output_plus_relational_overlay",
    }
    payload["search_indexing_policy"] = {
        "uses_m0_search_indexing": True,
        "m0_retrieval_strategy": m0_retrieval.get("strategy"),
        "m0_storage_backend": m0_ld_agent_payload.get("storage_backend")
        or m0_ld_agent_payload.get("ld_agent_memory", {}).get("storage_backend"),
        "relational_layer_has_independent_generic_search": False,
        "relational_layer_role": "overlay_after_m0_search",
    }
    payload["m0_base_memory"] = {
        "memory_provider": m0_ld_agent_payload.get("memory_provider"),
        "source_detail_ids": m0_source_detail_ids,
        "retrieval": m0_retrieval,
        "memory_context": m0_context,
    }
    payload["relational_overlay"] = {
        "condition_id": condition_id,
        "source_detail_ids": relational_source_detail_ids,
        "memory_context": relational_context,
    }
    payload["source_detail_ids"] = _unique_strings(
        m0_source_detail_ids + relational_source_detail_ids
    )
    payload["retrieval"] = {
        "strategy": "m0_base_search_plus_relational_overlay",
        "m0_base": m0_retrieval,
        "relational_payload_source": "memory_conditions",
        "relational_overlay_condition": condition_id,
    }
    return payload


def _load_memory_conditions(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if data.get("schema_version") != "memory_conditions_v0.1_docx_route":
        raise ValueError(f"Unsupported memory condition schema: {data.get('schema_version')}")
    return data


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _resolve_condition_ids(value: str, memory_conditions: dict[str, Any]) -> list[str]:
    requested = [item.strip() for item in value.split(",") if item.strip()]
    available = {item.get("condition_id") for item in memory_conditions.get("condition_specs", [])}
    missing = [item for item in requested if item not in available]
    if missing:
        raise ValueError(f"Unknown memory conditions: {missing}")
    return requested or list(DEFAULT_CONDITION_IDS)


def _condition_spec(memory_conditions: dict[str, Any], condition_id: str) -> dict[str, Any]:
    for item in memory_conditions.get("condition_specs", []):
        if item.get("condition_id") == condition_id:
            return item
    return {"condition_id": condition_id, "name": condition_id}


def _context_policy(memory_conditions: dict[str, Any], condition_ids: list[str]) -> dict[str, str]:
    return {
        condition_id: _condition_spec(memory_conditions, condition_id).get("definition", "")
        for condition_id in condition_ids
    }


def _append_short_term_user_turn(history: list[dict[str, str]], user_message: str) -> None:
    history.append({"role": "user", "content": user_message})


def _count_user_turns(history: list[dict[str, str]]) -> int:
    return sum(1 for item in history if item.get("role") == "user")


def _estimate_context_tokens(history: list[dict[str, str]]) -> int:
    # Lightweight stable estimate for cross-condition comparability; exact tokenizer is unnecessary here.
    total_chars = sum(len(str(item.get("content", ""))) for item in history)
    return max(0, total_chars // 4)


def _unique_strings(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value)
        if text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _print_progress(
    args: argparse.Namespace,
    turn_index: int,
    expected_turns: int,
    message: dict[str, Any],
) -> None:
    if not args.print_progress:
        return
    print(
        "[progress] "
        f"turn {turn_index}/{expected_turns} "
        f"day={message['day']} "
        f"message_id={message['message_id']} "
        f"type={message.get('turn_type', 'scripted_opening')}",
        flush=True,
    )


def _print_result(print_mode: str, turns: list[dict[str, Any]], condition_ids: list[str]) -> None:
    if print_mode == "summary":
        days = sorted({turn["input"]["day"] for turn in turns})
        print(
            "Run summary: "
            f"days={len(days)}, turns={len(turns)}, "
            f"conditions={','.join(condition_ids)}"
        )
        if turns:
            print(
                "Message range: "
                f"{turns[0]['source']['message_id']} -> {turns[-1]['source']['message_id']}"
            )
        return
    for turn in turns:
        print(f"\n[{turn['source']['message_id']}] {turn['input']['user_message']}")
        for condition_id in condition_ids:
            print(f"\n[{condition_id}]\n{turn['variants'][condition_id]['assistant_answer']}")


def _default_run_dir() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    return OUTPUTS_DIR / f"run_{timestamp}"


if __name__ == "__main__":
    raise SystemExit(main())
