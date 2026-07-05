#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.sampling.zh_localization import event_domain_zh, zh_text, zh_value  # noqa: E402


DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
EVENT_POOL = REPO_ROOT / "long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json"
OUTPUT = REPO_ROOT / "docs/demo5_l_fact_layer_examples.html"


def main() -> int:
    sampled = _load_json(DATA_DIR / "sampled_personas.json")
    event_lines_batch = _load_json(DATA_DIR / "event_lines_batch.json")
    event_pool = _load_json(EVENT_POOL)
    html_text = _page(
        personas=[item for item in sampled.get("personas", []) if isinstance(item, dict)],
        persona_payloads=[
            item for item in event_lines_batch.get("personas", []) if isinstance(item, dict)
        ],
        events_by_id={
            str(item.get("event_category_id")): item
            for item in event_pool.get("event_categories", [])
            if isinstance(item, dict)
        },
        summary=event_lines_batch.get("summary", {}),
    )
    OUTPUT.write_text(html_text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


def _page(
    *,
    personas: list[dict[str, Any]],
    persona_payloads: list[dict[str, Any]],
    events_by_id: dict[str, dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    persona_by_id = {str(item.get("persona_id")): item for item in personas}
    all_lines = [
        line
        for payload in persona_payloads
        for line in payload.get("event_lines", [])
        if isinstance(line, dict)
    ]
    stage_count = sum(len(line.get("stage_sequence", [])) for line in all_lines)
    stage_delta_count = sum(
        len(stage.get("stage_delta_facts", []))
        for line in all_lines
        for stage in line.get("stage_sequence", [])
        if isinstance(stage, dict)
    )
    candidate_index_counter = Counter(
        f"{item.get('source_field')}[{item.get('source_index')}]"
        for line in all_lines
        for stage in line.get("stage_sequence", [])[:1]
        for item in stage.get("event_candidate_facts", [])
        if isinstance(item, dict)
    )
    persona_sections = []
    for payload in persona_payloads:
        persona_id = str(
            payload.get("persona_ref", {}).get("persona_id")
            or payload.get("construction_scope", {}).get("persona_id")
        )
        persona_sections.append(
            _persona_section(
                persona=persona_by_id.get(persona_id, {}),
                payload=payload,
                events_by_id=events_by_id,
            )
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>5 人 L 事实分层示例</title>
  <style>
    :root {{
      --ink: #18212f;
      --muted: #667085;
      --line: #d6dde8;
      --panel: #ffffff;
      --band: #f4f6f9;
      --soft: #f9fbfd;
      --base: #175cd3;
      --event: #0f766e;
      --persona: #8a4b12;
      --stage: #7c3aed;
      --allow: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--band);
      font: 14px/1.62 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 26px 18px 48px;
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
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 16px 0 20px;
    }}
    .metric, .persona, .line {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .metric {{ padding: 13px; }}
    .metric b {{ display: block; font-size: 22px; }}
    .metric span {{ color: var(--muted); font-size: 12px; }}
    .persona {{
      margin-top: 18px;
      overflow: hidden;
    }}
    .persona > header {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      padding: 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .profile {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }}
    .field {{
      min-height: 72px;
      padding: 9px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }}
    .field b {{
      display: block;
      margin-bottom: 5px;
      color: var(--muted);
      font-size: 12px;
    }}
    .lines {{
      display: grid;
      gap: 12px;
      padding: 14px 16px 18px;
    }}
    details.line > summary {{
      cursor: pointer;
      padding: 12px 14px;
      list-style: none;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-weight: 800;
    }}
    details.line > summary::-webkit-details-marker {{ display: none; }}
    .line-body {{
      padding: 0 14px 14px;
      border-top: 1px solid var(--line);
    }}
    .two-col {{
      display: grid;
      grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
      gap: 12px;
      margin-top: 12px;
    }}
    .box {{
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
    }}
    .chips {{ margin-top: 8px; }}
    .chip {{
      display: inline-block;
      margin: 0 6px 6px 0;
      padding: 2px 7px;
      border-radius: 999px;
      background: #eef2ff;
      color: var(--ink);
      font-size: 12px;
      font-weight: 700;
    }}
    .base {{ color: var(--base); }}
    .event {{ color: var(--event); }}
    .persona-fact {{ color: var(--persona); }}
    .stage {{ color: var(--stage); }}
    .allow {{ color: var(--allow); }}
    table {{
      width: 100%;
      margin-top: 12px;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      vertical-align: top;
      padding: 9px;
      border: 1px solid var(--line);
      text-align: left;
      word-break: break-word;
    }}
    th {{
      background: #f2f5f9;
      color: #344054;
      font-size: 12px;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    li + li {{ margin-top: 4px; }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 960px) {{
      .summary, .profile, .two-col {{ grid-template-columns: 1fr; }}
      .persona > header, details.line > summary {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>5 人 L 事实分层示例</h1>
    <p class="muted">来源：<code>sampled_personas.json</code>、<code>event_category_pool_v0.1_60events.json</code>、<code>event_lines_batch.json</code>。本页展示重新生成后的五个人和他们的 L 事实层。</p>
    <section class="summary">
      {_metric("人物数", summary.get("persona_count", len(persona_payloads)))}
      {_metric("L 总数", summary.get("event_line_count", len(all_lines)))}
      {_metric("stage 总数", stage_count)}
      {_metric("stage delta facts", stage_delta_count)}
    </section>
    <section class="box">
      <h3>本次改动检查</h3>
      <p><span class="chip event">E 候选事实</span> 保留 core_issue、全部 possible_uncertainties、全部 possible_actions、全部 possible_emotional_load；当前候选索引包含：{_esc(", ".join(sorted(candidate_index_counter)))}。</p>
      <p><span class="chip persona-fact">persona 条件化事实</span> 已把职业、家庭结构、经济条件、社会支持、长期目标、决策风格、沟通风格写入每条 L。</p>
      <p><span class="chip stage">stage 递进事实</span> 按 initial / recurrence / turning_point / partial_resolution / reflection 逐步释放，不再五个阶段复用同一组 facts。</p>
    </section>
    {''.join(persona_sections)}
  </main>
</body>
</html>
"""


def _persona_section(
    *,
    persona: dict[str, Any],
    payload: dict[str, Any],
    events_by_id: dict[str, dict[str, Any]],
) -> str:
    persona_id = str(persona.get("persona_id") or payload.get("persona_ref", {}).get("persona_id"))
    lines = [item for item in payload.get("event_lines", []) if isinstance(item, dict)]
    line_html = "\n".join(
        _line_details(
            line=line,
            event=events_by_id.get(str(line.get("event_category_id")), {}),
            open_details=index < 2,
        )
        for index, line in enumerate(lines)
    )
    return f"""
    <section class="persona">
      <header>
        <div>
          <p class="muted"><code>{_esc(persona_id)}</code> · {_esc(persona.get("source_archetype"))}</p>
          <h2>{_esc(persona.get("source_archetype_label"))}</h2>
        </div>
        <p class="muted">L 数量：{len(lines)}</p>
      </header>
      <div class="profile">
        {_field("职业", persona.get("occupation"))}
        {_field("家庭", persona.get("family_structure"))}
        {_field("经济条件", persona.get("economic_condition"))}
        {_field("社会支持", persona.get("social_support"))}
        {_field("长期目标", persona.get("long_term_goals"))}
      </div>
      <div class="lines">
        {line_html}
      </div>
    </section>
"""


def _line_details(
    *,
    line: dict[str, Any],
    event: dict[str, Any],
    open_details: bool,
) -> str:
    stages = [item for item in line.get("stage_sequence", []) if isinstance(item, dict)]
    first_stage = stages[0] if stages else {}
    return f"""
      <details class="line" {'open' if open_details else ''}>
        <summary>
          <span>{_esc(_line_title(line))}</span>
          <span><code>{_esc(line.get("event_line_id"))}</code> · <code>{_esc(line.get("event_category_id"))}</code></span>
        </summary>
        <div class="line-body">
          <div class="two-col">
            <div class="box">
              <h3>E 原始池字段</h3>
              <p><b>领域：</b>{_esc(event_domain_zh(event.get("event_domain")))} / {_esc(event.get("event_type"))}</p>
              <p><b>core_issue：</b>{_esc(zh_text(event.get("core_issue") or ""))}</p>
              {_source_chips("possible_uncertainties", event.get("possible_uncertainties", []))}
              {_source_chips("possible_actions", event.get("possible_actions", []))}
              {_source_chips("possible_emotional_load", event.get("possible_emotional_load", []))}
            </div>
            <div class="box">
              <h3>L 条件化事实</h3>
              <p><b>persistent_event_summary：</b>{_esc(line.get("persistent_event_summary"))}</p>
              <p class="chips"><span class="chip base">allowed_base_facts</span></p>
              {_ul(first_stage.get("allowed_base_facts", []))}
              <p class="chips"><span class="chip event">event_candidate_facts</span></p>
              {_fact_record_list(first_stage.get("event_candidate_facts", []), show_source=True)}
              <p class="chips"><span class="chip persona-fact">persona_conditioned_facts</span></p>
              {_fact_record_list(first_stage.get("persona_conditioned_facts", []), show_source=True)}
            </div>
          </div>
          {_stage_table(stages)}
        </div>
      </details>
"""


def _stage_table(stages: list[dict[str, Any]]) -> str:
    rows = []
    for stage in stages:
        rows.append(
            f"""
        <tr>
          <td><b>{_esc(stage.get("stage_index"))}</b><br>{_esc(stage.get("event_stage"))}</td>
          <td>{_esc(stage.get("stage_goal"))}</td>
          <td>{_fact_record_list(stage.get("stage_delta_facts", []), show_source=True)}</td>
          <td>{_ul(stage.get("allowed_new_facts", []))}</td>
          <td>{_esc(stage.get("user_message_seed"))}</td>
        </tr>
"""
        )
    return f"""
          <table>
            <thead>
              <tr>
                <th style="width: 8%;">stage</th>
                <th style="width: 17%;">stage_goal</th>
                <th style="width: 23%;">stage_delta_facts</th>
                <th style="width: 27%;">allowed_new_facts</th>
                <th style="width: 25%;">user_message_seed</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
"""


def _source_chips(label: str, values: Any) -> str:
    if not isinstance(values, list):
        return ""
    chips = "".join(
        f'<span class="chip">{_esc(label)}[{index}] {_esc(zh_text(item))}</span>'
        for index, item in enumerate(values)
        if item not in (None, "")
    )
    return f'<p class="chips">{chips}</p>' if chips else ""


def _fact_record_list(records: Any, *, show_source: bool) -> str:
    if not isinstance(records, list):
        return "<p class=\"muted\">无</p>"
    items = []
    for record in records:
        if isinstance(record, dict):
            text = record.get("text")
            source = record.get("source_field") or record.get("source_fields")
            if isinstance(source, list):
                source_text = ", ".join(str(item) for item in source)
            else:
                index = record.get("source_index")
                source_text = (
                    f"{source}[{index}]"
                    if source and index is not None
                    else str(source or "")
                )
            prefix = f"<code>{_esc(source_text)}</code> " if show_source and source_text else ""
            items.append(f"<li>{prefix}{_esc(text)}</li>")
        elif record:
            items.append(f"<li>{_esc(record)}</li>")
    if not items:
        return "<p class=\"muted\">无</p>"
    return "<ul>" + "".join(items) + "</ul>"


def _ul(values: Any) -> str:
    if not isinstance(values, list):
        return "<p class=\"muted\">无</p>"
    items = [f"<li>{_esc(item)}</li>" for item in values if item not in (None, "")]
    if not items:
        return "<p class=\"muted\">无</p>"
    return "<ul>" + "".join(items) + "</ul>"


def _field(label: str, value: Any) -> str:
    rendered = zh_value(value)
    if isinstance(rendered, list):
        rendered = "、".join(str(item) for item in rendered)
    return f'<div class="field"><b>{_esc(label)}</b><p>{_esc(rendered)}</p></div>'


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><b>{_esc(value)}</b><span>{_esc(label)}</span></div>'


def _line_title(line: dict[str, Any]) -> str:
    title = line.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or line.get("event_category_id"))
    return str(title or line.get("event_category_id"))


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


if __name__ == "__main__":
    raise SystemExit(main())
