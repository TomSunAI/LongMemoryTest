#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DEFAULT_OUTPUT = REPO_ROOT / "docs/demo5_tau_i_probe_integrated_report.html"
DEFAULT_TAU_CONTRACT = DEFAULT_BASE_DIR / "tau_contract.json"
AAAI_PAPER_PATH = str(REPO_ROOT / "docs/references/aaai2027_remem_re.pdf")
DOCX_PATH = "/Users/tom/Desktop/Archetype_Guided_Persona_Event_Sampling_Implementation.docx"


STAGE_CN = {
    "initial": "初始提出",
    "recurrence": "再次出现",
    "turning_point": "转折判断",
    "partial_resolution": "部分处理",
    "reflection": "回看总结",
}

PAPER_PROBE_LABELS = {
    "P1": "Current Understanding / 当前理解",
    "P2": "State Transformation / 状态变化识别",
    "P3": "Memory Invocation / 共享记忆调用",
    "P4": "Natural Detail Use / 自然细节使用",
    "P5": "Relational Boundary / 关系边界",
    "P6": "Alienation Avoidance / 陌生化避免",
}

DIMENSION_LABELS = {
    "D1": "Situated Intent Understanding / 情境化意图理解",
    "D2": "Emotional-State Attunement / 情绪与状态调谐",
    "D3": "Contextual Specificity / 上下文具体性",
    "D4": "Continuity-Sensitive Response / 连续性敏感回应",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate integrated demo5 tau/I/probe HTML report.")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    parser.add_argument("--timeline", type=Path, default=None)
    parser.add_argument("--probe-plan", type=Path, default=None)
    parser.add_argument("--daily-interactions", type=Path, default=None)
    parser.add_argument("--tau-contract", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timeline_path = args.timeline or (args.base_dir / "timeline.json")
    probe_plan_path = args.probe_plan or (args.base_dir / "probe_plan.json")
    daily_path = args.daily_interactions or (args.base_dir / "daily_interaction_units.json")
    tau_path = args.tau_contract or DEFAULT_TAU_CONTRACT
    timeline = _load_json(timeline_path)
    probe_plan = _load_json(probe_plan_path)
    daily = _load_json(daily_path)
    tau_contract = _load_json(tau_path)
    html_text = render_report(
        tau_contract=tau_contract,
        timeline=timeline,
        probe_plan=probe_plan,
        daily=daily,
        tau_path=tau_path,
        timeline_path=timeline_path,
        probe_plan_path=probe_plan_path,
        daily_path=daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(
    *,
    tau_contract: dict[str, Any],
    timeline: dict[str, Any],
    probe_plan: dict[str, Any],
    daily: dict[str, Any],
    tau_path: Path,
    timeline_path: Path,
    probe_plan_path: Path,
    daily_path: Path,
) -> str:
    tau_summary = tau_contract.get("summary", {})
    timeline_summary = timeline.get("summary", {})
    probe_summary = probe_plan.get("summary", {})
    daily_summary = daily.get("summary", {})
    units = _all_units(daily)
    probed_units = [unit for unit in units if unit.get("probe_links")]
    unprobed_units = [unit for unit in units if not unit.get("probe_links")]
    first_unit = units[0] if units else None
    first_probed = probed_units[0] if probed_units else first_unit
    first_parallel_day = _first_parallel_day(daily)
    bindings = _binding_rows(daily)
    persona_sections = "".join(_persona_section(persona) for persona in daily.get("personas", []) if isinstance(persona, dict))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Demo5 tau 总览报告</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #5b6670;
      --line: #d8e0e7;
      --soft: #f6f8fb;
      --chip: #eef4ff;
      --accent: #1558d6;
      --ok: #1f7a45;
      --ok-bg: #edf7f0;
      --warn: #8a4b00;
      --warn-bg: #fff7e8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #fff;
      font: 15px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 34px 26px 72px; }}
    h1, h2, h3 {{ margin: 0; line-height: 1.25; }}
    h1 {{ font-size: 30px; }}
    h2 {{
      margin-top: 34px;
      padding-top: 22px;
      border-top: 1px solid var(--line);
      font-size: 22px;
    }}
    h3 {{ margin-top: 16px; font-size: 17px; }}
    p {{ margin: 8px 0; }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: #edf1f5;
      padding: 1px 4px;
      border-radius: 4px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      margin: 14px 0 20px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 9px;
      vertical-align: top;
      word-break: break-word;
    }}
    th {{ background: var(--soft); text-align: left; }}
    ol {{ margin: 10px 0 18px; padding-left: 24px; }}
    li {{ margin: 7px 0; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      background: #fff;
    }}
    .metric strong {{ display: block; font-size: 22px; line-height: 1.2; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .callout {{
      margin: 16px 0;
      padding: 13px 15px;
      background: var(--soft);
      border-left: 4px solid var(--accent);
    }}
    .ok {{
      margin: 16px 0;
      padding: 13px 15px;
      background: var(--ok-bg);
      border-left: 4px solid var(--ok);
    }}
    .warning {{
      margin: 16px 0;
      padding: 13px 15px;
      background: var(--warn-bg);
      border-left: 4px solid var(--warn);
    }}
    .formula {{
      margin: 10px 0 6px;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .tag {{
      display: inline-block;
      margin: 2px 4px 2px 0;
      padding: 2px 7px;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid #d6e5ff;
      font-size: 12px;
    }}
    .code-block {{
      margin: 12px 0 18px;
      padding: 12px 14px;
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f7f9fc;
      font: 13px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre-wrap;
    }}
    .narrow td:first-child {{ width: 23%; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .example-box {{
      margin: 14px 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }}
    .example-head {{
      padding: 10px 12px;
      background: var(--soft);
      border-bottom: 1px solid var(--line);
      font-weight: 700;
    }}
    .example-body {{ padding: 12px; }}
    .question {{
      margin: 8px 0 10px;
      padding: 12px 14px;
      border-left: 4px solid var(--accent);
      background: #f7f9fc;
      font-size: 16px;
      line-height: 1.7;
    }}
    details.persona {{
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    details.persona > summary {{
      cursor: pointer;
      padding: 12px 14px;
      font-weight: 700;
      background: var(--soft);
    }}
    .details-body {{ padding: 0 14px 14px; }}
    .parallel-row td {{ background: #fffaf2; }}
    @media (max-width: 920px) {{
      main {{ padding: 24px 14px 52px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .two-col {{ grid-template-columns: 1fr; }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>5 人 Demo：tau 总览报告</h1>
  <p class="meta">整合输入：<code>{_esc(_rel(tau_path))}</code>、<code>{_esc(_rel(timeline_path))}</code>、<code>{_esc(_rel(probe_plan_path))}</code>、<code>{_esc(_rel(daily_path))}</code></p>
  <p class="meta">依据：<code>{_esc(AAAI_PAPER_PATH)}</code> 的 <code>tau=(z,T,L,I,P)</code>；工程约束来自 <code>{_esc(DOCX_PATH)}</code> 与当前 JSON 池。</p>

  {_status_block(tau_contract.get("validation", {}), timeline.get("validation", {}), probe_plan.get("validation", {}), daily.get("validation", {}))}

  <section class="grid">
    {_metric("z persona", tau_summary.get("persona_count"), "人物合同")}
    {_metric("T themes", tau_summary.get("theme_count"), "长期主题")}
    {_metric("L lines", tau_summary.get("event_line_count"), "事件线")}
    {_metric("I units", tau_summary.get("interaction_unit_count"), "互动单元")}
    {_metric("P probes", tau_summary.get("targeted_probe_count"), "评测问题")}
    {_metric("Bindings", tau_summary.get("message_binding_count"), "消息绑定")}
    {_metric("Active days", tau_summary.get("active_day_count"), "有事件天")}
    {_metric("Parallel days", tau_summary.get("parallel_day_count"), "同日多事件")}
    {_metric("Median events/day", timeline_summary.get("daily_event_count_median_calendar"), "日历中位数")}
    {_metric("M0-M3", "ready", "接口已打通")}
    {_metric("P3b LLM", "candidate", "候选层保留 I")}
    {_metric("Generation", "not run", "本报告不生成")}
  </section>

  <h2>0. Tau 总览</h2>
  {_tau_overview_section(tau_contract, timeline, probe_plan, daily)}

  <h2>1. 总体结论</h2>
  <div class="callout">
    当前 5 人 demo 已经形成同一条链路：<code>tau_contract.json</code> 作为总合同；
    <code>timeline.json</code> 给出日历和事件 occurrence；
    <code>daily_interaction_units.json</code> 把每个 occurrence 变成可执行的 <code>I</code>；
    <code>probe_plan.json</code> 生成 targeted relational probes，并通过 <code>insert_after_message_id</code> 绑定到具体 <code>I unit</code> 后面。
    最新修改已把 tau 和 M0/M1/M2/M3 payload 接口打通，并增加 P3b LLM 自然化候选层；但本报告没有执行生成脚本。
  </div>
  {_source_table(tau_path, timeline_path, probe_plan_path, daily_path, tau_contract, timeline, probe_plan, daily)}

  <h2>2. 理论框架：tau=(z,T,L,I,P)</h2>
  {_tau_section(timeline_summary, daily_summary, probe_summary)}

  <h2>3. Timeline：T/L 的结构</h2>
  {_timeline_section(timeline)}

  <h2>4. I：Daily Interaction Units</h2>
  {_i_generation_section(daily_summary)}
  {_i_examples(first_unit, first_probed, first_parallel_day)}

  <h2>5. Probe：生成逻辑与模板</h2>
  {_probe_section(probe_plan)}

  <h2>6. I 与 Probe 的绑定关系</h2>
  {_binding_section(bindings, units, unprobed_units)}

  <h2>7. 并行事件处理</h2>
  {_parallel_section(first_parallel_day)}

  <h2>8. 非 LLM 生成边界</h2>
  {_non_llm_section()}

  <h2>9. Tau 到 M0-M3 与 P3b 接口</h2>
  {_tau_interface_section(tau_contract)}

  <h2>10. 5 人明细</h2>
  {persona_sections}
</main>
</body>
</html>
"""


def _source_table(
    tau_path: Path,
    timeline_path: Path,
    probe_plan_path: Path,
    daily_path: Path,
    tau_contract: dict[str, Any],
    timeline: dict[str, Any],
    probe_plan: dict[str, Any],
    daily: dict[str, Any],
) -> str:
    tau_summary = tau_contract.get("summary", {})
    timeline_summary = timeline.get("summary", {})
    timeline_config = timeline.get("construction_config", {})
    probe_summary = probe_plan.get("summary", {})
    daily_summary = daily.get("summary", {})
    rows = [
        ("论文依据", AAAI_PAPER_PATH, "ReMem-RE、tau=(z,T,L,I,P)、P1-P6 probes、D1-D4。"),
        (
            "工程规范",
            DOCX_PATH,
            (
                "5 人、30 天、产物落盘；当前按本轮修正使用高密度 timeline："
                f"每天 0-{timeline_config.get('max_events_per_active_day')} 个事件，"
                f"中位数 {timeline_summary.get('daily_event_count_median_calendar')}。"
            ),
        ),
        ("Tau contract", _rel(tau_path), f"总合同：z={tau_summary.get('persona_count')}、T={tau_summary.get('theme_count')}、L={tau_summary.get('event_line_count')}、I={tau_summary.get('interaction_unit_count')}、P={tau_summary.get('targeted_probe_count')}、bindings={tau_summary.get('message_binding_count')}。"),
        ("Timeline", _rel(timeline_path), f"{timeline_summary.get('event_occurrence_total')} 个 event occurrences；event_occurrences[]、并行事件、probe_insertions 回写。"),
        ("Probe plan", _rel(probe_plan_path), f"{probe_summary.get('probe_count')} 条 targeted relational probes。"),
        ("I units", _rel(daily_path), f"{daily_summary.get('interaction_unit_count')} 个 daily interaction units，含问题、约束、边界、probe links。"),
    ]
    return _table(["层级", "文件", "作用"], rows)


def _tau_overview_section(
    tau_contract: dict[str, Any],
    timeline: dict[str, Any],
    probe_plan: dict[str, Any],
    daily: dict[str, Any],
) -> str:
    tau_summary = tau_contract.get("summary", {})
    timeline_summary = timeline.get("summary", {})
    daily_summary = daily.get("summary", {})
    probe_summary = probe_plan.get("summary", {})
    scope = tau_contract.get("construction_scope", {})
    scope_rows = [
        ("from_sampled_personas", scope.get("from_sampled_personas"), "z 的来源。"),
        ("from_accepted_event_sets", scope.get("from_accepted_event_sets"), "T 的来源。"),
        ("from_event_lines_batch", scope.get("from_event_lines_batch"), "L 的来源。"),
        ("from_timeline", scope.get("from_timeline"), "occurrence / day / parallel events 的来源。"),
        ("from_daily_interaction_units", scope.get("from_daily_interaction_units"), "I 的来源。"),
        ("from_probe_plan", scope.get("from_probe_plan"), "P 的来源。"),
        ("llm_generation_used", scope.get("llm_generation_used"), "当前 tau 合同本身未使用 LLM 生成。"),
    ]
    component_rows = [
        ("z", tau_summary.get("persona_count"), "人物合同", "每个 persona 的稳定画像、长期目标、沟通风格、敏感边界。"),
        ("T", tau_summary.get("theme_count"), "长期主题", "由 persona-event compatibility 采样出的 accepted event categories。"),
        ("L", tau_summary.get("event_line_count"), "事件线", "同一主题跨天推进的 recurring event lines，包含 stage sequence 和关系记忆目标。"),
        ("I", tau_summary.get("interaction_unit_count"), "互动单元", "每个 active occurrence 对应一个用户可执行问题；不是只有 probe 才有 I。"),
        ("P", tau_summary.get("targeted_probe_count"), "评测 probe", "只读评测问题，插在部分 I 后面。"),
        ("message_bindings", tau_summary.get("message_binding_count"), "运行绑定", "把 I/P message_id 映射到 persona/day/event_line/stage/interaction_unit。"),
    ]
    pipeline_rows = [
        (
            "P0 Persona/Event",
            "sampled_personas.json + accepted_persona_event_sets.json",
            "生成 z 和 T 的候选基础。",
            "已完成，非本报告新生成。",
        ),
        (
            "P1 Event Lines / Timeline",
            "event_lines_batch.json + timeline.json",
            f"形成 L 和 {timeline_summary.get('event_occurrence_total')} 个 occurrence；每日 0-5 个事件，中位数 {timeline_summary.get('daily_event_count_median_calendar')}。",
            "已完成，validation=pass。",
        ),
        (
            "P2 Probe",
            "probe_plan.json",
            f"生成 {probe_summary.get('probe_count')} 条 P；D1-D4 primary coverage={_format_dimension_counts(probe_summary.get('primary_dimension_counts', {}))}。",
            "已完成，read-only。",
        ),
        (
            "P3a I Units",
            "daily_interaction_units.json",
            f"生成 {daily_summary.get('interaction_unit_count')} 个 I；其中 {tau_summary.get('probed_interaction_unit_count')} 个有 probe，{tau_summary.get('unprobed_interaction_unit_count')} 个无 probe。",
            "已完成，规则模板。",
        ),
        (
            "P4 Tau Contract",
            "tau_contract.json",
            f"总合同聚合 z/T/L/I/P 和 {tau_summary.get('message_binding_count')} 条 message binding。",
            "已完成，作为后续运行入口。",
        ),
        (
            "M0-M3 Adapter",
            "generate_memory_conditions_from_tau_contract(...)",
            "把 tau 适配为 M0/M1/M2/M3 payload 接口。",
            "代码已打通；本报告未运行生成脚本。",
        ),
        (
            "P3b Naturalization",
            "interaction_naturalizer.py",
            "LLM 只能基于 I unit 做自然话术候选，不覆盖 I。",
            "代码已打通；本报告未调用 LLM。",
        ),
    ]
    conclusion_rows = [
        ("当前能证明什么", "5 人、30 天、440 个 I、127 个 P、567 个 message binding 已经可形成完整 tau 合同。"),
        ("当前还不是最终实验什么", "尚未把 tau-route memory_conditions 正式生成出来，也尚未执行 M0/M1/M2/M3 runner。"),
        ("最重要的结构原则", "I 是结构化真值；P3b 自然化只是候选文本层；M0-M3 是同一个 tau 坐标下的记忆条件接口。"),
    ]
    return f"""
  <div class="callout">
    <strong>一句话：</strong>当前报告展示的是一个可审计的 tau 合同，而不是一次自然对话运行结果。
    它把人物、长期主题、事件线、互动单元和 probe 统一到 <code>tau=(z,T,L,I,P)</code>，
    并说明下一步如何接入 M0/M1/M2/M3 与 P3b LLM 自然化。
  </div>
  <h3>0.1 tau 合同组件</h3>
  {_table(["组件", "数量", "当前名称", "作用"], component_rows)}
  <h3>0.2 生成链路总览</h3>
  {_table(["阶段", "产物", "作用", "当前状态"], pipeline_rows)}
  <h3>0.3 construction_scope</h3>
  {_table(["字段", "值", "解释"], scope_rows)}
  <h3>0.4 当前判断</h3>
  {_table(["问题", "结论"], conclusion_rows)}
"""


def _tau_section(
    timeline_summary: dict[str, Any],
    daily_summary: dict[str, Any],
    probe_summary: dict[str, Any],
) -> str:
    rows = [
        ("z", "sampled user persona", "5 个 persona，来自 persona archetype JSON，经 P0 采样。"),
        ("T", "accepted event categories", f"长期事件主题来自 persona-event compatibility 后的 accepted event categories；active days={daily_summary.get('active_day_total')}。"),
        ("L", "recurring event lines", f"事件线总数={timeline_summary.get('event_line_count')}；每条线阶段单调推进。"),
        ("I", "daily interaction units", f"{daily_summary.get('interaction_unit_count')} 个 I；用户具体问题在 scripted_opening.user_message。"),
        ("P", "inserted targeted relational probes", f"{probe_summary.get('probe_count')} 条 probe；通过 insert_after_message_id 绑定到 I。"),
    ]
    return f"""
  <div class="formula">tau = (z, T, L, I, P)</div>
  {_table(["组件", "论文含义", "当前 demo 落地"], rows, class_name="narrow")}
  <div class="callout">
    关键区别：<strong>I 是正常用户互动</strong>，也就是用户当天具体问 agent 的问题；
    <strong>P 是评测 probe</strong>，插在 I 后面，用来测试 agent 是否能承接关系记忆、状态变化和边界。
  </div>
"""


def _timeline_section(timeline: dict[str, Any]) -> str:
    summary = timeline.get("summary", {})
    config = timeline.get("construction_config", {})
    source_rows = [
        (
            "最高研究来源",
            AAAI_PAPER_PATH,
            "How Agents Remember the Relationship: Evaluating Relational Memory；提出 ReMem-RE，把长期互动轨迹表示为 tau=(z,T,L,I,P)。",
            "给出 T=accepted event categories、L=recurring event lines、I=daily interaction units、P=targeted relational probes 的正式研究口径。",
        ),
        (
            "理论动机",
            "Mutual Theory of Mind / relational expectation",
            "用户在长期互动中不只提出任务，也期待 agent 按共享历史、熟悉回应规范、状态变化和边界来回应。",
            "Timeline 的作用是让这种关系期待先形成、延迟、再被 probe 评测。",
        ),
        (
            "工程规范来源",
            DOCX_PATH,
            (
                "原始工程要求规定第一阶段 5 人、30 天和中间产物；当前已按本轮讨论改为"
                f"每日 0-{config.get('max_events_per_active_day')} 个事件、中位数 "
                f"{summary.get('daily_event_count_median_calendar')} 的高密度排布。"
            ),
            "给出规模和验收方向；具体排布算法由当前工程实现负责。",
        ),
        (
            "当前实现来源",
            "src/long_memory_test/sampling/timeline_constructor.py",
            "用固定随机种子、occurrence round、active day 打包、并行事件和校验规则落地。",
            "这是我们为可复现、可审计和可扩展做的工程实现，不是论文逐字规定。",
        ),
    ]
    definition_rows = [
        (
            "T / event theme",
            "长期事件主题集合",
            f"由 accepted_persona_event_sets.json 提供；当前 5 人合计 {summary.get('event_line_count')} 条 accepted event categories / event lines。",
            "T 不是最终聊天内容，而是长期生活/工作领域中的可持续 concern。",
        ),
        (
            "L / event line",
            "持续事件线",
            "由 event_lines_batch.json 提供，每条线有 stage_sequence、surface_event 种子、allowed facts、latent concern。",
            "L 不是一次 topic 提及，而是同一 concern 跨多天演化的轨迹。",
        ),
        (
            "event occurrence",
            "L 到 I 的中间节点",
            "某条 L 在某一天第 N 次出现，带 occurrence_index、stage_index、interaction_unit_id。",
            "这是工程概念；论文不单独命名，但它让 L 可以落到具体 I。",
        ),
        (
            "active day",
            "日历容器",
            f"30 天里真正承载 occurrence 的日期；同一天可含 1-{config.get('max_events_per_active_day')} 条 occurrence，0 条为 inactive day。",
            "day 不是事件本身；真实分析优先读 event_occurrences[]。",
        ),
        (
            "I unit",
            "可执行互动单元",
            "每个 occurrence 后续生成一个 I，包含用户具体问题、follow-up 边界、scene boundary。",
            "Timeline 的最终目的不是展示日期，而是给 I/P 提供可追踪坐标。",
        ),
    ]
    algorithm_rows = [
        (
            "1. 读取 P1 event lines",
            "从 event_lines_batch.json 读取 persona_ref 和 event_lines[]。",
            "每条 event line 必须已有 stage_sequence；没有 stage_sequence 不进入 timeline。",
            "timeline_constructor.py:168-180, 523-527",
        ),
        (
            "2. 给每条 L 分配出现次数",
            f"每条 event line 至少 {config.get('event_line_occurrences_min')} 次、最多 {config.get('event_line_occurrences_max')} 次；总 active sessions 必须落在 {config.get('active_sessions_min')}-{config.get('active_sessions_max')}。",
            "下界还要满足 probe_candidate_min_per_persona，避免后续 probe 候选不足；上界受事件线容量和 30 天日历容量限制。",
            "timeline_constructor.py:239-290",
        ),
        (
            "3. 生成 occurrence tokens",
            "一个 token = 某条 event line 的第 N 次出现。",
            "按 occurrence round 交错：先排所有第 1 次，再排所有第 2 次，再排第 3 次；每轮内部固定随机种子打散。",
            "timeline_constructor.py:293-316",
        ),
        (
            "4. 计算 active day 数",
            "active session 是 occurrence 数，不再等同于日历天。",
            f"当前使用固定每日分布 {_format_histogram(config.get('daily_event_count_distribution', {}))}，每人 occurrence 总数固定为 {summary.get('active_sessions_per_persona_min')}。",
            "timeline_constructor.py:347-385",
        ),
        (
            "5. 把每日事件数铺到 30 天",
            "先把 30 天的事件数分布洗牌，得到每天应承载 0/1/2/3/4/5 条事件的日历骨架。",
            "inactive day 保留为空，不生成 occurrence，也不生成 I；active day 后续按目标数量填入 occurrence。",
            "timeline_constructor.py:353-385",
        ),
        (
            "6. 把 tokens 打包进日期",
            f"每个 active day 最多 {config.get('max_events_per_active_day')} 条事件；同一天不能重复同一条 event line；同一条线的日期必须递增。",
            "按固定日历容量精确打包，保证每日事件数直方图和 median 均匹配配置。",
            "timeline_constructor.py:528-588",
        ),
        (
            "7. 构造 event occurrence",
            "根据 occurrence_index 取 stage_sequence 中对应阶段；若超过原始阶段数且 allow_stage_reuse_after_sequence=true，则生成扩展阶段。",
            "同时生成 event_occurrence_id 和 interaction_unit_id，例如 P0001_D06_E002 / P0001_D06_M002。",
            "timeline_constructor.py:590-670",
        ),
        (
            "8. 构造 active day 节点",
            "每个 active day 写 event_occurrences[]，并保留第一条 occurrence 到 day 顶层用于旧代码兼容。",
            "同一天多事件时写 parallel_event_count、has_parallel_events、primary_event_occurrence_id。",
            "timeline_constructor.py:481-502",
        ),
        (
            "9. 运行校验",
            f"校验 {config.get('timeline_days')} 天、{config.get('active_sessions_min')}-{config.get('active_sessions_max')} active sessions、{config.get('event_line_occurrences_min')}-{config.get('event_line_occurrences_max')} 次出现、每日分布、中位数、单日上限、同日不重复、阶段单调、必须从 stage 1 开始。",
            "这保证 timeline 是可运行合同，不是人工故事表。",
            "timeline_constructor.py:59-165",
        ),
    ]
    boundary_rows = [
        (
            "论文直接提供",
            "tau=(z,T,L,I,P)、T 是 accepted event categories、L 是 recurring event lines、L 应该是跨多天演化而不是单次 topic。",
        ),
        (
            "docx / config 提供",
            f"5 人、30 天、当前配置为每人 {config.get('active_sessions_min')}-{config.get('active_sessions_max')} active sessions、每条 event line {config.get('event_line_occurrences_min')}-{config.get('event_line_occurrences_max')} 次、每日分布 {_format_histogram(config.get('daily_event_count_distribution', {}))}、probe 数量范围、必须落盘中间产物。",
        ),
        (
            "当前工程新增",
            f"occurrence round、固定每日事件数打包、同日最多 {config.get('max_events_per_active_day')} 条事件、parallel_event_days_min={config.get('parallel_event_days_min')}、probe_candidate_min_per_persona={config.get('probe_candidate_min_per_persona')}。",
        ),
        (
            "明确不是论文原生",
            "30 天 demo 数量、具体中文事件、M001/M002 ID、并行事件日、固定随机种子和当前排布算法。",
        ),
    ]
    current_rows = [
        ("active_session_total", summary.get("active_session_total"), "事件 occurrence / interaction session 总数；后续一一转成 I。"),
        ("active_day_total", summary.get("active_day_total"), "30 天中真正发生事件的日历天；可少于 active sessions。"),
        ("event_occurrence_total", summary.get("event_occurrence_total"), "Timeline 最小事件节点总数。"),
        ("parallel_event_day_total", summary.get("parallel_event_day_total"), "同一天有多个 occurrence 的天数。"),
        ("daily_event_count_histogram", _format_histogram(summary.get("daily_event_count_histogram", {})), "全体日历天上的事件数分布。"),
        ("daily_event_count_median_calendar", summary.get("daily_event_count_median_calendar"), "按所有日历天计算的事件数中位数。"),
        ("max_events_on_single_day", summary.get("max_events_on_single_day"), f"当前上限为 {config.get('max_events_per_active_day')}。"),
    ]
    return f"""
  <div class="callout">
    第 3 节的核心不是“当前结果有多少天”，而是解释 <code>T/L</code> 怎么被设计成可运行 timeline。
    来源上，<strong>AAAI 论文给的是 ReMem-RE 的受控长期互动构造框架</strong>；
    <strong>docx/config 给的是第一阶段规模和验收约束</strong>；
    <strong>timeline_constructor.py 给的是当前可复现排布算法</strong>。
  </div>
  <h3>3.1 论文来源：为什么需要 Timeline</h3>
  {_table(["层级", "来源", "提供什么", "对 Timeline 的含义"], source_rows)}
  <div class="callout">
    论文中的关键点是：长期互动轨迹不是为了模拟完整人类关系，而是为了构造一个受控上下文，
    让 relational expectation 可以先形成、隔一段时间后再被评测。
    因此 timeline 必须让同一 concern 跨多天出现，而不是把每一天当成孤立问答。
  </div>
  <h3>3.2 概念定义：T/L/occurrence/day/I 的关系</h3>
  {_table(["概念", "白话含义", "当前字段来源", "关键区别"], definition_rows)}
  <h3>3.3 当前 Timeline 生成算法</h3>
  {_table(["步骤", "做什么", "为什么这样做", "代码位置"], algorithm_rows)}
  <h3>3.4 哪些来自论文，哪些是工程实现</h3>
  {_table(["类别", "内容"], boundary_rows)}
  <h3>3.5 当前 demo 的结构结果</h3>
  {_table(["字段", "当前值", "解释"], current_rows, class_name="narrow")}
  <h3>Timeline 到 I 的关键</h3>
  <ol>
    <li><code>day</code> 是日历容器，不等于一个事件。</li>
    <li><code>event_occurrences[]</code> 才是后续生成 I 的最小单位。</li>
    <li>同一天两个 occurrence 会生成两个 <code>interaction_unit_id</code>，共享 <code>day_group_id</code>。</li>
  </ol>
"""


def _i_generation_section(daily_summary: dict[str, Any]) -> str:
    source_rows = [
        (
            "AAAI 论文",
            AAAI_PAPER_PATH,
            "I 是 daily interaction units，用来把 recurring event lines 落成用户 turn。",
            "论文强调每个 I 包含 scripted opening、constrained follow-up 和 strict scene boundary；它服务于长期关系期待的形成和评测。",
        ),
        (
            "工程 docx",
            DOCX_PATH,
            "06_generate_daily_interactions.py 输出 daily_interaction_units.json。",
            "要求每个 interaction 包含 scripted_opening、constrained_followup、scene_boundary；follow-up 不得引入 scene card 外事实。",
        ),
        (
            "直接输入",
            "timeline.json",
            "提供 active days、event_occurrences[]、surface_event、allowed_new_facts、prohibited_facts、related_previous_days。",
            "I 不自由创造新故事，而是把 timeline occurrence 转成可执行互动单元。",
        ),
        (
            "当前实现",
            "src/long_memory_test/sampling/daily_interaction_constructor.py",
            "确定性 constructor，llm_generation_used=false。",
            "输入相同 timeline 时输出相同 I；当前不调用大模型。",
        ),
    ]
    lifecycle_rows = [
        (
            "1. 批处理入口",
            "construct_daily_interactions_for_timeline 读取 timeline_batch，遍历每个 persona timeline。",
            "输出 schema、construction_scope、config、summary、personas，并在最后运行 validation。",
            "daily_interaction_constructor.py:16-47",
        ),
        (
            "2. 处理 inactive day",
            "inactive day 保留 day_group_id，但 interaction_units=[]。",
            "这样 30 天日历结构完整，同时不会把无事件日误当作互动。",
            "daily_interaction_constructor.py:141-154",
        ),
        (
            "3. active occurrence -> I",
            "active day 内每个 event_occurrences[] 都生成一个 I unit。",
            "同一天两个 occurrence 生成两个 I，共享 day_group_id，但 interaction_unit_id 不同。",
            "daily_interaction_constructor.py:155-193",
        ),
        (
            "4. 组装基础 metadata",
            "复制 day、event_line_id、event_stage、stage_index、occurrence_index、related_previous_days 等。",
            "这些字段让后续 run log、memory payload 和 scoring 能回到同一个 tau 坐标。",
            "daily_interaction_constructor.py:211-264",
        ),
        (
            "5. scripted_opening",
            "把 occurrence.surface_event 直接作为 scripted_opening.user_message。",
            "这是用户真正问 agent 的开场句，不是 agent 可见的实验标签，也不是新生成事实。",
            "daily_interaction_constructor.py:267-279",
        ),
        (
            "6. constrained_followup",
            "按 event_stage 选择允许话术动作，设置 followup_budget、reveal_steps、stop_conditions、must_not_introduce。",
            "它定义模拟用户后续最多怎么追问，而不是生成 assistant 答案。",
            "daily_interaction_constructor.py:282-311, 457-536",
        ),
        (
            "7. scene_boundary",
            "汇总 allowed_facts、latent_concerns、memory_level_rules、audit_dimensions。",
            "这是防止模型补事实、串线或泄露评测标签的场景边界。",
            "daily_interaction_constructor.py:314-454",
        ),
        (
            "8. probe_links",
            "如果 occurrence 已有 probe_insertions[]，复制为 probe_links，并标记 read_only=true。",
            "probe 是可选评测插入；I 的生成不依赖 probe。",
            "daily_interaction_constructor.py:219-224, 568-580",
        ),
        (
            "9. message_bindings",
            "为 scripted_opening 和 targeted_probe 建立 message_id -> tau 坐标映射。",
            "运行和评估时通过 binding 追踪 persona/day/event_line/stage/interaction_unit。",
            "daily_interaction_constructor.py:166-183, 583-608",
        ),
        (
            "10. validation",
            "检查每个 timeline occurrence 是否有 I、inactive day 是否为空、ID 是否重复、probe 是否挂对 I。",
            "还检查每个 I 是否有 user_message、followup、reveal_steps、must_not_introduce、allowed_facts、latent_concerns。",
            "daily_interaction_constructor.py:50-129, 611-632",
        ),
    ]
    field_rows = [
        ("interaction_unit_id", "I 的主键，例如 P0001_D10_M001。", "来自 timeline occurrence。"),
        ("event_occurrence_id", "对应 timeline 中的最小事件节点。", "用于确认 I 没有脱离 timeline。"),
        ("day_group_id", "日历日级容器，例如 P0001_D06。", "同日多 I 会共享它。"),
        ("within_day_index", "同一天内第几条 occurrence。", "M001/M002 的来源。"),
        ("event_line_id", "这次互动属于哪条持续事件线。", "后续 M2/M3 和记分都依赖它。"),
        ("event_stage / stage_index", "当前阶段，如 initial、recurrence、turning_point。", "用于限定 intent、tone、allowed moves。"),
        ("scripted_opening", "用户开场句、topic、intent、tone、conversation_goal。", "agent 运行时真正看到的是 user_message。"),
        ("constrained_followup", "后续追问预算、允许动作、reveal steps、停止条件、禁止引入项。", "控制同一 I 内的多轮扩展。"),
        ("scene_boundary", "allowed_facts、latent_concerns、memory level rules、audit dimensions。", "防止事实漂移和评测泄露。"),
        ("probe_links", "该 I 后面可选插入的 read-only probes。", "不是 I 的生成条件。"),
        ("source_timeline_fields", "保留 surface_event、assistant_memory_expectation、allowed/prohibited facts。", "方便审计 I 从哪里来。"),
    ]
    followup_rows = [
        ("source", "timeline_occurrence_rule_template", "说明 follow-up 来自规则模板，不是 LLM 自由生成。"),
        ("mode", "bounded_same_occurrence_followup", "后续追问只能围绕同一个 occurrence。"),
        ("variant_mode", "controlled_user_replay", "适合后续控制式回放和多条件对比。"),
        ("followup_budget", f"{daily_summary.get('followup_budget_default', 2) if daily_summary.get('followup_budget_default') else 2} 轮", "当前默认最多 2 轮。"),
        ("permitted_conversational_moves", "按 stage 选择允许动作", "例如 recurrence 可 refer_to_prior_context。"),
        ("reveal_steps", "每轮最多透露有限 allowed fact / latent concern", "避免用户突然添加剧本外事实。"),
        ("stop_conditions", "具体下一步、预算耗尽、需要新增事实时停止", "保证互动可控。"),
        ("must_not_introduce", "禁止新增事件、人口学事实、诊断、法律结论、同日其他 occurrence 事实等。", "硬边界。"),
    ]
    stage_rows = [
        ("initial", "name_initial_uncertainty", "第一次提出担心，说明触发点和不确定处。"),
        ("recurrence", "refer_to_prior_context", "表达不想从头解释，希望 assistant 接上前序。"),
        ("turning_point", "reassess_state_change", "指出当前状态和最初不同，要求重新校准优先级。"),
        ("partial_resolution", "check_remaining_gap", "说明已经处理一部分，询问是否还有明显漏项。"),
        ("reflection", "extract_reusable_pattern", "回看这条线，总结下次可复用处理方式。"),
        ("common", "clarify_current_constraint / ask_for_small_next_step", "任何阶段都可补充当前约束或要求收束到低风险下一步。"),
    ]
    boundary_rows = [
        ("persona_ref", "source_archetype、occupation、family_structure、primary_life_domains", "只作为稳定背景边界，不额外创造人物事实。"),
        ("timeline_occurrence", "event_title、event_summary、event_stage、stage_goal、assistant_memory_expectation", "定义当前 I 的核心上下文。"),
        ("event_line_stage", "allowed_new_facts", "当前阶段允许新增给 agent 的事实。"),
        ("event history pointer", "related_previous_days", "只暴露前序出现日指针，不自动注入所有历史细节。"),
        ("latent concerns", "stage_goal、latent_continuity、latent_no_restart", "用于评估 agent 是否识别用户隐含期待。"),
        ("memory_level_rules", "M0/M1/M2/M3 可用记忆边界", "防止不同实验条件看到不该看的信息。"),
        ("audit_dimensions", "allowed_fact_boundary、continuity、no_unprovided_detail、parallel isolation、probe read-only", "后续评估和人工审查的检查维度。"),
    ]
    constraint_rows = [
        ("非 LLM 生成", "construction_scope.llm_generation_used=false；当前没有 prompt/completion 产物。"),
        ("I 的生成条件", "每个 active event occurrence 必须生成一个 I；不是有 probe 才生成 I。"),
        ("事实边界", "strict_scene_boundary=true；follow-up 不得引入 scene card 外事实。"),
        ("同日隔离", "cross_occurrence_reference_allowed=false；同一天另一个 I 的事实不会自动混进来。"),
        ("probe 只读", "probe_links[].read_only=true；probe turn 不应写回用户事实。"),
        ("inactive day", "inactive day 必须 interaction_units=[]。"),
        ("校验状态", f"{daily_summary.get('interaction_unit_count')} 个 I、{daily_summary.get('probe_link_count')} 个 probe links，validation 应为 pass。"),
    ]
    return f"""
  <div class="callout">
    <code>I</code> 可以理解成“用户当天一次可执行互动的场景合同”：
    它不是 agent 的回答，也不是 probe 本身，而是把某个 timeline occurrence 转成
    agent 会看到的用户开场、后续追问边界、允许事实和审计坐标。
  </div>
  <h3>4.1 来源与定位</h3>
  {_table(["层级", "来源", "提供什么", "对 I 的含义"], source_rows)}
  <h3>4.2 生成生命周期</h3>
  {_table(["步骤", "做什么", "为什么这样做", "代码位置"], lifecycle_rows)}
  <h3>4.3 I unit 字段解释</h3>
  {_table(["字段", "含义", "用途"], field_rows)}
  <h3>4.4 constrained_followup 细节</h3>
  {_table(["字段", "当前规则", "作用"], followup_rows)}
  <h3>4.5 按阶段允许的话术动作</h3>
  {_table(["event_stage", "主要 move_id", "具体含义"], stage_rows)}
  <h3>4.6 scene_boundary 细节</h3>
  {_table(["来源", "写入内容", "约束作用"], boundary_rows)}
  <h3>4.7 当前硬约束</h3>
  {_table(["约束", "说明"], constraint_rows)}
"""


def _i_examples(
    first_unit: dict[str, Any] | None,
    first_probed: dict[str, Any] | None,
    first_parallel_day: dict[str, Any] | None,
) -> str:
    examples = [_unit_example(first_unit, "普通 I 示例"), _unit_example(first_probed, "带 Probe 的 I 示例")]
    if first_parallel_day:
        units = [unit for unit in first_parallel_day.get("interaction_units", []) if isinstance(unit, dict)]
        rows = [
            (
                f"#{unit.get('within_day_index')}",
                unit.get("interaction_unit_id"),
                _title(unit),
                _stage(unit),
                unit.get("scripted_opening", {}).get("user_message", ""),
            )
            for unit in units
        ]
        examples.append(f"""
<section class="example-box">
  <div class="example-head">同一天并行 I 示例：{_esc(str(first_parallel_day.get("day_group_id")))}</div>
  <div class="example-body">
    {_table(["日内序号", "I unit", "事件", "阶段", "用户具体问题"], rows)}
  </div>
</section>
""")
    return "\n".join(item for item in examples if item)


def _unit_example(unit: dict[str, Any] | None, label: str) -> str:
    if not unit:
        return ""
    opening = unit.get("scripted_opening", {})
    followup = unit.get("constrained_followup", {})
    boundary = unit.get("scene_boundary", {})
    probes = [probe for probe in unit.get("probe_links", []) if isinstance(probe, dict)]
    probe_text = "无" if not probes else "<br>".join(
        f"{_esc(str(probe.get('paper_probe_id')))}：{_esc(str(probe.get('question')))}"
        for probe in probes
    )
    rows = [
        ("I unit", f"<code>{_esc(str(unit.get('interaction_unit_id')))}</code>"),
        ("日期/阶段", f"D{int(unit.get('day', 0)):02d} / {_esc(_stage(unit))}"),
        ("事件线", _esc(_title(unit))),
        ("follow-up 预算", _esc(str(followup.get("followup_budget"))) + " 轮"),
        ("allowed facts", _esc(str(len(boundary.get("allowed_facts", [])))) + " 条"),
        ("latent concerns", _esc(str(len(boundary.get("latent_concerns", [])))) + " 条"),
        ("后接 probe", probe_text),
    ]
    return f"""
<section class="example-box">
  <div class="example-head">{_esc(label)}</div>
  <div class="example-body">
    <p class="meta">用户具体问题：</p>
    <div class="question">{_esc(str(opening.get("user_message", "")))}</div>
    {_table(["项", "内容"], rows, class_name="narrow", escape_cells=False)}
  </div>
</section>
"""


def _probe_section(probe_plan: dict[str, Any]) -> str:
    summary = probe_plan.get("summary", {})
    validation = probe_plan.get("validation", {})
    config = probe_plan.get("construction_config", {})
    type_rows = [
        (
            paper_id,
            PAPER_PROBE_LABELS.get(paper_id, paper_id),
            summary.get("paper_probe_type_counts", {}).get(paper_id, 0),
            _probe_current_coverage_note(paper_id, summary),
        )
        for paper_id in ["P1", "P2", "P3", "P4", "P5", "P6"]
    ]
    dim_rows = [
        (
            dim_id,
            DIMENSION_LABELS.get(dim_id, dim_id),
            summary.get("primary_dimension_counts", {}).get(dim_id, 0),
            _dimension_primary_meaning(dim_id),
        )
        for dim_id in ["D1", "D2", "D3", "D4"]
    ]
    secondary_dim_rows = [
        (
            dim_id,
            DIMENSION_LABELS.get(dim_id, dim_id),
            summary.get("evaluation_dimension_counts", {}).get(dim_id, 0),
            "包含 primary + secondary 维度，因此不要求均匀。",
        )
        for dim_id in ["D1", "D2", "D3", "D4"]
    ]
    source_rows = [
        (
            "AAAI 论文",
            AAAI_PAPER_PATH,
            "定义 targeted relational probes，并把它们插入长期事件轨迹中。",
            "P 是 tau 里的 probe 集合；具体生成时以 D1-D4 评估维度作为主轴。",
        ),
        (
            "AAAI 评估维度",
            "D1-D4",
            "D1 情境化意图、D2 情绪状态调谐、D3 上下文具体性、D4 连续性敏感回应。",
            "每条 probe 都有一个 primary D 维度，另有 0-1 个 secondary D 维度。",
        ),
        (
            "工程 docx",
            DOCX_PATH,
            "要求生成 probe_plan.json；每个 probe 绑定 interaction_unit_id、event_line_id、event_stage、probe_type、target_memory_type。",
            "同时明确 probe 不写回 M0 memory。",
        ),
        (
            "当前实现",
            "src/long_memory_test/sampling/probe_constructor.py",
            "确定性规则模板：从 timeline 选候选，先均衡分配 primary D，再派生 P 类型并写入 timeline。",
            "当前中文问题模板来自工程代码，不是 docx/JSON/论文原文。",
        ),
    ]
    lifecycle_rows = [
        ("1. 复制 timeline", "对 timeline_batch 做 deepcopy，后续把 probe_insertions 写回复制后的 timeline。", "避免破坏原始 timeline，同时生成 timeline_with_probes。", "probe_constructor.py:133-140"),
        (
            "2. 为每个 persona 选 probe slots",
            "遍历 persona_timeline，调用 _select_probe_days。",
            (
                f"每人要满足 {config.get('probes_per_persona_min', '-')}-"
                f"{config.get('probes_per_persona_max', '-')} probes；当前 5 人为 "
                f"{summary.get('probes_per_persona_min', '-')}-{summary.get('probes_per_persona_max', '-')}。"
            ),
            "probe_constructor.py:145-164, 318-363",
        ),
        ("3. 候选过滤", "只选择 active occurrence，且 probe_candidate=true，且 event_stage != initial。", "初始阶段通常还没有形成共享历史，不适合作为记忆调用类 probe。", "probe_constructor.py:324-330"),
        ("4. 每条事件线至少覆盖一次", "_required_probe_days 会按 event_line_id 保留每条线第一个候选。", "保证 probe 不只集中在少数事件线。", "probe_constructor.py:335-371"),
        ("5. 分配 primary D", "对 selected_slots 按 persona 内部 D1/D2/D3/D4 轮转分配 primary_dimension_id。", "这是当前 probe 生成主轴；每人的 primary D 覆盖差值不得超过 1。", "probe_constructor.py:_assign_primary_dimensions"),
        ("6. 控制同日密度", "同一个 active day 最多 1 条 probe。", "避免同一天评测过密，也避免多条并行事件被 probe 混淆。", "probe_constructor.py:165-203, 270-276"),
        ("7. 构造 probe", "_build_probe 写 primary_dimension_id、P 类型、probe_id、insert_after_message_id、event_line_id、event_stage、required_memory_type、target_detail_ids。", "P 类型由 primary D 和 occurrence 阶段派生，不再作为生成主轴。", "probe_constructor.py:_build_probe"),
        ("8. 写回 timeline", "day 和 occurrence 同时写入 probe_ids/probe_insertions。", "后续 I constructor 会从 occurrence.probe_insertions[] 复制到 probe_links。", "probe_constructor.py:169-203"),
        ("9. 校验", "检查重复 ID、插入位置、不能插到 initial、event_line 匹配、已写入 timeline、每人数量范围和 D 覆盖均衡。", "保证 probe 是可审计评测 turn，不是散落的问句。", "probe_constructor.py:243-315"),
    ]
    selection_rows = [
        ("候选来源", "timeline.days[].event_occurrences[]", "只从 active occurrence 中选。"),
        ("非初始阶段", "event_stage != initial", "必须先有前序语境，probe 才能测连续性、记忆调用和状态变化。"),
        ("probe_candidate", "timeline 中 occurrence_index >= 2 时标记为 true", "初始提出一般不测；后续出现才测 agent 是否承接。"),
        ("每人数量", f"{config.get('probes_per_persona_min', '-')}-{config.get('probes_per_persona_max', '-')}", "来自工程配置；当前高密度 timeline 提供更多候选。"),
        ("同日上限", f"{probe_plan.get('construction_config', {}).get('max_probes_per_active_day', 1)}", "避免一天内多个 probe 造成评测污染。"),
        ("主维度均衡", _format_dimension_counts(summary.get("primary_dimension_counts", {})), "当前以 D1-D4 primary dimension 为生成主轴。"),
        ("当前样本", f"{summary.get('probe_count')} 条，总体 validation={validation.get('status')}", "当前 5 人 demo 的实际结果。"),
    ]
    type_decision_rows = [
        ("D1", "current_understanding / P1；partial_resolution 时可派生 relational_boundary / P5", "核心测 situated intent：用户真正想解决什么。"),
        ("D2", "state_transformation / P2；reflection 时可派生 alienation_avoidance / P6", "核心测情绪/状态变化。"),
        ("D3", "natural_detail / P4", "核心测是否自然使用具体上下文细节。"),
        ("D4", "memory_invocation / P3；reflection 时可派生 P6，partial_resolution 时可派生 P5", "核心测连续性和共享历史承接。"),
    ]
    template_rows = [
        ("D1", "Situated Intent Understanding", "围绕「{title}」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。", "probe_constructor.py:_probe_question"),
        ("D2", "Emotional-State Attunement", "这次「{title}」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。", "probe_constructor.py:_probe_question"),
        ("D3", "Contextual Specificity", "你结合「{title}」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。", "probe_constructor.py:_probe_question"),
        ("D4", "Continuity-Sensitive Response", "{title}这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。", "probe_constructor.py:_probe_question"),
    ]
    required_memory_rows = [
        ("P1", "current_understanding", "relational_anchor, summary_memory", "当前理解用户表层问题背后的真实卡点。"),
        ("P2", "state_transformation", "summary_memory, event_memory, relational_anchor", "识别用户状态或事件阶段已经变化。"),
        ("P3", "memory_invocation", "event_memory, relational_anchor", "要求 agent 调用前序共享事件线。"),
        ("P4", "natural_detail", "event_memory, relational_anchor", "自然使用具体细节，但不滥用记忆。"),
        ("P5", "relational_boundary", "relational_anchor, response_boundary", "熟悉但不越界，不替用户编事实。"),
        ("P6", "alienation_avoidance", "relational_anchor, response_boundary, event_memory", "避免像第一次见面一样陌生化回应。"),
    ]
    field_rows = [
        ("probe_id / message_id", "probe turn 的唯一 ID，例如 P0001_D10_P001。"),
        ("turn_type", "固定为 targeted_probe。"),
        ("insert_after_message_id", "必须指向具体 I unit，例如 P0001_D10_M001。"),
        ("event_occurrence_id", "对应 timeline 的 occurrence，保证 probe 不只挂在 day 上。"),
        ("event_line_id / event_stage", "评估时知道 probe 属于哪条长期事件线和哪个阶段。"),
        ("primary_dimension_id", "D1-D4 主生成维度；当前覆盖应近似均匀。"),
        ("secondary_dimension_ids", "辅助评估维度；不作为均衡目标。"),
        ("paper_probe_id / paper_probe_type / paper_probe_zh", "P1-P6 题型标签，由 primary D 和 occurrence 阶段派生。"),
        ("evaluation_dimension_ids", "primary D 放在第一位，后接 secondary D。"),
        ("diagnostic_dimensions / tom_dimensions", "兼容旧评估器的细粒度诊断标签。"),
        ("required_memory_type", "期望用到哪类记忆，例如 event_memory、relational_anchor、response_boundary。"),
        ("target_detail_ids", "绑定具体 stage、occurrence、previous_days 等目标细节。"),
        ("tom_assessment", "写入 high_score_behavior / low_score_behavior / hidden_user_need。"),
        ("read_only / writeback_policy", "probe 不写回记忆，避免评测题污染后续 memory。"),
    ]
    validation_rows = [
        ("唯一性", "probe_id 不允许重复。"),
        ("插入位置存在", "insert_after_message_id 必须能在 active occurrence 中找到。"),
        ("不插 initial", "如果 slot.event_stage == initial，校验报错。"),
        ("事件线一致", "probe.event_line_id 必须等于被插入 occurrence 的 event_line_id。"),
        ("写回 timeline", "probe_id 必须出现在 day/occurrence 的 probe_ids 中。"),
        ("每人数量", f"每个 persona 必须在 {config.get('probes_per_persona_min', '-')}-{config.get('probes_per_persona_max', '-')} probes。"),
        ("同日密度", "每个 active day 最多 1 条 probe。"),
        ("当前结果", f"status={validation.get('status')}；issues={len(validation.get('issues', []))}。"),
    ]
    examples = _probe_examples(probe_plan)
    return f"""
  <div class="callout">
    Probe 不是 probability；这里指 <strong>targeted relational probe</strong>。
    它是插在某个 <code>I</code> 后面的只读评测 turn，用来检验 agent 是否能承接长期关系语境、
    状态变化、边界和自然细节。当前 Probe 不调用大模型；中文问题来自规则模板。
  </div>
  <h3>5.1 来源与定位</h3>
  {_table(["层级", "来源", "提供什么", "对 Probe 的含义"], source_rows)}
  <h3>5.2 生成生命周期</h3>
  {_table(["步骤", "做什么", "为什么这样做", "代码位置"], lifecycle_rows)}
  <h3>5.3 候选选择规则</h3>
  {_table(["规则", "当前定义", "作用"], selection_rows)}
  <h3>5.4 D1-D4 主生成维度覆盖</h3>
  {_table(["维度", "含义", "覆盖次数", "主要看什么"], dim_rows)}
  <h3>5.5 P1-P6 派生题型分布</h3>
  {_table(["论文类型", "含义", "当前数量", "当前覆盖说明"], type_rows)}
  <h3>5.6 D1-D4 全量评估维度计数</h3>
  {_table(["维度", "含义", "出现次数", "说明"], secondary_dim_rows)}
  <h3>5.7 D -> P 派生逻辑</h3>
  {_table(["primary D", "派生 P 题型", "说明"], type_decision_rows)}
  <h3>5.8 D-first 中文模板与出处</h3>
  {_table(["主维度", "含义", "中文模板", "代码位置"], template_rows)}
  <h3>5.9 Required memory 与评测意图</h3>
  {_table(["P 类型", "工程类型", "required_memory_type", "测试意图"], required_memory_rows)}
  <h3>5.10 Probe 字段合同</h3>
  {_table(["字段", "含义"], field_rows)}
  <h3>5.11 校验与防污染</h3>
  {_table(["校验点", "规则"], validation_rows)}
  <h3>5.12 Probe 示例</h3>
  {examples}
"""


def _probe_current_coverage_note(paper_id: str, summary: dict[str, Any]) -> str:
    count = int(summary.get("paper_probe_type_counts", {}).get(paper_id, 0))
    if count > 0:
        return "当前 demo 已覆盖；这是 D-first 生成后的派生题型数量。"
    return "当前 demo 未覆盖；P 类型不是均衡目标。"


def _dimension_primary_meaning(dim_id: str) -> str:
    meanings = {
        "D1": "看 agent 是否理解用户在当前情境里真正问什么，而不是只按表层问题回答。",
        "D2": "看 agent 是否感知用户当前情绪、能量和状态变化。",
        "D3": "看回答是否扎根具体共享上下文，而不是泛泛建议。",
        "D4": "看 agent 是否像连续互动伙伴一样承接前序，同时守住边界。",
    }
    return meanings.get(dim_id, "")


def _probe_examples(probe_plan: dict[str, Any]) -> str:
    examples: dict[str, dict[str, Any]] = {}
    for probe in probe_plan.get("probe_questions", []):
        if isinstance(probe, dict):
            examples.setdefault(str(probe.get("primary_dimension_id")), probe)
    rows = []
    for dimension_id, probe in sorted(examples.items()):
        rows.append(
            (
                dimension_id,
                DIMENSION_LABELS.get(dimension_id, dimension_id),
                probe.get("paper_probe_id"),
                probe.get("probe_type"),
                probe.get("probe_id"),
                f"D{int(probe.get('day', 0)):02d}",
                probe.get("insert_after_message_id"),
                probe.get("question"),
                ", ".join(str(item) for item in probe.get("evaluation_dimension_ids", [])),
            )
        )
    return _table(
        ["主 D", "含义", "派生 P", "工程类型", "Probe ID", "Day", "插入到 I", "问题", "D 维度"],
        rows,
    )


def _binding_section(
    bindings: list[dict[str, Any]],
    units: list[dict[str, Any]],
    unprobed_units: list[dict[str, Any]],
) -> str:
    rows = [
        (
            row["persona_id"],
            f"D{int(row['day']):02d}",
            row["interaction_unit_id"],
            row["event_occurrence_id"],
            row["event_stage_zh"],
            row["event_title"],
            row["user_message"],
            row["probe_id"],
            row["paper_probe_id"],
            row["probe_question"],
        )
        for row in bindings
    ]
    unprobed_rows = [
        (
            unit.get("persona_id"),
            f"D{int(unit.get('day', 0)):02d}",
            unit.get("interaction_unit_id"),
            unit.get("event_occurrence_id"),
            _stage(unit),
            _title(unit),
            unit.get("scripted_opening", {}).get("user_message", ""),
            "无 probe：正常训练/运行互动，只是不作为该点的 targeted evaluation turn。",
        )
        for unit in unprobed_units[:12]
    ]
    requirement_rows = [
        (
            "AAAI 论文 tau 口径",
            "I=daily interaction units，P=inserted targeted relational probes。",
            "P 插在某个 I 后面；论文口径不等于“只有带 P 才生成 I”。",
        ),
        (
            "当前工程 docx / 规模约束",
            "5 人、30 天、高密度 timeline；probe 数量由 probe construction config 控制。",
            "active sessions 对应 occurrence/I；probe 数量是另一个评测覆盖范围，I 不依赖 probe 才存在。",
        ),
        (
            "当前代码校验",
            "每个 timeline occurrence 必须有一个 I；probe 的 insert_after 必须等于对应 I。",
            "I 的完整性独立于 probe；probe 只校验是否正确挂载。",
        ),
    ]
    return f"""
  <div class="callout">
    这里的“绑定关系”不是说 <code>I</code> 只有在有 probe 时才存在。
    当前 <code>I</code> 的全集是 <strong>{len(units)}</strong> 个，其中 <strong>{len(bindings)}</strong> 个后面挂了 probe，
    还有 <strong>{len(unprobed_units)}</strong> 个没有 probe。<code>I</code> 的生成条件是 active
    <code>event_occurrence</code>；<code>Probe</code> 只是插在部分 <code>I</code> 后面的只读评测问题。
  </div>
  <div class="callout">
    绑定规则只适用于“有 probe 的 I”：<code>probe.insert_after_message_id == I.interaction_unit_id</code>，
    且 <code>probe.event_occurrence_id == I.event_occurrence_id</code>。
    Probe 是 <code>read_only=true</code>，不写回用户事实。
  </div>
  <h3>文档与代码要求</h3>
  {_table(["来源", "要求", "对 I/Probe 关系的含义"], requirement_rows)}
  <h3>无 Probe 的 I 示例</h3>
  {_table(["Persona", "Day", "I unit", "Occurrence", "阶段", "事件", "I 用户问题", "说明"], unprobed_rows)}
  <h3>有 Probe 的 I 绑定明细</h3>
  {_table(["Persona", "Day", "I unit", "Occurrence", "阶段", "事件", "I 用户问题", "Probe ID", "P 类型", "Probe 问题"], rows)}
"""


def _parallel_section(day: dict[str, Any] | None) -> str:
    if not day:
        return '<div class="warning">当前未找到并行事件天。</div>'
    rows = []
    for unit in day.get("interaction_units", []):
        if not isinstance(unit, dict):
            continue
        rows.append(
            (
                unit.get("within_day_index"),
                unit.get("interaction_unit_id"),
                unit.get("event_occurrence_id"),
                _title(unit),
                unit.get("scripted_opening", {}).get("user_message", ""),
                "有 probe" if unit.get("probe_links") else "无 probe",
            )
        )
    return f"""
  <div class="callout">
    示例 <code>{_esc(str(day.get("day_group_id")))}</code>：同一天多个 I 共享 day_group_id，
    但各自有独立 interaction_unit_id 和 scene_boundary。默认 <code>cross_occurrence_reference_allowed=false</code>，不自动串事实。
  </div>
  {_table(["日内序号", "I unit", "Occurrence", "事件", "用户具体问题", "Probe"], rows)}
"""


def _non_llm_section() -> str:
    rows = [
        ("Timeline", "规则构造", "按 30 天、active sessions、event line occurrence、parallel day 约束排布。"),
        ("I", "规则构造", "surface_event 直接进入 scripted_opening；follow-up 和 scene boundary 由规则模板生成。"),
        ("Probe", "规则构造", "先均衡分配 D1-D4 primary dimension，再按 D 和 occurrence 阶段派生 P 类型与模板。"),
        ("后续 LLM 位置", "P3b 可选", "只能做自然化改写或多轮展开，不能新增事实或突破 must-not-introduce。"),
    ]
    pseudo = """timeline.event_occurrences[]
  -> daily_interaction_units[].interaction_units[]
  -> scripted_opening.user_message
  -> constrained_followup + scene_boundary
  -> probe_links where insert_after_message_id == interaction_unit_id"""
    return f"""
  {_table(["对象", "当前生成方式", "边界"], rows)}
  <div class="code-block">{_esc(pseudo)}</div>
"""


def _tau_interface_section(tau_contract: dict[str, Any]) -> str:
    summary = tau_contract.get("summary", {})
    adapter_rows = [
        (
            "tau -> dialogue documents",
            "src/long_memory_test/agents/tau_dialogue_adapter.py",
            "build_tau_dialogue_documents(...)",
            "把 tau_contract.I 转为 runner messages，把 tau_contract.P 转为 probe_questions，并按 insert_after_message_id 分组。",
            "保留 canonical_user_message；如果后续接入 P3b 候选，也不覆盖原 I。",
        ),
        (
            "tau -> M0/M1/M2/M3 payloads",
            "src/long_memory_test/agents/memory_condition_builder.py",
            "generate_memory_conditions_from_tau_contract(...)",
            "从 L/I/P/message_bindings 直接构造 memory_conditions_v0.2_tau_route。",
            "只做适配，不生成新任务；runner 最终仍按 M0 base + relational overlay 组合。",
        ),
        (
            "runner schema support",
            "scripts/run_dialogue_conditions.py",
            "_load_memory_conditions(...)",
            "接受 memory_conditions_v0.2_tau_route。",
            "接口已接通；实际 runner 运行需先显式生成 tau-route memory_conditions。",
        ),
        (
            "P3b LLM naturalization",
            "src/long_memory_test/sampling/interaction_naturalizer.py",
            "naturalize_interaction_unit(...)",
            "LLM 基于 canonical I unit 输出自然化候选 JSON。",
            "只允许改写表达，不允许新增事实、改变阶段或突破 scene_boundary。",
        ),
    ]
    condition_rows = [
        (
            "M0",
            "LD-Agent 普通长期记忆基线",
            "读取同轮 M0 retrieved base。",
            "tau binding 只提供 message 坐标；不直接注入 P 标签。",
        ),
        (
            "M1",
            "M0 base + conclusion-level relational overlay",
            "主要来自 L.relational_memory_targets。",
            "结论级关系偏好、回应风格、边界。",
        ),
        (
            "M2",
            "M0 base + M1 + event summary overlay",
            "主要来自 L.persistent_event_summary、observed_stage_sequence、I 当前 stage。",
            "事件线摘要、阶段进展、前序处理策略。",
        ),
        (
            "M3",
            "M0 base + M1 + M2 + detail anchor overlay",
            "主要来自 I.scene_boundary.allowed_facts / latent_concerns，P.target_detail_ids。",
            "必要细节、隐含担心、禁止事实、probe 目标细节。",
        ),
    ]
    p3b_rows = [
        (
            "输入",
            "daily_interaction_units.json 中的 I unit。",
            "包含 scripted_opening、constrained_followup、scene_boundary、source_timeline_fields。",
        ),
        (
            "提示词核心",
            "canonical opening + event title/stage + conversation goal + allowed_facts + reveal_steps + stop_conditions。",
            "明确要求输出严格 JSON，只自然化表达。",
        ),
        (
            "输出",
            "naturalized_dialogue_candidate。",
            "包含 opening_user_message、followup_user_messages、fact_ids_used、non_destructive_policy。",
        ),
        (
            "校验",
            "source_interaction_unit_id、allowed_fact_ids、followup_budget、opening 是否真正改写。",
            "越界 fact id 会 fail；不允许把候选写回 scripted_opening。",
        ),
        (
            "当前状态",
            "脚本和测试已存在，但未调用 LLM。",
            "没有生成 daily_interaction_naturalized_candidates.json。",
        ),
    ]
    run_rows = [
        (
            "构建 tau-route memory conditions",
            "scripts/build_tau_memory_conditions.py --tau-contract long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json --output long_memory_experiment/cache/tau_memory_conditions_combined.json",
            "会写出 memory_conditions_v0.2_tau_route；本报告未执行。",
        ),
        (
            "P3b dry run",
            "scripts/run_p3b_interaction_naturalization.py --daily-interactions long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json --dry-run",
            "只检查会处理多少 I，不调用 LLM。",
        ),
        (
            "P3b 正式候选生成",
            "scripts/run_p3b_interaction_naturalization.py --limit N --provider poixe",
            "会调用 LLM 并写候选文件；必须先人工确认边界。",
        ),
    ]
    audit_rows = [
        ("tau message binding count", summary.get("message_binding_count"), "I + P 的消息坐标总数。"),
        ("interaction_unit_count", summary.get("interaction_unit_count"), "M0-M3 可运行用户 turn 的主体数量。"),
        ("targeted_probe_count", summary.get("targeted_probe_count"), "评测 turn 数量；probe 只读。"),
        ("probed_interaction_unit_count", summary.get("probed_interaction_unit_count"), "后接 P 的 I 数量。"),
        ("unprobed_interaction_unit_count", summary.get("unprobed_interaction_unit_count"), "无 P 但仍然有效的 I 数量。"),
    ]
    return f"""
  <div class="callout">
    这一节回答“tau 怎么接到后续实验”。当前不是把 I 直接一步变成自然对话，
    而是先把 <code>I unit</code> 保留下来，再通过 adapter 接 runner；
    如果需要更自然的用户表达，只走 P3b 候选层。
  </div>
  <h3>9.1 接口清单</h3>
  {_table(["接口", "文件", "函数/入口", "作用", "边界"], adapter_rows)}
  <h3>9.2 tau-route M0/M1/M2/M3 payload 逻辑</h3>
  {_table(["条件", "最终输入", "tau 来源", "记忆含义"], condition_rows)}
  <h3>9.3 P3b LLM 自然化候选层</h3>
  {_table(["环节", "内容", "边界"], p3b_rows)}
  <h3>9.4 后续可执行入口</h3>
  {_table(["动作", "命令", "说明"], run_rows)}
  <h3>9.5 当前接口审计数</h3>
  {_table(["字段", "值", "解释"], audit_rows)}
  <div class="warning">
    当前报告只生成 HTML，不执行上述命令；因此不会新增 memory condition 产物，也不会调用 LLM。
  </div>
"""


def _persona_section(persona: dict[str, Any]) -> str:
    units = [
        unit
        for day in persona.get("days", [])
        if isinstance(day, dict)
        for unit in day.get("interaction_units", [])
        if isinstance(unit, dict)
    ]
    probe_count = sum(len(unit.get("probe_links", [])) for unit in units)
    parallel_days = [
        day for day in persona.get("days", [])
        if isinstance(day, dict) and day.get("has_parallel_events")
    ]
    rows = []
    for unit in units:
        probes = unit.get("probe_links", [])
        probe_text = "无"
        if probes:
            probe_text = "<br>".join(
                f"{_esc(str(probe.get('probe_id')))} · {_esc(str(probe.get('paper_probe_id')))}<br>{_esc(str(probe.get('question')))}"
                for probe in probes
                if isinstance(probe, dict)
            )
        rows.append(
            (
                f"D{int(unit.get('day', 0)):02d} / #{unit.get('within_day_index')}",
                unit.get("interaction_unit_id"),
                _stage(unit),
                _title(unit),
                unit.get("scripted_opening", {}).get("user_message", ""),
                probe_text,
            )
        )
    parallel_text = "、".join(f"D{int(day.get('day', 0)):02d}" for day in parallel_days) or "无"
    ref = persona.get("persona_ref", {})
    return f"""
<details class="persona">
  <summary>{_esc(str(persona.get("persona_id")))}：{_esc(str(ref.get("occupation", "")))}，I units={len(units)}，probes={probe_count}</summary>
  <div class="details-body">
    <p class="meta">来源 archetype：<code>{_esc(str(ref.get("source_archetype", "")))}</code>；并行事件天：{_esc(parallel_text)}</p>
    {_table(["日期/序号", "I unit", "阶段", "事件", "I 用户问题", "Probe"], rows, escape_cells=False)}
  </div>
</details>
"""


def _binding_rows(daily: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for persona in daily.get("personas", []):
        if not isinstance(persona, dict):
            continue
        persona_id = str(persona.get("persona_id", ""))
        for day in persona.get("days", []):
            if not isinstance(day, dict):
                continue
            for unit in day.get("interaction_units", []):
                if not isinstance(unit, dict):
                    continue
                for probe in unit.get("probe_links", []):
                    if not isinstance(probe, dict):
                        continue
                    rows.append(
                        {
                            "persona_id": persona_id,
                            "day": unit.get("day"),
                            "interaction_unit_id": unit.get("interaction_unit_id"),
                            "event_occurrence_id": unit.get("event_occurrence_id"),
                            "event_stage_zh": _stage(unit),
                            "event_title": _title(unit),
                            "user_message": unit.get("scripted_opening", {}).get("user_message", ""),
                            "probe_id": probe.get("probe_id"),
                            "paper_probe_id": probe.get("paper_probe_id"),
                            "probe_question": probe.get("question"),
                        }
                    )
    return rows


def _all_units(daily: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        unit
        for persona in daily.get("personas", [])
        if isinstance(persona, dict)
        for day in persona.get("days", [])
        if isinstance(day, dict)
        for unit in day.get("interaction_units", [])
        if isinstance(unit, dict)
    ]


def _first_parallel_day(daily: dict[str, Any]) -> dict[str, Any] | None:
    for persona in daily.get("personas", []):
        if not isinstance(persona, dict):
            continue
        for day in persona.get("days", []):
            if isinstance(day, dict) and day.get("has_parallel_events"):
                return day
    return None


def _status_block(
    tau_validation: dict[str, Any],
    timeline_validation: dict[str, Any],
    probe_validation: dict[str, Any],
    daily_validation: dict[str, Any],
) -> str:
    rows = [
        ("Tau contract validation", tau_validation.get("status", "unknown"), "; ".join(str(item) for item in tau_validation.get("issues", [])) or "无"),
        ("Timeline validation", timeline_validation.get("status", "unknown"), "; ".join(str(item) for item in timeline_validation.get("issues", [])) or "无"),
        ("Probe validation", probe_validation.get("status", "unknown"), "; ".join(str(item) for item in probe_validation.get("issues", [])) or "无"),
        ("I validation", daily_validation.get("status", "unknown"), "; ".join(str(item) for item in daily_validation.get("issues", [])) or "无"),
    ]
    status = "pass" if all(str(row[1]) == "pass" for row in rows) else "check"
    cls = "ok" if status == "pass" else "warning"
    return f"""
  <div class="{cls}"><strong>整体校验：{_esc(status)}。</strong> Tau、Timeline、Probe、I 四层都应为 pass。</div>
  {_table(["校验层", "状态", "问题"], rows, class_name="narrow")}
"""


def _metric(label: str, value: Any, caption: str) -> str:
    return f'<div class="metric"><strong>{_esc(str(value))}</strong><span>{_esc(label)} / {_esc(caption)}</span></div>'


def _table(
    headers: list[str],
    rows: list[tuple[Any, ...]],
    *,
    class_name: str = "",
    escape_cells: bool = True,
) -> str:
    cls = f' class="{class_name}"' if class_name else ""
    header_html = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    row_html = []
    for row in rows:
        cells = []
        for cell in row:
            text = "" if cell is None else str(cell)
            cells.append(f"<td>{_esc(text) if escape_cells else text}</td>")
        row_html.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table{cls}><tr>{header_html}</tr>{''.join(row_html)}</table>"


def _title(unit: dict[str, Any]) -> str:
    value = unit.get("event_title", {})
    if isinstance(value, dict):
        return str(value.get("zh") or value.get("source") or unit.get("event_category_id", ""))
    return str(value or unit.get("event_category_id", ""))


def _stage(unit: dict[str, Any]) -> str:
    stage = str(unit.get("event_stage", ""))
    return STAGE_CN.get(stage, stage)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _format_histogram(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "-"
    items = []
    for key, count in sorted(value.items(), key=lambda item: int(item[0])):
        items.append(f"{key}:{count}")
    return ", ".join(items)


def _format_dimension_counts(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "-"
    return ", ".join(
        f"{dimension_id}:{value.get(dimension_id, 0)}"
        for dimension_id in ["D1", "D2", "D3", "D4"]
    )


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
