#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DAILY_INTERACTIONS = (
    REPO_ROOT
    / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "docs/p3_daily_interaction_demo5_report.html"
AAAI_PAPER_PATH = str(REPO_ROOT / "docs/references/aaai2027_remem_re.pdf")
DOCX_PATH = "/Users/tom/Desktop/Archetype_Guided_Persona_Event_Sampling_Implementation.docx"


STAGE_CN = {
    "initial": "初始提出",
    "recurrence": "再次出现",
    "turning_point": "转折判断",
    "partial_resolution": "部分处理",
    "reflection": "回看总结",
}

PROBE_CN = {
    "P1": "当前理解",
    "P2": "状态变化识别",
    "P3": "共享记忆调用",
    "P4": "自然细节使用",
    "P5": "关系边界",
    "P6": "陌生化避免",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Chinese HTML report for P3 daily interaction units."
    )
    parser.add_argument("--daily-interactions", type=Path, default=DEFAULT_DAILY_INTERACTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    daily_interactions = _load_json(args.daily_interactions)
    html_text = render_report(
        daily_interactions=daily_interactions,
        daily_interactions_path=args.daily_interactions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(*, daily_interactions: dict[str, Any], daily_interactions_path: Path) -> str:
    summary = daily_interactions.get("summary", {})
    validation = daily_interactions.get("validation", {})
    first_unit = _first_unit(daily_interactions)
    probed_unit = _first_probed_unit(daily_interactions) or first_unit
    parallel_day = _first_parallel_day(daily_interactions)
    persona_sections = "".join(
        _persona_section(persona)
        for persona in daily_interactions.get("personas", [])
        if isinstance(persona, dict)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>P3a Daily Interaction Units 报告</title>
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
    .parallel {{
      background: #fff4e5;
      border-color: #f0c57a;
      color: #8a4b00;
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
    .unit-row.parallel-row td {{ background: #fffaf2; }}
    .narrow td:first-child {{ width: 22%; }}
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
    .constraint-title {{
      margin: 16px 0 6px;
      font-weight: 700;
    }}
    .constraint-table td:first-child {{ width: 24%; }}
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
  <h1>I 生成报告：5 人 Daily Interaction Units</h1>
  <p class="meta">数据文件：<code>{_esc(str(daily_interactions_path))}</code></p>
  <p class="meta">关键依据：<code>{_esc(AAAI_PAPER_PATH)}</code> 的 <code>tau=(z,T,L,I,P)</code> 表示；项目生成规范来自 <code>{_esc(DOCX_PATH)}</code> 与当前 JSON 池。</p>

  {_status_block(validation)}

  <section class="grid">
    {_metric("Persona", summary.get("persona_count"), "人物数量")}
    {_metric("Calendar days", summary.get("calendar_day_count"), "保留日历天")}
    {_metric("Active days", summary.get("active_day_total"), "有互动的天")}
    {_metric("I units", summary.get("interaction_unit_count"), "互动单元")}
    {_metric("Parallel days", summary.get("parallel_day_total"), "同日多事件天")}
    {_metric("Probe links", summary.get("probe_link_count"), "prob 绑定数")}
  </section>

  <h2>这一步在 tau 中的位置</h2>
  <div class="formula">tau = (z, T, L, I, P)</div>
  <table class="narrow">
    <tr><th>组件</th><th>本项目当前含义</th><th>本轮状态</th></tr>
    <tr><td><code>z</code></td><td>一个具体 persona：来自 persona archetype JSON，经 P0 采样形成 5 人实例。</td><td>已完成</td></tr>
    <tr><td><code>T</code></td><td>30 天时间轴：包含 active/inactive day、并行事件天、事件 occurrence 排布。</td><td>已完成</td></tr>
    <tr><td><code>L</code></td><td>每个 persona 的长期事件线：事件类别、阶段序列、允许事实和禁止事实。</td><td>已完成</td></tr>
    <tr><td><code>I</code></td><td>可执行互动单元：scripted opening、follow-up 约束、scene boundary、message binding。</td><td><strong>本页执行</strong></td></tr>
    <tr><td><code>P</code></td><td>插入在 I 之后的 probe：P2/P3/P4/P5 等评测问题，只读，不写回用户事实。</td><td>已绑定到 I</td></tr>
  </table>

  <h2>阶段命名说明</h2>
  {_stage_naming_section()}

  <h2>I 生成过程：从 timeline 到 daily interaction units</h2>
  <ol>
    <li>读取 <code>timeline.json</code>。这里的最小执行单位不是日历日，而是每个 active day 内的 <code>event_occurrences[]</code>。</li>
    <li>对每个 occurrence 生成一个 <code>interaction_unit_id</code> 对应的 I unit。单日两个事件会生成两个 I unit，并共享同一个 <code>day_group_id</code>。</li>
    <li><code>scripted_opening.user_message</code> 直接继承 timeline 的 <code>surface_event</code>，因此不是自由生成的新事实。</li>
    <li><code>constrained_followup</code> 用规则模板生成：按 stage 选择允许话术动作，限制 follow-up 次数，并列出 reveal steps 和 stop conditions。</li>
    <li><code>scene_boundary</code> 从 persona_ref、event title、event summary、stage goal、allowed_new_facts、related_previous_days 中汇总允许事实。</li>
    <li>如果 occurrence 已经有 <code>probe_insertions[]</code>，则把 probe 绑定到同一个 <code>interaction_unit_id</code> 后面；probe 是只读评测，不改变事实边界。</li>
    <li>最后运行完整校验：每个 timeline occurrence 必须有一个 I unit；inactive day 不能有 unit；同日不能重复 event line；probe 的 insert_after 必须等于被绑定的 I unit。</li>
  </ol>
  {_implementation_detail_section()}

  <h2>I 的具体问题例子</h2>
  <div class="callout">
    下面高亮的“用户具体问题”就是 I 里面真正发给 agent 的开场句，也就是 <code>scripted_opening.user_message</code>。
    后面的“I 约束卡”是这条互动能怎么继续、能说哪些事实、不能新增什么事实的硬边界。
  </div>
  {_concrete_examples_section(first_unit=first_unit, probed_unit=probed_unit, parallel_day=parallel_day)}

  <h2>当前不是大模型生成</h2>
  {_non_llm_detail_section()}

  <h2>I Unit Schema</h2>
  {_schema_table()}

  <h2>并行事件处理</h2>
  {_parallel_block(parallel_day)}

  <h2>校验规则</h2>
  {_validation_table(validation)}

  <h2>样例 I Unit</h2>
  <div class="two-col">
    {_unit_snapshot(first_unit, "第一个 I unit")}
    {_unit_snapshot(probed_unit, "第一个带 probe 的 I unit")}
  </div>

  <h2>5 人明细</h2>
  {persona_sections}
</main>
</body>
</html>
"""


def _stage_naming_section() -> str:
    rows = [
        ("P3a 是什么", "项目内部阶段名，表示第 3 阶段的 a 子阶段：先把 timeline occurrence 转成 I interaction units。"),
        ("它不是论文里的 P3", "正式版论文 P3 指 Memory Invocation probe，是 probe 类型；这里 P3a 指工程生成阶段。"),
        ("为什么叫 P3a", "P0/P1/P2 已经分别完成 persona-event sampling、timeline/event lines、probe insertion；下一步开始生成 I，因此暂称 P3a。"),
        ("更准确的标题", "I 生成过程：从 timeline 到 daily interaction units。HTML 后续主标题优先用这个名称，P3a 只作为内部阶段别名。"),
    ]
    flow_rows = [
        ("P0", "抽样 persona 与事件组合", "sampled_personas.json / accepted_persona_event_sets.json"),
        ("P1", "构建 event lines 和 30 天 timeline", "event_lines_batch.json / timeline.json"),
        ("P2", "把 targeted probes 插入到具体 occurrence 后面", "probe_plan.json + timeline probe_insertions"),
        ("P3a", "把每个 event occurrence 转成可执行 I unit", "daily_interaction_units.json"),
        ("P3b", "可选：在 I unit 上自然化多轮用户话术", "暂未执行"),
        ("后续", "把 z,T,L,I,P 合成 tau 合同", "tau_contract.json"),
    ]
    return f"""
  <div class="callout">
    <code>P3a</code> 只是当前工程内部的阶段别名，不是 AAAI 论文里的 <code>P3 Memory Invocation</code> probe。
    为避免混淆，本报告把核心过程称为 <strong>I 生成过程</strong>。
  </div>
  {_simple_table(["问题", "解释"], rows, class_name="narrow")}
  {_simple_table(["阶段", "做什么", "主要产物"], flow_rows)}
"""


def _implementation_detail_section() -> str:
    step_rows = [
        (
            "1. 读取 timeline.json / event_occurrences[]",
            "这一点是在确定 I 的最小单位。30 天 timeline 里 day 是日历容器，真正要执行的互动是 active day 内的每个 event occurrence。这样同一天可以有两个不同事件，不会被压成一个混合问题。",
            "输入字段：timelines[].days[].active、days[].event_occurrences[]、event_occurrence_id、interaction_unit_id、day_interaction_unit_id。",
            "scripts/run_p3_daily_interaction_construction.py:37-44；src/long_memory_test/sampling/daily_interaction_constructor.py:16-47, 132-155, 635-643；timeline.json:125, 490-496。",
        ),
        (
            "2. occurrence -> interaction_unit_id -> I unit",
            "这一点是在建立一一对应关系：一个 occurrence 生成一个 I unit。I unit 是后续 agent 实际接收的一次互动单元；同日两个 occurrence 会生成 M001/M002 两个 unit，并共享同一个 day_group_id。",
            "输出字段：interaction_unit_id、event_occurrence_id、day_group_id、within_day_index、parallel_event_count、event_line_id。",
            "src/long_memory_test/sampling/daily_interaction_constructor.py:155-193, 211-264；timeline.json:490-573；daily_interaction_units.json:1865-1889。",
        ),
        (
            "3. scripted_opening.user_message 继承 surface_event",
            "这一点是在保证用户具体问题不是自由编出来的。timeline 已经为每个 occurrence 固定了 surface_event，I 只是把它放进 scripted_opening.user_message，作为 agent 真正看到的用户开场。",
            "输入字段：occurrence.surface_event、event_stage、stage_goal、assistant_memory_expectation。输出字段：scripted_opening.user_message、topic、intent、tone、conversation_goal。",
            "src/long_memory_test/sampling/daily_interaction_constructor.py:245, 267-279, 653-670；timeline.json:147, 512, 659；daily_interaction_units.json:1889-1899。",
        ),
        (
            "4. constrained_followup 规则模板",
            "这一点是在规定这次互动后续最多怎么继续。它不是生成 assistant 答案，而是限制模拟用户后续追问：最多几轮、能用哪些话术动作、每步最多透露哪些 fact/concern、什么时候停止。",
            "输出字段：followup_budget、permitted_conversational_moves、reveal_steps、stop_conditions、must_not_introduce、strict_scene_boundary。",
            "src/long_memory_test/sampling/daily_interaction_constructor.py:246-249, 282-311, 457-536；daily_interaction_units.json:1899-1969。",
        ),
        (
            "5. scene_boundary 汇总允许事实",
            "这一点是在给 agent/评测设事实边界。allowed_facts 定义这次 I 可以使用哪些事实，latent_concerns 定义用户没有明说但希望 agent 感知的关系性期待。边界外的内容不应该被模型补出来。",
            "输入字段：persona_ref、event_title、persistent_event_summary、event_stage、stage_goal、assistant_memory_expectation、allowed_new_facts、related_previous_days。输出字段：allowed_facts、allowed_fact_ids、latent_concerns、memory_level_rules、audit_dimensions。",
            "src/long_memory_test/sampling/daily_interaction_constructor.py:250-254, 314-354, 357-454；daily_interaction_units.json:1969-2145。",
        ),
        (
            "6. probe_insertions[] -> probe_links",
            "这一点是在把 P2 probe 挂到正确的 I 后面。probe 是只读评测问题，用来测试关系记忆/状态变化/边界等能力，不会写回用户事实；绑定必须落到具体 interaction_unit_id，而不是只落到日期。",
            "输入字段：occurrence.probe_insertions[].probe_id、paper_probe_id、event_occurrence_id、insert_after_message_id、question。输出字段：probe_links[].read_only=true。",
            "src/long_memory_test/sampling/daily_interaction_constructor.py:220-224, 568-580, 173-183, 583-608；timeline.json:682-684, 743-745；daily_interaction_units.json:2145-2221。",
        ),
        (
            "7. 完整校验",
            "这一点是在保证 I 合同没有漏项或错绑。校验会检查每个 timeline occurrence 都有 I、inactive day 不生成 unit、同日不重复同一 event line、probe 的 insert_after_message_id 必须等于对应 interaction_unit_id，并检查每个 unit 是否有 opening/followup/boundary。",
            "校验结果字段：validation.status、issues、warnings、unit_count、bound_probe_count。",
            "src/long_memory_test/sampling/daily_interaction_constructor.py:46, 50-129, 611-632；daily_interaction_units.json:33858。",
        ),
    ]
    input_rows = [
        ("timeline.json", "读取 5 个 persona 的 30 天时间轴，重点使用 days[].event_occurrences[]。"),
        ("persona_ref", "提供 source_archetype、occupation、family_structure、primary_life_domains 等稳定人物事实。"),
        ("event occurrence", "提供 event_line_id、event_stage、surface_event、allowed_new_facts、prohibited_facts、related_previous_days 等。"),
        ("probe_insertions", "如果 P2 已插入 probe，则复制到 I unit 的 probe_links，并绑定 insert_after_message_id。"),
    ]
    function_rows = [
        ("construct_daily_interactions_for_timeline", "批处理入口；遍历所有 persona timeline，汇总 summary，并调用 validation。"),
        ("_construct_persona_interactions", "处理单个 persona 的 30 天；inactive day 保留为空，active day 转成 interaction_units。"),
        ("_day_event_occurrences", "兼容新旧结构；优先读取 event_occurrences[]，没有时才退回 day 顶层事件。"),
        ("_build_interaction_unit", "把一个 occurrence 组装成一个 I unit，生成 opening、follow-up、scene boundary、probe links。"),
        ("_scripted_opening", "把 occurrence.surface_event 作为用户具体问题，并按 event_stage 生成 intent/tone。"),
        ("_constrained_followup", "生成 follow-up 预算、允许动作、reveal steps、stop conditions、must-not-introduce。"),
        ("_scene_boundary", "从 persona_ref 和 occurrence 中汇总 allowed_facts、latent_concerns、M0-M3 可见性说明。"),
        ("_message_binding", "把 opening/probe 映射回 persona_id、day、event_occurrence_id、event_line_id、interaction_unit_id。"),
        ("validate_daily_interactions", "校验 occurrence 是否都有 I、ID 是否重复、inactive day 是否为空、probe 是否绑定到正确 I。"),
    ]
    output_rows = [
        ("interaction_unit_id", "I 的主键，例如 P0001_D10_M001。"),
        ("scripted_opening", "用户真正问 agent 的开场句、目标、意图、语气。"),
        ("constrained_followup", "后续追问预算、允许动作、可透露 fact/concern、停止条件、禁止引入项。"),
        ("scene_boundary", "当前 I 可用事实和隐含担心，是防止模型编事实的边界。"),
        ("probe_links", "该 I 后面插入的评测 probe，read_only=true。"),
        ("message_bindings", "后续运行和评测时用于追踪每条 message 属于哪条 event line / occurrence。"),
    ]
    validation_rows = [
        ("完整性", "timeline 中每个 active occurrence 必须有一个 I unit。"),
        ("唯一性", "interaction_unit_id 不能重复。"),
        ("并行事件", "同一天可以有多个 I，但不能重复同一 event_line_id。"),
        ("事实隔离", "cross_occurrence_reference_allowed=false 时，同一天其他 occurrence 的事实不能自动混入。"),
        ("probe 绑定", "probe.insert_after_message_id 必须等于对应 interaction_unit_id。"),
        ("inactive day", "inactive day 不能生成 interaction_units。"),
    ]
    return f"""
  <h3>7 步过程逐条详解与引用位置</h3>
  {_simple_table(["步骤", "具体作用", "关键字段", "引用位置"], step_rows)}
  <h3>实现细节：输入层</h3>
  {_simple_table(["输入", "使用方式"], input_rows, class_name="narrow")}
  <h3>实现细节：函数层</h3>
  {_simple_table(["函数", "职责"], function_rows, class_name="narrow")}
  <h3>实现细节：输出字段</h3>
  {_simple_table(["输出字段", "含义"], output_rows, class_name="narrow")}
  <h3>实现细节：校验规则</h3>
  {_simple_table(["校验点", "规则"], validation_rows, class_name="narrow")}
"""


def _non_llm_detail_section() -> str:
    status_rows = [
        ("是否调用大模型", "否。当前 P3a 没有请求任何 LLM，也没有 prompt/completion 产物。"),
        ("生成方式", "确定性 Python constructor，输入相同的 timeline.json 会得到相同的 daily_interaction_units.json。"),
        ("实现入口", "src/long_memory_test/sampling/daily_interaction_constructor.py"),
        ("运行脚本", "scripts/run_p3_daily_interaction_construction.py"),
        ("HTML 报告脚本", "scripts/generate_p3_daily_interaction_report_html.py"),
        ("核心配置", "llm_generation_used=false；followup_budget_default=2；cross_occurrence_reference_allowed=false。"),
    ]
    provenance_rows = [
        ("scripted_opening.user_message", "直接复制", "timeline occurrence 的 surface_event。"),
        ("scripted_opening.intent/tone", "规则映射", "由 event_stage 映射，例如 initial -> introduce_current_concern，recurrence -> continue_recurring_event_line。"),
        ("constrained_followup.permitted_conversational_moves", "规则映射", "由 event_stage 选择允许动作，再追加 clarify_current_constraint / ask_for_small_next_step。"),
        ("constrained_followup.reveal_steps", "规则生成", "按 follow-up 预算生成 2 步，每步只能暴露 allowed_fact_ids / latent_concern_ids 的受限子集。"),
        ("scene_boundary.allowed_facts", "字段汇总", "persona_ref + event_title + persistent_event_summary + event_stage + stage_goal + allowed_new_facts + related_previous_days。"),
        ("scene_boundary.latent_concerns", "规则抽取", "从 stage_goal、latent_continuity、occurrence_index>=2 抽取隐含担心。"),
        ("must_not_introduce", "字段合并", "occurrence.prohibited_facts 加全局禁止项，例如不得引入新重大事件、同日其他 occurrence 事实、真实身份细节。"),
        ("probe_links", "直接绑定", "复制 occurrence.probe_insertions，并强制 read_only=true。"),
        ("message_bindings", "规则索引", "把 opening 和 probe 都绑定回 interaction_unit_id、event_occurrence_id、event_line_id、day_group_id。"),
    ]
    audit_rows = [
        ("可复现", "不依赖模型采样温度、供应商、上下文窗口或网络状态。"),
        ("可审计", "每个字段都能追溯到 timeline/persona/probe 或明确规则函数。"),
        ("防污染", "先固定 allowed_facts / must_not_introduce，再让后续 agent 回答，避免生成阶段提前污染评测事实。"),
        ("便于扩展", "P3a 先稳定生成 I 合同，P3b 再考虑自然化多轮对话。"),
    ]
    future_rows = [
        ("可接入位置", "P3b：在已生成 I unit 之上做自然语言改写或多轮展开。"),
        ("LLM 输入", "只能给定 scripted_opening、constrained_followup、scene_boundary、probe_links 的只读副本。"),
        ("LLM 输出", "只能输出更自然的用户话术或多轮用户 follow-up，不允许新增事实字段。"),
        ("必须保留", "原始 rule-template I、source field map、随机种子、validation report。"),
        ("必须校验", "输出不得越过 allowed_facts，不得违反 must_not_introduce，不得把 probe 答案泄露给被测 agent。"),
    ]
    pseudo_code = """for persona in timeline.timelines:
    for day in persona.days:
        for occurrence in day.event_occurrences:
            unit.scripted_opening.user_message = occurrence.surface_event
            unit.constrained_followup = build_stage_rule_template(occurrence.event_stage)
            unit.scene_boundary = collect_allowed_facts(persona_ref, occurrence)
            unit.probe_links = copy_probe_insertions_as_read_only(occurrence)
            validate(unit, timeline_occurrence, probe_binding)"""
    return f"""
  <div class="callout">
    本轮 P3a 是 deterministic constructor：<code>llm_generation_used=false</code>。
    这里的“模板”不是发给大模型的 prompt，而是 Python 规则模板。也就是说，当前 I 的用户问题、约束、allowed facts、probe 绑定都来自已有结构化数据和固定规则。
  </div>
  <h3>生成状态</h3>
  {_simple_table(["项目", "说明"], status_rows, class_name="narrow")}
  <h3>字段来源：哪些是复制，哪些是规则生成</h3>
  {_simple_table(["字段", "生成方式", "具体来源"], provenance_rows)}
  <h3>规则模板伪代码</h3>
  <div class="code-block">{_esc(pseudo_code)}</div>
  <h3>为什么这一层先不用 LLM</h3>
  {_simple_table(["原因", "说明"], audit_rows, class_name="narrow")}
  <h3>如果后续使用 LLM，应放在 P3b</h3>
  {_simple_table(["约束", "说明"], future_rows, class_name="narrow")}
  <h3>当前规则模板责任边界</h3>
  {_template_table()}
"""


def _template_table() -> str:
    rows = [
        (
            "scripted_opening",
            "timeline occurrence",
            "<event_surface> = occurrence.surface_event；intent/tone 由 event_stage 映射。",
        ),
        (
            "constrained_followup",
            "timeline_occurrence_rule_template",
            "followup_budget=2；按 stage 选择 permitted moves；每步只允许透露 allowed_fact_ids/latent_concern_ids 的受限子集。",
        ),
        (
            "scene_boundary",
            "timeline_occurrence_and_persona_ref",
            "allowed_facts = persona_ref + event_title + persistent_event_summary + stage_goal + allowed_new_facts + related_previous_days。",
        ),
        (
            "must_not_introduce",
            "event prohibited_facts + global guardrails",
            "不得引入 timeline 外重大事件、同日其他 occurrence 事实、真实姓名/地址/收入/诊断/法律结论等。",
        ),
        (
            "probe_links",
            "P2 probe insertion result",
            "只复制 probe_insertions；read_only=true；insert_after_message_id 必须等于 interaction_unit_id。",
        ),
    ]
    return _simple_table(
        ["字段", "来源", "模板逻辑"],
        rows,
        class_name="narrow",
    )


def _schema_table() -> str:
    rows = [
        ("interaction_unit_id", "可执行互动单元 ID，例如 P0001_D12_M001。"),
        ("event_occurrence_id", "来自 timeline 的 occurrence ID，保证 I 与 T/L 对齐。"),
        ("scripted_opening", "用户第一句、意图、语气、当前 conversation_goal。"),
        ("constrained_followup", "允许追问/补充方式、follow-up 预算、reveal steps、stop conditions。"),
        ("scene_boundary", "允许事实、隐含担心、M0-M3 可见性说明、审计维度。"),
        ("probe_links", "绑定在该 I unit 后面的 P 类 probe，read_only=true。"),
        ("message_bindings", "把 scripted opening 与 probe 都映射回同一个 occurrence 和 event line。"),
    ]
    return _simple_table(["字段", "说明"], rows, class_name="narrow")


def _concrete_examples_section(
    *,
    first_unit: dict[str, Any] | None,
    probed_unit: dict[str, Any] | None,
    parallel_day: dict[str, Any] | None,
) -> str:
    examples = [
        _question_example(first_unit, "例 1：普通 I，用户当天直接问 agent"),
        _question_example(probed_unit, "例 2：带 probe 的 I，先正常互动，后面插入测试问题"),
    ]
    parallel_html = _parallel_question_examples(parallel_day)
    return "\n".join(item for item in [*examples, parallel_html] if item)


def _question_example(unit: dict[str, Any] | None, label: str) -> str:
    if not unit:
        return ""
    opening = unit.get("scripted_opening", {})
    followup = unit.get("constrained_followup", {})
    boundary = unit.get("scene_boundary", {})
    probes = [probe for probe in unit.get("probe_links", []) if isinstance(probe, dict)]
    probe_text = "无"
    if probes:
        probe_text = "<br>".join(
            f"{_esc(str(probe.get('paper_probe_id', '')))}：{_esc(str(probe.get('question', '')))}"
            for probe in probes
        )
    rows = [
        ("I unit", f"<code>{_esc(str(unit.get('interaction_unit_id')))}</code>"),
        ("日期", f"D{_esc(str(unit.get('day')).zfill(2))}"),
        ("事件线", _esc(_title(unit))),
        ("阶段", _esc(STAGE_CN.get(str(unit.get("event_stage")), str(unit.get("event_stage"))))),
        ("本次互动目标", _esc(str(opening.get("conversation_goal", "")))),
        ("后续追问预算", _esc(str(followup.get("followup_budget", ""))) + " 轮"),
        ("允许事实边界", _esc(str(len(boundary.get("allowed_facts", [])))) + " 条 allowed facts"),
        ("后接 probe", probe_text),
    ]
    return f"""
<section class="example-box">
  <div class="example-head">{_esc(label)}</div>
  <div class="example-body">
    <p class="meta">这条 I 的核心就是下面这句用户问题：</p>
    <div class="question">{_esc(str(opening.get("user_message", "")))}</div>
    {_simple_table(["项", "内容"], rows, class_name="narrow", escape_cells=False)}
    {_constraints_card(unit)}
  </div>
</section>
"""


def _parallel_question_examples(day: dict[str, Any] | None) -> str:
    if not day:
        return ""
    units = [
        unit for unit in day.get("interaction_units", []) if isinstance(unit, dict)
    ]
    rows = [
        (
            f"#{unit.get('within_day_index')}",
            unit.get("interaction_unit_id"),
            _title(unit),
            STAGE_CN.get(str(unit.get("event_stage")), str(unit.get("event_stage"))),
            str(unit.get("scripted_opening", {}).get("user_message", "")),
        )
        for unit in units
    ]
    return f"""
<section class="example-box">
  <div class="example-head">例 3：同一天并行两个 I，两个问题互相隔离</div>
  <div class="example-body">
    <p class="meta">
      <code>{_esc(str(day.get("day_group_id")))}</code> 是第 {_esc(str(day.get("day")))} 天。
      两个 I unit 共享同一天，但 <code>cross_occurrence_reference_allowed=false</code>，所以不能自动把一个问题的事实混到另一个问题里。
    </p>
    {_simple_table(["日内序号", "I unit", "事件线", "阶段", "用户具体问题"], rows)}
    <div class="constraint-title">并行 I 的共同约束</div>
    {_simple_table(
        ["约束", "含义"],
        [
            ("同日事实隔离", "每个 I unit 只读取自己的 scene_boundary.allowed_facts，不自动合并同一天另一个 I 的事实。"),
            ("同日不重复同一事件线", "同一个 active day 内不会出现两条相同 event_line_id。"),
            ("probe 绑定到 occurrence", "probe 的 insert_after_message_id 指向具体 interaction_unit_id，而不是只指向日期。"),
        ],
        class_name="constraint-table",
    )}
  </div>
</section>
"""


def _constraints_card(unit: dict[str, Any]) -> str:
    followup = unit.get("constrained_followup", {})
    boundary = unit.get("scene_boundary", {})
    rows = [
        ("follow-up 预算", f"{_esc(str(followup.get('followup_budget', '')))} 轮"),
        ("允许动作", _move_tags(followup.get("permitted_conversational_moves", []))),
        ("reveal steps", _reveal_steps_detailed_html(followup.get("reveal_steps", []))),
        ("allowed facts 示例", _facts_html(boundary.get("allowed_facts", [])[:8])),
        ("latent concerns", _concerns_html(boundary.get("latent_concerns", [])[:6])),
        ("stop conditions", _list_html(followup.get("stop_conditions", []))),
        ("must-not-introduce", _list_html(followup.get("must_not_introduce", [])[:6])),
        (
            "并行隔离",
            "允许跨同日 occurrence 引用"
            if unit.get("cross_occurrence_reference_allowed")
            else "不允许自动引用同一天其他 occurrence 的事实",
        ),
    ]
    return f"""
    <div class="constraint-title">I 约束卡</div>
    {_simple_table(["约束项", "当前值"], rows, class_name="constraint-table", escape_cells=False)}
"""


def _parallel_block(day: dict[str, Any] | None) -> str:
    if not day:
        return '<div class="warning">当前数据没有发现并行事件天。</div>'
    units = [
        unit for unit in day.get("interaction_units", []) if isinstance(unit, dict)
    ]
    unit_rows = [
        (
            unit.get("within_day_index"),
            unit.get("interaction_unit_id"),
            unit.get("event_occurrence_id"),
            unit.get("event_line_id"),
            _title(unit),
            STAGE_CN.get(str(unit.get("event_stage")), str(unit.get("event_stage"))),
        )
        for unit in units
    ]
    return f"""
  <div class="callout">
    示例：<code>{_esc(str(day.get("day_group_id")))}</code> 第 {_esc(str(day.get("day")))} 天有 {len(units)} 个 I unit。
    本轮设置 <code>cross_occurrence_reference_allowed=false</code>，意思是两个事件虽然同一天发生，但每个 I unit 的 allowed facts 默认互相隔离，不自动串事实。
  </div>
  {_simple_table(["日内序号", "I unit", "Occurrence", "Event line", "事件", "阶段"], unit_rows)}
"""


def _validation_table(validation: dict[str, Any]) -> str:
    issues = validation.get("issues") or []
    warnings = validation.get("warnings") or []
    rows = [
        ("status", validation.get("status")),
        ("unit_count", validation.get("unit_count")),
        ("bound_probe_count", validation.get("bound_probe_count")),
        ("issues", "无" if not issues else "; ".join(str(item) for item in issues)),
        ("warnings", "无" if not warnings else "; ".join(str(item) for item in warnings)),
    ]
    return _simple_table(["校验项", "结果"], rows, class_name="narrow")


def _persona_section(persona: dict[str, Any]) -> str:
    units = _persona_units(persona)
    stage_counts = Counter(str(unit.get("event_stage")) for unit in units)
    probe_count = sum(len(unit.get("probe_links", [])) for unit in units)
    parallel_days = [
        day for day in persona.get("days", [])
        if isinstance(day, dict) and day.get("has_parallel_events")
    ]
    rows = []
    for unit in units:
        row_class = ' class="unit-row parallel-row"' if int(unit.get("parallel_event_count", 1)) > 1 else ""
        probes = unit.get("probe_links", [])
        rows.append(
            f"""<tr{row_class}>
  <td>D{_esc(str(unit.get("day")).zfill(2))} / #{_esc(str(unit.get("within_day_index")))}</td>
  <td><code>{_esc(str(unit.get("interaction_unit_id")))}</code><br><span class="meta">{_esc(str(unit.get("event_occurrence_id")))}</span></td>
  <td>{_esc(_title(unit))}<br><span class="meta">{_esc(str(unit.get("event_line_id")))}</span></td>
  <td>{_stage_label(unit)}</td>
  <td>{_esc(str(unit.get("scripted_opening", {}).get("user_message", "")))}</td>
  <td>{_probe_tags(probes)}</td>
</tr>"""
        )
    rows_html = "\n".join(rows)
    parallel_text = "、".join(f"D{int(day.get('day', 0)):02d}" for day in parallel_days) or "无"
    stage_text = " ".join(
        f'<span class="tag">{_esc(STAGE_CN.get(stage, stage))}: {count}</span>'
        for stage, count in sorted(stage_counts.items())
    )
    ref = persona.get("persona_ref", {})
    return f"""
<details class="persona">
  <summary>{_esc(str(persona.get("persona_id")))}：{_esc(str(ref.get("occupation", "")))}，I units={len(units)}，probe links={probe_count}</summary>
  <div class="details-body">
    <p class="meta">来源 archetype：<code>{_esc(str(ref.get("source_archetype", "")))}</code>；家庭结构：{_esc(str(ref.get("family_structure", "")))}；并行事件天：{_esc(parallel_text)}</p>
    <p>{stage_text}</p>
    <table>
      <tr><th>日期/序号</th><th>I 与 occurrence</th><th>事件线</th><th>阶段</th><th>scripted opening</th><th>Probe</th></tr>
      {rows_html}
    </table>
  </div>
</details>
"""


def _unit_snapshot(unit: dict[str, Any] | None, title: str) -> str:
    if not unit:
        return '<div class="warning">没有可展示的 I unit。</div>'
    opening = unit.get("scripted_opening", {})
    followup = unit.get("constrained_followup", {})
    boundary = unit.get("scene_boundary", {})
    reveal_steps = followup.get("reveal_steps", [])
    probes = unit.get("probe_links", [])
    rows = [
        ("I unit", f"<code>{_esc(str(unit.get('interaction_unit_id')))}</code>"),
        ("Occurrence", f"<code>{_esc(str(unit.get('event_occurrence_id')))}</code>"),
        ("事件", _esc(_title(unit))),
        ("阶段", _stage_label(unit)),
        ("用户开场", _esc(str(opening.get("user_message", "")))),
        ("follow-up 预算", _esc(str(followup.get("followup_budget", "")))),
        ("允许动作", _move_tags(followup.get("permitted_conversational_moves", []))),
        ("reveal steps", _reveal_steps_html(reveal_steps)),
        ("allowed facts", _esc(str(len(boundary.get("allowed_facts", [])))) + " 条"),
        ("latent concerns", _esc(str(len(boundary.get("latent_concerns", [])))) + " 条"),
        ("must-not-introduce", _list_html(followup.get("must_not_introduce", [])[:4])),
        ("probe", _probe_tags(probes) if probes else "无"),
    ]
    return f"""
<section>
  <h3>{_esc(title)}</h3>
  {_simple_table(["项", "内容"], rows, class_name="narrow", escape_cells=False)}
</section>
"""


def _status_block(validation: dict[str, Any]) -> str:
    status = validation.get("status")
    if status == "pass":
        return '<div class="ok"><strong>校验状态：pass。</strong> 当前 I unit 与 timeline occurrence、probe insertion 的绑定关系完整。</div>'
    issues = validation.get("issues") or []
    return f'<div class="warning"><strong>校验状态：{_esc(str(status))}。</strong><br>{_esc("; ".join(str(item) for item in issues))}</div>'


def _metric(label: str, value: Any, caption: str) -> str:
    return f'<div class="metric"><strong>{_esc(str(value))}</strong><span>{_esc(label)} / {_esc(caption)}</span></div>'


def _simple_table(
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


def _persona_units(persona: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        unit
        for day in persona.get("days", [])
        if isinstance(day, dict)
        for unit in day.get("interaction_units", [])
        if isinstance(unit, dict)
    ]


def _first_unit(payload: dict[str, Any]) -> dict[str, Any] | None:
    for persona in payload.get("personas", []):
        if not isinstance(persona, dict):
            continue
        units = _persona_units(persona)
        if units:
            return units[0]
    return None


def _first_probed_unit(payload: dict[str, Any]) -> dict[str, Any] | None:
    for persona in payload.get("personas", []):
        if not isinstance(persona, dict):
            continue
        for unit in _persona_units(persona):
            if unit.get("probe_links"):
                return unit
    return None


def _first_parallel_day(payload: dict[str, Any]) -> dict[str, Any] | None:
    for persona in payload.get("personas", []):
        if not isinstance(persona, dict):
            continue
        for day in persona.get("days", []):
            if isinstance(day, dict) and day.get("has_parallel_events"):
                return day
    return None


def _title(unit: dict[str, Any]) -> str:
    value = unit.get("event_title", {})
    if isinstance(value, dict):
        return str(value.get("zh") or value.get("source") or unit.get("event_category_id", ""))
    return str(value or unit.get("event_category_id", ""))


def _stage_label(unit: dict[str, Any]) -> str:
    stage = str(unit.get("event_stage", ""))
    return f'<span class="tag">{_esc(STAGE_CN.get(stage, stage))}</span>'


def _probe_tags(probes: list[Any]) -> str:
    if not probes:
        return "无"
    tags = []
    for probe in probes:
        if not isinstance(probe, dict):
            continue
        paper_id = str(probe.get("paper_probe_id", ""))
        label = PROBE_CN.get(paper_id, str(probe.get("probe_type", paper_id)))
        tags.append(
            f'<span class="tag">{_esc(paper_id)} {_esc(label)}</span>'
            f'<br><span class="meta">{_esc(str(probe.get("probe_id", "")))}</span>'
        )
    return " ".join(tags)


def _move_tags(moves: list[Any]) -> str:
    tags = []
    for move in moves:
        if isinstance(move, dict):
            tags.append(f'<span class="tag">{_esc(str(move.get("move_id", "")))}</span>')
    return " ".join(tags) or "无"


def _reveal_steps_html(steps: list[Any]) -> str:
    if not steps:
        return "无"
    lines = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"#{_esc(str(step.get('followup_index')))} "
            f"{_esc(str(step.get('instruction', '')))}"
        )
    return "<br>".join(lines)


def _reveal_steps_detailed_html(steps: list[Any]) -> str:
    if not steps:
        return "无"
    lines = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        fact_ids = ", ".join(str(item) for item in step.get("may_reveal_fact_ids", [])[:4])
        concern_ids = ", ".join(str(item) for item in step.get("may_reveal_concern_ids", [])[:3])
        detail = (
            f"#{_esc(str(step.get('followup_index')))} "
            f"{_esc(str(step.get('instruction', '')))}"
        )
        if fact_ids:
            detail += f"<br><span class=\"meta\">可透露 fact ids：{_esc(fact_ids)}</span>"
        if concern_ids:
            detail += f"<br><span class=\"meta\">可透露 concern ids：{_esc(concern_ids)}</span>"
        lines.append(detail)
    return "<br>".join(lines)


def _facts_html(facts: list[Any]) -> str:
    if not facts:
        return "无"
    lines = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        fact_type = str(fact.get("type", "fact"))
        fact_text = str(fact.get("text", ""))
        fact_id = str(fact.get("fact_id", ""))
        lines.append(
            f'<span class="tag">{_esc(fact_type)}</span> {_esc(fact_text)}'
            f'<br><span class="meta">{_esc(fact_id)}</span>'
        )
    return "<br>".join(lines)


def _concerns_html(concerns: list[Any]) -> str:
    if not concerns:
        return "无"
    lines = []
    for concern in concerns:
        if not isinstance(concern, dict):
            continue
        source = str(concern.get("source", "concern"))
        text = str(concern.get("text", ""))
        concern_id = str(concern.get("concern_id", ""))
        lines.append(
            f'<span class="tag">{_esc(source)}</span> {_esc(text)}'
            f'<br><span class="meta">{_esc(concern_id)}</span>'
        )
    return "<br>".join(lines)


def _list_html(items: list[Any]) -> str:
    if not items:
        return "无"
    return "<br>".join(_esc(str(item)) for item in items)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
