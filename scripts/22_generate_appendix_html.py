#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.evaluation.generation_prompt_reference import (  # noqa: E402
    build_answer_condition_system_prompt_template,
    build_relational_payload_context_template,
)
from long_memory_test.evaluation.llm_tom_judge import (  # noqa: E402
    FAILURE_TYPES,
    FLAG_NAMES,
    STRICT_SCORING_CONTRACT,
    TOM_DIMENSION_RUBRIC,
    _judge_system_prompt,
)
from long_memory_test.memory.ld_agent_runtime import (  # noqa: E402
    LD_PERSONA_SYSTEM_PROMPT,
    LD_SESSION_SUMMARY_SYSTEM_PROMPT,
)
from long_memory_test.memory.relational_runtime import (  # noqa: E402
    CONDITION_MEMORY_TYPES,
    CONCLUSION_MEMORY_TYPE,
    DETAIL_ANCHOR_MEMORY_TYPE,
    EVENT_SUMMARY_MEMORY_TYPE,
    RELATIONAL_CONDITION_COMPOSITION,
    RELATIONAL_MEMORY_SYSTEM_PROMPT,
    _relational_memory_prompt,
)
from long_memory_test.llm import (  # noqa: E402
    LLMConfigError,
    create_llm_client,
    get_llm_config,
)


TODAY = datetime.now().strftime("%Y%m%d")
DEFAULT_EXPERIMENT_ID = "aaai_appendix"
DEFAULT_DATA_DIR = (
    REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
)
DEFAULT_CANDIDATE_DATA_DIR = (
    REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo50_candidate"
)
DEFAULT_RAW_POOL_DIR = (
    REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_100"
)
DEFAULT_RUN_DIRS = [
    (
        "M-series pilot",
        REPO_ROOT
        / "long_memory_experiment/outputs/"
        / "run_20260704_two_person_m0_m3_current_event_lock_generation",
    ),
    (
        "Z-series pilot",
        REPO_ROOT
        / "long_memory_experiment/outputs/"
        / "run_20260706_two_person_m0_z1_z2_z3_atomic_generation_retry",
    ),
    (
        "U-series pilot",
        REPO_ROOT
        / "long_memory_experiment/outputs/"
        / "run_20260707_two_person_m0_u1_u2_u3_m0_augmented_atomic",
    ),
]

FAILURE_TYPE_EN = {
    "memory_absence": "The answer fails to connect to prior shared context when it should.",
    "memory_misuse": "The answer uses incorrect, outdated, irrelevant, or unreadable memory.",
    "memory_overuse": "The answer mechanically piles up details to appear familiar.",
    "fabrication": "The answer invents information that the user did not provide.",
    "alienation": "The answer sounds like customer service, becomes alienating, over-roleplays, or is overly intimate.",
    "instruction_only_success": "The answer only follows the explicit current instruction without relying on long-term memory.",
}

SCORING_POSTURE_EN = {
    "从 0 分开始加证据，不要从满分开始找缺点。": "Start from 0 and add points only when there is evidence; do not start from full marks and subtract.",
    "2 分是强证据满分，不是方向正确分；方向正确但证据不足通常只能给 1 分。": "A score of 2 requires strong evidence; a directionally correct but weakly supported answer usually receives at most 1.",
    "1 分代表部分识别但未充分转化为回应策略；2 分只给明确、有证据、服务当前判断的回答。": "A score of 1 means partial recognition without sufficient conversion into a response strategy; 2 is reserved for clear, evidenced responses that serve the current judgment.",
    "如果回答可以几乎原样复制给另一个有相同表面问题的用户，相关维度最高 1 分。": "If the answer could be copied almost unchanged to another user with the same surface question, the relevant dimension is capped at 1.",
    "如果 evidence_quote 不能直接支持该维度 reason，相关维度最高 1 分。": "If the evidence_quote does not directly support the dimension reason, the relevant dimension is capped at 1.",
}

SCORE_CAPS_EN = {
    "没有 assistant_answer 原文证据的维度必须给 0 分。": "A dimension with no evidence from the assistant_answer must receive 0.",
    "只复述用户问题，没有新增心理推断，hidden_intent_recognition 最高 1 分。": "If the answer only repeats the user question without a new psychological inference, hidden_intent_recognition is capped at 1.",
    "只说焦虑、累、担心等泛化情绪词，emotional_state_recognition 最高 1 分。": "If the answer only uses generic emotion words such as anxious, tired, or worried, emotional_state_recognition is capped at 1.",
    "没有调用 case.allowed_context.recent_dialogue 或 case.memory_condition.available_memory_excerpt 中的具体前文或共同处理方式，shared_context_invocation 最高 1 分。": "Without specific prior context or shared handling strategy from case.allowed_context.recent_dialogue or case.memory_condition.available_memory_excerpt, shared_context_invocation is capped at 1.",
    "没有明显陌生化错误只能得到 alienation_error_rate 1 分；必须有关系连续性证据才可给 2 分。": "The absence of obvious alienation errors only earns 1 for alienation_error_rate; 2 requires evidence of relational continuity.",
    "只使用当前用户问题里的明显词语，而没有调用可验证背景细节，natural_detail_use 最高 1 分。": "If the answer only uses obvious terms from the current user question without verifiable background details, natural_detail_use is capped at 1.",
    "没有明确区分已知/推测/不可补空白，memory_misuse 最高 1 分。": "Without a clear distinction among known facts, inference, and unfillable gaps, memory_misuse is capped at 1.",
    "出现编造事实、要求用户重讲已给背景、客服化称呼或机械背诵，相关维度最高 0 分，并标记对应 flag。": "If the answer fabricates facts, asks the user to repeat known context, uses customer-service-like address, or mechanically recites memory, the relevant dimensions are capped at 0 and the corresponding flag must be marked.",
}

RUBRIC_EN = {
    "hidden_intent_recognition": {
        "question": "Does the answer recognize the real need behind the user's surface wording?",
        "score_0": "Only answers the literal question, or misses what the user really wants to confirm.",
        "score_1": "Partially recognizes the subtext, but does not turn it into a response strategy.",
        "score_2": "Clearly captures the subtext and responds around the user's real need.",
    },
    "emotional_state_recognition": {
        "question": "Does the answer recognize states such as fatigue, disappointment, self-doubt, unease, or fear of being forgotten?",
        "score_0": "Treats the user's state as an ordinary consultation, or offers only generic comfort.",
        "score_1": "Mentions emotion, but weakly connects it to the advice.",
        "score_2": "Recognizes the specific state and adjusts the intensity of advice accordingly.",
    },
    "shared_context_invocation": {
        "question": "Does the answer continue the previously formed handling approach instead of starting from zero each time?",
        "score_0": "Asks the user to repeat history, or treats an ongoing event as if it appeared for the first time.",
        "score_1": "Vaguely says 'before' or 'we discussed', but lacks a verifiable connection.",
        "score_2": "Naturally connects to prior clues or a shared handling method and continues the current judgment.",
    },
    "alienation_error_rate": {
        "question": "Does the answer avoid customer-service tone, roleplay, excessive intimacy, or asking the user to restate history?",
        "score_0": "Contains obvious risk wording, asks the user to repeat known background, or breaks relational positioning.",
        "score_1": "Has no obvious risk, but remains neutral-assistant-like and lacks evidence of relational continuity.",
        "score_2": "Shows no alienation risk and maintains stable relational positioning through concrete wording or handling.",
    },
    "natural_detail_use": {
        "question": "Do key details serve psychological understanding rather than mechanical log recitation?",
        "score_0": "Piles up details, fabricates details, or does not use details to understand the user's state.",
        "score_1": "Uses a few details, but they weakly support the judgment.",
        "score_2": "Uses only necessary details and makes them serve emotion, boundary, or next-step judgment.",
    },
    "memory_misuse": {
        "question": "Does the answer avoid using outdated, irrelevant, nonexistent, or inappropriate memory?",
        "score_0": "Incorrectly uses outdated, irrelevant, nonexistent, or unreadable memory, or fabricates user information.",
        "score_1": "Slightly over-repeats memory, gives weak boundary clarification, or uses memory weakly for the current judgment.",
        "score_2": "Uses memory with restraint, knows when not to use it, and distinguishes known facts, inferences, and unfillable gaps.",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an AAAI appendix framework HTML page from selected "
            "trajectory data, experiment runs, and change notes."
        )
    )
    parser.add_argument(
        "--experiment-id",
        default=DEFAULT_EXPERIMENT_ID,
        help=(
            "Appendix id. Defaults to the fixed working appendix id "
            "'aaai_appendix', so repeated runs overwrite the same files. "
            "Use a custom id only when an explicit historical snapshot is needed."
        ),
    )
    parser.add_argument(
        "--title",
        default="AAAI Appendix Framework: Relational Memory Experiments",
    )
    parser.add_argument("--target-persona-count", type=int, default=50)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--candidate-data-dir", type=Path, default=DEFAULT_CANDIDATE_DATA_DIR
    )
    parser.add_argument("--raw-pool-dir", type=Path, default=DEFAULT_RAW_POOL_DIR)
    parser.add_argument(
        "--run-dir",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help=(
            "Experiment run to summarize. May be repeated. If omitted, the "
            "current M/Z/U pilot runs are used."
        ),
    )
    parser.add_argument(
        "--example-run-dir",
        type=Path,
        default=DEFAULT_RUN_DIRS[0][1],
        help="Run directory used for the M0-M3 memory condition example.",
    )
    parser.add_argument(
        "--example-message-id",
        default="",
        help="Optional message/probe id to use for the memory condition example.",
    )
    parser.add_argument(
        "--change-note",
        action="append",
        default=[],
        help="Experiment-specific modification note to show in the appendix context.",
    )
    parser.add_argument("--examples-per-bucket", type=int, default=2)
    parser.add_argument(
        "--translate-dynamic",
        action="store_true",
        help=(
            "Translate selected data-driven examples into English and cache the "
            "results. Static appendix descriptions are always bilingual."
        ),
    )
    parser.add_argument(
        "--translation-provider",
        default="deepseek",
        help="LLM provider for --translate-dynamic. Defaults to deepseek.",
    )
    parser.add_argument(
        "--translation-cache",
        type=Path,
        default=None,
        help="JSON cache for dynamic Chinese-to-English translations.",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir or (
        REPO_ROOT / "docs/appendix" / args.experiment_id
    )
    output = args.output or (output_dir / f"{args.experiment_id}.html")
    output_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = _parse_run_dirs(args.run_dir)
    data_summary = _trajectory_summary(args.data_dir)
    candidate_summary = _trajectory_summary(args.candidate_data_dir)
    raw_pool_summary = _raw_pool_summary(args.raw_pool_dir)
    run_summaries = [
        _run_summary(label=label, run_dir=run_dir) for label, run_dir in run_dirs
    ]
    example = _condition_example(
        run_dir=args.example_run_dir,
        message_id=args.example_message_id.strip() or None,
    )
    probes = _probe_records(args.data_dir)
    prompt_items = _prompt_items(example)
    construction_details = _construction_details(
        _construction_detail_data_dir(args.data_dir, args.candidate_data_dir)
    )
    translation_cache = args.translation_cache or (
        output_dir / f"{args.experiment_id}.translation_cache.json"
    )
    translator = DynamicTranslator(
        enabled=bool(args.translate_dynamic),
        provider=args.translation_provider,
        cache_path=translation_cache,
    )

    html_text = _render_page(
        title=args.title,
        experiment_id=args.experiment_id,
        target_persona_count=args.target_persona_count,
        data_dir=args.data_dir,
        candidate_data_dir=args.candidate_data_dir,
        raw_pool_dir=args.raw_pool_dir,
        data_summary=data_summary,
        candidate_summary=candidate_summary,
        raw_pool_summary=raw_pool_summary,
        run_summaries=run_summaries,
        example=example,
        probes=probes,
        examples_per_bucket=max(1, args.examples_per_bucket),
        change_notes=args.change_note,
        prompt_items=prompt_items,
        construction_details=construction_details,
        translator=translator,
    )
    if translator.translate_missing():
        html_text = _render_page(
            title=args.title,
            experiment_id=args.experiment_id,
            target_persona_count=args.target_persona_count,
            data_dir=args.data_dir,
            candidate_data_dir=args.candidate_data_dir,
            raw_pool_dir=args.raw_pool_dir,
            data_summary=data_summary,
            candidate_summary=candidate_summary,
            raw_pool_summary=raw_pool_summary,
            run_summaries=run_summaries,
            example=example,
            probes=probes,
            examples_per_bucket=max(1, args.examples_per_bucket),
            change_notes=args.change_note,
            prompt_items=prompt_items,
            construction_details=construction_details,
            translator=translator,
        )
    output.write_text(html_text, encoding="utf-8")

    manifest = {
        "schema_version": "aaai_appendix_framework_manifest_v0.1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "experiment_id": args.experiment_id,
        "appendix_id": args.experiment_id,
        "title": args.title,
        "target_persona_count": args.target_persona_count,
        "output_html": _display_path(output),
        "data_dir": _display_path(args.data_dir),
        "candidate_data_dir": _display_path(args.candidate_data_dir),
        "construction_detail_data_dir": _display_path(construction_details.get("path")),
        "raw_pool_dir": _display_path(args.raw_pool_dir),
        "run_dirs": [
            {"label": label, "path": _display_path(path)} for label, path in run_dirs
        ],
        "example_run_dir": _display_path(args.example_run_dir),
        "example_message_id": example.get("message_id"),
        "change_notes": list(args.change_note),
        "translation": {
            "dynamic_translation_enabled": bool(args.translate_dynamic),
            "provider": args.translation_provider if args.translate_dynamic else None,
            "cache_path": _display_path(translation_cache),
            "cached_item_count": len(translator.cache),
        },
        "source_files": [
            "scripts/22_generate_appendix_html.py",
            "src/long_memory_test/evaluation/generation_prompt_reference.py",
            "src/long_memory_test/evaluation/llm_tom_judge.py",
            "src/long_memory_test/memory/ld_agent_runtime.py",
            "src/long_memory_test/memory/relational_runtime.py",
        ],
    }
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output}")
    print(f"Wrote {manifest_path}")
    return 0


class DynamicTranslator:
    def __init__(
        self,
        *,
        enabled: bool,
        provider: str,
        cache_path: Path,
        max_source_chars: int = 900,
    ) -> None:
        self.enabled = enabled
        self.provider = provider
        self.cache_path = cache_path
        self.max_source_chars = max_source_chars
        self.cache = self._load_cache()
        self.missing: set[str] = set()

    def en(self, text: Any) -> str:
        source = _normalize_translation_source(text, self.max_source_chars)
        if not self.enabled or not source:
            return ""
        cached = self.cache.get(source)
        if isinstance(cached, str) and cached.strip():
            return cached.strip()
        self.missing.add(source)
        return ""

    def translate_missing(self) -> bool:
        if not self.enabled or not self.missing:
            return False
        sources = sorted(self.missing)
        self.missing.clear()
        try:
            llm_config = get_llm_config(provider=self.provider)
            client, llm_config = create_llm_client(llm_config)
        except LLMConfigError as exc:
            print(f"Translation skipped: {exc}", file=sys.stderr)
            return False

        changed = False
        for start in range(0, len(sources), 8):
            batch = sources[start : start + 8]
            prompt = {
                "instruction": (
                    "Translate each Chinese source string into concise, natural "
                    "academic English. Preserve IDs, condition names, probe names, "
                    "and technical terms such as persona, event line, interaction "
                    "unit, probe, tau, M0, M1, M2, M3, Z1, U1. Return only JSON: "
                    "{\"translations\": [{\"source\": \"...\", \"english\": \"...\"}]}"
                ),
                "sources": batch,
            }
            try:
                completion = client.with_options(timeout=120, max_retries=0).chat.completions.create(
                    model=llm_config.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a precise Chinese-to-English academic translator.",
                        },
                        {
                            "role": "user",
                            "content": json.dumps(prompt, ensure_ascii=False),
                        },
                    ],
                    temperature=0,
                    max_tokens=20000,
                    response_format={"type": "json_object"},
                )
                raw = completion.choices[0].message.content or "{}"
                parsed = json.loads(raw)
            except Exception as exc:  # pragma: no cover - network/API failures vary.
                print(f"Translation batch skipped: {exc}", file=sys.stderr)
                continue
            raw_translations = parsed.get("translations", [])
            if isinstance(raw_translations, dict):
                raw_translations = [
                    {"source": source, "english": english}
                    for source, english in raw_translations.items()
                ]
            for item in raw_translations:
                if not isinstance(item, dict):
                    continue
                source = _normalize_translation_source(
                    item.get("source"), self.max_source_chars
                )
                english = str(item.get("english") or "").strip()
                if source and english:
                    self.cache[source] = english
                    changed = True
        if changed:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self.cache, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return changed

    def _load_cache(self) -> dict[str, str]:
        if not self.cache_path.exists():
            return {}
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return {
            str(key): str(value)
            for key, value in payload.items()
            if isinstance(value, str)
        }


def _parse_run_dirs(values: list[str]) -> list[tuple[str, Path]]:
    if not values:
        return [(label, path) for label, path in DEFAULT_RUN_DIRS if path.exists()]
    parsed: list[tuple[str, Path]] = []
    for raw in values:
        if "=" not in raw:
            raise SystemExit(f"--run-dir must be LABEL=PATH, got: {raw}")
        label, path_text = raw.split("=", 1)
        parsed.append((label.strip() or Path(path_text).name, Path(path_text)))
    return parsed


def _trajectory_summary(data_dir: Path) -> dict[str, Any]:
    sampled = _load_json(data_dir / "sampled_personas.json")
    tau = _load_json(data_dir / "tau_contract.json")
    timeline = _load_json(data_dir / "timeline.json")
    probe_plan = _load_json(data_dir / "probe_plan.json")
    daily = _load_json(data_dir / "daily_interaction_units.json")
    tau_summary = dict(tau.get("summary", {})) if isinstance(tau, dict) else {}
    timeline_summary = (
        dict(timeline.get("summary", {})) if isinstance(timeline, dict) else {}
    )
    probe_summary = (
        dict(probe_plan.get("summary", {})) if isinstance(probe_plan, dict) else {}
    )
    daily_summary = dict(daily.get("summary", {})) if isinstance(daily, dict) else {}
    return {
        "path": data_dir,
        "exists": data_dir.exists(),
        "persona_count": (
            tau_summary.get("persona_count")
            or timeline_summary.get("persona_count")
            or probe_summary.get("persona_count")
            or daily_summary.get("persona_count")
            or _persona_count_from_sampled(sampled)
        ),
        "theme_count": tau_summary.get("theme_count"),
        "event_line_count": tau_summary.get("event_line_count")
        or timeline_summary.get("event_line_count"),
        "interaction_unit_count": tau_summary.get("interaction_unit_count")
        or daily_summary.get("interaction_unit_count")
        or timeline_summary.get("active_session_total"),
        "targeted_probe_count": tau_summary.get("targeted_probe_count")
        or probe_summary.get("probe_count")
        or timeline_summary.get("probe_count_total"),
        "active_day_count": tau_summary.get("active_day_count")
        or timeline_summary.get("active_day_total"),
        "calendar_days": _calendar_day_count(timeline),
        "event_stage_counts": timeline_summary.get("event_stage_counts", {}),
        "paper_probe_type_counts": tau_summary.get("paper_probe_type_counts")
        or probe_summary.get("paper_probe_type_counts", {}),
        "primary_dimension_counts": tau_summary.get("primary_dimension_counts")
        or probe_summary.get("primary_dimension_counts", {}),
        "validation": (
            tau.get("validation", {}).get("status")
            or timeline.get("validation", {}).get("status")
            or probe_plan.get("validation", {}).get("status")
        ),
    }


def _construction_detail_data_dir(data_dir: Path, candidate_data_dir: Path) -> Path:
    try:
        if data_dir.resolve() == DEFAULT_DATA_DIR.resolve() and candidate_data_dir.exists():
            return candidate_data_dir
    except Exception:
        pass
    return data_dir


def _construction_details(data_dir: Path) -> dict[str, Any]:
    sampled = _load_json(data_dir / "sampled_personas.json")
    accepted = _load_json(data_dir / "accepted_persona_event_sets.json")
    event_lines = _load_json(data_dir / "event_lines_batch.json")
    daily = _load_json(data_dir / "daily_interaction_units.json")
    probe_plan = _load_json(data_dir / "probe_plan.json")
    tau = _load_json(data_dir / "tau_contract.json")

    personas = sampled.get("personas", []) if isinstance(sampled, dict) else []
    zh_personas = (
        sampled.get("locale_views", {}).get("zh", {}).get("personas", [])
        if isinstance(sampled, dict)
        else []
    )
    zh_by_id = {
        item.get("persona_id"): item
        for item in zh_personas
        if isinstance(item, dict) and item.get("persona_id")
    }
    persona_inventory = []
    for persona in personas:
        if not isinstance(persona, dict):
            continue
        zh_persona = zh_by_id.get(persona.get("persona_id"), {})
        persona_inventory.append(
            {
                "persona_id": persona.get("persona_id"),
                "archetype": persona.get("source_archetype"),
                "label": persona.get("source_archetype_label"),
                "label_zh": zh_persona.get("source_archetype_label"),
                "occupation": persona.get("occupation"),
                "occupation_zh": zh_persona.get("occupation"),
                "life_stage": persona.get("life_stage"),
                "life_stage_zh": zh_persona.get("life_stage"),
                "domains": persona.get("primary_life_domains", []),
                "domains_zh": zh_persona.get("primary_life_domains", []),
                "communication_style": persona.get("communication_style", []),
                "communication_style_zh": zh_persona.get("communication_style", []),
                "memory_traits": persona.get("memory_relevant_traits", []),
                "memory_traits_zh": zh_persona.get("memory_relevant_traits", []),
            }
        )

    accepted_sets = (
        accepted.get("accepted_persona_event_sets", [])
        if isinstance(accepted, dict)
        else []
    )
    domain_counts: Counter[str] = Counter()
    category_by_id: dict[str, dict[str, Any]] = {}
    accepted_rows = []
    for item in accepted_sets:
        if not isinstance(item, dict):
            continue
        for domain, count in (item.get("domain_counts", {}) or {}).items():
            domain_counts[str(domain)] += int(count or 0)
        for event in item.get("accepted_events", []) or []:
            if not isinstance(event, dict):
                continue
            category_id = str(event.get("event_category_id") or "")
            if category_id and category_id not in category_by_id:
                category_by_id[category_id] = event
        accepted_rows.append(
            {
                "persona_id": item.get("persona_id"),
                "accepted_event_count": item.get("accepted_event_count"),
                "accepted_event_ids": item.get("accepted_event_ids", []),
                "domain_counts": item.get("domain_counts", {}),
            }
        )

    line_rows = []
    sample_event_line = {}
    event_line_personas = event_lines.get("personas", []) if isinstance(event_lines, dict) else []
    for item in event_line_personas:
        if not isinstance(item, dict):
            continue
        lines = item.get("event_lines", []) or []
        line_rows.append(
            {
                "persona_id": item.get("persona_ref", {}).get("persona_id")
                or (lines[0].get("persona_id") if lines else None),
                "event_line_count": item.get("event_line_count") or len(lines),
                "event_line_ids": [
                    line.get("event_line_id") for line in lines if isinstance(line, dict)
                ],
            }
        )
        if not sample_event_line and lines:
            sample_event_line = lines[0]

    daily_personas = daily.get("personas", []) if isinstance(daily, dict) else []
    sample_unit = {}
    unit_rows = []
    for item in daily_personas:
        if not isinstance(item, dict):
            continue
        unit_rows.append(
            {
                "persona_id": item.get("persona_id"),
                "interaction_unit_count": item.get("interaction_unit_count"),
                "active_day_count": item.get("active_day_count"),
            }
        )
        for day in item.get("days", []) or []:
            if not isinstance(day, dict):
                continue
            for unit in day.get("interaction_units", []) or []:
                if not isinstance(unit, dict):
                    continue
                if unit.get("probe_links"):
                    sample_unit = unit
                    break
            if sample_unit:
                break
        if sample_unit:
            break

    if sample_unit:
        sample_line_id = sample_unit.get("event_line_id")
        for item in event_line_personas:
            for line in item.get("event_lines", []) or []:
                if isinstance(line, dict) and line.get("event_line_id") == sample_line_id:
                    sample_event_line = line
                    break
            if sample_event_line.get("event_line_id") == sample_line_id:
                break

    sample_probe = {}
    probe_questions = (
        probe_plan.get("probe_questions", []) if isinstance(probe_plan, dict) else []
    )
    probe_links = sample_unit.get("probe_links", []) if isinstance(sample_unit, dict) else []
    probe_ids = {
        link.get("probe_id")
        for link in probe_links
        if isinstance(link, dict) and link.get("probe_id")
    }
    for probe in probe_questions:
        if not isinstance(probe, dict):
            continue
        if probe.get("probe_id") in probe_ids or (
            sample_unit
            and probe.get("insert_after_message_id")
            == sample_unit.get("scripted_opening", {}).get("message_id")
        ):
            sample_probe = probe
            break
    if not sample_probe and probe_questions:
        sample_probe = probe_questions[0]

    summary = tau.get("summary", {}) if isinstance(tau, dict) else {}
    return {
        "path": data_dir,
        "summary": summary,
        "persona_inventory": persona_inventory,
        "accepted_rows": accepted_rows,
        "domain_counts": dict(domain_counts),
        "categories": list(sorted(category_by_id.values(), key=lambda x: x.get("event_category_id", ""))),
        "event_line_rows": line_rows,
        "interaction_unit_rows": unit_rows,
        "sample_event_line": sample_event_line,
        "sample_unit": sample_unit,
        "sample_probe": sample_probe,
    }


def _raw_pool_summary(raw_pool_dir: Path) -> dict[str, Any]:
    sampled = _load_json(raw_pool_dir / "sampled_personas.json")
    return {
        "path": raw_pool_dir,
        "exists": raw_pool_dir.exists(),
        "persona_count": _persona_count_from_sampled(sampled),
        "has_tau_contract": (raw_pool_dir / "tau_contract.json").exists(),
    }


def _run_summary(*, label: str, run_dir: Path) -> dict[str, Any]:
    conversation = _load_json(run_dir / "conversation_log_two_person_eval.json")
    llm = _load_json(run_dir / "llm_judge_scores_two_person.json")
    automatic = _load_json(run_dir / "automatic_scores_two_person.json")
    turns = conversation.get("turns", []) if isinstance(conversation, dict) else []
    probe_turns = [
        turn
        for turn in turns
        if isinstance(turn, dict) and turn.get("input", {}).get("tom_dimensions")
    ]
    persona_ids = sorted({_persona_id(turn) for turn in turns if _persona_id(turn)})
    summary = llm.get("summary", {}) if isinstance(llm, dict) else {}
    variants = summary.get("variants") if isinstance(summary, dict) else {}
    if not variants and turns:
        first_variants = turns[0].get("variants", {}) if isinstance(turns[0], dict) else {}
        variants = {
            key: {"turn_count": len(probe_turns)}
            for key in sorted(first_variants)
        }
    return {
        "label": label,
        "run_dir": run_dir,
        "exists": run_dir.exists(),
        "persona_ids": persona_ids,
        "persona_count": len(persona_ids),
        "turn_count": len(turns),
        "probe_count": len(probe_turns),
        "variant_summaries": variants or {},
        "dimension_averages": summary.get("dimension_averages", {}),
        "persona_variance": summary.get("persona_variance", {}),
        "lowest_scoring_examples": summary.get("lowest_scoring_examples", []),
        "automatic_summary": automatic.get("summary", {}),
    }


def _condition_example(*, run_dir: Path, message_id: str | None) -> dict[str, Any]:
    conversation = _load_json(run_dir / "conversation_log_two_person_eval.json")
    turns = conversation.get("turns", []) if isinstance(conversation, dict) else []
    selected = None
    if message_id:
        for turn in turns:
            source_id = str(turn.get("source", {}).get("message_id") or "")
            input_id = str(turn.get("input", {}).get("message_id") or "")
            if message_id in {source_id, input_id}:
                selected = turn
                break
    if selected is None:
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            variants = turn.get("variants", {})
            if turn.get("input", {}).get("tom_dimensions") and all(
                key in variants for key in ("M0", "M1", "M2", "M3")
            ):
                selected = turn
                break
    if selected is None and turns:
        selected = turns[0]
    if not selected:
        return {"run_dir": run_dir, "rows": []}

    variants = selected.get("variants", {})
    preferred = [key for key in ("M0", "M1", "M2", "M3") if key in variants]
    if not preferred:
        preferred = sorted(variants)
    rows = []
    for condition in preferred:
        variant = variants.get(condition, {})
        rows.append(
            {
                "condition": condition,
                "memory_condition": variant.get("memory_condition") or condition,
                "memory_excerpt": _memory_excerpt(variant, limit=1100),
                "answer_excerpt": _truncate(
                    str(variant.get("assistant_answer") or ""), 700
                ),
            }
        )
    source = selected.get("source", {})
    message = selected.get("input", {})
    return {
        "run_dir": run_dir,
        "message_id": source.get("message_id") or message.get("message_id"),
        "persona_id": message.get("persona_id") or source.get("tau", {}).get("persona_id"),
        "day": message.get("day") or source.get("tau", {}).get("day"),
        "event_line_id": message.get("event_line_id")
        or source.get("tau", {}).get("event_line_id"),
        "topic": message.get("topic"),
        "user_message": message.get("user_message"),
        "probe_type": message.get("probe_type"),
        "paper_probe_id": message.get("paper_probe_id"),
        "primary_dimension_id": message.get("primary_dimension_id"),
        "evaluation_dimension_ids": message.get("evaluation_dimension_ids", []),
        "rows": rows,
        "input": message,
    }


def _probe_records(data_dir: Path) -> list[dict[str, Any]]:
    tau = _load_json(data_dir / "tau_contract.json")
    probes = tau.get("P") if isinstance(tau, dict) else None
    if isinstance(probes, list):
        return [probe for probe in probes if isinstance(probe, dict)]
    probe_plan = _load_json(data_dir / "probe_plan.json")
    probes = probe_plan.get("probe_questions") if isinstance(probe_plan, dict) else None
    return [probe for probe in probes or [] if isinstance(probe, dict)]


def _prompt_items(example: dict[str, Any]) -> list[dict[str, str]]:
    sample_message = dict(example.get("input", {})) if isinstance(example, dict) else {}
    if not sample_message:
        sample_message = {
            "message_id": "<MESSAGE_ID>",
            "day": "<DAY>",
            "topic": "<TOPIC>",
            "user_message": "<CURRENT_USER_MESSAGE>",
            "tau": {"event_line_id": "<EVENT_LINE_ID>"},
        }
    sample_answer = ""
    rows = example.get("rows", []) if isinstance(example, dict) else []
    for row in rows:
        if row.get("condition") == "M3":
            sample_answer = row.get("answer_excerpt", "")
            break
    if not sample_answer:
        sample_answer = "<CURRENT_ASSISTANT_ANSWER>"

    items = [
        {
            "title": "Agent response prompt template: M3",
            "source": "src/long_memory_test/evaluation/generation_prompt_reference.py",
            "text": build_answer_condition_system_prompt_template(condition_id="M3"),
        },
        {
            "title": "Memory reading payload template: M3",
            "source": "src/long_memory_test/evaluation/generation_prompt_reference.py",
            "text": build_relational_payload_context_template(condition_id="M3"),
        },
        {
            "title": "Memory reading payload template: Z1 independent",
            "source": "src/long_memory_test/evaluation/generation_prompt_reference.py",
            "text": build_relational_payload_context_template(condition_id="Z1"),
        },
        {
            "title": "M0 session memory writing prompt",
            "source": "src/long_memory_test/memory/ld_agent_runtime.py",
            "text": LD_SESSION_SUMMARY_SYSTEM_PROMPT,
        },
        {
            "title": "M0 persona memory writing prompt",
            "source": "src/long_memory_test/memory/ld_agent_runtime.py",
            "text": LD_PERSONA_SYSTEM_PROMPT,
        },
        {
            "title": "Relational memory writer system prompt",
            "source": "src/long_memory_test/memory/relational_runtime.py",
            "text": RELATIONAL_MEMORY_SYSTEM_PROMPT,
        },
        {
            "title": "Relational writer sample: M1 relationship conclusion",
            "source": "src/long_memory_test/memory/relational_runtime.py::_relational_memory_prompt",
            "text": _relational_memory_prompt(
                condition_id="M1",
                memory_type=CONCLUSION_MEMORY_TYPE,
                message=sample_message,
                assistant_answer=sample_answer,
                existing_summary="<EXISTING_EVENT_LINE_MEMORY_SUMMARY>",
            ),
        },
        {
            "title": "Relational writer sample: M2 event-line summary",
            "source": "src/long_memory_test/memory/relational_runtime.py::_relational_memory_prompt",
            "text": _relational_memory_prompt(
                condition_id="M2",
                memory_type=EVENT_SUMMARY_MEMORY_TYPE,
                message=sample_message,
                assistant_answer=sample_answer,
                existing_summary="<EXISTING_EVENT_LINE_MEMORY_SUMMARY>",
            ),
        },
        {
            "title": "Relational writer sample: M3 detail anchor",
            "source": "src/long_memory_test/memory/relational_runtime.py::_relational_memory_prompt",
            "text": _relational_memory_prompt(
                condition_id="M3",
                memory_type=DETAIL_ANCHOR_MEMORY_TYPE,
                message=sample_message,
                assistant_answer=sample_answer,
                existing_summary="<EXISTING_EVENT_LINE_MEMORY_SUMMARY>",
            ),
        },
        {
            "title": "Evaluator prompt",
            "source": "src/long_memory_test/evaluation/llm_tom_judge.py::_judge_system_prompt",
            "text": _judge_system_prompt(),
        },
    ]
    return items


def _render_page(
    *,
    title: str,
    experiment_id: str,
    target_persona_count: int,
    data_dir: Path,
    candidate_data_dir: Path,
    raw_pool_dir: Path,
    data_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
    raw_pool_summary: dict[str, Any],
    run_summaries: list[dict[str, Any]],
    example: dict[str, Any],
    probes: list[dict[str, Any]],
    examples_per_bucket: int,
    change_notes: list[str],
    prompt_items: list[dict[str, str]],
    construction_details: dict[str, Any],
    translator: DynamicTranslator,
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = "\n".join(
        [
            _hero(
                title=title,
                experiment_id=experiment_id,
                generated_at=generated_at,
                target_persona_count=target_persona_count,
                data_summary=data_summary,
                candidate_summary=candidate_summary,
                raw_pool_summary=raw_pool_summary,
                run_summaries=run_summaries,
            ),
            _section_context(
                target_persona_count=target_persona_count,
                data_dir=data_dir,
                candidate_data_dir=candidate_data_dir,
                raw_pool_dir=raw_pool_dir,
                change_notes=change_notes,
                run_summaries=run_summaries,
                translator=translator,
            ),
            _section_memory_conditions(example, translator=translator),
            _section_trajectory(
                target_persona_count=target_persona_count,
                data_summary=data_summary,
                candidate_summary=candidate_summary,
                raw_pool_summary=raw_pool_summary,
                construction_details=construction_details,
                translator=translator,
            ),
            _section_probe_examples(
                probes,
                examples_per_bucket=examples_per_bucket,
                translator=translator,
            ),
            _section_rubric(probes),
            _section_prompts(prompt_items),
            _section_extra_results(run_summaries),
            _section_sources(
                data_dir=data_dir,
                candidate_data_dir=candidate_data_dir,
                raw_pool_dir=raw_pool_dir,
                run_summaries=run_summaries,
            ),
        ]
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)}</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #667085;
      --line: #d7dee9;
      --panel: #ffffff;
      --band: #f4f6f9;
      --soft: #f9fbfd;
      --accent: #0f766e;
      --warn: #9a3412;
      --bad: #b42318;
      --blue: #3347b8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--band);
      color: var(--ink);
      font: 14px/1.62 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 28px 18px 58px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 10px; font-size: 22px; letter-spacing: 0; }}
    h3 {{ margin: 18px 0 8px; font-size: 16px; letter-spacing: 0; }}
    p {{ margin: 0 0 8px; }}
    code {{
      padding: 1px 5px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #f8fafc;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }}
    pre {{
      margin: 8px 0 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0f172a;
      color: #e5e7eb;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      margin: 10px 0 16px;
      background: var(--panel);
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 9px;
      vertical-align: top;
      word-break: break-word;
    }}
    th {{ background: #f8fafc; text-align: left; color: #344054; }}
    section, .hero {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 18px;
      margin-top: 14px;
    }}
    .hero {{ margin-top: 0; }}
    .subtitle {{ color: var(--muted); max-width: 1000px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: var(--soft);
    }}
    .metric b {{ display: block; font-size: 23px; line-height: 1.2; }}
    .metric span {{ color: var(--muted); font-size: 12px; }}
    .grid-2 {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .callout {{
      border-left: 4px solid var(--accent);
      background: #ecfdf5;
      padding: 10px 12px;
      margin: 10px 0;
    }}
    .todo {{
      border-left-color: var(--warn);
      background: #fff7ed;
    }}
    .tag {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 1px 8px;
      margin: 0 5px 5px 0;
      background: #f8fafc;
      color: #344054;
      font-size: 12px;
    }}
    details {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      background: var(--soft);
      margin: 8px 0;
    }}
    summary {{ cursor: pointer; font-weight: 650; }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 12px; }}
    .bi {{ display: grid; gap: 3px; }}
    .bi .zh {{ color: var(--ink); }}
    .bi .en {{ color: var(--muted); font-size: 12px; }}
    .en-block {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      border-left: 3px solid var(--line);
      padding-left: 8px;
    }}
    ul {{ margin: 8px 0 12px 20px; padding: 0; }}
    @media (max-width: 900px) {{
      .metrics, .grid-2 {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def _hero(
    *,
    title: str,
    experiment_id: str,
    generated_at: str,
    target_persona_count: int,
    data_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
    raw_pool_summary: dict[str, Any],
    run_summaries: list[dict[str, Any]],
) -> str:
    evaluated_personas = max(
        [int(item.get("persona_count") or 0) for item in run_summaries] or [0]
    )
    return f"""
<div class="hero">
  <h1>{_esc(title)}</h1>
  <p class="subtitle">{_bi_text("本页是可复用的 AAAI 附录生成框架：当前用 pilot/candidate 数据填充，最终 50 人完整实验完成后，用同一脚本替换数据源和 run 目录即可刷新。", "This page is a reusable AAAI appendix-generation framework. It is currently populated with pilot/candidate data; after the final 50-person experiment is complete, the same script can refresh the page by replacing the data source and run directories.")}</p>
  <p class="small muted">experiment_id: <code>{_esc(experiment_id)}</code> · generated_at: {_esc(generated_at)}</p>
  <div class="metrics">
    {_metric("Target personas", target_persona_count, "final plan")}
    {_metric("Evaluated personas", evaluated_personas, "current runs")}
    {_metric("Canonical data", data_summary.get("persona_count", "-"), "personas")}
    {_metric("Candidate pool", candidate_summary.get("persona_count", "-"), "personas")}
    {_metric("Raw pool", raw_pool_summary.get("persona_count", "-"), "personas")}
    {_metric("Run groups", len(run_summaries), "summarized")}
  </div>
</div>
"""


def _section_context(
    *,
    target_persona_count: int,
    data_dir: Path,
    candidate_data_dir: Path,
    raw_pool_dir: Path,
    change_notes: list[str],
    run_summaries: list[dict[str, Any]],
    translator: DynamicTranslator,
) -> str:
    notes = change_notes or [
        "当前页面未传入额外 change note；默认展示现有 M/Z/U pilot、demo5 canonical data、50-person candidate pool 与 100-person raw sampling pool。",
    ]
    return f"""
<section>
  <h2>0. 实验与改动上下文 / Experiment And Change Context</h2>
  <div class="callout">
    {_bi_text(f"附录写作口径：目标实验规模是 {target_persona_count} personas；当前页面中的数字按输入数据源自动生成，属于 pilot/candidate/final 中哪一类，由本节明确标注。", f"Appendix scope: the target experiment scale is {target_persona_count} personas. The numbers on this page are generated from the selected input sources, and this section explicitly marks whether they are pilot, candidate, or final data.")}
  </div>
  <table>
    <tr><th>{_bi_text("来源", "Source")}</th><th>{_bi_text("路径", "Path")}</th><th>{_bi_text("角色", "Role")}</th></tr>
    <tr><td>{_bi_text("Canonical trajectory data", "Canonical trajectory data")}</td><td><code>{_esc(_display_path(data_dir))}</code></td><td>{_bi_text("当前用于样例、probe、trajectory 结构说明的主数据源。", "The primary source for examples, probes, and trajectory-structure explanations in the current appendix draft.")}</td></tr>
    <tr><td>{_bi_text("Candidate trajectory pool", "Candidate trajectory pool")}</td><td><code>{_esc(_display_path(candidate_data_dir))}</code></td><td>{_bi_text("扩展候选池；当前可证明 pipeline 可扩到更多 persona。", "Expanded candidate pool; it demonstrates that the pipeline can scale to more personas.")}</td></tr>
    <tr><td>{_bi_text("Raw persona pool", "Raw persona pool")}</td><td><code>{_esc(_display_path(raw_pool_dir))}</code></td><td>{_bi_text("只作为 persona sampling 储备；若无 tau_contract，不可直接当完整实验。", "A reserve for persona sampling only; without a tau_contract, it should not be treated as a complete trajectory experiment.")}</td></tr>
  </table>
  <h3>改动说明 / Change Notes</h3>
  <ul>{''.join(f'<li>{_paragraph_bi(note, translator)}</li>' for note in notes)}</ul>
  <h3>纳入的运行 / Included Runs</h3>
  {_run_overview_table(run_summaries)}
</section>
"""


def _section_memory_conditions(
    example: dict[str, Any], *, translator: DynamicTranslator
) -> str:
    rows = example.get("rows", [])
    if not rows:
        condition_table = "<p class=\"muted\">未找到可展示的 condition example。</p>"
    else:
        condition_table = (
            "<table><tr>"
            f"<th>{_bi_text('条件', 'Condition')}</th>"
            f"<th>{_bi_text('可读记忆摘录', 'Readable memory excerpt')}</th>"
            f"<th>{_bi_text('助手回答摘录', 'Assistant answer excerpt')}</th>"
            "</tr>"
            + "".join(
                "<tr>"
                f"<td><code>{_esc(row.get('condition'))}</code><br><span class=\"small muted\">{_esc(row.get('memory_condition'))}</span></td>"
                f"<td>{_paragraph_bi(row.get('memory_excerpt'), translator)}</td>"
                f"<td>{_paragraph_bi(row.get('answer_excerpt'), translator)}</td>"
                "</tr>"
                for row in rows
            )
            + "</table>"
        )
    meta = {
        "message_id": example.get("message_id"),
        "persona_id": example.get("persona_id"),
        "day": example.get("day"),
        "event_line_id": example.get("event_line_id"),
        "topic": example.get("topic"),
        "probe_type": example.get("probe_type"),
        "paper_probe_id": example.get("paper_probe_id"),
        "primary_dimension_id": example.get("primary_dimension_id"),
        "evaluation_dimension_ids": example.get("evaluation_dimension_ids"),
    }
    return f"""
<section>
  <h2>1. 完整 Memory Condition 示例 / Complete Memory Condition Example</h2>
  <p>{_bi_text("本节固定同一个 user/probe turn，横向展示 M0/M1/M2/M3 在同一输入下的 memory payload 与回答差异。最终 50 人实验版可以通过 --example-run-dir 和 --example-message-id 指定代表样例。", "This section fixes one user/probe turn and compares the memory payload and assistant response under M0, M1, M2, and M3. In the final 50-person experiment, a representative example can be selected with --example-run-dir and --example-message-id.")}</p>
  <div class="grid-2">
    <div>
      <h3>选定轮次 / Selected Turn</h3>
      <table>{''.join(f'<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>' for k, v in meta.items())}</table>
    </div>
    <div>
      <h3>用户消息 / User Message</h3>
      <div class="callout">{_paragraph_bi(example.get("user_message"), translator)}</div>
    </div>
  </div>
  {condition_table}
</section>
"""


def _section_trajectory(
    *,
    target_persona_count: int,
    data_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
    raw_pool_summary: dict[str, Any],
    construction_details: dict[str, Any],
    translator: DynamicTranslator,
) -> str:
    return f"""
<section>
  <h2>2. 轨迹构造细节 / Trajectory Construction Details</h2>
  <p>{_bi_text("本节描述最终附录应固定的构造流程：persona sampling -> accepted event categories/themes -> recurring event lines -> 30-day daily interaction units -> opening/follow-up/probe binding -> tau contract validation。", "This section specifies the construction pipeline that should be fixed in the final appendix: persona sampling -> accepted event categories/themes -> recurring event lines -> 30-day daily interaction units -> opening/follow-up/probe binding -> tau contract validation.")}</p>
  <div class="callout todo">
    {_bi_text(f"当前目标是 {target_persona_count} personas 完整实验；当前表格同时展示 canonical pilot、candidate pool 和 raw pool，后续 50 人 run 完成后以 final data dir 覆盖本节统计。", f"The current target is a complete {target_persona_count}-persona experiment. The table currently shows the canonical pilot, candidate pool, and raw pool; after the final 50-person run is complete, this section should be regenerated from the final data directory.")}
  </div>
  <table>
    <tr><th>{_bi_text("数据集", "Dataset")}</th><th>{_bi_text("人物", "Personas")}</th><th>{_bi_text("事件线", "Event lines")}</th><th>{_bi_text("互动单元", "Interaction units")}</th><th>{_bi_text("定向 probes", "Targeted probes")}</th><th>{_bi_text("活跃天数", "Active days")}</th><th>{_bi_text("校验", "Validation")}</th></tr>
    {_trajectory_row("Canonical / current source", data_summary)}
    {_trajectory_row("Candidate trajectory pool", candidate_summary)}
    <tr><td>Raw persona pool</td><td>{_esc(raw_pool_summary.get("persona_count", "-"))}</td><td colspan="4">No tau_contract required/available: {_esc(not raw_pool_summary.get("has_tau_contract"))}</td><td>{_esc(raw_pool_summary.get("exists"))}</td></tr>
  </table>
  <h3>构造流程 / Construction Pipeline</h3>
  <ol>
    <li><b>z / personas</b>: {_bi_text("采样具有稳定生活约束、沟通风格、长期目标和敏感边界的人物画像。", "Sample persona profiles with stable life constraints, communication styles, long-term goals, and sensitive boundaries.")}</li>
    <li><b>T / accepted themes</b>: {_bi_text("为每个 persona 选择兼容的事件类别；当前实现中的 accepted event lines/themes 是数据驱动的，不强行固定为手写数量。", "Select compatible event categories for each persona; in the current implementation, accepted event lines/themes are data-driven rather than forced to a fixed hand-written count.")}</li>
    <li><b>L / event lines</b>: {_bi_text("把反复出现的用户生活情境转化为带阶段推进的 persistent event_line_id 对象。", "Convert recurring user-life situations into persistent event_line_id objects with staged progression.")}</li>
    <li><b>I / interaction units</b>: {_bi_text("把每次 occurrence 展开为可执行的每日互动单元，包含 scripted opening、constrained follow-up budget、allowed facts 和 scene boundary。", "Expand each occurrence into executable daily interaction units with a scripted opening, constrained follow-up budget, allowed facts, and a scene boundary.")}</li>
    <li><b>P / probes</b>: {_bi_text("在绑定的 interaction unit 之后插入只读 targeted relational probes；probe 不写回记忆。", "Insert read-only targeted relational probes after bound interaction units; probes do not write back to memory.")}</li>
    <li><b>Validation</b>: {_bi_text("检查 persona、theme、event_line_id、interaction_unit_id、event_occurrence_id、message_id 和 probe_id 的绑定完整性。", "Check binding integrity across persona, theme, event_line_id, interaction_unit_id, event_occurrence_id, message_id, and probe_id.")}</li>
  </ol>
  <h3>全量清单与抽样展开 / Full Inventory And Concrete Example</h3>
  <p>{_bi_text("本块按 z/T/L/I/P 分层展示：规模可控的 z/personas 与每人 accepted themes 全量列出；规模较大的 event lines、interaction units、probes 给出全量统计和每人计数，并展开一条可追踪样例链路。", "This block follows the z/T/L/I/P hierarchy. Manageable layers such as z/personas and per-persona accepted themes are listed in full; larger layers such as event lines, interaction units, and probes are summarized globally and per persona, with one traceable example expanded in detail.")}</p>
  {_construction_detail_html(construction_details, translator)}
  <h3>当前分布快照 / Current Distribution Snapshots</h3>
  <div class="grid-2">
    <div>{_counter_table("Paper probe type counts", data_summary.get("paper_probe_type_counts", {}))}</div>
    <div>{_counter_table("Primary dimension counts", data_summary.get("primary_dimension_counts", {}))}</div>
  </div>
</section>
"""


def _section_probe_examples(
    probes: list[dict[str, Any]],
    *,
    examples_per_bucket: int,
    translator: DynamicTranslator,
) -> str:
    return f"""
<section>
  <h2>3. Probe 例子 / Probe Examples</h2>
  <p>{_bi_text("每个 D1-D4 维度和 P1-P6 probe type 可以固定抽 2-3 个代表例子。当前页面从输入 tau_contract/probe_plan 自动抽取，最终实验只需换数据源刷新。", "For each D1-D4 dimension and P1-P6 probe type, the appendix can include 2-3 representative examples. This page samples them automatically from the selected tau_contract/probe_plan; the final experiment only needs a data-source refresh.")}</p>
  <h3>按主维度抽样 / Examples By Primary Dimension</h3>
  {_probe_bucket_tables(probes, key_func=lambda p: str(p.get("primary_dimension_id") or "unknown"), examples_per_bucket=examples_per_bucket, translator=translator)}
  <h3>按 Probe 类型抽样 / Examples By Probe Type</h3>
  {_probe_bucket_tables(probes, key_func=lambda p: str(p.get("paper_probe_id") or p.get("probe_type") or "unknown"), examples_per_bucket=examples_per_bucket, translator=translator)}
</section>
"""


def _section_rubric(probes: list[dict[str, Any]]) -> str:
    dimension_defs = _dimension_definitions(probes)
    return f"""
<section>
  <h2>4. 评测标准 / Evaluation Rubric</h2>
  <p>{_bi_text("附录中建议同时给出论文级 D1-D4 维度、实现级 LLM judge diagnostic dimensions、0/1/2 评分标准、strict caps、flags 和 failure types。", "The appendix should include the paper-level D1-D4 dimensions, implementation-level LLM-judge diagnostic dimensions, 0/1/2 scoring criteria, strict caps, flags, and failure types.")}</p>
  <h3>D1-D4 Probe 维度 / D1-D4 Probe Dimensions</h3>
  <table><tr><th>ID</th><th>{_bi_text("英文名", "Name")}</th><th>{_bi_text("中文名", "Chinese")}</th></tr>{''.join(f'<tr><td><code>{_esc(k)}</code></td><td>{_esc(v.get("name"))}</td><td>{_esc(v.get("zh"))}</td></tr>' for k, v in sorted(dimension_defs.items()))}</table>
  <h3>LLM Judge 诊断维度 / LLM Judge Diagnostic Dimensions</h3>
  <table>
    <tr><th>{_bi_text("维度", "Dimension")}</th><th>{_bi_text("评估问题", "Question")}</th><th>0</th><th>1</th><th>2</th></tr>
    {''.join(_rubric_row(k, v) for k, v in TOM_DIMENSION_RUBRIC.items())}
  </table>
  <div class="grid-2">
    <div>
      <h3>错误类型 / Failure Types</h3>
      <table><tr><th>{_bi_text("类型", "Type")}</th><th>{_bi_text("定义", "Definition")}</th></tr>{''.join(f'<tr><td><code>{_esc(k)}</code></td><td>{_bi_text(v, FAILURE_TYPE_EN.get(k, ""))}</td></tr>' for k, v in STRICT_SCORING_CONTRACT.get("failure_type_taxonomy", {}).items())}</table>
    </div>
    <div>
      <h3>Flags</h3>
      <p>{''.join(f'<span class="tag">{_esc(flag)}</span>' for flag in FLAG_NAMES)}</p>
      <h3>严格评分姿态 / Strict Scoring Posture</h3>
      <ul>{''.join(f'<li>{_bi_text(item, SCORING_POSTURE_EN.get(item, ""))}</li>' for item in STRICT_SCORING_CONTRACT.get("scoring_posture", []))}</ul>
    </div>
  </div>
  <details>
    <summary>严格分数上限 / Strict score caps</summary>
    <ul>{''.join(f'<li>{_bi_text(item, SCORE_CAPS_EN.get(item, ""))}</li>' for item in STRICT_SCORING_CONTRACT.get("score_caps", []))}</ul>
  </details>
  <details>
    <summary>允许的错误类型枚举 / Allowed failure type enum</summary>
    <p>{''.join(f'<span class="tag">{_esc(item)}</span>' for item in FAILURE_TYPES)}</p>
  </details>
</section>
"""


def _section_prompts(prompt_items: list[dict[str, str]]) -> str:
    details = []
    for item in prompt_items:
        details.append(
            "<details>"
            f"<summary>{_esc(item.get('title'))}</summary>"
            f"<p class=\"small muted\">Source: <code>{_esc(item.get('source'))}</code></p>"
            f"<pre>{_esc(item.get('text'))}</pre>"
            "</details>"
        )
    condition_table = (
        "<table><tr><th>Condition</th><th>Memory types</th><th>Composition</th></tr>"
        + "".join(
            "<tr>"
            f"<td><code>{_esc(condition)}</code></td>"
            f"<td>{_esc(', '.join(types))}</td>"
            f"<td>{_esc(RELATIONAL_CONDITION_COMPOSITION.get(condition, ''))}</td>"
            "</tr>"
            for condition, types in CONDITION_MEMORY_TYPES.items()
        )
        + "</table>"
    )
    return f"""
<section>
  <h2>5. 提示词 / Prompts</h2>
  <p>{_bi_text("本节从代码中的正式 prompt source 自动抽取。最终论文附录可选择完整贴出，或贴核心模板并引用代码/manifest。", "This section is extracted from the formal prompt sources in code. The final paper appendix can either include the full text or include the core templates with references to the code/manifest.")}</p>
  <h3>Runtime 条件清单 / Runtime Condition Inventory</h3>
  {condition_table}
  <h3>提示词模板与样例 / Prompt Templates And Samples</h3>
  {''.join(details)}
</section>
"""


def _section_extra_results(run_summaries: list[dict[str, Any]]) -> str:
    return f"""
<section>
  <h2>6. 额外结果 / Extra Results</h2>
  <p>{_bi_text("本节提供 per-condition、per-dimension、persona variance 和 low-score examples 的统一槽位。当前数字来自 pilot run；最终 50 人实验后同一脚本会自动刷新。", "This section provides unified slots for per-condition results, per-dimension results, persona variance, and low-score examples. The current numbers come from pilot runs; after the final 50-person experiment, the same script will refresh them automatically.")}</p>
  <h3>条件汇总 / Condition Summary</h3>
  {_condition_result_table(run_summaries)}
  <h3>按维度结果 / Per-Dimension Results</h3>
  {_dimension_result_table(run_summaries)}
  <h3>人物间方差 / Persona Variance</h3>
  {_persona_variance_table(run_summaries)}
  <h3>低分样例 / Lowest Scoring Examples</h3>
  {_lowest_examples_table(run_summaries)}
</section>
"""


def _section_sources(
    *,
    data_dir: Path,
    candidate_data_dir: Path,
    raw_pool_dir: Path,
    run_summaries: list[dict[str, Any]],
) -> str:
    run_items = "".join(
        f"<li><code>{_esc(item.get('label'))}</code>: <code>{_esc(_display_path(item.get('run_dir')))}</code></li>"
        for item in run_summaries
    )
    return f"""
<section>
  <h2>来源清单 / Source Manifest</h2>
  <ul>
    <li>Canonical data: <code>{_esc(_display_path(data_dir))}</code></li>
    <li>Candidate data: <code>{_esc(_display_path(candidate_data_dir))}</code></li>
    <li>Raw persona pool: <code>{_esc(_display_path(raw_pool_dir))}</code></li>
    {run_items}
    <li>Generator: <code>scripts/22_generate_appendix_html.py</code></li>
  </ul>
</section>
"""


def _run_overview_table(run_summaries: list[dict[str, Any]]) -> str:
    rows = []
    for item in run_summaries:
        variants = item.get("variant_summaries", {})
        rows.append(
            "<tr>"
            f"<td>{_esc(item.get('label'))}</td>"
            f"<td><code>{_esc(_display_path(item.get('run_dir')))}</code></td>"
            f"<td>{_esc(item.get('persona_count'))}<br><span class=\"small muted\">{_esc(', '.join(item.get('persona_ids', [])))}</span></td>"
            f"<td>{_esc(item.get('probe_count'))}</td>"
            f"<td>{''.join(f'<span class=\"tag\">{_esc(k)}</span>' for k in variants)}</td>"
            "</tr>"
        )
    return (
        "<table><tr><th>Run</th><th>Path</th><th>Personas</th><th>Probe turns</th><th>Conditions</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _trajectory_row(label: str, summary: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{_esc(label)}</td>"
        f"<td>{_esc(summary.get('persona_count', '-'))}</td>"
        f"<td>{_esc(summary.get('event_line_count', '-'))}</td>"
        f"<td>{_esc(summary.get('interaction_unit_count', '-'))}</td>"
        f"<td>{_esc(summary.get('targeted_probe_count', '-'))}</td>"
        f"<td>{_esc(summary.get('active_day_count', '-'))}</td>"
        f"<td>{_esc(summary.get('validation', '-'))}</td>"
        "</tr>"
    )


def _construction_detail_html(
    details: dict[str, Any], translator: DynamicTranslator
) -> str:
    if not isinstance(details, dict) or not details:
        return "<p class=\"muted\">No construction detail data available.</p>"
    summary = details.get("summary", {}) or {}
    source = _display_path(details.get("path"))
    return f"""
  <div class="callout">
    {_bi_text("本块使用下列 trajectory 数据源自动生成；默认工作版在 pilot 数据仍为 5 人时，使用 50 人 candidate pool 展示最终规模的构造细节。", "This block is generated from the trajectory data source below. In the working appendix, when the pilot source still has 5 personas, the 50-person candidate pool is used to show construction details at the intended final scale.")}
    <br><code>{_esc(source)}</code>
  </div>
  <table>
    <tr><th>{_bi_text("层", "Layer")}</th><th>{_bi_text("全量规模", "Full scale")}</th><th>{_bi_text("主文呈现方式", "How it is shown")}</th></tr>
    <tr><td><code>z / personas</code></td><td>{_esc(len(details.get("persona_inventory", [])))} personas</td><td>{_bi_text("全量列出每个 persona 的 ID、原型、职业/生活阶段、记忆相关特征。", "All personas are listed with ID, archetype, occupation/life stage, and memory-relevant traits.")}</td></tr>
    <tr><td><code>T / accepted themes</code></td><td>{_esc(len(details.get("accepted_rows", [])))} persona sets; {_esc(len(details.get("categories", [])))} unique categories</td><td>{_bi_text("全量给出 domain/category 分布和每个 persona 的 accepted event IDs。", "The domain/category distribution and each persona's accepted event IDs are shown in full.")}</td></tr>
    <tr><td><code>L / event lines</code></td><td>{_esc(summary.get("event_line_count", "-"))} event lines</td><td>{_bi_text("全量给出每人 event line 数量与 ID；正文展开一条完整 stage sequence。", "Per-persona event-line counts and IDs are listed; one full stage sequence is expanded.")}</td></tr>
    <tr><td><code>I / interaction units</code></td><td>{_esc(summary.get("interaction_unit_count", "-"))} units</td><td>{_bi_text("给出全量统计和每人计数；正文展开一个带 opening/follow-up/scene boundary 的 unit。", "Global statistics and per-persona counts are shown; one unit is expanded with opening, follow-up, and scene boundary.")}</td></tr>
    <tr><td><code>P / probes</code></td><td>{_esc(summary.get("targeted_probe_count", "-"))} probes</td><td>{_bi_text("给出 probe type / dimension 全量分布；正文展开一个 probe 的绑定、只读规则和 ground truth。", "Full probe-type and dimension distributions are shown; one probe is expanded with binding, read-only policy, and ground truth.")}</td></tr>
  </table>
  {_persona_inventory_table(details)}
  {_accepted_theme_tables(details)}
  {_event_line_detail_html(details)}
  {_interaction_unit_detail_html(details)}
  {_probe_detail_html(details, translator)}
"""


def _persona_inventory_table(details: dict[str, Any]) -> str:
    rows = []
    for item in details.get("persona_inventory", []):
        rows.append(
            "<tr>"
            f"<td><code>{_esc(item.get('persona_id'))}</code><br><span class=\"small muted\">{_esc(item.get('archetype'))}</span></td>"
            f"<td>{_bi_text(item.get('label_zh'), item.get('label'))}</td>"
            f"<td>{_bi_text(item.get('occupation_zh'), item.get('occupation'))}<br>{_bi_text(item.get('life_stage_zh'), item.get('life_stage'))}</td>"
            f"<td>{_bi_text(_join_values(item.get('domains_zh')), _join_values(item.get('domains')))}</td>"
            f"<td>{_bi_text(_join_values(item.get('communication_style_zh')), _join_values(item.get('communication_style')))}</td>"
            f"<td>{_bi_text(_join_values(item.get('memory_traits_zh')), _join_values(item.get('memory_traits')))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p class=\"muted\">No persona inventory available.</p>"
    return (
        f"<details open><summary>z / personas: {_esc(len(rows))} full rows</summary>"
        "<table><tr>"
        f"<th>{_bi_text('Persona', 'Persona')}</th>"
        f"<th>{_bi_text('原型', 'Archetype')}</th>"
        f"<th>{_bi_text('职业与阶段', 'Occupation and life stage')}</th>"
        f"<th>{_bi_text('生活域', 'Life domains')}</th>"
        f"<th>{_bi_text('沟通风格', 'Communication style')}</th>"
        f"<th>{_bi_text('记忆相关特征', 'Memory-relevant traits')}</th>"
        "</tr>"
        + "".join(rows)
        + "</table></details>"
    )


def _accepted_theme_tables(details: dict[str, Any]) -> str:
    domain_table = _counter_table(
        "T domain counts across accepted themes",
        details.get("domain_counts", {}),
    )
    category_rows = []
    for category in details.get("categories", []):
        category_rows.append(
            "<tr>"
            f"<td><code>{_esc(category.get('event_category_id'))}</code></td>"
            f"<td>{_esc(category.get('event_domain'))}</td>"
            f"<td>{_esc(category.get('title'))}</td>"
            f"<td>{_paragraph(category.get('core_issue'))}</td>"
            "</tr>"
        )
    persona_rows = []
    for item in details.get("accepted_rows", []):
        persona_rows.append(
            "<tr>"
            f"<td><code>{_esc(item.get('persona_id'))}</code></td>"
            f"<td>{_esc(item.get('accepted_event_count'))}</td>"
            f"<td>{''.join(f'<span class=\"tag\">{_esc(value)}</span>' for value in item.get('accepted_event_ids', []))}</td>"
            f"<td>{_domain_count_tags(item.get('domain_counts', {}))}</td>"
            "</tr>"
        )
    return f"""
  <details open><summary>T / accepted themes: full domain/category inventory</summary>
    <div class="grid-2">
      <div>{domain_table}</div>
      <div>
        <h3>{_bi_text("唯一事件类别", "Unique event categories")}</h3>
        <table><tr><th>ID</th><th>Domain</th><th>{_bi_text("标题", "Title")}</th><th>{_bi_text("核心问题", "Core issue")}</th></tr>{''.join(category_rows)}</table>
      </div>
    </div>
    <h3>{_bi_text("每个 persona 的 accepted event IDs", "Accepted event IDs for each persona")}</h3>
    <table><tr><th>Persona</th><th>Count</th><th>Accepted event IDs</th><th>Domain counts</th></tr>{''.join(persona_rows)}</table>
  </details>
"""


def _event_line_detail_html(details: dict[str, Any]) -> str:
    line_rows = []
    for item in details.get("event_line_rows", []):
        line_rows.append(
            "<tr>"
            f"<td><code>{_esc(item.get('persona_id'))}</code></td>"
            f"<td>{_esc(item.get('event_line_count'))}</td>"
            f"<td>{''.join(f'<span class=\"tag\">{_esc(value)}</span>' for value in item.get('event_line_ids', []))}</td>"
            "</tr>"
        )
    line = details.get("sample_event_line", {}) or {}
    stages = line.get("stage_sequence", []) if isinstance(line, dict) else []
    stage_rows = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        stage_rows.append(
            "<tr>"
            f"<td>{_esc(stage.get('stage_index'))}<br><code>{_esc(stage.get('event_stage'))}</code></td>"
            f"<td>{_bi_text(stage.get('source_stage_label_zh'), stage.get('source_stage_label'))}</td>"
            f"<td>{_bi_text(stage.get('stage_goal_zh'), stage.get('stage_goal'))}</td>"
            f"<td>{_bi_text(stage.get('user_message_seed_zh'), stage.get('user_message_seed'))}</td>"
            f"<td>{_bi_text(stage.get('assistant_memory_expectation_zh'), stage.get('assistant_memory_expectation'))}</td>"
            "</tr>"
        )
    title = line.get("event_title", {}) if isinstance(line.get("event_title"), dict) else {}
    return f"""
  <details><summary>L / event lines: full per-persona IDs and one expanded line</summary>
    <table><tr><th>Persona</th><th>Event line count</th><th>Event line IDs</th></tr>{''.join(line_rows)}</table>
    <h3>{_bi_text("抽样展开的 event line", "Expanded sample event line")}</h3>
    <table>
      <tr><th>ID</th><td><code>{_esc(line.get('event_line_id'))}</code></td></tr>
      <tr><th>{_bi_text('标题', 'Title')}</th><td>{_bi_text(title.get('zh'), title.get('source'))}</td></tr>
      <tr><th>{_bi_text('长期事件摘要', 'Persistent event summary')}</th><td>{_bi_text(line.get('persistent_event_summary_zh'), line.get('persistent_event_summary'))}</td></tr>
      <tr><th>{_bi_text('关系记忆目标', 'Relational memory targets')}</th><td>{_target_list(line.get('relational_memory_targets', []))}</td></tr>
    </table>
    <table><tr><th>Stage</th><th>{_bi_text('阶段标签', 'Stage label')}</th><th>{_bi_text('目标', 'Goal')}</th><th>{_bi_text('用户开场种子', 'User-message seed')}</th><th>{_bi_text('记忆期待', 'Memory expectation')}</th></tr>{''.join(stage_rows)}</table>
  </details>
"""


def _interaction_unit_detail_html(details: dict[str, Any]) -> str:
    summary = details.get("summary", {}) or {}
    unit_counts = summary.get("interaction_units_per_persona", {}) or {}
    probe_counts = summary.get("probes_per_persona", {}) or {}
    count_rows = []
    for persona_id in sorted(unit_counts):
        count_rows.append(
            "<tr>"
            f"<td><code>{_esc(persona_id)}</code></td>"
            f"<td>{_esc(unit_counts.get(persona_id))}</td>"
            f"<td>{_esc(probe_counts.get(persona_id, '-'))}</td>"
            "</tr>"
        )
    unit = details.get("sample_unit", {}) or {}
    opening = unit.get("scripted_opening", {}) if isinstance(unit, dict) else {}
    followup = unit.get("constrained_followup", {}) if isinstance(unit, dict) else {}
    scene = unit.get("scene_boundary", {}) if isinstance(unit, dict) else {}
    reveal_rows = []
    for step in followup.get("reveal_steps", []) or []:
        if not isinstance(step, dict):
            continue
        reveal_rows.append(
            "<tr>"
            f"<td>{_esc(step.get('followup_index'))}</td>"
            f"<td>{''.join(f'<span class=\"tag\">{_esc(value)}</span>' for value in step.get('preferred_moves', []))}</td>"
            f"<td>{_bi_text(step.get('instruction_zh'), step.get('instruction'))}</td>"
            f"<td>{''.join(f'<span class=\"tag\">{_esc(value)}</span>' for value in step.get('may_reveal_fact_ids', []))}</td>"
            "</tr>"
        )
    fact_rows = []
    for fact in (scene.get("allowed_facts", []) or [])[:10]:
        if not isinstance(fact, dict):
            continue
        fact_rows.append(
            "<tr>"
            f"<td><code>{_esc(fact.get('fact_id'))}</code><br><span class=\"small muted\">{_esc(fact.get('type'))}</span></td>"
            f"<td>{_bi_text(fact.get('text_zh'), fact.get('text'))}</td>"
            f"<td>{_esc(fact.get('source'))}</td>"
            "</tr>"
        )
    return f"""
  <details><summary>I / interaction units: full per-persona counts and one expanded unit</summary>
    <table><tr><th>Persona</th><th>Interaction units</th><th>Probe turns</th></tr>{''.join(count_rows)}</table>
    <h3>{_bi_text("抽样展开的 interaction unit", "Expanded sample interaction unit")}</h3>
    <table>
      <tr><th>ID</th><td><code>{_esc(unit.get('interaction_unit_id'))}</code></td></tr>
      <tr><th>Day / Stage</th><td>D{_esc(unit.get('day'))} · <code>{_esc(unit.get('event_stage'))}</code> · occurrence {_esc(unit.get('occurrence_index'))}</td></tr>
      <tr><th>Event line</th><td><code>{_esc(unit.get('event_line_id'))}</code></td></tr>
      <tr><th>{_bi_text('开场消息', 'Scripted opening')}</th><td>{_bi_text(opening.get('user_message_zh'), opening.get('user_message'))}</td></tr>
      <tr><th>{_bi_text('会话目标', 'Conversation goal')}</th><td>{_bi_text(opening.get('conversation_goal_zh'), opening.get('conversation_goal'))}</td></tr>
      <tr><th>{_bi_text('follow-up 预算', 'Follow-up budget')}</th><td>{_esc(followup.get('followup_budget'))}</td></tr>
    </table>
    <table><tr><th>Step</th><th>Preferred moves</th><th>{_bi_text('用户扩展规则', 'User expansion rule')}</th><th>May reveal fact IDs</th></tr>{''.join(reveal_rows)}</table>
    <table><tr><th>Allowed fact</th><th>{_bi_text('内容', 'Content')}</th><th>Source</th></tr>{''.join(fact_rows)}</table>
  </details>
"""


def _probe_detail_html(details: dict[str, Any], translator: DynamicTranslator) -> str:
    summary = details.get("summary", {}) or {}
    probe = details.get("sample_probe", {}) or {}
    ground_truth = probe.get("ground_truth", {}) if isinstance(probe, dict) else {}
    must = ground_truth.get("must_recognize", {}) if isinstance(ground_truth, dict) else {}
    respect = (
        ground_truth.get("must_use_or_respect", {})
        if isinstance(ground_truth, dict)
        else {}
    )
    return f"""
  <details><summary>P / probes: full distributions and one expanded read-only probe</summary>
    <div class="grid-2">
      <div>{_counter_table("Paper probe type counts", summary.get("paper_probe_type_counts", {}))}</div>
      <div>{_counter_table("Primary dimension counts", summary.get("primary_dimension_counts", {}))}</div>
    </div>
    <h3>{_bi_text("抽样展开的 targeted probe", "Expanded sample targeted probe")}</h3>
    <table>
      <tr><th>Probe ID</th><td><code>{_esc(probe.get('probe_id'))}</code></td></tr>
      <tr><th>Binding</th><td>insert_after_message_id: <code>{_esc(probe.get('insert_after_message_id'))}</code><br>event_line_id: <code>{_esc(probe.get('event_line_id'))}</code><br>day: D{_esc(probe.get('day'))}</td></tr>
      <tr><th>Type / Dimension</th><td><code>{_esc(probe.get('paper_probe_id'))}</code> {_esc(probe.get('paper_probe_type'))} · <code>{_esc(probe.get('primary_dimension_id'))}</code></td></tr>
      <tr><th>{_bi_text('Probe 问题', 'Probe question')}</th><td>{_paragraph_bi(probe.get('question') or probe.get('user_message'), translator)}</td></tr>
      <tr><th>{_bi_text('只读规则', 'Read-only rule')}</th><td>read_only: <code>{_esc(probe.get('read_only'))}</code><br>writeback_policy: <code>{_esc(probe.get('writeback_policy'))}</code></td></tr>
      <tr><th>{_bi_text('必须识别', 'Must recognize')}</th><td>{_paragraph_bi(_compact_json(must), translator)}</td></tr>
      <tr><th>{_bi_text('必须使用或尊重', 'Must use or respect')}</th><td>{_paragraph_bi(_compact_json(respect), translator)}</td></tr>
      <tr><th>{_bi_text('可接受回应摘要', 'Acceptable response summary')}</th><td>{_paragraph_bi(ground_truth.get('acceptable_response'), translator)}</td></tr>
    </table>
  </details>
"""


def _probe_bucket_tables(
    probes: list[dict[str, Any]],
    *,
    key_func: Any,
    examples_per_bucket: int,
    translator: DynamicTranslator,
) -> str:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for probe in probes:
        key = key_func(probe)
        buckets.setdefault(key, []).append(probe)
    if not buckets:
        return "<p class=\"muted\">No probe examples available.</p>"
    parts = []
    for key in sorted(buckets):
        rows = []
        for probe in buckets[key][:examples_per_bucket]:
            ground_truth = probe.get("ground_truth", {})
            must = ground_truth.get("must_recognize", {}) if isinstance(ground_truth, dict) else {}
            rows.append(
                "<tr>"
                f"<td><code>{_esc(probe.get('probe_id') or probe.get('message_id'))}</code><br><span class=\"small muted\">{_esc(probe.get('paper_probe_id') or probe.get('probe_type'))}</span></td>"
                f"<td>{_paragraph_bi(probe.get('question') or probe.get('user_message'), translator)}</td>"
                f"<td>{_esc(probe.get('event_line_id'))}<br>{_esc(probe.get('event_stage'))}</td>"
                f"<td>{_paragraph_bi(must.get('current_stage') or ground_truth.get('acceptable_response') if isinstance(ground_truth, dict) else '', translator)}</td>"
                "</tr>"
            )
        parts.append(
            f"<details open><summary>{_esc(key)} ({len(buckets[key])} total)</summary>"
            "<table><tr>"
            f"<th>{_bi_text('Probe', 'Probe')}</th>"
            f"<th>{_bi_text('问题', 'Question')}</th>"
            f"<th>{_bi_text('绑定', 'Binding')}</th>"
            f"<th>{_bi_text('预期识别', 'Expected recognition')}</th>"
            "</tr>"
            + "".join(rows)
            + "</table></details>"
        )
    return "".join(parts)


def _dimension_definitions(probes: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    dims: dict[str, dict[str, str]] = {}
    for probe in probes:
        primary = probe.get("primary_dimension")
        if isinstance(primary, dict) and primary.get("id"):
            dims[str(primary["id"])] = {
                "name": str(primary.get("name", "")),
                "zh": str(primary.get("zh", "")),
            }
        for item in probe.get("evaluation_dimensions", []):
            if isinstance(item, dict) and item.get("id"):
                dims[str(item["id"])] = {
                    "name": str(item.get("name", "")),
                    "zh": str(item.get("zh", "")),
                }
    return dims


def _rubric_row(key: str, item: dict[str, str]) -> str:
    return (
        "<tr>"
        f"<td><code>{_esc(key)}</code><br>{_esc(item.get('label'))}</td>"
        f"<td>{_bi_text(item.get('question'), RUBRIC_EN.get(key, {}).get('question', ''))}</td>"
        f"<td>{_bi_text(item.get('score_0'), RUBRIC_EN.get(key, {}).get('score_0', ''))}</td>"
        f"<td>{_bi_text(item.get('score_1'), RUBRIC_EN.get(key, {}).get('score_1', ''))}</td>"
        f"<td>{_bi_text(item.get('score_2'), RUBRIC_EN.get(key, {}).get('score_2', ''))}</td>"
        "</tr>"
    )


def _condition_result_table(run_summaries: list[dict[str, Any]]) -> str:
    rows = []
    for run in run_summaries:
        variants = run.get("variant_summaries", {})
        for condition, item in variants.items():
            rows.append(
                "<tr>"
                f"<td>{_esc(run.get('label'))}</td>"
                f"<td><code>{_esc(condition)}</code></td>"
                f"<td>{_esc(item.get('average_tom_score', '-'))}</td>"
                f"<td>{_esc(item.get('valid_judge_count', item.get('turn_count', '-')))}</td>"
                f"<td>{_esc(item.get('needs_human_review_count', '-'))}</td>"
                f"<td>{_esc(item.get('flag_count', '-'))}</td>"
                "</tr>"
            )
    return (
        "<table><tr><th>Run</th><th>Condition</th><th>Average ToM</th><th>Valid judge</th><th>Human review</th><th>Flags</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _dimension_result_table(run_summaries: list[dict[str, Any]]) -> str:
    active_dimensions = set(TOM_DIMENSION_RUBRIC)
    dim_names = sorted(
        {
            dim
            for run in run_summaries
            for values in (run.get("dimension_averages", {}) or {}).values()
            if isinstance(values, dict)
            for dim in values
            if dim in active_dimensions
        }
    )
    if not dim_names:
        return "<p class=\"muted\">No per-dimension result data available.</p>"
    header = "".join(f"<th>{_esc(dim)}</th>" for dim in dim_names)
    rows = []
    for run in run_summaries:
        for condition, values in (run.get("dimension_averages", {}) or {}).items():
            rows.append(
                "<tr>"
                f"<td>{_esc(run.get('label'))}</td>"
                f"<td><code>{_esc(condition)}</code></td>"
                + "".join(f"<td>{_esc(_fmt_float(values.get(dim)))}</td>" for dim in dim_names)
                + "</tr>"
            )
    return (
        f"<table><tr><th>Run</th><th>Condition</th>{header}</tr>"
        + "".join(rows)
        + "</table>"
    )


def _persona_variance_table(run_summaries: list[dict[str, Any]]) -> str:
    rows = []
    for run in run_summaries:
        for condition, item in (run.get("persona_variance", {}) or {}).items():
            rows.append(
                "<tr>"
                f"<td>{_esc(run.get('label'))}</td>"
                f"<td><code>{_esc(condition)}</code></td>"
                f"<td>{_esc(item.get('persona_count', '-'))}</td>"
                f"<td>{_esc(_fmt_float(item.get('variance')))}</td>"
                f"<td>{_esc(_fmt_float(item.get('stddev')))}</td>"
                f"<td>{_esc(_fmt_float(item.get('norm_variance')))}</td>"
                f"<td>{_esc(_fmt_float(item.get('norm_range')))}</td>"
                "</tr>"
            )
    if not rows:
        return "<p class=\"muted\">No persona variance data available.</p>"
    return (
        "<table><tr><th>Run</th><th>Condition</th><th>Personas</th><th>Variance</th><th>Stddev</th><th>Norm var</th><th>Norm range</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _lowest_examples_table(run_summaries: list[dict[str, Any]]) -> str:
    rows = []
    for run in run_summaries:
        for item in (run.get("lowest_scoring_examples", []) or [])[:8]:
            rows.append(
                "<tr>"
                f"<td>{_esc(run.get('label'))}</td>"
                f"<td><code>{_esc(item.get('message_id') or item.get('case_id'))}</code></td>"
                f"<td><code>{_esc(item.get('variant') or item.get('condition'))}</code></td>"
                f"<td>{_esc(item.get('score', item.get('tom_score', '-')))}</td>"
                f"<td>{_paragraph(_current_schema_text(item.get('reason') or item.get('overall_reason') or item.get('answer_excerpt')))}</td>"
                "</tr>"
            )
    if not rows:
        return "<p class=\"muted\">No low-score example data available.</p>"
    return (
        "<table><tr><th>Run</th><th>Message</th><th>Condition</th><th>Score</th><th>Reason / excerpt</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _counter_table(title: str, values: dict[str, Any]) -> str:
    if not isinstance(values, dict) or not values:
        return f"<h3>{_esc(title)}</h3><p class=\"muted\">No data.</p>"
    rows = "".join(
        f"<tr><td><code>{_esc(key)}</code></td><td>{_esc(value)}</td></tr>"
        for key, value in sorted(values.items())
    )
    return f"<h3>{_esc(title)}</h3><table><tr><th>Key</th><th>Count</th></tr>{rows}</table>"


def _metric(label: str, value: Any, note: str) -> str:
    return (
        "<div class=\"metric\">"
        f"<b>{_esc(value)}</b><span>{_esc(label)} / {_esc(note)}</span>"
        "</div>"
    )


def _memory_excerpt(variant: dict[str, Any], *, limit: int) -> str:
    payload = variant.get("memory_payload")
    if isinstance(payload, dict):
        for key in (
            "memory_context",
            "readable_memory",
            "allowed_memory",
            "memory_text",
            "summary",
        ):
            if payload.get(key):
                return _truncate(str(payload[key]), limit)
        return _truncate(json.dumps(payload, ensure_ascii=False, sort_keys=True), limit)
    if isinstance(payload, str):
        return _truncate(payload, limit)
    return _truncate(str(variant.get("memory_context") or ""), limit)


def _persona_id(turn: dict[str, Any]) -> str:
    source = turn.get("source", {}) if isinstance(turn, dict) else {}
    message = turn.get("input", {}) if isinstance(turn, dict) else {}
    return str(
        message.get("persona_id")
        or source.get("persona_id")
        or source.get("tau", {}).get("persona_id")
        or ""
    )


def _persona_count_from_sampled(sampled: dict[str, Any]) -> int | None:
    if not isinstance(sampled, dict):
        return None
    if isinstance(sampled.get("personas"), list):
        return len(sampled["personas"])
    summary = sampled.get("summary", {})
    if isinstance(summary, dict) and summary.get("persona_count") is not None:
        return int(summary["persona_count"])
    zh_personas = (
        sampled.get("locale_views", {})
        .get("zh", {})
        .get("personas", [])
    )
    if isinstance(zh_personas, list):
        return len(zh_personas)
    return None


def _calendar_day_count(timeline: dict[str, Any]) -> int | None:
    timelines = timeline.get("timelines") if isinstance(timeline, dict) else None
    if not isinstance(timelines, list):
        return None
    count = 0
    for item in timelines:
        days = item.get("days", []) if isinstance(item, dict) else []
        if isinstance(days, list):
            count += len(days)
    return count


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"items": data}


def _display_path(path: Any) -> str:
    if not isinstance(path, Path):
        path = Path(str(path))
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return str(path)


def _truncate(value: str, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _paragraph(value: Any) -> str:
    text = _truncate(str(value or ""), 1200)
    if not text:
        return "<span class=\"muted\">-</span>"
    return "<br>".join(_esc(part) for part in text.split("\n"))


def _paragraph_bi(value: Any, translator: DynamicTranslator) -> str:
    text = _truncate(str(value or ""), 1200)
    if not text:
        return "<span class=\"muted\">-</span>"
    english = translator.en(text)
    result = _paragraph(text)
    if english:
        result += f"<div class=\"en-block\">{_esc(english)}</div>"
    return result


def _bi_text(zh: Any, en: Any) -> str:
    zh_text = str(zh or "").strip()
    en_text = str(en or "").strip()
    if not zh_text and not en_text:
        return ""
    if not en_text:
        return _esc(zh_text)
    return (
        "<span class=\"bi\">"
        f"<span class=\"zh\">{_esc(zh_text)}</span>"
        f"<span class=\"en\">{_esc(en_text)}</span>"
        "</span>"
    )


def _normalize_translation_source(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rstrip()
    return text


def _join_values(values: Any, *, limit: int = 5) -> str:
    if isinstance(values, (list, tuple)):
        return " / ".join(str(value) for value in values[:limit] if value not in (None, ""))
    if isinstance(values, dict):
        return " / ".join(f"{key}: {value}" for key, value in list(values.items())[:limit])
    return str(values or "")


def _domain_count_tags(values: Any) -> str:
    if not isinstance(values, dict) or not values:
        return "<span class=\"muted\">-</span>"
    return "".join(
        f"<span class=\"tag\">{_esc(key)}={_esc(value)}</span>"
        for key, value in sorted(values.items())
    )


def _target_list(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "<span class=\"muted\">-</span>"
    items = []
    for item in values:
        if not isinstance(item, dict):
            continue
        items.append(
            "<li>"
            f"<code>{_esc(item.get('target_type'))}</code>: "
            f"{_bi_text(item.get('target_zh'), item.get('target'))}"
            "</li>"
        )
    return "<ul>" + "".join(items) + "</ul>" if items else "<span class=\"muted\">-</span>"


def _compact_json(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _current_schema_text(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "relationship_expectation_recognition": "alienation_error_rate",
        "关系期待识别": "关系语气/陌生化控制",
        "关系期待": "关系语气",
        "relationship expectation recognition": "relational-tone / alienation control",
        "relationship expectation": "relational-tone control",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _fmt_float(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return "-" if value in (None, "") else str(value)


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
