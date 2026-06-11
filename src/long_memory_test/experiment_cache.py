from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "data/config"
EXPERIMENT_ROOT = REPO_ROOT / "long_memory_experiment"
SCRIPT_DATA_DIR = EXPERIMENT_ROOT / "data/script"
MEMORY_CONDITIONS_DIR = EXPERIMENT_ROOT / "data/memory_conditions"
CACHE_DIR = EXPERIMENT_ROOT / "cache"
OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"

SCRIPT_TIMELINE_PATH = SCRIPT_DATA_DIR / "timeline.json"
DAILY_USER_MESSAGE_PATH = SCRIPT_DATA_DIR / "daily_user_message.json"
DAILY_SCENE_CARDS_PATH = SCRIPT_DATA_DIR / "daily_scene_cards.json"
BEI_ANNOTATIONS_PATH = SCRIPT_DATA_DIR / "bei_annotations.json"
PROBE_QUESTION_PLAN_PATH = SCRIPT_DATA_DIR / "probe_question_plan.json"
A_SCRIPT_PLAN_PATH = SCRIPT_DATA_DIR / "a_script_plan.json"
TAU_CONTRACT_PATH = SCRIPT_DATA_DIR / "tau_contract.json"
PERSONA_CONFIG_PATH = CONFIG_DIR / "persona.json"
USER_ACTOR_CONFIG_PATH = CONFIG_DIR / "user_actor.json"

CACHE_TIMELINE_EVENTS_PATH = CACHE_DIR / "timeline_events.json"
CACHE_MEMORY_CONDITIONS_PATH = CACHE_DIR / "memory_conditions_combined.json"
CACHE_MANIFEST_PATH = CACHE_DIR / "manifest.json"
EVENT_LINE_AUDIT_PATH = SCRIPT_DATA_DIR / "event_line_audit.json"
TAU_CONTRACT_SCHEMA_VERSION = "tau_construction_contract_v1"

M0_MEMORY_PATH = MEMORY_CONDITIONS_DIR / "m0_generic_agent_config.json"
M1_MEMORY_PATH = MEMORY_CONDITIONS_DIR / "m1_conclusion_memory.json"
M1_ALIAS_MEMORY_PATH = MEMORY_CONDITIONS_DIR / "mva_summary_memory.json"
M2_MEMORY_PATH = MEMORY_CONDITIONS_DIR / "m2_event_memory.json"
M3_MEMORY_PATH = MEMORY_CONDITIONS_DIR / "m3_relational_anchor_memory.json"


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


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def build_canonical_timeline(
    *,
    event_timeline: dict[str, Any],
    daily_messages: dict[str, Any],
    scene_cards: dict[str, Any] | None = None,
    probe_question_plan: dict[str, Any] | None = None,
    bei_annotations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the experiment-facing 30-day timeline schema.

    The old event-level timeline remains in cache for deterministic generators.
    The canonical script timeline is day-level and contains the fields used by
    the experimental design contract.
    """

    messages = daily_messages.get("messages", [])
    if not isinstance(messages, list) or not messages:
        raise ValueError("daily_user_message.json must contain messages")

    events_by_id = {
        str(event.get("event_id")): event
        for event in event_timeline.get("events", [])
        if isinstance(event, dict) and event.get("event_id")
    }
    scene_cards_by_message = {
        str(card.get("opening_message_id")): card
        for card in (scene_cards or {}).get("scene_cards", [])
        if isinstance(card, dict) and card.get("opening_message_id")
    }
    probes_by_opening: dict[str, list[dict[str, Any]]] = {}
    for probe in (probe_question_plan or {}).get("probe_questions", []):
        if not isinstance(probe, dict):
            continue
        opening_id = str(probe.get("insert_after_message_id") or "")
        probes_by_opening.setdefault(opening_id, []).append(probe)

    annotations_by_probe_id = {
        str(item.get("probe_id")): item
        for item in (bei_annotations or {}).get("annotations", [])
        if isinstance(item, dict) and item.get("probe_id")
    }

    previous_days_by_topic: dict[str, list[int]] = {}
    days = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        day = int(message.get("day", 0) or 0)
        if day <= 0:
            continue
        topic = str(message.get("topic", ""))
        event_refs = [str(item) for item in message.get("event_refs", [])]
        primary_event_id = str(message.get("primary_event_id") or event_refs[0])
        primary_event = events_by_id.get(primary_event_id, {})
        card = scene_cards_by_message.get(str(message.get("message_id")))
        probes = probes_by_opening.get(str(message.get("message_id")), [])
        related_previous_days = list(previous_days_by_topic.get(topic, []))
        day_probe_annotations = [
            annotations_by_probe_id[str(probe.get("probe_id"))]
            for probe in probes
            if str(probe.get("probe_id")) in annotations_by_probe_id
        ]

        probes_exist = bool(probes)
        days.append(
            {
                "day": day,
                "main_topic": topic,
                "event_stage": _event_stage(
                    message=message,
                    primary_event=primary_event,
                    related_previous_days=related_previous_days,
                ),
                "related_previous_days": related_previous_days,
                "surface_event": _surface_event(message=message, primary_event=primary_event),
                "latent_continuity": _latent_continuity(
                    topic=topic,
                    related_previous_days=related_previous_days,
                    card=card,
                    annotations=day_probe_annotations,
                ),
                "probe_candidate": probes_exist,
                "reason_for_probe": _reason_for_probe(
                    message=message,
                    probes=probes,
                    annotations=day_probe_annotations,
                    card=card,
                ),
                "opening_message_id": message.get("message_id"),
                "scene_id": card.get("scene_id") if card else None,
                "primary_event_id": primary_event_id,
                "event_refs": event_refs,
                "script_stage": message.get("script_stage"),
                "intent": message.get("intent"),
                "memory_relevance": message.get("memory_relevance"),
                "probe_ids": [probe.get("probe_id") for probe in probes],
            }
        )
        previous_days_by_topic.setdefault(topic, []).append(day)

    return {
        "schema_version": "timeline_v1_event_first_daily",
        "generation_mode": "event_first_bei_calibrated_daily_timeline",
        "construction_contract": {
            "notation": "tau=(z,T,L,I,P)",
            "source": display_path(TAU_CONTRACT_PATH),
        },
        "timeline_days": int(event_timeline.get("timeline_days") or len(days)),
        "source_cache": {
            "event_timeline": display_path(CACHE_TIMELINE_EVENTS_PATH),
        },
        "days": days,
        "summary": {
            "day_count": len(days),
            "probe_candidate_count": sum(1 for item in days if item["probe_candidate"]),
            "topics": sorted({str(item["main_topic"]) for item in days}),
        },
    }


def build_tau_contract(
    *,
    event_timeline: dict[str, Any],
    daily_messages: dict[str, Any],
    canonical_timeline: dict[str, Any],
    scene_cards: dict[str, Any] | None = None,
    probe_question_plan: dict[str, Any] | None = None,
    persona_config: dict[str, Any] | None = None,
    user_actor_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the single script-construction contract τ=(z,T,L,I,P).

    The contract is the only script-level source of truth. Downstream memory
    conditions and runtimes may reference these bindings, but must not redefine
    personas, event lines, interaction units, or probes.
    """

    events_by_id = {
        str(event.get("event_id")): event
        for event in event_timeline.get("events", [])
        if isinstance(event, dict) and event.get("event_id")
    }
    messages_by_id = {
        str(message.get("message_id")): message
        for message in daily_messages.get("messages", [])
        if isinstance(message, dict) and message.get("message_id")
    }
    probes = [
        probe
        for probe in (probe_question_plan or {}).get("probe_questions", [])
        if isinstance(probe, dict) and probe.get("message_id")
    ]
    probes_by_opening: dict[str, list[dict[str, Any]]] = {}
    for probe in probes:
        opening_id = str(probe.get("insert_after_message_id") or "")
        probes_by_opening.setdefault(opening_id, []).append(probe)
    scene_cards_by_message = {
        str(card.get("opening_message_id")): card
        for card in (scene_cards or {}).get("scene_cards", [])
        if isinstance(card, dict) and card.get("opening_message_id")
    }

    persona_id = str(
        event_timeline.get("persona_id")
        or daily_messages.get("persona_id")
        or "unknown_persona"
    )
    persona_contract = _build_persona_contract(
        persona_id=persona_id,
        persona_config=persona_config
        if persona_config is not None
        else _load_optional_json(PERSONA_CONFIG_PATH),
        user_actor_config=user_actor_config
        if user_actor_config is not None
        else _load_optional_json(USER_ACTOR_CONFIG_PATH),
    )
    themes: dict[str, dict[str, Any]] = {}
    event_lines: dict[str, dict[str, Any]] = {}
    interaction_units: dict[str, dict[str, Any]] = {}
    targeted_probes: dict[str, dict[str, Any]] = {}
    message_bindings: dict[str, dict[str, Any]] = {}

    for day_node in canonical_timeline.get("days", []):
        if not isinstance(day_node, dict):
            continue
        opening_id = str(day_node.get("opening_message_id") or "")
        if not opening_id:
            continue
        message = messages_by_id.get(opening_id, {})
        primary_event_id = str(day_node.get("primary_event_id") or "")
        root_event_id = _root_event_id(primary_event_id, events_by_id)
        event_refs = [str(item) for item in day_node.get("event_refs", []) if item]
        root_event = events_by_id.get(root_event_id, {})
        theme_label = str(day_node.get("main_topic") or message.get("topic") or "")
        domain = str(root_event.get("domain") or _first_string(message.get("domains", [])))
        theme_id = _tau_id("T", "_".join(item for item in [domain, theme_label] if item) or primary_event_id)
        event_line_id = _tau_id("L", root_event_id or theme_label or primary_event_id)
        probe_ids = [str(item) for item in day_node.get("probe_ids", []) if item]
        scene_card = scene_cards_by_message.get(opening_id, {})
        related_event_ids = _unique_strings(
            [
                root_event_id,
                str(day_node.get("related_event_id") or ""),
                *event_refs,
            ]
        )
        related_event_ids = [item for item in related_event_ids if item and item != primary_event_id]
        tau_binding = {
            "schema_version": "tau_binding_v1",
            "persona_id": persona_id,
            "theme_id": theme_id,
            "event_line_id": event_line_id,
            "event_stage": day_node.get("event_stage"),
            "interaction_unit_id": opening_id,
            "probe_ids": probe_ids,
            "primary_event_id": primary_event_id,
            "root_event_id": root_event_id,
            "related_event_ids": related_event_ids,
            "event_refs": event_refs,
        }
        message_bindings[opening_id] = dict(tau_binding)

        themes.setdefault(
            theme_id,
            {
                "theme_id": theme_id,
                "label": theme_label,
                "domains": [],
                "event_line_ids": [],
                "source_event_ids": [],
            },
        )
        themes[theme_id]["domains"] = _unique_strings([*themes[theme_id]["domains"], domain])
        themes[theme_id]["event_line_ids"] = _unique_strings(
            [*themes[theme_id]["event_line_ids"], event_line_id]
        )
        themes[theme_id]["source_event_ids"] = _unique_strings(
            [*themes[theme_id]["source_event_ids"], *event_refs]
        )

        event_lines.setdefault(
            event_line_id,
            {
                "event_line_id": event_line_id,
                "theme_id": theme_id,
                "root_event_id": root_event_id,
                "label": theme_label,
                "source_event_ids": [],
                "interaction_unit_ids": [],
                "probe_ids": [],
                "stage_sequence": [],
            },
        )
        event_line = event_lines[event_line_id]
        event_line["source_event_ids"] = _unique_strings(
            [*event_line["source_event_ids"], *event_refs]
        )
        event_line["interaction_unit_ids"] = _unique_strings(
            [*event_line["interaction_unit_ids"], opening_id]
        )
        event_line["probe_ids"] = _unique_strings([*event_line["probe_ids"], *probe_ids])
        event_line["stage_sequence"].append(
            {
                "day": day_node.get("day"),
                "message_id": opening_id,
                "stage": day_node.get("event_stage"),
                "surface_event": day_node.get("surface_event"),
                "latent_continuity": day_node.get("latent_continuity"),
            }
        )

        interaction_units[opening_id] = {
            "interaction_unit_id": opening_id,
            "day": day_node.get("day"),
            "theme_id": theme_id,
            "event_line_id": event_line_id,
            "event_stage": day_node.get("event_stage"),
            "message_id": opening_id,
            "scene_id": day_node.get("scene_id"),
            "primary_event_id": primary_event_id,
            "event_refs": event_refs,
            "probe_ids": probe_ids,
            "intent": day_node.get("intent"),
            "memory_relevance": day_node.get("memory_relevance"),
            "script_stage": day_node.get("script_stage"),
            "surface_event": day_node.get("surface_event"),
            "latent_continuity": day_node.get("latent_continuity"),
            "scene_card_id": scene_card.get("scene_id"),
            "scripted_opening": _scripted_opening_contract(
                day_node=day_node,
                message=message,
                scene_card=scene_card,
            ),
            "constrained_followup": _constrained_followup_contract(scene_card),
            "scene_boundary": _scene_boundary_contract(scene_card),
        }

        for probe in probes_by_opening.get(opening_id, []):
            probe_id = str(probe.get("probe_id") or probe.get("message_id"))
            probe_message_id = str(probe.get("message_id") or probe_id)
            probe_binding = {
                **tau_binding,
                "interaction_unit_id": opening_id,
                "probe_id": probe_id,
                "probe_type": probe.get("probe_type"),
            }
            message_bindings[probe_message_id] = probe_binding
            targeted_probes[probe_id] = {
                "probe_id": probe_id,
                "message_id": probe_message_id,
                "interaction_unit_id": opening_id,
                "theme_id": theme_id,
                "event_line_id": event_line_id,
                "event_stage": day_node.get("event_stage"),
                "probe_type": probe.get("probe_type"),
                "target_detail_ids": [
                    str(item) for item in probe.get("target_detail_ids", []) if item
                ],
                "tom_dimensions": [
                    str(item) for item in probe.get("tom_dimensions", []) if item
                ],
                "required_memory_type": [
                    str(item) for item in probe.get("required_memory_type", []) if item
                ],
            }

    contract = {
        "schema_version": TAU_CONTRACT_SCHEMA_VERSION,
        "notation": "tau=(z,T,L,I,P)",
        "definition": {
            "z": "sampled user persona",
            "T": "sampled long-term event themes",
            "L": "recurring event lines",
            "I": "daily interaction units",
            "P": "inserted targeted relational probes",
        },
        "source_paths": {
            "event_timeline": display_path(CACHE_TIMELINE_EVENTS_PATH),
            "daily_messages": display_path(DAILY_USER_MESSAGE_PATH),
            "daily_scene_cards": display_path(DAILY_SCENE_CARDS_PATH),
            "probe_questions": display_path(PROBE_QUESTION_PLAN_PATH),
            "canonical_timeline": display_path(SCRIPT_TIMELINE_PATH),
        },
        "z": persona_contract,
        "T": list(themes.values()),
        "L": list(event_lines.values()),
        "I": list(interaction_units.values()),
        "P": list(targeted_probes.values()),
        "message_bindings": message_bindings,
        "summary": {
            "theme_count": len(themes),
            "event_line_count": len(event_lines),
            "interaction_unit_count": len(interaction_units),
            "targeted_probe_count": len(targeted_probes),
            "bound_message_count": len(message_bindings),
        },
    }
    issues = validate_tau_contract(contract)
    contract["validation"] = {
        "status": "pass" if not issues else "fail",
        "issues": issues,
    }
    return contract


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def _build_persona_contract(
    *,
    persona_id: str,
    persona_config: dict[str, Any] | None,
    user_actor_config: dict[str, Any] | None,
) -> dict[str, Any]:
    persona = persona_config or {}
    actor = user_actor_config or {}
    stable_profile = actor.get("stable_profile", {})
    if not isinstance(stable_profile, dict):
        stable_profile = {}
    speech_profile = actor.get("speech_profile", {})
    if not isinstance(speech_profile, dict):
        speech_profile = {}
    emotional_model = actor.get("emotional_model", {})
    if not isinstance(emotional_model, dict):
        emotional_model = {}
    memory_detail_contract = actor.get("memory_detail_contract", {})
    if not isinstance(memory_detail_contract, dict):
        memory_detail_contract = {}
    guardrails = actor.get("guardrails", {})
    if not isinstance(guardrails, dict):
        guardrails = {}

    stable_attributes = _drop_empty_values(
        {
            "age": stable_profile.get("age", persona.get("age")),
            "occupation": stable_profile.get("occupation", persona.get("occupation")),
            "family_status": stable_profile.get("family_status", persona.get("family_status")),
            "child_age": stable_profile.get("child_age", persona.get("child_age")),
            "life_situation": persona.get("family_status") or stable_profile.get("family_status"),
            "interaction_style": persona.get("social_style") or speech_profile.get("register"),
        }
    )
    pressure_sources = _unique_strings(
        [
            *_as_list(stable_profile.get("stable_pressure_sources")),
            *_as_list(persona.get("pressure_sources")),
        ]
    )
    personality_traits = _unique_strings(
        [
            *_as_list(stable_profile.get("core_traits")),
            *_as_list(persona.get("personality_traits")),
        ]
    )
    stable_memory_details = [
        dict(item)
        for item in memory_detail_contract.get("stable_details_for_m1", [])
        if isinstance(item, dict)
    ]

    return {
        "schema_version": "tau_persona_v1",
        "persona_id": persona_id,
        "source": {
            "persona_id": "event_timeline.persona_id_or_daily_messages.persona_id",
            "persona_config": display_path(PERSONA_CONFIG_PATH)
            if persona_config
            else None,
            "user_actor_config": display_path(USER_ACTOR_CONFIG_PATH)
            if user_actor_config
            else None,
        },
        "name": persona.get("name"),
        "actor_id": actor.get("actor_id"),
        "stable_attributes": stable_attributes,
        "personality_traits": personality_traits,
        "pressure_sources": pressure_sources,
        "long_term_goals": _unique_strings(_as_list(persona.get("long_term_goals"))),
        "speech_profile": _drop_empty_values(
            {
                "language": speech_profile.get("language"),
                "register": speech_profile.get("register"),
                "typical_shape": _as_list(speech_profile.get("typical_shape")),
                "sentence_tendencies": _as_list(speech_profile.get("sentence_tendencies")),
                "avoid": _as_list(speech_profile.get("avoid")),
            }
        ),
        "emotional_model": _drop_empty_values(
            {
                "baseline": emotional_model.get("baseline"),
                "under_stress": _as_list(emotional_model.get("under_stress")),
                "disclosure_style": emotional_model.get("disclosure_style", {}),
            }
        ),
        "stable_memory_details": stable_memory_details,
        "guardrails": guardrails,
        "pdf_alignment": {
            "meaning": "z is the sampled stable user persona used to construct every long-term trajectory.",
            "covered_stable_attributes": sorted(stable_attributes.keys()),
            "unprovided_pdf_examples": [
                item
                for item in ["gender"]
                if item not in stable_attributes
            ],
        },
    }


def _scripted_opening_contract(
    *,
    day_node: dict[str, Any],
    message: dict[str, Any],
    scene_card: dict[str, Any],
) -> dict[str, Any]:
    return _drop_empty_values(
        {
            "message_id": day_node.get("opening_message_id") or message.get("message_id"),
            "user_message": (
                scene_card.get("opening_user_message")
                or message.get("user_message")
                or day_node.get("surface_event")
            ),
            "intent": day_node.get("intent") or message.get("intent"),
            "tone": scene_card.get("tone") or message.get("tone"),
            "conversation_goal": scene_card.get("conversation_goal")
            or message.get("conversation_goal"),
            "script_stage": day_node.get("script_stage"),
            "memory_relevance": day_node.get("memory_relevance"),
            "introduces_current_event_state": True,
        }
    )


def _constrained_followup_contract(scene_card: dict[str, Any]) -> dict[str, Any]:
    controls = scene_card.get("expansion_controls", {})
    if not isinstance(controls, dict):
        controls = {}
    return _drop_empty_values(
        {
            "source": "daily_scene_card.expansion_controls",
            "mode": controls.get("mode"),
            "variant_mode": controls.get("variant_mode"),
            "followup_budget": controls.get("followup_budget"),
            "permitted_conversational_moves": [
                dict(item)
                for item in _as_list(controls.get("allowed_followup_moves"))
                if isinstance(item, dict)
            ],
            "reveal_steps": [
                dict(item)
                for item in _as_list(controls.get("reveal_schedule"))
                if isinstance(item, dict)
            ],
            "stop_conditions": [
                str(item) for item in _as_list(controls.get("stop_conditions")) if item
            ],
            "must_not_introduce": [
                str(item) for item in _as_list(controls.get("must_not_invent")) if item
            ],
            "strict_scene_boundary": True,
        }
    )


def _scene_boundary_contract(scene_card: dict[str, Any]) -> dict[str, Any]:
    memory_detail_expectations = scene_card.get("memory_detail_expectations", {})
    if not isinstance(memory_detail_expectations, dict):
        memory_detail_expectations = {}
    allowed_facts = [
        dict(item)
        for item in _as_list(scene_card.get("allowed_facts"))
        if isinstance(item, dict)
    ]
    latent_concerns = [
        dict(item)
        for item in _as_list(scene_card.get("latent_concerns"))
        if isinstance(item, dict)
    ]
    active_events = [
        item
        for item in _as_list(scene_card.get("active_events"))
        if isinstance(item, dict)
    ]
    return _drop_empty_values(
        {
            "source": "daily_scene_card",
            "allowed_facts": allowed_facts,
            "allowed_fact_ids": [
                str(item.get("fact_id"))
                for item in allowed_facts
                if item.get("fact_id")
            ],
            "latent_concerns": latent_concerns,
            "latent_concern_ids": [
                str(item.get("concern_id"))
                for item in latent_concerns
                if item.get("concern_id")
            ],
            "active_event_ids": [
                str(item.get("event_id"))
                for item in active_events
                if item.get("event_id")
            ],
            "memory_level_rules": memory_detail_expectations.get("level_rules", {}),
            "audit_dimensions": memory_detail_expectations.get("audit_dimensions", []),
            "stable_detail_ids": [
                str(item.get("detail_id"))
                for item in _as_list(memory_detail_expectations.get("stable_details"))
                if isinstance(item, dict) and item.get("detail_id")
            ],
            "event_detail_ids": [
                str(item.get("detail_id"))
                for item in _as_list(memory_detail_expectations.get("event_details"))
                if isinstance(item, dict) and item.get("detail_id")
            ],
            "latent_concern_detail_ids": [
                str(item.get("detail_id"))
                for item in _as_list(memory_detail_expectations.get("latent_concern_details"))
                if isinstance(item, dict) and item.get("detail_id")
            ],
            "strict_scene_boundary": True,
        }
    )


def _drop_empty_values(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in data.items()
        if value is not None and value != [] and value != {}
    }


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_tau_contract(contract: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if contract.get("schema_version") != TAU_CONTRACT_SCHEMA_VERSION:
        issues.append("Unsupported tau contract schema_version.")
    if not contract.get("z", {}).get("persona_id"):
        issues.append("Missing z.persona_id.")
    z = contract.get("z", {})
    stable_attributes = z.get("stable_attributes", {}) if isinstance(z, dict) else {}
    if not isinstance(stable_attributes, dict) or not stable_attributes:
        issues.append("Missing z.stable_attributes for sampled persona.")
    else:
        for required_key in ["age", "occupation", "life_situation", "interaction_style"]:
            if required_key not in stable_attributes:
                issues.append(f"Missing z.stable_attributes.{required_key}.")
    if isinstance(z, dict) and not z.get("speech_profile"):
        issues.append("Missing z.speech_profile for interaction style.")
    theme_ids = {str(item.get("theme_id")) for item in contract.get("T", [])}
    event_line_ids = {str(item.get("event_line_id")) for item in contract.get("L", [])}
    unit_ids = {str(item.get("interaction_unit_id")) for item in contract.get("I", [])}
    if not theme_ids:
        issues.append("T must contain at least one event theme.")
    if not event_line_ids:
        issues.append("L must contain at least one recurring event line.")
    if not unit_ids:
        issues.append("I must contain at least one daily interaction unit.")
    for line in contract.get("L", []):
        if str(line.get("theme_id")) not in theme_ids:
            issues.append(f"Event line {line.get('event_line_id')} references missing theme.")
    for unit in contract.get("I", []):
        if str(unit.get("event_line_id")) not in event_line_ids:
            issues.append(f"Interaction unit {unit.get('interaction_unit_id')} references missing event line.")
        scripted_opening = unit.get("scripted_opening", {})
        constrained_followup = unit.get("constrained_followup", {})
        scene_boundary = unit.get("scene_boundary", {})
        if not isinstance(scripted_opening, dict) or not scripted_opening.get("user_message"):
            issues.append(
                f"Interaction unit {unit.get('interaction_unit_id')} is missing scripted opening."
            )
        if not isinstance(constrained_followup, dict):
            issues.append(
                f"Interaction unit {unit.get('interaction_unit_id')} is missing constrained follow-up."
            )
        else:
            if "followup_budget" not in constrained_followup:
                issues.append(
                    f"Interaction unit {unit.get('interaction_unit_id')} is missing follow-up budget."
                )
            if not constrained_followup.get("permitted_conversational_moves"):
                issues.append(
                    f"Interaction unit {unit.get('interaction_unit_id')} is missing permitted moves."
                )
            if not constrained_followup.get("reveal_steps"):
                issues.append(
                    f"Interaction unit {unit.get('interaction_unit_id')} is missing reveal steps."
                )
            if not constrained_followup.get("must_not_introduce"):
                issues.append(
                    f"Interaction unit {unit.get('interaction_unit_id')} is missing must-not-introduce boundary."
                )
        if not isinstance(scene_boundary, dict) or not scene_boundary.get("allowed_facts"):
            issues.append(
                f"Interaction unit {unit.get('interaction_unit_id')} is missing scene allowed facts."
            )
    for probe in contract.get("P", []):
        if str(probe.get("interaction_unit_id")) not in unit_ids:
            issues.append(f"Probe {probe.get('probe_id')} references missing interaction unit.")
    for message_id, binding in contract.get("message_bindings", {}).items():
        if str(binding.get("event_line_id")) not in event_line_ids:
            issues.append(f"Message {message_id} references missing event line.")
        if str(binding.get("theme_id")) not in theme_ids:
            issues.append(f"Message {message_id} references missing theme.")
    return issues


def attach_tau_metadata_to_script_docs(
    *,
    canonical_timeline: dict[str, Any],
    daily_messages: dict[str, Any],
    scene_cards: dict[str, Any] | None,
    probe_question_plan: dict[str, Any] | None,
    tau_contract: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    bindings = tau_contract.get("message_bindings", {})
    canonical = dict(canonical_timeline)
    canonical_days = []
    for day in canonical.get("days", []):
        if not isinstance(day, dict):
            canonical_days.append(day)
            continue
        item = dict(day)
        binding = bindings.get(str(item.get("opening_message_id")))
        if binding:
            item["tau"] = binding
        canonical_days.append(item)
    canonical["days"] = canonical_days
    canonical["tau_contract"] = {
        "schema_version": tau_contract.get("schema_version"),
        "path": display_path(TAU_CONTRACT_PATH),
        "notation": tau_contract.get("notation"),
        "summary": tau_contract.get("summary", {}),
    }

    daily = dict(daily_messages)
    daily["tau_contract"] = canonical["tau_contract"]
    daily["messages"] = [
        _with_tau_binding(message, bindings)
        for message in daily_messages.get("messages", [])
    ]

    scenes = None
    if scene_cards is not None:
        scenes = dict(scene_cards)
        scenes["tau_contract"] = canonical["tau_contract"]
        scenes["scene_cards"] = [
            _with_tau_binding(card, bindings, message_key="opening_message_id")
            for card in scene_cards.get("scene_cards", [])
        ]

    probes = None
    if probe_question_plan is not None:
        probes = dict(probe_question_plan)
        probes["tau_contract"] = canonical["tau_contract"]
        probes["probe_questions"] = [
            _with_tau_binding(probe, bindings)
            for probe in probe_question_plan.get("probe_questions", [])
        ]
    return canonical, daily, scenes, probes


def _with_tau_binding(
    item: Any,
    bindings: dict[str, dict[str, Any]],
    *,
    message_key: str = "message_id",
) -> Any:
    if not isinstance(item, dict):
        return item
    result = dict(item)
    binding = bindings.get(str(result.get(message_key) or ""))
    if binding:
        result["tau"] = binding
    return result


def split_memory_conditions(combined: dict[str, Any]) -> dict[str, dict[str, Any]]:
    condition_specs = {
        str(item.get("condition_id")): item
        for item in combined.get("condition_specs", [])
        if isinstance(item, dict) and item.get("condition_id")
    }
    defaults = combined.get("default_payloads", {})
    payloads_by_message = combined.get("memory_payloads_by_message_id", {})
    result = {}
    for condition_id in ["M0", "M1", "M2", "M3"]:
        result[condition_id] = {
            "schema_version": "memory_condition_v1",
            "condition_id": condition_id,
            "tau_contract": combined.get("tau_contract", {}),
            "condition_spec": condition_specs.get(condition_id, {}),
            "default_payload": defaults.get(condition_id, {}),
            "payloads_by_message_id": {
                message_id: payloads[condition_id]
                for message_id, payloads in payloads_by_message.items()
                if isinstance(payloads, dict) and condition_id in payloads
            },
            "source_cache": display_path(CACHE_MEMORY_CONDITIONS_PATH),
        }
    return result


def write_memory_condition_files(combined: dict[str, Any]) -> None:
    split = split_memory_conditions(combined)
    write_json(M0_MEMORY_PATH, split["M0"])
    write_json(M1_MEMORY_PATH, split["M1"])
    write_json(M1_ALIAS_MEMORY_PATH, split["M1"])
    write_json(M2_MEMORY_PATH, split["M2"])
    write_json(M3_MEMORY_PATH, split["M3"])


def refresh_canonical_timeline_from_files() -> dict[str, Any]:
    event_timeline = load_json(CACHE_TIMELINE_EVENTS_PATH)
    daily_messages = load_json(DAILY_USER_MESSAGE_PATH)
    scene_cards = load_json(DAILY_SCENE_CARDS_PATH) if DAILY_SCENE_CARDS_PATH.exists() else None
    probe_plan = load_json(PROBE_QUESTION_PLAN_PATH) if PROBE_QUESTION_PLAN_PATH.exists() else None
    bei = load_json(BEI_ANNOTATIONS_PATH) if BEI_ANNOTATIONS_PATH.exists() else None
    canonical = build_canonical_timeline(
        event_timeline=event_timeline,
        daily_messages=daily_messages,
        scene_cards=scene_cards,
        probe_question_plan=probe_plan,
        bei_annotations=bei,
    )
    tau_contract = build_tau_contract(
        event_timeline=event_timeline,
        daily_messages=daily_messages,
        scene_cards=scene_cards,
        probe_question_plan=probe_plan,
        canonical_timeline=canonical,
    )
    if tau_contract.get("validation", {}).get("status") != "pass":
        raise ValueError(
            "Invalid tau construction contract: "
            + "; ".join(tau_contract.get("validation", {}).get("issues", []))
        )
    canonical, daily_messages, scene_cards, probe_plan = attach_tau_metadata_to_script_docs(
        canonical_timeline=canonical,
        daily_messages=daily_messages,
        scene_cards=scene_cards,
        probe_question_plan=probe_plan,
        tau_contract=tau_contract,
    )
    write_json(TAU_CONTRACT_PATH, tau_contract)
    write_json(DAILY_USER_MESSAGE_PATH, daily_messages)
    if scene_cards is not None:
        write_json(DAILY_SCENE_CARDS_PATH, scene_cards)
    if probe_plan is not None:
        write_json(PROBE_QUESTION_PLAN_PATH, probe_plan)
    write_json(SCRIPT_TIMELINE_PATH, canonical)
    write_json(
        EVENT_LINE_AUDIT_PATH,
        build_event_line_audit(
            canonical_timeline=canonical,
            probe_question_plan=probe_plan,
            bei_annotations=bei,
        ),
    )
    return canonical


def build_event_line_audit(
    *,
    canonical_timeline: dict[str, Any],
    probe_question_plan: dict[str, Any] | None = None,
    bei_annotations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    days = [
        day
        for day in canonical_timeline.get("days", [])
        if isinstance(day, dict)
    ]
    probes = [
        probe
        for probe in (probe_question_plan or {}).get("probe_questions", [])
        if isinstance(probe, dict)
    ]
    annotations_by_probe_id = {
        str(item.get("probe_id")): item
        for item in (bei_annotations or {}).get("annotations", [])
        if isinstance(item, dict) and item.get("probe_id")
    }
    probes_by_day: dict[int, list[dict[str, Any]]] = {}
    for probe in probes:
        probes_by_day.setdefault(int(probe.get("day", 0) or 0), []).append(probe)

    topic_lines = []
    for topic in sorted({str(day.get("main_topic", "")) for day in days}):
        topic_days = [day for day in days if day.get("main_topic") == topic]
        topic_probes = [
            probe
            for day in topic_days
            for probe in probes_by_day.get(int(day.get("day", 0) or 0), [])
        ]
        stages = [str(day.get("event_stage", "")) for day in topic_days]
        required_memory_types = sorted(
            {
                memory_type
                for probe in topic_probes
                for memory_type in _probe_required_memory_types(
                    probe=probe,
                    annotations_by_probe_id=annotations_by_probe_id,
                )
            }
        )
        topic_lines.append(
            {
                "topic": topic,
                "theme_id": next(
                    (
                        str(day.get("tau", {}).get("theme_id"))
                        for day in topic_days
                        if isinstance(day.get("tau"), dict)
                        and day.get("tau", {}).get("theme_id")
                    ),
                    None,
                ),
                "event_line_ids": sorted(
                    {
                        str(day.get("tau", {}).get("event_line_id", ""))
                        for day in topic_days
                        if isinstance(day.get("tau"), dict)
                        and day.get("tau", {}).get("event_line_id")
                    }
                ),
                "days": [day.get("day") for day in topic_days],
                "stage_by_day": {
                    f"D{int(day.get('day', 0)):02d}": day.get("event_stage")
                    for day in topic_days
                },
                "coverage": {
                    "has_initial": "initial" in stages,
                    "has_recurrence": "recurrence" in stages or len(topic_days) > 1,
                    "has_escalation_or_turning_point": any(
                        stage in {"escalation", "turning_point"}
                        for stage in stages
                    ),
                    "has_resolution": "resolution" in stages,
                    "has_reflection": "reflection" in stages,
                    "probe_count": len(topic_probes),
                    "probe_types": sorted({str(probe.get("probe_type")) for probe in topic_probes}),
                    "required_memory_types": required_memory_types,
                },
                "suggested_fix": _topic_line_fix(
                    topic=topic,
                    stages=stages,
                    topic_day_count=len(topic_days),
                    topic_probes=topic_probes,
                ),
            }
        )

    candidate_nodes = [day for day in days if day.get("probe_candidate")]
    dimension_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for probe in probes:
        type_name = str(probe.get("probe_type", "unknown"))
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
        for dimension in probe.get("tom_dimensions", []):
            dimension_name = str(dimension)
            dimension_counts[dimension_name] = dimension_counts.get(dimension_name, 0) + 1

    return {
        "schema_version": "event_line_audit_v1",
        "candidate_selection_contract": {
            "recommended_candidate_node_count": "15-20",
            "actual_candidate_node_count": len(candidate_nodes),
            "candidate_definition": (
                "A day-level node selected for formal probes because it involves repeated "
                "themes, state changes, shared context invocation, or memory misuse risk."
            ),
        },
        "probe_set_contract": {
            "recommended_probe_count": "24-36",
            "actual_probe_count": len(probes),
            "probe_type_counts": dict(sorted(type_counts.items())),
            "tom_dimension_counts": dict(sorted(dimension_counts.items())),
        },
        "candidate_nodes": [
            {
                "day": day.get("day"),
                "main_topic": day.get("main_topic"),
                "event_line_id": (
                    day.get("tau", {}).get("event_line_id")
                    if isinstance(day.get("tau"), dict)
                    else None
                ),
                "event_stage": day.get("event_stage"),
                "related_previous_days": day.get("related_previous_days", []),
                "probe_ids": day.get("probe_ids", []),
                "reason_for_probe": day.get("reason_for_probe", ""),
            }
            for day in candidate_nodes
        ],
        "topic_lines": topic_lines,
    }


def update_cache_manifest(paths: dict[str, Path], *, note: str | None = None) -> None:
    manifest = {
        "schema_version": "experiment_cache_manifest_v1",
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "note": note or "experiment cache refreshed",
        "files": {
            name: {
                "path": display_path(path),
                "sha256": _sha256_file(path) if path.exists() else None,
                "exists": path.exists(),
            }
            for name, path in sorted(paths.items())
        },
    }
    write_json(CACHE_MANIFEST_PATH, manifest)


def latest_run_dir() -> Path:
    if not OUTPUTS_DIR.exists():
        raise FileNotFoundError(f"No outputs directory exists at {OUTPUTS_DIR}")
    runs = sorted(
        path
        for path in OUTPUTS_DIR.iterdir()
        if path.is_dir() and path.name.startswith("run_")
    )
    if not runs:
        raise FileNotFoundError(f"No run_* directories found in {OUTPUTS_DIR}")
    return runs[-1]


def _event_stage(
    *,
    message: dict[str, Any],
    primary_event: dict[str, Any],
    related_previous_days: list[int],
) -> str:
    planned_stage = str(primary_event.get("planned_event_stage", ""))
    if planned_stage in {
        "initial",
        "recurrence",
        "escalation",
        "turning_point",
        "resolution",
        "reflection",
    }:
        return planned_stage

    intent = str(message.get("intent", ""))
    status = str(primary_event.get("status", ""))
    user_message = str(message.get("user_message", ""))
    script_stage = int(message.get("script_stage", 0) or 0)
    if status == "resolved":
        return "resolution"
    if any(
        keyword in user_message
        for keyword in ["放一放", "降级", "不再硬扛", "先恢复", "轻一点处理", "别让它继续消耗"]
    ):
        return "resolution"
    if related_previous_days and any(
        keyword in user_message
        for keyword in ["承认现实", "不可能每一段", "可以先放过", "底下其实", "支持感的问题"]
    ):
        return "turning_point"
    if any(keyword in user_message for keyword in ["紧一下", "抗拒", "成本", "影响推进"]):
        return "escalation"
    if intent in {"decision_support", "follow_up_update"} and related_previous_days:
        return "turning_point"
    if intent in {"pattern_check", "weekly_reflection"} or script_stage >= 3:
        return "reflection"
    if intent == "implicit_recall":
        return "escalation"
    if related_previous_days or primary_event.get("related_event_id"):
        return "recurrence"
    if status in {"ongoing", "unresolved"} and script_stage > 0:
        return "escalation"
    return "initial"


def _surface_event(*, message: dict[str, Any], primary_event: dict[str, Any]) -> str:
    user_message = str(message.get("user_message", "")).strip()
    if user_message:
        return user_message
    return str(primary_event.get("description") or primary_event.get("title") or "")


def _latent_continuity(
    *,
    topic: str,
    related_previous_days: list[int],
    card: dict[str, Any] | None,
    annotations: list[dict[str, Any]],
) -> str:
    if annotations:
        expectation = str(annotations[0].get("relational_expectation", "")).strip()
        if expectation:
            return expectation
    if related_previous_days:
        days = "、".join(str(day) for day in related_previous_days)
        return f"此前已在第 {days} 天讨论过「{topic}」，本日需要接上旧处理方式而不是从零开始。"
    if card:
        concerns = card.get("latent_concerns", [])
        if concerns:
            return str(concerns[0].get("text", ""))
    return "当前节点主要用于建立事件线和后续记忆评估背景。"


def _reason_for_probe(
    *,
    message: dict[str, Any],
    probes: list[dict[str, Any]],
    annotations: list[dict[str, Any]],
    card: dict[str, Any] | None,
) -> str:
    if annotations:
        return str(annotations[0].get("gold_response_strategy", ""))
    if probes:
        assessment = probes[0].get("tom_assessment", {})
        if isinstance(assessment, dict):
            return str(assessment.get("hidden_user_need") or assessment.get("high_score_behavior") or "")
    if card:
        expectations = card.get("memory_detail_expectations", {})
        event_details = expectations.get("event_details", [])
        if event_details:
            return str(event_details[0].get("expected_response_mode", ""))
    return str(message.get("conversation_goal", ""))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe_required_memory_types(
    *,
    probe: dict[str, Any],
    annotations_by_probe_id: dict[str, dict[str, Any]],
) -> list[str]:
    if isinstance(probe.get("required_memory_type"), list):
        return [str(item) for item in probe["required_memory_type"]]
    annotation = annotations_by_probe_id.get(str(probe.get("probe_id")))
    if annotation and isinstance(annotation.get("required_memory_type"), list):
        return [str(item) for item in annotation["required_memory_type"]]
    return []


def _topic_line_fix(
    *,
    topic: str,
    stages: list[str],
    topic_day_count: int,
    topic_probes: list[dict[str, Any]],
) -> str | None:
    if not topic_probes:
        return "No formal probe is attached to this topic; keep it as background unless it becomes a long-term line."
    if "initial" not in stages:
        return "Add or mark an initial node so the line has a clear starting state."
    if "recurrence" not in stages and topic_day_count <= 1:
        return "Add a recurrence node that tests whether the agent can avoid restarting from zero."
    if not any(stage in {"escalation", "turning_point"} for stage in stages):
        return "Add a state-change node, such as action-to-observation or hard-trying-to-downgrade."
    if "resolution" not in stages:
        return "Add a downgrade/recovery node so the line does not only repeat or escalate."
    if "reflection" not in stages:
        return "Add a summary or pattern-recognition node for end-of-line evaluation."
    return None


def _root_event_id(event_id: str, events_by_id: dict[str, dict[str, Any]]) -> str:
    current = str(event_id or "")
    seen = set()
    while current and current not in seen:
        seen.add(current)
        event = events_by_id.get(current, {})
        related = str(event.get("related_event_id") or "")
        if not related:
            return current
        current = related
    return current or str(event_id or "")


def _tau_id(prefix: str, value: str) -> str:
    normalized = str(value or "unknown")
    slug = "".join(
        char.lower()
        if char.isascii() and (char.isalnum() or char == "_")
        else "_"
        for char in normalized
    )
    slug = "_".join(part for part in slug.split("_") if part)[:48]
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{slug or 'x'}_{digest}"


def _first_string(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            if item:
                return str(item)
        return ""
    if value:
        return str(value)
    return ""


def _unique_strings(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value)
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result
