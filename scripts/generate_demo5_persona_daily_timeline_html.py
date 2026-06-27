#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
TIMELINE_PATH = DATA_DIR / "timeline.json"
EVENT_LINES_PATH = DATA_DIR / "event_lines_batch.json"
SAMPLED_PERSONAS_PATH = DATA_DIR / "sampled_personas.json"
PROBE_PATH = DATA_DIR / "probe_plan.json"
P3B_PATH = DATA_DIR / "daily_interaction_naturalized_candidates_deepseek_all440.json"
OUTPUT = REPO_ROOT / "docs/demo5_persona_daily_timeline_detail.html"


STAGE_ZH = {
    "initial": "初始提出",
    "recurrence": "再次出现",
    "turning_point": "转折判断",
    "partial_resolution": "部分处理",
    "reflection": "回看总结",
}


def main() -> int:
    timeline = _load_json(TIMELINE_PATH)
    event_lines = _load_json(EVENT_LINES_PATH)
    sampled = _load_json(SAMPLED_PERSONAS_PATH)
    probe_plan = _load_json(PROBE_PATH)
    p3b = _load_json(P3B_PATH)

    zh_personas = {
        str(persona.get("persona_id")): persona
        for persona in sampled.get("locale_views", {}).get("zh", {}).get("personas", [])
        if isinstance(persona, dict)
    }
    lines_by_persona = _lines_by_persona(event_lines)
    OUTPUT.write_text(
        _render(
            timeline=timeline,
            zh_personas=zh_personas,
            lines_by_persona=lines_by_persona,
            probes_by_message=_probes_by_message(probe_plan),
            p3b_by_unit=_p3b_by_unit(p3b),
            probe_summary=probe_plan.get("summary", {}),
            p3b_summary=p3b.get("summary", {}),
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")
    return 0


def _render(
    *,
    timeline: dict[str, Any],
    zh_personas: dict[str, dict[str, Any]],
    lines_by_persona: dict[str, list[dict[str, Any]]],
    probes_by_message: dict[str, list[dict[str, Any]]],
    p3b_by_unit: dict[str, dict[str, Any]],
    probe_summary: dict[str, Any],
    p3b_summary: dict[str, Any],
) -> str:
    summary = timeline.get("summary", {})
    persona_sections = []
    for index, persona_timeline in enumerate(timeline.get("timelines", [])):
        if not isinstance(persona_timeline, dict):
            continue
        persona_id = str(persona_timeline.get("persona_id") or "")
        persona_sections.append(
            _persona_section(
                persona_timeline=persona_timeline,
                zh_persona=zh_personas.get(persona_id, {}),
                event_lines=lines_by_persona.get(persona_id, []),
                probes_by_message=probes_by_message,
                p3b_by_unit=p3b_by_unit,
                open_by_default=index == 0,
            )
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>5 人按天 Timeline 明细</title>
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
      max-width: 1360px;
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
    .hero, .persona, .box, .metric, .day-card, .occurrence {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .hero {{ padding: 18px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .metrics.secondary {{
      grid-template-columns: repeat(6, minmax(0, 1fr));
      margin-top: 10px;
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
    .day-cell.active {{
      background: #eaf7f5;
      border-color: #b8d9d4;
      color: var(--accent);
      font-weight: 800;
    }}
    .day-cell.parallel {{
      background: #fff7ed;
      border-color: #fed7aa;
      color: var(--warn);
    }}
    .line-index {{
      margin: 12px 0 18px;
    }}
    .day-list {{
      display: grid;
      gap: 12px;
    }}
    .day-card {{
      overflow: hidden;
    }}
    .day-card > header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    .day-card.inactive > header {{
      background: var(--empty);
    }}
    .occurrences {{
      display: grid;
      gap: 10px;
      padding: 12px;
    }}
    .occurrence {{
      overflow: hidden;
      background: #fff;
    }}
    .occurrence > header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .occurrence-body {{
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 12px;
      padding: 12px;
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
    .tag.empty {{ background: #f3f4f6; color: var(--muted); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
      word-break: break-word;
    }}
    th {{
      background: #f2f5f9;
      color: #344054;
      font-size: 12px;
    }}
    ul {{ margin: 0; padding-left: 18px; }}
    li + li {{ margin-top: 4px; }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 12px; }}
    .surface {{
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      white-space: pre-wrap;
    }}
    .p3b-block, .probe-block {{
      margin-top: 12px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
    }}
    .p3b-block {{
      border-left: 4px solid var(--blue);
    }}
    .probe-block {{
      border-left: 4px solid var(--warn);
    }}
    .p3b-block.missing, .probe-block.empty {{
      border-left-color: var(--muted);
      background: #f8fafc;
    }}
    .probe-card + .probe-card {{
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px dashed var(--line);
    }}
    .dialogue-label {{
      margin: 8px 0 4px;
      color: var(--muted);
      font-weight: 800;
      font-size: 12px;
    }}
    .p3b-text {{
      border-color: #c7d2fe;
      background: #f8faff;
    }}
    .probe-text {{
      border-color: #fed7aa;
      background: #fffaf3;
    }}
    @media (max-width: 980px) {{
      .metrics, .profile, .occurrence-body {{ grid-template-columns: 1fr; }}
      .calendar {{ grid-template-columns: repeat(10, minmax(24px, 1fr)); }}
      details.persona > summary, .day-card > header, .occurrence > header {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>5 人按天 Timeline 明细</h1>
      <p>本页把五个人的全部事件线重新整理成 30 天日历视图。每一天直接展示当天发生的 0-5 条事件、对应事件线 L、阶段、当天用户描述和事实变化。</p>
      <div class="metrics">
        {_metric("persona", summary.get("persona_count"))}
        {_metric("event lines", summary.get("event_line_count"))}
        {_metric("event occurrences", summary.get("event_occurrence_total"))}
        {_metric("active days", summary.get("active_day_total"))}
        {_metric("max/day", summary.get("max_events_on_single_day"))}
        {_metric("median/day", summary.get("daily_event_count_median_calendar"))}
      </div>
      <div class="metrics secondary">
        {_metric("Probe", probe_summary.get("probe_count"))}
        {_metric("P3B candidates", p3b_summary.get("candidate_count"))}
        {_metric("P3B pass", p3b_summary.get("pass_count"))}
        {_metric("P3B fail", p3b_summary.get("fail_count"))}
        {_metric("primary D", _counter_compact(probe_summary.get("primary_dimension_counts")))}
        {_metric("paper P", _counter_compact(probe_summary.get("paper_probe_type_counts")))}
      </div>
      <div class="source-note">
        <p><b>阅读方式：</b>每个人先看“事件线索引”知道有哪些 L，再看 30 天日历和 Day-by-Day 明细。每条 occurrence 现在同时展示：I/T 的当天描述、P3B 自然化后向 agent 发问的内容、以及正式插入的 Probe 测评题。</p>
        <p class="muted small">数据来源：<code>{_esc(TIMELINE_PATH.relative_to(REPO_ROOT))}</code> + <code>{_esc(EVENT_LINES_PATH.relative_to(REPO_ROOT))}</code> + <code>{_esc(PROBE_PATH.relative_to(REPO_ROOT))}</code> + <code>{_esc(P3B_PATH.relative_to(REPO_ROOT))}</code>。</p>
      </div>
    </section>
    {''.join(persona_sections)}
  </main>
</body>
</html>
"""


def _persona_section(
    *,
    persona_timeline: dict[str, Any],
    zh_persona: dict[str, Any],
    event_lines: list[dict[str, Any]],
    probes_by_message: dict[str, list[dict[str, Any]]],
    p3b_by_unit: dict[str, dict[str, Any]],
    open_by_default: bool,
) -> str:
    persona_id = str(persona_timeline.get("persona_id") or "")
    persona_ref = persona_timeline.get("persona_ref", {})
    days = [day for day in persona_timeline.get("days", []) if isinstance(day, dict)]
    occurrence_days = _occurrence_days(days)
    line_lookup = {str(line.get("event_line_id")): line for line in event_lines}
    line_day_lookup = _line_day_lookup(days)
    calendar = "".join(_calendar_cell(day) for day in days)
    line_index = _line_index(
        event_lines=event_lines,
        occurrence_counts=persona_timeline.get("event_line_occurrence_counts", {}),
        line_day_lookup=line_day_lookup,
    )
    day_cards = "".join(
        _day_card(
            day=day,
            line_lookup=line_lookup,
            probes_by_message=probes_by_message,
            p3b_by_unit=p3b_by_unit,
        )
        for day in days
    )
    open_attr = " open" if open_by_default else ""
    return f"""
    <details class="persona"{open_attr}>
      <summary>
        <div>
          <p class="muted"><code>{_esc(persona_id)}</code> · {_esc(zh_persona.get("source_archetype_label") or persona_ref.get("source_archetype_label_zh") or persona_ref.get("source_archetype"))}</p>
          <h2>{_esc(zh_persona.get("occupation") or persona_ref.get("occupation_zh") or persona_ref.get("occupation"))}</h2>
        </div>
        <div>
          <span class="tag">{_esc(persona_timeline.get("event_line_count"))} 条 L</span>
          <span class="tag blue">{_esc(persona_timeline.get("event_occurrence_total"))} 条 occurrence</span>
          <span class="tag warn">{_esc(persona_timeline.get("parallel_event_day_count"))} 个并行日</span>
        </div>
      </summary>
      <div class="persona-body">
        {_profile_html(zh_persona=zh_persona, persona_ref=persona_ref)}
        <h3>事件线索引</h3>
        <div class="line-index">{line_index}</div>
        <h3>30 天日历</h3>
        <div class="calendar">{calendar}</div>
        <p class="muted small">活跃天：{_esc(persona_timeline.get("active_day_count"))}；无事件天：{30 - len(occurrence_days)}；同日多事件天：{_esc(persona_timeline.get("parallel_event_day_count"))}。</p>
        <h3 style="margin-top:14px;">Day-by-Day 明细</h3>
        <div class="day-list">{day_cards}</div>
      </div>
    </details>
"""


def _profile_html(*, zh_persona: dict[str, Any], persona_ref: dict[str, Any]) -> str:
    rows = [
        ("年龄", zh_persona.get("age_range")),
        ("家庭结构", zh_persona.get("family_structure") or persona_ref.get("family_structure_zh")),
        ("经济条件", zh_persona.get("economic_condition")),
        ("社会支持", zh_persona.get("social_support")),
        ("主要生活领域", zh_persona.get("primary_life_domains") or persona_ref.get("primary_life_domains_zh")),
        ("长期目标", zh_persona.get("long_term_goals")),
        ("沟通风格", zh_persona.get("communication_style")),
        ("压力反应", zh_persona.get("stress_response")),
    ]
    return '<div class="profile">' + "".join(_field(label, value) for label, value in rows) + "</div>"


def _line_index(
    *,
    event_lines: list[dict[str, Any]],
    occurrence_counts: dict[str, Any],
    line_day_lookup: dict[str, list[int]],
) -> str:
    rows = []
    for index, line in enumerate(event_lines, start=1):
        line_id = str(line.get("event_line_id") or "")
        days = line_day_lookup.get(line_id, [])
        rows.append(
            (
                f"#{index}",
                _line_title(line),
                line.get("event_domain_zh") or line.get("event_domain"),
                occurrence_counts.get(line_id, len(days)),
                ", ".join(f"D{day:02d}" for day in days),
                line.get("persistent_event_summary_zh") or line.get("persistent_event_summary"),
            )
        )
    return _table(["序号", "L 标题", "领域", "出现次数", "出现日", "L 摘要"], rows)


def _day_card(
    *,
    day: dict[str, Any],
    line_lookup: dict[str, dict[str, Any]],
    probes_by_message: dict[str, list[dict[str, Any]]],
    p3b_by_unit: dict[str, dict[str, Any]],
) -> str:
    day_no = int(day.get("day") or 0)
    occurrences = _day_event_occurrences(day)
    if not occurrences:
        return f"""
        <article class="day-card inactive">
          <header>
            <div>
              <h3>Day {day_no:02d}</h3>
              <p class="muted">当天无事件发生。</p>
            </div>
            <span class="tag empty">0 event</span>
          </header>
        </article>
"""
    occurrence_cards = "".join(
        _occurrence_card(
            occurrence=occurrence,
            line=line_lookup.get(str(occurrence.get("event_line_id")), {}),
            probes=probes_by_message.get(str(occurrence.get("interaction_unit_id")), []),
            p3b=p3b_by_unit.get(str(occurrence.get("interaction_unit_id")), {}),
            total=len(occurrences),
        )
        for occurrence in occurrences
    )
    return f"""
        <article class="day-card">
          <header>
            <div>
              <h3>Day {day_no:02d}</h3>
              <p class="muted">当天发生 {len(occurrences)} 条事件 occurrence。</p>
            </div>
            <div>
              <span class="tag {'warn' if len(occurrences) > 1 else ''}">x{len(occurrences)}</span>
              <span class="tag blue">{_esc(day.get("day_group_id") or day.get("day_interaction_unit_id"))}</span>
            </div>
          </header>
          <div class="occurrences">{occurrence_cards}</div>
        </article>
"""


def _occurrence_card(
    *,
    occurrence: dict[str, Any],
    line: dict[str, Any],
    probes: list[dict[str, Any]],
    p3b: dict[str, Any],
    total: int,
) -> str:
    title = _occurrence_title(occurrence)
    previous_days = occurrence.get("related_previous_days", [])
    stage_facts = _fact_texts(occurrence.get("stage_delta_facts", []))
    probe_text = _probe_text(occurrence)
    source_event = line.get("source_event_category", {}) if isinstance(line, dict) else {}
    p3b_html = _p3b_html(p3b)
    probe_html = _probe_html(occurrence=occurrence, probes=probes)
    return f"""
          <section class="occurrence">
            <header>
              <div>
                <p class="muted">M{_esc(occurrence.get("within_day_index"))}/{total} · <code>{_esc(occurrence.get("interaction_unit_id"))}</code> · <code>{_esc(occurrence.get("event_occurrence_id"))}</code></p>
                <h4>{_esc(title)}</h4>
              </div>
              <div>
                <span class="tag">{_esc(STAGE_ZH.get(str(occurrence.get("event_stage")), occurrence.get("event_stage")))}</span>
                <span class="tag blue">第 {_esc(occurrence.get("occurrence_index"))}/{_esc(occurrence.get("occurrence_count_for_line"))} 次</span>
                {probe_text}
              </div>
            </header>
            <div class="occurrence-body">
              <div>
                <p class="muted"><code>{_esc(occurrence.get("event_line_id"))}</code> · {_esc(occurrence.get("event_domain_zh") or occurrence.get("event_domain"))}</p>
                <p style="margin:8px 0 4px;"><b>I/T 当天用户描述</b></p>
                <div class="surface">{_esc(occurrence.get("surface_event_zh") or occurrence.get("surface_event"))}</div>
                <p style="margin:8px 0 4px;"><b>当天事实变化</b></p>
                {_ul(stage_facts)}
                {p3b_html}
              </div>
              <div>
                {_table(["字段", "内容"], [
                    ("L 摘要", occurrence.get("persistent_event_summary_zh") or occurrence.get("persistent_event_summary") or line.get("persistent_event_summary_zh")),
                    ("阶段目标", occurrence.get("stage_goal_zh") or occurrence.get("stage_goal")),
                    ("助手记忆预期", occurrence.get("assistant_memory_expectation_zh") or occurrence.get("assistant_memory_expectation")),
                    ("前序天", ", ".join(f"D{int(day):02d}" for day in previous_days) if previous_days else "无"),
                    ("E core_issue", source_event.get("core_issue_zh") or occurrence.get("allowed_base_facts_zh", [""])[0]),
                ])}
                {probe_html}
              </div>
            </div>
          </section>
"""


def _p3b_html(p3b: dict[str, Any]) -> str:
    if not p3b:
        return """
                <div class="p3b-block missing">
                  <h4>P3B 向 agent 发问</h4>
                  <p class="muted">当前 I unit 没有找到 P3B 候选。</p>
                </div>
"""
    followups = p3b.get("followup_user_messages", [])
    if not isinstance(followups, list):
        followups = []
    followup_html = "".join(
        f'<p class="dialogue-label">follow-up {index}</p><div class="surface p3b-text">{_esc(text)}</div>'
        for index, text in enumerate(followups, start=1)
    )
    validation = p3b.get("validation", {}) if isinstance(p3b.get("validation"), dict) else {}
    fact_ids = p3b.get("fact_ids_used", []) if isinstance(p3b.get("fact_ids_used"), list) else []
    return f"""
                <div class="p3b-block">
                  <h4>P3B 向 agent 发问</h4>
                  <p class="dialogue-label">opening</p>
                  <div class="surface p3b-text">{_esc(p3b.get("opening_user_message"))}</div>
                  {followup_html}
                  <p class="muted small">validation={_esc(validation.get("status"))} · fact_ids_used={len(fact_ids)}</p>
                  {_fact_id_tags(fact_ids)}
                </div>
"""


def _probe_html(*, occurrence: dict[str, Any], probes: list[dict[str, Any]]) -> str:
    if not probes:
        candidate_note = "候选节点，但本轮未插入正式 Probe。" if occurrence.get("probe_candidate") else "当前节点不是 Probe 插入点。"
        return f"""
                <div class="probe-block empty">
                  <h4>Probe 测评题</h4>
                  <p class="muted">{_esc(candidate_note)}</p>
                </div>
"""
    probe_cards = []
    for probe in probes:
        primary = probe.get("primary_dimension", {})
        dimensions = probe.get("evaluation_dimensions", [])
        tom = probe.get("tom_assessment", {}) if isinstance(probe.get("tom_assessment"), dict) else {}
        ground_truth = probe.get("ground_truth", {}) if isinstance(probe.get("ground_truth"), dict) else {}
        probe_cards.append(
            f"""
                  <div class="probe-card">
                    <p>
                      <span class="tag warn">{_esc(probe.get("probe_id"))}</span>
                      <span class="tag">{_esc(probe.get("paper_probe_id"))} · {_esc(probe.get("paper_probe_zh") or probe.get("paper_probe_type"))}</span>
                      <span class="tag blue">{_esc(_dimension_label(primary))}</span>
                    </p>
                    <p class="dialogue-label">Probe 发问</p>
                    <div class="surface probe-text">{_esc(probe.get("question") or probe.get("user_message"))}</div>
                    {_table(["测评字段", "内容"], [
                        ("evaluation_dimensions", _dimension_list(dimensions)),
                        ("required_memory_type", probe.get("required_memory_type")),
                        ("hidden_user_need", tom.get("hidden_user_need")),
                        ("high_score_behavior", tom.get("high_score_behavior")),
                        ("low_score_behavior", tom.get("low_score_behavior")),
                    ])}
                    <p class="dialogue-label">Ground truth</p>
                    {_table(["Ground truth 字段", "内容"], [
                        ("current_stage", _nested_get(ground_truth, ["must_recognize", "current_stage"])),
                        ("current_state_change", _nested_get(ground_truth, ["must_recognize", "current_state_change"])),
                        ("previous_days", _nested_get(ground_truth, ["must_recognize", "previous_days"])),
                        ("expected_references", ground_truth.get("expected_references")),
                        ("acceptable_response", ground_truth.get("acceptable_response")),
                        ("reference_answer_zh", ground_truth.get("reference_answer_zh")),
                        ("reference_answer_usage", ground_truth.get("reference_answer_usage")),
                        ("failure_modes", ground_truth.get("failure_modes")),
                        ("must_not_claim", ground_truth.get("must_not_claim")),
                    ])}
                  </div>
"""
        )
    return f"""
                <div class="probe-block">
                  <h4>Probe 测评题</h4>
                  {''.join(probe_cards)}
                </div>
"""


def _calendar_cell(day: dict[str, Any]) -> str:
    day_no = int(day.get("day") or 0)
    count = len(_day_event_occurrences(day))
    classes = ["day-cell"]
    if count:
        classes.append("active")
    if count > 1:
        classes.append("parallel")
    label = f"D{day_no:02d}"
    detail = "无" if count == 0 else f"x{count}"
    return f'<div class="{" ".join(classes)}"><span>{label}</span><br><span>{detail}</span></div>'


def _lines_by_persona(event_lines_batch: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for item in event_lines_batch.get("personas", []):
        if not isinstance(item, dict):
            continue
        persona_id = str(item.get("construction_scope", {}).get("persona_id") or item.get("persona_id") or "")
        result[persona_id] = [
            line for line in item.get("event_lines", []) if isinstance(line, dict)
        ]
    return result


def _probes_by_message(probe_plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for probe in probe_plan.get("probe_questions", []):
        if not isinstance(probe, dict):
            continue
        message_id = str(probe.get("insert_after_message_id") or "")
        if message_id:
            result[message_id].append(probe)
    return dict(result)


def _p3b_by_unit(p3b: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(candidate.get("source_interaction_unit_id")): candidate
        for candidate in p3b.get("naturalized_dialogues", [])
        if isinstance(candidate, dict) and candidate.get("source_interaction_unit_id")
    }


def _line_day_lookup(days: list[dict[str, Any]]) -> dict[str, list[int]]:
    lookup: dict[str, set[int]] = defaultdict(set)
    for day in days:
        day_no = int(day.get("day") or 0)
        for occurrence in _day_event_occurrences(day):
            lookup[str(occurrence.get("event_line_id"))].add(day_no)
    return {line_id: sorted(values) for line_id, values in lookup.items()}


def _occurrence_days(days: list[dict[str, Any]]) -> set[int]:
    return {int(day.get("day") or 0) for day in days if _day_event_occurrences(day)}


def _day_event_occurrences(day: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = [
        item for item in day.get("event_occurrences", []) if isinstance(item, dict)
    ]
    if occurrences:
        return occurrences
    if day.get("active"):
        return [day]
    return []


def _occurrence_title(occurrence: dict[str, Any]) -> str:
    title = occurrence.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or occurrence.get("event_category_id") or "")
    return str(title or occurrence.get("event_category_id") or "")


def _line_title(line: dict[str, Any]) -> str:
    title = line.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or line.get("event_category_id") or "")
    return str(title or line.get("event_category_id") or "")


def _fact_texts(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text_zh") or item.get("text")
            if text:
                out.append(str(text))
        elif item not in (None, ""):
            out.append(str(item))
    return out


def _probe_text(occurrence: dict[str, Any]) -> str:
    probes = occurrence.get("probe_insertions", [])
    if isinstance(probes, list) and probes:
        ids = ", ".join(str(item.get("probe_id")) for item in probes if isinstance(item, dict))
        return f'<span class="tag warn">Probe { _esc(ids) }</span>'
    if occurrence.get("probe_candidate"):
        return '<span class="tag blue">probe candidate</span>'
    return ""


def _dimension_label(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("zh") or value.get("name") or value.get("id") or "")
    return _value_text(value)


def _dimension_list(values: Any) -> str:
    if not isinstance(values, list):
        return _value_text(values)
    labels = [_dimension_label(value) for value in values]
    return "；".join(label for label in labels if label)


def _nested_get(value: Any, path: list[str]) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return current


def _fact_id_tags(fact_ids: list[Any]) -> str:
    if not fact_ids:
        return '<p class="muted small">未声明 fact_ids_used。</p>'
    tags = "".join(f'<span class="tag blue">{_esc(fact_id)}</span>' for fact_id in fact_ids[:8])
    extra = "" if len(fact_ids) <= 8 else f'<span class="tag">+{len(fact_ids) - 8}</span>'
    return f"<p>{tags}{extra}</p>"


def _counter_compact(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    return " ".join(f"{key}:{count}" for key, count in value.items())


def _field(label: str, value: Any) -> str:
    return f'<div class="box"><b>{_esc(label)}</b><p>{_esc(_value_text(value))}</p></div>'


def _table(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    header_html = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    row_html = []
    for row in rows:
        row_html.append("<tr>" + "".join(f"<td>{_esc(_value_text(cell))}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(row_html)}</tbody></table>"


def _value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "；".join(str(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        return "；".join(f"{key}: {_value_text(item)}" for key, item in value.items())
    return str(value)


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><b>{_esc(value)}</b><span>{_esc(label)}</span></div>'


def _ul(values: list[str]) -> str:
    items = [f"<li>{_esc(value)}</li>" for value in values if value]
    if not items:
        return '<p class="muted">无</p>'
    return "<ul>" + "".join(items) + "</ul>"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


if __name__ == "__main__":
    raise SystemExit(main())
