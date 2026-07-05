#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMELINE = (
    REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "docs/p1_timeline_demo5_report.html"
AAAI_PAPER_PATH = str(REPO_ROOT / "docs/references/aaai2027_remem_re.pdf")
DOCX_PATH = "/Users/tom/Desktop/Archetype_Guided_Persona_Event_Sampling_Implementation.docx"


STAGE_CN = {
    "initial": "初始提出",
    "recurrence": "再次出现",
    "turning_point": "转折判断",
    "partial_resolution": "部分处理",
    "reflection": "回看总结",
}

OCCUPATION_CN = {
    "property service assistant": "物业服务助理",
    "call center customer service agent": "呼叫中心客服",
    "platform-based service worker": "平台服务劳动者",
    "convenience store owner": "便利店店主",
    "hotel front desk worker": "酒店前台",
}

FAMILY_CN = {
    "single, rents a room": "单身，租住一间房",
    "single, lives with roommates": "单身，与室友合住",
    "married with one preschool child": "已婚，有一个学龄前孩子",
    "living with extended family": "与大家庭同住",
    "single parent with one preschool child": "单亲，带一个学龄前孩子",
}

DOMAIN_CN = {
    "business": "小生意经营",
    "childcare": "儿童照护",
    "commuting": "通勤",
    "customer_conflict": "客户冲突",
    "customer_relationship": "客户关系",
    "family": "家庭",
    "family_coordination": "家庭协调",
    "finance": "财务",
    "gig_work": "平台/零工",
    "housing": "住房",
    "housing_rent": "住房租金",
    "school": "学校事务",
    "social_connection": "社会连接",
    "work": "工作",
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
    parser = argparse.ArgumentParser(description="Generate a Chinese HTML report for P1 timeline.")
    parser.add_argument("--timeline", type=Path, default=DEFAULT_TIMELINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timeline = _load_json(args.timeline)
    html_text = render_report(timeline=timeline, timeline_path=args.timeline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(*, timeline: dict[str, Any], timeline_path: Path) -> str:
    summary = timeline.get("summary", {})
    validation = timeline.get("validation", {})
    config = timeline.get("construction_config", {})
    persona_sections = "".join(
        _persona_section(item)
        for item in timeline.get("timelines", [])
        if isinstance(item, dict)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>P1 5 人 Timeline 报告</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #5b6670;
      --line: #d8e0e7;
      --soft: #f6f8fb;
      --accent: #1558d6;
      --chip: #eef4ff;
      --active: #eaf4ee;
      --warn: #8a4b00;
      --warn-bg: #fff7e8;
      --ok-bg: #edf7f0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #fff;
      font: 15px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 34px 26px 72px; }}
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
    .meta {{ color: var(--muted); font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }}
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
    .warning {{
      margin: 16px 0;
      padding: 13px 15px;
      background: var(--warn-bg);
      border-left: 4px solid var(--warn);
    }}
    .ok {{
      margin: 16px 0;
      padding: 13px 15px;
      background: var(--ok-bg);
      border-left: 4px solid #26834a;
    }}
    .formula {{
      margin: 12px 0 4px;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .source-table td:first-child {{ width: 18%; }}
    .logic-list {{
      margin: 12px 0 18px;
      padding-left: 22px;
    }}
    .logic-list li {{ margin: 7px 0; }}
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
    .tag {{
      display: inline-block;
      margin: 2px 4px 2px 0;
      padding: 2px 7px;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid #d6e5ff;
      font-size: 12px;
    }}
    .parallel-badge {{
      display: inline-block;
      margin-left: 6px;
      padding: 1px 6px;
      border-radius: 999px;
      background: #fff4e5;
      border: 1px solid #f0c57a;
      color: #8a4b00;
      font-size: 12px;
      font-weight: 700;
    }}
    .parallel-row td {{
      background: #fffaf2;
    }}
    .day-grid {{
      display: grid;
      grid-template-columns: repeat(30, minmax(22px, 1fr));
      gap: 3px;
      margin: 12px 0 18px;
    }}
    .day-cell {{
      min-height: 28px;
      border: 1px solid var(--line);
      border-radius: 4px;
      display: grid;
      place-items: center;
      color: var(--muted);
      font-size: 12px;
      background: #fff;
    }}
    .day-cell.active {{
      background: var(--active);
      color: #0f5132;
      border-color: #b8d9c2;
      font-weight: 700;
    }}
    .day-cell.parallel {{
      background: #fff4e5;
      color: #8a4b00;
      border-color: #f0c57a;
    }}
    details.persona {{
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }}
    details.persona summary {{
      cursor: pointer;
      padding: 11px 13px;
      background: #fbfcfe;
      font-weight: 650;
    }}
    .persona-body {{ padding: 12px 14px 14px; }}
    @media (max-width: 900px) {{
      main {{ padding: 24px 14px 56px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .day-grid {{ grid-template-columns: repeat(10, minmax(22px, 1fr)); }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>P1 5 人 Timeline 报告</h1>
  <p class="meta">Timeline 文件：<code>{_esc(_rel(timeline_path))}</code></p>

  <section>
    <h2>构建状态</h2>
    <div class="grid">
      {_metric("状态", validation.get("status", "-"), "validation")}
      {_metric("Persona", summary.get("persona_count", "-"), "实例")}
      {_metric("Event lines", summary.get("event_line_count", "-"), "事件线")}
      {_metric("Sessions", summary.get("active_session_total", "-"), "事件 occurrence")}
      {_metric("Active days", summary.get("active_day_total", "-"), "有事件的天")}
      {_metric("Parallel days", summary.get("parallel_event_day_total", "-"), "同日多事件")}
      {_metric("Probes", summary.get("probe_count_total", 0), "已插入")}
      {_metric("每人 probes", f"{summary.get('probes_per_persona_min', 0)}-{summary.get('probes_per_persona_max', 0)}", "范围")}
      {_metric("单日上限", summary.get("max_events_on_single_day", "-"), "事件数")}
    </div>
    <div class="callout">
      当前完成 P1 timeline：每个 persona 都有 30 天时间池；
      active sessions 指事件 occurrence 总数，当前每人为
      {_esc(summary.get("active_sessions_per_persona_min", "-"))}-{_esc(summary.get("active_sessions_per_persona_max", "-"))}；
      同一天可以包含多条 <code>event_occurrences</code>，当前单日上限为
      {_esc(config.get("max_events_per_active_day", "-"))}。
      每日事件数直方图为 {_esc(_format_histogram(summary.get("daily_event_count_histogram", {})))}，
      日历中位数为 {_esc(summary.get("daily_event_count_median_calendar", "-"))}。
      P2 probes 已按规则插入到非初始阶段的具体 occurrence 后。
    </div>
  </section>

  {_tau_concept_section(timeline=timeline, timeline_path=timeline_path)}

  {_methodology_section(timeline=timeline, timeline_path=timeline_path)}

  <section>
    <h2>并行事件日索引</h2>
    <div class="callout">
      这里专门列出“一天发生两条事件”的日期。日历格子里也会用橙色 <code>x2</code> 标记；
      明细表中同一天会出现两行，分别标为 <code>1/2</code> 和 <code>2/2</code>。
    </div>
    {_parallel_event_index(timeline)}
  </section>

  <section>
    <h2>阶段分布</h2>
    {_count_table(summary.get("event_stage_counts", {}), labeler=_stage_label)}
    <h3>事件领域分布</h3>
    {_count_table(summary.get("event_domain_counts", {}), labeler=lambda value: value)}
    <h3>论文 Probe P1-P6 分布</h3>
    {_count_table(summary.get("paper_probe_type_counts", {}), labeler=_paper_probe_label)}
    <h3>D1-D4 主生成维度覆盖</h3>
    {_count_table(summary.get("primary_dimension_counts", {}), labeler=_dimension_label)}
    <h3>D1-D4 全量评估维度计数</h3>
    {_count_table(summary.get("evaluation_dimension_counts", {}), labeler=_dimension_label)}
    <h3>工程 Probe 类型分布</h3>
    {_count_table(summary.get("probe_type_counts", {}), labeler=_probe_type_label)}
  </section>

  <section>
    <h2>Persona Timeline 明细</h2>
    {persona_sections}
  </section>
</main>
</body>
</html>
"""


def _tau_concept_section(*, timeline: dict[str, Any], timeline_path: Path) -> str:
    summary = timeline.get("summary", {})
    validation = timeline.get("validation", {})
    config = timeline.get("construction_config", {})
    base_dir = timeline_path.resolve().parent
    probe_plan_path = base_dir / "probe_plan.json"
    return f"""
  <section>
    <h2>tau=(z,T,L,I,P) 概念说明</h2>
    <div class="callout">
      当前项目以 AAAI 2027 论文 <strong>How Agents Remember the Relationship: Evaluating Relational Memory</strong>
      中的 ReMem-RE 框架为最高研究口径。论文给出长期关系记忆评估的轨迹合同
      <code>tau=(z,T,L,I,P)</code>；docx 和 sampling config 给出第一阶段规模；
      当前代码把这些要求落成可复现的 5 人、30 天、并行事件 timeline 与 probe plan。
    </div>
    <p class="meta">
      关键依据：<code>{_esc(AAAI_PAPER_PATH)}</code>；
      工程要求：<code>{_esc(DOCX_PATH)}</code>；
      当前 timeline：<code>{_esc(_rel(timeline_path))}</code>；
      当前 probe plan：<code>{_esc(_rel(probe_plan_path))}</code>。
    </p>

    <h3>AAAI 论文口径</h3>
    <p>
      该论文关注的不是普通 factual recall，而是长期人机互动里的
      <strong>relational expectation</strong>：用户期待 agent 的回应能够体现共享历史、
      熟悉的回应规范、用户状态变化和关系边界。
    </p>
    <div class="formula">tau = (z, T, L, I, P)</div>
    <p class="meta">tau 是受控长期互动轨迹合同，用来把人物、事件、事件线、互动单元和 probe 放在同一套可审计坐标中。</p>

    <table>
      <thead><tr><th>符号</th><th>论文含义</th><th>本项目中文解释</th><th>当前工程落点</th><th>状态</th></tr></thead>
      <tbody>
        <tr><td><code>z</code></td><td>sampled user persona</td><td>被采样出来的用户人物实例。</td><td><code>sampled_personas.json</code>、timeline 中的 <code>persona_ref</code>。</td><td>已生成 {_esc(summary.get("persona_count", "-"))} 人。</td></tr>
        <tr><td><code>T</code></td><td>accepted event categories</td><td>经 persona-event compatibility 验证后被接受的事件类别。</td><td><code>accepted_persona_event_sets.json</code>；来源为事件池 JSON。</td><td>已生成。</td></tr>
        <tr><td><code>L</code></td><td>recurring event lines</td><td>跨天反复推进的持续事件线，不是一次性故事。</td><td><code>event_lines_batch.json</code>；当前 5 人合计 {_esc(summary.get("event_line_count", "-"))} 条。</td><td>已生成。</td></tr>
        <tr><td><code>I</code></td><td>daily interaction units</td><td>可运行的每日互动单元，包含 scripted opening、follow-up 边界、allowed facts 等。</td><td>当前 timeline 是 I 的前置结构；P3 已生成 <code>daily_interaction_units.json</code>。</td><td>已生成。</td></tr>
        <tr><td><code>P</code></td><td>inserted targeted relational probes</td><td>插入式关系记忆测试问题，用于考察共享上下文、状态变化、关系边界等。</td><td><code>probe_plan.json</code>；当前共 {_esc(summary.get("probe_count_total", "-"))} 条。</td><td>已生成。</td></tr>
      </tbody>
    </table>

    <h3>和当前 Timeline 概念的对应</h3>
    <table>
      <thead><tr><th>当前概念</th><th>属于 tau 哪一层</th><th>含义</th><th>是否论文原生概念</th><th>当前出处</th></tr></thead>
      <tbody>
        <tr><td><code>persona</code></td><td><code>z</code></td><td>一个被采样出来的模拟用户，包括职业、家庭结构、生活领域等。</td><td>是，作为 sampled user persona。</td><td>人物池 JSON + P0 采样。</td></tr>
        <tr><td><code>event category / event theme</code></td><td><code>T</code></td><td>候选生活事件主题，如通勤、住房、家庭责任、消费纠纷。</td><td>是，正式版称为 accepted event categories。</td><td>事件池 JSON + accepted event set。</td></tr>
        <tr><td><code>event line</code></td><td><code>L</code></td><td>一个主题展开成跨天持续事件线，带阶段序列和用户消息种子。</td><td>是，作为 recurring event lines。</td><td>P1 event line construction。</td></tr>
        <tr><td><code>event occurrence</code></td><td><code>L -> I</code> 的中间节点</td><td>某条 event line 在某一天的第 N 次出现，是 timeline 的最小事件节点。</td><td>不是论文顶层符号，是工程落地概念。</td><td>timeline constructor。</td></tr>
        <tr><td><code>occurrence round</code></td><td><code>L</code> 的排布策略</td><td>出现轮次：先排所有事件线第 1 次，再排第 2 次，再排第 3 次。</td><td>不是论文原生概念，是工程策略。</td><td><code>_interleaved_tokens()</code>。</td></tr>
        <tr><td><code>active session</code></td><td><code>I</code> 的前置计数</td><td>当前指事件 occurrence / interaction session 总数，不再等于日历天。</td><td>docx/配置给规模，具体语义由工程定义。</td><td>sampling config + timeline validation。</td></tr>
        <tr><td><code>active day</code></td><td><code>I</code> 的日历容器</td><td>30 天中有事件发生的日历日。当前一天可以包含 1-{_esc(config.get("max_events_per_active_day", "-"))} 条 occurrence。</td><td>不是论文顶层符号，是工程容器。</td><td>timeline constructor。</td></tr>
        <tr><td><code>parallel event day</code></td><td><code>I</code> 的日历结构</td><td>同一个 active day 里有多条事件 occurrence，模拟真实生活多线并行。</td><td>不是论文规定，是本轮工程修正。</td><td><code>max_events_per_active_day={_esc(config.get("max_events_per_active_day", "-"))}</code>、<code>parallel_event_days_min={_esc(config.get("parallel_event_days_min", "-"))}</code>。</td></tr>
        <tr><td><code>interaction_unit_id</code></td><td><code>I</code></td><td>每条 occurrence 的互动锚点，例如同一天可有 <code>M001</code>、<code>M002</code>。</td><td>论文要求 I 可审计；ID 是工程实现。</td><td>timeline constructor。</td></tr>
        <tr><td><code>probe</code></td><td><code>P</code></td><td>定向关系 probe，不是 probability。它插在具体 occurrence 后，且不写回记忆。</td><td>是，论文有 targeted relational probes；当前文案为工程模板。</td><td>P2 probe constructor。</td></tr>
      </tbody>
    </table>

    <h3>依据分层</h3>
    <table class="source-table">
      <thead><tr><th>层级</th><th>文件/来源</th><th>提供什么</th><th>不提供什么</th></tr></thead>
      <tbody>
        <tr><td>最高研究口径</td><td><code>{_esc(AAAI_PAPER_PATH)}</code><br>How Agents Remember the Relationship: Evaluating Relational Memory</td><td>ReMem-RE、relational expectation、<code>tau=(z,T,L,I,P)</code>、P1-P6 probe、D1-D4 评估维度、M0-M3 记忆条件。</td><td>不规定我们的具体 5 人 demo 数量、具体中文事件、具体 occurrence round 算法。</td></tr>
        <tr><td>第一阶段工程要求</td><td><code>{_esc(DOCX_PATH)}</code><br><code>docs/archetype_guided_generation_basis.md</code></td><td>原始要求定义 5 人、30 天、可审计中间产物；当前已按本轮修正切换为高密度 timeline：每天 0-{_esc(config.get("max_events_per_active_day", "-"))} 个事件、中位数 {_esc(summary.get("daily_event_count_median_calendar", "-"))}。</td><td>不提供最终人物剧本，也不提供具体 probe 中文文案。</td></tr>
        <tr><td>受控素材池</td><td><code>persona_archetype_pool_v0.1.json</code><br><code>event_category_pool_v0.1_60events.json</code></td><td>人物 archetype、生活领域、事件类别、事件 domain、stage patterns 等素材边界。</td><td>不是最终样本；不能直接把池子当最终故事。</td></tr>
        <tr><td>机器配置</td><td><code>long_memory_experiment/data/sampling/sampling_config.json</code></td><td>随机种子、数量范围、并行事件约束、probe 候选下限。</td><td>不生成内容，只定义生成约束。</td></tr>
        <tr><td>工程实现</td><td><code>src/long_memory_test/sampling/timeline_constructor.py</code><br><code>src/long_memory_test/sampling/probe_constructor.py</code></td><td>确定性采样、timeline 排布、并行事件打包、probe 插入和校验。</td><td>不是论文原文；属于可审计实现。</td></tr>
        <tr><td>当前实例</td><td><code>{_esc(_rel(timeline_path))}</code><br><code>{_esc(_rel(probe_plan_path))}</code></td><td>当前 5 人 demo 的实际 timeline 和 probe plan。</td><td>只是当前随机种子的产物，不代表唯一可能样本。</td></tr>
      </tbody>
    </table>

    <h3>当前完成度</h3>
    <div class="ok">
      当前 5 人 demo 已经完成 <code>z</code>、<code>T</code>、<code>L</code>、timeline occurrence 排布、
      <code>I</code> 和 <code>P</code>；P4 也已生成 <code>tau_contract.json</code>，
      把 <code>z,T,L,I,P</code> 固化为同一份可审计合同。
    </div>
    <table>
      <thead><tr><th>项目</th><th>当前值</th><th>说明</th></tr></thead>
      <tbody>
        <tr><td>timeline validation</td><td>{_esc(validation.get("status", "-"))}</td><td>当前 timeline 结构校验结果。</td></tr>
        <tr><td>active sessions</td><td>{_esc(summary.get("active_sessions_per_persona_min", "-"))}-{_esc(summary.get("active_sessions_per_persona_max", "-"))}</td><td>当前指事件 occurrence / interaction session。</td></tr>
        <tr><td>active days</td><td>{_esc(summary.get("active_days_per_persona_min", "-"))}-{_esc(summary.get("active_days_per_persona_max", "-"))}</td><td>有事件发生的日历日。</td></tr>
        <tr><td>parallel event days</td><td>{_esc(summary.get("parallel_event_days_per_persona_min", "-"))}-{_esc(summary.get("parallel_event_days_per_persona_max", "-"))}</td><td>每人同日多事件日。</td></tr>
        <tr><td>daily event histogram</td><td>{_esc(_format_histogram(summary.get("daily_event_count_histogram", {})))}</td><td>全体日历天上的事件数分布。</td></tr>
        <tr><td>daily event median</td><td>{_esc(summary.get("daily_event_count_median_calendar", "-"))}</td><td>按所有日历天计算。</td></tr>
        <tr><td>max events on single day</td><td>{_esc(summary.get("max_events_on_single_day", "-"))}</td><td>当前单日最多 {_esc(config.get("max_events_per_active_day", "-"))} 条事件。</td></tr>
        <tr><td>probes per persona</td><td>{_esc(summary.get("probes_per_persona_min", "-"))}-{_esc(summary.get("probes_per_persona_max", "-"))}</td><td>当前实际 probe 覆盖范围。</td></tr>
      </tbody>
    </table>
    <div class="warning">
      这里要区分清楚：论文要求的是可审计的长期关系轨迹 <code>tau</code>；docx 要求的是第一阶段规模；
      <code>occurrence round</code>、<code>parallel event day</code>、<code>probe_candidate_min_per_persona</code>
      和固定每日事件数分布是当前工程为了让轨迹可复现、可校验、能覆盖足够 probe 而加入的实现规则。
    </div>
  </section>
    """


def _methodology_section(*, timeline: dict[str, Any], timeline_path: Path) -> str:
    config = timeline.get("construction_config", {})
    summary = timeline.get("summary", {})
    base_dir = timeline_path.resolve().parent
    return f"""
  <section>
    <h2>来源与生成逻辑</h2>
    <h3>Probe 来源确认</h3>
    <div class="callout">
      当前报告里的 probe 不是概率值，也不是从原始 JSON 直接抽出的字段。
      它是 P2 规则模块根据已经生成的 timeline 自动构造出的定向测试问题，
      用来检验模型能否调用共享上下文、识别状态变化、把握关系边界，并且不得写回记忆。
      多事件并行后，probe 绑定到具体 <code>event_occurrence_id</code> 和 occurrence 级
      <code>interaction_unit_id</code>。
    </div>
    <table>
      <thead><tr><th>来源层级</th><th>具体输入</th><th>作用</th></tr></thead>
      <tbody>
        <tr><td>原始人物池</td><td><code>long_memory_experiment/data/sampling/persona_archetype_pool_v0.1.json</code></td><td>提供 persona archetype、职业、家庭结构、生活领域等边界。</td></tr>
        <tr><td>原始事件池</td><td><code>long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json</code></td><td>提供 event category、domain、uncertainties、actions、stage_patterns。</td></tr>
        <tr><td>P0 采样结果</td><td><code>{_esc(_rel(base_dir / "accepted_persona_event_sets.json"))}</code></td><td>确定 5 个 persona 分别接受哪些事件类别。</td></tr>
        <tr><td>P1 事件线</td><td><code>{_esc(_rel(base_dir / "event_lines_batch.json"))}</code></td><td>把事件类别转成每条 event line 的阶段序列和用户消息种子。</td></tr>
        <tr><td>P1 timeline</td><td><code>{_esc(_rel(timeline_path))}</code></td><td>确定每条 event line 具体出现在哪些天、处于哪个阶段。</td></tr>
        <tr><td>P2 probe plan</td><td><code>{_esc(_rel(base_dir / "probe_plan.json"))}</code></td><td>从 timeline 的候选 active day 中生成 probe，并插回 timeline。</td></tr>
      </tbody>
    </table>

    <h3>Probe 插入规则</h3>
    <ol class="logic-list">
      <li>候选节点来自 timeline 里的 active day 内部 <code>event_occurrences[]</code>，且 <code>probe_candidate=true</code>，也就是同一事件线至少第 2 次出现。</li>
      <li>初始阶段 <code>initial</code> 不插 probe；probe 只考察已经有上下文积累后的记忆与关系理解。</li>
      <li>每个 active day 最多插入 1 条 probe；如果同一天有多个候选 occurrence，只选择其中一个，避免同一天 probe 过密。</li>
      <li>当前实际每个 persona 生成 {_esc(summary.get("probes_per_persona_min", "-"))}-{_esc(summary.get("probes_per_persona_max", "-"))} 条 probe；如果候选数量超过上限，先保证尽量覆盖不同 event line，再用固定随机种子补足。</li>
      <li>选定 slots 后，按 persona 内部轮转分配 <code>primary_dimension_id</code>：D1、D2、D3、D4。当前主 D 覆盖为 {_esc(_format_dimension_counts(summary.get("primary_dimension_counts", {})))}。</li>
      <li>P1-P6 不再作为生成主轴，而是由 primary D 和 occurrence 阶段派生出的题型标签。</li>
      <li>每条 probe 写入 <code>primary_dimension_id</code>、<code>secondary_dimension_ids</code>、<code>required_memory_type</code>、<code>tom_dimensions</code>、<code>target_detail_ids</code>，并标记 <code>read_only=true</code>。</li>
    </ol>

    {_probe_generation_deep_dive(timeline)}

    <h3>Timeline 配置</h3>
    <table>
      <thead><tr><th>参数</th><th>当前值</th><th>含义</th></tr></thead>
      <tbody>
        <tr><td><code>random_seed</code></td><td>{_esc(config.get("random_seed", "-"))}</td><td>固定随机性，保证同一输入可复现。</td></tr>
        <tr><td><code>timeline_days</code></td><td>{_esc(config.get("timeline_days", "-"))}</td><td>每个 persona 的时间池天数。</td></tr>
        <tr><td><code>active_sessions_min/max</code></td><td>{_esc(config.get("active_sessions_min", "-"))}-{_esc(config.get("active_sessions_max", "-"))}</td><td>每个 persona 的事件 occurrence / interaction session 数量范围。</td></tr>
        <tr><td><code>event_line_occurrences_min/max</code></td><td>{_esc(config.get("event_line_occurrences_min", "-"))}-{_esc(config.get("event_line_occurrences_max", "-"))}</td><td>每条 event line 在 30 天内出现的次数范围。</td></tr>
        <tr><td><code>max_events_per_active_day</code></td><td>{_esc(config.get("max_events_per_active_day", "-"))}</td><td>同一个日历日最多允许多少条事件 occurrence 并行发生。</td></tr>
        <tr><td><code>parallel_event_days_min</code></td><td>{_esc(config.get("parallel_event_days_min", "-"))}</td><td>每个 persona 至少构造多少个同日多事件日。</td></tr>
        <tr><td><code>daily_event_count_distribution</code></td><td>{_esc(_format_histogram(config.get("daily_event_count_distribution", {})))}</td><td>每个 persona 的 30 天日历固定分布：key 是当天 occurrence 数，value 是天数。</td></tr>
        <tr><td><code>daily_event_count_median_target</code></td><td>{_esc(config.get("daily_event_count_median_target", "-"))}</td><td>按日历天计算的事件数中位数目标。</td></tr>
        <tr><td><code>allow_stage_reuse_after_sequence</code></td><td>{_esc(config.get("allow_stage_reuse_after_sequence", "-"))}</td><td>当 occurrence 次数超过原始 stage_sequence 长度时，是否允许生成扩展阶段。</td></tr>
        <tr><td><code>probe_candidate_min_per_persona</code></td><td>{_esc(config.get("probe_candidate_min_per_persona", "-"))}</td><td>为 P2 保留的非初始 probe 候选 occurrence 下限。</td></tr>
      </tbody>
    </table>

    <h3>Timeline 排布逻辑</h3>
    <ol class="logic-list">
      <li>先读取每个 persona 的 P1 event lines。当前汇总为 {_esc(summary.get("persona_count", "-"))} 个 persona、{_esc(summary.get("event_line_count", "-"))} 条 event line。</li>
      <li>每条 event line 先分配最低出现次数 {_esc(config.get("event_line_occurrences_min", "-"))} 次；当前每日事件数分布固定为 {_esc(_format_histogram(config.get("daily_event_count_distribution", {})))}，所以每个 persona 的 target occurrence 总数固定为 {_esc(summary.get("active_sessions_per_persona_min", "-"))}。这里的 session 指事件 occurrence，不再等同于日历日。</li>
      <li>每条 event line 的阶段顺序严格单调：第 1 次对应 <code>initial</code>，第 2 次对应 <code>recurrence</code>，后续按该事件线的 <code>stage_sequence</code> 继续推进。若 occurrence 超过原始阶段数，且 <code>allow_stage_reuse_after_sequence=true</code>，则按 recurrence / turning_point / partial_resolution / reflection 生成扩展阶段。</li>
      <li>把不同事件线按 occurrence round 交错：先排所有第 1 次出现，再排第 2 次出现，再排第 3 次出现；每一轮内部用固定随机种子打散，避免同一事件线连续堆叠。</li>
      <li>如果配置了 <code>daily_event_count_distribution</code>，先把 30 天的事件数固定下来，再把 occurrence token 打包进这些日历日；当前允许同一天 0-{_esc(config.get("max_events_per_active_day", "-"))} 条事件，且同一条 event line 不会在同一天重复。</li>
      <li>每条 occurrence 都有自己的 <code>event_occurrence_id</code> 和 <code>interaction_unit_id</code>，例如 <code>D12_M001</code>、<code>D12_M002</code>；active day 顶层保留第一条 occurrence 作为兼容主事件。</li>
      <li>未被分配 occurrence 的日期保留为 inactive day；active day 会额外写入 <code>parallel_event_count</code>、<code>has_parallel_events</code>、<code>primary_event_occurrence_id</code>。</li>
      <li>最后运行校验：每人必须 {_esc(config.get("timeline_days", "-"))} 天、active sessions 必须在 {_esc(config.get("active_sessions_min", "-"))}-{_esc(config.get("active_sessions_max", "-"))}、每条 event line 必须出现 {_esc(config.get("event_line_occurrences_min", "-"))}-{_esc(config.get("event_line_occurrences_max", "-"))} 次、每日分布和中位数必须匹配配置、单日事件数不超过上限、同日不重复同一 event line、事件线阶段顺序不能倒退，并且必须从第 1 阶段开始。</li>
    </ol>
  </section>
    """


def _probe_generation_deep_dive(timeline: dict[str, Any]) -> str:
    summary = timeline.get("summary", {})
    return f"""
    <h3>Probe 本质生成逻辑：规则模板，不是 LLM 生成</h3>
    <div class="callout">
      当前 P2 probe 没有调用大模型，也没有使用自由生成 prompt。
      它的“提示词逻辑”本质上是代码里的中文模板：
      先从 timeline 节点读取 <code>event_title</code>、<code>event_stage</code>、<code>occurrence_index</code>、
      <code>related_previous_days</code> 等字段；再先分配 <code>D1-D4 primary_dimension_id</code>，
      最后由 primary D 和 occurrence 阶段派生 P 类型与中文模板。
      因此它可复现、可审计，但语言变化较少；后续如果要更自然，可以把这套规则升级成 LLM prompt 约束。
    </div>

    <h3>模板出处与责任边界</h3>
    <table>
      <thead><tr><th>问题</th><th>当前结论</th><th>出处</th></tr></thead>
      <tbody>
        <tr><td>docx 是否给了具体 probe 文案？</td><td>没有。docx 固化的是第一阶段规模、产物和 probe 数量要求，不包含当前这些中文句子；当前 probe 数量以 <code>probe_plan.json</code> 和 sampling config 为准。</td><td><code>docs/archetype_guided_generation_basis.md</code>：记录原始第一阶段要求和必须落盘 <code>probe_plan.json</code>。</td></tr>
        <tr><td>JSON 事件池是否给了具体 probe 文案？</td><td>没有。事件池说明事件应适合 delayed relational probes，并提供 event title、stage、uncertainties、actions 等素材。</td><td><code>event_category_pool_v0.1_60events.json</code>：<code>suitable for delayed relational probes</code>。</td></tr>
        <tr><td>当前具体中文模板来自哪里？</td><td>来自 P2 工程实现，是我在 <code>probe_constructor.py</code> 里写的确定性模板，不是原始材料引用。</td><td><code>src/long_memory_test/sampling/probe_constructor.py</code> 的 <code>_probe_question()</code>。</td></tr>
        <tr><td>模板为什么这样写？</td><td>它们是把 docx 的 probe 产物要求、事件池的延迟关系探针目标，以及 D1-D4 评测维度合成成工程规则。当前以 D1-D4 作为主生成轴，P1-P6 只是派生题型标签。</td><td><code>_assign_primary_dimensions()</code>、<code>_probe_type_for_dimension()</code>、<code>_probe_question()</code>。</td></tr>
      </tbody>
    </table>

    <h3>Probe 生成伪代码</h3>
    <pre class="code-block">{_esc(_probe_generation_pseudocode())}</pre>

    <h3>Probe 输入字段</h3>
    <table>
      <thead><tr><th>字段</th><th>来自哪里</th><th>在 probe 生成中的作用</th></tr></thead>
      <tbody>
        <tr><td><code>persona_id</code></td><td>P0 sampled persona / P1 timeline</td><td>写入 probe id，例如 <code>P0001_D12_P001</code>。</td></tr>
        <tr><td><code>day</code></td><td>P1 timeline active day</td><td>确定 probe 插入在第几天。</td></tr>
        <tr><td><code>event_occurrence_id</code></td><td>P1 timeline occurrence</td><td>确定 probe 对准当天哪一条并行事件。</td></tr>
        <tr><td><code>interaction_unit_id</code></td><td>P1 timeline occurrence</td><td>写入 <code>insert_after_message_id</code>，表示 probe 插在具体 occurrence 的用户消息之后。</td></tr>
        <tr><td><code>event_line_id</code></td><td>P1 event line / P1 timeline occurrence</td><td>保证 probe 指向同一条持续事件线。</td></tr>
        <tr><td><code>event_title.zh</code></td><td>事件池中文映射 / P1 event line</td><td>填入中文模板里的 <code>{{title}}</code>。</td></tr>
        <tr><td><code>primary_dimension_id</code></td><td>P2 规则分配</td><td>D1-D4 主生成维度，当前每个 persona 内近似均匀。</td></tr>
        <tr><td><code>event_stage</code></td><td>P1 timeline</td><td>辅助派生 P 类型，例如 D4 + reflection 会派生 P6。</td></tr>
        <tr><td><code>occurrence_index</code></td><td>P1 timeline</td><td>用于标记事件线第几次出现，帮助审计连续性。</td></tr>
        <tr><td><code>related_previous_days</code></td><td>P1 timeline</td><td>说明这条事件线以前出现过哪些天，支持“不要从头解释”的测试目标。</td></tr>
      </tbody>
    </table>

    <h3>D-first 生成逻辑</h3>
    <table>
      <thead><tr><th>primary D</th><th>主测试目标</th><th>派生 P 类型</th><th>当前 5 人 primary 覆盖</th></tr></thead>
      <tbody>
        <tr><td><code>D1</code></td><td>情境化意图理解：用户真正想解决什么。</td><td>通常 P1；partial_resolution 可派生 P5。</td><td>{_esc(_primary_dimension_count(summary, "D1"))} 条</td></tr>
        <tr><td><code>D2</code></td><td>情绪与状态调谐：用户状态是否变化。</td><td>通常 P2；reflection 可派生 P6。</td><td>{_esc(_primary_dimension_count(summary, "D2"))} 条</td></tr>
        <tr><td><code>D3</code></td><td>上下文具体性：是否自然使用具体细节。</td><td>P4。</td><td>{_esc(_primary_dimension_count(summary, "D3"))} 条</td></tr>
        <tr><td><code>D4</code></td><td>连续性敏感回应：是否承接共享历史。</td><td>通常 P3；reflection 可派生 P6，partial_resolution 可派生 P5。</td><td>{_esc(_primary_dimension_count(summary, "D4"))} 条</td></tr>
      </tbody>
    </table>

    <h3>具体 D-first 提示词模板</h3>
    <table>
      <thead><tr><th>primary D</th><th>中文模板</th><th>派生 P</th><th>说明</th></tr></thead>
      <tbody>
        <tr><td><code>D1</code></td><td><code>{_esc("围绕「{title}」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。")}</code></td><td>P1 / P5</td><td>先测 situated intent。</td></tr>
        <tr><td><code>D2</code></td><td><code>{_esc("这次「{title}」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。")}</code></td><td>P2 / P6</td><td>先测状态变化和调谐。</td></tr>
        <tr><td><code>D3</code></td><td><code>{_esc("你结合「{title}」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。")}</code></td><td>P4</td><td>先测上下文具体性。</td></tr>
        <tr><td><code>D4</code></td><td><code>{_esc("{title}这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。")}</code></td><td>P3 / P5 / P6</td><td>先测连续性和记忆调用。</td></tr>
      </tbody>
    </table>

    <h3>当前 5 人样例</h3>
    {_probe_generation_examples(timeline)}
    """


def _probe_generation_pseudocode() -> str:
    return """for each persona_timeline:
  candidates = active day.event_occurrences where:
    active day == true
    occurrence.probe_candidate == true
    occurrence.event_stage != "initial"

  selected_slots = first candidate from each event_line_id
  selected_slots += shuffled remaining occurrences until probes_per_persona_max
  enforce max_probes_per_active_day == 1
  assign primary_dimension_id by balanced cycle:
    D1 -> D2 -> D3 -> D4

  for each selected occurrence:
    primary_dimension_id = occurrence.primary_dimension_id
    probe_type = type_by(primary_dimension_id, occurrence.event_stage)
    title = occurrence.event_title.zh
    question = template[primary_dimension_id].format(title=title)
    probe = {
      probe_id,
      event_occurrence_id,
      insert_after_message_id: occurrence.interaction_unit_id,
      event_line_id,
      event_stage,
      primary_dimension_id,
      paper_probe_id,
      paper_probe_type,
      evaluation_dimension_ids,
      required_memory_type,
      diagnostic_dimensions,
      target_detail_ids,
      read_only: true,
      writeback_policy: "probe_turn_must_not_write_to_memory"
    }"""


def _probe_generation_examples(timeline: dict[str, Any]) -> str:
    examples: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for persona_timeline in timeline.get("timelines", []):
        if not isinstance(persona_timeline, dict):
            continue
        for day in persona_timeline.get("days", []):
            if not isinstance(day, dict):
                continue
            for occurrence in _day_event_occurrences(day):
                for probe in occurrence.get("probe_insertions", []):
                    if not isinstance(probe, dict):
                        continue
                    probe_type = str(probe.get("probe_type", ""))
                    examples.setdefault(probe_type, (occurrence, probe))
            if _day_event_occurrences(day):
                continue
            for probe in day.get("probe_insertions", []):
                if not isinstance(probe, dict):
                    continue
                probe_type = str(probe.get("probe_type", ""))
                examples.setdefault(probe_type, (day, probe))
    if not examples:
        return "<p class='meta'>当前 timeline 未插入 probe。</p>"
    rows = []
    for probe_type, (day, probe) in sorted(examples.items()):
        paper_probe_id = str(probe.get("paper_probe_id") or "")
        dimension_ids = probe.get("evaluation_dimension_ids", [])
        rows.append(
            "<tr>"
            f"<td><code>{_esc(paper_probe_id)}</code><br>{_esc(_paper_probe_label(paper_probe_id))}<br>"
            f"<span class='meta'><code>{_esc(probe_type)}</code></span></td>"
            f"<td>{_esc(day.get('persona_id'))} · D{int(day.get('day', 0)):02d}<br>"
            f"<span class='meta'>stage={_esc(day.get('event_stage'))}；occurrence={_esc(day.get('occurrence_index'))}；within_day={_esc(day.get('within_day_index', 1))}</span></td>"
            f"<td>{_esc(_event_title_zh(day))}</td>"
            f"<td>{_tags([str(item) for item in dimension_ids], labeler=_dimension_label)}</td>"
            f"<td>{_esc(probe.get('question'))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>论文类型</th><th>触发节点</th><th>事件标题</th><th>D1-D4</th><th>生成问题</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _parallel_event_index(timeline: dict[str, Any]) -> str:
    rows = []
    for persona_timeline in timeline.get("timelines", []):
        if not isinstance(persona_timeline, dict):
            continue
        persona_id = str(persona_timeline.get("persona_id", ""))
        rows.extend(_parallel_day_rows(persona_id=persona_id, timeline=persona_timeline))
    if not rows:
        return "<p class='meta'>当前 timeline 没有同日多事件。</p>"
    return (
        "<table>"
        "<thead><tr><th>Persona</th><th>Day</th><th>序号</th><th>阶段</th><th>事件</th><th>event_line</th><th>Probe</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _parallel_day_rows(*, persona_id: str, timeline: dict[str, Any]) -> list[str]:
    rows = []
    for day in timeline.get("days", []):
        if not isinstance(day, dict) or not day.get("active"):
            continue
        occurrences = _day_event_occurrences(day)
        if len(occurrences) <= 1:
            continue
        for occurrence in occurrences:
            probe_ids = occurrence.get("probe_ids", [])
            probe_text = ", ".join(str(item) for item in probe_ids) if probe_ids else "无"
            rows.append(
                "<tr class='parallel-row'>"
                f"<td><code>{_esc(persona_id)}</code></td>"
                f"<td>D{int(day.get('day', 0)):02d}<span class='parallel-badge'>x{len(occurrences)}</span></td>"
                f"<td>{_esc(occurrence.get('within_day_index', 1))}/{len(occurrences)}<br>"
                f"<span class='meta'>{_esc(occurrence.get('event_occurrence_id', ''))}</span></td>"
                f"<td>{_esc(_stage_label(str(occurrence.get('event_stage'))))}</td>"
                f"<td>{_esc(_event_title_zh(occurrence))}</td>"
                f"<td><code>{_esc(occurrence.get('event_line_id'))}</code></td>"
                f"<td>{_esc(probe_text)}</td>"
                "</tr>"
            )
    return rows


def _persona_section(timeline: dict[str, Any]) -> str:
    persona = timeline.get("persona_ref", {})
    active_days = [day for day in timeline.get("days", []) if isinstance(day, dict) and day.get("active")]
    active_day_lookup = {
        int(day.get("day", 0)): len(_day_event_occurrences(day))
        for day in active_days
    }
    day_grid = "".join(
        _day_grid_cell(day=day, event_count=active_day_lookup.get(day, 0))
        for day in range(1, int(timeline.get("timeline_days", 30)) + 1)
    )
    occurrence_rows = "".join(
        "<tr>"
        f"<td><code>{_esc(line_id)}</code></td>"
        f"<td>{_esc(count)}</td>"
        "</tr>"
        for line_id, count in timeline.get("event_line_occurrence_counts", {}).items()
    )
    parallel_rows = "".join(
        _parallel_day_rows(persona_id=str(timeline.get("persona_id", "")), timeline=timeline)
    )
    parallel_table = (
        "<table><thead><tr><th>Persona</th><th>Day</th><th>序号</th><th>阶段</th><th>事件</th><th>event_line</th><th>Probe</th></tr></thead>"
        f"<tbody>{parallel_rows}</tbody></table>"
        if parallel_rows
        else "<p class='meta'>该 persona 没有同日多事件。</p>"
    )
    day_rows = "".join(_day_rows(day) for day in active_days)
    return f"""
    <details class="persona" open>
      <summary>
        <code>{_esc(timeline.get("persona_id"))}</code>
        · {_esc(persona.get("source_archetype"))}
        · sessions {_esc(timeline.get("active_session_count"))}
        · active days {_esc(timeline.get("active_day_count"))}
        · parallel days {_esc(timeline.get("parallel_event_day_count", 0))}
        · event lines {_esc(timeline.get("event_line_count"))}
      </summary>
      <div class="persona-body">
        <p class="meta">
          职业：{_esc(_occupation_label(persona.get("occupation")))}；
          家庭结构：{_esc(_family_label(persona.get("family_structure")))}；
          生活领域：{_tags(persona.get("primary_life_domains", []), labeler=_domain_label)}
        </p>
        <div class="day-grid">{day_grid}</div>
        <h3>并行事件日</h3>
        {parallel_table}
        <h3>事件线出现次数</h3>
        <table><thead><tr><th>event_line_id</th><th>出现次数</th></tr></thead><tbody>{occurrence_rows}</tbody></table>
        <h3>Active Day / Occurrence 绑定</h3>
        <table>
          <thead><tr><th>Day</th><th>阶段</th><th>事件</th><th>event_line</th><th>用户消息种子</th><th>Probe</th></tr></thead>
          <tbody>{day_rows}</tbody>
        </table>
      </div>
    </details>
    """


def _day_rows(day: dict[str, Any]) -> str:
    occurrences = _day_event_occurrences(day)
    rows = []
    for occurrence in occurrences:
        title_zh = _event_title_zh(occurrence)
        previous = occurrence.get("related_previous_days", [])
        previous_text = f"；前序天：{previous}" if previous else ""
        rows.append(
            "<tr>"
            f"<td>D{int(day.get('day', 0)):02d}<br>"
            f"<span class='meta'>{_esc(occurrence.get('within_day_index', 1))}/{len(occurrences)} · "
            f"{_esc(occurrence.get('event_occurrence_id', ''))}</span></td>"
            f"<td>{_esc(_stage_label(str(occurrence.get('event_stage'))))}</td>"
            f"<td>{_esc(title_zh)}<br><span class='meta'>{_esc(occurrence.get('event_domain_zh'))}{_esc(previous_text)}</span></td>"
            f"<td><code>{_esc(occurrence.get('event_line_id'))}</code></td>"
            f"<td>{_esc(occurrence.get('surface_event'))}</td>"
            f"<td>{_probe_cell(occurrence)}</td>"
            "</tr>"
        )
    return "".join(rows)


def _day_grid_cell(*, day: int, event_count: int) -> str:
    classes = ["day-cell"]
    if event_count:
        classes.append("active")
    if event_count > 1:
        classes.append("parallel")
    label = (
        str(day)
        if event_count <= 1
        else f"{day}<br><span class='parallel-badge'>x{event_count}</span>"
    )
    return f"<div class='{' '.join(classes)}'>{label}</div>"


def _event_title_zh(day: dict[str, Any]) -> str:
    title = day.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or day.get("event_category_id", ""))
    return str(title or day.get("event_category_id", ""))


def _day_event_occurrences(day: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = [
        item for item in day.get("event_occurrences", []) if isinstance(item, dict)
    ]
    if occurrences:
        return occurrences
    if day.get("active"):
        return [day]
    return []


def _count_table(data: Any, *, labeler) -> str:
    if not isinstance(data, dict) or not data:
        return "<p class='meta'>未提供。</p>"
    rows = []
    for key, count in sorted(data.items(), key=lambda item: (-int(item[1]), str(item[0]))):
        rows.append(
            "<tr>"
            f"<td><code>{_esc(key)}</code></td>"
            f"<td>{_esc(labeler(str(key)))}</td>"
            f"<td>{_esc(count)}</td>"
            "</tr>"
        )
    return f"<table><thead><tr><th>ID</th><th>中文说明</th><th>数量</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _metric(value: str, number: Any, label: str) -> str:
    return (
        "<div class='metric'>"
        f"<strong>{_esc(number)}</strong>"
        f"<span>{_esc(value)} · {_esc(label)}</span>"
        "</div>"
    )


def _tags(values: Any, *, labeler=None) -> str:
    if not isinstance(values, list) or not values:
        return "<span class='meta'>未提供</span>"
    return "".join(
        f"<span class='tag'>{_esc(labeler(str(item)) if labeler else item)}</span>"
        for item in values
    )


def _stage_label(stage: str) -> str:
    return STAGE_CN.get(stage, stage)


def _probe_type_label(probe_type: str) -> str:
    return {
        "current_understanding": "当前理解",
        "memory_invocation": "共享记忆调用",
        "state_transformation": "状态变化识别",
        "relational_boundary": "关系边界",
        "alienation_avoidance": "陌生化避免",
        "natural_detail": "自然细节使用",
    }.get(probe_type, probe_type)


def _paper_probe_label(paper_probe_id: str) -> str:
    return PAPER_PROBE_LABELS.get(paper_probe_id, paper_probe_id)


def _dimension_label(dimension_id: str) -> str:
    return DIMENSION_LABELS.get(dimension_id, dimension_id)


def _paper_count(summary: dict[str, Any], paper_probe_id: str) -> int:
    counts = summary.get("paper_probe_type_counts", {})
    if not isinstance(counts, dict):
        return 0
    return int(counts.get(paper_probe_id, 0))


def _primary_dimension_count(summary: dict[str, Any], dimension_id: str) -> int:
    counts = summary.get("primary_dimension_counts", {})
    if not isinstance(counts, dict):
        return 0
    return int(counts.get(dimension_id, 0))


def _probe_cell(day: dict[str, Any]) -> str:
    probes = [item for item in day.get("probe_insertions", []) if isinstance(item, dict)]
    if not probes:
        return "<span class='meta'>无</span>"
    rows = []
    for probe in probes:
        paper_probe_id = str(probe.get("paper_probe_id") or "")
        dimensions = [str(item) for item in probe.get("evaluation_dimension_ids", [])]
        rows.append(
            f"<code>{_esc(probe.get('probe_id'))}</code>"
            f"<br><span class='tag'>{_esc(paper_probe_id)} · {_esc(_paper_probe_label(paper_probe_id))}</span>"
            f"<br>{_tags(dimensions, labeler=_dimension_label)}"
            f"<br><span class='meta'>工程类型：{_esc(_probe_type_label(str(probe.get('probe_type'))))}</span>"
            f"<br>{_esc(probe.get('question'))}"
        )
    return "<br><br>".join(rows)


def _occupation_label(value: Any) -> str:
    text = str(value if value is not None else "")
    return OCCUPATION_CN.get(text, text)


def _family_label(value: Any) -> str:
    text = str(value if value is not None else "")
    return FAMILY_CN.get(text, text)


def _domain_label(value: str) -> str:
    return DOMAIN_CN.get(value, value)


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


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
