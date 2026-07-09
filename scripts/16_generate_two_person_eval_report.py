#!/usr/bin/env python3
"""Generate a two-person memory evaluation report."""

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


DEFAULT_VARIANTS = ("M0", "M1", "M2", "M3")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a detailed two-person evaluation report.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    run_dir = args.run_dir
    output = args.output or run_dir / "two_person_eval_report.md"
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
    variants = report_variants(llm=llm, conversation=conversation, run_config=run_config)
    persona_counts = defaultdict(int)
    for turn in probe_turns:
        persona_counts[persona_id(turn)] += 1

    lines: list[str] = []
    add_header(lines, run_dir=run_dir, probe_turns=probe_turns, conversation=conversation, variants=variants)
    add_chain(lines, variants=variants)
    add_condition_standards(lines, context_policy=context_policy, run_config=run_config, variants=variants)
    add_prompt_reference(lines, conversation=conversation, variants=variants)
    add_scoring_standard(lines, llm=llm)
    add_summary(lines, llm=llm, automatic=automatic, variants=variants)
    add_persona_summary(lines, llm=llm, variants=variants)
    add_case_tables(lines, llm=llm, variants=variants)
    add_representative_cases(lines, llm=llm, conversation=conversation, variants=variants)
    add_files(lines, run_dir=run_dir)
    return "\n".join(lines).rstrip() + "\n"


def add_header(
    lines: list[str],
    *,
    run_dir: Path,
    probe_turns: list[dict[str, Any]],
    conversation: dict[str, Any],
    variants: tuple[str, ...],
) -> None:
    extraction = conversation.get("extraction", {})
    variant_label = "/".join(variants)
    lines.extend(
        [
            f"# Two-Person {variant_label} Memory Evaluation Report",
            "",
            f"- Run dir: `{run_dir}`",
            f"- Scope: `{', '.join(extraction.get('personas', ['P0001', 'P0002']))}`",
            f"- Generated dialogue turns kept for evaluator context: `{extraction.get('kept_turns', len(conversation.get('turns', [])))}`",
            f"- Targeted probe turns actually scored: `{len(probe_turns)}`",
            f"- Conditions scored: `{', '.join(variants)}`",
            f"- LLM judge cases: `{len(probe_turns)} probes x {len(variants)} conditions = {len(probe_turns) * len(variants)}`",
            "- Important: scripted/opening turns are retained only as recent dialogue context. Scores are computed only for probe turns with `tom_dimensions`.",
            "",
        ]
    )


def add_chain(lines: list[str], *, variants: tuple[str, ...]) -> None:
    lines.extend(
        [
            "## Evaluation Chain",
            "",
            f"1. Generate `{', '.join(variants)}` answers with the same user input, model, decoding settings, and short-term context policy.",
            "2. Keep full two-person dialogue context for judging continuity.",
            "3. Score only targeted probe turns. Non-probe turns are not scored.",
            "4. Run rule-based ToM triage as a diagnostic layer.",
            "5. Run strict blinded LLM-as-judge as the primary score.",
            "",
        ]
    )


def add_condition_standards(
    lines: list[str],
    *,
    context_policy: dict[str, str],
    run_config: dict[str, Any],
    variants: tuple[str, ...],
) -> None:
    payload = run_config.get("m0_ld_agent_memory_baseline", {}).get("payload_isolation", {})
    controlled = run_config.get("controlled_variables", {})
    relational = run_config.get("relational_memory_runtimes", {})
    lines.extend(
        [
            "## Condition Standards",
            "",
            "| Condition | Memory access standard | Payload/runtime boundary |",
            "|---|---|---|",
        ]
    )
    for variant in variants:
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
            f"- Z1/Z2/Z3 use M0 base memory: `{controlled.get('z1_z2_z3_use_m0_base_memory')}`",
            f"- U1/U2/U3 use M0 base memory: `{controlled.get('u1_u2_u3_use_m0_base_memory')}`",
            f"- Relational runtime namespace policy: {relational.get('namespace_policy', '')}",
            "",
            "Operational interpretation:",
            "",
            *condition_interpretation_lines(variants),
            "- Probe turns are read-only: they use available memory for answering but do not write back new memory.",
            "",
        ]
    )


def add_prompt_reference(lines: list[str], *, conversation: dict[str, Any], variants: tuple[str, ...]) -> None:
    relational_variants = tuple(variant for variant in variants if variant in RELATIONAL_CONDITION_IDS)
    if not relational_variants:
        return
    examples = prompt_reference_examples(conversation, variants=relational_variants)
    lines.extend(
        [
            "## Relational Prompt Reference",
            "",
            "This section documents the current answer-generation prompt reference for relational conditions in this run. Existing scores in this report are not recomputed by this reference section.",
            "",
            "### System Prompt Template",
            "",
        ]
    )
    for condition_id in relational_variants:
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
            "The `<*_MEMORY_CONTEXT>` placeholder above is filled with the composed payload below. M-series payloads may include M0 as background; Z-series payloads are independent and do not compose with M0.",
            "",
        ]
    )
    for condition_id in relational_variants:
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
    for condition_id in relational_variants:
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


def add_summary(
    lines: list[str],
    *,
    llm: dict[str, Any],
    automatic: dict[str, Any],
    variants: tuple[str, ...],
) -> None:
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
            "Persona variance from LLM judge:",
            "",
            persona_variance_table(llm=llm, variants=variants),
            "",
            "Failure type counts from LLM judge:",
            "",
            failure_table(llm["summary"]["variants"]),
            "",
            main_readout(llm=llm, automatic=automatic, variants=variants),
            "",
        ]
    )


def main_readout(*, llm: dict[str, Any], automatic: dict[str, Any], variants: tuple[str, ...]) -> str:
    llm_variants = llm["summary"]["variants"]
    automatic_variants = automatic["summary"]["variants"]
    dimension_averages = llm["summary"].get("dimension_averages", {})

    score_winner = max(
        variants,
        key=lambda variant: llm_variants[variant]["average_tom_score"],
    )
    flag_winner = min(
        variants,
        key=lambda variant: llm_variants[variant]["flag_count"],
    )
    diagnostic_winner = max(
        variants,
        key=lambda variant: automatic_variants[variant]["average_tom_score"],
    )
    leading_dimensions = [
        dimension
        for dimension, value in dimension_averages.get(score_winner, {}).items()
        if value == max(
            dimension_averages.get(variant, {}).get(dimension, float("-inf"))
            for variant in variants
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


def add_persona_summary(lines: list[str], *, llm: dict[str, Any], variants: tuple[str, ...]) -> None:
    by_persona: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for turn in llm["turns"]:
        pid = str(turn["message_id"]).split("_", 1)[0]
        for variant, result in turn["variants"].items():
            by_persona[pid][variant].append(float(result["tom_score"]))

    lines.extend(
        [
            "## Persona-Level Score Summary",
            "",
            "| Persona | " + " | ".join(variants) + " | Winner |",
            "|---" + "|---:" * len(variants) + "|---|",
        ]
    )
    for pid in sorted(by_persona):
        averages = {
            variant: sum(by_persona[pid][variant]) / len(by_persona[pid][variant])
            for variant in variants
        }
        winner = max(averages, key=averages.get)
        lines.append(
            "| "
            + pid
            + " | "
            + " | ".join(f"{averages[variant]:.2f}" for variant in variants)
            + f" | {winner} |"
        )
    lines.append("")


def add_case_tables(lines: list[str], *, llm: dict[str, Any], variants: tuple[str, ...]) -> None:
    lines.extend(
        [
            "## All Probe Cases With Scores",
            "",
            f"Each row is one targeted probe. {len(variants)} condition answers were judged for each row.",
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
                "| Message ID | Day | Probe type | Topic | Dimensions | "
                + " | ".join(variants)
                + " | Winner | User probe |",
                "|---|---:|---|---|---"
                + "|---:" * len(variants)
                + "|---|---|",
            ]
        )
        for turn in turns_by_persona[pid]:
            scores = variant_scores(turn, variants=variants)
            winner = max(scores, key=scores.get)
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(turn["message_id"]),
                        str(turn.get("day", "")),
                        clean_table_text(turn.get("probe_type", "")),
                        clean_table_text(turn.get("topic", "")),
                        clean_table_text(", ".join(turn.get("tom_dimensions", []))),
                        *[f"{scores[variant]:.1f}" for variant in variants],
                        winner,
                        clean_table_text(excerpt(turn.get("user_message", ""), 90)),
                    ]
                )
                + " |"
            )
        lines.append("")


def add_representative_cases(
    lines: list[str],
    *,
    llm: dict[str, Any],
    conversation: dict[str, Any],
    variants: tuple[str, ...],
) -> None:
    conversation_by_id = {
        turn.get("source", {}).get("message_id"): turn
        for turn in conversation.get("turns", [])
        if turn.get("input", {}).get("tom_dimensions")
    }
    turns = llm["turns"]
    anchor_variant = preferred_variant(variants, ("M2", "Z2", "U2"), default=variants[0])
    detail_variant = preferred_variant(variants, ("M3", "Z3", "U3"), default=variants[-1])
    anchor_margin_cases = sorted(
        turns,
        key=lambda turn: variant_scores(turn, variants=variants)[anchor_variant] - max(
            score
            for variant, score in variant_scores(turn, variants=variants).items()
            if variant != anchor_variant
        ),
        reverse=True,
    )[:6]
    lowest_cases = sorted(
        turns,
        key=lambda turn: sum(variant_scores(turn, variants=variants).values()) / len(variants),
    )[:6]
    detail_win_cases = [
        turn
        for turn in turns
        if max(
            variant_scores(turn, variants=variants),
            key=variant_scores(turn, variants=variants).get,
        )
        == detail_variant
    ][:4]

    lines.extend(["## Representative Cases", ""])
    add_case_detail_section(
        lines,
        title=f"{anchor_variant} strongest margin cases",
        turns=anchor_margin_cases,
        conversation_by_id=conversation_by_id,
        variants=variants,
    )
    add_case_detail_section(
        lines,
        title="Lowest average cases",
        turns=lowest_cases,
        conversation_by_id=conversation_by_id,
        variants=variants,
    )
    add_case_detail_section(
        lines,
        title=f"{detail_variant} winning cases",
        turns=detail_win_cases,
        conversation_by_id=conversation_by_id,
        variants=variants,
    )


def add_case_detail_section(
    lines: list[str],
    *,
    title: str,
    turns: list[dict[str, Any]],
    conversation_by_id: dict[str, dict[str, Any]],
    variants: tuple[str, ...],
) -> None:
    lines.extend([f"### {title}", ""])
    for turn in turns:
        scores = variant_scores(turn, variants=variants)
        conv = conversation_by_id.get(turn["message_id"], {})
        target_ids = conv.get("input", {}).get("target_detail_ids", [])
        lines.extend(
            [
                f"#### `{turn['message_id']}` {turn.get('topic', '')}",
                "",
                f"- Persona: `{str(turn['message_id']).split('_', 1)[0]}`; day: `{turn.get('day')}`; probe type: `{turn.get('probe_type')}`",
                f"- User probe: {turn.get('user_message', '')}",
                f"- Target detail ids: `{', '.join(map(str, target_ids)) if target_ids else 'n/a'}`",
                "- Scores: "
                + ", ".join(f"{variant} `{scores[variant]:.1f}`" for variant in variants),
                "",
                "| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |",
                "|---|---:|---|---|---|---|",
            ]
        )
        for variant in variants:
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
            f"- This report: `{run_dir / 'two_person_eval_report.md'}`",
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


def report_variants(
    *,
    llm: dict[str, Any],
    conversation: dict[str, Any],
    run_config: dict[str, Any],
) -> tuple[str, ...]:
    configured = [
        str(item)
        for item in run_config.get("conditions", [])
        if item
    ]
    scored = list((llm.get("summary", {}).get("variants") or {}).keys())
    if configured:
        result = tuple(variant for variant in configured if variant in scored or not scored)
        if result:
            return result
    if scored:
        return tuple(scored)
    for turn in conversation.get("turns", []):
        variants = turn.get("variants")
        if isinstance(variants, dict) and variants:
            return tuple(str(item) for item in variants)
    return DEFAULT_VARIANTS


def condition_interpretation_lines(variants: tuple[str, ...]) -> list[str]:
    descriptions = {
        "M0": "M0 is the ordinary LD-Agent-style long/short memory baseline.",
        "M1": "M1 adds conclusion-level relational memory on top of the M0 base.",
        "M2": "M2 adds event-line summary memory on top of M0 + M1.",
        "M3": "M3 adds detail-level relational anchors on top of M0 + M1 + M2.",
        "Z1": "Z1 is the atomic conclusion-level relational memory condition; it does not compose with M0 or other Z/M layers.",
        "Z2": "Z2 is the atomic event-line summary memory condition; it does not compose with M0 or other Z/M layers.",
        "Z3": "Z3 is the atomic detail-anchor memory condition; it does not compose with M0 or other Z/M layers.",
        "U1": "U1 is M0 plus an atomic conclusion-level relational runtime; it does not inherit U2/U3 or cumulative M layers.",
        "U2": "U2 is M0 plus an atomic event-line summary runtime; it does not inherit U1/M1 conclusion memory or U3/M3 detail memory.",
        "U3": "U3 is M0 plus an atomic detail-anchor runtime; it does not inherit U1/U2 or cumulative M layers.",
    }
    return [f"- {descriptions.get(variant, variant + ' uses the configured memory condition boundary.')}" for variant in variants]


def preferred_variant(
    variants: tuple[str, ...],
    preferred: tuple[str, ...],
    *,
    default: str,
) -> str:
    for variant in preferred:
        if variant in variants:
            return variant
    return default


def prompt_reference_examples(
    conversation: dict[str, Any],
    *,
    variants: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    examples: dict[str, dict[str, Any]] = {}
    for turn in conversation.get("turns", []):
        if not turn.get("input", {}).get("tom_dimensions"):
            continue
        turn_variants = turn.get("variants", {})
        input_payload = turn.get("input", {})
        for condition_id in variants:
            if condition_id in examples:
                continue
            variant = turn_variants.get(condition_id)
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
        if all(condition_id in examples for condition_id in variants):
            break
    return examples


def persona_id(turn: dict[str, Any]) -> str:
    message_id = str(turn.get("source", {}).get("message_id") or turn.get("message_id") or "")
    return message_id.split("_", 1)[0] if "_" in message_id else message_id


def variant_scores(turn: dict[str, Any], *, variants: tuple[str, ...]) -> dict[str, float]:
    return {
        variant: float(turn["variants"].get(variant, {}).get("tom_score", 0.0))
        for variant in variants
    }


def persona_variance_table(*, llm: dict[str, Any], variants: tuple[str, ...]) -> str:
    stats = persona_score_stats(llm=llm, variants=variants)
    lines = [
        "| Condition | Persona count | Persona means | Mean | Variance | Std dev | Range | CV | Norm var | Norm range | M0 var reduction |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in variants:
        item = stats.get(variant, {})
        persona_means = item.get("persona_means", {})
        means_text = "; ".join(
            f"{pid}={float(score):.2f}"
            for pid, score in sorted(persona_means.items())
        )
        lines.append(
            "| {variant} | {count} | {means} | {mean:.2f} | {variance:.2f} | {stddev:.2f} | {range_value:.2f} | {cv:.3f} | {norm_variance:.3f} | {norm_range:.3f} | {m0_reduction:.1%} |".format(
                variant=variant,
                count=int(item.get("persona_count", 0)),
                means=clean_table_text(means_text or "-"),
                mean=float(item.get("mean", 0.0)),
                variance=float(item.get("variance", 0.0)),
                stddev=float(item.get("stddev", 0.0)),
                range_value=float(item.get("range", 0.0)),
                cv=float(item.get("cv", 0.0)),
                norm_variance=float(item.get("norm_variance", 0.0)),
                norm_range=float(item.get("norm_range", 0.0)),
                m0_reduction=float(item.get("m0_variance_reduction", 0.0)),
            )
        )
    lines.append("")
    lines.append(
        "Variance is computed across persona-level average ToM scores within this report "
        "(population variance, not cross-experiment variance). "
        "`Norm var` is variance / 2500, because 2500 is the maximum population variance "
        "on a 0-100 score scale. `M0 var reduction` is positive when the condition is "
        "more even across personas than M0 in the same report."
    )
    return "\n".join(lines)


def persona_score_stats(*, llm: dict[str, Any], variants: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    scores_by_variant_persona: dict[str, dict[str, list[float]]] = {
        variant: defaultdict(list) for variant in variants
    }
    for turn in llm.get("turns", []):
        if not isinstance(turn, dict):
            continue
        pid = str(turn.get("message_id", "")).split("_", 1)[0]
        if not pid:
            continue
        turn_variants = turn.get("variants", {})
        if not isinstance(turn_variants, dict):
            continue
        for variant in variants:
            result = turn_variants.get(variant, {})
            if not isinstance(result, dict):
                continue
            valid = bool(
                result.get(
                    "is_valid_judge_result",
                    result.get("judge_status") == "ok" or "tom_score" in result,
                )
            )
            if not valid:
                continue
            scores_by_variant_persona[variant][pid].append(float(result.get("tom_score", 0.0)))

    stats: dict[str, dict[str, Any]] = {}
    raw_stats: dict[str, dict[str, Any]] = {}
    for variant, persona_scores in scores_by_variant_persona.items():
        persona_means = {
            pid: sum(scores) / len(scores)
            for pid, scores in persona_scores.items()
            if scores
        }
        values = list(persona_means.values())
        mean = sum(values) / len(values) if values else 0.0
        variance = (
            sum((value - mean) ** 2 for value in values) / len(values)
            if values
            else 0.0
        )
        raw_stats[variant] = {
            "persona_count": len(values),
            "persona_means": persona_means,
            "mean": mean,
            "variance": variance,
            "stddev": variance ** 0.5,
            "range": (max(values) - min(values)) if values else 0.0,
        }
    m0_variance = float(raw_stats.get("M0", {}).get("variance", 0.0))
    for variant, item in raw_stats.items():
        mean = float(item.get("mean", 0.0))
        variance = float(item.get("variance", 0.0))
        stddev = float(item.get("stddev", 0.0))
        range_value = float(item.get("range", 0.0))
        item["cv"] = stddev / mean if mean else 0.0
        item["norm_variance"] = min(1.0, max(0.0, variance / 2500.0))
        item["norm_stddev"] = min(1.0, max(0.0, stddev / 50.0))
        item["norm_range"] = min(1.0, max(0.0, range_value / 100.0))
        item["m0_variance_reduction"] = (
            (m0_variance - variance) / m0_variance if m0_variance else 0.0
        )
        stats[variant] = item
    return stats


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
