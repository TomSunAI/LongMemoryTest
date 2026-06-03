from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from long_memory_test.llm import LLMConfig


MAX_DIMENSION_SCORE = 2


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
    "relationship_expectation_recognition": {
        "label": "关系期待识别",
        "question": "是否识别用户期待熟悉、直接、不过度表演的关系回应。",
        "score_0": "客服式、模板化、过度亲密，或没有回应关系位置。",
        "score_1": "语气不陌生，但只是普通友好；没有体现稳定关系期待。",
        "score_2": "熟悉、直接、不过度表演，并把关系期待体现在回应方式里。",
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
        "只是友好、有礼貌、会安慰，但没有稳定关系位置证据，relationship_expectation_recognition 最高 1 分。",
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
) -> dict[str, Any]:
    turns = conversation_log.get("turns", [])
    if not isinstance(turns, list):
        raise ValueError("conversation log must contain a turns list")

    selected_variants = set(variants or [])
    aggregate: dict[str, Any] = {}
    evaluated_turns: list[dict[str, Any]] = []
    judged_count = 0

    for turn_position, turn in enumerate(turns):
        message = turn.get("input", {})
        dimensions = [str(item) for item in message.get("tom_dimensions", [])]
        current_message_id = str(turn.get("source", {}).get("message_id") or "")
        if not dimensions:
            continue
        if message_id and current_message_id != message_id:
            continue

        turn_result = {
            "turn_index": turn.get("turn_index"),
            "message_id": current_message_id,
            "day": message.get("day"),
            "probe_type": message.get("probe_type"),
            "topic": message.get("topic"),
            "user_message": message.get("user_message"),
            "tom_dimensions": list(dimensions),
            "required_memory_type": list(message.get("required_memory_type", [])),
            "dependency_analysis": dict(message.get("dependency_analysis", {})),
            "variants": {},
        }

        for variant_name, variant in sorted(turn.get("variants", {}).items()):
            if selected_variants and variant_name not in selected_variants:
                continue
            if limit is not None and judged_count >= limit:
                break

            if print_progress:
                print(
                    "[judge] "
                    f"case={judged_count + 1} "
                    f"message_id={current_message_id} "
                    f"variant={variant_name}",
                    flush=True,
                )

            judge_case = build_judge_case(
                turns=turns,
                turn_position=turn_position,
                variant_name=variant_name,
                context_turns=context_turns,
                max_answer_chars=max_answer_chars,
                max_context_answer_chars=max_context_answer_chars,
            )
            raw_output, judgement = request_parseable_llm_judgement(
                client=client,
                llm_config=llm_config,
                judge_case=judge_case,
                dimensions=dimensions,
                max_output_tokens=max_output_tokens,
                timeout_seconds=timeout_seconds,
            )
            normalized = normalize_judgement(
                judgement=judgement,
                dimensions=dimensions,
                raw_output=raw_output,
            )
            turn_result["variants"][variant_name] = normalized
            _update_aggregate(aggregate, variant_name, normalized)
            judged_count += 1

        if turn_result["variants"]:
            evaluated_turns.append(turn_result)
        if limit is not None and judged_count >= limit:
            break

    summary = _build_summary(aggregate)
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
        },
        "summary": summary,
        "turns": evaluated_turns,
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
    dimensions = [str(item) for item in message.get("tom_dimensions", [])]
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
) -> tuple[str, dict[str, Any]]:
    last_output = ""
    for _attempt in range(2):
        last_output = request_llm_judgement(
            client=client,
            llm_config=llm_config,
            judge_case=judge_case,
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
        )
        try:
            return last_output, parse_judge_output(last_output)
        except (json.JSONDecodeError, ValueError):
            continue
    return last_output, _fallback_parse_error_judgement(dimensions=dimensions)


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


def _fallback_parse_error_judgement(*, dimensions: list[str]) -> dict[str, Any]:
    return {
        "dimension_scores": {
            dimension: {
                "score": 0,
                "evidence_quote": "",
                "reason": "judge 输出不是可解析 JSON，本 case 进入人工复核。",
            }
            for dimension in dimensions
        },
        "flags": {
            name: False for name in FLAG_NAMES
        },
        "failure_types": [],
        "overall_reason": "judge 输出不是可解析 JSON，本 case 不作为可靠自动评分，应人工复核。",
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
    needs_human_review = bool(
        judgement.get("needs_human_review", False)
        or confidence < 0.55
        or any(flags.values())
        or bool(failure_types)
    )
    return {
        "tom_score": computed_tom_score,
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
        "| Variant | Probe answers | Avg ToM score | Avg confidence | Human review | Flags |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for variant_name, item in sorted(summary.get("variants", {}).items()):
        lines.append(
            "| {variant} | {turns} | {score:.1f} | {confidence:.2f} | {review} | {flags} |".format(
                variant=variant_name,
                turns=item["turn_count"],
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
            "你的任务是评价 assistant_answer 是否理解用户的心理状态、隐含意图、关系期待和共同语境。",
            "你只能依据用户提供的 case JSON 评分，不要脑补未提供的长期历史。",
            "case 使用盲化条件名 Condition A/B/C/D；不要尝试反推出 M0/M1/M2/M3。",
            "case 不提供 BEI、gold label 或高低分答案标签；不得把这些当评分依据。",
            "你必须严格评分。默认从 0 分开始，只有 assistant_answer 中有明确证据时才加分。",
            "每个维度使用 0-2 分：0=失败，1=部分识别，2=明确识别并转化为回应策略。",
            "2 分是强证据满分，不是方向正确分。普通、可用、礼貌、能安慰的回答通常只能得 1 分。",
            "不要因为回答更长、格式更整齐、语气更热情或安慰更多就给高分。",
            "不要因为回答最终建议看起来合理就给高分；ToM 分数看的是心理推断、关系位置、可验证共同语境和自然细节。",
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
    item["tom_score_sum"] += judged_result["tom_score"]
    item["confidence_sum"] += judged_result["confidence"]
    item["needs_human_review_count"] += int(bool(judged_result["needs_human_review"]))
    for flag_name, enabled in judged_result["flags"].items():
        if enabled:
            item["flag_count"] += 1
            item["flag_counts"][flag_name] += 1
    for failure_type in judged_result.get("failure_types", []):
        item["failure_type_counts"][failure_type] += 1
    for dimension, result in judged_result["dimension_scores"].items():
        item["dimension_score_sums"][dimension] += result["score"]
        item["dimension_counts"][dimension] += 1


def _build_summary(aggregate: dict[str, Any]) -> dict[str, Any]:
    variants = {}
    dimension_averages = {}
    for variant_name, item in aggregate.items():
        turn_count = item["turn_count"]
        variants[variant_name] = {
            "turn_count": turn_count,
            "average_tom_score": round(
                item["tom_score_sum"] / turn_count if turn_count else 0.0,
                2,
            ),
            "average_confidence": round(
                item["confidence_sum"] / turn_count if turn_count else 0.0,
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
            and dimension
            in {"alienation_error_rate", "relationship_expectation_recognition"},
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
                "relationship_expectation_recognition",
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
