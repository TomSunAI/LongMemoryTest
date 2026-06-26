from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


REQUIRED_ARCHETYPE_FIELDS = {
    "archetype_id",
    "label",
    "age_range_options",
    "occupation_options",
    "occupation_status_options",
    "education_options",
    "family_structure_options",
    "life_stage_options",
    "economic_condition_options",
    "social_support_options",
    "likely_life_domains",
    "long_term_goal_options",
    "communication_style_options",
    "stress_response_options",
    "decision_style_options",
    "memory_relevant_trait_options",
}

REQUIRED_EVENT_FIELDS = {
    "event_category_id",
    "event_domain",
    "event_type",
    "title",
    "core_issue",
    "compatible_archetypes",
    "incompatible_archetypes",
    "stage_patterns",
    "possible_uncertainties",
    "possible_emotional_load",
    "possible_actions",
    "relational_memory_potential",
    "memory_risks",
}

CHILDCARE_ARCHETYPES = {
    "A03_gig_worker_parent",
    "A05_single_parent_service_worker",
    "A12_early_parenthood_return_to_work",
}
INFANT_CARE_ARCHETYPES = {"A12_early_parenthood_return_to_work"}
ELDERCARE_ARCHETYPES = {"A06_midlife_caregiver"}
ADULT_CHILD_ARCHETYPES = {"A11_adult_child_boundary_family"}
VISA_ADMIN_ARCHETYPES = {"A10_international_student_admin_pressure"}
JOB_SEARCH_ARCHETYPES = {
    "A01_early_career_renter",
    "A07_unemployed_job_seeker",
    "A10_international_student_admin_pressure",
}
RETIREMENT_ROUTINE_ARCHETYPES = {"A09_retirement_adjustment"}
CHILD_RELATED_ARCHETYPES = (
    CHILDCARE_ARCHETYPES | INFANT_CARE_ARCHETYPES | ADULT_CHILD_ARCHETYPES
)
CHILD_RELATED_LIFE_DOMAINS = {"childcare", "infant_care", "adult_child_boundary", "school"}

WORK_FAMILY_DOMAINS = {
    "work",
    "career",
    "family",
    "family_coordination",
    "work_family_intersection",
    "childcare",
    "infant_care",
    "adult_child_boundary",
    "eldercare",
}


@dataclass(frozen=True)
class RealismValidationConfig:
    events_per_persona_min: int = 4
    events_per_persona_max: int = 6
    candidate_events_min: int = 8
    candidate_events_max: int = 12
    min_event_domains_per_persona: int = 3
    max_events_per_domain_per_persona: int = 2
    require_non_work_family_domain: bool = True
    high_autobiography_risk_threshold: int = 4
    medium_autobiography_risk_threshold: int = 3
    max_same_archetype_ratio_in_batch: float = 0.2
    max_researcher_or_student_ratio_in_batch: float = 0.25
    max_child_related_ratio_in_batch: float = 0.35
    min_batch_size_for_ratio_failure: int = 20
    non_work_family_domains: set[str] = field(
        default_factory=lambda: {
            "administration",
            "business",
            "community",
            "commuting",
            "consumer_issue",
            "daily_life",
            "digital_life",
            "education",
            "finance",
            "gig_work",
            "health_routine",
            "housing",
            "job_search",
            "learning",
            "neighborhood",
            "personal_boundary",
            "personal_planning",
            "pet_care",
            "relationship",
            "relocation",
            "retirement",
            "self_worth",
            "social_connection",
            "visa_administration",
        }
    )


def build_realism_validation_report(
    *,
    archetype_pool: dict[str, Any],
    event_pool: dict[str, Any],
    sampled_personas: dict[str, Any] | None = None,
    accepted_event_sets: dict[str, Any] | None = None,
    config: RealismValidationConfig | None = None,
) -> dict[str, Any]:
    """Validate source pools and optional sampled persona-event assignments.

    The report is intended as the P0 gate before generating event lines or natural
    language dialogue. It checks plausibility and coverage, not literary quality.
    """

    cfg = config or RealismValidationConfig()
    pool_report = validate_pool_feasibility(
        archetype_pool=archetype_pool,
        event_pool=event_pool,
        config=cfg,
    )
    batch_report = None
    if sampled_personas is not None or accepted_event_sets is not None:
        batch_report = validate_batch_samples(
            sampled_personas=sampled_personas or {},
            accepted_event_sets=accepted_event_sets or {},
            archetype_pool=archetype_pool,
            event_pool=event_pool,
            config=cfg,
        )

    issues = list(pool_report["issues"])
    warnings = list(pool_report["warnings"])
    if batch_report:
        issues.extend(batch_report["issues"])
        warnings.extend(batch_report["warnings"])

    return {
        "schema_version": "realism_validation_report_v0.1",
        "validation_scope": {
            "pool_feasibility": True,
            "batch_samples": batch_report is not None,
            "language_naturalness": "not_applicable_until_text_generation",
        },
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "pool_report": pool_report,
        "batch_report": batch_report,
    }


def validate_pool_feasibility(
    *,
    archetype_pool: dict[str, Any],
    event_pool: dict[str, Any],
    config: RealismValidationConfig | None = None,
) -> dict[str, Any]:
    cfg = config or RealismValidationConfig()
    archetypes = _extract_archetypes(archetype_pool)
    events = _extract_events(event_pool)
    archetype_ids = [str(item.get("archetype_id", "")) for item in archetypes]
    event_ids = [str(item.get("event_category_id", "")) for item in events]

    issues: list[str] = []
    warnings: list[str] = []
    issues.extend(_duplicate_issues("archetype_id", archetype_ids))
    issues.extend(_duplicate_issues("event_category_id", event_ids))

    for archetype in archetypes:
        missing = sorted(REQUIRED_ARCHETYPE_FIELDS - set(archetype))
        if missing:
            issues.append(f"Archetype {archetype.get('archetype_id')} missing fields: {missing}")
        for key in REQUIRED_ARCHETYPE_FIELDS:
            if key.endswith("_options") or key == "likely_life_domains":
                if not _nonempty_list(archetype.get(key)):
                    issues.append(
                        f"Archetype {archetype.get('archetype_id')} has empty or invalid {key}."
                    )

    known_archetype_ids = set(archetype_ids)
    for event in events:
        event_id = str(event.get("event_category_id", ""))
        missing = sorted(REQUIRED_EVENT_FIELDS - set(event))
        if missing:
            issues.append(f"Event {event_id} missing fields: {missing}")
        compatible = set(_string_list(event.get("compatible_archetypes")))
        incompatible = set(_string_list(event.get("incompatible_archetypes")))
        unknown_refs = sorted((compatible | incompatible) - known_archetype_ids)
        if unknown_refs:
            issues.append(f"Event {event_id} references unknown archetypes: {unknown_refs}")
        overlap = sorted(compatible & incompatible)
        if overlap:
            issues.append(
                f"Event {event_id} has overlapping compatible/incompatible refs: {overlap}"
            )
        if not compatible:
            issues.append(f"Event {event_id} has no compatible_archetypes.")
        if not _has_valid_stage_pattern(event):
            issues.append(f"Event {event_id} has no valid 3+ stage pattern.")
        for key in ["possible_uncertainties", "possible_emotional_load", "possible_actions"]:
            if not _nonempty_list(event.get(key)):
                issues.append(f"Event {event_id} has empty or invalid {key}.")

    archetype_feasibility = []
    events_by_id = {str(event.get("event_category_id")): event for event in events}
    for archetype in archetypes:
        archetype_id = str(archetype.get("archetype_id", ""))
        compatible_events = [
            event
            for event in events
            if _event_is_compatible_with_archetype(event, archetype_id)
            and not _hard_rule_reasons(archetype_id, event)
        ]
        domains = sorted({str(event.get("event_domain")) for event in compatible_events})
        domain_counts = Counter(str(event.get("event_domain")) for event in compatible_events)
        capped_capacity = sum(
            min(count, cfg.max_events_per_domain_per_persona)
            for count in domain_counts.values()
        )
        non_work_family_count = sum(
            count
            for domain, count in domain_counts.items()
            if domain in cfg.non_work_family_domains and domain not in WORK_FAMILY_DOMAINS
        )
        can_satisfy = (
            len(compatible_events) >= cfg.candidate_events_min
            and len(domains) >= cfg.min_event_domains_per_persona
            and capped_capacity >= cfg.events_per_persona_min
            and (
                not cfg.require_non_work_family_domain
                or non_work_family_count >= 1
            )
        )
        if not can_satisfy:
            issues.append(
                "Archetype "
                f"{archetype_id} cannot satisfy event sampling constraints "
                f"(compatible_events={len(compatible_events)}, domains={len(domains)}, "
                f"capped_capacity={capped_capacity}, non_work_family={non_work_family_count})."
            )
        archetype_feasibility.append(
            {
                "archetype_id": archetype_id,
                "compatible_event_count": len(compatible_events),
                "candidate_min_required": cfg.candidate_events_min,
                "domain_count": len(domains),
                "domains": domains,
                "domain_counts": dict(sorted(domain_counts.items())),
                "capped_event_capacity_under_domain_limit": capped_capacity,
                "non_work_family_event_count": non_work_family_count,
                "can_satisfy_p0_sampling_constraints": can_satisfy,
            }
        )

    return {
        "schema_version": "pool_feasibility_report_v0.1",
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "archetype_count": len(archetypes),
            "event_category_count": len(events),
            "event_domain_count": len({str(event.get("event_domain")) for event in events}),
            "archetypes_ready": sum(
                1 for item in archetype_feasibility if item["can_satisfy_p0_sampling_constraints"]
            ),
        },
        "event_domain_distribution": dict(
            sorted(Counter(str(event.get("event_domain")) for event in events).items())
        ),
        "archetype_feasibility": archetype_feasibility,
        "known_event_ids": sorted(events_by_id),
    }


def validate_batch_samples(
    *,
    sampled_personas: dict[str, Any],
    accepted_event_sets: dict[str, Any],
    archetype_pool: dict[str, Any],
    event_pool: dict[str, Any],
    config: RealismValidationConfig | None = None,
) -> dict[str, Any]:
    cfg = config or RealismValidationConfig()
    personas = _extract_personas(sampled_personas)
    sets_by_persona = _extract_event_sets_by_persona(accepted_event_sets)
    archetypes_by_id = {
        str(item.get("archetype_id")): item
        for item in _extract_archetypes(archetype_pool)
        if item.get("archetype_id")
    }
    events_by_id = {
        str(item.get("event_category_id")): item
        for item in _extract_events(event_pool)
        if item.get("event_category_id")
    }

    issues: list[str] = []
    warnings: list[str] = []
    persona_reports = []
    for persona in personas:
        persona_id = str(persona.get("persona_id", ""))
        if not persona_id:
            issues.append("Sampled persona missing persona_id.")
            continue
        event_ids = sets_by_persona.get(persona_id)
        if event_ids is None:
            issues.append(f"Persona {persona_id} has no accepted event set.")
            continue
        report = validate_persona_event_set(
            persona=persona,
            accepted_event_ids=event_ids,
            events_by_id=events_by_id,
            archetypes_by_id=archetypes_by_id,
            config=cfg,
        )
        persona_reports.append(report)
        issues.extend(report["issues"])
        warnings.extend(report["warnings"])

    known_persona_ids = {str(item.get("persona_id")) for item in personas}
    unknown_set_personas = sorted(set(sets_by_persona) - known_persona_ids)
    for persona_id in unknown_set_personas:
        issues.append(f"Accepted event set references unknown persona_id={persona_id}.")

    batch_diversity = _validate_batch_diversity(personas, config=cfg)
    issues.extend(batch_diversity["issues"])
    warnings.extend(batch_diversity["warnings"])

    return {
        "schema_version": "batch_realism_validation_report_v0.1",
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "persona_count": len(personas),
            "persona_event_sets_checked": len(persona_reports),
            "pass_count": sum(1 for item in persona_reports if item["status"] == "pass"),
            "high_autobiography_risk_count": sum(
                1 for item in persona_reports if item["autobiography_risk"]["level"] == "high"
            ),
        },
        "batch_diversity": batch_diversity,
        "persona_reports": persona_reports,
    }


def validate_persona_event_set(
    *,
    persona: dict[str, Any],
    accepted_event_ids: list[str],
    events_by_id: dict[str, dict[str, Any]],
    archetypes_by_id: dict[str, dict[str, Any]],
    config: RealismValidationConfig | None = None,
) -> dict[str, Any]:
    cfg = config or RealismValidationConfig()
    persona_id = str(persona.get("persona_id", "unknown_persona"))
    source_archetype = str(persona.get("source_archetype", ""))
    issues: list[str] = []
    warnings: list[str] = []

    if not source_archetype:
        issues.append(f"Persona {persona_id} missing source_archetype.")
    elif source_archetype not in archetypes_by_id:
        issues.append(
            f"Persona {persona_id} references unknown source_archetype={source_archetype}."
        )

    life_plausibility = _validate_persona_plausibility(
        persona=persona,
        archetype=archetypes_by_id.get(source_archetype, {}),
    )
    issues.extend(life_plausibility["issues"])
    warnings.extend(life_plausibility["warnings"])

    events = []
    for event_id in accepted_event_ids:
        event = events_by_id.get(str(event_id))
        if event is None:
            issues.append(f"Persona {persona_id} references unknown event_id={event_id}.")
            continue
        events.append(event)

    event_checks = []
    for event in events:
        event_id = str(event.get("event_category_id", ""))
        hard_reasons = _hard_rule_reasons(source_archetype, event)
        compatible = _event_is_compatible_with_archetype(event, source_archetype)
        incompatible = source_archetype in set(_string_list(event.get("incompatible_archetypes")))
        decision = "accept"
        reasons = []
        if incompatible:
            decision = "reject"
            reasons.append("source_archetype is explicitly incompatible")
        if not compatible:
            decision = "reject"
            reasons.append("source_archetype is not listed in compatible_archetypes")
        if hard_reasons:
            decision = "reject"
            reasons.extend(hard_reasons)
        if decision == "reject":
            issues.append(f"Persona {persona_id} event {event_id} failed compatibility: {reasons}")
        event_checks.append(
            {
                "event_category_id": event_id,
                "domain": event.get("event_domain"),
                "decision": decision,
                "hard_rule_pass": not hard_reasons and not incompatible,
                "compatible_archetype_pass": compatible,
                "reasons": reasons or ["compatible with source_archetype and hard rules"],
            }
        )

    domain_diversity = _validate_domain_diversity(
        persona_id=persona_id,
        events=events,
        accepted_event_ids=accepted_event_ids,
        config=cfg,
    )
    issues.extend(domain_diversity["issues"])
    warnings.extend(domain_diversity["warnings"])

    causal_coherence = _validate_causal_structure(persona_id=persona_id, events=events)
    issues.extend(causal_coherence["issues"])
    warnings.extend(causal_coherence["warnings"])

    autobiography_risk = _autobiography_risk(
        persona=persona,
        events=events,
        config=cfg,
    )
    if autobiography_risk["level"] == "high":
        issues.append(
            f"Persona {persona_id} high autobiography risk: "
            + ", ".join(autobiography_risk["matched_signals"])
        )
    elif autobiography_risk["level"] == "medium":
        warnings.append(
            f"Persona {persona_id} medium autobiography risk: "
            + ", ".join(autobiography_risk["matched_signals"])
        )

    return {
        "schema_version": "persona_event_realism_report_v0.1",
        "persona_id": persona_id,
        "source_archetype": source_archetype,
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "life_plausibility": life_plausibility,
        "event_compatibility": {
            "status": (
                "pass"
                if all(item["decision"] == "accept" for item in event_checks)
                else "fail"
            ),
            "event_checks": event_checks,
        },
        "domain_diversity": domain_diversity,
        "causal_coherence": causal_coherence,
        "autobiography_risk": autobiography_risk,
        "language_naturalness_review": {
            "status": "pending",
            "reason": "Naturalness requires generated dialogue text or human review sample.",
        },
    }


def _validate_persona_plausibility(
    *,
    persona: dict[str, Any],
    archetype: dict[str, Any],
) -> dict[str, Any]:
    persona_id = str(persona.get("persona_id", "unknown_persona"))
    issues: list[str] = []
    warnings: list[str] = []
    required = {
        "persona_id",
        "source_archetype",
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
    }
    for key in sorted(required):
        value = persona.get(key)
        if value is None or value == "" or value == []:
            issues.append(f"Persona {persona_id} missing or empty {key}.")

    option_checks = {
        "age_range": "age_range_options",
        "occupation": "occupation_options",
        "occupation_status": "occupation_status_options",
        "education_background": "education_options",
        "family_structure": "family_structure_options",
        "life_stage": "life_stage_options",
        "economic_condition": "economic_condition_options",
        "social_support": "social_support_options",
    }
    for persona_key, archetype_key in option_checks.items():
        if not archetype:
            continue
        value = persona.get(persona_key)
        options = set(_string_list(archetype.get(archetype_key)))
        if value and options and str(value) not in options:
            issues.append(
                f"Persona {persona_id} {persona_key}={value!r} is outside {archetype_key}."
            )

    primary_domains = set(_string_list(persona.get("primary_life_domains")))
    likely_domains = set(_string_list(archetype.get("likely_life_domains"))) if archetype else set()
    if primary_domains and likely_domains and not primary_domains <= likely_domains:
        warnings.append(
            f"Persona {persona_id} has primary_life_domains outside archetype likely domains: "
            f"{sorted(primary_domains - likely_domains)}."
        )

    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
    }


def _validate_domain_diversity(
    *,
    persona_id: str,
    events: list[dict[str, Any]],
    accepted_event_ids: list[str],
    config: RealismValidationConfig,
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    event_count = len(accepted_event_ids)
    if event_count < config.events_per_persona_min or event_count > config.events_per_persona_max:
        issues.append(
            f"Persona {persona_id} accepted event count {event_count} outside "
            f"{config.events_per_persona_min}-{config.events_per_persona_max}."
        )
    domain_counts = Counter(str(event.get("event_domain")) for event in events)
    if len(domain_counts) < config.min_event_domains_per_persona:
        issues.append(
            f"Persona {persona_id} covers only {len(domain_counts)} event domains; "
            f"required {config.min_event_domains_per_persona}."
        )
    overloaded = {
        domain: count
        for domain, count in domain_counts.items()
        if count > config.max_events_per_domain_per_persona
    }
    if overloaded:
        issues.append(
            "Persona "
            f"{persona_id} has too many events in one domain: "
            f"{dict(sorted(overloaded.items()))}."
        )
    non_work_family = [
        domain
        for domain in domain_counts
        if domain in config.non_work_family_domains and domain not in WORK_FAMILY_DOMAINS
    ]
    if config.require_non_work_family_domain and not non_work_family:
        issues.append(f"Persona {persona_id} lacks a non-work/family event domain.")
    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "event_count": event_count,
        "domain_counts": dict(sorted(domain_counts.items())),
        "non_work_family_domains": sorted(non_work_family),
    }


def _validate_causal_structure(
    *,
    persona_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    event_checks = []
    for event in events:
        event_id = str(event.get("event_category_id", ""))
        event_issues = []
        if not _has_valid_stage_pattern(event):
            event_issues.append("missing 3+ stage pattern")
        for key in [
            "core_issue",
            "possible_uncertainties",
            "possible_emotional_load",
            "possible_actions",
        ]:
            value = event.get(key)
            if key == "core_issue":
                if not str(value or "").strip():
                    event_issues.append("missing core_issue")
            elif not _nonempty_list(value):
                event_issues.append(f"missing {key}")
        if event_issues:
            issues.append(
                f"Persona {persona_id} event {event_id} "
                f"weak causal structure: {event_issues}"
            )
        event_checks.append(
            {
                "event_category_id": event_id,
                "status": "pass" if not event_issues else "fail",
                "issues": event_issues,
            }
        )
    return {
        "status": "pass" if not issues else "fail",
        "interpretation": (
            "This validates event-category causal ingredients. Full BEI/relational "
            "trajectory coherence is checked after event_lines are constructed."
        ),
        "issues": issues,
        "warnings": warnings,
        "event_checks": event_checks,
    }


def _autobiography_risk(
    *,
    persona: dict[str, Any],
    events: list[dict[str, Any]],
    config: RealismValidationConfig,
) -> dict[str, Any]:
    text = _flatten_text([persona, events]).lower()
    matched = []
    if any(marker in text for marker in ["researcher", "academic", "paper", "grant"]):
        matched.append("researcher_or_academic")
    if _has_child_related_sampling_signal(persona) or _events_have_child_related_signal(events):
        matched.append("child_or_school_pressure")
    if any(
        marker in text
        for marker in ["paper deadline", "paper_deadline", "manuscript", "grant proposal"]
    ):
        matched.append("paper_deadline")
    if any(marker in text for marker in ["collaboration", "collaborator"]):
        matched.append("collaboration_misalignment")
    if any(
        marker in text
        for marker in ["household division", "division of labor", "housework imbalance"]
    ):
        matched.append("spouse_household_division")
    if any(marker in text for marker in ["sleep", "night care", "fragmented"]):
        matched.append("sleep_disruption")
    if any(marker in text for marker in ["kindergarten", "school instability"]):
        matched.append("school_instability")

    if len(matched) >= config.high_autobiography_risk_threshold:
        level = "high"
    elif len(matched) >= config.medium_autobiography_risk_threshold:
        level = "medium"
    else:
        level = "low"
    return {
        "level": level,
        "matched_signal_count": len(matched),
        "matched_signals": matched,
    }


def _validate_batch_diversity(
    personas: list[dict[str, Any]],
    *,
    config: RealismValidationConfig,
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    total = len(personas)
    if total == 0:
        issues.append("No sampled personas provided.")
        return {
            "status": "fail",
            "issues": issues,
            "warnings": warnings,
            "counts": {},
            "ratios": {},
        }
    source_counts = Counter(str(persona.get("source_archetype")) for persona in personas)
    max_archetype_count = max(source_counts.values())
    max_archetype_ratio = max_archetype_count / total
    _record_ratio_excess(
        label="Max same-archetype",
        ratio=max_archetype_ratio,
        limit=config.max_same_archetype_ratio_in_batch,
        total=total,
        config=config,
        issues=issues,
        warnings=warnings,
    )

    researcher_or_student_count = sum(
        1
        for persona in personas
        if any(
            marker in _flatten_text([persona]).lower()
            for marker in ["researcher", "academic", "student"]
        )
    )
    child_related_count = sum(
        1 for persona in personas if _has_child_related_sampling_signal(persona)
    )
    researcher_ratio = researcher_or_student_count / total
    child_related_ratio = child_related_count / total
    _record_ratio_excess(
        label="Researcher/student",
        ratio=researcher_ratio,
        limit=config.max_researcher_or_student_ratio_in_batch,
        total=total,
        config=config,
        issues=issues,
        warnings=warnings,
    )
    _record_ratio_excess(
        label="Child-related",
        ratio=child_related_ratio,
        limit=config.max_child_related_ratio_in_batch,
        total=total,
        config=config,
        issues=issues,
        warnings=warnings,
    )

    age_count = len(
        {str(persona.get("age_range")) for persona in personas if persona.get("age_range")}
    )
    occupation_count = len(
        {str(persona.get("occupation")) for persona in personas if persona.get("occupation")}
    )
    family_count = len(
        {
            str(persona.get("family_structure"))
            for persona in personas
            if persona.get("family_structure")
        }
    )
    if total >= 20 and age_count < 4:
        warnings.append(f"Batch has only {age_count} age ranges; recommended at least 4.")
    if total >= 20 and occupation_count < 6:
        warnings.append(
            f"Batch has only {occupation_count} occupation types; recommended at least 6."
        )
    if total >= 20 and family_count < 5:
        warnings.append(f"Batch has only {family_count} family structures; recommended at least 5.")

    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "counts": {
            "personas": total,
            "source_archetypes": dict(sorted(source_counts.items())),
            "age_range_count": age_count,
            "occupation_count": occupation_count,
            "family_structure_count": family_count,
            "researcher_or_student_count": researcher_or_student_count,
            "child_related_count": child_related_count,
        },
        "ratios": {
            "max_same_archetype_ratio": max_archetype_ratio,
            "researcher_or_student_ratio": researcher_ratio,
            "child_related_ratio": child_related_ratio,
        },
    }


def _record_ratio_excess(
    *,
    label: str,
    ratio: float,
    limit: float,
    total: int,
    config: RealismValidationConfig,
    issues: list[str],
    warnings: list[str],
) -> None:
    if ratio <= limit:
        return
    message = f"{label} ratio {ratio:.2f} exceeds {limit:.2f}."
    if total >= config.min_batch_size_for_ratio_failure:
        issues.append(message)
        return
    warnings.append(
        f"{message} Treated as a small-demo warning because batch size "
        f"{total} is below {config.min_batch_size_for_ratio_failure}."
    )


def _has_child_related_sampling_signal(persona: dict[str, Any]) -> bool:
    source_archetype = str(persona.get("source_archetype", ""))
    if source_archetype in CHILD_RELATED_ARCHETYPES:
        return True
    primary_domains = set(_string_list(persona.get("primary_life_domains")))
    return bool(primary_domains & CHILD_RELATED_LIFE_DOMAINS)


def _events_have_child_related_signal(events: list[dict[str, Any]]) -> bool:
    for event in events:
        domain = str(event.get("event_domain", ""))
        if domain in CHILD_RELATED_LIFE_DOMAINS:
            return True
        event_type = str(event.get("event_type", "")).lower()
        if any(
            marker in event_type
            for marker in [
                "child_school",
                "childcare",
                "infant",
                "adult_child",
                "school_instability",
            ]
        ):
            return True
    return False


def _hard_rule_reasons(archetype_id: str, event: dict[str, Any]) -> list[str]:
    domain = str(event.get("event_domain", ""))
    event_type = str(event.get("event_type", ""))
    reasons = []
    if domain == "childcare" and archetype_id not in CHILDCARE_ARCHETYPES:
        reasons.append("childcare events require a parent/childcare archetype")
    if domain == "infant_care" and archetype_id not in INFANT_CARE_ARCHETYPES:
        reasons.append("infant_care events require early-parenthood archetype")
    if domain == "eldercare" and archetype_id not in ELDERCARE_ARCHETYPES:
        reasons.append("eldercare events require midlife caregiver archetype")
    if domain == "adult_child_boundary" and archetype_id not in ADULT_CHILD_ARCHETYPES:
        reasons.append("adult_child_boundary events require adult-child boundary archetype")
    if domain == "visa_administration" and archetype_id not in VISA_ADMIN_ARCHETYPES:
        reasons.append("visa_administration events require international-student archetype")
    if domain == "job_search" and archetype_id not in JOB_SEARCH_ARCHETYPES:
        reasons.append("job_search events require A01/A07/A10 archetype")
    if (
        event_type == "retirement_routine_and_identity"
        and archetype_id not in RETIREMENT_ROUTINE_ARCHETYPES
    ):
        reasons.append("retirement routine/identity event requires retirement archetype")
    return reasons


def _event_is_compatible_with_archetype(event: dict[str, Any], archetype_id: str) -> bool:
    compatible = set(_string_list(event.get("compatible_archetypes")))
    incompatible = set(_string_list(event.get("incompatible_archetypes")))
    return archetype_id in compatible and archetype_id not in incompatible


def _extract_archetypes(pool: dict[str, Any]) -> list[dict[str, Any]]:
    archetypes = pool.get("archetypes", [])
    return [item for item in archetypes if isinstance(item, dict)]


def _extract_events(pool: dict[str, Any]) -> list[dict[str, Any]]:
    events = pool.get("event_categories", [])
    return [item for item in events if isinstance(item, dict)]


def _extract_personas(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ["personas", "sampled_personas"]:
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(data.get("persona_id"), str):
        return [data]
    return []


def _extract_event_sets_by_persona(data: dict[str, Any]) -> dict[str, list[str]]:
    for key in ["accepted_persona_event_sets", "event_sets", "persona_event_sets"]:
        value = data.get(key)
        if isinstance(value, list):
            return _event_sets_list_to_mapping(value)
    value = data.get("event_sets_by_persona")
    if isinstance(value, dict):
        return {
            str(persona_id): [str(item) for item in event_ids]
            for persona_id, event_ids in value.items()
            if isinstance(event_ids, list)
        }
    if isinstance(data.get("persona_id"), str):
        event_ids = data.get("accepted_event_ids") or data.get("event_category_ids") or []
        if isinstance(event_ids, list):
            return {str(data["persona_id"]): [str(item) for item in event_ids]}
    return {}


def _event_sets_list_to_mapping(items: list[Any]) -> dict[str, list[str]]:
    result = {}
    for item in items:
        if not isinstance(item, dict) or not item.get("persona_id"):
            continue
        event_ids = item.get("accepted_event_ids") or item.get("event_category_ids") or []
        if isinstance(event_ids, list):
            result[str(item["persona_id"])] = [str(event_id) for event_id in event_ids]
    return result


def _duplicate_issues(label: str, values: list[str]) -> list[str]:
    counts = Counter(values)
    return [
        f"Duplicate {label}: {value}"
        for value, count in sorted(counts.items())
        if value and count > 1
    ]


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item)]


def _has_valid_stage_pattern(event: dict[str, Any]) -> bool:
    patterns = event.get("stage_patterns")
    if not isinstance(patterns, list):
        return False
    for pattern in patterns:
        if isinstance(pattern, list) and len([item for item in pattern if str(item)]) >= 3:
            return True
    return False


def _flatten_text(items: Any) -> str:
    if isinstance(items, dict):
        return " ".join(_flatten_text(value) for value in items.values())
    if isinstance(items, list):
        return " ".join(_flatten_text(item) for item in items)
    if items is None:
        return ""
    return str(items)
