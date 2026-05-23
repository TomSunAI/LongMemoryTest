from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TIMELINE_DAYS = 30


@dataclass(frozen=True)
class GeneratorConfig:
    persona_path: Path
    life_domains_path: Path
    event_templates_path: Path
    timeline_days: int = DEFAULT_TIMELINE_DAYS
    seed: int = 42


class TimelineGenerationError(ValueError):
    """Raised when input configuration cannot produce a valid timeline."""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise TimelineGenerationError(f"Expected JSON object in {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def generate_timeline(config: GeneratorConfig) -> dict[str, Any]:
    rng = random.Random(config.seed)
    persona = load_json(config.persona_path)
    life_domains = load_json(config.life_domains_path)
    event_templates = load_json(config.event_templates_path)

    domains = _validate_domains(life_domains)
    templates = _validate_templates(event_templates)

    daily_events: dict[int, list[dict[str, Any]]] = {
        day: [] for day in range(1, config.timeline_days + 1)
    }
    event_counter = 1

    mainline_templates = _choose_mainline_templates(templates, rng)
    for template in mainline_templates:
        chain_events = _build_mainline_chain(
            template=template,
            timeline_days=config.timeline_days,
            rng=rng,
            start_event_number=event_counter,
        )
        event_counter += len(chain_events)
        for event in chain_events:
            daily_events[event["day"]].append(event)

    for day in range(1, config.timeline_days + 1):
        target_count = rng.randint(1, 3)
        while len(daily_events[day]) < target_count:
            domain = _weighted_domain(domains, rng)
            template = _sample_template_for_domain(templates, domain, rng)
            event = _build_single_event(
                template=template,
                event_number=event_counter,
                day=day,
                rng=rng,
            )
            event_counter += 1
            daily_events[day].append(event)

        if len(daily_events[day]) > 3:
            daily_events[day] = daily_events[day][:3]

    events = [
        event
        for day in range(1, config.timeline_days + 1)
        for event in sorted(daily_events[day], key=lambda item: item["event_id"])
    ]

    _renumber_events(events)

    return {
        "persona_id": persona.get("persona_id", "unknown"),
        "timeline_days": config.timeline_days,
        "seed": config.seed,
        "events": events,
    }


def _validate_domains(data: dict[str, Any]) -> list[dict[str, Any]]:
    domains = data.get("domains")
    if not isinstance(domains, list) or not domains:
        raise TimelineGenerationError("life_domains.json must contain a non-empty domains list")
    for domain in domains:
        if not isinstance(domain, dict) or not domain.get("domain"):
            raise TimelineGenerationError("Each domain must be an object with a domain field")
        if not isinstance(domain.get("weight"), int | float) or domain["weight"] <= 0:
            raise TimelineGenerationError(f"Domain {domain.get('domain')} must have weight > 0")
    return domains


def _validate_templates(data: dict[str, Any]) -> list[dict[str, Any]]:
    templates = data.get("templates")
    if not isinstance(templates, list) or not templates:
        raise TimelineGenerationError("event_templates.json must contain a non-empty templates list")

    required_fields = {
        "template_id",
        "domain",
        "title_template",
        "description_template",
        "default_emotional_intensity",
        "default_decision_impact",
        "default_time_sensitivity",
        "follow_up_needed",
        "should_be_remembered",
    }
    for template in templates:
        missing = sorted(required_fields - set(template))
        if missing:
            raise TimelineGenerationError(
                f"Template {template.get('template_id', '<unknown>')} missing fields: {missing}"
            )
    return templates


def _choose_mainline_templates(
    templates: list[dict[str, Any]], rng: random.Random
) -> list[dict[str, Any]]:
    candidates = [
        template
        for template in templates
        if template["follow_up_needed"] and template["should_be_remembered"]
    ]
    if len(candidates) < 2:
        raise TimelineGenerationError(
            "At least two templates must have follow_up_needed=true and should_be_remembered=true"
        )

    rng.shuffle(candidates)
    candidates.sort(
        key=lambda template: (
            template["default_emotional_intensity"],
            template["default_decision_impact"],
            template["default_time_sensitivity"],
        ),
        reverse=True,
    )

    selected: list[dict[str, Any]] = []
    selected_domains: set[str] = set()
    for template in candidates:
        if template["domain"] in selected_domains:
            continue
        selected.append(template)
        selected_domains.add(template["domain"])
        if len(selected) == 2:
            return selected

    return candidates[:2]


def _build_mainline_chain(
    template: dict[str, Any],
    timeline_days: int,
    rng: random.Random,
    start_event_number: int,
) -> list[dict[str, Any]]:
    first_day = rng.randint(1, max(1, timeline_days // 3))
    second_day = rng.randint(first_day + 3, max(first_day + 4, timeline_days * 2 // 3))
    third_day = rng.randint(second_day + 3, timeline_days)
    days = sorted({first_day, second_day, third_day})

    events: list[dict[str, Any]] = []
    root_event_id = _event_id(start_event_number)

    for index, day in enumerate(days):
        event_number = start_event_number + index
        if index == 0:
            status = "unresolved"
            related_event_id = None
            title_suffix = ""
            description_suffix = " This is the first point in a continuing event chain."
        elif index == len(days) - 1:
            status = rng.choice(["ongoing", "unresolved", "resolved"])
            related_event_id = root_event_id
            title_suffix = " - follow-up"
            description_suffix = " This follow-up captures how the issue has progressed after earlier discussion."
        else:
            status = "ongoing"
            related_event_id = root_event_id
            title_suffix = " - update"
            description_suffix = " This update keeps the same issue active across the simulated timeline."

        event = _build_single_event(
            template=template,
            event_number=event_number,
            day=day,
            rng=rng,
            status=status,
            related_event_id=related_event_id,
            title_suffix=title_suffix,
            description_suffix=description_suffix,
        )
        event["event_type"] = "mainline"
        events.append(event)

    return events


def _build_single_event(
    template: dict[str, Any],
    event_number: int,
    day: int,
    rng: random.Random,
    status: str | None = None,
    related_event_id: str | None = None,
    title_suffix: str = "",
    description_suffix: str = "",
) -> dict[str, Any]:
    event_type = "side" if template["should_be_remembered"] else "background"
    return {
        "event_id": _event_id(event_number),
        "day": day,
        "date": None,
        "domain": template["domain"],
        "event_type": event_type,
        "title": f"{template['title_template']}{title_suffix}",
        "participants": list(template.get("participants", ["user"])),
        "description": f"{template['description_template']}{description_suffix}",
        "emotional_intensity": _jitter_score(template["default_emotional_intensity"], rng),
        "decision_impact": _jitter_score(template["default_decision_impact"], rng),
        "time_sensitivity": _jitter_score(template["default_time_sensitivity"], rng),
        "status": status or _default_status(template, rng),
        "follow_up_needed": bool(template["follow_up_needed"]),
        "should_be_remembered": bool(template["should_be_remembered"]),
        "related_event_id": related_event_id,
        "source_template_id": template["template_id"],
    }


def _weighted_domain(domains: list[dict[str, Any]], rng: random.Random) -> str:
    total_weight = sum(domain["weight"] for domain in domains)
    threshold = rng.uniform(0, total_weight)
    running = 0.0
    for domain in domains:
        running += domain["weight"]
        if running >= threshold:
            return domain["domain"]
    return domains[-1]["domain"]


def _sample_template_for_domain(
    templates: list[dict[str, Any]], domain: str, rng: random.Random
) -> dict[str, Any]:
    candidates = [template for template in templates if template["domain"] == domain]
    if not candidates:
        candidates = templates
    return rng.choice(candidates)


def _jitter_score(value: int, rng: random.Random) -> int:
    return min(5, max(1, int(value) + rng.choice([-1, 0, 0, 1])))


def _default_status(template: dict[str, Any], rng: random.Random) -> str:
    if template["follow_up_needed"]:
        return rng.choice(["new", "ongoing", "unresolved"])
    return rng.choice(["new", "resolved"])


def _event_id(number: int) -> str:
    return f"E{number:03d}"


def _renumber_events(events: list[dict[str, Any]]) -> None:
    old_to_new: dict[str, str] = {}
    for index, event in enumerate(events, start=1):
        old_id = event["event_id"]
        new_id = _event_id(index)
        old_to_new[old_id] = new_id
        event["event_id"] = new_id

    for event in events:
        related_event_id = event.get("related_event_id")
        if related_event_id is not None:
            event["related_event_id"] = old_to_new[related_event_id]
