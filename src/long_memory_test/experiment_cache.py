from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
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

CACHE_TIMELINE_EVENTS_PATH = CACHE_DIR / "timeline_events.json"
CACHE_MEMORY_CONDITIONS_PATH = CACHE_DIR / "memory_conditions_combined.json"
CACHE_MANIFEST_PATH = CACHE_DIR / "manifest.json"
EVENT_LINE_AUDIT_PATH = SCRIPT_DATA_DIR / "event_line_audit.json"

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
