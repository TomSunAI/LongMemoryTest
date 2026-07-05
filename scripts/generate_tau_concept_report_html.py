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
DEFAULT_PROBE_PLAN = (
    REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json"
)
DEFAULT_CONFIG = REPO_ROOT / "long_memory_experiment/data/sampling/sampling_config.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs/tau_timeline_concept_report.html"
AAAI_PAPER_PATH = str(REPO_ROOT / "docs/references/aaai2027_remem_re.pdf")
DOCX_PATH = "/Users/tom/Desktop/Archetype_Guided_Persona_Event_Sampling_Implementation.docx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate tau concept explanation report.")
    parser.add_argument("--timeline", type=Path, default=DEFAULT_TIMELINE)
    parser.add_argument("--probe-plan", type=Path, default=DEFAULT_PROBE_PLAN)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timeline = _load_json(args.timeline)
    probe_plan = _load_json(args.probe_plan)
    config = _load_json(args.config)
    html_text = render_report(
        timeline=timeline,
        probe_plan=probe_plan,
        config=config,
        timeline_path=args.timeline,
        probe_plan_path=args.probe_plan,
        config_path=args.config,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(
    *,
    timeline: dict[str, Any],
    probe_plan: dict[str, Any],
    config: dict[str, Any],
    timeline_path: Path,
    probe_plan_path: Path,
    config_path: Path,
) -> str:
    summary = timeline.get("summary", {})
    timeline_config = timeline.get("construction_config", {})
    probe_summary = probe_plan.get("summary", {})
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>tau=(z,T,L,I,P) 与 Timeline 概念说明</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #58636d;
      --line: #d8e1e8;
      --soft: #f6f8fb;
      --accent: #1457c8;
      --warn: #8a4b00;
      --warn-bg: #fff7e8;
      --ok-bg: #edf7f0;
      --chip: #eef4ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #fff;
      font: 15px/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 34px 26px 72px; }}
    h1, h2, h3 {{ margin: 0; line-height: 1.28; }}
    h1 {{ font-size: 30px; }}
    h2 {{ margin-top: 34px; padding-top: 22px; border-top: 1px solid var(--line); font-size: 22px; }}
    h3 {{ margin-top: 18px; font-size: 17px; }}
    p {{ margin: 8px 0; }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: #edf1f5;
      padding: 1px 4px;
      border-radius: 4px;
    }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin: 14px 0 20px; }}
    th, td {{ border: 1px solid var(--line); padding: 8px 9px; vertical-align: top; word-break: break-word; }}
    th {{ background: var(--soft); text-align: left; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
    .metric {{ border: 1px solid var(--line); border-radius: 8px; padding: 11px 12px; background: #fff; }}
    .metric strong {{ display: block; font-size: 22px; line-height: 1.2; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .callout {{ margin: 16px 0; padding: 13px 15px; background: var(--soft); border-left: 4px solid var(--accent); }}
    .warning {{ margin: 16px 0; padding: 13px 15px; background: var(--warn-bg); border-left: 4px solid var(--warn); }}
    .ok {{ margin: 16px 0; padding: 13px 15px; background: var(--ok-bg); border-left: 4px solid #26834a; }}
    .tag {{ display: inline-block; margin: 2px 4px 2px 0; padding: 2px 7px; border-radius: 999px; background: var(--chip); border: 1px solid #d6e5ff; font-size: 12px; }}
    .formula {{ font-size: 24px; font-weight: 700; letter-spacing: 0; margin: 12px 0 4px; }}
    .logic-list {{ margin: 12px 0 18px; padding-left: 22px; }}
    .logic-list li {{ margin: 7px 0; }}
    .source-table td:first-child {{ width: 18%; }}
    @media (max-width: 900px) {{
      main {{ padding: 24px 14px 56px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>tau=(z,T,L,I,P) 与 Timeline 概念说明</h1>
  <p class="meta">生成依据：<code>{_esc(AAAI_PAPER_PATH)}</code>、<code>{_esc(DOCX_PATH)}</code>、<code>{_esc(_rel(config_path))}</code>、<code>{_esc(_rel(timeline_path))}</code>、<code>{_esc(_rel(probe_plan_path))}</code></p>

  <section>
    <h2>一句话结论</h2>
    <div class="callout">
      当前项目以 AAAI 2027 论文 <strong>How Agents Remember the Relationship: Evaluating Relational Memory</strong>
      中的 ReMem-RE 框架为最高研究口径。论文给出长期关系记忆评估的轨迹合同
      <code>tau=(z,T,L,I,P)</code>；docx 和 sampling config 给出第一阶段规模；当前代码把这些要求落成
      可复现的 5 人、30 天、并行事件 timeline 与 probe plan。
    </div>
    <div class="grid">
      {_metric("Persona", summary.get("persona_count", "-"), "z 的实例数")}
      {_metric("Event lines", summary.get("event_line_count", "-"), "L")}
      {_metric("Occurrences", summary.get("event_occurrence_total", "-"), "timeline 事件节点")}
      {_metric("Active days", summary.get("active_day_total", "-"), "日历分布")}
      {_metric("Parallel days", summary.get("parallel_event_day_total", "-"), "同日多事件")}
      {_metric("Probes", probe_summary.get("probe_count", summary.get("probe_count_total", "-")), "P")}
      {_metric("Probe range", f"{probe_summary.get('probes_per_persona_min', '-')}-{probe_summary.get('probes_per_persona_max', '-')}", "每人")}
      {_metric("Validation", f"{timeline.get('validation', {}).get('status', '-')}/{probe_plan.get('validation', {}).get('status', '-')}", "timeline/probe")}
    </div>
  </section>

  <section>
    <h2>AAAI 论文口径</h2>
    <p>
      本项目当前以用户指定的 <code>{_esc(AAAI_PAPER_PATH)}</code> 为关键论文依据。当前读取记录显示，
      该论文题名为 <strong>How Agents Remember the Relationship: Evaluating Relational Memory</strong>，
      框架名为 <strong>ReMem-RE</strong>，研究目标是评估长期互动中 agent 是否能回应关系性期待，而不是只做普通事实回忆。
    </p>
    <div class="formula">tau = (z, T, L, I, P)</div>
    <p class="meta">tau 是一个受控长期互动轨迹合同，用来把人物、事件、事件线、互动单元和 probe 放在同一套可审计坐标中。</p>
    <table>
      <thead><tr><th>符号</th><th>论文含义</th><th>本项目中文解释</th><th>当前工程落点</th><th>状态</th></tr></thead>
      <tbody>
        <tr><td><code>z</code></td><td>sampled user persona</td><td>被采样出来的用户人物实例。</td><td><code>sampled_personas.json</code>、timeline 中的 <code>persona_ref</code>。</td><td>已生成 5 人。</td></tr>
        <tr><td><code>T</code></td><td>accepted event categories</td><td>经 persona-event compatibility 验证后被接受的事件类别。</td><td><code>accepted_persona_event_sets.json</code>；来源为事件池 JSON。</td><td>已生成。</td></tr>
        <tr><td><code>L</code></td><td>recurring event lines</td><td>跨天反复推进的持续事件线，不是一次性故事。</td><td><code>event_lines_batch.json</code>；当前 5 人合计 {_esc(summary.get("event_line_count", "-"))} 条。</td><td>已生成。</td></tr>
        <tr><td><code>I</code></td><td>daily interaction units</td><td>可运行的每日互动单元，包含 scripted opening、follow-up 边界、allowed facts 等。</td><td>当前 timeline 是 I 的前置结构；后续应生成 <code>daily_interaction_units.json</code>。</td><td>待推进。</td></tr>
        <tr><td><code>P</code></td><td>inserted targeted relational probes</td><td>插入式关系记忆测试问题，用于考察共享上下文、状态变化、关系边界等。</td><td><code>probe_plan.json</code>；当前共 {_esc(probe_summary.get("probe_count", "-"))} 条。</td><td>已生成。</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>概念映射</h2>
    <table>
      <thead><tr><th>当前概念</th><th>属于 tau 哪一层</th><th>含义</th><th>是否论文原生概念</th><th>当前出处</th></tr></thead>
      <tbody>
        <tr><td><code>persona</code></td><td><code>z</code></td><td>一个被采样出来的模拟用户，包括职业、家庭结构、生活领域等。</td><td>是，作为 sampled user persona。</td><td>人物池 JSON + P0 采样。</td></tr>
        <tr><td><code>event category / event theme</code></td><td><code>T</code></td><td>候选生活事件主题，如通勤、住房、家庭责任、消费纠纷。</td><td>是，正式版称为 accepted event categories。</td><td>事件池 JSON + accepted event set。</td></tr>
        <tr><td><code>event line</code></td><td><code>L</code></td><td>一个主题展开成跨天持续事件线，带阶段序列和用户消息种子。</td><td>是，作为 recurring event lines。</td><td>P1 event line construction。</td></tr>
        <tr><td><code>event occurrence</code></td><td><code>L -> I</code> 的中间节点</td><td>某条 event line 在某一天的第 N 次出现，是 timeline 的最小事件节点。</td><td>不是论文顶层符号，是工程落地概念。</td><td>timeline constructor。</td></tr>
        <tr><td><code>occurrence round</code></td><td><code>L</code> 的排布策略</td><td>出现轮次：先排所有事件线第 1 次，再排第 2 次，再排第 3 次。</td><td>不是论文原生概念，是工程策略。</td><td><code>_interleaved_tokens()</code>。</td></tr>
        <tr><td><code>active session</code></td><td><code>I</code> 的前置计数</td><td>当前指事件 occurrence / interaction session 总数，不再等于日历天。</td><td>docx/配置给规模，具体语义由工程定义。</td><td>sampling config + timeline validation。</td></tr>
        <tr><td><code>active day</code></td><td><code>I</code> 的日历容器</td><td>30 天中有事件发生的日历日。当前一天可以包含 1-{_esc(timeline_config.get("max_events_per_active_day", "-"))} 条 occurrence；0 条的是 inactive day。</td><td>不是论文顶层符号，是工程容器。</td><td>timeline constructor。</td></tr>
        <tr><td><code>parallel event day</code></td><td><code>I</code> 的日历结构</td><td>同一个 active day 里有多条事件 occurrence，模拟真实生活多线并行。</td><td>不是论文规定，是本轮工程修正。</td><td><code>max_events_per_active_day={_esc(timeline_config.get("max_events_per_active_day", "-"))}</code>、<code>parallel_event_days_min={_esc(timeline_config.get("parallel_event_days_min", "-"))}</code>。</td></tr>
        <tr><td><code>interaction_unit_id</code></td><td><code>I</code></td><td>每条 occurrence 的互动锚点，例如同一天可有 <code>M001</code>、<code>M002</code>。</td><td>论文要求 I 可审计；ID 是工程实现。</td><td>timeline constructor。</td></tr>
        <tr><td><code>probe</code></td><td><code>P</code></td><td>定向关系 probe，不是 probability。它插在具体 occurrence 后，且不写回记忆。</td><td>是，论文有 targeted relational probes；当前文案为工程模板。</td><td>P2 probe constructor。</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>Timeline 排布逻辑详解</h2>
    <ol class="logic-list">
      <li><strong>输入不是自由故事。</strong>先从 P0/P1 产物读取每个 persona 的 event lines；当前 5 人共有 {_esc(summary.get("event_line_count", "-"))} 条 event line。</li>
      <li><strong>先定日历密度。</strong>当前每个 persona 的每日事件数分布固定为 {_esc(_format_histogram(timeline_config.get("daily_event_count_distribution", {})))}，因此每人 occurrence 总数固定为 {_esc(summary.get("active_sessions_per_persona_min", "-"))}，日历中位数为 {_esc(summary.get("daily_event_count_median_calendar", "-"))}。</li>
      <li><strong>再定每条线出现几次。</strong>每条 event line 至少 {_esc(timeline_config.get("event_line_occurrences_min", "-"))} 次、最多 {_esc(timeline_config.get("event_line_occurrences_max", "-"))} 次；总数必须满足上一步的固定日历密度。</li>
      <li><strong>阶段由出现次数推进。</strong>第 1 次出现通常是 <code>initial</code>，第 2 次是 <code>recurrence</code>，后续按该 event line 的 <code>stage_sequence</code> 继续进入转折、部分处理或回看。高密度模式下若 occurrence 超过原始阶段数，且 <code>allow_stage_reuse_after_sequence=true</code>，则生成扩展阶段。</li>
      <li><strong>按出现轮次交错。</strong>先收集所有 event line 的第 1 次出现，再收集第 2 次出现，再收集第 3 次出现；每一轮内部随机打散，防止同一事件线连续堆叠。</li>
      <li><strong>再放入 30 天日历。</strong>当前不是先随机决定 active day 数量，而是先使用固定每日分布；每一天可有 0-{_esc(timeline_config.get("max_events_per_active_day", "-"))} 条 occurrence，并要求每人至少 {_esc(timeline_config.get("parallel_event_days_min", "-"))} 个并行事件日。</li>
      <li><strong>每条 occurrence 独立可追踪。</strong>同一天两条事件会生成两个 occurrence 级 ID，例如 <code>D08_M001</code>、<code>D08_M002</code>；probe 可以绑定到其中一条，而不是只绑定到“这一天”。</li>
      <li><strong>最后校验。</strong>校验 {_esc(timeline_config.get("timeline_days", "-"))} 天、{_esc(timeline_config.get("active_sessions_min", "-"))}-{_esc(timeline_config.get("active_sessions_max", "-"))} sessions、每条线 {_esc(timeline_config.get("event_line_occurrences_min", "-"))}-{_esc(timeline_config.get("event_line_occurrences_max", "-"))} 次出现、每日分布和中位数、单日事件数不超过上限、同日不重复同一 event line、阶段顺序不倒退，并保证每条线从第 1 阶段开始。</li>
    </ol>
    <div class="warning">
      这里要区分清楚：论文要求的是可审计的长期关系轨迹 <code>tau</code>；docx 要求的是第一阶段规模；
      <code>occurrence round</code>、<code>parallel event day</code>、固定每日事件数分布和
      <code>probe_candidate_min_per_persona</code> 是当前工程为了让轨迹可复现、可校验、能覆盖足够 probe 而加入的实现规则。
    </div>
  </section>

  <section>
    <h2>依据分层</h2>
    <table class="source-table">
      <thead><tr><th>层级</th><th>文件/来源</th><th>提供什么</th><th>不提供什么</th></tr></thead>
      <tbody>
        <tr><td>最高研究口径</td><td><code>{_esc(AAAI_PAPER_PATH)}</code><br>How Agents Remember the Relationship: Evaluating Relational Memory</td><td>ReMem-RE、relational expectation、<code>tau=(z,T,L,I,P)</code>、targeted probes、D1-D4 评估维度、M0-M3 记忆条件。</td><td>不规定我们的具体 5 人 demo 数量、具体中文事件、具体 occurrence round 算法；当前工程以 D1-D4 作为 probe 生成主轴。</td></tr>
        <tr><td>第一阶段工程要求</td><td><code>{_esc(DOCX_PATH)}</code><br><code>docs/archetype_guided_generation_basis.md</code></td><td>原始要求定义 5 人、30 天和可审计中间产物；当前已按本轮修正切换为高密度 timeline：每天 0-{_esc(timeline_config.get("max_events_per_active_day", "-"))} 个事件、中位数 {_esc(summary.get("daily_event_count_median_calendar", "-"))}。</td><td>不提供最终人物剧本，也不提供具体 probe 中文文案。</td></tr>
        <tr><td>受控素材池</td><td><code>persona_archetype_pool_v0.1.json</code><br><code>event_category_pool_v0.1_60events.json</code></td><td>人物 archetype、生活领域、事件类别、事件 domain、stage patterns 等素材边界。</td><td>不是最终样本；不能直接把池子当最终故事。</td></tr>
        <tr><td>机器配置</td><td><code>{_esc(_rel(config_path))}</code></td><td>随机种子、数量范围、并行事件约束、probe 候选下限。</td><td>不生成内容，只定义生成约束。</td></tr>
        <tr><td>工程实现</td><td><code>src/long_memory_test/sampling/timeline_constructor.py</code><br><code>src/long_memory_test/sampling/probe_constructor.py</code></td><td>确定性采样、timeline 排布、并行事件打包、probe 插入和校验。</td><td>不是论文原文；属于可审计实现。</td></tr>
        <tr><td>当前实例</td><td><code>{_esc(_rel(timeline_path))}</code><br><code>{_esc(_rel(probe_plan_path))}</code></td><td>当前 5 人 demo 的实际 timeline 和 probe plan。</td><td>只是当前随机种子的产物，不代表唯一可能样本。</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>当前完成度</h2>
    <div class="ok">
      当前 5 人 demo 已经完成 <code>z</code>、<code>T</code>、<code>L</code>、timeline occurrence 排布、
      <code>I</code> 和 <code>P</code>；P4 也已生成 <code>tau_contract.json</code>，
      把 <code>z,T,L,I,P</code> 固化为同一份可审计合同。
    </div>
    <table>
      <thead><tr><th>项目</th><th>当前值</th><th>说明</th></tr></thead>
      <tbody>
        <tr><td>第一阶段 persona</td><td>{_esc(config.get("num_personas", "-"))}</td><td>docx canonical demo，不是 100 人压力测试。</td></tr>
        <tr><td>timeline days</td><td>{_esc(config.get("timeline_days", "-"))}</td><td>每人 30 天时间池。</td></tr>
        <tr><td>active sessions</td><td>{_esc(summary.get("active_sessions_per_persona_min", "-"))}-{_esc(summary.get("active_sessions_per_persona_max", "-"))}</td><td>当前指事件 occurrence / interaction session。</td></tr>
        <tr><td>active days</td><td>{_esc(summary.get("active_days_per_persona_min", "-"))}-{_esc(summary.get("active_days_per_persona_max", "-"))}</td><td>有事件发生的日历日。</td></tr>
        <tr><td>parallel event days</td><td>{_esc(summary.get("parallel_event_days_per_persona_min", "-"))}-{_esc(summary.get("parallel_event_days_per_persona_max", "-"))}</td><td>每人同日多事件日。</td></tr>
        <tr><td>daily event histogram</td><td>{_esc(_format_histogram(summary.get("daily_event_count_histogram", {})))}</td><td>全体日历天上的事件数分布。</td></tr>
        <tr><td>daily event median</td><td>{_esc(summary.get("daily_event_count_median_calendar", "-"))}</td><td>按所有日历天计算。</td></tr>
        <tr><td>max events on single day</td><td>{_esc(summary.get("max_events_on_single_day", "-"))}</td><td>当前单日最多 {_esc(timeline_config.get("max_events_per_active_day", "-"))} 条事件。</td></tr>
        <tr><td>probes per persona</td><td>{_esc(probe_summary.get("probes_per_persona_min", "-"))}-{_esc(probe_summary.get("probes_per_persona_max", "-"))}</td><td>当前实际 probe 覆盖范围。</td></tr>
      </tbody>
    </table>
  </section>
</main>
</body>
</html>
"""


def _metric(value: str, number: Any, label: str) -> str:
    return (
        "<div class='metric'>"
        f"<strong>{_esc(number)}</strong>"
        f"<span>{_esc(value)} · {_esc(label)}</span>"
        "</div>"
    )


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


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
