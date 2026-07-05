#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
OUTPUT = REPO_ROOT / "docs/demo5_persona_all_event_lines_detail.html"


def main() -> int:
    sampled = _load_json(DATA_DIR / "sampled_personas.json")
    accepted = _load_json(DATA_DIR / "accepted_persona_event_sets.json")
    batch = _load_json(DATA_DIR / "event_lines_batch.json")

    zh_personas = {
        str(persona.get("persona_id")): persona
        for persona in sampled.get("locale_views", {}).get("zh", {}).get("personas", [])
        if isinstance(persona, dict)
    }
    accepted_by_persona = {
        str(item.get("persona_id")): item
        for item in accepted.get("accepted_persona_event_sets", [])
        if isinstance(item, dict)
    }
    persona_batches = [
        item for item in batch.get("personas", []) if isinstance(item, dict)
    ]

    OUTPUT.write_text(
        _render(
            batch=batch,
            zh_personas=zh_personas,
            accepted_by_persona=accepted_by_persona,
            persona_batches=persona_batches,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")
    return 0


def _render(
    *,
    batch: dict[str, Any],
    zh_personas: dict[str, dict[str, Any]],
    accepted_by_persona: dict[str, dict[str, Any]],
    persona_batches: list[dict[str, Any]],
) -> str:
    summary = batch.get("summary", {})
    persona_sections = "".join(
        _persona_section(
            persona_batch=item,
            zh_persona=zh_personas.get(str(item.get("construction_scope", {}).get("persona_id") or item.get("persona_id")), {}),
            accepted_set=accepted_by_persona.get(str(item.get("construction_scope", {}).get("persona_id") or item.get("persona_id")), {}),
            open_by_default=index == 0,
        )
        for index, item in enumerate(persona_batches)
    )
    event_lines = batch.get("event_lines", [])
    domain_counts = Counter(
        str(line.get("event_domain_zh") or line.get("event_domain"))
        for line in event_lines
        if isinstance(line, dict)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>5 人完整事件线明细</title>
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
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--band);
      color: var(--ink);
      font: 14px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 28px 18px 56px;
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
    .hero, .persona, .line-card, .box, .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .hero {{ padding: 18px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
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
    .line-card {{
      overflow: hidden;
      margin-top: 12px;
    }}
    .line-card > header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    .line-body {{
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr);
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
    .facts, .stages {{
      display: grid;
      gap: 10px;
    }}
    .stage {{
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }}
    .stage header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      background: #f8fafc;
    }}
    .stage-body {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 10px;
      padding: 12px;
    }}
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
      text-align: left;
      vertical-align: top;
      word-break: break-word;
    }}
    th {{
      background: #f2f5f9;
      color: #344054;
      font-size: 12px;
    }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 12px; }}
    @media (max-width: 980px) {{
      .metrics, .profile, .line-body, .stage-body {{ grid-template-columns: 1fr; }}
      details.persona > summary, .line-card > header, .stage header {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>5 人完整事件线明细</h1>
      <p>本页展示当前 demo5 的五个人物资料，以及每个人从 P0 接受事件 E 到 P1 事件线 L 的完整展开。每条 L 都保留 E 来源、允许事实、记忆目标和 5 个阶段。</p>
      <div class="metrics">
        {_metric("persona", summary.get("persona_count"))}
        {_metric("event lines", summary.get("event_line_count"))}
        {_metric("P0001", summary.get("event_lines_per_persona", {}).get("P0001"))}
        {_metric("P0004 max", summary.get("event_lines_per_persona", {}).get("P0004"))}
        {_metric("domains", len(domain_counts))}
      </div>
      <div class="source-note">
        <p><b>数据来源：</b><code>sampled_personas.json</code> 提供人物；<code>accepted_persona_event_sets.json</code> 提供每人接受的 E；<code>event_lines_batch.json</code> 提供每条 L 的 5 阶段事件线。</p>
        <p class="muted small">领域分布：{_esc(_counter_text(domain_counts))}</p>
      </div>
    </section>
    {persona_sections}
  </main>
</body>
</html>
"""


def _persona_section(
    *,
    persona_batch: dict[str, Any],
    zh_persona: dict[str, Any],
    accepted_set: dict[str, Any],
    open_by_default: bool,
) -> str:
    scope = persona_batch.get("construction_scope", {})
    persona_id = str(scope.get("persona_id") or persona_batch.get("persona_id") or zh_persona.get("persona_id") or "")
    lines = [
        line for line in persona_batch.get("event_lines", []) if isinstance(line, dict)
    ]
    persona_ref = persona_batch.get("persona_ref", {})
    event_ids = accepted_set.get("accepted_event_ids", [])
    profile_html = _profile_html(zh_persona=zh_persona, persona_ref=persona_ref)
    line_cards = "".join(_line_card(line=line, index=index + 1) for index, line in enumerate(lines))
    open_attr = " open" if open_by_default else ""
    return f"""
    <details class="persona"{open_attr}>
      <summary>
        <div>
          <p class="muted"><code>{_esc(persona_id)}</code> · {_esc(zh_persona.get("source_archetype_label") or persona_ref.get("source_archetype_label_zh") or persona_ref.get("source_archetype_label"))}</p>
          <h2>{_esc(zh_persona.get("occupation") or persona_ref.get("occupation_zh") or persona_ref.get("occupation"))}</h2>
        </div>
        <div>
          <span class="tag">{len(lines)} 条 L</span>
          <span class="tag blue">{len(event_ids) if isinstance(event_ids, list) else accepted_set.get("accepted_event_count")} 个 E</span>
        </div>
      </summary>
      <div class="persona-body">
        {profile_html}
        <h3>全部事件线</h3>
        {line_cards}
      </div>
    </details>
"""


def _profile_html(*, zh_persona: dict[str, Any], persona_ref: dict[str, Any]) -> str:
    rows = [
        ("年龄", zh_persona.get("age_range")),
        ("职业状态", zh_persona.get("occupation_status")),
        ("教育背景", zh_persona.get("education_background")),
        ("家庭结构", zh_persona.get("family_structure") or persona_ref.get("family_structure_zh")),
        ("生活阶段", zh_persona.get("life_stage")),
        ("经济条件", zh_persona.get("economic_condition")),
        ("社会支持", zh_persona.get("social_support")),
        ("主要生活领域", zh_persona.get("primary_life_domains") or persona_ref.get("primary_life_domains_zh")),
        ("长期目标", zh_persona.get("long_term_goals")),
        ("沟通风格", zh_persona.get("communication_style")),
        ("压力反应", zh_persona.get("stress_response")),
        ("决策风格", zh_persona.get("decision_style")),
        ("记忆相关特征", zh_persona.get("memory_relevant_traits")),
        ("敏感字段边界", zh_persona.get("sensitive_fields")),
    ]
    return '<div class="profile">' + "".join(_field(label, value) for label, value in rows) + "</div>"


def _line_card(*, line: dict[str, Any], index: int) -> str:
    title = _title(line)
    source = line.get("source_event_category", {})
    latent = line.get("latent_concerns_zh") or line.get("latent_concerns") or []
    targets = line.get("relational_memory_targets", [])
    stages = [stage for stage in line.get("stage_sequence", []) if isinstance(stage, dict)]
    return f"""
        <article class="line-card">
          <header>
            <div>
              <p class="muted">#{index} · <code>{_esc(line.get("event_line_id"))}</code></p>
              <h3>{_esc(title)}</h3>
              <p class="muted"><code>{_esc(line.get("event_category_id"))}</code> · {_esc(line.get("event_domain_zh") or line.get("event_domain"))} · {_esc(line.get("event_type"))}</p>
            </div>
            <div>
              <span class="tag">L</span>
              <span class="tag blue">5 stages</span>
            </div>
          </header>
          <div class="line-body">
            <aside class="facts">
              <div class="box">
                <h4>E 来源</h4>
                {_table(["字段", "内容"], [
                    ("core_issue", source.get("core_issue_zh") or line.get("persistent_event_summary_zh")),
                    ("possible_uncertainties", _list_text(source.get("possible_uncertainties_zh") or [])),
                    ("possible_actions", _list_text(source.get("possible_actions_zh") or [])),
                    ("possible_emotional_load", _list_text(source.get("possible_emotional_load_zh") or [])),
                    ("memory_risks", _list_text(source.get("memory_risks_zh") or [])),
                ])}
              </div>
              <div class="box">
                <h4>L 层边界</h4>
                {_table(["字段", "内容"], [
                    ("persistent_event_summary", line.get("persistent_event_summary_zh") or line.get("persistent_event_summary")),
                    ("participants", _list_text(line.get("participants_zh") or line.get("participants") or [])),
                    ("latent_concerns", _list_text(latent)),
                    ("relational_memory_targets", _targets_text(targets)),
                ])}
              </div>
            </aside>
            <section class="stages">
              {''.join(_stage_card(stage=stage) for stage in stages)}
            </section>
          </div>
        </article>
"""


def _stage_card(*, stage: dict[str, Any]) -> str:
    return f"""
      <div class="stage">
        <header>
          <div>
            <h4>阶段 {stage.get("stage_index")} · {_esc(stage.get("source_stage_label_zh") or stage.get("source_stage_label") or stage.get("event_stage"))}</h4>
            <p class="muted"><code>{_esc(stage.get("event_stage"))}</code></p>
          </div>
          <span class="tag warn">{_esc(stage.get("stage_goal_zh") or stage.get("stage_goal"))}</span>
        </header>
        <div class="stage-body">
          <div>
            <p><b>用户消息种子</b></p>
            <p>{_esc(stage.get("user_message_seed_zh") or stage.get("user_message_seed"))}</p>
            <p style="margin-top:8px;"><b>助手记忆预期</b></p>
            <p>{_esc(stage.get("assistant_memory_expectation_zh") or stage.get("assistant_memory_expectation"))}</p>
            <p style="margin-top:8px;"><b>用户状态提示</b></p>
            <p>{_esc(stage.get("user_state_hint_zh") or stage.get("user_state_hint"))}</p>
          </div>
          <div>
            <p><b>阶段新增事实</b></p>
            {_ul(_fact_texts(stage.get("stage_delta_facts", [])))}
            <p style="margin-top:8px;"><b>allowed_new_facts</b></p>
            {_ul(stage.get("allowed_new_facts_zh") or stage.get("allowed_new_facts") or [])}
            <p style="margin-top:8px;"><b>禁止引入</b></p>
            {_ul(stage.get("prohibited_facts_zh") or stage.get("prohibited_facts") or [])}
          </div>
        </div>
      </div>
"""


def _field(label: str, value: Any) -> str:
    return f'<div class="box"><b>{_esc(label)}</b><p>{_esc(_value_text(value))}</p></div>'


def _table(headers: list[str], rows: list[tuple[Any, Any]]) -> str:
    header_html = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    row_html = "".join(
        f"<tr><td>{_esc(label)}</td><td>{_esc(_value_text(value))}</td></tr>"
        for label, value in rows
    )
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table>"


def _title(line: dict[str, Any]) -> str:
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
            out.append(str(item.get("text_zh") or item.get("text") or ""))
        elif item not in (None, ""):
            out.append(str(item))
    return [item for item in out if item]


def _targets_text(targets: Any) -> str:
    if not isinstance(targets, list):
        return _value_text(targets)
    values = []
    for target in targets:
        if isinstance(target, dict):
            kind = target.get("target_type", "")
            text = target.get("target_zh") or target.get("target") or ""
            values.append(f"{kind}: {text}" if kind else str(text))
        elif target not in (None, ""):
            values.append(str(target))
    return "；".join(values)


def _list_text(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(str(item) for item in value if item not in (None, ""))
    return _value_text(value)


def _value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "；".join(str(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        return "；".join(f"{key}: {_value_text(item)}" for key, item in value.items())
    return str(value)


def _counter_text(counter: Counter[Any]) -> str:
    return "；".join(f"{key}: {count}" for key, count in counter.most_common())


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><b>{_esc(value)}</b><span>{_esc(label)}</span></div>'


def _ul(values: Any) -> str:
    if not isinstance(values, list):
        return "<p class=\"muted\">无</p>"
    items = [f"<li>{_esc(item)}</li>" for item in values if item not in (None, "")]
    if not items:
        return "<p class=\"muted\">无</p>"
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
