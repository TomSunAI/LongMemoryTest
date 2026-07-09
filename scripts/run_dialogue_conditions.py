#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _mac_awake import (
    DEFAULT_CAFFEINATE_FLAGS,
    maybe_reexec_under_awake_guard,
    parse_caffeinate_flags,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.llm import create_llm_client  # noqa: E402
from long_memory_test.memory import (  # noqa: E402
    CUMULATIVE_RELATIONAL_CONDITION_IDS,
    INDEPENDENT_RELATIONAL_CONDITION_IDS,
    LDAgentMemoryRuntime,
    M0_AUGMENTED_ATOMIC_RELATIONAL_CONDITION_IDS,
    RELATIONAL_CONDITION_IDS,
    RelationalMemoryRuntime,
    relational_condition_is_independent,
    relational_condition_uses_m0_base,
)
from long_memory_test.evaluation.generation_prompt_reference import (  # noqa: E402
    build_answer_condition_system_prompt,
    build_independent_relational_payload_context,
    build_relational_payload_context,
)
from long_memory_test.agents import dialogue_runner_helpers as runner_helpers  # noqa: E402
from long_memory_test.experiment_cache import (  # noqa: E402
    CACHE_MEMORY_CONDITIONS_PATH,
    DAILY_SCENE_CARDS_PATH,
    DAILY_USER_MESSAGE_PATH,
    OUTPUTS_DIR,
    PROBE_QUESTION_PLAN_PATH,
)


DEFAULT_CONDITION_IDS = ["M0", "M1", "M2", "M3"]
MIN_ASSISTANT_ANSWER_CHARS = 20
ASSISTANT_ANSWER_MAX_ATTEMPTS = 4
LLM_REQUEST_MAX_ATTEMPTS = 3
SHORT_TERM_CONTEXT_MODE = "shared_user_turns_only"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run docx-route dialogue turns under M0/M1/M2/M3 memory conditions, "
            "with optional independent Z1/Z2/Z3 feature runtimes."
        )
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
    parser.add_argument("--relational-memory-top-k", type=int, default=5)
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
    parser.add_argument(
        "--no-caffeinate",
        action="store_true",
        help=(
            "Disable the macOS caffeinate awake guard. By default long runs "
            "prevent system sleep while allowing display sleep."
        ),
    )
    parser.add_argument(
        "--caffeinate-flags",
        default=DEFAULT_CAFFEINATE_FLAGS,
        help=(
            "Flags passed to caffeinate on macOS. Default '-i -m -s' prevents "
            "idle system sleep and disk sleep without preventing display sleep."
        ),
    )
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
    caffeinate_flags = parse_caffeinate_flags(args.caffeinate_flags)
    reexec_code = maybe_reexec_under_awake_guard(
        sys.argv,
        disabled=args.no_caffeinate,
        flags=caffeinate_flags,
    )
    if reexec_code is not None:
        return reexec_code

    messages_doc = _load_json(args.daily_messages)
    message_ids = runner_helpers.resolve_message_ids(args, messages_doc["messages"])
    messages = [
        runner_helpers.find_message(messages_doc["messages"], message_id)
        for message_id in message_ids
    ]
    scene_cards = (
        runner_helpers.load_scene_cards(args.scene_cards)
        if args.scene_followups > 0 or args.probe_questions
        else {}
    )
    probe_questions = (
        runner_helpers.load_probe_questions(args.probe_questions)
        if args.probe_questions
        else {}
    )
    memory_conditions = _load_memory_conditions(args.memory_conditions)
    condition_ids = _resolve_condition_ids(args.conditions, memory_conditions)
    existing_result = runner_helpers.load_resume_result(args.output) if args.resume else None

    llm_client, llm_config = create_llm_client()
    max_tokens = args.max_tokens or runner_helpers.default_max_tokens(
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
    expected_turns = runner_helpers.expected_turn_count(
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
    result["tau_contract"] = memory_conditions.get("tau_contract", {})
    uses_m0_base = any(_condition_uses_m0_base(condition_id) for condition_id in condition_ids)
    if uses_m0_base and existing_result and existing_result.get("m0_ld_agent_memory"):
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
    elif uses_m0_base:
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
    else:
        m0_memory_runtime = LDAgentMemoryRuntime(
            top_k=args.m0_ld_agent_top_k,
            short_term_k=args.m0_ld_agent_short_term_k,
            llm_client=llm_client,
            llm_model=llm_config.model,
            llm_timeout=args.llm_timeout,
            storage_backend=args.m0_ld_agent_storage_backend,
            chroma_path=args.m0_ld_agent_chroma_path,
        )
    result["m0_ld_agent_memory"] = m0_memory_runtime.snapshot()
    relational_memory_runtimes = _build_relational_memory_runtimes(
        result=result,
        condition_ids=condition_ids,
        output_dir=args.output.parent,
        top_k=args.relational_memory_top_k,
        llm_client=llm_client,
        llm_model=llm_config.model,
        llm_timeout=args.llm_timeout,
    )
    result["relational_memory_runtimes"] = _relational_runtime_snapshots(
        relational_memory_runtimes
    )
    _write_run_config(
        args.output.parent / "run_config.json",
        result=result,
        args=args,
        llm_config=llm_config,
        max_tokens=max_tokens,
        condition_ids=condition_ids,
    )

    expected_message_ids = runner_helpers.expected_message_id_sequence(
        messages=messages,
        scene_cards=scene_cards,
        scene_followups=args.scene_followups,
        probe_questions=probe_questions,
    )
    runner_helpers.assert_completed_turns_are_expected_prefix(
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
                    relational_memory_runtimes=relational_memory_runtimes,
                    condition_ids=condition_ids,
                    short_term_histories=short_term_histories,
                    previous_message_ids=list(transcript_message_ids),
                )
                result["turns"].append(turn)
                result["m0_ld_agent_memory"] = m0_memory_runtime.snapshot()
                result["relational_memory_runtimes"] = _relational_runtime_snapshots(
                    relational_memory_runtimes
                )
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
                followup = runner_helpers.generate_user_followup(
                    client=llm_client,
                    model=llm_config.model,
                    scene_card=scene_card,
                    opening_message=message,
                    followup_index=next_followup_index,
                    previous_user_messages=[item["user_message"] for item in user_inputs],
                    timeout=args.llm_timeout,
                    max_tokens=max_tokens,
                )
                current_input = runner_helpers.build_followup_message(
                    opening_message=message,
                    scene_card=scene_card,
                    followup_index=next_followup_index,
                    followup=followup,
                )
                current_input = _with_followup_tau(
                    followup_message=current_input,
                    opening_message=message,
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
                relational_memory_runtimes=relational_memory_runtimes,
                condition_ids=condition_ids,
                short_term_histories=short_term_histories,
                previous_message_ids=list(transcript_message_ids),
            )
            result["turns"].append(turn)
            result["m0_ld_agent_memory"] = m0_memory_runtime.snapshot()
            result["relational_memory_runtimes"] = _relational_runtime_snapshots(
                relational_memory_runtimes
            )
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

    if uses_m0_base:
        m0_memory_runtime.flush_current_session(reason="run_complete")
    result["m0_ld_agent_memory"] = m0_memory_runtime.snapshot()
    result["relational_memory_runtimes"] = _relational_runtime_snapshots(
        relational_memory_runtimes
    )
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
    relational_memory_runtimes: dict[str, RelationalMemoryRuntime] | None = None,
) -> dict[str, Any]:
    user_message = str(message["user_message"])
    variants = {}
    history_before_by_condition = {
        condition_id: list(short_term_histories[condition_id])
        for condition_id in condition_ids
    }
    memory_action_start = len(m0_memory_runtime.actions)
    uses_m0_base = any(_condition_uses_m0_base(condition_id) for condition_id in condition_ids)
    m0_ld_agent_payload = (
        m0_memory_runtime.retrieve_payload(message) if uses_m0_base else {}
    )
    relational_memory_runtimes = relational_memory_runtimes or {}
    relational_action_starts = {
        condition_id: len(runtime.actions)
        for condition_id, runtime in relational_memory_runtimes.items()
    }
    max_workers = max(1, min(int(condition_workers), len(condition_ids)))

    def run_one_condition(condition_id: str) -> tuple[str, dict[str, Any]]:
        payload = _runtime_payload_for_condition(
            memory_conditions=memory_conditions,
            condition_id=condition_id,
            message=message,
            m0_ld_agent_payload=m0_ld_agent_payload,
            relational_memory_runtimes=relational_memory_runtimes,
        )
        payload = dict(payload)
        if isinstance(message.get("tau"), dict):
            payload.setdefault("tau", dict(message["tau"]))
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
    if uses_m0_base:
        m0_answer = str(variants.get("M0", {}).get("assistant_answer", ""))
        m0_record_action = m0_memory_runtime.record_completed_turn(
            message=message,
            assistant_answer=m0_answer,
            run_id=run_id,
        )
        if "M0" in variants:
            variants["M0"]["memory_writeback"] = m0_record_action
        memory_actions = list(m0_memory_runtime.actions[memory_action_start:])
    else:
        memory_actions = []
    for condition_id, runtime in relational_memory_runtimes.items():
        if condition_id not in variants:
            continue
        action = runtime.record_completed_turn(
            message=message,
            assistant_answer=str(variants[condition_id].get("assistant_answer", "")),
            run_id=run_id,
        )
        variants[condition_id]["memory_writeback"] = action
        memory_actions.extend(
            runtime.actions[relational_action_starts.get(condition_id, 0):]
        )
    for condition_id in condition_ids:
        _append_short_term_user_turn(short_term_histories[condition_id], user_message)

    return {
        "run_id": run_id,
        "created_at": created_at,
        "turn_index": turn_index,
        "probe": "docx_m0_m1_m2_m3_memory_conditions",
        "conversation_context_policy": _context_policy(memory_conditions, condition_ids),
        "source": {
            "daily_messages_path": runner_helpers.display_path(daily_messages_path),
            "scene_cards_path": (
                runner_helpers.display_path(scene_cards_path) if scene_cards_path else None
            ),
            "memory_conditions_path": runner_helpers.display_path(memory_conditions_path),
            "message_id": message["message_id"],
            "tau": dict(message.get("tau", {})) if isinstance(message.get("tau"), dict) else {},
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
        "evaluation_targets": runner_helpers.build_evaluation_targets(scene_card, message),
        "memory_setup": {
            "route": "docx",
            "script_construction": {
                "notation": "tau=(z,T,L,I,P)",
                "tau": (
                    dict(message.get("tau", {}))
                    if isinstance(message.get("tau"), dict)
                    else {}
                ),
            },
            "conditions": condition_ids,
            "memory_payload_source": runner_helpers.display_path(memory_conditions_path),
            "m0_memory_provider": "ld_agent_memory",
            "m0_ld_agent_reference": m0_ld_agent_payload.get("ld_agent_reference"),
            "m1_m2_m3_share_m0_base_memory": any(
                condition_id in CUMULATIVE_RELATIONAL_CONDITION_IDS
                for condition_id in condition_ids
            ),
            "relational_conditions_share_m0_base_memory": any(
                condition_id in CUMULATIVE_RELATIONAL_CONDITION_IDS
                for condition_id in condition_ids
            ),
            "z1_z2_z3_use_m0_base_memory": False,
            "payload_isolation": True,
            "relational_runtime_conditions": sorted(relational_memory_runtimes),
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
        completion = _create_chat_completion_with_retry(
            request_client=request_client,
            request_kwargs=request_kwargs,
            condition_id=condition_id,
        )
        last_content = completion.choices[0].message.content or ""
        if len(last_content.strip()) >= MIN_ASSISTANT_ANSWER_CHARS:
            return last_content
        if attempt < ASSISTANT_ANSWER_MAX_ATTEMPTS - 1:
            time.sleep(min(2.0, 0.5 * (attempt + 1)))
    raise RuntimeError(
        "LLM returned an empty or degenerate assistant answer repeatedly "
        f"for condition {condition_id}. Last answer: {last_content!r}"
    )


def _create_chat_completion_with_retry(
    *,
    request_client: Any,
    request_kwargs: dict[str, Any],
    condition_id: str,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(LLM_REQUEST_MAX_ATTEMPTS):
        try:
            return request_client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            last_error = exc
            if attempt >= LLM_REQUEST_MAX_ATTEMPTS - 1:
                break
            backoff = min(20.0, 2.0 * (attempt + 1))
            print(
                "[warn] "
                f"condition={condition_id} request failed "
                f"attempt={attempt + 1}/{LLM_REQUEST_MAX_ATTEMPTS}: "
                f"{type(exc).__name__}: {exc}; retrying in {backoff:.1f}s",
                flush=True,
            )
            time.sleep(backoff)
    assert last_error is not None
    raise last_error


def _build_condition_system_prompt(
    *,
    condition_id: str,
    condition_spec: dict[str, Any],
    memory_payload: dict[str, Any],
) -> str:
    return build_answer_condition_system_prompt(
        condition_id=condition_id,
        memory_context=str(memory_payload.get("memory_context", "")),
    )


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
        runner_helpers.display_path(probe_questions_path) if probe_questions_path else None
    )
    requested_memory_path = runner_helpers.display_path(memory_conditions_path)
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
    runner_helpers.write_checkpoint(
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
    relational_condition_ids = [
        condition_id
        for condition_id in condition_ids
        if condition_id in RELATIONAL_CONDITION_IDS
    ]
    cumulative_relational_condition_ids = [
        condition_id
        for condition_id in condition_ids
        if condition_id in CUMULATIVE_RELATIONAL_CONDITION_IDS
    ]
    independent_relational_condition_ids = [
        condition_id
        for condition_id in condition_ids
        if condition_id in INDEPENDENT_RELATIONAL_CONDITION_IDS
    ]
    m0_augmented_atomic_condition_ids = [
        condition_id
        for condition_id in condition_ids
        if condition_id in M0_AUGMENTED_ATOMIC_RELATIONAL_CONDITION_IDS
    ]
    m0_base_condition_ids = [
        condition_id for condition_id in condition_ids if _condition_uses_m0_base(condition_id)
    ]
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
            "m1_m2_m3_share_m0_base_memory": bool(cumulative_relational_condition_ids),
            "relational_conditions_share_m0_base_memory": bool(
                cumulative_relational_condition_ids
            ),
            "condition_payloads_are_isolated": True,
            "m1_m2_m3_are_independent_memory_runtimes": True,
            "z1_z2_z3_are_independent_single_feature_runtimes": True,
            "u1_u2_u3_are_m0_augmented_single_feature_runtimes": True,
            "z1_z2_z3_use_m0_base_memory": False,
            "u1_u2_u3_use_m0_base_memory": bool(m0_augmented_atomic_condition_ids),
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
            "daily_messages": runner_helpers.display_path(args.daily_messages),
            "scene_cards": runner_helpers.display_path(args.scene_cards),
            "probe_questions": (
                runner_helpers.display_path(args.probe_questions) if args.probe_questions else None
            ),
            "memory_conditions": runner_helpers.display_path(args.memory_conditions),
            "tau_contract": result.get("tau_contract", {}),
        },
        "script_construction": {
            "notation": "tau=(z,T,L,I,P)",
            "single_script_source": True,
            "tau_contract": result.get("tau_contract", {}),
            "conditions_do_not_generate_scripts": True,
        },
        "conditions": condition_ids,
        "relational_memory_runtimes": {
            "provider": "independent_relational_memory_runtime",
            "conditions": relational_condition_ids,
            "cumulative_m_conditions": cumulative_relational_condition_ids,
            "m0_independent_z_conditions": independent_relational_condition_ids,
            "m0_augmented_atomic_u_conditions": m0_augmented_atomic_condition_ids,
            "top_k": args.relational_memory_top_k,
            "storage_root": runner_helpers.display_path(path.parent / "memory_runtimes"),
            "namespace_policy": (
                "M1/M2/M3/Z1/Z2/Z3 each read and write only their own condition namespace; "
                "M2/M3 cumulative lower-level memories are copied inside the same condition namespace; "
                "Z1/Z2/Z3 are single-feature runtimes and do not inherit each other. "
                "U1/U2/U3 are also single-feature runtimes, each composed with M0 base. "
                "M1/M2/M3 final prompt payloads are composed with same-turn M0 retrieved base; "
                "Z1/Z2/Z3 final prompt payloads are not composed with M0; "
                "U1/U2/U3 final prompt payloads are composed with same-turn M0 retrieved base."
            ),
            "writeback_method": "llm_event_line_relational_memory_consolidation_with_deterministic_fallback",
            "probe_writeback": False,
            "uses_m0_payload": bool(
                cumulative_relational_condition_ids
                or m0_augmented_atomic_condition_ids
            ),
            "uses_m0_payload_by_condition": {
                condition_id: relational_condition_uses_m0_base(condition_id)
                for condition_id in relational_condition_ids
            },
            "uses_other_condition_payloads": False,
        },
        "m0_ld_agent_memory_baseline": {
            "provider": "ld_agent_memory",
            "active": bool(m0_base_condition_ids),
            "ld_agent_reference": result.get("m0_ld_agent_memory", {}).get(
                "ld_agent_reference"
            ),
            "top_k": args.m0_ld_agent_top_k,
            "short_term_k": args.m0_ld_agent_short_term_k,
            "storage_backend": args.m0_ld_agent_storage_backend,
            "chroma_path": (
                runner_helpers.display_path(args.m0_ld_agent_chroma_path)
                if args.m0_ld_agent_chroma_path
                else None
            ),
            "uses_ld_agent_generator": False,
            "uses_ld_agent_checkpoint": False,
            "uses_letta": False,
            "writeback_method": "ld_agent_session_summary_and_personas_traits",
            "payload_isolation": {
                "M0": "runtime_ld_agent_session_summary_payload",
                "M1": "runtime_ld_agent_session_summary_payload_plus_conclusion_overlay",
                "M2": "runtime_ld_agent_session_summary_payload_plus_conclusion_and_event_summary_overlay",
                "M3": "runtime_ld_agent_session_summary_payload_plus_conclusion_event_summary_and_detail_anchor_overlay",
                "Z1": "independent_conclusion_overlay_without_m0_base",
                "Z2": "independent_event_summary_overlay_without_m0_base",
                "Z3": "independent_detail_anchor_overlay_without_m0_base",
                "U1": "runtime_ld_agent_session_summary_payload_plus_atomic_conclusion_overlay",
                "U2": "runtime_ld_agent_session_summary_payload_plus_atomic_event_summary_overlay",
                "U3": "runtime_ld_agent_session_summary_payload_plus_atomic_detail_anchor_overlay",
                "m1_m2_m3_share_m0_payload": True,
                "z1_z2_z3_share_m0_payload": False,
                "u1_u2_u3_share_m0_payload": True,
                "m1_m2_m3_answer_writeback_isolated": True,
                "z1_z2_z3_answer_writeback_isolated": True,
                "u1_u2_u3_answer_writeback_isolated": True,
            },
            "long_term_memory_bank": [
                "session_summary_memories",
                "generic_persona_memories",
            ],
            "retrieval": {
                "strategy": "topic_overlap_time_decay",
                "top_k": args.m0_ld_agent_top_k,
            },
            "used_by_conditions": m0_base_condition_ids,
        },
        "scene_followups": args.scene_followups,
        "expected_turns": result["expected_turns"],
        "outputs": {
            "responses_by_condition": runner_helpers.display_path(args.output),
            "conversation_log": runner_helpers.display_path(args.conversation_log),
            "run_config": runner_helpers.display_path(path),
        },
        "checkpoint_policy": {
            "resume_supported": True,
            "completed_message_ids_are_persisted": True,
            "duplicate_message_ids_are_skipped": True,
            "input_hash_recorded_per_turn": True,
            "checkpoint_written_after_each_completed_turn": True,
            "m0_ld_agent_memory_snapshot_persisted": bool(m0_base_condition_ids),
            "relational_memory_runtime_snapshots_persisted": True,
            "condition_payloads_are_isolated": True,
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


def _with_followup_tau(
    *,
    followup_message: dict[str, Any],
    opening_message: dict[str, Any],
) -> dict[str, Any]:
    result = dict(followup_message)
    tau = opening_message.get("tau")
    if isinstance(tau, dict):
        result["tau"] = {
            **tau,
            "followup_message_id": result.get("message_id"),
            "followup_of": opening_message.get("message_id"),
            "turn_role": "llm_user_followup",
        }
    return result


def _build_relational_memory_runtimes(
    *,
    result: dict[str, Any],
    condition_ids: list[str],
    output_dir: Path,
    top_k: int,
    llm_client: Any | None = None,
    llm_model: str | None = None,
    llm_timeout: float = 60.0,
) -> dict[str, RelationalMemoryRuntime]:
    snapshots = result.get("relational_memory_runtimes", {})
    runtimes: dict[str, RelationalMemoryRuntime] = {}
    for condition_id in condition_ids:
        if condition_id not in RELATIONAL_CONDITION_IDS:
            continue
        storage_root = output_dir / "memory_runtimes" / condition_id
        snapshot = snapshots.get(condition_id) if isinstance(snapshots, dict) else None
        if snapshot:
            runtimes[condition_id] = RelationalMemoryRuntime.from_snapshot(
                snapshot,
                condition_id=condition_id,
                top_k=top_k,
                storage_root=storage_root,
                llm_client=llm_client,
                llm_model=llm_model,
                llm_timeout=llm_timeout,
            )
        else:
            runtimes[condition_id] = RelationalMemoryRuntime.from_completed_turns(
                result.get("turns", []),
                condition_id=condition_id,
                top_k=top_k,
                storage_root=storage_root,
                llm_client=llm_client,
                llm_model=llm_model,
                llm_timeout=llm_timeout,
            )
    return runtimes


def _relational_runtime_snapshots(
    runtimes: dict[str, RelationalMemoryRuntime],
) -> dict[str, dict[str, Any]]:
    return {
        condition_id: runtime.snapshot()
        for condition_id, runtime in sorted(runtimes.items())
    }


def _runtime_payload_for_condition(
    *,
    memory_conditions: dict[str, Any],
    condition_id: str,
    message: dict[str, Any],
    m0_ld_agent_payload: dict[str, Any] | None,
    relational_memory_runtimes: dict[str, RelationalMemoryRuntime],
) -> dict[str, Any]:
    if condition_id == "M0":
        return dict(m0_ld_agent_payload or {})
    runtime = relational_memory_runtimes.get(condition_id)
    if runtime is not None:
        relational_overlay = runtime.retrieve_payload(message)
        if relational_condition_is_independent(condition_id):
            return _finalize_independent_relational_payload(
                condition_id=condition_id,
                relational_overlay=relational_overlay,
                overlay_source="relational_memory_runtime",
            )
        return _compose_relational_payload_with_m0_base(
            condition_id=condition_id,
            m0_ld_agent_payload=dict(m0_ld_agent_payload or {}),
            relational_overlay=relational_overlay,
            overlay_source="relational_memory_runtime",
        )
    return _payload_for_condition(
        memory_conditions,
        condition_id,
        message,
        m0_ld_agent_payload=m0_ld_agent_payload,
    )


def _payload_for_condition(
    memory_conditions: dict[str, Any],
    condition_id: str,
    message: dict[str, Any],
    *,
    m0_ld_agent_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if condition_id == "M0":
        return dict(m0_ld_agent_payload or {})

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
            if relational_condition_is_independent(condition_id):
                return _finalize_independent_relational_payload(
                    condition_id=condition_id,
                    relational_overlay=payload,
                    overlay_source="memory_conditions",
                )
            return _compose_relational_payload_with_m0_base(
                condition_id=condition_id,
                m0_ld_agent_payload=dict(m0_ld_agent_payload or {}),
                relational_overlay=payload,
                overlay_source="memory_conditions",
            )
    default_payload = memory_conditions.get("default_payloads", {}).get(condition_id, {})
    payload = dict(default_payload)
    payload.setdefault("condition_id", condition_id)
    if relational_condition_is_independent(condition_id):
        return _finalize_independent_relational_payload(
            condition_id=condition_id,
            relational_overlay=payload,
            overlay_source="memory_conditions_default",
        )
    return _compose_relational_payload_with_m0_base(
        condition_id=condition_id,
        m0_ld_agent_payload=dict(m0_ld_agent_payload or {}),
        relational_overlay=payload,
        overlay_source="memory_conditions_default",
    )


def _finalize_independent_relational_payload(
    *,
    condition_id: str,
    relational_overlay: dict[str, Any],
    overlay_source: str,
) -> dict[str, Any]:
    overlay = dict(relational_overlay)
    overlay_context = str(overlay.get("memory_context", "")).strip()
    if not overlay_context:
        overlay_context = "- 当前没有检索到可用关系记忆增强。"

    relational_retrieval = overlay.get("retrieval", {})
    if not isinstance(relational_retrieval, dict):
        relational_retrieval = {}

    payload = dict(overlay)
    payload["condition_id"] = condition_id
    payload["memory_provider"] = overlay.get("memory_provider") or "independent_relational_memory"
    payload["requires_runtime_letta"] = False
    payload["requires_runtime_ld_agent_memory"] = False
    payload["payload_role"] = "final_condition_payload"
    payload["memory_context"] = build_independent_relational_payload_context(
        condition_id=condition_id,
        overlay_context=overlay_context,
    )
    payload["source_detail_ids"] = _unique_strings(
        [str(item) for item in overlay.get("source_detail_ids", []) if item]
    )
    payload.pop("m0_base_memory", None)
    payload["relational_overlay"] = {
        "condition_id": condition_id,
        "memory_provider": overlay.get("memory_provider"),
        "runtime_id": overlay.get("runtime_id"),
        "enabled_memory_types": list(overlay.get("enabled_memory_types", [])),
        "source_detail_ids": list(overlay.get("source_detail_ids", [])),
        "memory_context": overlay_context,
        "retrieval": dict(relational_retrieval),
    }
    payload["memory_composition"] = {
        "base_condition": None,
        "base_provider": None,
        "base_payload_required": False,
        "base_payload_shared_by": [],
        "overlay_condition": condition_id,
        "overlay_source": overlay_source,
        "composition_rule": "independent_relational_payload_no_m0_base",
        "condition_answer_isolation": (
            "only the shared user turn is reused; condition assistant answers "
            "do not feed other conditions"
        ),
        "uses_m0_payload": False,
        "uses_other_condition_payloads": False,
    }
    payload["search_indexing_policy"] = {
        "uses_m0_search_indexing": False,
        "m0_retrieval_strategy": None,
        "m0_storage_backend": None,
        "relational_layer_has_independent_generic_search": False,
        "relational_layer_role": "independent_condition_payload",
        "relational_retrieval_strategy": relational_retrieval.get("strategy"),
    }
    payload["retrieval"] = {
        "strategy": "independent_relational_overlay_only",
        "uses_m0_payload": False,
        "uses_other_condition_payloads": False,
        "relational_retrieval": relational_retrieval,
        "relational_overlay_condition": condition_id,
        "relational_payload_source": overlay_source,
    }
    return payload


def _compose_relational_payload_with_m0_base(
    *,
    condition_id: str,
    m0_ld_agent_payload: dict[str, Any],
    relational_overlay: dict[str, Any],
    overlay_source: str,
) -> dict[str, Any]:
    if relational_condition_is_independent(condition_id):
        return _finalize_independent_relational_payload(
            condition_id=condition_id,
            relational_overlay=relational_overlay,
            overlay_source=overlay_source,
        )
    if condition_id not in RELATIONAL_CONDITION_IDS:
        return dict(relational_overlay)

    overlay = dict(relational_overlay)
    m0_base = dict(m0_ld_agent_payload)
    m0_context = _sanitize_m0_base_context_for_relational_overlay(
        str(m0_base.get("memory_context", ""))
    ).strip()
    overlay_context = str(overlay.get("memory_context", "")).strip()
    if not m0_context:
        m0_context = "- 当前 M0 runtime 没有检索到可用普通长期记忆。"
    if not overlay_context:
        overlay_context = "- 当前没有检索到可用关系记忆增强。"

    payload = dict(overlay)
    payload["condition_id"] = condition_id
    payload["memory_provider"] = "m0_base_plus_relational_overlay"
    payload["requires_runtime_letta"] = False
    payload["requires_runtime_ld_agent_memory"] = True
    payload["payload_role"] = "final_condition_payload"
    payload["memory_context"] = build_relational_payload_context(
        condition_id=condition_id,
        overlay_context=overlay_context,
        m0_context=m0_context,
    )
    payload["source_detail_ids"] = _unique_strings(
        [
            *[str(item) for item in m0_base.get("source_detail_ids", []) if item],
            *[str(item) for item in overlay.get("source_detail_ids", []) if item],
        ]
    )
    payload["m0_base_memory"] = {
        "condition_id": "M0",
        "memory_provider": m0_base.get("memory_provider"),
        "runtime_id": m0_base.get("runtime_id"),
        "memory_unit": m0_base.get("memory_unit"),
        "storage_backend": m0_base.get("storage_backend"),
        "source_detail_ids": list(m0_base.get("source_detail_ids", [])),
        "memory_context": m0_context,
        "retrieval": dict(m0_base.get("retrieval", {})),
    }
    payload["relational_overlay"] = {
        "condition_id": condition_id,
        "memory_provider": overlay.get("memory_provider"),
        "runtime_id": overlay.get("runtime_id"),
        "enabled_memory_types": list(overlay.get("enabled_memory_types", [])),
        "source_detail_ids": list(overlay.get("source_detail_ids", [])),
        "memory_context": overlay_context,
        "retrieval": dict(overlay.get("retrieval", {})),
    }
    payload["memory_composition"] = {
        "base_condition": "M0",
        "base_provider": m0_base.get("memory_provider"),
        "base_payload_required": True,
        "base_payload_shared_by": [
            item for item in RELATIONAL_CONDITION_IDS if relational_condition_uses_m0_base(item)
        ],
        "overlay_condition": condition_id,
        "overlay_source": overlay_source,
        "composition_rule": "m0_base_plus_condition_relational_overlay",
        "condition_answer_isolation": (
            "only the shared user turn is reused; condition assistant answers "
            "do not feed other conditions"
        ),
        "m0_current_session_agent_answers_removed": True,
        "m0_event_line_filtering": False,
        "m0_base_role": "generic_session_day_background",
        "relational_overlay_precedence": True,
    }
    m0_retrieval = m0_base.get("retrieval", {})
    if not isinstance(m0_retrieval, dict):
        m0_retrieval = {}
    relational_retrieval = overlay.get("retrieval", {})
    if not isinstance(relational_retrieval, dict):
        relational_retrieval = {}
    payload["search_indexing_policy"] = {
        "uses_m0_search_indexing": True,
        "m0_retrieval_strategy": m0_retrieval.get("strategy")
        or m0_base.get("retrieval_strategy"),
        "m0_storage_backend": m0_base.get("storage_backend"),
        "relational_layer_has_independent_generic_search": False,
        "relational_layer_role": "condition_specific_overlay_after_m0_retrieval",
        "relational_retrieval_strategy": relational_retrieval.get("strategy"),
    }
    payload["retrieval"] = {
        "strategy": "m0_retrieval_plus_relational_overlay",
        "uses_m0_payload": True,
        "uses_other_condition_payloads": False,
        "m0_retrieval": m0_retrieval,
        "relational_retrieval": relational_retrieval,
        "relational_overlay_condition": condition_id,
        "relational_payload_source": overlay_source,
    }
    return payload


def _sanitize_m0_base_context_for_relational_overlay(memory_context: str) -> str:
    """Prevent relational conditions from reading M0's current-session assistant answers."""
    lines = []
    for line in str(memory_context).splitlines():
        for marker in (" | Assistant(M0):", " | Assistant:", " | Agent:"):
            if line.lstrip().startswith(("- (line ", "   - (line ")) and marker in line:
                line = line.split(marker, 1)[0]
                break
        lines.append(line)
    return "\n".join(lines)


def _unique_strings(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _load_memory_conditions(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    supported_schemas = {
        "memory_conditions_v0.1_docx_route",
        "memory_conditions_v0.2_tau_route",
    }
    if data.get("schema_version") not in supported_schemas:
        raise ValueError(f"Unsupported memory condition schema: {data.get('schema_version')}")
    return data


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _condition_uses_m0_base(condition_id: str) -> bool:
    return condition_id == "M0" or relational_condition_uses_m0_base(condition_id)


def _resolve_condition_ids(value: str, memory_conditions: dict[str, Any]) -> list[str]:
    requested = [item.strip() for item in value.split(",") if item.strip()]
    available = {item.get("condition_id") for item in memory_conditions.get("condition_specs", [])}
    available.update(["M0", *RELATIONAL_CONDITION_IDS])
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
