#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import sys
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.evaluation.llm_tom_judge import TOM_DIMENSION_RUBRIC  # noqa: E402
from long_memory_test.evaluation.generation_prompt_reference import (  # noqa: E402
    RELATIONAL_CONDITION_IDS,
    build_answer_condition_system_prompt,
    build_answer_condition_system_prompt_template,
    build_relational_payload_context_template,
    memory_context_from_variant,
)


RUN_DIR = REPO_ROOT / "long_memory_experiment/outputs/run_20260628_demo5_tau_full_m0_m3"
DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
OUTPUT = REPO_ROOT / "docs/two_person_m0_m3_probe_evaluation_report.html"
VARIANTS = ("M0", "M1", "M2", "M3")


CONDITION_COLORS = {
    "M0": "#3347b8",
    "M1": "#0f766e",
    "M2": "#7c3aed",
    "M3": "#b45309",
    "Z1": "#0f766e",
    "Z2": "#7c3aed",
    "Z3": "#b45309",
    "U1": "#047857",
    "U2": "#6d28d9",
    "U3": "#a16207",
}

FAILURE_TYPE_EXPLANATIONS = {
    "memory_absence": "该接上旧语境、旧处理方式或前序事件时没有接上，甚至要求用户重讲背景。",
    "memory_misuse": "调用了错误、过期、无关或不可读记忆，或者把不该确定的内容当成确定事实。",
    "memory_overuse": "为了显得记得而机械堆细节、背日志，导致回答不自然或没有服务当前判断。",
    "fabrication": "补出用户没有说过、上下文中不可验证的具体信息。",
    "alienation": "客服化、陌生化、过度角色化、过度亲密，或让用户感觉关系位置不连续。",
    "instruction_only_success": "回答表面完成当前显性指令，但主要依赖当前问题，没有体现长期记忆或关系连续性。",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the two-person M0-M3 HTML report.")
    parser.add_argument("--run-dir", type=Path, default=RUN_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Trajectory data directory that contains sampled_personas.json.",
    )
    args = parser.parse_args()

    run_dir = args.run_dir
    output = args.output
    llm = _load_json(run_dir / "llm_judge_scores_two_person.json")
    automatic = _load_json(run_dir / "automatic_scores_two_person.json")
    conversation = _load_json(run_dir / "conversation_log_two_person_eval.json")
    run_config = _load_json(run_dir / "run_config.json")
    sampled = _load_json(args.data_dir / "sampled_personas.json")

    personas = {
        str(persona.get("persona_id")): persona
        for persona in sampled.get("locale_views", {}).get("zh", {}).get("personas", [])
        if isinstance(persona, dict)
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        _render(
            llm=llm,
            automatic=automatic,
            conversation=conversation,
            run_config=run_config,
            personas=personas,
            run_dir=run_dir,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {output}")
    return 0


def _render(
    *,
    llm: dict[str, Any],
    automatic: dict[str, Any],
    conversation: dict[str, Any],
    run_config: dict[str, Any],
    personas: dict[str, dict[str, Any]],
    run_dir: Path,
) -> str:
    global VARIANTS
    VARIANTS = _report_variants(llm=llm, conversation=conversation, run_config=run_config)
    variant_label = "/".join(VARIANTS)
    eval_turns = {
        str(turn.get("message_id")): turn
        for turn in llm.get("turns", [])
        if isinstance(turn, dict)
    }
    conversation_probes = [
        turn
        for turn in conversation.get("turns", [])
        if isinstance(turn, dict) and turn.get("input", {}).get("tom_dimensions")
    ]
    turns_by_persona: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for turn in conversation.get("turns", []):
        if isinstance(turn, dict):
            turns_by_persona[_persona_id(turn)].append(turn)

    probes_by_persona: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for turn in conversation_probes:
        probes_by_persona[_persona_id(turn)].append(turn)

    persona_sections = "".join(
        _persona_section(
            persona_id=persona_id,
            persona=personas.get(persona_id, {}),
            all_turns=turns_by_persona.get(persona_id, []),
            probe_turns=probe_turns,
            eval_turns=eval_turns,
            open_by_default=index == 0,
        )
        for index, persona_id in enumerate(sorted(turns_by_persona))
        for probe_turns in [probes_by_persona.get(persona_id, [])]
    )

    method = llm.get("method", {})
    context_policy = _first_context_policy(conversation)
    summary = llm.get("summary", {})
    extraction = conversation.get("extraction", {})
    probe_count = len(conversation_probes)
    case_count = probe_count * len(VARIANTS)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>两人 {variant_label} Probe 评测汇报</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #667085;
      --line: #d7dee9;
      --panel: #ffffff;
      --band: #f4f6f9;
      --soft: #f9fbfd;
      --accent: #0f766e;
      --blue: #3347b8;
      --warn: #9a3412;
      --bad: #b42318;
      --ok: #0f766e;
      --purple: #7c3aed;
      --empty: #f3f4f6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--band);
      color: var(--ink);
      font: 14px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 28px 18px 58px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 0; font-size: 21px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; letter-spacing: 0; }}
    h4 {{ margin: 0 0 6px; font-size: 14px; letter-spacing: 0; }}
    p {{ margin: 0; }}
    code {{
      padding: 1px 5px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #f8fafc;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      margin: 10px 0 16px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 9px;
      vertical-align: top;
      word-break: break-word;
    }}
    th {{ background: #f8fafc; text-align: left; color: #344054; }}
    .hero, .persona, .box, .metric, .probe, .standard, .answer-row, .prompt-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .hero {{ padding: 18px; }}
    .subtitle {{ color: var(--muted); max-width: 980px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .metric {{ padding: 12px; }}
    .metric b {{ display: block; font-size: 24px; line-height: 1.2; }}
    .metric span {{ color: var(--muted); font-size: 12px; }}
    .source-note {{
      margin-top: 12px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fffdf7;
    }}
    .section {{
      margin-top: 16px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .section > h2 {{ margin-bottom: 12px; }}
    .summary-grid {{
      display: grid;
      grid-template-columns: 1.05fr 1fr;
      gap: 14px;
    }}
    .field-guide {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 8px;
      margin: 10px 0 16px;
    }}
    .field-guide div {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
      padding: 9px;
    }}
    .field-guide strong {{
      display: block;
      margin-bottom: 3px;
      color: #344054;
    }}
    .standard-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .standard {{ padding: 12px; background: var(--soft); }}
    .standard h3 {{ display: flex; align-items: center; gap: 8px; }}
    .prompt-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    .prompt-card {{
      overflow: hidden;
      background: var(--soft);
    }}
    .prompt-card > summary {{
      cursor: pointer;
      list-style: none;
      padding: 10px 12px;
      background: #fbfcfe;
      border-bottom: 1px solid var(--line);
      font-weight: 800;
    }}
    .prompt-card > summary::-webkit-details-marker {{ display: none; }}
    .prompt-text {{
      margin: 0;
      padding: 10px 12px;
      max-height: 520px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace;
      color: #344054;
      background: #fff;
    }}
    .condition-dot {{
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: currentColor;
    }}
    .tag {{
      display: inline-block;
      margin: 0 6px 6px 0;
      padding: 2px 7px;
      border-radius: 999px;
      background: #eaf7f5;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    .tag.blue {{ background: #eef2ff; color: var(--blue); }}
    .tag.warn {{ background: #fff7ed; color: var(--warn); }}
    .tag.bad {{ background: #fef3f2; color: var(--bad); }}
    .tag.gray {{ background: #f2f4f7; color: #475467; }}
    .scorebar {{
      display: grid;
      grid-template-columns: 52px minmax(0, 1fr) 48px;
      gap: 8px;
      align-items: center;
      margin: 6px 0;
      font-size: 13px;
    }}
    .bar {{
      height: 9px;
      border-radius: 999px;
      background: #edf1f5;
      overflow: hidden;
    }}
    .bar i {{ display: block; height: 100%; border-radius: inherit; }}
    details.persona {{
      margin-top: 16px;
      overflow: hidden;
    }}
    details.persona > summary {{
      list-style: none;
      cursor: pointer;
      padding: 14px 16px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    details.persona > summary::-webkit-details-marker {{ display: none; }}
    .persona-body {{ padding: 14px 16px 18px; }}
    .profile {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .box {{ padding: 12px; background: var(--soft); }}
    .box b {{
      display: block;
      margin-bottom: 4px;
      color: var(--muted);
      font-size: 12px;
    }}
    .calendar {{
      display: grid;
      grid-template-columns: repeat(30, minmax(24px, 1fr));
      gap: 4px;
      margin: 10px 0 14px;
    }}
    .day-cell {{
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 5px;
      display: grid;
      place-items: center;
      background: #fff;
      color: var(--muted);
      font-size: 12px;
      text-align: center;
    }}
    .day-cell.probed {{
      background: #eaf7f5;
      border-color: #b8d9d4;
      color: var(--accent);
      font-weight: 800;
    }}
    .day-cell.low {{
      background: #fef3f2;
      border-color: #fecdca;
      color: var(--bad);
    }}
    .probe-list {{ display: grid; gap: 12px; }}
    .probe {{ overflow: hidden; }}
    .probe > header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    .probe-title {{ font-weight: 800; }}
    .question {{
      margin-top: 8px;
      padding: 10px 12px;
      border-left: 4px solid var(--accent);
      background: #f7f9fc;
    }}
    .probe-body {{
      display: grid;
      grid-template-columns: 0.95fr 1.55fr;
      gap: 12px;
      padding: 12px;
    }}
    .basis {{
      display: grid;
      gap: 10px;
      align-content: start;
    }}
    .answer-grid {{ display: grid; gap: 10px; }}
    .dialogue-section {{
      margin: 18px 0;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }}
    .dialogue-section > p {{
      margin: 4px 0 12px;
    }}
    .day-block {{
      margin-top: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }}
    .day-block > summary {{
      cursor: pointer;
      list-style: none;
      padding: 10px 12px;
      background: #fbfcfe;
      border-bottom: 1px solid var(--line);
      font-weight: 800;
    }}
    .day-block > summary::-webkit-details-marker {{ display: none; }}
    .day-turns {{
      display: grid;
      gap: 10px;
      padding: 10px;
    }}
    .turn-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
      overflow: hidden;
    }}
    .turn-card.probe-turn {{
      border-left: 5px solid var(--accent);
    }}
    .turn-head {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    .turn-body {{
      padding: 10px;
      display: grid;
      gap: 10px;
    }}
    .user-msg {{
      padding: 9px;
      border-left: 4px solid #98a2b3;
      background: #fff;
      white-space: pre-wrap;
    }}
    .assistant-variants {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }}
    .assistant-answer {{
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      overflow: hidden;
    }}
    .assistant-answer > summary, .full-answer > summary {{
      cursor: pointer;
      list-style: none;
      padding: 7px 9px;
      background: #fbfcfe;
      font-weight: 800;
    }}
    .assistant-answer > summary::-webkit-details-marker,
    .full-answer > summary::-webkit-details-marker {{ display: none; }}
    .answer-text {{
      padding: 9px;
      border-top: 1px solid var(--line);
      white-space: pre-wrap;
      word-break: break-word;
      color: #344054;
    }}
    .turn-scorebars {{
      max-width: 520px;
    }}
    .eval-link {{
      display: inline-block;
      border: 1px solid #b8d9d4;
      border-radius: 999px;
      background: #eaf7f5;
      color: var(--accent);
      padding: 2px 8px;
      font-weight: 800;
      font-size: 12px;
      text-decoration: none;
    }}
    .answer-row {{
      overflow: hidden;
      border-left-width: 5px;
    }}
    .answer-row > header {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .answer-body {{ padding: 10px; }}
    .reason {{ color: #344054; }}
    .excerpt {{
      margin-top: 8px;
      color: #475467;
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
    }}
    .detail-block {{
      margin-top: 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      overflow: hidden;
    }}
    .detail-block > summary {{
      cursor: pointer;
      list-style: none;
      padding: 8px 10px;
      background: #fbfcfe;
      font-weight: 800;
    }}
    .detail-block > summary::-webkit-details-marker {{ display: none; }}
    .dimension-table {{
      margin: 0;
      table-layout: auto;
      font-size: 13px;
    }}
    .dimension-table th, .dimension-table td {{
      padding: 7px 8px;
    }}
    .dimension-score {{
      display: inline-block;
      min-width: 36px;
      text-align: center;
      border-radius: 999px;
      padding: 1px 7px;
      font-weight: 900;
      background: #eef2ff;
      color: var(--blue);
    }}
    .failure-examples {{
      display: grid;
      gap: 8px;
      padding: 10px;
    }}
    .failure-example {{
      border: 1px solid #fecdca;
      border-radius: 7px;
      background: #fffbfa;
      padding: 9px;
    }}
    .failure-example h4 {{
      color: var(--bad);
      margin-bottom: 4px;
    }}
    .failure-example blockquote {{
      margin: 7px 0 0;
      padding: 7px 9px;
      border-left: 4px solid #f97066;
      background: #fff;
      color: #344054;
    }}
    .score {{
      font-weight: 900;
      font-size: 18px;
    }}
    .winner {{
      border: 1px solid #d6bbfb;
      background: #f4ebff;
      color: var(--purple);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 800;
    }}
    .muted {{ color: var(--muted); }}
    .compact td, .compact th {{ padding: 6px 7px; }}
    .dim-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    @media (max-width: 1050px) {{
      .metrics, .standard-grid, .prompt-grid, .profile, .summary-grid, .probe-body, .dim-grid, .field-guide, .assistant-variants {{
        grid-template-columns: 1fr;
      }}
      .calendar {{ grid-template-columns: repeat(10, minmax(24px, 1fr)); }}
      main {{ padding: 20px 12px 48px; }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <h1>两人 {variant_label} Probe 评测汇报</h1>
    <p class="subtitle">这个页面按“人物 - 全轮对话 - probe 评分”组织。全轮对话包含普通 scripted turn 和 targeted probe；总体分数只统计带 <code>tom_dimensions</code> 的 targeted probe。</p>
    <div class="metrics">
      {_metric("Personas", len(probes_by_persona), "本次保留")}
      {_metric("Context turns", extraction.get("kept_turns", len(conversation.get("turns", []))), "供评测上下文")}
      {_metric("Probe turns", probe_count, "真正评分")}
      {_metric("Judge cases", case_count, "probe x " + variant_label)}
      {_metric("Best condition", _best_condition(summary), "LLM judge")}
      {_metric("Judge", method.get("judge_model", "-"), method.get("strictness", "-"))}
    </div>
    <div class="source-note">
      输入：<code>{_esc(_rel(run_dir / "conversation_log_two_person_eval.json"))}</code>；
      主评分：<code>{_esc(_rel(run_dir / "llm_judge_scores_two_person.json"))}</code>；
      规则诊断：<code>{_esc(_rel(run_dir / "automatic_scores_two_person.json"))}</code>。
    </div>
  </section>

  {_summary_section(llm=llm, automatic=automatic)}
  {_condition_section(context_policy=context_policy, run_config=run_config)}
  {_prompt_reference_section(conversation=conversation)}
  {_rubric_section()}
  {persona_sections}
</main>
</body>
</html>
"""


def _summary_section(*, llm: dict[str, Any], automatic: dict[str, Any]) -> str:
    variants = llm.get("summary", {}).get("variants", {})
    automatic_variants = automatic.get("summary", {}).get("variants", {})
    return f"""
  <section class="section">
    <h2>1. 总体结论</h2>
    <div class="summary-grid">
      <div>
        <h3>LLM-as-judge 主评分</h3>
        {_scorebars(variants, "average_tom_score")}
        <table class="compact">
          <thead><tr><th>Condition</th><th>Probe answers</th><th>Valid judge</th><th>Invalid judge</th><th>Avg ToM</th><th>Human review</th><th>Flags</th></tr></thead>
          <tbody>
            {''.join(_variant_summary_row(name, item) for name, item in sorted(variants.items()))}
          </tbody>
        </table>
        {_field_guide()}
      </div>
      <div>
        <h3>规则评测诊断层</h3>
        {_scorebars(automatic_variants, "average_tom_score")}
        <table class="compact">
          <thead><tr><th>Condition</th><th>Probe turns</th><th>Avg ToM</th><th>Ask-repeat</th><th>Alienation</th></tr></thead>
          <tbody>
            {''.join(_auto_summary_row(name, item) for name, item in sorted(automatic_variants.items()))}
          </tbody>
        </table>
      </div>
    </div>
    <h3>LLM judge 维度均分</h3>
    {_dimension_table(llm.get("summary", {}).get("dimension_averages", {}))}
    {_dimension_field_guide()}
    <h3>跨 persona 方差</h3>
    {_persona_variance_table(llm)}
    <p class="source-note">方差口径：同一份报告内，先计算每个 persona 在该 condition 下的平均 LLM judge ToM score，再对这些 persona 均分计算总体方差；不跨实验合并。Norm var = variance / 2500，因为 0-100 分制的最大总体方差是 2500；M0 var reduction 为正，表示比同报告 M0 更均衡。</p>
    <h3>失败类型计数</h3>
    {_failure_table(variants)}
    {_failure_field_guide()}
  </section>
"""


def _field_guide() -> str:
    items = [
        (
            "Condition",
            "实验条件：M0 为普通长期记忆 baseline；M 系列为逐步叠加关系记忆；Z 系列为不拼接 M0 的原子关系记忆条件。",
        ),
        (
            "Probe answers",
            "该条件下被 LLM judge 打分的 probe 回答数；本次两人各 26 个 probe，所以每个条件为 52。",
        ),
        (
            "Valid judge",
            "成功拿到可解析 LLM judge JSON 并进入均分统计的 case 数。",
        ),
        (
            "Invalid judge",
            "API 请求失败或 judge 输出不可解析的 case 数；这些 case 不进入均分，正常正式结果应为 0。",
        ),
        (
            "Avg ToM",
            "该条件所有 probe 回答的平均 ToM 分，百分制；越高表示越能识别隐含意图、情绪、关系期待并正确使用记忆。",
        ),
        (
            "Human review",
            "建议人工复核的 case 数；不是已经人工评过，而是 judge 认为需要保守检查。",
        ),
        (
            "Flags",
            "judge 标出的风险标签总数，例如 memory_misuse、memory_absence、fabrication、alienation。",
        ),
    ]
    cards = "".join(
        f"<div><strong>{_esc(label)}</strong><p>{_esc(text)}</p></div>"
        for label, text in items
    )
    return f'<div class="field-guide">{cards}</div>'


def _dimension_field_guide() -> str:
    items = [
        (
            "alienation_error_rate",
            "陌生化错误控制。2 分表示没有客服化、角色化、过度亲密或要求重讲历史，并能保持稳定关系位置；0 分表示有明显陌生化风险。",
        ),
        (
            "emotional_state_recognition",
            "情绪状态识别。看回答是否识别疲惫、失落、自我怀疑、不安、担心被遗忘等具体状态，并据此调整建议强度。",
        ),
        (
            "hidden_intent_recognition",
            "隐含意图识别。看回答是否接住用户字面问题背后的真实诉求，而不是只回答表面问题。",
        ),
        (
            "memory_misuse",
            "记忆误用控制。看回答是否克制调用记忆，是否区分已知、推测和不可补空白；错误、过期、无关或编造记忆会拉低该项。",
        ),
        (
            "natural_detail_use",
            "自然细节调用。看回答是否只使用必要且可验证的背景细节服务心理理解，而不是机械背日志或堆砌细节。",
        ),
        (
            "shared_context_invocation",
            "共同语境调用。看回答是否自然接上此前形成的共同处理方式或旧线索，而不是把持续事件当第一次出现。",
        ),
    ]
    return _guide_cards(items)


def _failure_field_guide() -> str:
    items = [
        (
            "alienation",
            "陌生化失败：客服化、陌生化、过度角色化、过度亲密，或让用户感觉关系位置不连续。",
        ),
        (
            "fabrication",
            "事实编造：补出用户没有说过、上下文中不可验证的具体信息。",
        ),
        (
            "instruction_only_success",
            "只完成显性指令：回答表面可用，但主要依赖当前问题，没有体现长期记忆或关系连续性。",
        ),
        (
            "memory_absence",
            "记忆缺失：该接上旧语境、旧处理方式或前序事件时没有接上，甚至要求用户重讲背景。",
        ),
        (
            "memory_misuse",
            "记忆误用：调用了错误、过期、无关或不可读记忆，或者把不该确定的内容当成确定事实。",
        ),
        (
            "memory_overuse",
            "记忆过度使用：为了显得记得而机械堆细节、背日志，导致回答不自然或没有服务当前判断。",
        ),
    ]
    return _guide_cards(items)


def _guide_cards(items: list[tuple[str, str]]) -> str:
    cards = "".join(
        f"<div><strong>{_esc(label)}</strong><p>{_esc(text)}</p></div>"
        for label, text in items
    )
    return f'<div class="field-guide">{cards}</div>'


def _condition_section(*, context_policy: dict[str, str], run_config: dict[str, Any]) -> str:
    payload = run_config.get("m0_ld_agent_memory_baseline", {}).get("payload_isolation", {})
    cards = []
    for variant in VARIANTS:
        color = CONDITION_COLORS.get(variant, "#3347b8")
        cards.append(
            f"""
      <div class="standard">
        <h3 style="color:{color}"><span class="condition-dot"></span>{variant}</h3>
        <p>{_esc(context_policy.get(variant, ""))}</p>
        <p class="muted"><code>{_esc(payload.get(variant, ""))}</code></p>
      </div>"""
        )
    return f"""
  <section class="section">
    <h2>2. 条件标准</h2>
    <div class="standard-grid">
      {''.join(cards)}
    </div>
    <div class="source-note">
      控制变量：同一用户输入、同一模型、同一短期上下文策略；只改变长期记忆条件。M 系列使用同轮 M0 base memory；Z 系列为原子关系记忆条件，不拼接 M0。Probe turn 为 read-only，不写回记忆。
    </div>
  </section>
"""


def _prompt_reference_section(*, conversation: dict[str, Any]) -> str:
    relational_variants = tuple(variant for variant in VARIANTS if variant in RELATIONAL_CONDITION_IDS)
    if not relational_variants:
        return ""
    template_cards = "".join(
        _prompt_card(
            title=f"{condition_id} system prompt template",
            body=build_answer_condition_system_prompt_template(condition_id=condition_id),
            open_by_default=condition_id == relational_variants[0],
        )
        for condition_id in relational_variants
    )
    payload_cards = "".join(
        _prompt_card(
            title=f"{condition_id} payload composition template",
            body=build_relational_payload_context_template(condition_id=condition_id),
        )
        for condition_id in relational_variants
    )
    example_cards = "".join(
        _prompt_card(
            title=(
                f"{condition_id} example · {example.get('message_id', '-')}"
                f" · {example.get('topic', '-')}"
            ),
            body=example.get("system_prompt", ""),
            note=(
                "User probe: "
                + str(example.get("user_message", ""))
                + "\nSource detail ids: "
                + (", ".join(example.get("source_detail_ids", [])) or "n/a")
            ),
        )
        for condition_id, example in _prompt_reference_examples(conversation).items()
    )
    return f"""
  <section class="section">
    <h2>3. Relational Prompt Reference</h2>
    <p class="muted">这里记录当前代码中的关系条件回答生成 prompt 参考模板。本节不重新计算本报告里的旧回答分数。</p>
    <h3>System prompt templates</h3>
    <div class="prompt-grid">{template_cards}</div>
    <h3>Relational payload templates</h3>
    <p class="muted">system prompt 中的 memory context 会被下列 payload 填充：M 系列可能包含 M0 普通背景，Z 系列不拼接 M0。</p>
    <div class="prompt-grid">{payload_cards}</div>
    <h3>Examples from this run</h3>
    <p class="muted">示例把当前 prompt 模板与 compact evaluator log 中保留的 memory context 组合展示，用于实现参考和审计阅读；它不表示旧回答已经按新 prompt 重新生成。</p>
    <div class="prompt-grid">{example_cards}</div>
  </section>
"""


def _prompt_card(*, title: str, body: str, note: str = "", open_by_default: bool = False) -> str:
    note_html = f'<pre class="prompt-text">{_esc(note)}</pre>' if note else ""
    return f"""
      <details class="prompt-card" {'open' if open_by_default else ''}>
        <summary>{_esc(title)}</summary>
        {note_html}
        <pre class="prompt-text">{_esc(body)}</pre>
      </details>
"""


def _rubric_section() -> str:
    rows = []
    for name, rubric in TOM_DIMENSION_RUBRIC.items():
        rows.append(
            "<tr>"
            f"<td><code>{_esc(name)}</code><br>{_esc(rubric.get('label', ''))}</td>"
            f"<td>{_esc(rubric.get('score_0', ''))}</td>"
            f"<td>{_esc(rubric.get('score_1', ''))}</td>"
            f"<td>{_esc(rubric.get('score_2', ''))}</td>"
            "</tr>"
        )
    return f"""
  <section class="section">
    <h2>4. 评分标准</h2>
    <table>
      <thead><tr><th>ToM 维度</th><th>0 分</th><th>1 分</th><th>2 分</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </section>
"""


def _persona_section(
    *,
    persona_id: str,
    persona: dict[str, Any],
    all_turns: list[dict[str, Any]],
    probe_turns: list[dict[str, Any]],
    eval_turns: dict[str, dict[str, Any]],
    open_by_default: bool,
) -> str:
    scores = _persona_scores(probe_turns=probe_turns, eval_turns=eval_turns)
    probe_type_counts = Counter(str(turn.get("input", {}).get("probe_type")) for turn in probe_turns)
    dimension_counts = Counter(
        dim
        for turn in probe_turns
        for dim in turn.get("input", {}).get("evaluation_dimension_ids", [])
    )
    probe_cards = "".join(
        _probe_card(turn=turn, eval_turn=eval_turns.get(str(turn.get("source", {}).get("message_id")), {}))
        for turn in sorted(probe_turns, key=lambda item: (item.get("input", {}).get("day", 0), item.get("input", {}).get("message_id", "")))
    )
    return f"""
  <details class="persona" {'open' if open_by_default else ''}>
    <summary>
      <div>
        <h2>{_esc(persona_id)} · {_esc(persona.get('source_archetype_label', ''))}</h2>
        <p class="muted">{_esc(persona.get('occupation', ''))}；{_esc(persona.get('family_structure', ''))}；{_esc(persona.get('economic_condition', ''))}</p>
      </div>
      <div>{_winner_tags(scores)}</div>
    </summary>
    <div class="persona-body">
      <div class="profile">
        {_profile_box("生活阶段", persona.get("life_stage"))}
        {_profile_box("社会支持", persona.get("social_support"))}
        {_profile_box("沟通风格", "、".join(persona.get("communication_style", [])))}
        {_profile_box("记忆相关特征", "、".join(persona.get("memory_relevant_traits", [])))}
      </div>
      <div class="summary-grid">
        <div class="box">
          <b>Probe 日历</b>
          {_probe_calendar(probe_turns, eval_turns)}
        </div>
        <div class="box">
          <b>Persona 内均分</b>
          {_scorebars({variant: {"average_tom_score": score} for variant, score in scores.items()}, "average_tom_score")}
          <div>{_count_tags("Probe type", probe_type_counts)}{_count_tags("D", dimension_counts)}</div>
        </div>
      </div>
      <div class="dialogue-section">
        <h3>全轮对话轨迹</h3>
        <p class="muted">包含该 persona 的全部 {len(all_turns)} 轮：普通 scripted turn 作为上下文展示，targeted probe 同时给出 M0-M3 评分并链接到下方评测详情。</p>
        {_dialogue_timeline(all_turns=all_turns, eval_turns=eval_turns)}
      </div>
      <div class="dialogue-section">
        <h3>Probe 评测详情</h3>
      </div>
      <div class="probe-list">
        {probe_cards}
      </div>
    </div>
  </details>
"""


def _probe_card(*, turn: dict[str, Any], eval_turn: dict[str, Any]) -> str:
    inp = turn.get("input", {})
    message_id = str(inp.get("message_id") or turn.get("source", {}).get("message_id"))
    scores = _variant_scores(eval_turn)
    winners = _winners(scores)
    ground_truth = inp.get("ground_truth", {})
    must = ground_truth.get("must_recognize", {})
    expected_refs = ground_truth.get("expected_references", [])
    state_change = must.get("current_state_change", [])
    variants = eval_turn.get("variants", {})
    source_variants = turn.get("variants", {}) if isinstance(turn.get("variants"), dict) else {}
    answer_rows = "".join(
        _answer_row(
            variant,
            variants.get(variant, {}),
            variant in winners,
            source_variants.get(variant, {}).get("assistant_answer", "")
            if isinstance(source_variants.get(variant), dict)
            else "",
        )
        for variant in VARIANTS
    )
    avg_score = sum(scores.values()) / len(scores) if scores else 0.0
    return f"""
        <article class="probe" id="probe-{_anchor_id(message_id)}">
          <header>
            <div>
              <div class="probe-title">{_esc(message_id)} · Day {_esc(inp.get('day'))} · {_esc(inp.get('topic'))}</div>
              <div>
                {_tag(inp.get('probe_type'), 'blue')}
                {_tag(inp.get('paper_probe_id'), 'gray')}
                {''.join(_tag(dim, 'warn') for dim in inp.get('evaluation_dimension_ids', []))}
                {''.join(_tag(dim, '') for dim in inp.get('tom_dimensions', []))}
              </div>
              <div class="question">{_esc(inp.get('user_message', ''))}</div>
            </div>
            <div>
              <span class="winner">winner: {_esc(', '.join(winners) if winners else '-')}</span>
              <div class="muted">avg {avg_score:.1f}</div>
            </div>
          </header>
          <div class="probe-body">
            <div class="basis">
              <div class="box">
                <b>评测 ground truth / probe 依据</b>
                <p><strong>事件线：</strong>{_esc(ground_truth.get('event_title_zh') or inp.get('topic'))}</p>
                <p><strong>阶段：</strong>{_esc(ground_truth.get('event_stage') or inp.get('event_stage'))}；occurrence {_esc(ground_truth.get('occurrence_index', '-'))}</p>
                <p><strong>前序天：</strong>{_esc(', '.join(map(str, must.get('previous_days', []))) or '-')}</p>
                <p><strong>状态变化：</strong>{_esc('；'.join(map(str, state_change)) or '-')}</p>
                <p><strong>期望引用：</strong>{_esc('；'.join(map(str, expected_refs)) or '-')}</p>
              </div>
              <div class="box">
                <b>M0-M3 分数</b>
                {_case_scorebars(scores)}
              </div>
            </div>
            <div class="answer-grid">
              {answer_rows}
            </div>
          </div>
        </article>
"""


def _answer_row(variant: str, result: dict[str, Any], winner: bool, full_answer: str) -> str:
    color = CONDITION_COLORS[variant]
    failures = result.get("failure_types", [])
    flags = result.get("flags", {})
    active_flags = [key for key, value in flags.items() if value]
    return f"""
      <div class="answer-row" style="border-left-color:{color}">
        <header>
          <div><strong style="color:{color}">{variant}</strong> {'<span class="winner">winner</span>' if winner else ''}</div>
          <div class="score">{float(result.get('tom_score', 0.0)):.1f}</div>
        </header>
        <div class="answer-body">
          <div>{''.join(_tag(item, 'bad') for item in failures) or '<span class="tag gray">no failure type</span>'}</div>
          <p class="reason"><strong>Judge reason：</strong>{_esc(result.get('overall_reason', ''))}</p>
          <p class="muted"><strong>Flags：</strong>{_esc(', '.join(active_flags) if active_flags else '-')}</p>
          {_dimension_detail(result)}
          {_failure_examples(result)}
          <div class="excerpt"><strong>Judge excerpt：</strong>{_esc(result.get('answer_excerpt', ''))}</div>
          <details class="full-answer">
            <summary>完整回答</summary>
            <div class="answer-text">{_esc(full_answer or result.get('answer_excerpt', ''))}</div>
          </details>
        </div>
      </div>
"""


def _dimension_detail(result: dict[str, Any]) -> str:
    dims = result.get("dimension_scores", {})
    if not isinstance(dims, dict) or not dims:
        return """
          <div class="excerpt"><strong>维度分：</strong>本 case 没有返回维度明细。</div>
"""
    rows = []
    for name, item in sorted(dims.items()):
        if not isinstance(item, dict):
            continue
        score = item.get("score", "-")
        max_score = item.get("max_score", 2)
        raw_score = item.get("raw_score")
        raw_note = "" if raw_score in (None, score) else f" raw={raw_score}"
        adjustments = item.get("strict_adjustments", [])
        adjustment_text = ", ".join(map(str, adjustments)) if adjustments else "-"
        rows.append(
            "<tr>"
            f"<td><code>{_esc(name)}</code><br>{_esc(_dimension_label(name))}</td>"
            f"<td><span class=\"dimension-score\">{_esc(score)}/{_esc(max_score)}</span><br><span class=\"muted\">{_esc(raw_note)}</span></td>"
            f"<td>{_esc(item.get('evidence_quote', '-') or '-')}</td>"
            f"<td>{_esc(item.get('reason', '-') or '-')}<br><span class=\"muted\">strict: {_esc(adjustment_text)}</span></td>"
            "</tr>"
        )
    return f"""
          <details class="detail-block" open>
            <summary>维度评分明细</summary>
            <table class="dimension-table">
              <thead><tr><th>维度</th><th>分数</th><th>证据 quote</th><th>判分理由</th></tr></thead>
              <tbody>{''.join(rows)}</tbody>
            </table>
          </details>
"""


def _failure_examples(result: dict[str, Any]) -> str:
    failures = [str(item) for item in result.get("failure_types", []) if item]
    if not failures:
        return """
          <details class="detail-block">
            <summary>缺陷标签与失败例子</summary>
            <div class="failure-examples"><span class="tag gray">本回答没有被 judge 标记缺陷标签。</span></div>
          </details>
"""
    dims = result.get("dimension_scores", {}) if isinstance(result.get("dimension_scores"), dict) else {}
    cards = []
    for failure in failures:
        evidence = _failure_evidence(failure=failure, dims=dims, result=result)
        cards.append(
            f"""
              <div class="failure-example">
                <h4>{_esc(failure)}</h4>
                <p>{_esc(FAILURE_TYPE_EXPLANATIONS.get(failure, "judge 标出的回答缺陷。"))}</p>
                <blockquote>{_esc(evidence)}</blockquote>
                <p class="muted"><strong>判定依据：</strong>{_esc(result.get("overall_reason", "-"))}</p>
              </div>"""
        )
    return f"""
          <details class="detail-block" open>
            <summary>缺陷标签与失败例子</summary>
            <div class="failure-examples">{''.join(cards)}</div>
          </details>
"""


def _failure_evidence(*, failure: str, dims: dict[str, Any], result: dict[str, Any]) -> str:
    preferred_dimensions = {
        "memory_absence": ("shared_context_invocation",),
        "memory_misuse": ("memory_misuse", "natural_detail_use", "shared_context_invocation"),
        "memory_overuse": ("natural_detail_use", "memory_misuse"),
        "fabrication": ("memory_misuse", "natural_detail_use"),
        "alienation": ("alienation_error_rate",),
        "instruction_only_success": ("hidden_intent_recognition", "shared_context_invocation"),
    }
    candidates = list(preferred_dimensions.get(failure, ()))
    low_score_dims = [
        name
        for name, item in dims.items()
        if isinstance(item, dict) and float(item.get("score", 2) or 0) <= 1
    ]
    candidates.extend(low_score_dims)
    for name in candidates:
        item = dims.get(name)
        if isinstance(item, dict) and item.get("evidence_quote"):
            return str(item.get("evidence_quote"))
    return str(result.get("answer_excerpt") or result.get("overall_reason") or "-")


def _dimension_label(name: str) -> str:
    rubric = TOM_DIMENSION_RUBRIC.get(name, {})
    return str(rubric.get("label") or name)


def _dialogue_timeline(
    *, all_turns: list[dict[str, Any]], eval_turns: dict[str, dict[str, Any]]
) -> str:
    turns_by_day: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for turn in all_turns:
        day = int(turn.get("input", {}).get("day") or 0)
        turns_by_day[day].append(turn)

    blocks = []
    for day, turns in sorted(turns_by_day.items()):
        ordered = sorted(
            turns,
            key=lambda item: (
                item.get("input", {}).get("within_day_index") or 0,
                str(item.get("input", {}).get("message_id") or ""),
            ),
        )
        probe_count = sum(1 for turn in ordered if _is_probe_turn(turn))
        open_attr = " open" if probe_count else ""
        turn_cards = "".join(_dialogue_turn_card(turn=turn, eval_turns=eval_turns) for turn in ordered)
        blocks.append(
            f"""
          <details class="day-block"{open_attr}>
            <summary>Day {_esc(day)} · {len(ordered)} turns · {probe_count} probe</summary>
            <div class="day-turns">{turn_cards}</div>
          </details>"""
        )
    return "".join(blocks)


def _dialogue_turn_card(*, turn: dict[str, Any], eval_turns: dict[str, dict[str, Any]]) -> str:
    inp = turn.get("input", {})
    message_id = str(inp.get("message_id") or turn.get("source", {}).get("message_id") or "")
    is_probe = _is_probe_turn(turn)
    eval_turn = eval_turns.get(str(turn.get("source", {}).get("message_id") or message_id), {}) if is_probe else {}
    scores = _variant_scores(eval_turn) if is_probe else {}
    variants = turn.get("variants", {}) if isinstance(turn.get("variants"), dict) else {}
    topic = inp.get("topic_zh") or inp.get("topic") or ""
    answer_cards = "".join(
        _conversation_answer_card(
            variant=variant,
            answer=variants.get(variant, {}).get("assistant_answer", "")
            if isinstance(variants.get(variant), dict)
            else "",
            score=scores.get(variant) if is_probe else None,
        )
        for variant in VARIANTS
    )
    tags = [
        _tag(inp.get("turn_type"), "blue" if is_probe else "gray"),
        _tag(inp.get("event_stage"), "gray"),
        _tag(inp.get("probe_type"), "warn") if is_probe else "",
    ]
    eval_link = (
        f'<a class="eval-link" href="#probe-{_anchor_id(message_id)}">查看评测</a>'
        if is_probe
        else ""
    )
    scorebars = f'<div class="turn-scorebars">{_case_scorebars(scores)}</div>' if is_probe else ""
    return f"""
              <article class="turn-card {'probe-turn' if is_probe else ''}" id="dialogue-{_anchor_id(message_id)}">
                <div class="turn-head">
                  <div>
                    <strong>{_esc(message_id)}</strong> · {_esc(topic)}
                    <div>{''.join(tags)}</div>
                  </div>
                  <div>{eval_link}</div>
                </div>
                <div class="turn-body">
                  <div class="user-msg">{_esc(inp.get("user_message", ""))}</div>
                  {scorebars}
                  <div class="assistant-variants">{answer_cards}</div>
                </div>
              </article>"""


def _conversation_answer_card(*, variant: str, answer: str, score: float | None) -> str:
    color = CONDITION_COLORS[variant]
    score_text = "" if score is None else f" · {score:.1f}"
    return f"""
                    <details class="assistant-answer">
                      <summary style="color:{color}">{_esc(variant)}{_esc(score_text)}</summary>
                      <div class="answer-text">{_esc(answer or "-")}</div>
                    </details>"""


def _is_probe_turn(turn: dict[str, Any]) -> bool:
    return bool(turn.get("input", {}).get("tom_dimensions"))


def _variant_summary_row(name: str, item: dict[str, Any]) -> str:
    return (
        f"<tr><td><strong>{_esc(name)}</strong></td>"
        f"<td>{_esc(item.get('turn_count'))}</td>"
        f"<td>{_esc(item.get('valid_judge_count', item.get('turn_count')))}</td>"
        f"<td>{_esc(item.get('invalid_judge_count', 0))}</td>"
        f"<td>{float(item.get('average_tom_score', 0)):.2f}</td>"
        f"<td>{_esc(item.get('needs_human_review_count'))}</td>"
        f"<td>{_esc(item.get('flag_count'))}</td></tr>"
    )


def _auto_summary_row(name: str, item: dict[str, Any]) -> str:
    return (
        f"<tr><td><strong>{_esc(name)}</strong></td>"
        f"<td>{_esc(item.get('turn_count'))}</td>"
        f"<td>{float(item.get('average_tom_score', 0)):.2f}</td>"
        f"<td>{_esc(item.get('ask_repeat_error_count'))}</td>"
        f"<td>{_esc(item.get('alienation_error_count'))}</td></tr>"
    )


def _dimension_table(data: dict[str, dict[str, Any]]) -> str:
    dimensions = sorted({name for values in data.values() for name in values})
    rows = []
    for variant in sorted(data):
        cells = "".join(f"<td>{float(data[variant].get(name, 0)):.2f}</td>" for name in dimensions)
        rows.append(f"<tr><td><strong>{_esc(variant)}</strong></td>{cells}</tr>")
    head = "".join(f"<th>{_esc(name)}</th>" for name in dimensions)
    return f"<table class=\"compact\"><thead><tr><th>Condition</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _failure_table(variants: dict[str, dict[str, Any]]) -> str:
    failures = sorted({name for item in variants.values() for name in item.get("failure_type_counts", {})})
    rows = []
    for variant, item in sorted(variants.items()):
        counts = item.get("failure_type_counts", {})
        cells = "".join(f"<td>{_esc(counts.get(name, 0))}</td>" for name in failures)
        rows.append(f"<tr><td><strong>{_esc(variant)}</strong></td>{cells}</tr>")
    head = "".join(f"<th>{_esc(name)}</th>" for name in failures)
    return f"<table class=\"compact\"><thead><tr><th>Condition</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _persona_variance_table(llm: dict[str, Any]) -> str:
    stats = _persona_score_stats(llm)
    rows = []
    for variant in VARIANTS:
        item = stats.get(variant, {})
        persona_means = item.get("persona_means", {})
        means_text = "; ".join(
            f"{pid}={float(score):.2f}"
            for pid, score in sorted(persona_means.items())
        )
        rows.append(
            "<tr>"
            f"<td><strong>{_esc(variant)}</strong></td>"
            f"<td>{_esc(item.get('persona_count', 0))}</td>"
            f"<td>{_esc(means_text or '-')}</td>"
            f"<td>{float(item.get('mean', 0.0)):.2f}</td>"
            f"<td>{float(item.get('variance', 0.0)):.2f}</td>"
            f"<td>{float(item.get('stddev', 0.0)):.2f}</td>"
            f"<td>{float(item.get('range', 0.0)):.2f}</td>"
            f"<td>{float(item.get('cv', 0.0)):.3f}</td>"
            f"<td>{float(item.get('norm_variance', 0.0)):.3f}</td>"
            f"<td>{float(item.get('norm_range', 0.0)):.3f}</td>"
            f"<td>{float(item.get('m0_variance_reduction', 0.0)):.1%}</td>"
            "</tr>"
        )
    return (
        '<table class="compact"><thead><tr><th>Condition</th><th>Persona count</th>'
        "<th>Persona means</th><th>Mean</th><th>Variance</th><th>Std dev</th>"
        "<th>Range</th><th>CV</th><th>Norm var</th><th>Norm range</th>"
        f"<th>M0 var reduction</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _persona_score_stats(llm: dict[str, Any]) -> dict[str, dict[str, Any]]:
    scores_by_variant_persona: dict[str, dict[str, list[float]]] = {
        variant: defaultdict(list) for variant in VARIANTS
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
        for variant in VARIANTS:
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


def _scorebars(variants: dict[str, dict[str, Any]], key: str) -> str:
    rows = []
    for variant, item in sorted(variants.items()):
        score = float(item.get(key, 0.0))
        rows.append(_scorebar(variant, score))
    return "".join(rows)


def _case_scorebars(scores: dict[str, float]) -> str:
    return "".join(_scorebar(variant, scores.get(variant, 0.0)) for variant in VARIANTS)


def _scorebar(variant: str, score: float) -> str:
    color = CONDITION_COLORS.get(variant, "#3347b8")
    return f"""
      <div class="scorebar">
        <strong style="color:{color}">{_esc(variant)}</strong>
        <span class="bar"><i style="width:{max(0, min(score, 100)):.1f}%; background:{color}"></i></span>
        <span>{score:.1f}</span>
      </div>"""


def _probe_calendar(probe_turns: list[dict[str, Any]], eval_turns: dict[str, dict[str, Any]]) -> str:
    days = {}
    for turn in probe_turns:
        day = int(turn.get("input", {}).get("day") or 0)
        eval_turn = eval_turns.get(str(turn.get("source", {}).get("message_id")), {})
        scores = _variant_scores(eval_turn)
        avg_score = sum(scores.values()) / len(scores) if scores else 100
        days[day] = avg_score
    cells = []
    for day in range(1, 31):
        if day in days:
            cls = "day-cell probed low" if days[day] < 35 else "day-cell probed"
            cells.append(f'<div class="{cls}" title="avg {days[day]:.1f}">{day}<br>{days[day]:.0f}</div>')
        else:
            cells.append(f'<div class="day-cell">{day}</div>')
    return '<div class="calendar">' + "".join(cells) + "</div>"


def _persona_scores(
    *, probe_turns: list[dict[str, Any]], eval_turns: dict[str, dict[str, Any]]
) -> dict[str, float]:
    values: dict[str, list[float]] = {variant: [] for variant in VARIANTS}
    for turn in probe_turns:
        eval_turn = eval_turns.get(str(turn.get("source", {}).get("message_id")), {})
        for variant, score in _variant_scores(eval_turn).items():
            values[variant].append(score)
    return {
        variant: (sum(scores) / len(scores) if scores else 0.0)
        for variant, scores in values.items()
    }


def _variant_scores(eval_turn: dict[str, Any]) -> dict[str, float]:
    variants = eval_turn.get("variants", {}) if isinstance(eval_turn, dict) else {}
    return {
        variant: float(variants.get(variant, {}).get("tom_score", 0.0))
        for variant in VARIANTS
    }


def _winners(scores: dict[str, float]) -> list[str]:
    if not scores:
        return []
    best = max(scores.values())
    return [variant for variant, score in scores.items() if score == best]


def _winner_tags(scores: dict[str, float]) -> str:
    winners = _winners(scores)
    return "".join(f'<span class="winner">{_esc(item)} {scores[item]:.1f}</span> ' for item in winners)


def _count_tags(label: str, counts: Counter) -> str:
    if not counts:
        return ""
    parts = [f'<span class="tag gray">{_esc(label)} { _esc(k) }: {_esc(v)}</span>' for k, v in sorted(counts.items())]
    return "".join(parts)


def _profile_box(label: str, value: Any) -> str:
    return f'<div class="box"><b>{_esc(label)}</b><p>{_esc(value or "-")}</p></div>'


def _metric(label: str, value: Any, note: Any) -> str:
    return f'<div class="metric"><span>{_esc(label)}</span><b>{_esc(value)}</b><span>{_esc(note)}</span></div>'


def _tag(value: Any, tone: str = "") -> str:
    if value in (None, "", []):
        return ""
    cls = f"tag {tone}".strip()
    return f'<span class="{cls}">{_esc(value)}</span>'


def _best_condition(summary: dict[str, Any]) -> str:
    variants = summary.get("variants", {})
    if not variants:
        return "-"
    best = max(variants, key=lambda item: float(variants[item].get("average_tom_score", 0.0)))
    return f"{best} {float(variants[best].get('average_tom_score', 0.0)):.1f}"


def _first_context_policy(conversation: dict[str, Any]) -> dict[str, str]:
    for turn in conversation.get("turns", []):
        policy = turn.get("conversation_context_policy")
        if isinstance(policy, dict):
            return {str(key): str(value) for key, value in policy.items()}
    return {}


def _prompt_reference_examples(conversation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    relational_variants = tuple(variant for variant in VARIANTS if variant in RELATIONAL_CONDITION_IDS)
    examples: dict[str, dict[str, Any]] = {}
    for turn in conversation.get("turns", []):
        if not isinstance(turn, dict) or not turn.get("input", {}).get("tom_dimensions"):
            continue
        variants = turn.get("variants", {})
        if not isinstance(variants, dict):
            continue
        input_payload = turn.get("input", {})
        for condition_id in relational_variants:
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
        if all(condition_id in examples for condition_id in relational_variants):
            break
    return examples


def _persona_id(turn: dict[str, Any]) -> str:
    message_id = str(turn.get("source", {}).get("message_id") or turn.get("input", {}).get("message_id") or "")
    return message_id.split("_", 1)[0] if "_" in message_id else message_id


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _report_variants(
    *,
    llm: dict[str, Any],
    conversation: dict[str, Any],
    run_config: dict[str, Any],
) -> tuple[str, ...]:
    configured = [str(item) for item in run_config.get("conditions", []) if item]
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
    return ("M0", "M1", "M2", "M3")


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _anchor_id(value: Any) -> str:
    text = str(value)
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in text)


if __name__ == "__main__":
    raise SystemExit(main())
