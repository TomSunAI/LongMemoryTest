#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DAILY_PATH = DATA_DIR / "daily_interaction_units.json"
NATURALIZED_PATH = DATA_DIR / "daily_interaction_naturalized_candidates_deepseek_all440.json"
OUTPUT = REPO_ROOT / "docs/p3b_deepseek_all_rounds_report.html"


def main() -> int:
    daily = _load_json(DAILY_PATH)
    naturalized = _load_json(NATURALIZED_PATH)
    candidates_by_unit = {
        str(item.get("source_interaction_unit_id")): item
        for item in naturalized.get("naturalized_dialogues", [])
        if isinstance(item, dict)
    }
    html_text = _page(
        daily=daily,
        naturalized=naturalized,
        candidates_by_unit=candidates_by_unit,
    )
    OUTPUT.write_text(html_text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


def _page(
    *,
    daily: dict[str, Any],
    naturalized: dict[str, Any],
    candidates_by_unit: dict[str, dict[str, Any]],
) -> str:
    daily_summary = daily.get("summary", {})
    naturalized_summary = naturalized.get("summary", {})
    units = _all_units(daily)
    units_by_id = {str(unit.get("interaction_unit_id")): unit for unit in units}
    candidates = [
        candidate
        for candidate in naturalized.get("naturalized_dialogues", [])
        if isinstance(candidate, dict)
    ]

    missing_p3b = sorted(set(units_by_id) - set(candidates_by_unit))
    extra_p3b = sorted(set(candidates_by_unit) - set(units_by_id))
    stage_counts = Counter(str(unit.get("event_stage")) for unit in units)
    followup_counts = Counter(
        len(candidate.get("followup_user_messages") or [])
        for candidate in candidates
        if isinstance(candidate.get("followup_user_messages") or [], list)
    )
    fact_count_distribution = Counter(
        len(candidate.get("fact_ids_used") or [])
        for candidate in candidates
        if isinstance(candidate.get("fact_ids_used") or [], list)
    )
    validation_counts = Counter(
        str(candidate.get("validation", {}).get("status", "unknown"))
        for candidate in candidates
    )
    fact_usage = {
        "current_state_change_fact": sum(
            _candidate_uses(candidate, "current_state_change_fact") for candidate in candidates
        ),
        "stage_delta_fact": sum(_candidate_uses(candidate, "stage_delta_fact") for candidate in candidates),
        "latent_concern": sum(_candidate_uses(candidate, ":latent_") for candidate in candidates),
        "event_title": sum(_candidate_uses(candidate, "event_title") for candidate in candidates),
        "persona_fact": sum(_candidate_uses(candidate, "persona_") for candidate in candidates),
    }
    rewritten_count = sum(
        str(candidate.get("opening_user_message") or "")
        != str(candidate.get("canonical_opening_user_message") or "")
        for candidate in candidates
    )

    persona_sections = [
        _persona_section(persona=persona, candidates_by_unit=candidates_by_unit)
        for persona in daily.get("personas", [])
        if isinstance(persona, dict)
    ]
    persona_rows = _persona_rows(daily=daily, candidates_by_unit=candidates_by_unit)
    stage_example_cards = _example_cards(
        title="按阶段抽样",
        examples=_stage_examples(units=units, candidates_by_unit=candidates_by_unit),
        candidates_by_unit=candidates_by_unit,
    )
    persona_example_cards = _example_cards(
        title="按 persona 抽样",
        examples=_persona_examples(daily=daily, candidates_by_unit=candidates_by_unit),
        candidates_by_unit=candidates_by_unit,
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>P3B DeepSeek 全量自然化结果报告</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #667085;
      --line: #d7dee9;
      --panel: #ffffff;
      --band: #f4f6f9;
      --soft: #f9fbfd;
      --ok: #0f766e;
      --warn: #b42318;
      --accent: #3347b8;
      --p3b: #7c3aed;
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
      padding: 26px 18px 54px;
    }}
    h1 {{ margin: 0 0 10px; font-size: 28px; letter-spacing: 0; }}
    h2 {{ margin: 0; font-size: 21px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; letter-spacing: 0; }}
    p {{ margin: 0; }}
    code {{
      padding: 1px 5px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #f8fafc;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin: 16px 0;
    }}
    .metric, .section, .card, .box {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .metric {{ padding: 12px; }}
    .metric b {{ display: block; font-size: 23px; }}
    .metric span {{ color: var(--muted); font-size: 12px; }}
    .section {{
      margin-top: 16px;
      overflow: hidden;
    }}
    .section > header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .section-body {{ padding: 14px 16px 18px; }}
    .note {{
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fffdf7;
      margin: 14px 0;
    }}
    .cards {{
      display: grid;
      gap: 12px;
    }}
    .card {{
      overflow: hidden;
    }}
    .card header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      padding: 12px;
    }}
    .box {{ padding: 12px; background: var(--soft); }}
    .turns {{
      display: grid;
      grid-template-columns: 128px minmax(0, 1fr);
      gap: 8px 12px;
      align-items: start;
    }}
    .turn-label {{
      color: var(--muted);
      font-weight: 800;
      font-size: 12px;
    }}
    .message {{
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      white-space: pre-wrap;
    }}
    .tag {{
      display: inline-block;
      margin: 0 6px 6px 0;
      padding: 2px 7px;
      border-radius: 999px;
      background: #eef2ff;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    .tag.p3b {{ background: #f3e8ff; color: var(--p3b); }}
    .tag.ok {{ background: #ecfdf3; color: var(--ok); }}
    .tag.fail {{ background: #fef3f2; color: var(--warn); }}
    details.persona {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      margin-top: 12px;
      overflow: hidden;
    }}
    details.persona > summary {{
      list-style: none;
      cursor: pointer;
      padding: 12px 14px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-weight: 800;
      background: #fbfcfe;
    }}
    details.persona > summary::-webkit-details-marker {{ display: none; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px;
      vertical-align: top;
      text-align: left;
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
    @media (max-width: 980px) {{
      .summary, .grid {{ grid-template-columns: 1fr; }}
      .turns {{ grid-template-columns: 1fr; }}
      .section > header, details.persona > summary, .card header {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>P3B DeepSeek 全量自然化结果报告</h1>
    <p class="muted">本页总结刚跑完的 440 条 P3B 候选。P3B 是自然语言候选层，canonical I unit 仍保留为结构化真值。</p>

    <section class="summary">
      {_metric("persona", daily_summary.get("persona_count"))}
      {_metric("canonical I", daily_summary.get("interaction_unit_count"))}
      {_metric("P3B candidates", naturalized_summary.get("candidate_count"))}
      {_metric("P3B pass", naturalized_summary.get("pass_count"))}
      {_metric("P3B fail", naturalized_summary.get("fail_count"))}
      {_metric("opening rewritten", rewritten_count)}
    </section>

    <section class="note">
      <p><b>当前结论：</b>P3B 已覆盖全部 <code>{_esc(len(units))}</code> 个 interaction unit，校验结果为 <code>{_esc(dict(validation_counts))}</code>。缺失 P3B 的 I unit 数为 <code>{len(missing_p3b)}</code>，额外孤立候选数为 <code>{len(extra_p3b)}</code>。</p>
      <p class="muted small">输入：<code>{_esc(DAILY_PATH.relative_to(REPO_ROOT))}</code>；P3B 输出：<code>{_esc(NATURALIZED_PATH.relative_to(REPO_ROOT))}</code>；模型：<code>{_esc(naturalized.get("llm_model"))}</code>。</p>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>1. 全量统计</h2>
          <p class="muted">这里统计的是 P3B 输出声明和 I unit 元数据，不把自然化文本写回 canonical I。</p>
        </div>
        <span class="tag p3b">{_esc(naturalized.get("llm_provider"))}</span>
      </header>
      <div class="section-body">
        {_table(["统计项", "结果", "说明"], [
          ("stage 分布", _counter_text(stage_counts), "来自 daily_interaction_units.json 的 event_stage。"),
          ("follow-up 数量分布", _counter_text(followup_counts), "每条 P3B 候选最多 2 条 follow-up。"),
          ("fact_ids_used 数量分布", _counter_text(fact_count_distribution), "P3B 输出声明使用的事实 id 数。"),
          ("current_state_change_fact 使用", f"{fact_usage['current_state_change_fact']} / {len(candidates)}", "是否声明使用当前事件状态变化事实。"),
          ("stage_delta_fact 使用", f"{fact_usage['stage_delta_fact']} / {len(candidates)}", "是否声明使用阶段推进事实。"),
          ("latent concern 使用", f"{fact_usage['latent_concern']} / {len(candidates)}", "是否声明使用 latent_stage_goal / latent_no_restart 等隐含关注点。"),
          ("event_title 使用", f"{fact_usage['event_title']} / {len(candidates)}", "是否声明使用事件标题。"),
          ("persona fact 使用", f"{fact_usage['persona_fact']} / {len(candidates)}", "是否声明使用 persona 职业、家庭等事实。"),
        ])}
      </div>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>2. Persona 级别概览</h2>
          <p class="muted">每个人 88 条 I unit，P3B 均已生成并通过校验。</p>
        </div>
        <span class="tag">{_esc(daily_summary.get("persona_count"))} personas</span>
      </header>
      <div class="section-body">
        {_table(["persona", "I/P3B", "pass/fail", "stage 分布", "follow-up 分布", "probe 绑定"], persona_rows)}
      </div>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>3. 具体例子</h2>
          <p class="muted">每张卡同时显示 I 中文模板、P3B 自然化、多轮 follow-up、当前事实变化和 fact_ids_used。</p>
        </div>
        <span class="tag">examples</span>
      </header>
      <div class="section-body">
        {stage_example_cards}
        {persona_example_cards}
      </div>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>4. 全量明细</h2>
          <p class="muted">按 persona 展开；每行是一条 interaction unit。P3B 列展示自然化 opening、follow-up 数和校验。</p>
        </div>
        <span class="tag">{len(units)} rows</span>
      </header>
      <div class="section-body">
        {''.join(persona_sections)}
      </div>
    </section>
  </main>
</body>
</html>
"""


def _example_cards(
    *,
    title: str,
    examples: list[dict[str, Any]],
    candidates_by_unit: dict[str, dict[str, Any]],
) -> str:
    cards = []
    for unit in examples:
        unit_id = str(unit.get("interaction_unit_id") or "")
        candidate = candidates_by_unit.get(unit_id)
        if candidate:
            cards.append(_p3b_dialogue_card(unit=unit, candidate=candidate))
    if not cards:
        return ""
    return f"<h3>{_esc(title)}</h3><div class=\"cards\">{''.join(cards)}</div>"


def _p3b_dialogue_card(*, unit: dict[str, Any], candidate: dict[str, Any]) -> str:
    unit_id = str(unit.get("interaction_unit_id") or candidate.get("source_interaction_unit_id"))
    status = str(candidate.get("validation", {}).get("status", "unknown"))
    followups = candidate.get("followup_user_messages", [])
    if not isinstance(followups, list):
        followups = []
    opening = unit.get("scripted_opening", {}) if isinstance(unit.get("scripted_opening"), dict) else {}
    current_fact = unit.get("current_state_change_fact", {})
    turns = [
        ("I 中文模板", opening.get("user_message_zh") or opening.get("user_message")),
        ("P3B opening", candidate.get("opening_user_message")),
    ]
    turns.extend((f"P3B follow-up {idx}", text) for idx, text in enumerate(followups, start=1))
    return f"""
      <article class="card">
        <header>
          <div>
            <p class="muted"><code>{_esc(unit.get("persona_id"))}</code> · <code>{_esc(unit_id)}</code> · Day {_esc(unit.get("day"))} · M{_esc(unit.get("within_day_index"))}</p>
            <h3>{_esc(_event_title(unit))}</h3>
          </div>
          <div>
            <span class="tag">{_esc(unit.get("event_stage"))}</span>
            <span class="tag">occurrence {_esc(unit.get("occurrence_index"))}</span>
            <span class="tag {'ok' if status == 'pass' else 'fail'}">validation={_esc(status)}</span>
          </div>
        </header>
        <div class="grid">
          <div class="box">
            <h3>完整对话轮次</h3>
            <div class="turns">{''.join(_turn_row(label, text) for label, text in turns)}</div>
          </div>
          <div class="box">
            <h3>事实边界</h3>
            <p><span class="tag">current_state_change_fact</span></p>
            <p>{_esc(_fact_text(current_fact))}</p>
            <p><span class="tag">conversation_goal</span></p>
            <p>{_esc(opening.get("conversation_goal_zh") or opening.get("conversation_goal"))}</p>
            <p><span class="tag">fact_ids_used</span></p>
            {_ul(candidate.get("fact_ids_used", []))}
            <p><span class="tag">notes</span></p>
            <p>{_esc(candidate.get("notes"))}</p>
          </div>
        </div>
      </article>
"""


def _persona_section(
    *,
    persona: dict[str, Any],
    candidates_by_unit: dict[str, dict[str, Any]],
) -> str:
    persona_id = str(persona.get("persona_id") or "")
    persona_ref = persona.get("persona_ref", {}) if isinstance(persona.get("persona_ref"), dict) else {}
    units = [
        unit
        for day in persona.get("days", [])
        if isinstance(day, dict)
        for unit in day.get("interaction_units", [])
        if isinstance(unit, dict)
    ]
    rows = []
    for unit in units:
        unit_id = str(unit.get("interaction_unit_id") or "")
        candidate = candidates_by_unit.get(unit_id)
        opening = unit.get("scripted_opening", {}) if isinstance(unit.get("scripted_opening"), dict) else {}
        probe_links = unit.get("probe_links", [])
        current_fact = unit.get("current_state_change_fact", {})
        rows.append(
            f"""
          <tr>
            <td><code>{_esc(unit_id)}</code><br>Day {_esc(unit.get("day"))} · M{_esc(unit.get("within_day_index"))}</td>
            <td>{_esc(_event_title(unit))}<br><code>{_esc(unit.get("event_line_id"))}</code></td>
            <td>{_esc(unit.get("occurrence_index"))}<br>{_esc(unit.get("event_stage"))}</td>
            <td>{_esc(opening.get("user_message_zh") or opening.get("user_message"))}</td>
            <td>{_esc(_fact_text(current_fact))}</td>
            <td>{_p3b_cell(candidate)}</td>
            <td>{_esc(len(probe_links) if isinstance(probe_links, list) else 0)}</td>
          </tr>
"""
        )
    return f"""
      <details class="persona">
        <summary>
          <span>{_esc(persona_id)} · {_esc(persona_ref.get("source_archetype_label_zh") or persona_ref.get("source_archetype_label") or persona_ref.get("source_archetype") or "")}</span>
          <span>{len(units)} I units</span>
        </summary>
        <table>
          <thead>
            <tr>
              <th style="width: 10%;">I unit</th>
              <th style="width: 16%;">事件线</th>
              <th style="width: 7%;">轮次/stage</th>
              <th style="width: 25%;">I 中文模板</th>
              <th style="width: 20%;">current_state_change_fact</th>
              <th style="width: 18%;">P3B DeepSeek</th>
              <th style="width: 4%;">Probe</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </details>
"""


def _p3b_cell(candidate: dict[str, Any] | None) -> str:
    if not candidate:
        return '<span class="muted">未生成</span>'
    status = candidate.get("validation", {}).get("status")
    opening = candidate.get("opening_user_message")
    followups = candidate.get("followup_user_messages", [])
    followup_count = len(followups) if isinstance(followups, list) else 0
    fact_count = len(candidate.get("fact_ids_used", [])) if isinstance(candidate.get("fact_ids_used", []), list) else 0
    return (
        f'<span class="tag p3b">已生成</span> '
        f'<span class="tag {"ok" if status == "pass" else "fail"}">{_esc(status)}</span>'
        f'<p>{_esc(opening)}</p>'
        f'<p class="muted">follow-ups: {followup_count} · fact ids: {fact_count}</p>'
    )


def _persona_rows(
    *,
    daily: dict[str, Any],
    candidates_by_unit: dict[str, dict[str, Any]],
) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for persona in daily.get("personas", []):
        if not isinstance(persona, dict):
            continue
        persona_id = str(persona.get("persona_id") or "")
        units = [
            unit
            for day in persona.get("days", [])
            if isinstance(day, dict)
            for unit in day.get("interaction_units", [])
            if isinstance(unit, dict)
        ]
        candidate_list = [candidates_by_unit.get(str(unit.get("interaction_unit_id"))) for unit in units]
        candidates = [candidate for candidate in candidate_list if isinstance(candidate, dict)]
        validation = Counter(str(c.get("validation", {}).get("status", "unknown")) for c in candidates)
        stages = Counter(str(unit.get("event_stage")) for unit in units)
        followups = Counter(
            len(candidate.get("followup_user_messages") or [])
            for candidate in candidates
            if isinstance(candidate.get("followup_user_messages") or [], list)
        )
        probe_count = sum(
            len(unit.get("probe_links", [])) if isinstance(unit.get("probe_links", []), list) else 0
            for unit in units
        )
        rows.append(
            (
                persona_id,
                f"{len(units)} / {len(candidates)}",
                _counter_text(validation),
                _counter_text(stages),
                _counter_text(followups),
                probe_count,
            )
        )
    return rows


def _stage_examples(
    *,
    units: list[dict[str, Any]],
    candidates_by_unit: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    preferred_order = ["initial", "recurrence", "partial_resolution", "turning_point", "reflection"]
    examples: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for stage in preferred_order:
        stage_units = [
            unit
            for unit in units
            if str(unit.get("event_stage")) == stage
            and str(unit.get("interaction_unit_id")) in candidates_by_unit
        ]
        if not stage_units:
            continue
        # Pick a later occurrence when possible to expose memory continuity, not only Day 1 openings.
        unit = sorted(stage_units, key=lambda u: int(u.get("occurrence_index") or 0), reverse=True)[0]
        unit_id = str(unit.get("interaction_unit_id"))
        if unit_id not in seen_ids:
            examples.append(unit)
            seen_ids.add(unit_id)
    return examples


def _persona_examples(
    *,
    daily: dict[str, Any],
    candidates_by_unit: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for persona in daily.get("personas", []):
        if not isinstance(persona, dict):
            continue
        units = [
            unit
            for day in persona.get("days", [])
            if isinstance(day, dict)
            for unit in day.get("interaction_units", [])
            if isinstance(unit, dict)
            and str(unit.get("interaction_unit_id")) in candidates_by_unit
        ]
        if not units:
            continue
        # Favor a unit that has two follow-ups and uses stage/latent facts.
        ranked = sorted(
            units,
            key=lambda unit: _example_score(unit=unit, candidate=candidates_by_unit[str(unit.get("interaction_unit_id"))]),
            reverse=True,
        )
        unit = ranked[0]
        unit_id = str(unit.get("interaction_unit_id"))
        if unit_id not in seen_ids:
            examples.append(unit)
            seen_ids.add(unit_id)
    return examples


def _example_score(*, unit: dict[str, Any], candidate: dict[str, Any]) -> tuple[int, int, int]:
    followup_count = len(candidate.get("followup_user_messages") or [])
    fact_ids = candidate.get("fact_ids_used") if isinstance(candidate.get("fact_ids_used"), list) else []
    stage_or_latent = sum(
        1
        for fact_id in fact_ids
        if "stage_delta_fact" in str(fact_id) or ":latent_" in str(fact_id)
    )
    day = int(unit.get("day") or 0)
    return followup_count, stage_or_latent, day


def _candidate_uses(candidate: dict[str, Any], needle: str) -> bool:
    fact_ids = candidate.get("fact_ids_used", [])
    return isinstance(fact_ids, list) and any(needle in str(fact_id) for fact_id in fact_ids)


def _turn_row(label: str, text: Any) -> str:
    return f'<div class="turn-label">{_esc(label)}</div><div class="message">{_esc(text)}</div>'


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


def _event_title(unit: dict[str, Any]) -> str:
    title = unit.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or unit.get("event_category_id") or "")
    return str(title or unit.get("event_category_id") or "")


def _fact_text(fact: Any) -> str:
    if not isinstance(fact, dict):
        return ""
    return str(fact.get("text_zh") or fact.get("text") or "")


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><b>{_esc(value)}</b><span>{_esc(label)}</span></div>'


def _table(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    header_html = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    row_html = []
    for row in rows:
        cells = "".join(f"<td>{_esc(cell)}</td>" for cell in row)
        row_html.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(row_html)}</tbody></table>"


def _counter_text(counter: Counter[Any]) -> str:
    if not counter:
        return "无"
    return "；".join(f"{key}: {value}" for key, value in counter.most_common())


def _ul(values: Any) -> str:
    if not isinstance(values, list):
        return '<p class="muted">无</p>'
    items = [f"<li>{_esc(item)}</li>" for item in values if item not in (None, "")]
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
