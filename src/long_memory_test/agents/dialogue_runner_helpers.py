from __future__ import annotations

import json
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DEEPSEEK_MAX_OUTPUT_TOKENS = 384_000
REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_message_ids(args: Namespace, messages: list[dict[str, Any]]) -> list[str]:
    if getattr(args, "all_message_ids", False):
        return [str(message["message_id"]) for message in messages]
    if getattr(args, "message_ids", None):
        return [
            message_id.strip()
            for message_id in str(args.message_ids).split(",")
            if message_id.strip()
        ]
    return [str(args.message_id)]


def find_message(messages: list[dict[str, Any]], message_id: str) -> dict[str, Any]:
    for message in messages:
        if str(message.get("message_id")) == message_id:
            return message
    raise ValueError(f"Message id not found: {message_id}")


def load_scene_cards(path: Path) -> dict[str, dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    cards = doc.get("scene_cards")
    if not isinstance(cards, list):
        raise ValueError(f"daily scene cards file must contain scene_cards: {path}")
    result: dict[str, dict[str, Any]] = {}
    for card in cards:
        if not isinstance(card, dict):
            continue
        opening_message_id = card.get("opening_message_id")
        if opening_message_id:
            result[str(opening_message_id)] = card
    return result


def load_probe_questions(path: Path) -> dict[str, list[dict[str, Any]]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    questions = doc.get("probe_questions")
    if not isinstance(questions, list):
        raise ValueError(f"probe question plan must contain probe_questions: {path}")
    result: dict[str, list[dict[str, Any]]] = {}
    for question in questions:
        if not isinstance(question, dict):
            continue
        insert_after = question.get("insert_after_message_id")
        message_id = question.get("message_id")
        if not insert_after or not message_id:
            raise ValueError("Every probe question must include insert_after_message_id and message_id")
        result.setdefault(str(insert_after), []).append(question)
    for items in result.values():
        items.sort(key=lambda item: str(item["message_id"]))
    return result


def load_resume_result(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"--resume was set but output file does not exist: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or not isinstance(result.get("turns"), list):
        raise ValueError(f"Cannot resume from invalid probe output: {path}")
    return result


def default_max_tokens(provider: str, model: str) -> int | None:
    if provider == "deepseek" and model.startswith("deepseek-v4-"):
        return DEFAULT_DEEPSEEK_MAX_OUTPUT_TOKENS
    return None


def expected_turn_count(
    messages: list[dict[str, Any]],
    scene_cards: dict[str, dict[str, Any]],
    scene_followups: int,
    probe_questions: dict[str, list[dict[str, Any]]] | None = None,
) -> int:
    count = 0
    probe_questions = probe_questions or {}
    for message in messages:
        scene_card = scene_cards.get(str(message["message_id"]))
        followup_budget = (
            int(scene_card.get("expansion_controls", {}).get("followup_budget", 0))
            if scene_card
            else 0
        )
        count += 1 + min(max(scene_followups, 0), followup_budget)
        count += len(probe_questions.get(str(message["message_id"]), []))
    return count


def expected_message_id_sequence(
    *,
    messages: list[dict[str, Any]],
    scene_cards: dict[str, dict[str, Any]],
    scene_followups: int,
    probe_questions: dict[str, list[dict[str, Any]]] | None = None,
) -> list[str]:
    message_ids: list[str] = []
    probe_questions = probe_questions or {}
    for message in messages:
        message_id = str(message["message_id"])
        message_ids.append(message_id)
        scene_card = scene_cards.get(message_id)
        followup_budget = (
            int(scene_card.get("expansion_controls", {}).get("followup_budget", 0))
            if scene_card
            else 0
        )
        requested_followups = min(max(scene_followups, 0), followup_budget)
        for followup_index in range(1, requested_followups + 1):
            message_ids.append(f"{message_id}_F{followup_index:03d}")
        for probe_question in probe_questions.get(message_id, []):
            message_ids.append(str(probe_question["message_id"]))
    return message_ids


def assert_completed_turns_are_expected_prefix(
    turns: list[dict[str, Any]],
    expected_message_ids: list[str],
) -> None:
    completed_message_ids = [str(turn["source"]["message_id"]) for turn in turns]
    expected_prefix = expected_message_ids[: len(completed_message_ids)]
    if completed_message_ids != expected_prefix:
        raise ValueError(
            "Cannot resume because completed turns are not a prefix of the requested "
            f"plan. completed={completed_message_ids} expected_prefix={expected_prefix}"
        )


def rebuild_two_condition_runtime_state(
    turns: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, str]]], list[str], dict[str, dict[str, Any]]]:
    short_term_histories: dict[str, list[dict[str, str]]] = {"M0": [], "M1": []}
    transcript_message_ids: list[str] = []
    completed_turn_inputs: dict[str, dict[str, Any]] = {}
    for expected_index, turn in enumerate(turns, start=1):
        if turn.get("turn_index") != expected_index:
            raise ValueError(
                "Cannot resume because turn_index values are not contiguous: "
                f"expected {expected_index}, got {turn.get('turn_index')}"
            )
        message_id = str(turn["source"]["message_id"])
        user_message = str(turn["input"]["user_message"])
        append_short_term_history(
            short_term_histories["M0"],
            user_message,
            str(turn["variants"]["M0"]["assistant_answer"]),
        )
        append_short_term_history(
            short_term_histories["M1"],
            user_message,
            str(turn["variants"]["M1"]["assistant_answer"]),
        )
        transcript_message_ids.append(message_id)
        completed_turn_inputs[message_id] = dict(turn["input"])
    return short_term_histories, transcript_message_ids, completed_turn_inputs


def append_short_term_history(
    history: list[dict[str, str]],
    user_message: str,
    answer: str,
) -> None:
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": answer})


def write_checkpoint(
    *,
    output_path: Path,
    conversation_log_path: Path,
    result: dict[str, Any],
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
    atomic_write_json(output_path, result)
    sync_conversation_log(
        path=conversation_log_path,
        run_id=result["run_id"],
        turns=result["turns"],
        reset=reset_conversation_log,
    )


def sync_conversation_log(
    *,
    path: Path,
    run_id: str,
    turns: list[dict[str, Any]],
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
    atomic_write_json(path, log)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def generate_user_followup(
    *,
    client: Any,
    model: str,
    scene_card: dict[str, Any],
    opening_message: dict[str, Any],
    followup_index: int,
    previous_user_messages: list[str],
    timeout: float,
    max_tokens: int | None,
) -> dict[str, Any]:
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
    parsed = parse_json_object(raw_output)
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


def parse_json_object(raw_text: str) -> dict[str, Any]:
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


def build_followup_message(
    *,
    opening_message: dict[str, Any],
    scene_card: dict[str, Any],
    followup_index: int,
    followup: dict[str, Any],
) -> dict[str, Any]:
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


def build_evaluation_targets(
    scene_card: dict[str, Any] | None,
    message: dict[str, Any] | None = None,
) -> dict[str, Any]:
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


def display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)
