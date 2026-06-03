from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MEMORY_LEVEL_RANK = {"M0": 0, "M1": 1, "M2": 2, "M3": 3}

DETAIL_KEYWORDS: dict[str, list[str]] = {
    "m1_response_style_direct": [
        "直接",
        "少废话",
        "不绕",
        "客服",
        "空泛安慰",
        "标准答案",
    ],
    "m1_anxiety_fact_first": [
        "事实",
        "选项",
        "风险",
        "下一步",
        "拆开",
        "先做",
    ],
    "m1_repeated_topic_no_restart": [
        "接着",
        "之前",
        "不是从零",
        "前面",
        "老问题",
        "同一件事",
    ],
    "kindergarten_information_vague": [
        "消息模糊",
        "信息不清楚",
        "没有正式通知",
        "正式通知",
        "具体原因",
        "没落地",
        "悬而未决",
        "没定下来",
    ],
    "child_stability_not_school_choice": [
        "孩子被折腾",
        "孩子稳定",
        "稳定感",
        "不只是换园",
        "换不换园",
        "孩子适应",
    ],
    "collaboration_logic_misaligned": [
        "概念",
        "实现",
        "错位",
        "对齐",
        "方向错位",
        "底层逻辑",
    ],
    "collaboration_realigning_cost": [
        "重新对齐",
        "底层逻辑",
        "有限精力",
        "消耗",
        "对齐成本",
        "吞掉",
    ],
    "family_coordination_support_gap": [
        "支持感",
        "被看见",
        "家里分工",
        "事务",
        "情绪",
        "家务",
    ],
    "partner_hears_task_not_emotion": [
        "只听到具体事务",
        "真实情绪",
        "任务",
        "事务诉求",
        "情绪诉求",
    ],
    "fragmented_sleep_amplifies_reactivity": [
        "睡眠",
        "睡得很碎",
        "缺觉",
        "放大",
        "耐心",
        "专注",
        "稳压器",
        "刹车",
    ],
    "fatigue_driving_response": [
        "太累",
        "疲惫",
        "被疲惫推着走",
        "生理",
        "放大器",
        "刹车",
    ],
    "friendship_low_social_battery": [
        "社交电量",
        "独处",
        "恢复",
        "见朋友",
        "轻量",
    ],
    "social_plan_as_state_signal": [
        "状态的信号",
        "状态观察",
        "观察自身状态",
    ],
    "paper_deadline_triage": [
        "优先级",
        "取舍",
        "必须认真改",
        "可以先放过",
        "截稿",
        "交付",
    ],
    "perfectionism_blocks_delivery": [
        "完美",
        "不够完美",
        "逐段打磨",
        "交付",
        "时间不允许",
    ],
    "dropoff_crying_replayed": [
        "哭得",
        "哭闹",
        "门口",
        "画面",
        "反复",
        "硬抱",
        "早上",
    ],
    "child_adaptation_or_parent_reactivity": [
        "适应慢",
        "被孩子情绪带走",
        "家长反应",
        "向老师确认",
        "孩子状态",
    ],
    "latent_1": [],
    "latent_2": [],
}

RISKY_ADDRESS_TERMS = [
    "亲爱的",
    "姐妹",
    "主人",
    "用户",
    "Wendy",
    "老朋友",
]
ROLE_ADDRESS_TERMS = ["妈妈", "父母", "家长", "研究者"]
MEMORY_CLAIM_TERMS = [
    "我记得",
    "之前聊过",
    "上次",
    "我们之前",
    "接着之前",
    "你之前",
    "老问题",
]


@dataclass(frozen=True)
class DetailTarget:
    detail_id: str
    category: str
    min_memory_level: str
    text: str
    expected_response_mode: str
    keywords: tuple[str, ...]
    should_be_remembered: bool | None = None
    detail_retention: str | None = None


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def evaluate_detail_hits(
    *,
    conversation_log: dict[str, Any],
    scene_cards: dict[str, Any],
) -> dict[str, Any]:
    detail_lookup = build_detail_lookup(scene_cards)
    turns = conversation_log.get("turns", [])
    if not isinstance(turns, list):
        raise ValueError("conversation log must contain a turns list")

    previous_user_messages: list[str] = []
    evaluated_turns = []
    aggregate: dict[str, Any] = {}

    for turn in turns:
        user_message = str(turn.get("input", {}).get("user_message", ""))
        user_context = "\n".join([*previous_user_messages, user_message])
        target_ids = _target_detail_ids(turn)
        turn_result = {
            "turn_index": turn.get("turn_index"),
            "message_id": turn.get("source", {}).get("message_id"),
            "day": turn.get("input", {}).get("day"),
            "turn_type": turn.get("source", {}).get("turn_type"),
            "target_detail_ids": target_ids,
            "variants": {},
        }

        for variant_name, variant in turn.get("variants", {}).items():
            answer = str(variant.get("assistant_answer", ""))
            variant_result = evaluate_variant_answer(
                memory_level=variant_name,
                answer=answer,
                user_context=user_context,
                target_ids=target_ids,
                detail_lookup=detail_lookup,
            )
            turn_result["variants"][variant_name] = variant_result
            _update_aggregate(aggregate, variant_name, variant_result)

        evaluated_turns.append(turn_result)
        if user_message:
            previous_user_messages.append(user_message)

    summary = _build_summary(aggregate)
    return {
        "schema_version": "detail_hit_evaluation_v0.1",
        "method": {
            "name": "rough_keyword_detail_hit_evaluator",
            "description": (
                "Heuristic scorer for detail usage, memory-level compliance, "
                "special address terms, and explicit memory claims. It is meant "
                "for quick triage, not final judgment."
            ),
            "scoring_dimensions": [
                "detail_hit",
                "correct_memory_level",
                "natural_use_not_mechanical_recall_proxy",
                "no_unprovided_or_forbidden_detail_proxy",
                "special_address_terms",
            ],
        },
        "summary": summary,
        "turns": evaluated_turns,
    }


def build_detail_lookup(scene_cards: dict[str, Any]) -> dict[str, DetailTarget]:
    cards = scene_cards.get("scene_cards", [])
    if not isinstance(cards, list):
        raise ValueError("scene cards document must contain a scene_cards list")

    details: dict[str, DetailTarget] = {}
    for card in cards:
        expectations = card.get("memory_detail_expectations", {})
        _add_details(
            details,
            expectations.get("stable_details", []),
            category="stable",
            default_level="M1",
        )
        _add_details(
            details,
            expectations.get("event_details", []),
            category="event",
            default_level="M2",
        )
        _add_details(
            details,
            expectations.get("latent_concern_details", []),
            category="latent",
            default_level="M3",
        )
    return details


def _add_details(
    details: dict[str, DetailTarget],
    raw_details: list[dict[str, Any]],
    *,
    category: str,
    default_level: str,
) -> None:
    for raw_detail in raw_details:
        detail_id = raw_detail.get("detail_id")
        if not detail_id or detail_id in details:
            continue
        keywords = keywords_for_detail(raw_detail)
        details[detail_id] = DetailTarget(
            detail_id=detail_id,
            category=category,
            min_memory_level=raw_detail.get("min_memory_level", default_level),
            text=raw_detail.get("text", ""),
            expected_response_mode=raw_detail.get("expected_response_mode", ""),
            keywords=tuple(keywords),
            should_be_remembered=raw_detail.get("should_be_remembered"),
            detail_retention=raw_detail.get("detail_retention"),
        )


def keywords_for_detail(detail: dict[str, Any]) -> list[str]:
    keys = [
        str(detail.get("detail_id", "")).split(":")[-1],
        str(detail.get("template_anchor_id", "")),
    ]
    keywords: list[str] = []
    for key in keys:
        keywords.extend(DETAIL_KEYWORDS.get(key, []))
        if key.startswith("latent_"):
            keywords.extend(_extract_chinese_terms(detail.get("text", "")))
    keywords.extend(_extract_chinese_terms(detail.get("text", "")))
    keywords.extend(_extract_chinese_terms(detail.get("expected_response_mode", "")))
    return _dedupe_keywords(keywords)


def evaluate_variant_answer(
    *,
    memory_level: str,
    answer: str,
    user_context: str,
    target_ids: list[str],
    detail_lookup: dict[str, DetailTarget],
) -> dict[str, Any]:
    hit_details = []
    allowed_hit_details = []
    forbidden_hit_details = []
    allowed_targets = []

    for detail_id in target_ids:
        detail = detail_lookup.get(detail_id)
        if not detail:
            continue
        available_via_user_context = detail_available_in_context(detail, user_context)
        allowed = _detail_allowed_for_level(
            detail=detail,
            memory_level=memory_level,
            available_via_user_context=available_via_user_context,
        )
        if allowed:
            allowed_targets.append(detail_id)

        match = detail_is_hit(detail, answer)
        if not match["hit"]:
            continue
        item = {
            "detail_id": detail_id,
            "category": detail.category,
            "min_memory_level": detail.min_memory_level,
            "available_via_user_context": available_via_user_context,
            "keyword_hits": match["keyword_hits"],
            "text": detail.text,
        }
        hit_details.append(item)
        if allowed:
            allowed_hit_details.append(item)
        else:
            forbidden_hit_details.append(item)

    address = detect_address_terms(answer)
    memory_claims = detect_memory_claims(answer)
    allowed_hit_rate = (
        len(allowed_hit_details) / len(allowed_targets) if allowed_targets else 0.0
    )
    raw_hit_rate = len(hit_details) / len(target_ids) if target_ids else 0.0
    rough_score = _rough_score(
        allowed_hit_rate=allowed_hit_rate,
        forbidden_hit_count=len(forbidden_hit_details),
        risky_address_count=address["risky_count"],
        memory_claim_count=len(memory_claims),
        memory_level=memory_level,
    )

    return {
        "rough_score": rough_score,
        "target_count": len(target_ids),
        "allowed_target_count": len(allowed_targets),
        "raw_hit_rate": round(raw_hit_rate, 4),
        "allowed_hit_rate": round(allowed_hit_rate, 4),
        "hit_detail_ids": [item["detail_id"] for item in hit_details],
        "allowed_hit_detail_ids": [item["detail_id"] for item in allowed_hit_details],
        "forbidden_hit_detail_ids": [
            item["detail_id"] for item in forbidden_hit_details
        ],
        "hit_details": hit_details,
        "forbidden_hit_details": forbidden_hit_details,
        "address_terms": address,
        "memory_claim_terms": memory_claims,
    }


def detail_is_hit(detail: DetailTarget, text: str) -> dict[str, Any]:
    keyword_hits = find_keyword_hits(text, detail.keywords)
    strong_hits = [item for item in keyword_hits if len(_normalize(item)) >= 4]
    hit = bool(strong_hits) or len(keyword_hits) >= 2
    return {"hit": hit, "keyword_hits": keyword_hits}


def detail_available_in_context(detail: DetailTarget, user_context: str) -> bool:
    return bool(find_keyword_hits(user_context, detail.keywords))


def find_keyword_hits(text: str, keywords: list[str] | tuple[str, ...]) -> list[str]:
    normalized_text = _normalize(text)
    hits = []
    for keyword in keywords:
        normalized_keyword = _normalize(keyword)
        if not normalized_keyword or len(normalized_keyword) < 2:
            continue
        if normalized_keyword in normalized_text:
            hits.append(keyword)
    return _dedupe_keywords(hits)


def detect_address_terms(answer: str) -> dict[str, Any]:
    risky = _term_counts(answer, RISKY_ADDRESS_TERMS)
    role = _term_counts(answer, ROLE_ADDRESS_TERMS)
    return {
        "risky_terms": risky,
        "role_terms": role,
        "risky_count": sum(risky.values()),
        "role_count": sum(role.values()),
    }


def detect_memory_claims(answer: str) -> list[str]:
    return [
        term
        for term, count in _term_counts(answer, MEMORY_CLAIM_TERMS).items()
        for _ in range(count)
    ]


def render_markdown_report(evaluation: dict[str, Any]) -> str:
    summary = evaluation.get("summary", {})
    lines = [
        "# Detail Hit Evaluation",
        "",
        "This is a rough keyword-based triage report, not a final semantic judgment.",
        "",
        "## Summary",
        "",
        "| Variant | Turns | Avg score | Allowed hit rate | Raw hit rate | Forbidden hits | Risky address | Memory claims |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant_name, item in sorted(summary.get("variants", {}).items()):
        lines.append(
            "| {variant} | {turns} | {score:.1f} | {allowed:.2%} | {raw:.2%} | {forbidden} | {address} | {claims} |".format(
                variant=variant_name,
                turns=item["turn_count"],
                score=item["average_rough_score"],
                allowed=item["allowed_hit_rate"],
                raw=item["raw_hit_rate"],
                forbidden=item["forbidden_hit_count"],
                address=item["risky_address_count"],
                claims=item["memory_claim_count"],
            )
        )

    lines.extend(["", "## Top Forbidden Detail Examples", ""])
    examples = summary.get("top_forbidden_examples", [])
    if not examples:
        lines.append("No forbidden detail examples detected by the rough scorer.")
    else:
        for example in examples[:10]:
            lines.append(
                "- `{variant}` `{message_id}` hit `{detail_id}` via {keywords}".format(
                    variant=example["variant"],
                    message_id=example["message_id"],
                    detail_id=example["detail_id"],
                    keywords=", ".join(example["keyword_hits"]),
                )
            )

    lines.extend(["", "## Address Term Examples", ""])
    address_examples = summary.get("address_examples", [])
    if not address_examples:
        lines.append("No risky special address examples detected.")
    else:
        for example in address_examples[:10]:
            lines.append(
                "- `{variant}` `{message_id}` risky={risky_terms} role={role_terms}".format(
                    variant=example["variant"],
                    message_id=example["message_id"],
                    risky_terms=example["risky_terms"],
                    role_terms=example["role_terms"],
                )
            )

    lines.append("")
    return "\n".join(lines)


def _target_detail_ids(turn: dict[str, Any]) -> list[str]:
    detail_recall = turn.get("evaluation_targets", {}).get("detail_recall", {})
    ids = detail_recall.get("target_detail_ids", [])
    return [item for item in ids if isinstance(item, str)]


def _detail_allowed_for_level(
    *,
    detail: DetailTarget,
    memory_level: str,
    available_via_user_context: bool,
) -> bool:
    if available_via_user_context:
        return True
    level_rank = MEMORY_LEVEL_RANK.get(memory_level, 0)
    required_rank = MEMORY_LEVEL_RANK.get(detail.min_memory_level, 99)
    if detail.category == "stable":
        return True
    return level_rank >= required_rank


def _update_aggregate(
    aggregate: dict[str, Any],
    variant_name: str,
    variant_result: dict[str, Any],
) -> None:
    item = aggregate.setdefault(
        variant_name,
        {
            "turn_count": 0,
            "rough_score_sum": 0.0,
            "target_count": 0,
            "allowed_target_count": 0,
            "hit_count": 0,
            "allowed_hit_count": 0,
            "forbidden_hit_count": 0,
            "risky_address_count": 0,
            "role_address_count": 0,
            "memory_claim_count": 0,
            "forbidden_examples": [],
            "address_examples": [],
        },
    )
    item["turn_count"] += 1
    item["rough_score_sum"] += variant_result["rough_score"]
    item["target_count"] += variant_result["target_count"]
    item["allowed_target_count"] += variant_result["allowed_target_count"]
    item["hit_count"] += len(variant_result["hit_detail_ids"])
    item["allowed_hit_count"] += len(variant_result["allowed_hit_detail_ids"])
    item["forbidden_hit_count"] += len(variant_result["forbidden_hit_detail_ids"])
    item["risky_address_count"] += variant_result["address_terms"]["risky_count"]
    item["role_address_count"] += variant_result["address_terms"]["role_count"]
    item["memory_claim_count"] += len(variant_result["memory_claim_terms"])


def _build_summary(aggregate: dict[str, Any]) -> dict[str, Any]:
    variants = {}
    all_forbidden_examples = []
    address_examples = []

    # The examples need turn metadata, so they are populated in a second pass below.
    for variant_name, item in aggregate.items():
        turn_count = item["turn_count"]
        target_count = item["target_count"]
        allowed_target_count = item["allowed_target_count"]
        variants[variant_name] = {
            "turn_count": turn_count,
            "average_rough_score": round(
                item["rough_score_sum"] / turn_count if turn_count else 0.0,
                2,
            ),
            "raw_hit_rate": (
                item["hit_count"] / target_count if target_count else 0.0
            ),
            "allowed_hit_rate": (
                item["allowed_hit_count"] / allowed_target_count
                if allowed_target_count
                else 0.0
            ),
            "hit_count": item["hit_count"],
            "allowed_hit_count": item["allowed_hit_count"],
            "forbidden_hit_count": item["forbidden_hit_count"],
            "risky_address_count": item["risky_address_count"],
            "role_address_count": item["role_address_count"],
            "memory_claim_count": item["memory_claim_count"],
        }

    return {
        "variants": variants,
        "top_forbidden_examples": all_forbidden_examples,
        "address_examples": address_examples,
    }


def enrich_summary_examples(evaluation: dict[str, Any]) -> None:
    forbidden_examples = []
    address_examples = []
    for turn in evaluation.get("turns", []):
        message_id = turn.get("message_id")
        for variant_name, result in turn.get("variants", {}).items():
            for detail in result.get("forbidden_hit_details", []):
                forbidden_examples.append(
                    {
                        "message_id": message_id,
                        "variant": variant_name,
                        "detail_id": detail["detail_id"],
                        "category": detail["category"],
                        "keyword_hits": detail["keyword_hits"],
                    }
                )
            address = result.get("address_terms", {})
            if address.get("risky_count") or address.get("role_count"):
                address_examples.append(
                    {
                        "message_id": message_id,
                        "variant": variant_name,
                        "risky_terms": address.get("risky_terms", {}),
                        "role_terms": address.get("role_terms", {}),
                    }
                )
    evaluation["summary"]["top_forbidden_examples"] = forbidden_examples[:50]
    evaluation["summary"]["address_examples"] = address_examples[:50]


def _rough_score(
    *,
    allowed_hit_rate: float,
    forbidden_hit_count: int,
    risky_address_count: int,
    memory_claim_count: int,
    memory_level: str,
) -> float:
    score = 50.0 + allowed_hit_rate * 50.0
    score -= forbidden_hit_count * 15.0
    score -= risky_address_count * 5.0
    if memory_level == "M0":
        score -= memory_claim_count * 4.0
    else:
        score -= memory_claim_count * 1.5
    return round(max(0.0, min(100.0, score)), 2)


def _extract_chinese_terms(text: str) -> list[str]:
    terms = []
    for part in re.split(r"[，。；、：,.!?！？\s]+", str(text)):
        part = part.strip()
        if 2 <= len(part) <= 12:
            terms.append(part)
    return terms


def _dedupe_keywords(keywords: list[str]) -> list[str]:
    seen = set()
    result = []
    for keyword in keywords:
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        result.append(keyword)
    return result


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def _term_counts(text: str, terms: list[str]) -> dict[str, int]:
    normalized = _normalize(text)
    counts = Counter()
    for term in terms:
        normalized_term = _normalize(term)
        if not normalized_term:
            continue
        counts[term] = normalized.count(normalized_term)
    return {term: count for term, count in counts.items() if count > 0}


def evaluate_files(
    *,
    conversation_log_path: Path,
    scene_cards_path: Path,
    output_json_path: Path,
    output_markdown_path: Path | None = None,
) -> dict[str, Any]:
    evaluation = evaluate_detail_hits(
        conversation_log=load_json(conversation_log_path),
        scene_cards=load_json(scene_cards_path),
    )
    enrich_summary_examples(evaluation)
    write_json(output_json_path, evaluation)
    if output_markdown_path:
        output_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        output_markdown_path.write_text(
            render_markdown_report(evaluation),
            encoding="utf-8",
        )
    return evaluation
