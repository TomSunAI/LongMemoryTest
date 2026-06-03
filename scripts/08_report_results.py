#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.experiment_cache import (  # noqa: E402
    M0_MEMORY_PATH,
    M1_MEMORY_PATH,
    M2_MEMORY_PATH,
    M3_MEMORY_PATH,
    PROBE_QUESTION_PLAN_PATH,
    SCRIPT_TIMELINE_PATH,
    latest_run_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write final run report and human review sample.")
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--review-limit", type=int, default=24)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir or latest_run_dir()
    automatic = _load_optional(run_dir / "automatic_scores.json")
    llm_judge = _load_optional(run_dir / "llm_judge_scores.json")
    conversation = _load_optional(run_dir / "conversation_log.json")
    timeline = _load_optional(SCRIPT_TIMELINE_PATH)
    probe_plan = _load_optional(PROBE_QUESTION_PLAN_PATH)
    memory_conditions = _load_memory_condition_defs()
    dependency = _dependency_analysis(llm_judge)
    if dependency["cases"]:
        (run_dir / "dependency_analysis.json").write_text(
            json.dumps(dependency, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    _write_final_report(
        run_dir=run_dir,
        automatic=automatic,
        llm_judge=llm_judge,
        conversation=conversation,
        timeline=timeline,
        probe_plan=probe_plan,
        memory_conditions=memory_conditions,
        dependency=dependency,
    )
    _write_human_review_sample(
        path=run_dir / "human_review_sample.xlsx",
        rows=_review_rows(llm_judge or automatic or conversation, limit=args.review_limit),
    )
    print(f"Wrote {run_dir / 'final_report.md'}")
    print(f"Wrote {run_dir / 'human_review_sample.xlsx'}")
    if dependency["cases"]:
        print(f"Wrote {run_dir / 'dependency_analysis.json'}")
    return 0


def _load_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_final_report(
    *,
    run_dir: Path,
    automatic: dict[str, Any] | None,
    llm_judge: dict[str, Any] | None,
    conversation: dict[str, Any] | None,
    timeline: dict[str, Any] | None,
    probe_plan: dict[str, Any] | None,
    memory_conditions: list[dict[str, Any]],
    dependency: dict[str, Any],
) -> None:
    primary_scores = llm_judge or automatic
    lines = [
        "# Long Memory Experiment Final Report",
        "",
        f"- Run dir: `{run_dir}`",
        f"- Conversation turns: {_turn_count(conversation)}",
        "",
        "## Table 1. Memory Conditions",
        "",
        _memory_condition_table(memory_conditions),
        "",
        "## Table 2. Topic Lines And Turning Points",
        "",
        _topic_turning_point_table(timeline),
        "",
        "## Table 3. Probe Type And ToM Dimension Coverage",
        "",
        _probe_coverage_table(probe_plan),
        "",
        "## Table 4. Overall And Dimension Scores",
        "",
        _overall_dimension_scores_table(primary_scores, memory_conditions=memory_conditions),
        "",
        "## Table 5. Results By Probe Type",
        "",
        _probe_type_result_table(primary_scores, probe_plan=probe_plan, memory_conditions=memory_conditions),
        "",
        "## Table 6. Error Type Statistics",
        "",
        _failure_type_table(llm_judge, memory_conditions=memory_conditions),
        "",
        "## Table 7. Dependency Question Analysis",
        "",
        _dependency_table(dependency, probe_plan=probe_plan, memory_conditions=memory_conditions),
        "",
        "## Case Studies",
        "",
        _case_study_section(llm_judge),
        "",
        "## Automatic Scores Triage",
        "",
        _summary_table(automatic),
        "",
        "## LLM Judge Summary",
        "",
        _summary_table(llm_judge),
        "",
        "## Prompt Templates",
        "",
        "- BEI annotation prompt: `long_memory_experiment/data/prompt_templates/bei_annotation_prompt.md`",
        "- Probe generation prompt: `long_memory_experiment/data/prompt_templates/probe_generation_prompt.md`",
        "- LLM-as-judge prompt: `long_memory_experiment/data/prompt_templates/llm_judge_prompt.md`",
        "",
        "## Notes",
        "",
        "- This report uses the event-first, BEI-calibrated data structure.",
        "- Rule scoring is triage only; LLM judge is the semantic scoring layer.",
        "- `human_review_sample.xlsx` hides memory condition names and uses Condition A/B/C/D.",
        "",
    ]
    (run_dir / "final_report.md").write_text("\n".join(lines), encoding="utf-8")


def _turn_count(conversation: dict[str, Any] | None) -> int:
    if not conversation:
        return 0
    turns = conversation.get("turns", [])
    return len(turns) if isinstance(turns, list) else 0


def _load_memory_condition_defs() -> list[dict[str, Any]]:
    conditions = []
    for path in [M0_MEMORY_PATH, M1_MEMORY_PATH, M2_MEMORY_PATH, M3_MEMORY_PATH]:
        data = _load_optional(path)
        if not data:
            continue
        spec = data.get("condition_spec", {})
        if isinstance(spec, dict):
            conditions.append(spec)
    return conditions


def _condition_ids(memory_conditions: list[dict[str, Any]] | None = None) -> list[str]:
    ids = [
        str(item.get("condition_id", ""))
        for item in (memory_conditions or [])
        if item.get("condition_id")
    ]
    return ids or ["M0", "M1", "M2", "M3"]


def _standard_tom_dimensions() -> list[str]:
    return [
        "hidden_intent_recognition",
        "emotional_state_recognition",
        "relationship_expectation_recognition",
        "shared_context_invocation",
        "natural_detail_use",
        "memory_misuse",
        "alienation_error_rate",
    ]


def _standard_failure_types() -> list[str]:
    return [
        "memory_absence",
        "memory_misuse",
        "memory_overuse",
        "fabrication",
        "alienation",
        "instruction_only_success",
    ]


def _preferred_probe_types() -> list[str]:
    return [
        "current_understanding",
        "memory_invocation",
        "state_transformation",
        "relational_boundary",
        "alienation",
        "natural_detail",
    ]


def _memory_condition_table(conditions: list[dict[str, Any]]) -> str:
    if not conditions:
        return "_Memory condition files not found._"
    rows = [
        "| Condition | Report Name | Can Read | Cannot Read | Theoretical Use |",
        "|---|---|---|---|---|",
    ]
    for item in conditions:
        rows.append(
            "| "
            + " | ".join(
                [
                    _md(item.get("condition_id", "")),
                    _md(item.get("name", "")),
                    _md(", ".join(str(value) for value in item.get("can_read", []))),
                    _md(", ".join(str(value) for value in item.get("cannot_read", []))),
                    _md(item.get("theoretical_use", item.get("definition", ""))),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _topic_turning_point_table(timeline: dict[str, Any] | None) -> str:
    if not timeline:
        return "_Timeline not generated yet._"
    days = timeline.get("days", [])
    if not isinstance(days, list) or not days:
        return "_No timeline days found._"
    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for day in days:
        if isinstance(day, dict):
            by_topic[str(day.get("main_topic", ""))].append(day)
    rows = [
        "| Topic Line | Days | Stages | Key Turning / Escalation Nodes | Probe Nodes |",
        "|---|---|---|---|---|",
    ]
    for topic, items in sorted(by_topic.items()):
        stages = []
        key_nodes = []
        probe_nodes = []
        for item in sorted(items, key=lambda value: int(value.get("day", 0))):
            day = int(item.get("day", 0))
            stage = str(item.get("event_stage", ""))
            stages.append(f"D{day:02d}:{stage}")
            if stage in {"escalation", "turning_point", "resolution", "reflection"}:
                key_nodes.append(f"D{day:02d} {stage}: {item.get('surface_event', '')}")
            if item.get("probe_candidate") or item.get("probe_ids"):
                probe_nodes.append(f"D{day:02d}")
        rows.append(
            "| "
            + " | ".join(
                [
                    _md(topic),
                    _md(", ".join(f"D{int(item.get('day', 0)):02d}" for item in items)),
                    _md(", ".join(stages)),
                    _md("; ".join(key_nodes) if key_nodes else "None marked"),
                    _md(", ".join(probe_nodes)),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _probe_coverage_table(probe_plan: dict[str, Any] | None) -> str:
    if not probe_plan:
        return "_Probe plan not generated yet._"
    probes = probe_plan.get("probe_questions", [])
    if not isinstance(probes, list) or not probes:
        return "_No probe questions found._"
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for probe in probes:
        if isinstance(probe, dict):
            by_type[str(probe.get("probe_type", ""))].append(probe)
    rows = [
        "| Probe Type | Count | ToM Dimensions Covered | Required Memory Types | Explicit / Implicit Mix |",
        "|---|---:|---|---|---|",
    ]
    for probe_type, items in sorted(by_type.items()):
        dimensions = sorted(
            {
                str(dimension)
                for item in items
                for dimension in item.get("tom_dimensions", [])
            }
        )
        memory_types = sorted(
            {
                str(memory_type)
                for item in items
                for memory_type in item.get("required_memory_type", [])
            }
        )
        explicit_count = sum(
            1
            for item in items
            if probe_type == "memory_invocation" or "不想从头" in str(item.get("user_message", ""))
        )
        implicit_count = len(items) - explicit_count
        rows.append(
            "| "
            + " | ".join(
                [
                    _md(probe_type),
                    str(len(items)),
                    _md(", ".join(dimensions)),
                    _md(", ".join(memory_types)),
                    _md(f"explicit={explicit_count}, implicit={implicit_count}"),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _summary_table(evaluation: dict[str, Any] | None) -> str:
    if not evaluation:
        return "_Not generated yet._"
    variants = evaluation.get("summary", {}).get("variants", {})
    if not isinstance(variants, dict) or not variants:
        return "_No variant summary found._"
    rows = ["| Variant | Turns | Avg ToM | Failure Marks | Human Review |", "|---|---:|---:|---:|---:|"]
    for variant, item in sorted(variants.items()):
        failure_marks = sum(item.get("failure_type_counts", {}).values()) or item.get("flag_count", 0)
        rows.append(
            "| "
            f"{variant} | "
            f"{item.get('turn_count', item.get('probe_answers', 0))} | "
            f"{item.get('average_tom_score', '')} | "
            f"{failure_marks} | "
            f"{item.get('needs_human_review_count', item.get('human_review', 0))} |"
        )
    return "\n".join(rows)


def _overall_dimension_scores_table(
    evaluation: dict[str, Any] | None,
    *,
    memory_conditions: list[dict[str, Any]],
) -> str:
    variants = (
        evaluation.get("summary", {}).get("variants", {})
        if evaluation
        else {}
    )
    dimension_averages = (
        evaluation.get("summary", {}).get("dimension_averages", {})
        if evaluation
        else {}
    )
    dimensions = _standard_tom_dimensions()
    rows = [
        "| Condition | Answers | Avg ToM | "
        + " | ".join(dimensions)
        + " |",
        "|---|---:|---:" + "|---:" * len(dimensions) + "|",
    ]
    for variant in _condition_ids(memory_conditions):
        item = variants.get(variant, {}) if isinstance(variants, dict) else {}
        averages = dimension_averages.get(variant, {})
        rows.append(
            "| "
            + str(variant)
            + " | "
            + str(item.get("turn_count", item.get("probe_answers", "TBD")))
            + " | "
            + str(item.get("average_tom_score", "TBD"))
            + " | "
            + " | ".join(str(averages.get(dimension, "TBD")) for dimension in dimensions)
            + " |"
        )
    return "\n".join(rows)


def _probe_type_result_table(
    evaluation: dict[str, Any] | None,
    *,
    probe_plan: dict[str, Any] | None,
    memory_conditions: list[dict[str, Any]],
) -> str:
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for turn in (evaluation or {}).get("turns", []):
        if not isinstance(turn, dict):
            continue
        probe_type = str(turn.get("probe_type", ""))
        if not probe_type:
            continue
        for variant, judgement in (turn.get("variants") or {}).items():
            if isinstance(judgement, dict):
                grouped[probe_type][str(variant)].append(_score_value(judgement))
    variants = _condition_ids(memory_conditions)
    probe_type_counts = _probe_type_counts(probe_plan)
    rows = [
        "| Probe Type | Count | " + " | ".join(f"{variant} Avg" for variant in variants) + " |",
        "|---|---:" + "|---:" * len(variants) + "|",
    ]
    all_probe_types = [
        *_preferred_probe_types(),
        *sorted((set(grouped) | set(probe_type_counts)) - set(_preferred_probe_types())),
    ]
    for probe_type in all_probe_types:
        count = max(
            [len(values) for values in grouped.get(probe_type, {}).values()]
            + [probe_type_counts.get(probe_type, 0)]
        )
        scores = []
        for variant in variants:
            values = grouped[probe_type].get(variant, [])
            scores.append(f"{sum(values) / len(values):.2f}" if values else "TBD")
        rows.append(
            "| " + _md(probe_type) + " | " + str(count) + " | " + " | ".join(scores) + " |"
        )
    return "\n".join(rows)


def _probe_type_counts(probe_plan: dict[str, Any] | None) -> dict[str, int]:
    summary_counts = (
        probe_plan.get("summary", {}).get("probe_type_counts", {})
        if probe_plan
        else {}
    )
    if isinstance(summary_counts, dict) and summary_counts:
        return {str(key): int(value) for key, value in summary_counts.items()}
    counts: dict[str, int] = defaultdict(int)
    for probe in (probe_plan or {}).get("probe_questions", []):
        if isinstance(probe, dict):
            counts[str(probe.get("probe_type", ""))] += 1
    return dict(counts)


def _failure_type_table(
    evaluation: dict[str, Any] | None,
    *,
    memory_conditions: list[dict[str, Any]] | None = None,
) -> str:
    variants = (
        evaluation.get("summary", {}).get("variants", {})
        if evaluation
        else {}
    )
    names = _standard_failure_types()
    rows = ["| Condition | " + " | ".join(names) + " |", "|---" + "|---:" * len(names) + "|"]
    for variant in _condition_ids(memory_conditions):
        item = variants.get(variant, {}) if isinstance(variants, dict) else {}
        counts = item.get("failure_type_counts", {}) if isinstance(item, dict) else {}
        rows.append(
            "| "
            + str(variant)
            + " | "
            + " | ".join(str(counts.get(name, "TBD")) for name in names)
            + " |"
        )
    return "\n".join(rows)


def _case_study_section(evaluation: dict[str, Any] | None) -> str:
    case_1 = _find_case_m0_fail_m3_pass(evaluation)
    case_2 = _find_case_m1_m2_m3_gradient(evaluation)
    case_3 = _find_case_m3_overuse(evaluation)
    return "\n\n".join(
        [
            "### Case Study 1. M0 generic memory fails; M3 catches the relational anchor\n\n"
            + _render_case_study(case_1),
            "### Case Study 2. M1 conclusion is insufficient; M2 restores event line; M3 adds boundary/familiarity\n\n"
            + _render_case_study(case_2),
            "### Case Study 3. M3 overuses memory: failure boundary\n\n"
            + _render_case_study(case_3),
        ]
    )


def _find_case_m0_fail_m3_pass(evaluation: dict[str, Any] | None) -> dict[str, Any] | None:
    for turn in _iter_scored_turns(evaluation):
        variants = turn.get("variants", {})
        m0 = variants.get("M0", {})
        m3 = variants.get("M3", {})
        if _score_value(m0) < 60 <= _score_value(m3):
            return _case_payload(turn, ["M0", "M3"])
    return None


def _find_case_m1_m2_m3_gradient(evaluation: dict[str, Any] | None) -> dict[str, Any] | None:
    for turn in _iter_scored_turns(evaluation):
        variants = turn.get("variants", {})
        m1 = _score_value(variants.get("M1", {}))
        m2 = _score_value(variants.get("M2", {}))
        m3 = _score_value(variants.get("M3", {}))
        if m1 < m2 <= m3 and m3 >= 60:
            return _case_payload(turn, ["M1", "M2", "M3"])
    return None


def _find_case_m3_overuse(evaluation: dict[str, Any] | None) -> dict[str, Any] | None:
    for turn in _iter_scored_turns(evaluation):
        m3 = (turn.get("variants") or {}).get("M3", {})
        failure_types = set(m3.get("failure_types", [])) if isinstance(m3, dict) else set()
        if failure_types & {"memory_overuse", "memory_misuse", "fabrication"}:
            return _case_payload(turn, ["M3"])
    return None


def _iter_scored_turns(evaluation: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not evaluation:
        return []
    return [turn for turn in evaluation.get("turns", []) if isinstance(turn, dict)]


def _case_payload(turn: dict[str, Any], variants: list[str]) -> dict[str, Any]:
    variant_payloads = {}
    for variant in variants:
        judgement = (turn.get("variants") or {}).get(variant, {})
        if not isinstance(judgement, dict):
            continue
        variant_payloads[variant] = {
            "score": _score_value(judgement),
            "failure_types": judgement.get("failure_types", []),
            "answer_excerpt": judgement.get("answer_excerpt", ""),
            "reason": judgement.get("overall_reason", ""),
        }
    return {
        "message_id": turn.get("message_id"),
        "day": turn.get("day"),
        "topic": turn.get("topic"),
        "probe_type": turn.get("probe_type"),
        "user_message": turn.get("user_message"),
        "variants": variant_payloads,
    }


def _render_case_study(case: dict[str, Any] | None) -> str:
    if not case:
        return "\n".join(
            [
                "| Field | Standard Fill |",
                "|---|---|",
                "| Selection rule | Auto-filled after LLM judge results are available. |",
                "| Probe metadata | `message_id`, day, topic, probe_type, user_message. |",
                "| Condition comparison | Relevant M0/M1/M2/M3 scores and answer excerpts. |",
                "| Evidence | Judge `overall_reason`, `evidence_quote`, and `failure_types`. |",
                "| Status | TBD until `llm_judge_scores.json` exists. |",
            ]
        )
    lines = [
        f"- Probe: `{case.get('message_id')}` day={case.get('day')} "
        f"type={case.get('probe_type')} topic={case.get('topic')}",
        f"- User message: {_md(str(case.get('user_message', '')))}",
    ]
    for variant, item in sorted(case.get("variants", {}).items()):
        lines.append(
            f"- {variant}: score={item.get('score')} "
            f"failure_types={item.get('failure_types', [])}; "
            f"reason={_md(str(item.get('reason', '')))}; "
            f"excerpt={_md(str(item.get('answer_excerpt', '')))}"
        )
    return "\n".join(lines)


def _dependency_table(
    dependency: dict[str, Any],
    *,
    probe_plan: dict[str, Any] | None,
    memory_conditions: list[dict[str, Any]],
) -> str:
    summary = dependency.get("summary_by_variant", {})
    labels = [
        "fully_correct",
        "remember_but_cannot_use",
        "guessing_current_cue_success",
        "full_failure",
    ]
    planned_pairs = _planned_dependency_group_count(probe_plan)
    rows = ["| Variant | Pairs | " + " | ".join(labels) + " |", "|---|---:" + "|---:" * len(labels) + "|"]
    for variant in _condition_ids(memory_conditions):
        item = summary.get(variant, {}) if isinstance(summary, dict) else {}
        rows.append(
            "| "
            + str(variant)
            + " | "
            + str(item.get("pair_count", planned_pairs if planned_pairs else "TBD"))
            + " | "
            + " | ".join(
                str(item.get("classification_counts", {}).get(label, "TBD"))
                for label in labels
            )
            + " |"
        )
    return "\n".join(rows)


def _planned_dependency_group_count(probe_plan: dict[str, Any] | None) -> int:
    if not probe_plan:
        return 0
    value = probe_plan.get("summary", {}).get("dependency_group_count")
    if value is not None:
        return int(value)
    return len(
        {
            probe.get("dependency_analysis", {}).get("group_id")
            for probe in probe_plan.get("probe_questions", [])
            if isinstance(probe, dict)
            and probe.get("dependency_analysis", {}).get("group_id")
        }
    )


def _review_rows(source: dict[str, Any] | None, *, limit: int) -> list[list[str]]:
    rows = [[
        "case_id",
        "message_id",
        "day",
        "topic",
        "probe_type",
        "blind_condition",
        "tom_score",
        "confidence",
        "failure_types",
        "needs_human_review",
        "sampling_bucket",
        "user_message",
        "answer_excerpt",
        "overall_reason",
        "human_score",
        "human_failure_type",
        "human_notes",
    ]]
    if not source:
        return rows
    candidates = _review_candidates(source)
    selected = _select_review_candidates(candidates, limit=limit)
    for item in selected:
        judgement = item["judgement"]
        rows.append(
            [
                item["case_id"],
                item["message_id"],
                item["day"],
                item["topic"],
                item["probe_type"],
                item["blind_condition"],
                str(judgement.get("tom_score", "")),
                str(judgement.get("confidence", "")),
                ", ".join(str(value) for value in judgement.get("failure_types", [])),
                str(judgement.get("needs_human_review", "")),
                item["sampling_bucket"],
                item["user_message"],
                str(judgement.get("answer_excerpt", "")),
                str(judgement.get("overall_reason", "")),
                "",
                "",
                "",
            ]
        )
    return rows


def _review_candidates(source: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    divergence_ids = _divergent_message_ids(source)
    for turn in source.get("turns", []):
        if not isinstance(turn, dict):
            continue
        for variant, judgement in sorted((turn.get("variants") or {}).items()):
            if not isinstance(judgement, dict):
                continue
            message_id = str(turn.get("message_id", ""))
            score = _score_value(judgement)
            if message_id in divergence_ids:
                bucket = "model_divergence"
            elif judgement.get("needs_human_review") or score < 50:
                bucket = "low_or_flagged"
            elif score >= 80:
                bucket = "high_score"
            else:
                bucket = "random_middle"
            blind_condition = _blind_condition_label(str(variant))
            candidates.append(
                {
                    "case_id": f"{message_id}:{blind_condition}",
                    "message_id": message_id,
                    "day": str(turn.get("day", "")),
                    "topic": str(turn.get("topic", "")),
                    "probe_type": str(turn.get("probe_type", "")),
                    "variant": str(variant),
                    "blind_condition": blind_condition,
                    "sampling_bucket": bucket,
                    "user_message": str(turn.get("user_message", "")),
                    "judgement": judgement,
                }
            )
    return candidates


def _select_review_candidates(candidates: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    priority = {
        "low_or_flagged": 0,
        "model_divergence": 1,
        "high_score": 2,
        "random_middle": 3,
    }
    selected = []
    seen = set()
    for item in sorted(
        candidates,
        key=lambda value: (
            priority.get(value["sampling_bucket"], 99),
            value["message_id"],
            value["blind_condition"],
        ),
    ):
        if len(selected) >= limit:
            break
        if item["case_id"] in seen:
            continue
        selected.append(item)
        seen.add(item["case_id"])
    return selected


def _divergent_message_ids(source: dict[str, Any], *, threshold: float = 25.0) -> set[str]:
    result = set()
    for turn in source.get("turns", []):
        if not isinstance(turn, dict):
            continue
        scores = [
            _score_value(judgement)
            for judgement in (turn.get("variants") or {}).values()
            if isinstance(judgement, dict)
        ]
        if len(scores) >= 2 and max(scores) - min(scores) >= threshold:
            result.add(str(turn.get("message_id", "")))
    return result


def _dependency_analysis(
    evaluation: dict[str, Any] | None,
    *,
    correct_threshold: float = 60.0,
) -> dict[str, Any]:
    if not evaluation:
        return {
            "method": {
                "correct_threshold": correct_threshold,
                "classification": {},
            },
            "summary_by_variant": {},
            "cases": [],
        }

    turns_by_id = {
        str(turn.get("message_id", "")): turn
        for turn in evaluation.get("turns", [])
        if isinstance(turn, dict)
    }
    cases = []
    summary: dict[str, Any] = defaultdict(
        lambda: {
            "pair_count": 0,
            "classification_counts": defaultdict(int),
        }
    )

    for main_turn in turns_by_id.values():
        dependency_info = main_turn.get("dependency_analysis", {})
        if not isinstance(dependency_info, dict) or dependency_info.get("role") != "main":
            continue
        dependency_id = str(dependency_info.get("paired_probe_id") or "")
        dependency_turn = turns_by_id.get(dependency_id)
        if not dependency_turn:
            continue
        for variant, main_judgement in sorted((main_turn.get("variants") or {}).items()):
            dependency_judgement = (dependency_turn.get("variants") or {}).get(variant)
            if not isinstance(main_judgement, dict) or not isinstance(dependency_judgement, dict):
                continue
            dependency_score = _score_value(dependency_judgement)
            main_score = _score_value(main_judgement)
            classification = _dependency_classification(
                dependency_score=dependency_score,
                main_score=main_score,
                threshold=correct_threshold,
            )
            summary_item = summary[str(variant)]
            summary_item["pair_count"] += 1
            summary_item["classification_counts"][classification] += 1
            cases.append(
                {
                    "variant": str(variant),
                    "blind_condition": _blind_condition_label(str(variant)),
                    "group_id": dependency_info.get("group_id"),
                    "dependency_probe_id": dependency_id,
                    "main_probe_id": str(main_turn.get("message_id", "")),
                    "topic": main_turn.get("topic"),
                    "dependency_score": dependency_score,
                    "main_score": main_score,
                    "classification": classification,
                }
            )

    return {
        "method": {
            "correct_threshold": correct_threshold,
            "classification": {
                "fully_correct": "依赖题 D 对、主问题 C 对。",
                "remember_but_cannot_use": "依赖题 D 对、主问题 C 错。",
                "guessing_current_cue_success": "依赖题 D 错、主问题 C 对。",
                "full_failure": "依赖题 D 错、主问题 C 错。",
            },
        },
        "summary_by_variant": {
            variant: {
                "pair_count": item["pair_count"],
                "classification_counts": dict(sorted(item["classification_counts"].items())),
            }
            for variant, item in sorted(summary.items())
        },
        "cases": cases,
    }


def _dependency_classification(
    *,
    dependency_score: float,
    main_score: float,
    threshold: float,
) -> str:
    dependency_correct = dependency_score >= threshold
    main_correct = main_score >= threshold
    if dependency_correct and main_correct:
        return "fully_correct"
    if dependency_correct and not main_correct:
        return "remember_but_cannot_use"
    if not dependency_correct and main_correct:
        return "guessing_current_cue_success"
    return "full_failure"


def _score_value(judgement: dict[str, Any]) -> float:
    try:
        return float(judgement.get("tom_score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _md(value: Any) -> str:
    text = " ".join(str(value).split())
    return text.replace("|", "\\|")


def _blind_condition_label(variant_name: str) -> str:
    labels = {
        "M0": "Condition A",
        "M1": "Condition B",
        "M2": "Condition C",
        "M3": "Condition D",
    }
    return labels.get(str(variant_name), "Condition X")


def _write_human_review_sample(*, path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_data = "\n".join(
        "      <row r=\"{row_num}\">{cells}</row>".format(
            row_num=index,
            cells="".join(
                _cell(column=index_col, row=index, value=value)
                for index_col, value in enumerate(row, start=1)
            ),
        )
        for index, row in enumerate(rows, start=1)
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        f"{sheet_data}"
        "</sheetData>"
        "</worksheet>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml())
        zf.writestr("_rels/.rels", _root_rels_xml())
        zf.writestr("xl/workbook.xml", _workbook_xml())
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _cell(*, column: int, row: int, value: str) -> str:
    coordinate = f"{_column_name(column)}{row}"
    escaped = html.escape(value, quote=False)
    return f'<c r="{coordinate}" t="inlineStr"><is><t>{escaped}</t></is></c>'


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""


def _root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _workbook_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="human_review_sample" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""


def _workbook_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


if __name__ == "__main__":
    raise SystemExit(main())
