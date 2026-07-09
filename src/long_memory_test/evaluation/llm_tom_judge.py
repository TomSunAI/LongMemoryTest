from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from pathlib import Path
from typing import Any

from long_memory_test.llm import LLMConfig


MAX_DIMENSION_SCORE = 2
ERROR_TEXT_LIMIT = 2000


FAILURE_TYPES = [
    "memory_absence",
    "memory_misuse",
    "memory_overuse",
    "fabrication",
    "alienation",
    "instruction_only_success",
]


TOM_DIMENSION_RUBRIC: dict[str, dict[str, str]] = {
    "hidden_intent_recognition": {
        "label": "隐含意图识别",
        "question": "是否识别用户字面表达背后的真实诉求。",
        "score_0": "只回答字面问题，或没有接住用户真正想确认的东西。",
        "score_1": "部分识别潜台词，但没有转化为回应策略。",
        "score_2": "明确接住潜台词，并围绕用户真实需求回应。",
    },
    "emotional_state_recognition": {
        "label": "情绪状态识别",
        "question": "是否识别疲惫、失落、自我怀疑、不安、担心被遗忘等状态。",
        "score_0": "把用户状态当普通咨询处理，或只有泛化安慰。",
        "score_1": "提到情绪，但和建议关系弱。",
        "score_2": "识别具体状态，并据此调整建议强度。",
    },
    "shared_context_invocation": {
        "label": "共同语境调用",
        "question": "是否接上此前形成的处理方式，而不是每次从零开始。",
        "score_0": "要求用户重讲历史，或把持续事件当成第一次出现。",
        "score_1": "泛称“之前”或“我们说过”，但没有可验证连接。",
        "score_2": "自然接上旧线索或共同处理方式，并继续当前判断。",
    },
    "alienation_error_rate": {
        "label": "陌生化错误率",
        "question": "是否出现客服化、角色化、过度亲密或要求重讲历史。",
        "score_0": "出现明显风险词、要求用户重复既有背景，或关系位置明显出戏。",
        "score_1": "没有明显风险，但只是中性助理式回答；缺少关系连续性证据。",
        "score_2": "无陌生化风险，并且通过具体措辞或处理方式保持稳定关系位置。",
    },
    "natural_detail_use": {
        "label": "自然细节调用",
        "question": "关键细节是否服务于心理理解，而不是机械背日志。",
        "score_0": "堆砌细节、编造细节，或完全没有用细节理解用户状态。",
        "score_1": "用少量细节但服务判断不足，或连接较弱。",
        "score_2": "只调用必要细节，并服务情绪、边界或下一步判断。",
    },
    "memory_misuse": {
        "label": "记忆误用",
        "question": "是否错误调用过期、无关或不存在的记忆，或在不该调用时乱调用。",
        "score_0": "错误调用过期、无关、不存在或不可读记忆，或编造用户没说过的信息。",
        "score_1": "轻微过度复述、边界说明不足，或记忆调用和当前判断关系弱。",
        "score_2": "克制调用，知道何时不调用，并清楚区分已知、推测和不可补空白。",
    },
}


FLAG_NAMES = [
    "memory_absence",
    "memory_misuse",
    "memory_overuse",
    "fabrication",
    "alienation",
    "instruction_only_success",
    "alienation_error",
    "asks_user_to_repeat_context",
    "generic_comfort",
    "fabricated_detail",
    "mechanical_recall",
]


class LLMJudgeError(RuntimeError):
    """Raised when the judge request path cannot produce reliable scores."""

    def __init__(self, message: str, diagnostic: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic or {}


class LLMJudgeRequestError(LLMJudgeError):
    """Raised when the judge API request fails after retries."""


class LLMJudgeOutputError(LLMJudgeError):
    """Raised when the judge response cannot be parsed after retries."""


STRICT_SCORING_CONTRACT = {
    "scoring_posture": [
        "从 0 分开始加证据，不要从满分开始找缺点。",
        "2 分是强证据满分，不是方向正确分；方向正确但证据不足通常只能给 1 分。",
        "1 分代表部分识别但未充分转化为回应策略；2 分只给明确、有证据、服务当前判断的回答。",
        "如果回答可以几乎原样复制给另一个有相同表面问题的用户，相关维度最高 1 分。",
        "如果 evidence_quote 不能直接支持该维度 reason，相关维度最高 1 分。",
    ],
    "score_caps": [
        "没有 assistant_answer 原文证据的维度必须给 0 分。",
        "只复述用户问题，没有新增心理推断，hidden_intent_recognition 最高 1 分。",
        "只说焦虑、累、担心等泛化情绪词，emotional_state_recognition 最高 1 分。",
        "没有调用 case.allowed_context.recent_dialogue 或 case.memory_condition.available_memory_excerpt 中的具体前文或共同处理方式，shared_context_invocation 最高 1 分。",
        "没有明显陌生化错误只能得到 alienation_error_rate 1 分；必须有关系连续性证据才可给 2 分。",
        "只使用当前用户问题里的明显词语，而没有调用可验证背景细节，natural_detail_use 最高 1 分。",
        "没有明确区分已知/推测/不可补空白，memory_misuse 最高 1 分。",
        "出现编造事实、要求用户重讲已给背景、客服化称呼或机械背诵，相关维度最高 0 分，并标记对应 flag。",
    ],
    "calibration_examples": [
        "普通但可用的建议通常是 40-60 分，不应自动给 80 分以上。",
        "能识别潜台词但缺少上下文或关系证据，通常只能给 1 分。",
        "只有同时满足心理推断、关系位置、可验证语境和具体回应策略，相关维度才给 2 分。",
    ],
    "failure_type_taxonomy": {
        "memory_absence": "该接上旧语境时没有接上。",
        "memory_misuse": "调用了错误、过期、无关或不可读记忆。",
        "memory_overuse": "为了显得记得而机械堆细节。",
        "fabrication": "补出用户没有说过的信息。",
        "alienation": "客服化、陌生化、过度角色化或过度亲密。",
        "instruction_only_success": "只是服从当前显性指令，没有依赖长期记忆。",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def preflight_llm_judge(
    *,
    client: Any,
    llm_config: LLMConfig,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Run a tiny JSON-mode request so API/network failures fail before scoring."""
    try:
        output = request_llm_judgement(
            client=client,
            llm_config=llm_config,
            judge_case={
                "case_id": "preflight",
                "instruction": "只返回一个 JSON object，字段 ok 必须为 true。",
            },
            max_output_tokens=64,
            timeout_seconds=timeout_seconds,
        )
    except LLMJudgeError:
        raise
    except Exception as exc:
        diagnostic = describe_llm_exception(exc)
        raise LLMJudgeRequestError(
            "LLM judge preflight failed: " + summarize_llm_diagnostic(diagnostic),
            diagnostic,
        ) from exc

    try:
        parsed = parse_judge_output(output)
    except (json.JSONDecodeError, ValueError) as exc:
        diagnostic = {
            "error_type": type(exc).__name__,
            "message": str(exc),
            "raw_output_excerpt": _truncate(output, ERROR_TEXT_LIMIT),
            "classification": "invalid_response",
        }
        raise LLMJudgeOutputError(
            "LLM judge preflight returned invalid output: "
            + summarize_llm_diagnostic(diagnostic),
            diagnostic,
        ) from exc

    if not isinstance(parsed, dict):
        diagnostic = {
            "error_type": "InvalidPreflightOutput",
            "message": "preflight output is not a JSON object",
            "raw_output_excerpt": _truncate(output, ERROR_TEXT_LIMIT),
            "classification": "invalid_response",
        }
        raise LLMJudgeOutputError(
            "LLM judge preflight returned invalid output: "
            + summarize_llm_diagnostic(diagnostic),
            diagnostic,
        )
    return {
        "status": "ok",
        "provider": llm_config.provider,
        "base_url": llm_config.base_url,
        "model": llm_config.model,
        "output_excerpt": _truncate(output, 300),
    }


def evaluate_files_with_llm_judge(
    *,
    conversation_log_path: Path,
    output_json_path: Path,
    output_markdown_path: Path | None,
    client: Any,
    llm_config: LLMConfig,
    limit: int | None = None,
    message_id: str | None = None,
    variants: list[str] | None = None,
    context_turns: int = 999,
    max_answer_chars: int = 6000,
    max_context_answer_chars: int = 1200,
    max_output_tokens: int = 4096,
    timeout_seconds: float = 120.0,
    print_progress: bool = False,
    judge_workers: int = 1,
    allow_partial_failures: bool = False,
) -> dict[str, Any]:
    evaluation = evaluate_tom_quality_with_llm_judge(
        conversation_log=load_json(conversation_log_path),
        client=client,
        llm_config=llm_config,
        limit=limit,
        message_id=message_id,
        variants=variants,
        context_turns=context_turns,
        max_answer_chars=max_answer_chars,
        max_context_answer_chars=max_context_answer_chars,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        print_progress=print_progress,
        judge_workers=judge_workers,
        allow_partial_failures=allow_partial_failures,
    )
    write_json(output_json_path, evaluation)
    if output_markdown_path:
        output_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        output_markdown_path.write_text(
            render_markdown_report(evaluation),
            encoding="utf-8",
        )
    return evaluation


def evaluate_tom_quality_with_llm_judge(
    *,
    conversation_log: dict[str, Any],
    client: Any,
    llm_config: LLMConfig,
    limit: int | None = None,
    message_id: str | None = None,
    variants: list[str] | None = None,
    context_turns: int = 999,
    max_answer_chars: int = 6000,
    max_context_answer_chars: int = 1200,
    max_output_tokens: int = 4096,
    timeout_seconds: float = 120.0,
    print_progress: bool = False,
    judge_workers: int = 1,
    allow_partial_failures: bool = False,
) -> dict[str, Any]:
    turns = conversation_log.get("turns", [])
    if not isinstance(turns, list):
        raise ValueError("conversation log must contain a turns list")

    selected_variants = set(variants or [])
    judge_workers = max(1, int(judge_workers))
    judge_tasks = []

    for turn_position, turn in enumerate(turns):
        message = turn.get("input", {})
        dimensions = _active_tom_dimensions(message.get("tom_dimensions", []))
        current_message_id = str(turn.get("source", {}).get("message_id") or "")
        if not dimensions:
            continue
        if message_id and current_message_id != message_id:
            continue

        for variant_name, variant in sorted(turn.get("variants", {}).items()):
            if selected_variants and variant_name not in selected_variants:
                continue
            if limit is not None and len(judge_tasks) >= limit:
                break

            judge_case = build_judge_case(
                turns=turns,
                turn_position=turn_position,
                variant_name=variant_name,
                context_turns=context_turns,
                max_answer_chars=max_answer_chars,
                max_context_answer_chars=max_context_answer_chars,
            )
            judge_tasks.append(
                {
                    "case_index": len(judge_tasks) + 1,
                    "turn_position": turn_position,
                    "message_id": current_message_id,
                    "variant_name": variant_name,
                    "dimensions": dimensions,
                    "judge_case": judge_case,
                }
            )
        if limit is not None and len(judge_tasks) >= limit:
            break

    judged_items = _run_judge_tasks(
        judge_tasks=judge_tasks,
        client=client,
        llm_config=llm_config,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        print_progress=print_progress,
        judge_workers=judge_workers,
        allow_partial_failures=allow_partial_failures,
    )

    aggregate: dict[str, Any] = {}
    evaluated_turns_by_position: dict[int, dict[str, Any]] = {}
    for item in sorted(judged_items, key=lambda result: result["case_index"]):
        turn_position = int(item["turn_position"])
        variant_name = str(item["variant_name"])
        normalized = item["normalized"]
        turn_result = evaluated_turns_by_position.setdefault(
            turn_position,
            _build_turn_result(turns[turn_position]),
        )
        turn_result["variants"][variant_name] = normalized
        _update_aggregate(aggregate, variant_name, normalized)

    evaluated_turns = [
        evaluated_turns_by_position[position]
        for position in sorted(evaluated_turns_by_position)
        if evaluated_turns_by_position[position]["variants"]
    ]
    summary = _build_summary(aggregate)
    summary["persona_variance"] = _persona_score_stats(evaluated_turns)
    enrich_lowest_examples(summary=summary, turns=evaluated_turns)
    return {
        "schema_version": "tom_quality_llm_judge_v0.3",
        "method": {
            "name": "llm_as_judge_tom_quality_evaluator",
            "strictness": "strict_v0.3",
            "description": (
                "LLM-as-judge ToM evaluator. It uses structured, blind per-answer "
                "judgement over targeted probe turns. Rule-based scoring remains a "
                "separate diagnostic layer and is not used as the primary score here."
            ),
            "judge_provider": llm_config.provider,
            "judge_base_url": llm_config.base_url,
            "judge_model": llm_config.model,
            "quality_standard": list(TOM_DIMENSION_RUBRIC),
            "score_scale": (
                "Strict 0-2 scale. 0 means failure, 1 means partial recognition, "
                "and 2 requires explicit answer evidence plus a response strategy "
                "grounded in allowed case context."
            ),
            "failure_type_taxonomy": list(FAILURE_TYPES),
            "blind_review": "The judge prompt does not reveal whether the answer came from M0, M1, M2, or M3.",
            "gold_label_policy": "Judge cases exclude BEI, gold strategies, high-score behavior, and low-score behavior.",
            "judge_workers": judge_workers,
            "allow_partial_failures": allow_partial_failures,
        },
        "summary": summary,
        "turns": evaluated_turns,
    }


def _build_turn_result(turn: dict[str, Any]) -> dict[str, Any]:
    message = turn.get("input", {})
    return {
        "turn_index": turn.get("turn_index"),
        "message_id": str(turn.get("source", {}).get("message_id") or ""),
        "day": message.get("day"),
        "probe_type": message.get("probe_type"),
        "topic": message.get("topic"),
        "user_message": message.get("user_message"),
        "tom_dimensions": _active_tom_dimensions(message.get("tom_dimensions", [])),
        "required_memory_type": list(message.get("required_memory_type", [])),
        "dependency_analysis": dict(message.get("dependency_analysis", {})),
        "variants": {},
    }


def _active_tom_dimensions(dimensions: Any) -> list[str]:
    return [
        str(item)
        for item in dimensions or []
        if str(item) in TOM_DIMENSION_RUBRIC
    ]


def _run_judge_tasks(
    *,
    judge_tasks: list[dict[str, Any]],
    client: Any,
    llm_config: LLMConfig,
    max_output_tokens: int,
    timeout_seconds: float,
    print_progress: bool,
    judge_workers: int,
    allow_partial_failures: bool,
) -> list[dict[str, Any]]:
    if judge_workers <= 1:
        return [
            _run_one_judge_task(
                task=task,
                client=client,
                llm_config=llm_config,
                max_output_tokens=max_output_tokens,
                timeout_seconds=timeout_seconds,
                print_progress=print_progress,
                total_cases=len(judge_tasks),
                allow_partial_failures=allow_partial_failures,
            )
            for task in judge_tasks
        ]

    completed: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=judge_workers) as executor:
        futures = [
            executor.submit(
                _run_one_judge_task,
                task=task,
                client=client,
                llm_config=llm_config,
                max_output_tokens=max_output_tokens,
                timeout_seconds=timeout_seconds,
                print_progress=print_progress,
                total_cases=len(judge_tasks),
                allow_partial_failures=allow_partial_failures,
            )
            for task in judge_tasks
        ]
        for future in as_completed(futures):
            completed.append(future.result())
    return completed


def _run_one_judge_task(
    *,
    task: dict[str, Any],
    client: Any,
    llm_config: LLMConfig,
    max_output_tokens: int,
    timeout_seconds: float,
    print_progress: bool,
    total_cases: int,
    allow_partial_failures: bool,
) -> dict[str, Any]:
    if print_progress:
        print(
            "[judge] "
            f"case={task['case_index']}/{total_cases} "
            f"message_id={task['message_id']} "
            f"variant={task['variant_name']}",
            flush=True,
        )
    raw_output, judgement = request_parseable_llm_judgement(
        client=client,
        llm_config=llm_config,
        judge_case=task["judge_case"],
        dimensions=task["dimensions"],
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        allow_partial_failures=allow_partial_failures,
    )
    normalized = normalize_judgement(
        judgement=judgement,
        dimensions=task["dimensions"],
        raw_output=raw_output,
    )
    return {
        **task,
        "normalized": normalized,
    }


def build_judge_case(
    *,
    turns: list[dict[str, Any]],
    turn_position: int,
    variant_name: str,
    context_turns: int,
    max_answer_chars: int,
    max_context_answer_chars: int,
) -> dict[str, Any]:
    turn = turns[turn_position]
    message = turn.get("input", {})
    source = turn.get("source", {})
    variant_payload = turn.get("variants", {}).get(variant_name, {})
    answer = str(variant_payload.get("assistant_answer", ""))
    dimensions = _active_tom_dimensions(message.get("tom_dimensions", []))
    return {
        "case_id": source.get("message_id"),
        "day": message.get("day"),
        "topic": message.get("topic"),
        "probe_type": message.get("probe_type"),
        "user_message": message.get("user_message"),
        "tom_dimensions": dimensions,
        "probe_metadata": {
            "required_memory_type": list(message.get("required_memory_type", [])),
            "dependency_analysis": dict(message.get("dependency_analysis", {})),
        },
        "blind_condition": _blind_condition_label(variant_name),
        "memory_condition": _memory_condition_summary(variant_payload),
        "rubric": {
            dimension: TOM_DIMENSION_RUBRIC.get(dimension, {"label": dimension})
            for dimension in dimensions
        },
        "strict_scoring_contract": STRICT_SCORING_CONTRACT,
        "allowed_context": {
            "recent_dialogue": _recent_dialogue(
                turns=turns,
                turn_position=turn_position,
                variant_name=variant_name,
                context_turns=context_turns,
                max_context_answer_chars=max_context_answer_chars,
            ),
            "judge_boundary": [
                "只能依据本 case 提供的用户问题、近期对话、可读记忆条件说明和 assistant_answer 评分。",
                "不要根据未提供的长期历史脑补事实。",
                "不要使用未提供的 BEI、gold strategy 或高低分答案标签，因为本 case 不提供这些 gold label。",
                "不要因为回答更长、格式更整齐或更会安慰就自动给高分。",
                "如果回答编造了用户没有说过的具体事实，应标记 fabrication。",
            ],
        },
        "assistant_answer": _truncate(answer, max_answer_chars),
    }


def _blind_condition_label(variant_name: str) -> str:
    labels = {
        "M0": "Condition A",
        "M1": "Condition B",
        "M2": "Condition C",
        "M3": "Condition D",
    }
    return labels.get(str(variant_name), "Condition X")


def _memory_condition_summary(variant_payload: dict[str, Any]) -> dict[str, Any]:
    payload = (
        variant_payload.get("memory_payload")
        or variant_payload.get("memory_context")
        or variant_payload.get("prompt_memory")
        or {}
    )
    if isinstance(payload, str):
        return {
            "readable_memory_boundary": "",
            "available_memory_excerpt": _sanitize_condition_text(_truncate(payload, 1800)),
        }
    if not isinstance(payload, dict):
        return {"readable_memory_boundary": "", "available_memory_excerpt": ""}

    boundary_keys = [
        "condition_description",
        "readable_memory",
        "allowed_memory",
        "cannot_read",
        "forbidden_memory",
        "memory_boundary",
        "policy",
    ]
    excerpt_keys = [
        "memory_context",
        "memory_text",
        "summary",
        "event_memory",
        "relational_anchor_memory",
        "payload",
    ]
    boundary = {
        key: payload.get(key)
        for key in boundary_keys
        if key in payload and payload.get(key) not in (None, "")
    }
    excerpt_parts = [
        payload.get(key)
        for key in excerpt_keys
        if key in payload and payload.get(key) not in (None, "")
    ]
    if not excerpt_parts and payload:
        excerpt_parts = [payload]
    return {
        "readable_memory_boundary": _sanitize_condition_text(
            _truncate(json.dumps(boundary, ensure_ascii=False, sort_keys=True), 1200)
        )
        if boundary
        else "",
        "available_memory_excerpt": _sanitize_condition_text(
            _truncate(json.dumps(excerpt_parts, ensure_ascii=False, sort_keys=True), 2200)
        )
        if excerpt_parts
        else "",
    }


def _sanitize_condition_text(text: str) -> str:
    replacements = {
        "M0": "Condition A",
        "M1": "Condition B",
        "M2": "Condition C",
        "M3": "Condition D",
        "Generic Agent Memory Baseline": "Condition A",
        "Conclusion-level Relational Memory": "Condition B",
        "Summary-level Relational Memory": "Condition C",
        "Detail-level / Relational Anchor Memory": "Condition D",
    }
    sanitized = str(text)
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target)
    return sanitized


def request_llm_judgement(
    *,
    client: Any,
    llm_config: LLMConfig,
    judge_case: dict[str, Any],
    max_output_tokens: int,
    timeout_seconds: float,
) -> str:
    request_client = client.with_options(max_retries=0, timeout=timeout_seconds)
    request_kwargs = {
        "model": llm_config.model,
        "messages": [
            {"role": "system", "content": _judge_system_prompt()},
            {"role": "user", "content": json.dumps(judge_case, ensure_ascii=False)},
        ],
        "temperature": 0,
        "max_tokens": max_output_tokens,
        "response_format": {"type": "json_object"},
    }
    completion = request_client.chat.completions.create(**request_kwargs)
    return completion.choices[0].message.content or ""


def request_parseable_llm_judgement(
    *,
    client: Any,
    llm_config: LLMConfig,
    judge_case: dict[str, Any],
    dimensions: list[str],
    max_output_tokens: int,
    timeout_seconds: float,
    allow_partial_failures: bool = False,
) -> tuple[str, dict[str, Any]]:
    last_output = ""
    last_diagnostic: dict[str, Any] = {}
    for attempt in range(4):
        try:
            last_output = request_llm_judgement(
                client=client,
                llm_config=llm_config,
                judge_case=judge_case,
                max_output_tokens=max_output_tokens,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            last_diagnostic = describe_llm_exception(exc)
            if attempt < 3:
                time.sleep(2.0 * (attempt + 1))
                continue
            message = "judge 请求失败：" + summarize_llm_diagnostic(last_diagnostic)
            if not allow_partial_failures:
                raise LLMJudgeRequestError(message, last_diagnostic) from exc
            return message, _fallback_parse_error_judgement(
                dimensions=dimensions,
                reason=message,
                judge_status="request_error",
                judge_error=last_diagnostic,
            )
        try:
            return last_output, parse_judge_output(last_output)
        except (json.JSONDecodeError, ValueError) as exc:
            last_diagnostic = {
                "error_type": type(exc).__name__,
                "message": str(exc),
                "raw_output_excerpt": _truncate(last_output, ERROR_TEXT_LIMIT),
                "classification": "invalid_response",
            }
            continue
    message = "judge 输出不是可解析 JSON：" + summarize_llm_diagnostic(last_diagnostic)
    if not allow_partial_failures:
        raise LLMJudgeOutputError(message, last_diagnostic)
    return last_output, _fallback_parse_error_judgement(
        dimensions=dimensions,
        reason=message,
        judge_status="parse_error",
        judge_error=last_diagnostic,
    )


def parse_judge_output(raw_output: str) -> dict[str, Any]:
    text = raw_output.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError(f"Judge output is not JSON: {raw_output[:500]}")
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("Judge output must be a JSON object")
    return parsed


def describe_llm_exception(exc: BaseException) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {
        "error_type": type(exc).__name__,
        "message": str(exc),
    }
    for attr in ("status_code", "code", "type", "param", "request_id"):
        if hasattr(exc, attr):
            value = getattr(exc, attr)
            if value is not None:
                diagnostic[attr if attr != "type" else "api_error_type"] = value

    response = getattr(exc, "response", None)
    if response is not None:
        response_info: dict[str, Any] = {}
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            response_info["status_code"] = status_code
            diagnostic.setdefault("status_code", status_code)
        headers = dict(getattr(response, "headers", {}) or {})
        safe_headers = {
            key: value
            for key, value in headers.items()
            if key.lower() in {"content-type", "x-request-id", "cf-ray", "server"}
        }
        if safe_headers:
            response_info["headers"] = safe_headers
        try:
            response_info["text_excerpt"] = _truncate(response.text, ERROR_TEXT_LIMIT)
        except Exception as inner:  # pragma: no cover - defensive for SDK variants.
            response_info["text_error"] = repr(inner)
        diagnostic["response"] = response_info

    body = getattr(exc, "body", None)
    if body is not None:
        diagnostic["body_excerpt"] = _truncate(repr(body), ERROR_TEXT_LIMIT)

    causes = []
    seen: set[int] = set()
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    while cause is not None and id(cause) not in seen and len(causes) < 6:
        seen.add(id(cause))
        causes.append(
            {
                "error_type": type(cause).__name__,
                "message": str(cause),
            }
        )
        cause = getattr(cause, "__cause__", None) or getattr(cause, "__context__", None)
    if causes:
        diagnostic["causes"] = causes

    diagnostic["classification"] = classify_llm_diagnostic(diagnostic)
    return diagnostic


def classify_llm_diagnostic(diagnostic: dict[str, Any]) -> str:
    status = diagnostic.get("status_code")
    response = diagnostic.get("response", {})
    if status is None and isinstance(response, dict):
        status = response.get("status_code")
    text_parts = [
        str(diagnostic.get("message", "")),
        str(diagnostic.get("body_excerpt", "")),
    ]
    if isinstance(response, dict):
        text_parts.append(str(response.get("text_excerpt", "")))
    for cause in diagnostic.get("causes", []):
        if isinstance(cause, dict):
            text_parts.append(str(cause.get("error_type", "")))
            text_parts.append(str(cause.get("message", "")))
    text = " ".join(text_parts).lower()

    if status in (401, 403):
        return "authentication_or_permission"
    if status == 402 or any(word in text for word in ("insufficient", "balance", "quota")):
        return "quota_or_balance"
    if status == 429:
        return "rate_limit_or_quota"
    if "gaierror" in text or "nodename nor servname" in text or "name resolution" in text:
        return "dns_resolution"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "connection" in text or "connecterror" in text or "connect error" in text:
        return "connection_error"
    if status is not None:
        return "http_error"
    return "unknown"


def summarize_llm_diagnostic(diagnostic: dict[str, Any]) -> str:
    parts = [
        f"classification={diagnostic.get('classification', 'unknown')}",
        f"type={diagnostic.get('error_type', 'unknown')}",
    ]
    if diagnostic.get("status_code") is not None:
        parts.append(f"status={diagnostic['status_code']}")
    if diagnostic.get("message"):
        parts.append("message=" + _truncate(str(diagnostic["message"]), 220))
    causes = diagnostic.get("causes", [])
    if causes and isinstance(causes[0], dict):
        parts.append(
            "root_cause="
            + _truncate(
                f"{causes[-1].get('error_type')}: {causes[-1].get('message')}",
                220,
            )
        )
    response = diagnostic.get("response", {})
    if isinstance(response, dict) and response.get("text_excerpt"):
        parts.append("response=" + _truncate(str(response["text_excerpt"]), 300))
    return "; ".join(parts)


def _fallback_parse_error_judgement(
    *,
    dimensions: list[str],
    reason: str = "judge 输出不是可解析 JSON",
    judge_status: str = "parse_error",
    judge_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "judge_status": judge_status,
        "judge_error": judge_error or {},
        "dimension_scores": {
            dimension: {
                "score": 0,
                "evidence_quote": "",
                "reason": f"{reason}，本 case 进入人工复核。",
            }
            for dimension in dimensions
        },
        "flags": {
            name: False for name in FLAG_NAMES
        },
        "failure_types": [],
        "overall_reason": f"{reason}，本 case 不作为可靠自动评分，应人工复核。",
        "confidence": 0.0,
        "needs_human_review": True,
        "answer_excerpt": "",
    }



def normalize_judgement(
    *,
    judgement: dict[str, Any],
    dimensions: list[str],
    raw_output: str,
) -> dict[str, Any]:
    dimension_scores = {}
    raw_dimension_scores = judgement.get("dimension_scores", {})
    if not isinstance(raw_dimension_scores, dict):
        raw_dimension_scores = {}
    flags = _normalize_flags(judgement.get("flags", {}))
    failure_types = _normalize_failure_types(
        raw_failure_types=judgement.get("failure_types", []),
        flags=flags,
    )
    flags = _merge_failure_types_into_flags(flags=flags, failure_types=failure_types)

    for dimension in dimensions:
        raw_item = raw_dimension_scores.get(dimension, {})
        if not isinstance(raw_item, dict):
            raw_item = {}
        raw_score = _coerce_score(raw_item.get("score"))
        evidence_quote = str(raw_item.get("evidence_quote", ""))
        score, strict_adjustments = _apply_strict_caps(
            dimension=dimension,
            raw_score=raw_score,
            evidence_quote=evidence_quote,
            flags=flags,
        )
        dimension_scores[dimension] = {
            "score": score,
            "raw_score": raw_score,
            "max_score": MAX_DIMENSION_SCORE,
            "evidence_quote": evidence_quote,
            "reason": str(raw_item.get("reason", "")),
            "strict_adjustments": strict_adjustments,
        }

    average_score = (
        sum(item["score"] for item in dimension_scores.values()) / len(dimension_scores)
        if dimension_scores
        else 0.0
    )
    computed_tom_score = round((average_score / MAX_DIMENSION_SCORE) * 100.0, 2)
    confidence = _coerce_confidence(judgement.get("confidence"))
    judge_status = str(judgement.get("judge_status") or "ok")
    is_valid_judge_result = judge_status == "ok"
    needs_human_review = bool(
        judgement.get("needs_human_review", False)
        or confidence < 0.55
        or any(flags.values())
        or bool(failure_types)
        or not is_valid_judge_result
    )
    return {
        "tom_score": computed_tom_score,
        "judge_status": judge_status,
        "is_valid_judge_result": is_valid_judge_result,
        "judge_error": judgement.get("judge_error", {}),
        "dimension_scores": dimension_scores,
        "flags": flags,
        "failure_types": failure_types,
        "overall_reason": str(judgement.get("overall_reason", "")),
        "confidence": confidence,
        "needs_human_review": needs_human_review,
        "answer_excerpt": str(judgement.get("answer_excerpt", ""))[:300],
        "raw_model_output": raw_output,
    }


def render_markdown_report(evaluation: dict[str, Any]) -> str:
    summary = evaluation.get("summary", {})
    lines = [
        "# ToM LLM Judge Evaluation",
        "",
        "This is the primary strict LLM-as-judge ToM report. Rule-based scoring is a diagnostic layer only.",
        "",
        "## Summary",
        "",
        "| Variant | Probe answers | Valid judge | Invalid judge | Avg ToM score | Avg confidence | Human review | Flags |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant_name, item in sorted(summary.get("variants", {}).items()):
        lines.append(
            "| {variant} | {turns} | {valid} | {invalid} | {score:.1f} | {confidence:.2f} | {review} | {flags} |".format(
                variant=variant_name,
                turns=item["turn_count"],
                valid=item.get("valid_judge_count", item["turn_count"]),
                invalid=item.get("invalid_judge_count", 0),
                score=item["average_tom_score"],
                confidence=item["average_confidence"],
                review=item["needs_human_review_count"],
                flags=item["flag_count"],
            )
        )

    lines.extend(["", "## Dimension Averages", ""])
    dimension_names = sorted(
        {
            dimension
            for item in summary.get("dimension_averages", {}).values()
            for dimension in item
        }
    )
    if dimension_names:
        lines.append("| Variant | " + " | ".join(dimension_names) + " |")
        lines.append("|---" + "|---:" * len(dimension_names) + "|")
        for variant_name, item in sorted(summary.get("dimension_averages", {}).items()):
            lines.append(
                "| "
                + variant_name
                + " | "
                + " | ".join(f"{item.get(name, 0.0):.2f}" for name in dimension_names)
                + " |"
            )

    persona_variance = summary.get("persona_variance") or _persona_score_stats(
        evaluation.get("turns", [])
    )
    lines.extend(["", "## Persona Variance", ""])
    if persona_variance:
        lines.append(
            "| Variant | Persona count | Persona means | Mean | Variance | Std dev | Range | CV | Norm var | Norm range | M0 var reduction |"
        )
        lines.append("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for variant_name, item in sorted(persona_variance.items()):
            persona_means = item.get("persona_means", {})
            means_text = "; ".join(
                f"{pid}={float(score):.2f}"
                for pid, score in sorted(persona_means.items())
            )
            lines.append(
                "| {variant} | {count} | {means} | {mean:.2f} | {variance:.2f} | {stddev:.2f} | {range_value:.2f} | {cv:.3f} | {norm_variance:.3f} | {norm_range:.3f} | {m0_reduction:.1%} |".format(
                    variant=variant_name,
                    count=int(item.get("persona_count", 0)),
                    means=_clean_markdown_cell(means_text or "-"),
                    mean=float(item.get("mean", 0.0)),
                    variance=float(item.get("variance", 0.0)),
                    stddev=float(item.get("stddev", 0.0)),
                    range_value=float(item.get("range", 0.0)),
                    cv=float(item.get("cv", 0.0)),
                    norm_variance=float(item.get("norm_variance", 0.0)),
                    norm_range=float(item.get("norm_range", 0.0)),
                    m0_reduction=float(item.get("m0_variance_reduction", 0.0)),
                )
            )
        lines.append("")
        lines.append(
            "Variance is computed across persona-level average ToM scores within this report "
            "(population variance, not cross-experiment variance). "
            "`Norm var` is variance / 2500, because 2500 is the maximum population variance "
            "on a 0-100 score scale. `M0 var reduction` is positive when the condition is "
            "more even across personas than M0 in the same report."
        )
    else:
        lines.append("No persona-level score data.")

    lines.extend(["", "## Failure Types", ""])
    failure_type_names = sorted(
        {
            failure_type
            for item in summary.get("variants", {}).values()
            for failure_type in item.get("failure_type_counts", {})
        }
    )
    if failure_type_names:
        lines.append("| Variant | " + " | ".join(failure_type_names) + " |")
        lines.append("|---" + "|---:" * len(failure_type_names) + "|")
        for variant_name, item in sorted(summary.get("variants", {}).items()):
            counts = item.get("failure_type_counts", {})
            lines.append(
                "| "
                + variant_name
                + " | "
                + " | ".join(str(counts.get(name, 0)) for name in failure_type_names)
                + " |"
            )
    else:
        lines.append("No failure types marked.")

    lines.extend(["", "## Lowest Scoring Examples", ""])
    examples = summary.get("lowest_scoring_examples", [])
    if not examples:
        lines.append("No judged examples.")
    else:
        for example in examples[:10]:
            lines.append(
                "- `{variant}` `{message_id}` score={score:.1f} confidence={confidence:.2f}: {reason}".format(
                    variant=example["variant"],
                    message_id=example["message_id"],
                    score=example["tom_score"],
                    confidence=example["confidence"],
                    reason=example["overall_reason"],
                )
            )

    lines.append("")
    return "\n".join(lines)


def _judge_system_prompt() -> str:
    return "\n".join(
        [
            "你是长程关系记忆实验中的 ToM 评审员，不是对话助手。",
            "你的任务是评价 assistant_answer 是否理解用户的心理状态、隐含意图、共同语境、自然细节使用和记忆边界。",
            "你只能依据用户提供的 case JSON 评分，不要脑补未提供的长期历史。",
            "case 使用盲化条件名 Condition A/B/C/D；不要尝试反推出 M0/M1/M2/M3。",
            "case 不提供 BEI、gold label 或高低分答案标签；不得把这些当评分依据。",
            "你必须严格评分。默认从 0 分开始，只有 assistant_answer 中有明确证据时才加分。",
            "每个维度使用 0-2 分：0=失败，1=部分识别，2=明确识别并转化为回应策略。",
            "2 分是强证据满分，不是方向正确分。普通、可用、礼貌、能安慰的回答通常只能得 1 分。",
            "不要因为回答更长、格式更整齐、语气更热情或安慰更多就给高分。",
            "不要因为回答最终建议看起来合理就给高分；ToM 分数看的是心理推断、可验证共同语境、自然细节和记忆边界。",
            "如果回答可以几乎原样复制给另一个有相同表面问题的用户，相关维度最高 1 分。",
            "如果回答只复述用户问题，没有形成新的心理判断，相关维度最高 1 分。",
            "shared_context_invocation 和 natural_detail_use 的 2 分必须有 case.allowed_context.recent_dialogue 或 case.memory_condition 中可验证的具体前文证据。",
            "alienation_error_rate 不是无错误就满分：无明显错误但缺少关系连续性证据，只能给 1 分。",
            "memory_misuse 维度要判断回答是否克制、是否区分已知/推测/不可补空白，是否调用了错误或不可读记忆。",
            "必须按 case.tom_dimensions 中列出的维度逐项评分，每个维度只能给 0、1、2。",
            "必须为每个维度引用 assistant_answer 中的短证据；如果没有证据，evidence_quote 置为空字符串。",
            "请用 failure_types 标记失败类型，可选值只能是 memory_absence、memory_misuse、memory_overuse、fabrication、alienation、instruction_only_success。",
            "如果回答要求用户重新解释已提供背景、使用客服化/过度亲密称呼、泛化安慰、编造细节或机械背诵，请在 failure_types 中标记。",
            "输出必须是一个 JSON object，不要 Markdown，不要额外说明。",
            "JSON schema:",
            "{",
            '  "dimension_scores": {',
            '    "<dimension_id>": {"score": 0, "evidence_quote": "", "reason": ""}',
            "  },",
            '  "failure_types": [],',
            '  "flags": {',
            '    "memory_absence": false,',
            '    "memory_misuse": false,',
            '    "memory_overuse": false,',
            '    "fabrication": false,',
            '    "alienation": false,',
            '    "instruction_only_success": false',
            "  },",
            '  "overall_reason": "",',
            '  "confidence": 0.0,',
            '  "needs_human_review": false,',
            '  "answer_excerpt": ""',
            "}",
        ]
    )


def _recent_dialogue(
    *,
    turns: list[dict[str, Any]],
    turn_position: int,
    variant_name: str,
    context_turns: int,
    max_context_answer_chars: int,
) -> list[dict[str, str]]:
    start = max(0, turn_position - max(context_turns, 0))
    recent = []
    for turn in turns[start:turn_position]:
        variant = turn.get("variants", {}).get(variant_name, {})
        answer = variant.get("assistant_answer")
        if answer is None:
            continue
        message = turn.get("input", {})
        recent.append(
            {
                "message_id": str(turn.get("source", {}).get("message_id", "")),
                "turn_type": str(turn.get("source", {}).get("turn_type", "")),
                "user_message": _truncate(str(message.get("user_message", "")), 900),
                "assistant_answer": _truncate(str(answer), max_context_answer_chars),
            }
        )
    return recent


def _update_aggregate(
    aggregate: dict[str, Any],
    variant_name: str,
    judged_result: dict[str, Any],
) -> None:
    item = aggregate.setdefault(
        variant_name,
        {
            "turn_count": 0,
            "valid_judge_count": 0,
            "invalid_judge_count": 0,
            "judge_status_counts": defaultdict(int),
            "tom_score_sum": 0.0,
            "confidence_sum": 0.0,
            "needs_human_review_count": 0,
            "flag_count": 0,
            "flag_counts": defaultdict(int),
            "failure_type_counts": defaultdict(int),
            "dimension_score_sums": defaultdict(float),
            "dimension_counts": defaultdict(int),
        },
    )
    item["turn_count"] += 1
    judge_status = str(judged_result.get("judge_status") or "ok")
    item["judge_status_counts"][judge_status] += 1
    is_valid = bool(judged_result.get("is_valid_judge_result", True))
    if is_valid:
        item["valid_judge_count"] += 1
        item["tom_score_sum"] += judged_result["tom_score"]
        item["confidence_sum"] += judged_result["confidence"]
    else:
        item["invalid_judge_count"] += 1
    item["needs_human_review_count"] += int(bool(judged_result["needs_human_review"]))
    for flag_name, enabled in judged_result["flags"].items():
        if enabled:
            item["flag_count"] += 1
            item["flag_counts"][flag_name] += 1
    for failure_type in judged_result.get("failure_types", []):
        item["failure_type_counts"][failure_type] += 1
    for dimension, result in judged_result["dimension_scores"].items():
        if not is_valid:
            continue
        item["dimension_score_sums"][dimension] += result["score"]
        item["dimension_counts"][dimension] += 1


def _build_summary(aggregate: dict[str, Any]) -> dict[str, Any]:
    variants = {}
    dimension_averages = {}
    for variant_name, item in aggregate.items():
        turn_count = item["turn_count"]
        valid_judge_count = item["valid_judge_count"]
        variants[variant_name] = {
            "turn_count": turn_count,
            "valid_judge_count": valid_judge_count,
            "invalid_judge_count": item["invalid_judge_count"],
            "judge_status_counts": dict(sorted(item["judge_status_counts"].items())),
            "average_tom_score": round(
                item["tom_score_sum"] / valid_judge_count if valid_judge_count else 0.0,
                2,
            ),
            "average_confidence": round(
                item["confidence_sum"] / valid_judge_count if valid_judge_count else 0.0,
                3,
            ),
            "needs_human_review_count": item["needs_human_review_count"],
            "flag_count": item["flag_count"],
            "flag_counts": dict(sorted(item["flag_counts"].items())),
            "failure_type_counts": dict(sorted(item["failure_type_counts"].items())),
        }
        dimension_averages[variant_name] = {
            dimension: round(
                item["dimension_score_sums"][dimension]
                / item["dimension_counts"][dimension],
                2,
            )
            for dimension in sorted(item["dimension_counts"])
        }
    return {
        "variants": variants,
        "dimension_averages": dimension_averages,
        "lowest_scoring_examples": [],
    }


def _persona_score_stats(turns: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    scores_by_variant_persona: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        pid = str(turn.get("message_id", "")).split("_", 1)[0]
        if not pid:
            continue
        variants = turn.get("variants", {})
        if not isinstance(variants, dict):
            continue
        for variant_name, result in variants.items():
            if not isinstance(result, dict):
                continue
            valid = bool(
                result.get(
                    "is_valid_judge_result",
                    result.get("judge_status") == "ok" or "tom_score" in result,
                )
            )
            if not valid:
                continue
            scores_by_variant_persona[str(variant_name)][pid].append(
                float(result.get("tom_score", 0.0))
            )

    stats: dict[str, dict[str, Any]] = {}
    raw_stats: dict[str, dict[str, Any]] = {}
    for variant_name, persona_scores in scores_by_variant_persona.items():
        persona_means = {
            pid: sum(scores) / len(scores)
            for pid, scores in persona_scores.items()
            if scores
        }
        values = list(persona_means.values())
        mean = sum(values) / len(values) if values else 0.0
        variance = (
            sum((value - mean) ** 2 for value in values) / len(values)
            if values
            else 0.0
        )
        raw_stats[variant_name] = {
            "persona_count": len(values),
            "persona_means": {
                pid: round(score, 4)
                for pid, score in sorted(persona_means.items())
            },
            "mean": round(mean, 4),
            "variance": round(variance, 4),
            "stddev": round(variance ** 0.5, 4),
            "range": round((max(values) - min(values)) if values else 0.0, 4),
        }
    m0_variance = float(raw_stats.get("M0", {}).get("variance", 0.0))
    for variant_name, item in raw_stats.items():
        mean = float(item.get("mean", 0.0))
        variance = float(item.get("variance", 0.0))
        stddev = float(item.get("stddev", 0.0))
        range_value = float(item.get("range", 0.0))
        item["cv"] = round(stddev / mean if mean else 0.0, 6)
        item["norm_variance"] = round(min(1.0, max(0.0, variance / 2500.0)), 6)
        item["norm_stddev"] = round(min(1.0, max(0.0, stddev / 50.0)), 6)
        item["norm_range"] = round(min(1.0, max(0.0, range_value / 100.0)), 6)
        item["m0_variance_reduction"] = round(
            (m0_variance - variance) / m0_variance if m0_variance else 0.0,
            6,
        )
        stats[variant_name] = item
    return dict(sorted(stats.items()))


def _clean_markdown_cell(value: Any) -> str:
    text = " ".join(str(value).split())
    return text.replace("|", "\\|")


def enrich_lowest_examples(
    *,
    summary: dict[str, Any],
    turns: list[dict[str, Any]],
) -> None:
    examples = []
    for turn in turns:
        for variant_name, result in turn.get("variants", {}).items():
            examples.append(
                {
                    "message_id": turn.get("message_id"),
                    "variant": variant_name,
                    "tom_score": result.get("tom_score", 0.0),
                    "confidence": result.get("confidence", 0.0),
                    "overall_reason": result.get("overall_reason", ""),
                    "answer_excerpt": result.get("answer_excerpt", ""),
                }
            )
    summary["lowest_scoring_examples"] = sorted(
        examples,
        key=lambda item: (item["tom_score"], item["confidence"], item["variant"]),
    )[:20]


def _normalize_flags(raw_flags: Any) -> dict[str, bool]:
    raw = raw_flags if isinstance(raw_flags, dict) else {}
    return {name: bool(raw.get(name, False)) for name in FLAG_NAMES}


def _normalize_failure_types(
    *,
    raw_failure_types: Any,
    flags: dict[str, bool],
) -> list[str]:
    values: list[str] = []
    if isinstance(raw_failure_types, list):
        values.extend(str(item) for item in raw_failure_types)
    elif isinstance(raw_failure_types, str):
        values.extend(part.strip() for part in raw_failure_types.split(","))

    flag_mapping = {
        "memory_absence": "memory_absence",
        "memory_misuse": "memory_misuse",
        "memory_overuse": "memory_overuse",
        "fabrication": "fabrication",
        "alienation": "alienation",
        "instruction_only_success": "instruction_only_success",
        "asks_user_to_repeat_context": "memory_absence",
        "fabricated_detail": "fabrication",
        "mechanical_recall": "memory_overuse",
        "alienation_error": "alienation",
        "generic_comfort": "instruction_only_success",
    }
    for flag_name, failure_type in flag_mapping.items():
        if flags.get(flag_name, False):
            values.append(failure_type)

    normalized = []
    seen = set()
    for value in values:
        value = str(value).strip()
        if value in FAILURE_TYPES and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def _merge_failure_types_into_flags(
    *,
    flags: dict[str, bool],
    failure_types: list[str],
) -> dict[str, bool]:
    merged = dict(flags)
    for failure_type in failure_types:
        merged[failure_type] = True
    reverse_mapping = {
        "memory_absence": "asks_user_to_repeat_context",
        "memory_overuse": "mechanical_recall",
        "fabrication": "fabricated_detail",
        "alienation": "alienation_error",
        "instruction_only_success": "generic_comfort",
    }
    for failure_type, flag_name in reverse_mapping.items():
        if failure_type in failure_types:
            merged[flag_name] = True
    return {name: bool(merged.get(name, False)) for name in FLAG_NAMES}


def _apply_strict_caps(
    *,
    dimension: str,
    raw_score: int,
    evidence_quote: str,
    flags: dict[str, bool],
) -> tuple[int, list[str]]:
    score = raw_score
    adjustments = []

    if not evidence_quote.strip() and score > 0:
        score = 0
        adjustments.append("missing_dimension_evidence_quote")

    caps: list[tuple[bool, int, str]] = [
        (
            (flags.get("alienation_error", False) or flags.get("alienation", False))
            and dimension == "alienation_error_rate",
            0,
            "alienation_error_flag_cap",
        ),
        (
            (
                flags.get("asks_user_to_repeat_context", False)
                or flags.get("memory_absence", False)
            )
            and dimension in {"shared_context_invocation", "alienation_error_rate"},
            0,
            "asks_user_to_repeat_context_flag_cap",
        ),
        (
            (
                flags.get("fabricated_detail", False)
                or flags.get("fabrication", False)
            )
            and dimension
            in {"natural_detail_use", "shared_context_invocation", "memory_misuse"},
            0,
            "fabricated_detail_flag_cap",
        ),
        (
            flags.get("memory_misuse", False)
            and dimension
            in {"memory_misuse", "natural_detail_use", "shared_context_invocation"},
            0,
            "memory_misuse_flag_cap",
        ),
        (
            (
                flags.get("generic_comfort", False)
                or flags.get("instruction_only_success", False)
            )
            and dimension
            in {"hidden_intent_recognition", "emotional_state_recognition"},
            1,
            "generic_comfort_flag_cap",
        ),
        (
            (
                flags.get("mechanical_recall", False)
                or flags.get("memory_overuse", False)
            )
            and dimension
            in {
                "natural_detail_use",
                "shared_context_invocation",
                "memory_misuse",
            },
            1,
            "mechanical_recall_flag_cap",
        ),
    ]
    for should_apply, cap, reason in caps:
        if should_apply and score > cap:
            score = cap
            adjustments.append(reason)

    return score, adjustments


def _coerce_score(value: Any) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return min(MAX_DIMENSION_SCORE, max(0, numeric))


def _coerce_confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(min(1.0, max(0.0, numeric)), 3)


def _truncate(text: str, max_chars: int) -> str:
    compact = " ".join(str(text).split())
    if max_chars <= 0 or len(compact) <= max_chars:
        return compact
    return compact[:max_chars] + "..."
