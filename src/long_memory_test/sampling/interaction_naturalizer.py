from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from json import JSONDecodeError
from typing import Any


NATURALIZED_DIALOGUE_SCHEMA_VERSION = "interaction_naturalization_v0.1"


@dataclass(frozen=True)
class InteractionNaturalizationConfig:
    max_followups: int = 2
    max_allowed_facts: int = 12
    temperature: float = 0.2
    top_p: float = 1.0
    max_tokens: int = 900
    timeout_seconds: float = 120.0
    json_response_format: bool = True
    retry_on_invalid_json: bool = True


def build_naturalization_prompt(
    *,
    interaction_unit: dict[str, Any],
    bound_probes: list[dict[str, Any]] | None = None,
    config: InteractionNaturalizationConfig | None = None,
) -> list[dict[str, str]]:
    cfg = config or InteractionNaturalizationConfig()
    probes = [probe for probe in (bound_probes or []) if isinstance(probe, dict)]
    opening = _opening(interaction_unit)
    boundary = _scene_boundary(interaction_unit)
    followup = _followup(interaction_unit)
    current_state_change_fact = interaction_unit.get("current_state_change_fact")
    allowed_facts = _priority_allowed_facts(
        facts=boundary.get("allowed_facts", []),
        current_state_change_fact=current_state_change_fact,
    )
    allowed_fact_ids = [str(item.get("fact_id")) for item in allowed_facts if item.get("fact_id")]
    latent_concern_ids = [
        str(item)
        for item in boundary.get("latent_concern_ids", [])
        if item not in (None, "")
    ]
    prompt_payload = {
        "task": "naturalize_existing_interaction_unit_without_changing_facts",
        "source_interaction_unit_id": interaction_unit.get("interaction_unit_id"),
        "canonical_opening_user_message": opening.get("user_message"),
        "canonical_opening_user_message_zh": opening.get("user_message_zh"),
        "current_state_change_fact": current_state_change_fact,
        "event_title": interaction_unit.get("event_title"),
        "event_stage": interaction_unit.get("event_stage"),
        "conversation_goal": opening.get("conversation_goal"),
        "conversation_goal_zh": opening.get("conversation_goal_zh"),
        "allowed_facts": allowed_facts[: cfg.max_allowed_facts],
        "allowed_fact_ids": allowed_fact_ids[: cfg.max_allowed_facts],
        "latent_concerns": boundary.get("latent_concerns", []),
        "latent_concern_ids": latent_concern_ids,
        "permitted_conversational_moves": followup.get("permitted_conversational_moves", []),
        "reveal_steps": followup.get("reveal_steps", [])[: cfg.max_followups],
        "must_not_introduce": followup.get("must_not_introduce", []),
        "stop_conditions": followup.get("stop_conditions", []),
        "bound_probe_followup_guidance": _probe_followup_guidance(probes),
        "required_output_schema": {
            "source_interaction_unit_id": "same id as input",
            "opening_user_message": "natural Chinese user opening based only on canonical_opening_user_message_zh; do not use probe wording here",
            "followup_user_messages": ["0-2 optional followups within reveal_steps; may align with bound_probe_followup_guidance when present, but do not copy the formal probe question"],
            "fact_ids_used": ["subset of allowed_fact_ids or latent_concern_ids"],
            "notes": "short audit note",
        },
    }
    system = (
        "你是长期互动实验的数据自然化助手。你只能把已有 I unit 改写得更像自然用户表达；"
        "不能创造新事实，不能改变事件阶段，不能越过 scene_boundary。"
        "输出必须是严格 JSON，不要 Markdown。"
    )
    user = (
        "请基于下面的 canonical I unit 生成自然化候选。"
        "注意：canonical I unit 仍是唯一结构真值，你只输出候选话术。"
        "如果提供了 bound_probe_followup_guidance，只能用于 followup_user_messages，"
        "不能影响 opening_user_message，也不能复制正式 Probe 问题。\n"
        + json.dumps(prompt_payload, ensure_ascii=False, indent=2)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _priority_allowed_facts(
    *,
    facts: Any,
    current_state_change_fact: Any,
) -> list[dict[str, Any]]:
    if not isinstance(facts, list):
        return []
    current_id = ""
    if isinstance(current_state_change_fact, dict):
        current_id = str(current_state_change_fact.get("fact_id") or "")
    priority_types = {"current_state_change_fact", "stage_delta_fact"}
    prioritized: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in facts:
        if not isinstance(item, dict):
            continue
        fact_id = str(item.get("fact_id") or "")
        if fact_id in seen:
            continue
        seen.add(fact_id)
        if fact_id == current_id or str(item.get("type") or "") in priority_types:
            prioritized.append(item)
        else:
            remaining.append(item)
    return [*prioritized, *remaining]


def _probe_followup_guidance(probes: list[dict[str, Any]]) -> dict[str, Any]:
    if not probes:
        return {
            "has_bound_probe": False,
            "policy": "No bound probe; generate follow-ups only from reveal_steps.",
        }
    return {
        "has_bound_probe": True,
        "policy": (
            "Use these probes only to shape followup_user_messages. "
            "Do not use probe wording in opening_user_message. "
            "Do not copy the formal probe question exactly. "
            "The official targeted_probe turn remains separate and read-only."
        ),
        "bound_probes": [_probe_guidance_item(probe) for probe in probes],
    }


def _probe_guidance_item(probe: dict[str, Any]) -> dict[str, Any]:
    ground_truth = probe.get("ground_truth", {}) if isinstance(probe.get("ground_truth"), dict) else {}
    tom = probe.get("tom_assessment", {}) if isinstance(probe.get("tom_assessment"), dict) else {}
    return {
        "probe_id": probe.get("probe_id"),
        "paper_probe_id": probe.get("paper_probe_id"),
        "paper_probe_zh": probe.get("paper_probe_zh"),
        "primary_dimension_id": probe.get("primary_dimension_id"),
        "primary_dimension": probe.get("primary_dimension"),
        "formal_probe_question": probe.get("question") or probe.get("user_message"),
        "followup_alignment_goal": tom.get("hidden_user_need")
        or ground_truth.get("acceptable_response"),
        "high_score_behavior": tom.get("high_score_behavior"),
        "ground_truth_expected_references": ground_truth.get("expected_references", []),
        "ground_truth_failure_modes": ground_truth.get("failure_modes", []),
    }


def naturalize_interaction_unit(
    *,
    interaction_unit: dict[str, Any],
    client: Any,
    model: str,
    bound_probes: list[dict[str, Any]] | None = None,
    config: InteractionNaturalizationConfig | None = None,
) -> dict[str, Any]:
    cfg = config or InteractionNaturalizationConfig()
    messages = build_naturalization_prompt(
        interaction_unit=interaction_unit,
        bound_probes=bound_probes,
        config=cfg,
    )
    raw = _request_raw_json_candidate(
        client=client,
        model=model,
        messages=messages,
        cfg=cfg,
    )
    parsed = _parse_json_object(raw)
    candidate = normalize_naturalized_dialogue(
        interaction_unit=interaction_unit,
        candidate=parsed,
        bound_probes=bound_probes,
        raw_output=str(raw),
        config=cfg,
    )
    validation = validate_naturalized_dialogue(
        interaction_unit=interaction_unit,
        naturalized_dialogue=candidate,
    )
    candidate["validation"] = validation
    return candidate


def _request_raw_json_candidate(
    *,
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    cfg: InteractionNaturalizationConfig,
) -> str:
    response = _create_completion(
        client=client,
        model=model,
        messages=messages,
        cfg=cfg,
        use_json_response_format=cfg.json_response_format,
    )
    raw = _message_content(response)
    try:
        _parse_json_object(raw)
        return raw
    except (JSONDecodeError, ValueError) as first_error:
        if not cfg.retry_on_invalid_json:
            raise ValueError(_invalid_json_message(first_error=first_error, raw=raw)) from first_error
    retry_messages = [
        *messages,
        {
            "role": "user",
            "content": (
                "上一轮输出不是可解析的 JSON。请只输出一个 JSON object，"
                "字段必须包含 source_interaction_unit_id、opening_user_message、"
                "followup_user_messages、fact_ids_used、notes；不要解释。"
            ),
        },
    ]
    response = _create_completion(
        client=client,
        model=model,
        messages=retry_messages,
        cfg=cfg,
        use_json_response_format=cfg.json_response_format,
    )
    raw = _message_content(response)
    try:
        _parse_json_object(raw)
    except (JSONDecodeError, ValueError) as second_error:
        raise ValueError(_invalid_json_message(first_error=second_error, raw=raw)) from second_error
    return raw


def _create_completion(
    *,
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    cfg: InteractionNaturalizationConfig,
    use_json_response_format: bool,
) -> Any:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": cfg.temperature,
        "top_p": cfg.top_p,
        "max_tokens": cfg.max_tokens,
        "timeout": cfg.timeout_seconds,
    }
    if use_json_response_format:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        return client.chat.completions.create(**kwargs)
    except Exception:
        if not use_json_response_format:
            raise
        kwargs.pop("response_format", None)
        return client.chat.completions.create(**kwargs)


def _message_content(response: Any) -> str:
    choices = getattr(response, "choices", []) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", "") if message is not None else ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(getattr(item, "text", "") or getattr(item, "content", "") or ""))
        return "\n".join(part for part in parts if part)
    reasoning_content = getattr(message, "reasoning_content", "") if message is not None else ""
    if isinstance(reasoning_content, str) and reasoning_content.strip():
        return reasoning_content
    return str(content or "")


def _invalid_json_message(*, first_error: Exception, raw: str) -> str:
    preview = raw[:500].replace("\n", "\\n")
    return f"Naturalization output was not valid JSON: {first_error}. raw_preview={preview!r}"


def normalize_naturalized_dialogue(
    *,
    interaction_unit: dict[str, Any],
    candidate: dict[str, Any],
    bound_probes: list[dict[str, Any]] | None = None,
    raw_output: str = "",
    config: InteractionNaturalizationConfig | None = None,
) -> dict[str, Any]:
    cfg = config or InteractionNaturalizationConfig()
    unit_id = str(interaction_unit.get("interaction_unit_id") or "")
    opening = _opening(interaction_unit)
    followups = candidate.get("followup_user_messages", [])
    if not isinstance(followups, list):
        followups = []
    fact_ids_used = candidate.get("fact_ids_used", [])
    if not isinstance(fact_ids_used, list):
        fact_ids_used = []
    probes = [probe for probe in (bound_probes or []) if isinstance(probe, dict)]
    return {
        "schema_version": NATURALIZED_DIALOGUE_SCHEMA_VERSION,
        "naturalized_dialogue_id": f"{unit_id}_NAT001",
        "source_interaction_unit_id": str(candidate.get("source_interaction_unit_id") or unit_id),
        "source_message_id": opening.get("message_id") or unit_id,
        "llm_generated": bool(raw_output),
        "canonical_opening_user_message": opening.get("user_message"),
        "opening_user_message": str(candidate.get("opening_user_message") or "").strip(),
        "followup_user_messages": [
            str(item).strip() for item in followups[: cfg.max_followups] if str(item).strip()
        ],
        "fact_ids_used": [str(item) for item in fact_ids_used if item],
        "bound_probe_ids": [
            str(probe.get("probe_id")) for probe in probes if probe.get("probe_id")
        ],
        "bound_probe_refs": [
            {
                "probe_id": probe.get("probe_id"),
                "paper_probe_id": probe.get("paper_probe_id"),
                "primary_dimension_id": probe.get("primary_dimension_id"),
                "question": probe.get("question") or probe.get("user_message"),
            }
            for probe in probes
        ],
        "probe_aware_followup_policy": {
            "bound_probe_count": len(probes),
            "opening_must_ignore_probe": True,
            "followups_may_align_with_probe": bool(probes),
            "formal_probe_question_must_not_be_copied": True,
        },
        "notes": str(candidate.get("notes") or ""),
        "raw_output": raw_output,
        "construction_config": asdict(cfg),
        "non_destructive_policy": {
            "canonical_i_unit_preserved": True,
            "naturalized_text_is_candidate_only": True,
            "must_not_overwrite_scripted_opening": True,
        },
    }


def validate_naturalized_dialogue(
    *,
    interaction_unit: dict[str, Any],
    naturalized_dialogue: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    unit_id = str(interaction_unit.get("interaction_unit_id") or "")
    if naturalized_dialogue.get("source_interaction_unit_id") != unit_id:
        issues.append("source_interaction_unit_id does not match interaction_unit_id.")
    if not str(naturalized_dialogue.get("opening_user_message") or "").strip():
        issues.append("opening_user_message is empty.")
    boundary = _scene_boundary(interaction_unit)
    allowed_fact_ids = set(str(item) for item in boundary.get("allowed_fact_ids", []))
    allowed_latent_concern_ids = set(
        str(item) for item in boundary.get("latent_concern_ids", [])
    )
    allowed_latent_concern_ids.update(
        str(item.get("concern_id"))
        for item in boundary.get("latent_concerns", [])
        if isinstance(item, dict) and item.get("concern_id")
    )
    allowed_detail_ids = allowed_fact_ids | allowed_latent_concern_ids
    invalid_fact_ids = [
        fact_id
        for fact_id in naturalized_dialogue.get("fact_ids_used", [])
        if str(fact_id) not in allowed_detail_ids
    ]
    if invalid_fact_ids:
        issues.append(f"fact_ids_used contains ids outside scene_boundary: {invalid_fact_ids}.")
    max_followups = int(_followup(interaction_unit).get("followup_budget", 0) or 0)
    if len(naturalized_dialogue.get("followup_user_messages", [])) > max_followups:
        issues.append("followup_user_messages exceeds followup_budget.")
    if naturalized_dialogue.get("opening_user_message") == _opening(interaction_unit).get("user_message"):
        issues.append("opening_user_message was not naturalized; it exactly matches canonical opening.")
    probe_questions = [
        str(probe.get("question") or probe.get("user_message") or "").strip()
        for probe in naturalized_dialogue.get("bound_probe_refs", [])
        if isinstance(probe, dict)
    ]
    opening_text = str(naturalized_dialogue.get("opening_user_message") or "").strip()
    followup_texts = [
        str(item).strip()
        for item in naturalized_dialogue.get("followup_user_messages", [])
        if str(item).strip()
    ]
    for question in probe_questions:
        if question and opening_text == question:
            issues.append("opening_user_message copied a formal probe question.")
        if question and question in followup_texts:
            issues.append("followup_user_messages copied a formal probe question exactly.")
    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "allowed_fact_id_count": len(allowed_fact_ids),
        "allowed_latent_concern_id_count": len(allowed_latent_concern_ids),
    }


def attach_naturalized_dialogues(
    *,
    daily_interactions: dict[str, Any],
    naturalized_dialogues: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return a copy with candidate naturalization attached, preserving I units."""

    copied = json.loads(json.dumps(daily_interactions, ensure_ascii=False))
    for persona in copied.get("personas", []):
        if not isinstance(persona, dict):
            continue
        for day in persona.get("days", []):
            if not isinstance(day, dict):
                continue
            for unit in day.get("interaction_units", []):
                if not isinstance(unit, dict):
                    continue
                unit_id = str(unit.get("interaction_unit_id") or "")
                if unit_id in naturalized_dialogues:
                    unit["naturalized_dialogue_candidate"] = naturalized_dialogues[unit_id]
                    unit["scripted_opening_preserved"] = True
    copied.setdefault("construction_scope", {})["naturalized_dialogues_attached"] = True
    return copied


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Naturalization output must be a JSON object.")
    return parsed


def _opening(unit: dict[str, Any]) -> dict[str, Any]:
    opening = unit.get("scripted_opening", {})
    return opening if isinstance(opening, dict) else {}


def _followup(unit: dict[str, Any]) -> dict[str, Any]:
    followup = unit.get("constrained_followup", {})
    return followup if isinstance(followup, dict) else {}


def _scene_boundary(unit: dict[str, Any]) -> dict[str, Any]:
    boundary = unit.get("scene_boundary", {})
    return boundary if isinstance(boundary, dict) else {}
