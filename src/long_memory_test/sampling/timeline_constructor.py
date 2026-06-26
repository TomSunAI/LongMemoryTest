from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TimelineConstructionConfig:
    random_seed: int = 20260701
    timeline_days: int = 30
    active_sessions_min: int = 15
    active_sessions_max: int = 20
    event_line_occurrences_min: int = 3
    event_line_occurrences_max: int = 6
    max_events_per_active_day: int = 2
    parallel_event_days_min: int = 2
    probe_candidate_min_per_persona: int = 14
    daily_event_count_distribution: dict[int, int] | None = None
    daily_event_count_median_target: float | None = None
    allow_stage_reuse_after_sequence: bool = False


def construct_timeline_for_batch(
    *,
    event_lines_batch: dict[str, Any],
    config: TimelineConstructionConfig | None = None,
) -> dict[str, Any]:
    cfg = config or TimelineConstructionConfig()
    rng = random.Random(cfg.random_seed)
    persona_payloads = [
        item for item in event_lines_batch.get("personas", []) if isinstance(item, dict)
    ]
    timelines = []
    for payload in persona_payloads:
        timelines.append(_construct_persona_timeline(payload=payload, cfg=cfg, rng=rng))

    summary = _summarize_timelines(timelines)
    validation = validate_timeline(
        {
            "timelines": timelines,
            "construction_config": asdict(cfg),
        }
    )
    return {
        "schema_version": "timeline_batch_v0.1",
        "sampling_stage": "P1_timeline_construction",
        "construction_scope": {
            "from_event_lines_batch": True,
            "timeline_constructed": True,
            "daily_interactions_constructed": False,
            "probe_plan_constructed": False,
        },
        "construction_config": asdict(cfg),
        "summary": summary,
        "validation": validation,
        "timelines": timelines,
    }


def validate_timeline(timeline_batch: dict[str, Any]) -> dict[str, Any]:
    cfg_data = timeline_batch.get("construction_config", {})
    cfg = TimelineConstructionConfig(
        random_seed=int(cfg_data.get("random_seed", 20260701)),
        timeline_days=int(cfg_data.get("timeline_days", 30)),
        active_sessions_min=int(cfg_data.get("active_sessions_min", 15)),
        active_sessions_max=int(cfg_data.get("active_sessions_max", 20)),
        event_line_occurrences_min=int(cfg_data.get("event_line_occurrences_min", 3)),
        event_line_occurrences_max=int(cfg_data.get("event_line_occurrences_max", 6)),
        max_events_per_active_day=int(cfg_data.get("max_events_per_active_day", 2)),
        parallel_event_days_min=int(cfg_data.get("parallel_event_days_min", 2)),
        probe_candidate_min_per_persona=int(cfg_data.get("probe_candidate_min_per_persona", 14)),
        daily_event_count_distribution=_daily_event_count_distribution_from_value(
            cfg_data.get("daily_event_count_distribution")
        ),
        daily_event_count_median_target=_optional_float(
            cfg_data.get("daily_event_count_median_target")
        ),
        allow_stage_reuse_after_sequence=bool(
            cfg_data.get("allow_stage_reuse_after_sequence", False)
        ),
    )
    issues: list[str] = []
    warnings: list[str] = []
    for persona_timeline in timeline_batch.get("timelines", []):
        if not isinstance(persona_timeline, dict):
            issues.append("Invalid persona timeline entry.")
            continue
        persona_id = str(persona_timeline.get("persona_id", ""))
        days = [item for item in persona_timeline.get("days", []) if isinstance(item, dict)]
        if len(days) != cfg.timeline_days:
            issues.append(
                f"{persona_id} has {len(days)} days; expected {cfg.timeline_days}."
            )
        active_days = [day for day in days if day.get("active")]
        active_day_count = len(active_days)
        event_occurrences_by_day = {
            int(day.get("day", 0)): _day_event_occurrences(day)
            for day in active_days
        }
        active_session_count = sum(len(items) for items in event_occurrences_by_day.values())
        calendar_event_counts = [
            len(_day_event_occurrences(day)) if day.get("active") else 0
            for day in days
        ]
        if cfg.daily_event_count_distribution is not None:
            actual_distribution = Counter(calendar_event_counts)
            expected_distribution = cfg.daily_event_count_distribution
            if dict(sorted(actual_distribution.items())) != dict(sorted(expected_distribution.items())):
                issues.append(
                    f"{persona_id} daily event count distribution "
                    f"{dict(sorted(actual_distribution.items()))}; expected "
                    f"{dict(sorted(expected_distribution.items()))}."
                )
            median = _median(calendar_event_counts)
            if (
                cfg.daily_event_count_median_target is not None
                and median != cfg.daily_event_count_median_target
            ):
                issues.append(
                    f"{persona_id} daily event count median is {median}; expected "
                    f"{cfg.daily_event_count_median_target}."
                )
        if active_session_count < cfg.active_sessions_min or active_session_count > cfg.active_sessions_max:
            issues.append(
                f"{persona_id} has {active_session_count} active sessions; expected "
                f"{cfg.active_sessions_min}-{cfg.active_sessions_max}."
            )
        if int(persona_timeline.get("active_session_count", active_session_count)) != active_session_count:
            issues.append(f"{persona_id} active_session_count does not match event occurrences.")
        if int(persona_timeline.get("active_day_count", active_day_count)) != active_day_count:
            issues.append(f"{persona_id} active_day_count does not match active days.")
        seen_days = set()
        for day in active_days:
            day_number = int(day.get("day", 0))
            if day_number in seen_days:
                issues.append(f"{persona_id} has duplicate active day {day_number}.")
            seen_days.add(day_number)
            occurrences = event_occurrences_by_day[day_number]
            if not occurrences:
                issues.append(f"{persona_id} day {day_number} is active but has no event occurrences.")
            if len(occurrences) > cfg.max_events_per_active_day:
                issues.append(
                    f"{persona_id} day {day_number} has {len(occurrences)} events; "
                    f"expected at most {cfg.max_events_per_active_day}."
                )
            line_ids_on_day = [str(item.get("event_line_id")) for item in occurrences]
            duplicate_lines = sorted(
                line_id for line_id, count in Counter(line_ids_on_day).items() if count > 1
            )
            if duplicate_lines:
                issues.append(
                    f"{persona_id} day {day_number} repeats event lines: {duplicate_lines}."
                )
        all_occurrences = [
            occurrence
            for day in active_days
            for occurrence in event_occurrences_by_day[int(day.get("day", 0))]
        ]
        parallel_day_count = sum(
            1 for occurrences in event_occurrences_by_day.values() if len(occurrences) > 1
        )
        if (
            cfg.max_events_per_active_day > 1
            and active_session_count > active_day_count
            and parallel_day_count < cfg.parallel_event_days_min
        ):
            issues.append(
                f"{persona_id} has {parallel_day_count} parallel event days; expected at least "
                f"{cfg.parallel_event_days_min}."
            )
        counts = Counter(str(occurrence.get("event_line_id")) for occurrence in all_occurrences)
        for event_line_id, count in counts.items():
            if count < cfg.event_line_occurrences_min or count > cfg.event_line_occurrences_max:
                issues.append(
                    f"{persona_id}/{event_line_id} occurs {count} times; expected "
                    f"{cfg.event_line_occurrences_min}-{cfg.event_line_occurrences_max}."
                )
        stages_by_line: dict[str, list[int]] = defaultdict(list)
        occurrence_indexes_by_line: dict[str, list[int]] = defaultdict(list)
        for day in active_days:
            for occurrence in event_occurrences_by_day[int(day.get("day", 0))]:
                line_id = str(occurrence.get("event_line_id"))
                stages_by_line[line_id].append(int(occurrence.get("stage_index", 0)))
                occurrence_indexes_by_line[line_id].append(int(occurrence.get("occurrence_index", 0)))
        for event_line_id, stage_indexes in stages_by_line.items():
            if stage_indexes != sorted(stage_indexes):
                issues.append(f"{persona_id}/{event_line_id} stage order is not monotonic.")
            if stage_indexes and stage_indexes[0] != 1:
                issues.append(f"{persona_id}/{event_line_id} does not start at stage 1.")
            occurrence_indexes = occurrence_indexes_by_line[event_line_id]
            if occurrence_indexes != list(range(1, len(occurrence_indexes) + 1)):
                issues.append(f"{persona_id}/{event_line_id} occurrence indexes are not continuous.")
    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
    }


def _construct_persona_timeline(
    *,
    payload: dict[str, Any],
    cfg: TimelineConstructionConfig,
    rng: random.Random,
) -> dict[str, Any]:
    persona_ref = payload.get("persona_ref", {})
    persona_id = str(persona_ref.get("persona_id"))
    event_lines = [
        item for item in payload.get("event_lines", []) if isinstance(item, dict)
    ]
    if not event_lines:
        raise ValueError(f"{persona_id} has no event lines.")
    daily_event_counts = _daily_event_counts_for_persona(cfg=cfg, rng=rng)
    occurrence_counts = _assign_occurrence_counts(
        event_lines=event_lines,
        cfg=cfg,
        rng=rng,
        target_total=sum(daily_event_counts) if daily_event_counts is not None else None,
    )
    tokens = _interleaved_tokens(
        event_lines=event_lines,
        occurrence_counts=occurrence_counts,
        rng=rng,
    )
    if daily_event_counts is None:
        active_day_count = _active_day_count_for_tokens(token_count=len(tokens), cfg=cfg)
        active_days = _spread_days(count=active_day_count, timeline_days=cfg.timeline_days, rng=rng)
        tokens_by_day = _pack_tokens_into_days(
            tokens=tokens,
            active_days=active_days,
            cfg=cfg,
            rng=rng,
        )
    else:
        active_days = [
            day
            for day, count in enumerate(daily_event_counts, start=1)
            if count > 0
        ]
        tokens_by_day = _pack_tokens_into_daily_event_counts(
            tokens=tokens,
            daily_event_counts=daily_event_counts,
            cfg=cfg,
            rng=rng,
        )
    scheduled_days_by_line: defaultdict[str, list[int]] = defaultdict(list)
    active_day_map = {}
    for day in active_days:
        occurrences = [
            _build_event_occurrence(
                persona_id=persona_id,
                day=day,
                within_day_index=within_day_index,
                token=token,
                occurrence_counts=occurrence_counts,
                scheduled_days_by_line=scheduled_days_by_line,
                cfg=cfg,
            )
            for within_day_index, token in enumerate(tokens_by_day[day], start=1)
        ]
        active_day_map[day] = _build_active_day_from_occurrences(
            persona_id=persona_id,
            day=day,
            occurrences=occurrences,
        )
    days = [
        active_day_map.get(day, {"day": day, "active": False, "event_occurrences": []})
        for day in range(1, cfg.timeline_days + 1)
    ]
    parallel_day_count = sum(
        1 for day in active_day_map.values() if int(day.get("parallel_event_count", 0)) > 1
    )
    return {
        "persona_id": persona_id,
        "persona_ref": persona_ref,
        "timeline_days": cfg.timeline_days,
        "active_session_count": len(tokens),
        "active_day_count": len(active_days),
        "event_occurrence_total": len(tokens),
        "parallel_event_day_count": parallel_day_count,
        "event_line_count": len(event_lines),
        "event_line_occurrence_counts": dict(sorted(occurrence_counts.items())),
        "days": days,
    }


def _assign_occurrence_counts(
    *,
    event_lines: list[dict[str, Any]],
    cfg: TimelineConstructionConfig,
    rng: random.Random,
    target_total: int | None = None,
) -> dict[str, int]:
    line_ids = [str(line.get("event_line_id")) for line in event_lines]
    min_total = len(line_ids) * cfg.event_line_occurrences_min
    stage_capacity = sum(_line_occurrence_capacity(line=line, cfg=cfg) for line in event_lines)
    probe_candidate_floor = len(line_ids) + max(0, cfg.probe_candidate_min_per_persona)
    lower = max(cfg.active_sessions_min, min_total, probe_candidate_floor)
    upper = min(
        cfg.active_sessions_max,
        stage_capacity,
        cfg.timeline_days * max(1, cfg.max_events_per_active_day),
    )
    if target_total is not None:
        if target_total < lower or target_total > upper:
            raise ValueError(
                "Cannot satisfy fixed daily event distribution: "
                f"target_total={target_total}, lower={lower}, upper={upper}, "
                f"stage_capacity={stage_capacity}."
            )
        lower = upper = target_total
    if lower > upper:
        raise ValueError(
            "Cannot satisfy timeline constraints: "
            f"min_total={min_total}, active_range={cfg.active_sessions_min}-{cfg.active_sessions_max}, "
            f"probe_candidate_floor={probe_candidate_floor}, stage_capacity={stage_capacity}, "
            f"timeline_days={cfg.timeline_days}."
        )
    target_total = target_total if target_total is not None else rng.randint(lower, upper)
    counts = {line_id: cfg.event_line_occurrences_min for line_id in line_ids}
    remaining = target_total - min_total
    shuffled_lines = event_lines[:]
    while remaining > 0:
        rng.shuffle(shuffled_lines)
        progressed = False
        for line in shuffled_lines:
            line_id = str(line.get("event_line_id"))
            capacity = _line_occurrence_capacity(line=line, cfg=cfg)
            if counts[line_id] >= capacity:
                continue
            counts[line_id] += 1
            remaining -= 1
            progressed = True
            if remaining == 0:
                break
        if not progressed:
            raise ValueError("No event line capacity left while assigning timeline occurrences.")
    return counts


def _line_occurrence_capacity(
    *,
    line: dict[str, Any],
    cfg: TimelineConstructionConfig,
) -> int:
    if cfg.allow_stage_reuse_after_sequence:
        return cfg.event_line_occurrences_max
    return min(cfg.event_line_occurrences_max, len(_stage_sequence(line)))


def _daily_event_counts_for_persona(
    *,
    cfg: TimelineConstructionConfig,
    rng: random.Random,
) -> list[int] | None:
    distribution = cfg.daily_event_count_distribution
    if distribution is None:
        return None
    if sum(distribution.values()) != cfg.timeline_days:
        raise ValueError(
            "daily_event_count_distribution must sum to timeline_days: "
            f"{sum(distribution.values())} != {cfg.timeline_days}."
        )
    max_events_per_day = max(1, cfg.max_events_per_active_day)
    counts = []
    for event_count, day_count in sorted(distribution.items()):
        if event_count < 0 or event_count > max_events_per_day:
            raise ValueError(
                f"daily_event_count_distribution has event count {event_count}; "
                f"expected 0-{max_events_per_day}."
            )
        if day_count < 0:
            raise ValueError("daily_event_count_distribution cannot contain negative day counts.")
        counts.extend([event_count] * day_count)
    rng.shuffle(counts)
    median = _median(counts)
    if (
        cfg.daily_event_count_median_target is not None
        and median != cfg.daily_event_count_median_target
    ):
        raise ValueError(
            f"daily_event_count_distribution median is {median}; expected "
            f"{cfg.daily_event_count_median_target}."
        )
    return counts


def _interleaved_tokens(
    *,
    event_lines: list[dict[str, Any]],
    occurrence_counts: dict[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    ordered_lines = event_lines[:]
    rng.shuffle(ordered_lines)
    tokens = []
    max_occurrences = max(occurrence_counts.values())
    for occurrence_index in range(1, max_occurrences + 1):
        round_lines = ordered_lines[:]
        rng.shuffle(round_lines)
        for line in round_lines:
            line_id = str(line.get("event_line_id"))
            if occurrence_counts[line_id] < occurrence_index:
                continue
            tokens.append(
                {
                    "event_line": line,
                    "occurrence_index": occurrence_index,
                }
            )
    return tokens


def _spread_days(*, count: int, timeline_days: int, rng: random.Random) -> list[int]:
    if count > timeline_days:
        raise ValueError(f"Cannot place {count} sessions in {timeline_days} days.")
    if count == 1:
        return [1]
    days: list[int] = []
    used: set[int] = set()
    for index in range(count):
        base = 1 + round(index * (timeline_days - 1) / (count - 1))
        candidates = [base, base - 1, base + 1, base - 2, base + 2]
        rng.shuffle(candidates)
        selected = None
        for candidate in candidates:
            if 1 <= candidate <= timeline_days and candidate not in used:
                selected = candidate
                break
        if selected is None:
            for candidate in range(1, timeline_days + 1):
                if candidate not in used:
                    selected = candidate
                    break
        if selected is None:
            raise ValueError("Could not allocate unique timeline day.")
        used.add(selected)
        days.append(selected)
    return sorted(days)


def _active_day_count_for_tokens(
    *,
    token_count: int,
    cfg: TimelineConstructionConfig,
) -> int:
    if token_count <= 0:
        return 0
    max_events_per_day = max(1, cfg.max_events_per_active_day)
    min_day_count = (token_count + max_events_per_day - 1) // max_events_per_day
    max_day_count = min(token_count, cfg.timeline_days)
    if max_day_count < min_day_count:
        raise ValueError(
            f"Cannot place {token_count} sessions in {cfg.timeline_days} days "
            f"with max_events_per_active_day={max_events_per_day}."
        )
    desired_parallel_days = min(
        max(0, cfg.parallel_event_days_min),
        max(0, token_count - min_day_count),
    )
    desired_day_count = token_count - desired_parallel_days
    return max(min_day_count, min(max_day_count, desired_day_count))


def _pack_tokens_into_days(
    *,
    tokens: list[dict[str, Any]],
    active_days: list[int],
    cfg: TimelineConstructionConfig,
    rng: random.Random,
) -> dict[int, list[dict[str, Any]]]:
    max_events_per_day = max(1, cfg.max_events_per_active_day)
    if len(tokens) > len(active_days) * max_events_per_day:
        raise ValueError(
            f"Cannot pack {len(tokens)} sessions into {len(active_days)} active days "
            f"with max_events_per_active_day={max_events_per_day}."
        )
    bins: dict[int, list[dict[str, Any]]] = {day: [] for day in active_days}
    last_day_by_line: dict[str, int] = {}
    day_indexes = list(range(len(active_days)))
    for token_index, token in enumerate(tokens):
        preferred = (
            0
            if len(tokens) == 1
            else round(token_index * (len(active_days) - 1) / (len(tokens) - 1))
        )
        candidates = sorted(
            day_indexes,
            key=lambda index: (abs(index - preferred), index),
        )
        equal_distance_groups: dict[int, list[int]] = defaultdict(list)
        for index in candidates:
            equal_distance_groups[abs(index - preferred)].append(index)
        candidates = []
        for distance in sorted(equal_distance_groups):
            group = equal_distance_groups[distance]
            rng.shuffle(group)
            candidates.extend(sorted(group))
        selected_day = None
        line_id = str(token["event_line"].get("event_line_id"))
        token_is_probe_candidate = int(token.get("occurrence_index", 0)) >= 2
        for avoid_candidate_collision in (True, False):
            for day_index in candidates:
                day = active_days[day_index]
                if len(bins[day]) >= max_events_per_day:
                    continue
                if any(str(item["event_line"].get("event_line_id")) == line_id for item in bins[day]):
                    continue
                if day <= last_day_by_line.get(line_id, 0):
                    continue
                if avoid_candidate_collision and token_is_probe_candidate and any(
                    int(item.get("occurrence_index", 0)) >= 2 for item in bins[day]
                ):
                    continue
                selected_day = day
                break
            if selected_day is not None:
                break
        if selected_day is None:
            raise ValueError(f"Could not allocate timeline day for event line {line_id}.")
        bins[selected_day].append(token)
        last_day_by_line[line_id] = selected_day
    return bins


def _pack_tokens_into_daily_event_counts(
    *,
    tokens: list[dict[str, Any]],
    daily_event_counts: list[int],
    cfg: TimelineConstructionConfig,
    rng: random.Random,
) -> dict[int, list[dict[str, Any]]]:
    if len(daily_event_counts) != cfg.timeline_days:
        raise ValueError(
            f"daily_event_counts has {len(daily_event_counts)} days; "
            f"expected {cfg.timeline_days}."
        )
    if sum(daily_event_counts) != len(tokens):
        raise ValueError(
            f"Cannot pack {len(tokens)} tokens into daily counts totaling "
            f"{sum(daily_event_counts)}."
        )
    max_events_per_day = max(1, cfg.max_events_per_active_day)
    for day, count in enumerate(daily_event_counts, start=1):
        if count < 0 or count > max_events_per_day:
            raise ValueError(
                f"Day {day} has target count {count}; expected 0-{max_events_per_day}."
            )
    active_days = [
        day
        for day, count in enumerate(daily_event_counts, start=1)
        if count > 0
    ]
    capacities = {
        day: daily_event_counts[day - 1]
        for day in active_days
    }
    bins: dict[int, list[dict[str, Any]]] = {day: [] for day in active_days}
    slot_days = [
        day
        for day in active_days
        for _ in range(capacities[day])
    ]
    last_day_by_line: dict[str, int] = {}
    for token_index, token in enumerate(tokens):
        preferred_day = slot_days[token_index]
        candidates = sorted(
            active_days,
            key=lambda day: (abs(day - preferred_day), day),
        )
        equal_distance_groups: dict[int, list[int]] = defaultdict(list)
        for day in candidates:
            equal_distance_groups[abs(day - preferred_day)].append(day)
        candidates = []
        for distance in sorted(equal_distance_groups):
            group = equal_distance_groups[distance]
            rng.shuffle(group)
            candidates.extend(sorted(group))
        selected_day = None
        line_id = str(token["event_line"].get("event_line_id"))
        for day in candidates:
            if len(bins[day]) >= capacities[day]:
                continue
            if any(str(item["event_line"].get("event_line_id")) == line_id for item in bins[day]):
                continue
            if day <= last_day_by_line.get(line_id, 0):
                continue
            selected_day = day
            break
        if selected_day is None:
            raise ValueError(
                f"Could not allocate high-density timeline day for event line {line_id}."
            )
        bins[selected_day].append(token)
        last_day_by_line[line_id] = selected_day
    return bins


def _build_event_occurrence(
    *,
    persona_id: str,
    day: int,
    within_day_index: int,
    token: dict[str, Any],
    occurrence_counts: dict[str, int],
    scheduled_days_by_line: defaultdict[str, list[int]],
    cfg: TimelineConstructionConfig,
) -> dict[str, Any]:
    line = token["event_line"]
    occurrence_index = int(token["occurrence_index"])
    stage = _stage_for_occurrence(line=line, occurrence_index=occurrence_index, cfg=cfg)
    event_line_id = str(line.get("event_line_id"))
    interaction_unit_id = f"{persona_id}_D{day:02d}_M{within_day_index:03d}"
    event_occurrence_id = f"{persona_id}_D{day:02d}_E{within_day_index:03d}"
    related_previous_days = [
        prior_day
        for prior_day in scheduled_days_by_line[event_line_id]
        if isinstance(prior_day, int)
    ]
    scheduled_days_by_line[event_line_id].append(day)
    return {
        "day": day,
        "active": True,
        "event_occurrence_id": event_occurrence_id,
        "within_day_index": within_day_index,
        "interaction_unit_id": interaction_unit_id,
        "persona_id": persona_id,
        "event_line_id": event_line_id,
        "event_category_id": line.get("event_category_id"),
        "event_domain": line.get("event_domain"),
        "event_domain_zh": line.get("event_domain_zh"),
        "event_title": line.get("event_title", {}),
        "persistent_event_summary": line.get("persistent_event_summary"),
        "persistent_event_summary_zh": line.get("persistent_event_summary_zh"),
        "occurrence_index": occurrence_index,
        "occurrence_count_for_line": occurrence_counts[event_line_id],
        "stage_index": int(stage.get("stage_index", occurrence_index)),
        "event_stage": stage.get("event_stage"),
        "stage_goal": stage.get("stage_goal"),
        "stage_goal_zh": stage.get("stage_goal_zh"),
        "surface_event": stage.get("user_message_seed"),
        "surface_event_zh": stage.get("user_message_seed_zh"),
        "assistant_memory_expectation": stage.get("assistant_memory_expectation"),
        "assistant_memory_expectation_zh": stage.get("assistant_memory_expectation_zh"),
        "latent_continuity": _latent_continuity(stage),
        "latent_continuity_zh": _latent_continuity_zh(stage),
        "related_previous_days": related_previous_days,
        "previous_occurrence_day": related_previous_days[-1] if related_previous_days else None,
        "probe_candidate": occurrence_index >= 2,
        "allowed_base_facts": stage.get("allowed_base_facts", []),
        "allowed_base_facts_zh": stage.get("allowed_base_facts_zh", []),
        "event_candidate_facts": stage.get("event_candidate_facts", []),
        "persona_conditioned_facts": stage.get("persona_conditioned_facts", []),
        "stage_delta_facts": stage.get("stage_delta_facts", []),
        "allowed_new_facts": stage.get("allowed_new_facts", []),
        "allowed_new_facts_zh": stage.get("allowed_new_facts_zh", []),
        "prohibited_facts": stage.get("prohibited_facts", []),
        "prohibited_facts_zh": stage.get("prohibited_facts_zh", []),
    }


def _build_active_day_from_occurrences(
    *,
    persona_id: str,
    day: int,
    occurrences: list[dict[str, Any]],
) -> dict[str, Any]:
    if not occurrences:
        raise ValueError(f"{persona_id} day {day} has no event occurrences.")
    primary = occurrences[0]
    result = {
        "day": day,
        "active": True,
        "persona_id": persona_id,
        "day_interaction_unit_id": f"{persona_id}_D{day:02d}",
        "event_occurrences": occurrences,
        "parallel_event_count": len(occurrences),
        "has_parallel_events": len(occurrences) > 1,
        "primary_event_occurrence_id": primary.get("event_occurrence_id"),
    }
    for key, value in primary.items():
        result.setdefault(key, value)
    return result


def _day_event_occurrences(day: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = [
        item for item in day.get("event_occurrences", []) if isinstance(item, dict)
    ]
    if occurrences:
        return occurrences
    if day.get("active"):
        return [day]
    return []


def _latent_continuity(stage: dict[str, Any]) -> str:
    expectation = str(stage.get("assistant_memory_expectation", ""))
    if expectation:
        return expectation
    return "Continue the same event line within the fact boundary."


def _latent_continuity_zh(stage: dict[str, Any]) -> str:
    expectation = str(stage.get("assistant_memory_expectation_zh", ""))
    if expectation:
        return expectation
    return "承接同一事件线，在事实边界内继续。"


def _stage_for_occurrence(
    *,
    line: dict[str, Any],
    occurrence_index: int,
    cfg: TimelineConstructionConfig,
) -> dict[str, Any]:
    stages = _stage_sequence(line)
    if occurrence_index <= len(stages):
        return stages[occurrence_index - 1]
    if not cfg.allow_stage_reuse_after_sequence:
        raise ValueError(
            f"Event line {line.get('event_line_id')} has only {len(stages)} stages; "
            f"cannot build occurrence {occurrence_index}."
        )
    return _extended_stage(line=line, occurrence_index=occurrence_index, stages=stages)


def _extended_stage(
    *,
    line: dict[str, Any],
    occurrence_index: int,
    stages: list[dict[str, Any]],
) -> dict[str, Any]:
    cycle = ["recurrence", "turning_point", "partial_resolution", "reflection"]
    event_stage = cycle[(occurrence_index - len(stages) - 1) % len(cycle)]
    base = next(
        (stage for stage in stages if stage.get("event_stage") == event_stage),
        stages[-1],
    )
    title = _line_title(line)
    title_zh = _line_title_zh(line)
    stage_goal = {
        "recurrence": "The event line appears again; the user wants continuity rather than restarting the explanation.",
        "turning_point": "A new small change appears in the event line; the user needs to recalibrate priorities or boundaries.",
        "partial_resolution": "The user has made partial progress and needs to check remaining risks and the next step.",
        "reflection": "The user reviews this line to extract a reusable pattern or confirm relational boundaries.",
    }[event_stage]
    stage_goal_zh = {
        "recurrence": "事件线继续反复出现，用户希望助手承接前序而不是重启解释。",
        "turning_point": "事件线出现新的小变化，用户需要重新校准优先级或边界。",
        "partial_resolution": "用户已经推进一部分处理，需要检查剩余风险和下一步。",
        "reflection": "用户回看这条线，抽取可复用模式或确认关系边界。",
    }[event_stage]
    user_message = {
        "recurrence": (
            f"The \"{title}\" issue we have discussed before came up again today. "
            "I do not want to explain it from scratch; continue from the earlier handling approach."
        ),
        "turning_point": (
            f"The \"{title}\" line has a new change today. "
            "Help me judge whether this means the priority should change."
        ),
        "partial_resolution": (
            f"I made a bit more progress on the \"{title}\" line, but it is not fully resolved. "
            "Help me identify the most important remaining gap."
        ),
        "reflection": (
            f"I want to review the \"{title}\" line. "
            "Help me summarize a handling method I can reuse later."
        ),
    }[event_stage]
    user_message_zh = {
        "recurrence": (
            f"之前反复说过的「{title_zh}」今天又冒出来了。"
            "我不想从头解释，你接着前面的处理方式帮我看。"
        ),
        "turning_point": (
            f"「{title_zh}」这条线今天又有了一个新变化。"
            "你帮我判断这是不是说明优先级要调整。"
        ),
        "partial_resolution": (
            f"「{title_zh}」这条线我又推进了一点，但还没完全结束。"
            "你帮我看现在最该补哪个缺口。"
        ),
        "reflection": (
            f"我想回看一下「{title_zh}」这条线。"
            "你帮我总结一个之后还能复用的处理方式。"
        ),
    }[event_stage]
    expectation = {
        "recurrence": "Continue the same event line and previous handling strategy; do not ask the user to restate the background.",
        "turning_point": "Identify the difference between the current change and previous state, then recalibrate advice.",
        "partial_resolution": "Continue from what has been handled, check remaining gaps, and do not add unprovided facts.",
        "reflection": "Extract a reusable pattern while keeping a familiar but bounded tone.",
    }[event_stage]
    expectation_zh = {
        "recurrence": "承接同一事件线和前序处理策略，不要要求用户重讲背景。",
        "turning_point": "识别当前变化与前序状态的差异，重新校准建议。",
        "partial_resolution": "承接已处理部分，检查剩余缺口，不新增未给出的事实。",
        "reflection": "抽取可复用模式，同时保持熟悉但不越界的口吻。",
    }[event_stage]
    return {
        "stage_index": occurrence_index,
        "event_stage": event_stage,
        "source_stage_label": f"extended {event_stage}",
        "stage_goal": stage_goal,
        "stage_goal_zh": stage_goal_zh,
        "allowed_base_facts": base.get("allowed_base_facts", []),
        "allowed_base_facts_zh": base.get("allowed_base_facts_zh", []),
        "event_candidate_facts": base.get("event_candidate_facts", []),
        "persona_conditioned_facts": base.get("persona_conditioned_facts", []),
        "stage_delta_facts": [
            *base.get("stage_delta_facts", []),
            {
                "source_fields": ["extended_stage"],
                "text": f"Occurrence {occurrence_index} is an extended stage; it should continue the original {event_stage} stage facts and clarify that this is not a new event line.",
                "text_zh": f"第 {occurrence_index} 次出现是扩展阶段，应承接原始 {event_stage} 阶段事实，同时说明这不是新的事件线。",
            },
        ],
        "allowed_new_facts": base.get("allowed_new_facts", []),
        "allowed_new_facts_zh": base.get("allowed_new_facts_zh", []),
        "user_state_hint": base.get("user_state_hint"),
        "user_state_hint_zh": base.get("user_state_hint_zh"),
        "user_message_seed": user_message,
        "user_message_seed_zh": user_message_zh,
        "assistant_memory_expectation": expectation,
        "assistant_memory_expectation_zh": expectation_zh,
        "prohibited_facts": base.get("prohibited_facts", []),
        "prohibited_facts_zh": base.get("prohibited_facts_zh", []),
        "extended_stage_generated": True,
    }


def _stage_sequence(line: dict[str, Any]) -> list[dict[str, Any]]:
    stages = [item for item in line.get("stage_sequence", []) if isinstance(item, dict)]
    if not stages:
        raise ValueError(f"Event line {line.get('event_line_id')} has no stage_sequence.")
    return stages


def _line_title(line: dict[str, Any]) -> str:
    title = line.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("source") or title.get("zh") or line.get("event_category_id", ""))
    return str(title or line.get("event_category_id", ""))


def _line_title_zh(line: dict[str, Any]) -> str:
    title = line.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or line.get("event_category_id", ""))
    return str(title or line.get("event_category_id", ""))


def _daily_event_count_distribution_from_value(value: Any) -> dict[int, int] | None:
    if value in (None, "", {}):
        return None
    if not isinstance(value, dict):
        raise ValueError("daily_event_count_distribution must be an object.")
    result = {}
    for key, raw_count in value.items():
        result[int(key)] = int(raw_count)
    return result


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _summarize_timelines(timelines: list[dict[str, Any]]) -> dict[str, Any]:
    active_counts = [int(item.get("active_session_count", 0)) for item in timelines]
    active_day_counts = [int(item.get("active_day_count", 0)) for item in timelines]
    occurrence_counts = [int(item.get("event_occurrence_total", 0)) for item in timelines]
    parallel_day_counts = [int(item.get("parallel_event_day_count", 0)) for item in timelines]
    event_line_counts = [int(item.get("event_line_count", 0)) for item in timelines]
    domain_counts: Counter[str] = Counter()
    event_stage_counts: Counter[str] = Counter()
    daily_event_count_histogram: Counter[int] = Counter()
    calendar_event_counts: list[int] = []
    active_event_counts: list[int] = []
    max_events_on_single_day = 0
    for timeline in timelines:
        for day in timeline.get("days", []):
            if not isinstance(day, dict):
                continue
            occurrences = _day_event_occurrences(day) if day.get("active") else []
            occurrence_count = len(occurrences)
            calendar_event_counts.append(occurrence_count)
            daily_event_count_histogram[occurrence_count] += 1
            if occurrence_count > 0:
                active_event_counts.append(occurrence_count)
            if not day.get("active"):
                continue
            max_events_on_single_day = max(max_events_on_single_day, len(occurrences))
            for occurrence in occurrences:
                domain_counts[str(occurrence.get("event_domain"))] += 1
                event_stage_counts[str(occurrence.get("event_stage"))] += 1
    return {
        "persona_count": len(timelines),
        "event_line_count": sum(event_line_counts),
        "active_session_total": sum(active_counts),
        "active_sessions_per_persona_min": min(active_counts or [0]),
        "active_sessions_per_persona_max": max(active_counts or [0]),
        "active_day_total": sum(active_day_counts),
        "active_days_per_persona_min": min(active_day_counts or [0]),
        "active_days_per_persona_max": max(active_day_counts or [0]),
        "event_occurrence_total": sum(occurrence_counts),
        "event_occurrences_per_persona_min": min(occurrence_counts or [0]),
        "event_occurrences_per_persona_max": max(occurrence_counts or [0]),
        "parallel_event_day_total": sum(parallel_day_counts),
        "parallel_event_days_per_persona_min": min(parallel_day_counts or [0]),
        "parallel_event_days_per_persona_max": max(parallel_day_counts or [0]),
        "max_events_on_single_day": max_events_on_single_day,
        "daily_event_count_histogram": dict(sorted(daily_event_count_histogram.items())),
        "daily_event_count_median_calendar": _median(calendar_event_counts),
        "daily_event_count_median_active": _median(active_event_counts),
        "event_domain_counts": dict(sorted(domain_counts.items())),
        "event_stage_counts": dict(sorted(event_stage_counts.items())),
    }
