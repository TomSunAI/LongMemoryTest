#!/usr/bin/env python3
"""Generate a two-person M0-M3 evaluation report."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.evaluation.llm_tom_judge import (  # noqa: E402
    FAILURE_TYPES,
    TOM_DIMENSION_RUBRIC,
)
from long_memory_test.evaluation.generation_prompt_reference import (  # noqa: E402
    RELATIONAL_CONDITION_IDS,
    build_answer_condition_system_prompt,
    build_answer_condition_system_prompt_template,
    build_relational_payload_context_template,
    memory_context_from_variant,
)


VARIANTS = ("M0", "M1", "M2", "M3")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a detailed two-person evaluation report.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    run_dir = args.run_dir
    output = args.output or run_dir / "two_person_m0_m3_evaluation_report.md"
    report = build_report(run_dir=run_dir)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {output}")
    return 0


def build_report(*, run_dir: Path) -> str:
    llm = load_json(run_dir / "llm_judge_scores_two_person.json")
    automatic = load_json(run_dir / "automatic_scores_two_person.json")
    conversation = load_json(run_dir / "conversation_log_two_person_eval.json")
    run_config = load_json(run_dir / "run_config.json")

    context_policy = first_context_policy(conversation)
    probe_turns = [turn for turn in conversation["turns"] if turn.get("input", {}).get("tom_dimensions")]
    persona_counts = defaultdict(int)
    for turn in probe_turns:
        persona_counts[persona_id(turn)] += 1

    lines: list[str] = []
    add_header(lines, run_dir=run_dir, probe_turns=probe_turns, conversation=conversation)
    add_chain(lines)
    add_condition_standards(lines, context_policy=context_policy, run_config=run_config)
    add_prompt_reference(lines, conversation=conversation)
    add_scoring_standard(lines, llm=llm)
    add_summary(lines, llm=llm, automatic=automatic)
    add_persona_summary(lines, llm=llm)
    add_case_tables(lines, llm=llm)
    add_representative_cases(lines, llm=llm, conversation=conversation)
    add_files(lines, run_dir=run_dir)
    return "\n".join(lines).rstrip() + "\n"


def add_header(lines: list[str], *, run_dir: Path, probe_turns: list[dict[str, Any]], conversation: dict[str, Any]) -> None:
    extraction = conversation.get("extraction", {})
    lines.extend(
        [
            "# Two-Person M0-M3 Memory Evaluation Report",
            "",
            f"- Run dir: `{run_dir}`",
            f"- Scope: `{', '.join(extraction.get('personas', ['P0001', 'P0002']))}`",
            f"- Generated dialogue turns kept for evaluator context: `{extraction.get('kept_turns', len(conversation.get('turns', [])))}`",
            f"- Targeted probe turns actually scored: `{len(probe_turns)}`",
            f"- LLM judge cases: `{len(probe_turns)} probes x 4 conditions = {len(probe_turns) * 4}`",
            "- Important: scripted/opening turns are retained only as recent dialogue context. Scores are computed only for probe turns with `tom_dimensions`.",
            "",
        ]
    )


def add_chain(lines: list[str]) -> None:
    lines.extend(
        [
            "## Evaluation Chain",
            "",
            "1. Generate M0/M1/M2/M3 answers with the same user input, model, decoding settings, and short-term context policy.",
            "2. Keep full two-person dialogue context for judging continuity.",
            "3. Score only targeted probe turns. Non-probe turns are not scored.",
            "4. Run rule-based ToM triage as a diagnostic layer.",
            "5. Run strict blinded LLM-as-judge as the primary score.",
            "",
        ]
    )


def add_condition_standards(
    lines: list[str], *, context_policy: dict[str, str], run_config: dict[str, Any]
) -> None:
    payload = run_config.get("m0_ld_agent_memory_baseline", {}).get("payload_isolation", {})
    controlled = run_config.get("controlled_variables", {})
    relational = run_config.get("relational_memory_runtimes", {})
    lines.extend(
        [
            "## M0-M3 Condition Standards",
            "",
            "| Condition | Memory access standard | Payload/runtime boundary |",
            "|---|---|---|",
        ]
    )
    for variant in VARIANTS:
        lines.append(
            "| {variant} | {policy} | `{payload}` |".format(
                variant=variant,
                policy=clean_table_text(context_policy.get(variant, "")),
                payload=payload.get(variant, ""),
            )
        )
    lines.extend(
        [
            "",
            "Controlled variables:",
            "",
            f"- Same user input for all conditions: `{controlled.get('same_user_input_for_all_conditions')}`",
            f"- Same model for all conditions: `{controlled.get('same_model_for_all_conditions')}`",
            f"- Same short-term context policy: `{controlled.get('same_short_term_context_policy')}` / `{controlled.get('short_term_context_mode')}`",
            f"- Only long-term memory condition changes: `{controlled.get('only_long_term_memory_condition_changes')}`",
            f"- M1/M2/M3 share the same M0 base memory payload: `{controlled.get('m1_m2_m3_share_m0_base_memory')}`",
            f"- M1/M2/M3 runtime namespace policy: {relational.get('namespace_policy', '')}",
            "",
            "Operational interpretation:",
            "",
            "- M0 is the ordinary LD-Agent-style long/short memory baseline.",
            "- M1 adds conclusion-level relational memory on top of the M0 base.",
            "- M2 adds event-line summary memory on top of M0 + M1.",
            "- M3 adds detail-level relational anchors on top of M0 + M1 + M2.",
            "- Probe turns are read-only: they use available memory for answering but do not write back new memory.",
            "",
        ]
    )


def add_prompt_reference(lines: list[str], *, conversation: dict[str, Any]) -> None:
    examples = prompt_reference_examples(conversation)
    lines.extend(
        [
            "## M1-M3 Prompt Reference",
            "",
            "This section documents the current answer-generation prompt reference for M1/M2/M3. M0 remains the unchanged baseline; the relational priority lines below apply only to M1/M2/M3. Existing scores in this report are not recomputed by this reference section.",
            "",
            "### System Prompt Template",
            "",
        ]
    )
    for condition_id in RELATIONAL_CONDITION_IDS:
        lines.extend(
            [
                f"#### {condition_id}",
                "",
                "```text",
                build_answer_condition_system_prompt_template(condition_id=condition_id),
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "### Relational Payload Template",
            "",
            "The `<M*_MEMORY_CONTEXT>` placeholder above is filled with the composed payload below. The relation layer is the main memory; M0 is included only as ordinary background.",
            "",
        ]
    )
    for condition_id in RELATIONAL_CONDITION_IDS:
        lines.extend(
            [
                f"#### {condition_id}",
                "",
                "```text",
                build_relational_payload_context_template(condition_id=condition_id),
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "### Example Prompts From This Run",
            "",
            "Examples combine the current prompt template with memory contexts retained in the compact evaluator log. They are for implementation reference and audit readability, not evidence that older generated answers have been recomputed.",
            "",
        ]
    )
    for condition_id in RELATIONAL_CONDITION_IDS:
        example = examples.get(condition_id)
        if not example:
            continue
        lines.extend(
            [
                f"<details><summary>{condition_id} example: `{example['message_id']}` / {example['topic']}</summary>",
                "",
                f"- User probe: {example['user_message']}",
                f"- Source detail ids: `{', '.join(example['source_detail_ids']) if example['source_detail_ids'] else 'n/a'}`",
                "",
                "```text",
                example["system_prompt"],
                "```",
                "",
                "</details>",
                "",
            ]
        )


def add_scoring_standard(lines: list[str], *, llm: dict[str, Any]) -> None:
    method = llm.get("method", {})
    lines.extend(
        [
            "## Scoring Standard",
            "",
            f"- Primary evaluator: `{method.get('name')}` / `{method.get('strictness')}`",
            f"- Judge model: `{method.get('judge_provider')}` `{method.get('judge_model')}`",
            f"- Blind review: {method.get('blind_review')}",
            f"- Score scale: {method.get('score_scale')}",
            f"- Gold labels hidden from judge: {method.get('gold_label_policy')}",
            "",
            "| Dimension | Label | 0 | 1 | 2 |",
            "|---|---|---|---|---|",
        ]
    )
    for name, rubric in TOM_DIMENSION_RUBRIC.items():
        lines.append(
            "| {name} | {label} | {s0} | {s1} | {s2} |".format(
                name=name,
                label=clean_table_text(rubric.get("label", "")),
                s0=clean_table_text(rubric.get("score_0", "")),
                s1=clean_table_text(rubric.get("score_1", "")),
                s2=clean_table_text(rubric.get("score_2", "")),
            )
        )
    lines.extend(
        [
            "",
            "Failure taxonomy: " + ", ".join(f"`{item}`" for item in FAILURE_TYPES),
            "",
        ]
    )


def add_summary(lines: list[str], *, llm: dict[str, Any], automatic: dict[str, Any]) -> None:
    lines.extend(
        [
            "## Overall Results",
            "",
            "Primary LLM-as-judge score:",
            "",
            "| Condition | Probe answers | Valid judge | Invalid judge | Avg ToM | Avg confidence | Human review | Flags |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for variant, item in sorted(llm["summary"]["variants"].items()):
        lines.append(
            f"| {variant} | {item['turn_count']} | {item.get('valid_judge_count', item['turn_count'])} | "
            f"{item.get('invalid_judge_count', 0)} | {item['average_tom_score']:.2f} | "
            f"{item['average_confidence']:.3f} | {item['needs_human_review_count']} | "
            f"{item['flag_count']} |"
        )

    lines.extend(
        [
            "",
            "Diagnostic rule-based score:",
            "",
            "| Condition | Probe turns | Avg ToM | Alienation errors | Ask-repeat errors |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for variant, item in sorted(automatic["summary"]["variants"].items()):
        lines.append(
            f"| {variant} | {item['turn_count']} | {item['average_tom_score']:.2f} | "
            f"{item['alienation_error_count']} | {item['ask_repeat_error_count']} |"
        )

    lines.extend(
        [
            "",
            "Dimension averages from LLM judge:",
            "",
            dimension_average_table(llm["summary"].get("dimension_averages", {})),
            "",
            "Failure type counts from LLM judge:",
            "",
            failure_table(llm["summary"]["variants"]),
            "",
            main_readout(llm=llm, automatic=automatic),
            "",
        ]
    )


def main_readout(*, llm: dict[str, Any], automatic: dict[str, Any]) -> str:
    llm_variants = llm["summary"]["variants"]
    automatic_variants = automatic["summary"]["variants"]
    dimension_averages = llm["summary"].get("dimension_averages", {})

    score_winner = max(
        VARIANTS,
        key=lambda variant: llm_variants[variant]["average_tom_score"],
    )
    flag_winner = min(
        VARIANTS,
        key=lambda variant: llm_variants[variant]["flag_count"],
    )
    diagnostic_winner = max(
        VARIANTS,
        key=lambda variant: automatic_variants[variant]["average_tom_score"],
    )
    leading_dimensions = [
        dimension
        for dimension, value in dimension_averages.get(score_winner, {}).items()
        if value == max(
            dimension_averages.get(variant, {}).get(dimension, float("-inf"))
            for variant in VARIANTS
        )
    ]
    dimension_text = (
        ", ".join(f"`{dimension}`" for dimension in leading_dimensions)
        if leading_dimensions
        else "no single LLM-judge dimension"
    )

    return (
        "Main readout: "
        f"{score_winner} has the highest strict LLM judge score "
        f"({llm_variants[score_winner]['average_tom_score']:.2f}). "
        f"{flag_winner} has the fewest total LLM-judge flags "
        f"({llm_variants[flag_winner]['flag_count']}). "
        f"{diagnostic_winner} leads the rule-based diagnostic score "
        f"({automatic_variants[diagnostic_winner]['average_tom_score']:.2f}), "
        "which is diagnostic rather than the primary result. "
        f"The primary-score winner leads on {dimension_text}."
    )


def add_persona_summary(lines: list[str], *, llm: dict[str, Any]) -> None:
    by_persona: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for turn in llm["turns"]:
        pid = str(turn["message_id"]).split("_", 1)[0]
        for variant, result in turn["variants"].items():
            by_persona[pid][variant].append(float(result["tom_score"]))

    lines.extend(
        [
            "## Persona-Level Score Summary",
            "",
            "| Persona | M0 | M1 | M2 | M3 | Winner |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for pid in sorted(by_persona):
        averages = {
            variant: sum(by_persona[pid][variant]) / len(by_persona[pid][variant])
            for variant in VARIANTS
        }
        winner = max(averages, key=averages.get)
        lines.append(
            f"| {pid} | {averages['M0']:.2f} | {averages['M1']:.2f} | "
            f"{averages['M2']:.2f} | {averages['M3']:.2f} | {winner} |"
        )
    lines.append("")


def add_case_tables(lines: list[str], *, llm: dict[str, Any]) -> None:
    lines.extend(
        [
            "## All Probe Cases With Scores",
            "",
            "Each row is one targeted probe. Four condition answers were judged for each row.",
            "",
        ]
    )
    turns_by_persona: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for turn in llm["turns"]:
        turns_by_persona[str(turn["message_id"]).split("_", 1)[0]].append(turn)

    for pid in sorted(turns_by_persona):
        lines.extend(
            [
                f"### {pid}",
                "",
                "| Message ID | Day | Probe type | Topic | Dimensions | M0 | M1 | M2 | M3 | Winner | User probe |",
                "|---|---:|---|---|---|---:|---:|---:|---:|---|---|",
            ]
        )
        for turn in turns_by_persona[pid]:
            scores = variant_scores(turn)
            winner = max(scores, key=scores.get)
            lines.append(
                "| {mid} | {day} | {ptype} | {topic} | {dims} | {m0:.1f} | {m1:.1f} | {m2:.1f} | {m3:.1f} | {winner} | {probe} |".format(
                    mid=turn["message_id"],
                    day=turn.get("day", ""),
                    ptype=clean_table_text(turn.get("probe_type", "")),
                    topic=clean_table_text(turn.get("topic", "")),
                    dims=clean_table_text(", ".join(turn.get("tom_dimensions", []))),
                    m0=scores["M0"],
                    m1=scores["M1"],
                    m2=scores["M2"],
                    m3=scores["M3"],
                    winner=winner,
                    probe=clean_table_text(excerpt(turn.get("user_message", ""), 90)),
                )
            )
        lines.append("")


def add_representative_cases(
    lines: list[str], *, llm: dict[str, Any], conversation: dict[str, Any]
) -> None:
    conversation_by_id = {
        turn.get("source", {}).get("message_id"): turn
        for turn in conversation.get("turns", [])
        if turn.get("input", {}).get("tom_dimensions")
    }
    turns = llm["turns"]
    m2_margin_cases = sorted(
        turns,
        key=lambda turn: variant_scores(turn)["M2"] - max(
            variant_scores(turn)[variant] for variant in ("M0", "M1", "M3")
        ),
        reverse=True,
    )[:6]
    lowest_cases = sorted(
        turns,
        key=lambda turn: sum(variant_scores(turn).values()) / len(VARIANTS),
    )[:6]
    m3_win_cases = [
        turn
        for turn in turns
        if max(variant_scores(turn), key=variant_scores(turn).get) == "M3"
    ][:4]

    lines.extend(["## Representative Cases", ""])
    add_case_detail_section(
        lines,
        title="M2 strongest cases",
        turns=m2_margin_cases,
        conversation_by_id=conversation_by_id,
    )
    add_case_detail_section(
        lines,
        title="Lowest average cases",
        turns=lowest_cases,
        conversation_by_id=conversation_by_id,
    )
    add_case_detail_section(
        lines,
        title="M3 wins despite not winning overall",
        turns=m3_win_cases,
        conversation_by_id=conversation_by_id,
    )


def add_case_detail_section(
    lines: list[str],
    *,
    title: str,
    turns: list[dict[str, Any]],
    conversation_by_id: dict[str, dict[str, Any]],
) -> None:
    lines.extend([f"### {title}", ""])
    for turn in turns:
        scores = variant_scores(turn)
        conv = conversation_by_id.get(turn["message_id"], {})
        target_ids = conv.get("input", {}).get("target_detail_ids", [])
        lines.extend(
            [
                f"#### `{turn['message_id']}` {turn.get('topic', '')}",
                "",
                f"- Persona: `{str(turn['message_id']).split('_', 1)[0]}`; day: `{turn.get('day')}`; probe type: `{turn.get('probe_type')}`",
                f"- User probe: {turn.get('user_message', '')}",
                f"- Target detail ids: `{', '.join(map(str, target_ids)) if target_ids else 'n/a'}`",
                f"- Scores: M0 `{scores['M0']:.1f}`, M1 `{scores['M1']:.1f}`, M2 `{scores['M2']:.1f}`, M3 `{scores['M3']:.1f}`",
                "",
                "| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |",
                "|---|---:|---|---|---|---|",
            ]
        )
        for variant in VARIANTS:
            result = turn["variants"][variant]
            lines.append(
                "| {variant} | {score:.1f} | {review} | {failures} | {reason} | {answer} |".format(
                    variant=variant,
                    score=result["tom_score"],
                    review="yes" if result.get("needs_human_review") else "no",
                    failures=clean_table_text(", ".join(result.get("failure_types", [])) or "-"),
                    reason=clean_table_text(excerpt(result.get("overall_reason", ""), 150)),
                    answer=clean_table_text(excerpt(result.get("answer_excerpt", ""), 120)),
                )
            )
        lines.append("")


def add_files(lines: list[str], *, run_dir: Path) -> None:
    lines.extend(
        [
            "## Files",
            "",
            f"- Evaluator input: `{run_dir / 'conversation_log_two_person_eval.json'}`",
            f"- Rule-based diagnostic scores: `{run_dir / 'automatic_scores_two_person.json'}`",
            f"- LLM judge scores: `{run_dir / 'llm_judge_scores_two_person.json'}`",
            f"- This report: `{run_dir / 'two_person_m0_m3_evaluation_report.md'}`",
            "",
        ]
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def first_context_policy(conversation: dict[str, Any]) -> dict[str, str]:
    for turn in conversation.get("turns", []):
        policy = turn.get("conversation_context_policy")
        if isinstance(policy, dict):
            return {str(key): str(value) for key, value in policy.items()}
    return {}


def prompt_reference_examples(conversation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    examples: dict[str, dict[str, Any]] = {}
    for turn in conversation.get("turns", []):
        if not turn.get("input", {}).get("tom_dimensions"):
            continue
        variants = turn.get("variants", {})
        input_payload = turn.get("input", {})
        for condition_id in RELATIONAL_CONDITION_IDS:
            if condition_id in examples:
                continue
            variant = variants.get(condition_id)
            if not isinstance(variant, dict):
                continue
            memory_context = memory_context_from_variant(variant)
            if not memory_context:
                continue
            memory_payload = variant.get("memory_payload")
            source_detail_ids = []
            if isinstance(memory_payload, dict):
                source_detail_ids = [
                    str(item)
                    for item in memory_payload.get("source_detail_ids", [])
                    if item
                ]
            examples[condition_id] = {
                "message_id": input_payload.get("message_id")
                or turn.get("source", {}).get("message_id", ""),
                "topic": input_payload.get("topic", ""),
                "user_message": input_payload.get("user_message", ""),
                "source_detail_ids": source_detail_ids,
                "system_prompt": build_answer_condition_system_prompt(
                    condition_id=condition_id,
                    memory_context=memory_context,
                ),
            }
        if all(condition_id in examples for condition_id in RELATIONAL_CONDITION_IDS):
            break
    return examples


def persona_id(turn: dict[str, Any]) -> str:
    message_id = str(turn.get("source", {}).get("message_id") or turn.get("message_id") or "")
    return message_id.split("_", 1)[0] if "_" in message_id else message_id


def variant_scores(turn: dict[str, Any]) -> dict[str, float]:
    return {
        variant: float(turn["variants"].get(variant, {}).get("tom_score", 0.0))
        for variant in VARIANTS
    }


def dimension_average_table(dimension_averages: dict[str, dict[str, float]]) -> str:
    dimensions = sorted({name for values in dimension_averages.values() for name in values})
    lines = [
        "| Condition | " + " | ".join(dimensions) + " |",
        "|---" + "|---:" * len(dimensions) + "|",
    ]
    for variant in sorted(dimension_averages):
        values = dimension_averages[variant]
        lines.append(
            "| "
            + variant
            + " | "
            + " | ".join(f"{float(values.get(name, 0.0)):.2f}" for name in dimensions)
            + " |"
        )
    return "\n".join(lines)


def failure_table(variants: dict[str, dict[str, Any]]) -> str:
    failures = sorted(
        {name for item in variants.values() for name in item.get("failure_type_counts", {})}
    )
    lines = [
        "| Condition | " + " | ".join(failures) + " |",
        "|---" + "|---:" * len(failures) + "|",
    ]
    for variant, item in sorted(variants.items()):
        counts = item.get("failure_type_counts", {})
        lines.append(
            "| "
            + variant
            + " | "
            + " | ".join(str(counts.get(name, 0)) for name in failures)
            + " |"
        )
    return "\n".join(lines)


def clean_table_text(value: Any) -> str:
    text = " ".join(str(value).split())
    return text.replace("|", "\\|")


def excerpt(value: Any, length: int) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= length else text[: length - 3] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
