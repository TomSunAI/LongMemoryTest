from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from .realism_validator import (
    RealismValidationConfig,
    WORK_FAMILY_DOMAINS,
    _event_is_compatible_with_archetype,
    _hard_rule_reasons,
    build_realism_validation_report,
    validate_persona_event_set,
)
from .zh_localization import event_category_summary_zh, event_category_title_zh, zh_value


@dataclass(frozen=True)
class P0SamplingConfig:
    random_seed: int = 20260701
    num_personas: int = 5
    events_per_persona_min: int = 4
    events_per_persona_max: int = 6
    candidate_events_min: int = 8
    candidate_events_max: int = 12
    min_event_domains_per_persona: int = 3
    max_events_per_domain_per_persona: int = 2
    min_primary_life_domains_per_persona: int = 3
    min_long_term_goals_per_persona: int = 2
    min_communication_styles_per_persona: int = 2
    min_stress_responses_per_persona: int = 2
    max_candidate_resample_attempts: int = 20


def run_p0_persona_event_sampling(
    *,
    archetype_pool: dict[str, Any],
    event_pool: dict[str, Any],
    config: P0SamplingConfig | None = None,
) -> dict[str, Any]:
    cfg = config or P0SamplingConfig()
    rng = random.Random(cfg.random_seed)
    archetypes = [item for item in archetype_pool.get("archetypes", []) if isinstance(item, dict)]
    events = [item for item in event_pool.get("event_categories", []) if isinstance(item, dict)]
    if not archetypes:
        raise ValueError("No archetypes found in archetype_pool.")
    if not events:
        raise ValueError("No event categories found in event_pool.")

    personas = _sample_personas(archetypes=archetypes, cfg=cfg, rng=rng)
    candidate_sets = []
    accepted_sets = []
    persona_reports = []
    events_by_id = {
        str(event.get("event_category_id")): event
        for event in events
        if event.get("event_category_id")
    }
    archetypes_by_id = {
        str(archetype.get("archetype_id")): archetype
        for archetype in archetypes
        if archetype.get("archetype_id")
    }
    validator_config = RealismValidationConfig(
        events_per_persona_min=cfg.events_per_persona_min,
        events_per_persona_max=cfg.events_per_persona_max,
        candidate_events_min=cfg.candidate_events_min,
        candidate_events_max=cfg.candidate_events_max,
        min_event_domains_per_persona=cfg.min_event_domains_per_persona,
        max_events_per_domain_per_persona=cfg.max_events_per_domain_per_persona,
    )

    for persona in personas:
        candidate_set, accepted_set, decision_report = _sample_events_for_persona(
            persona=persona,
            events=events,
            events_by_id=events_by_id,
            archetypes_by_id=archetypes_by_id,
            cfg=cfg,
            validator_config=validator_config,
            rng=rng,
        )
        candidate_sets.append(candidate_set)
        accepted_sets.append(accepted_set)
        persona_reports.append(decision_report)

    raw_sampled_personas = {
        "schema_version": "sampled_personas_v0.1",
        "sampling_stage": "P0_persona_sampling",
        "sampling_config": asdict(cfg),
        "personas": personas,
    }
    sampled_personas = {
        **raw_sampled_personas,
        "locale_views": {
            "zh": {
                "personas": [_localized_persona_output(persona) for persona in personas],
            }
        },
    }
    candidate_event_sets = {
        "schema_version": "candidate_event_sets_v0.1",
        "sampling_stage": "P0_event_candidate_sampling",
        "sampling_config": asdict(cfg),
        "candidate_event_sets": candidate_sets,
    }
    accepted_event_sets = {
        "schema_version": "accepted_persona_event_sets_v0.1",
        "sampling_stage": "P0_compatibility_validated_event_sets",
        "sampling_config": asdict(cfg),
        "accepted_persona_event_sets": accepted_sets,
    }
    realism_report = build_realism_validation_report(
        archetype_pool=archetype_pool,
        event_pool=event_pool,
        sampled_personas=raw_sampled_personas,
        accepted_event_sets=accepted_event_sets,
        config=validator_config,
    )
    compatibility_report = {
        "schema_version": "compatibility_report_v0.1",
        "sampling_stage": "P0_persona_event_compatibility_validation",
        "status": "pass" if realism_report["status"] == "pass" else "fail",
        "sampling_config": asdict(cfg),
        "summary": _build_summary(
            personas=personas,
            candidate_sets=candidate_sets,
            accepted_sets=accepted_sets,
            realism_report=realism_report,
        ),
        "persona_reports": persona_reports,
        "batch_realism_report": realism_report.get("batch_report"),
    }
    return {
        "sampled_personas": sampled_personas,
        "candidate_event_sets": candidate_event_sets,
        "accepted_persona_event_sets": accepted_event_sets,
        "compatibility_report": compatibility_report,
        "realism_validation_report": realism_report,
    }


def _sample_personas(
    *,
    archetypes: list[dict[str, Any]],
    cfg: P0SamplingConfig,
    rng: random.Random,
) -> list[dict[str, Any]]:
    order = _balanced_archetype_order(archetypes=archetypes, count=cfg.num_personas)
    personas = []
    for index, archetype in enumerate(order, start=1):
        archetype_id = str(archetype["archetype_id"])
        persona = {
            "persona_id": f"P{index:04d}",
            "source_archetype": archetype_id,
            "source_archetype_label": archetype.get("label", ""),
            "age_range": _choice(archetype, "age_range_options", rng),
            "occupation": _choice(archetype, "occupation_options", rng),
            "occupation_status": _choice(archetype, "occupation_status_options", rng),
            "education_background": _choice(archetype, "education_options", rng),
            "family_structure": _choice(archetype, "family_structure_options", rng),
            "life_stage": _choice(archetype, "life_stage_options", rng),
            "economic_condition": _choice(archetype, "economic_condition_options", rng),
            "social_support": _choice(archetype, "social_support_options", rng),
            "primary_life_domains": _sample_list(
                archetype.get("likely_life_domains", []),
                minimum=cfg.min_primary_life_domains_per_persona,
                rng=rng,
            ),
            "long_term_goals": _sample_list(
                archetype.get("long_term_goal_options", []),
                minimum=cfg.min_long_term_goals_per_persona,
                rng=rng,
            ),
            "communication_style": _sample_list(
                archetype.get("communication_style_options", []),
                minimum=cfg.min_communication_styles_per_persona,
                rng=rng,
            ),
            "stress_response": _sample_list(
                archetype.get("stress_response_options", []),
                minimum=cfg.min_stress_responses_per_persona,
                rng=rng,
            ),
            "decision_style": _sample_list(
                archetype.get("decision_style_options", []),
                minimum=1,
                rng=rng,
            ),
            "memory_relevant_traits": _sample_list(
                archetype.get("memory_relevant_trait_options", []),
                minimum=1,
                rng=rng,
            ),
            "sensitive_fields": {
                "gender": "unprovided",
                "health_status": "ordinary fatigue, stress, or routine pressure only",
                "family_details": "general family structure only",
                "income": "broad economic condition only",
            },
        }
        personas.append(persona)
    return personas


def _localized_persona_output(persona: dict[str, Any]) -> dict[str, Any]:
    output = dict(persona)
    for key in [
        "source_archetype_label",
        "age_range",
        "occupation",
        "occupation_status",
        "education_background",
        "family_structure",
        "life_stage",
        "economic_condition",
        "social_support",
        "primary_life_domains",
        "long_term_goals",
        "communication_style",
        "stress_response",
        "decision_style",
        "memory_relevant_traits",
        "sensitive_fields",
    ]:
        if key in output:
            output[key] = zh_value(output[key])
    return output


def _balanced_archetype_order(
    *,
    archetypes: list[dict[str, Any]],
    count: int,
) -> list[dict[str, Any]]:
    result = []
    for index in range(count):
        result.append(archetypes[index % len(archetypes)])
    return result


def _sample_events_for_persona(
    *,
    persona: dict[str, Any],
    events: list[dict[str, Any]],
    events_by_id: dict[str, dict[str, Any]],
    archetypes_by_id: dict[str, dict[str, Any]],
    cfg: P0SamplingConfig,
    validator_config: RealismValidationConfig,
    rng: random.Random,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    persona_id = str(persona["persona_id"])
    archetype_id = str(persona["source_archetype"])
    eligible = [
        event
        for event in events
        if _event_is_compatible_with_archetype(event, archetype_id)
        and not _hard_rule_reasons(archetype_id, event)
    ]
    if len(eligible) < cfg.candidate_events_min:
        raise ValueError(
            f"{archetype_id} has only {len(eligible)} eligible events; "
            f"need at least {cfg.candidate_events_min}."
        )

    last_candidate_events: list[dict[str, Any]] = []
    last_accepted_events: list[dict[str, Any]] = []
    for _attempt in range(cfg.max_candidate_resample_attempts):
        candidate_count = rng.randint(
            cfg.candidate_events_min,
            min(cfg.candidate_events_max, len(eligible)),
        )
        candidate_events = _sample_candidate_events(
            events=eligible,
            count=candidate_count,
            rng=rng,
        )
        accepted_count = rng.randint(cfg.events_per_persona_min, cfg.events_per_persona_max)
        accepted_events = _choose_accepted_events(
            candidate_events=candidate_events,
            accepted_count=accepted_count,
            cfg=cfg,
            rng=rng,
        )
        last_candidate_events = candidate_events
        last_accepted_events = accepted_events
        if not accepted_events:
            continue
        accepted_event_ids = [str(event["event_category_id"]) for event in accepted_events]
        event_report = validate_persona_event_set(
            persona=persona,
            accepted_event_ids=accepted_event_ids,
            events_by_id=events_by_id,
            archetypes_by_id=archetypes_by_id,
            config=validator_config,
        )
        if event_report["status"] == "pass":
            return _build_persona_event_outputs(
                persona=persona,
                candidate_events=candidate_events,
                accepted_events=accepted_events,
                validator_report=event_report,
                cfg=cfg,
            )

    accepted_event_ids = [str(event.get("event_category_id")) for event in last_accepted_events]
    event_report = validate_persona_event_set(
        persona=persona,
        accepted_event_ids=accepted_event_ids,
        events_by_id=events_by_id,
        archetypes_by_id=archetypes_by_id,
        config=validator_config,
    )
    raise ValueError(
        f"Could not sample a valid accepted event set for {persona_id}/{archetype_id}: "
        f"{event_report['issues']}"
    )


def _sample_candidate_events(
    *,
    events: list[dict[str, Any]],
    count: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    by_domain = _events_by_domain(events)
    domains = list(by_domain)
    rng.shuffle(domains)
    selected = []
    selected_ids = set()

    for domain in domains:
        if len(selected) >= count:
            break
        choices = by_domain[domain][:]
        rng.shuffle(choices)
        event = choices[0]
        selected.append(event)
        selected_ids.add(str(event["event_category_id"]))

    remaining = [
        event for event in events if str(event.get("event_category_id")) not in selected_ids
    ]
    rng.shuffle(remaining)
    selected.extend(remaining[: max(0, count - len(selected))])
    rng.shuffle(selected)
    return selected[:count]


def _choose_accepted_events(
    *,
    candidate_events: list[dict[str, Any]],
    accepted_count: int,
    cfg: P0SamplingConfig,
    rng: random.Random,
) -> list[dict[str, Any]]:
    by_domain = _events_by_domain(candidate_events)
    non_work_family_domains = [
        domain
        for domain in by_domain
        if domain not in WORK_FAMILY_DOMAINS
    ]
    if not non_work_family_domains:
        return []

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    domain_counts: Counter[str] = Counter()

    first_domain = rng.choice(non_work_family_domains)
    _add_from_domain(
        domain=first_domain,
        by_domain=by_domain,
        selected=selected,
        selected_ids=selected_ids,
        domain_counts=domain_counts,
        rng=rng,
    )

    domains = list(by_domain)
    rng.shuffle(domains)
    for domain in domains:
        if len(domain_counts) >= cfg.min_event_domains_per_persona:
            break
        _add_from_domain(
            domain=domain,
            by_domain=by_domain,
            selected=selected,
            selected_ids=selected_ids,
            domain_counts=domain_counts,
            rng=rng,
        )

    remaining = [
        event
        for event in candidate_events
        if str(event.get("event_category_id")) not in selected_ids
    ]
    rng.shuffle(remaining)
    for event in remaining:
        if len(selected) >= accepted_count:
            break
        domain = str(event.get("event_domain"))
        if domain_counts[domain] >= cfg.max_events_per_domain_per_persona:
            continue
        selected.append(event)
        selected_ids.add(str(event["event_category_id"]))
        domain_counts[domain] += 1

    if len(selected) < cfg.events_per_persona_min:
        return []
    if len(domain_counts) < cfg.min_event_domains_per_persona:
        return []
    return selected[:accepted_count]


def _add_from_domain(
    *,
    domain: str,
    by_domain: dict[str, list[dict[str, Any]]],
    selected: list[dict[str, Any]],
    selected_ids: set[str],
    domain_counts: Counter[str],
    rng: random.Random,
) -> None:
    choices = [
        event
        for event in by_domain.get(domain, [])
        if str(event.get("event_category_id")) not in selected_ids
    ]
    if not choices:
        return
    rng.shuffle(choices)
    event = choices[0]
    selected.append(event)
    selected_ids.add(str(event["event_category_id"]))
    domain_counts[domain] += 1


def _build_persona_event_outputs(
    *,
    persona: dict[str, Any],
    candidate_events: list[dict[str, Any]],
    accepted_events: list[dict[str, Any]],
    validator_report: dict[str, Any],
    cfg: P0SamplingConfig,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    persona_id = str(persona["persona_id"])
    archetype_id = str(persona["source_archetype"])
    accepted_ids = {str(event["event_category_id"]) for event in accepted_events}
    accepted_domain_counts = Counter(str(event.get("event_domain")) for event in accepted_events)

    candidates = []
    candidate_decisions = []
    for event in candidate_events:
        event_id = str(event["event_category_id"])
        accepted = event_id in accepted_ids
        decision = "accept" if accepted else "reject"
        reasons = (
            [
                "source_archetype 在 compatible_archetypes 中",
                "通过 hard rule 检查",
                (
                    f"被选入 {cfg.events_per_persona_min}-{cfg.events_per_persona_max} "
                    "条接受事件集合以满足领域覆盖"
                ),
            ]
            if accepted
            else _candidate_rejection_reasons(
                event,
                accepted_domain_counts,
                cfg=cfg,
            )
        )
        event_ref = _event_reference(event)
        candidates.append(
            {
                **event_ref,
                "candidate_status": "compatible_candidate",
                "decision_after_validation": decision,
                "decision_reasons": reasons,
            }
        )
        candidate_decisions.append(
            {
                **event_ref,
                "decision": decision,
                "reasons": reasons,
            }
        )

    candidate_set = {
        "persona_id": persona_id,
        "source_archetype": archetype_id,
        "candidate_event_count": len(candidate_events),
        "candidates": candidates,
    }
    accepted_set = {
        "persona_id": persona_id,
        "source_archetype": archetype_id,
        "accepted_event_count": len(accepted_events),
        "accepted_event_ids": [str(event["event_category_id"]) for event in accepted_events],
        "domain_counts": dict(sorted(accepted_domain_counts.items())),
        "accepted_events": [_event_reference(event) for event in accepted_events],
    }
    decision_report = {
        "persona_id": persona_id,
        "source_archetype": archetype_id,
        "status": validator_report["status"],
        "candidate_event_count": len(candidate_events),
        "accepted_event_count": len(accepted_events),
        "candidate_decisions": candidate_decisions,
        "validator_report": validator_report,
    }
    return candidate_set, accepted_set, decision_report


def _candidate_rejection_reasons(
    event: dict[str, Any],
    accepted_domain_counts: Counter[str],
    *,
    cfg: P0SamplingConfig,
) -> list[str]:
    domain = str(event.get("event_domain"))
    if accepted_domain_counts[domain] >= cfg.max_events_per_domain_per_persona:
        return [f"同一事件领域已达到每人最多 {cfg.max_events_per_domain_per_persona} 条的上限"]
    return [
        (
            f"本轮保留 {cfg.events_per_persona_min}-{cfg.events_per_persona_max} "
            "条事件预算，优先选择更能补足领域覆盖的候选事件"
        )
    ]


def _build_summary(
    *,
    personas: list[dict[str, Any]],
    candidate_sets: list[dict[str, Any]],
    accepted_sets: list[dict[str, Any]],
    realism_report: dict[str, Any],
) -> dict[str, Any]:
    archetype_counts = Counter(str(persona.get("source_archetype")) for persona in personas)
    accepted_domain_counts: Counter[str] = Counter()
    accepted_event_counts = []
    candidate_event_counts = []
    for item in accepted_sets:
        accepted_event_counts.append(int(item.get("accepted_event_count", 0)))
        accepted_domain_counts.update(item.get("domain_counts", {}))
    for item in candidate_sets:
        candidate_event_counts.append(int(item.get("candidate_event_count", 0)))
    return {
        "persona_count": len(personas),
        "candidate_event_sets": len(candidate_sets),
        "accepted_event_sets": len(accepted_sets),
        "candidate_events_total": sum(candidate_event_counts),
        "accepted_events_total": sum(accepted_event_counts),
        "accepted_events_per_persona_min": min(accepted_event_counts or [0]),
        "accepted_events_per_persona_max": max(accepted_event_counts or [0]),
        "candidate_events_per_persona_min": min(candidate_event_counts or [0]),
        "candidate_events_per_persona_max": max(candidate_event_counts or [0]),
        "source_archetype_counts": dict(sorted(archetype_counts.items())),
        "accepted_event_domain_counts": dict(sorted(accepted_domain_counts.items())),
        "realism_validation_status": realism_report.get("status"),
        "realism_issue_count": len(realism_report.get("issues", [])),
        "realism_warning_count": len(realism_report.get("warnings", [])),
    }


def _event_reference(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_category_id": event.get("event_category_id"),
        "event_domain": event.get("event_domain"),
        "event_type": event.get("event_type"),
        "title": event_category_title_zh(event),
        "core_issue": event_category_summary_zh(event),
    }


def _events_by_domain(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_domain[str(event.get("event_domain"))].append(event)
    return dict(by_domain)


def _choice(archetype: dict[str, Any], key: str, rng: random.Random) -> str:
    values = [str(value) for value in archetype.get(key, []) if value is not None]
    if not values:
        raise ValueError(f"Archetype {archetype.get('archetype_id')} has no {key}.")
    return rng.choice(values)


def _sample_list(values: Any, *, minimum: int, rng: random.Random) -> list[str]:
    items = [str(value) for value in values if value is not None] if isinstance(values, list) else []
    if len(items) <= minimum:
        return items[:]
    maximum = min(len(items), max(minimum, minimum + 1))
    count = rng.randint(minimum, maximum)
    return rng.sample(items, count)
