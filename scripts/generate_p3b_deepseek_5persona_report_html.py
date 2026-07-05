#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DAILY_PATH = DATA_DIR / "daily_interaction_units.json"
NATURALIZED_PATH = DATA_DIR / "daily_interaction_naturalized_candidates_deepseek_5personas.json"
OUTPUT = REPO_ROOT / "docs/p3b_deepseek_5persona_naturalization_report.html"


def main() -> int:
    daily = _load_json(DAILY_PATH)
    naturalized = _load_json(NATURALIZED_PATH)
    units_by_id = _units_by_id(daily)
    html_text = _page(naturalized=naturalized, units_by_id=units_by_id)
    OUTPUT.write_text(html_text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


def _page(*, naturalized: dict[str, Any], units_by_id: dict[str, dict[str, Any]]) -> str:
    cards = []
    for candidate in naturalized.get("naturalized_dialogues", []):
        if not isinstance(candidate, dict):
            continue
        unit = units_by_id.get(str(candidate.get("source_interaction_unit_id")), {})
        cards.append(_candidate_card(candidate=candidate, unit=unit))
    summary = naturalized.get("summary", {})
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>P3b DeepSeek 5 Persona Naturalization</title>
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
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--band);
      color: var(--ink);
      font: 14px/1.62 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 26px 18px 50px;
    }}
    h1 {{ margin: 0 0 10px; font-size: 28px; letter-spacing: 0; }}
    h2 {{ margin: 0; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 15px; letter-spacing: 0; }}
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
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 16px 0;
    }}
    .metric, .card, .box {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .metric {{ padding: 12px; }}
    .metric b {{ display: block; font-size: 23px; }}
    .metric span {{ color: var(--muted); font-size: 12px; }}
    .note {{
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fffdf7;
      margin: 0 0 16px;
    }}
    .card {{
      margin-top: 14px;
      overflow: hidden;
    }}
    .card header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 14px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      padding: 14px;
    }}
    .box {{ padding: 12px; background: var(--soft); }}
    .message {{
      padding: 10px;
      border-radius: 7px;
      border: 1px solid var(--line);
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
    .ok {{ color: var(--ok); }}
    .fail {{ color: var(--warn); }}
    ul {{ margin: 0; padding-left: 18px; }}
    li + li {{ margin-top: 4px; }}
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
    .muted {{ color: var(--muted); }}
    @media (max-width: 920px) {{
      .summary, .grid {{ grid-template-columns: 1fr; }}
      .card header {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>P3b DeepSeek 5 Persona 自然化候选</h1>
    <p class="muted">输入是标准 P3 I unit；DeepSeek 只生成自然语言候选，不覆盖 canonical I。</p>
    <section class="summary">
      {_metric("LLM Provider", naturalized.get("llm_provider"))}
      {_metric("LLM Model", naturalized.get("llm_model"))}
      {_metric("候选数", summary.get("candidate_count"))}
      {_metric("校验通过", summary.get("pass_count"))}
    </section>
    <section class="note">
      <p><b>边界：</b>P3b 输出是候选层，字段 <code>canonical_i_units_preserved=true</code>、<code>naturalized_text_is_candidate_only=true</code>。正式结构真值仍是 <code>daily_interaction_units.json</code>。</p>
    </section>
    {''.join(cards)}
  </main>
</body>
</html>
"""


def _candidate_card(*, candidate: dict[str, Any], unit: dict[str, Any]) -> str:
    validation = candidate.get("validation", {})
    status = str(validation.get("status", "unknown"))
    unit_id = str(candidate.get("source_interaction_unit_id") or unit.get("interaction_unit_id"))
    persona_id = str(unit.get("persona_id") or unit_id.split("_D", 1)[0])
    opening = unit.get("scripted_opening", {}) if isinstance(unit.get("scripted_opening"), dict) else {}
    source_fields = unit.get("source_timeline_fields", {})
    if not isinstance(source_fields, dict):
        source_fields = {}
    return f"""
    <section class="card">
      <header>
        <div>
          <p class="muted"><code>{_esc(persona_id)}</code> · <code>{_esc(unit_id)}</code> · <code>{_esc(unit.get("event_line_id"))}</code></p>
          <h2>{_esc(_event_title(unit))}</h2>
        </div>
        <div>
          <span class="tag">{_esc(unit.get("event_stage"))}</span>
          <span class="tag {'ok' if status == 'pass' else 'fail'}">validation={_esc(status)}</span>
        </div>
      </header>
      <div class="grid">
        <div class="box">
          <h3>Canonical I · 规则生成</h3>
          <p class="muted">scripted_opening.user_message</p>
          <p class="message">{_esc(opening.get("user_message"))}</p>
          <p class="muted">conversation_goal</p>
          <p>{_esc(opening.get("conversation_goal"))}</p>
        </div>
        <div class="box">
          <h3>P3b DeepSeek · 自然化候选</h3>
          <p class="muted">opening_user_message</p>
          <p class="message">{_esc(candidate.get("opening_user_message"))}</p>
          <p class="muted">followup_user_messages</p>
          {_ul(candidate.get("followup_user_messages", []))}
        </div>
      </div>
      <div class="grid">
        <div class="box">
          <h3>候选使用的 fact ids</h3>
          {_fact_table(candidate.get("fact_ids_used", []), unit)}
        </div>
        <div class="box">
          <h3>来源事实摘要</h3>
          <p><span class="tag">allowed_base</span></p>
          {_ul(source_fields.get("allowed_base_facts", []))}
          <p><span class="tag">persona_conditioned</span></p>
          {_fact_record_ul(source_fields.get("persona_conditioned_facts", []))}
          <p><span class="tag">stage_delta</span></p>
          {_fact_record_ul(source_fields.get("stage_delta_facts", []))}
        </div>
      </div>
      <div class="grid">
        <div class="box">
          <h3>模型审计 notes</h3>
          <p>{_esc(candidate.get("notes"))}</p>
        </div>
        <div class="box">
          <h3>校验结果</h3>
          <p>status: <b class="{'ok' if status == 'pass' else 'fail'}">{_esc(status)}</b></p>
          {_ul(validation.get("issues", []))}
        </div>
      </div>
    </section>
"""


def _fact_table(fact_ids: Any, unit: dict[str, Any]) -> str:
    facts = {}
    boundary = unit.get("scene_boundary", {})
    if isinstance(boundary, dict):
        for item in boundary.get("allowed_facts", []):
            if isinstance(item, dict):
                facts[str(item.get("fact_id"))] = item
    rows = []
    if isinstance(fact_ids, list):
        for fact_id in fact_ids:
            fact = facts.get(str(fact_id), {})
            rows.append(
                f"<tr><td><code>{_esc(fact_id)}</code></td><td>{_esc(fact.get('type'))}</td><td>{_esc(fact.get('text'))}</td></tr>"
            )
    if not rows:
        rows.append('<tr><td colspan="3" class="muted">无</td></tr>')
    return f"<table><thead><tr><th>fact_id</th><th>type</th><th>text</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _fact_record_ul(records: Any) -> str:
    if not isinstance(records, list):
        return '<p class="muted">无</p>'
    values = [
        str(item.get("text") if isinstance(item, dict) else item)
        for item in records
        if item
    ]
    return _ul(values)


def _ul(values: Any) -> str:
    if not isinstance(values, list):
        return '<p class="muted">无</p>'
    items = [f"<li>{_esc(item)}</li>" for item in values if item not in (None, "")]
    if not items:
        return '<p class="muted">无</p>'
    return "<ul>" + "".join(items) + "</ul>"


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><b>{_esc(value)}</b><span>{_esc(label)}</span></div>'


def _event_title(unit: dict[str, Any]) -> str:
    title = unit.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or unit.get("event_category_id") or "")
    return str(title or unit.get("event_category_id") or "")


def _units_by_id(daily: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(unit.get("interaction_unit_id")): unit
        for persona in daily.get("personas", [])
        if isinstance(persona, dict)
        for day in persona.get("days", [])
        if isinstance(day, dict)
        for unit in day.get("interaction_units", [])
        if isinstance(unit, dict) and unit.get("interaction_unit_id")
    }


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


if __name__ == "__main__":
    raise SystemExit(main())
