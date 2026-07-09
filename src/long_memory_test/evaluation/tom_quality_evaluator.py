from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TOM_DIMENSIONS = [
    "hidden_intent_recognition",
    "emotional_state_recognition",
    "shared_context_invocation",
    "alienation_error_rate",
    "natural_detail_use",
    "memory_misuse",
]

RELATIONAL_TONE_PATTERNS = [
    "像之前",
    "之前那样",
    "我们",
    "熟悉",
    "平时",
    "关系",
    "节奏",
    "陌生",
    "客服",
    "出戏",
    "直接",
    "自然",
    "不夸张",
    "我还是我",
]

DIMENSION_PATTERNS: dict[str, list[str]] = {
    "hidden_intent_recognition": [
        "不是只",
        "不只是",
        "不是在",
        "而是",
        "其实",
        "真正",
        "背后",
        "这层",
        "潜台词",
        "你担心",
        "你怕",
        "你希望",
        "你在确认",
    ],
    "emotional_state_recognition": [
        "不安",
        "担心",
        "怕",
        "焦虑",
        "紧",
        "累",
        "疲惫",
        "委屈",
        "自责",
        "心疼",
        "失落",
        "状态",
        "反应",
        "放大",
        "被带走",
        "没被看见",
        "支持感",
    ],
    "shared_context_invocation": [
        "接着",
        "之前",
        "上次",
        "我们之前",
        "不从头",
        "这条线",
        "处理方式",
        "延续",
        "前面",
        "老问题",
    ],
    "natural_detail_use": [
        "孩子被反复折腾",
        "孩子稳定",
        "稳定性",
        "正式通知",
        "底层逻辑",
        "重新对齐",
        "支持感",
        "被看见",
        "完美",
        "交付",
        "碎睡眠",
        "睡眠",
        "放大反应",
        "哭的画面",
        "适应慢",
        "被他的情绪带走",
        "见人",
        "状态信号",
        "社交电量",
        "恢复",
    ],
    "memory_misuse": [
        "已知",
        "推测",
        "不确定",
        "不能确定",
        "不补",
        "不编",
        "只按",
        "没有足够信息",
        "不为了显得懂",
        "如果我没记错",
    ],
}

ALIENATION_RISK_TERMS = [
    "亲爱的",
    "主人",
    "用户",
    "姐妹",
    "作为一个AI",
    "作为AI",
    "无法提供",
    "请提供更多",
    "请重新说明",
    "请详细描述",
]

ASK_REPEAT_TERMS = [
    "重新解释",
    "从头说",
    "请提供更多背景",
    "请补充背景",
    "需要你说明",
]

GENERIC_COMFORT_TERMS = [
    "别想太多",
    "一切都会好",
    "保持积极",
    "不要焦虑",
]

MEMORY_OVERUSE_TERMS = [
    "我记得你之前说过很多次",
    "我把前面都复述一下",
    "根据你完整的历史",
    "从第一天开始",
]

FABRICATION_RISK_TERMS = [
    "你老公一定",
    "老师明确",
    "对方就是",
    "孩子肯定",
]


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


def evaluate_tom_quality(*, conversation_log: dict[str, Any]) -> dict[str, Any]:
    turns = conversation_log.get("turns", [])
    if not isinstance(turns, list):
        raise ValueError("conversation log must contain a turns list")

    evaluated_turns = []
    aggregate: dict[str, Any] = {}
    for turn in turns:
        message = turn.get("input", {})
        dimensions = _active_tom_dimensions(message.get("tom_dimensions", []))
        if not dimensions:
            continue

        turn_result = {
            "turn_index": turn.get("turn_index"),
            "message_id": turn.get("source", {}).get("message_id"),
            "day": message.get("day"),
            "probe_type": message.get("probe_type"),
            "topic": message.get("topic"),
            "user_message": message.get("user_message"),
            "tom_dimensions": list(dimensions),
            "variants": {},
        }
        for variant_name, variant in turn.get("variants", {}).items():
            answer = str(variant.get("assistant_answer", ""))
            variant_result = evaluate_variant_tom_answer(
                answer=answer,
                user_message=str(message.get("user_message", "")),
                dimensions=dimensions,
                tom_assessment=None,
            )
            turn_result["variants"][variant_name] = variant_result
            _update_aggregate(aggregate, variant_name, variant_result)

        evaluated_turns.append(turn_result)

    return {
        "schema_version": "tom_quality_evaluation_v0.1",
        "method": {
            "name": "rule_based_tom_quality_evaluator",
            "description": (
                "ToM-only rule-based triage evaluator. It scores whether answers "
                "recognize hidden intent, emotional state, shared context, "
                "alienation errors, natural detail use, and memory "
                "misuse risk. It does "
                "not use detail-hit, memory-level compliance, or previous rough "
                "memory scoring."
            ),
            "quality_standard": list(TOM_DIMENSIONS),
            "explicitly_excluded": [
                "detail_hit",
                "correct_memory_level",
                "natural_use_not_mechanical_recall",
                "no_unprovided_or_forbidden_detail",
                "raw_keyword_memory_detail_score",
            ],
        },
        "summary": _build_summary(aggregate),
        "turns": evaluated_turns,
    }


def evaluate_variant_tom_answer(
    *,
    answer: str,
    user_message: str,
    dimensions: list[str],
    tom_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dimension_results = {}
    for dimension in dimensions:
        if dimension == "alienation_error_rate":
            result = _score_alienation(answer)
        elif dimension == "memory_misuse":
            result = _score_memory_misuse(answer)
        else:
            result = _score_positive_dimension(
                dimension=dimension,
                answer=answer,
                user_message=user_message,
            )
        dimension_results[dimension] = result

    average_score = (
        sum(item["score"] for item in dimension_results.values()) / len(dimension_results)
        if dimension_results
        else 0.0
    )
    tom_score = round((average_score / 2.0) * 100.0, 2)
    risks = detect_tom_risks(answer)
    return {
        "tom_score": tom_score,
        "dimension_results": dimension_results,
        "risks": risks,
        "answer_excerpt": _excerpt(answer),
    }


def _active_tom_dimensions(dimensions: Any) -> list[str]:
    return [
        str(item)
        for item in dimensions or []
        if str(item) in TOM_DIMENSIONS
    ]


def detect_tom_risks(answer: str) -> dict[str, Any]:
    return {
        "alienation_terms": _term_counts(answer, ALIENATION_RISK_TERMS),
        "asks_user_to_repeat_context": _term_counts(answer, ASK_REPEAT_TERMS),
        "generic_comfort_terms": _term_counts(answer, GENERIC_COMFORT_TERMS),
        "memory_overuse_terms": _term_counts(answer, MEMORY_OVERUSE_TERMS),
        "fabrication_risk_terms": _term_counts(answer, FABRICATION_RISK_TERMS),
    }


def render_markdown_report(evaluation: dict[str, Any]) -> str:
    summary = evaluation.get("summary", {})
    lines = [
        "# ToM Quality Evaluation",
        "",
        "This is a ToM-only rule-based triage report. It does not use detail-hit or memory-level scoring.",
        "",
        "## Summary",
        "",
        "| Variant | Probe turns | Avg ToM score | Alienation errors | Ask-repeat errors | Generic comfort hits |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for variant_name, item in sorted(summary.get("variants", {}).items()):
        lines.append(
            "| {variant} | {turns} | {score:.1f} | {alienation} | {repeat} | {generic} |".format(
                variant=variant_name,
                turns=item["turn_count"],
                score=item["average_tom_score"],
                alienation=item["alienation_error_count"],
                repeat=item["ask_repeat_error_count"],
                generic=item["generic_comfort_count"],
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

    lines.extend(["", "## Lowest Scoring Probe Examples", ""])
    examples = summary.get("lowest_scoring_examples", [])
    if not examples:
        lines.append("No ToM probe examples evaluated.")
    else:
        for example in examples[:8]:
            lines.append(
                "- `{variant}` `{message_id}` score={score:.1f}: {excerpt}".format(
                    variant=example["variant"],
                    message_id=example["message_id"],
                    score=example["tom_score"],
                    excerpt=example["answer_excerpt"],
                )
            )

    lines.append("")
    return "\n".join(lines)


def _score_positive_dimension(
    *,
    dimension: str,
    answer: str,
    user_message: str,
) -> dict[str, Any]:
    patterns = [
        *DIMENSION_PATTERNS.get(dimension, []),
        *_assessment_terms(user_message),
    ]
    hits = find_phrase_hits(answer, patterns)
    risks = detect_tom_risks(answer)
    risk_count = (
        sum(risks["asks_user_to_repeat_context"].values())
        + sum(risks["generic_comfort_terms"].values())
    )
    if risk_count and len(hits) <= 1:
        score = 0
    elif len(hits) >= 2:
        score = 2
    elif len(hits) >= 1:
        score = 1
    else:
        score = 0
    return {
        "score": score,
        "max_score": 2,
        "evidence_terms": hits[:12],
        "risk_terms": risks,
    }


def _score_alienation(answer: str) -> dict[str, Any]:
    risks = detect_tom_risks(answer)
    alienation_count = sum(risks["alienation_terms"].values())
    repeat_count = sum(risks["asks_user_to_repeat_context"].values())
    relationship_hits = find_phrase_hits(
        answer,
        RELATIONAL_TONE_PATTERNS
        + ["熟一点", "不夸张", "不搞那些虚的", "直接自然", "稳定的节奏"],
    )
    if alienation_count:
        score = 0
    elif repeat_count and not relationship_hits:
        score = 0
    elif relationship_hits:
        score = 2
    else:
        score = 1
    return {
        "score": score,
        "max_score": 2,
        "evidence_terms": relationship_hits[:12],
        "risk_terms": risks,
    }


def _score_memory_misuse(answer: str) -> dict[str, Any]:
    risks = detect_tom_risks(answer)
    misuse_count = (
        sum(risks["asks_user_to_repeat_context"].values())
        + sum(risks["memory_overuse_terms"].values())
        + sum(risks["fabrication_risk_terms"].values())
    )
    boundary_hits = find_phrase_hits(answer, DIMENSION_PATTERNS["memory_misuse"])
    if misuse_count:
        score = 0
    elif boundary_hits:
        score = 2
    else:
        score = 1
    return {
        "score": score,
        "max_score": 2,
        "evidence_terms": boundary_hits[:12],
        "risk_terms": risks,
    }


def _update_aggregate(
    aggregate: dict[str, Any],
    variant_name: str,
    variant_result: dict[str, Any],
) -> None:
    item = aggregate.setdefault(
        variant_name,
        {
            "turn_count": 0,
            "tom_score_sum": 0.0,
            "dimension_score_sums": defaultdict(float),
            "dimension_counts": defaultdict(int),
            "alienation_error_count": 0,
            "ask_repeat_error_count": 0,
            "generic_comfort_count": 0,
            "examples": [],
        },
    )
    item["turn_count"] += 1
    item["tom_score_sum"] += variant_result["tom_score"]
    for dimension, result in variant_result["dimension_results"].items():
        item["dimension_score_sums"][dimension] += result["score"]
        item["dimension_counts"][dimension] += 1
    risks = variant_result["risks"]
    item["alienation_error_count"] += sum(risks["alienation_terms"].values())
    item["ask_repeat_error_count"] += sum(risks["asks_user_to_repeat_context"].values())
    item["generic_comfort_count"] += sum(risks["generic_comfort_terms"].values())
    item["examples"].append(variant_result)


def _build_summary(aggregate: dict[str, Any]) -> dict[str, Any]:
    variants = {}
    dimension_averages: dict[str, dict[str, float]] = {}
    lowest_examples = []
    for variant_name, item in aggregate.items():
        turn_count = item["turn_count"]
        variants[variant_name] = {
            "turn_count": turn_count,
            "average_tom_score": round(
                item["tom_score_sum"] / turn_count if turn_count else 0.0,
                2,
            ),
            "alienation_error_count": item["alienation_error_count"],
            "ask_repeat_error_count": item["ask_repeat_error_count"],
            "generic_comfort_count": item["generic_comfort_count"],
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
        "lowest_scoring_examples": lowest_examples,
    }


def enrich_lowest_examples(evaluation: dict[str, Any]) -> None:
    examples = []
    for turn in evaluation.get("turns", []):
        for variant_name, result in turn.get("variants", {}).items():
            examples.append(
                {
                    "message_id": turn.get("message_id"),
                    "variant": variant_name,
                    "tom_score": result.get("tom_score", 0.0),
                    "answer_excerpt": result.get("answer_excerpt", ""),
                }
            )
    evaluation["summary"]["lowest_scoring_examples"] = sorted(
        examples,
        key=lambda item: (item["tom_score"], item["variant"], item["message_id"]),
    )[:20]


def find_phrase_hits(text: str, phrases: list[str]) -> list[str]:
    normalized = _normalize(text)
    hits = []
    seen = set()
    for phrase in phrases:
        phrase = str(phrase).strip()
        if not phrase or phrase in seen:
            continue
        normalized_phrase = _normalize(phrase)
        if len(normalized_phrase) < 2:
            continue
        if normalized_phrase in normalized:
            hits.append(phrase)
            seen.add(phrase)
    return hits


def _assessment_terms(text: str) -> list[str]:
    terms = []
    for part in re.split(r"[，。；、：,.!?！？\s]+", str(text)):
        part = part.strip()
        if 2 <= len(part) <= 10:
            terms.append(part)
    return terms


def _term_counts(text: str, terms: list[str]) -> dict[str, int]:
    normalized = _normalize(text)
    counts = Counter()
    for term in terms:
        normalized_term = _normalize(term)
        if normalized_term:
            counts[term] = normalized.count(normalized_term)
    return {term: count for term, count in counts.items() if count > 0}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def _excerpt(text: str, length: int = 220) -> str:
    compact = " ".join(str(text).split())
    return compact if len(compact) <= length else compact[:length] + "..."


def evaluate_files(
    *,
    conversation_log_path: Path,
    output_json_path: Path,
    output_markdown_path: Path | None = None,
) -> dict[str, Any]:
    evaluation = evaluate_tom_quality(conversation_log=load_json(conversation_log_path))
    enrich_lowest_examples(evaluation)
    write_json(output_json_path, evaluation)
    if output_markdown_path:
        output_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        output_markdown_path.write_text(
            render_markdown_report(evaluation),
            encoding="utf-8",
        )
    return evaluation
