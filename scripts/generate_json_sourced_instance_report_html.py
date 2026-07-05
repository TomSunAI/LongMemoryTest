#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_P0_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DEFAULT_ARCHETYPE_POOL = (
    REPO_ROOT / "long_memory_experiment/data/sampling/persona_archetype_pool_v0.1.json"
)
DEFAULT_EVENT_POOL = (
    REPO_ROOT / "long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "docs/json_sourced_instance_p0001_report.html"


PERSONA_FIELD_SOURCE = {
    "age_range": "age_range_options",
    "occupation": "occupation_options",
    "occupation_status": "occupation_status_options",
    "education_background": "education_options",
    "family_structure": "family_structure_options",
    "life_stage": "life_stage_options",
    "economic_condition": "economic_condition_options",
    "social_support": "social_support_options",
    "primary_life_domains": "likely_life_domains",
    "long_term_goals": "long_term_goal_options",
    "communication_style": "communication_style_options",
    "stress_response": "stress_response_options",
    "decision_style": "decision_style_options",
    "memory_relevant_traits": "memory_relevant_trait_options",
}


FIELD_LABELS = {
    "age_range": "年龄范围",
    "occupation": "职业",
    "occupation_status": "职业状态",
    "education_background": "教育背景",
    "family_structure": "家庭结构",
    "life_stage": "人生阶段",
    "economic_condition": "经济状态",
    "social_support": "社会支持",
    "primary_life_domains": "主要生活领域",
    "long_term_goals": "长期目标",
    "communication_style": "沟通风格",
    "stress_response": "压力反应",
    "decision_style": "决策风格",
    "memory_relevant_traits": "记忆相关特征",
}


DOMAIN_CN = {
    "administration": "行政手续",
    "education": "教育/学业",
    "health_routine": "健康日常",
    "learning": "学习转型",
    "pet_care": "宠物照护",
    "work_family_intersection": "工作-家庭交叉",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate one JSON-sourced persona report.")
    parser.add_argument("--persona-id", default="P0001")
    parser.add_argument("--p0-dir", type=Path, default=DEFAULT_P0_DIR)
    parser.add_argument("--persona-archetype-pool", type=Path, default=DEFAULT_ARCHETYPE_POOL)
    parser.add_argument("--event-category-pool", type=Path, default=DEFAULT_EVENT_POOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sampled = _load_json(args.p0_dir / "sampled_personas.json")
    accepted = _load_json(args.p0_dir / "accepted_persona_event_sets.json")
    candidates = _load_json(args.p0_dir / "candidate_event_sets.json")
    archetype_pool = _load_json(args.persona_archetype_pool)
    event_pool = _load_json(args.event_category_pool)

    persona = _find_by_id(sampled.get("personas", []), "persona_id", args.persona_id)
    accepted_set = _find_by_id(
        accepted.get("accepted_persona_event_sets", []),
        "persona_id",
        args.persona_id,
    )
    candidate_set = _find_by_id(
        candidates.get("candidate_event_sets", []),
        "persona_id",
        args.persona_id,
    )
    archetype = _find_by_id(
        archetype_pool.get("archetypes", []),
        "archetype_id",
        str(persona.get("source_archetype")),
    )
    events_by_id = {
        str(event.get("event_category_id")): event
        for event in event_pool.get("event_categories", [])
        if isinstance(event, dict)
    }
    html_text = render_report(
        persona=persona,
        archetype=archetype,
        accepted_set=accepted_set,
        candidate_set=candidate_set,
        events_by_id=events_by_id,
        p0_dir=args.p0_dir,
        archetype_pool_path=args.persona_archetype_pool,
        event_pool_path=args.event_category_pool,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(
    *,
    persona: dict[str, Any],
    archetype: dict[str, Any],
    accepted_set: dict[str, Any],
    candidate_set: dict[str, Any],
    events_by_id: dict[str, dict[str, Any]],
    p0_dir: Path,
    archetype_pool_path: Path,
    event_pool_path: Path,
) -> str:
    accepted_events = [
        events_by_id[event_id]
        for event_id in accepted_set.get("accepted_event_ids", [])
        if event_id in events_by_id
    ]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JSON 来源单人实例 P0001</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #5b6670;
      --line: #d8e0e7;
      --soft: #f6f8fb;
      --accent: #1558d6;
      --chip: #eef4ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #fff;
      font: 15px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 34px 26px 72px; }}
    h1, h2, h3 {{ margin: 0; line-height: 1.25; }}
    h1 {{ font-size: 30px; }}
    h2 {{
      margin-top: 34px;
      padding-top: 22px;
      border-top: 1px solid var(--line);
      font-size: 22px;
    }}
    h3 {{ margin-top: 14px; font-size: 17px; }}
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
    .callout {{
      margin: 16px 0;
      padding: 13px 15px;
      background: var(--soft);
      border-left: 4px solid var(--accent);
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
    ul.compact {{ margin: 6px 0 0 20px; padding: 0; }}
    li {{ margin: 3px 0; }}
    @media (max-width: 900px) {{
      main {{ padding: 24px 14px 56px; }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>JSON 来源单人实例：<code>{_esc(persona.get("persona_id"))}</code></h1>
  <p class="meta">
    P0 输出目录：<code>{_esc(_rel(p0_dir))}</code><br>
    人物来源 JSON：<code>{_esc(_rel(archetype_pool_path))}</code><br>
    事件来源 JSON：<code>{_esc(_rel(event_pool_path))}</code>
  </p>

  <section>
    <h2>结论</h2>
    <div class="callout">
      这个实例 <code>{_esc(persona.get("persona_id"))}</code> 是从今天整理的
      <code>persona_archetype_pool_v0.1.json</code> 中的
      <code>{_esc(persona.get("source_archetype"))}</code> 采样出来的；
      它的接受事件来自 <code>event_category_pool_v0.1_60events.json</code>。
      当前只完成到 <strong>P0</strong>，也就是具体人物和接受事件集合；
      还没有生成真正的 <code>event_lines.json</code>、timeline、daily interaction 或 probe。
    </div>
  </section>

  <section>
    <h2>来源 Archetype</h2>
    {_archetype_table(archetype)}
  </section>

  <section>
    <h2>具体人物字段 z</h2>
    {_persona_source_table(persona, archetype)}
  </section>

  <section>
    <h2>接受事件集合 T</h2>
    <p class="meta">
      这些还只是 event category，不是跨天事件线。下一步 P1 才会把每个 category
      展开成带 initial / recurrence / turning point / partial resolution / reflection 的事件线。
    </p>
    {_accepted_event_table(accepted_events)}
  </section>

  <section>
    <h2>候选事件决策</h2>
    {_candidate_table(candidate_set)}
  </section>
</main>
</body>
</html>
"""


def _archetype_table(archetype: dict[str, Any]) -> str:
    return f"""
    <table>
      <tbody>
        <tr><th>archetype_id</th><td><code>{_esc(archetype.get("archetype_id"))}</code></td></tr>
        <tr><th>label</th><td>{_esc(archetype.get("label"))}</td></tr>
        <tr><th>core_description</th><td>{_esc(archetype.get("core_description"))}</td></tr>
        <tr><th>likely_life_domains</th><td>{_tags(archetype.get("likely_life_domains", []))}</td></tr>
      </tbody>
    </table>
    """


def _persona_source_table(persona: dict[str, Any], archetype: dict[str, Any]) -> str:
    rows = []
    for persona_key, source_key in PERSONA_FIELD_SOURCE.items():
        value = persona.get(persona_key)
        allowed = archetype.get(source_key, [])
        rows.append(
            "<tr>"
            f"<th>{_esc(FIELD_LABELS.get(persona_key, persona_key))}</th>"
            f"<td>{_format_value(value)}</td>"
            f"<td><code>{_esc(source_key)}</code></td>"
            f"<td>{_format_value(allowed)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>字段</th><th>采样值</th><th>来源 JSON 字段</th>"
        "<th>JSON 允许候选</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _accepted_event_table(events: list[dict[str, Any]]) -> str:
    rows = []
    for event in events:
        rows.append(
            "<tr>"
            f"<td><code>{_esc(event.get('event_category_id'))}</code></td>"
            f"<td>{_esc(_domain_label(str(event.get('event_domain'))))}</td>"
            f"<td>{_esc(event.get('title'))}</td>"
            f"<td>{_esc(event.get('core_issue'))}</td>"
            f"<td>{_format_value(event.get('stage_patterns', []))}</td>"
            f"<td>{_format_value(event.get('possible_actions', []))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>ID</th><th>领域</th><th>标题</th><th>核心问题</th>"
        "<th>P1 可用阶段模板</th><th>可能行动</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _candidate_table(candidate_set: dict[str, Any]) -> str:
    rows = []
    for event in candidate_set.get("candidates", []):
        if not isinstance(event, dict):
            continue
        rows.append(
            "<tr>"
            f"<td><code>{_esc(event.get('event_category_id'))}</code></td>"
            f"<td>{_esc(_domain_label(str(event.get('event_domain'))))}</td>"
            f"<td>{_esc(event.get('decision_after_validation'))}</td>"
            f"<td>{_format_value(event.get('decision_reasons', []))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>ID</th><th>领域</th><th>决策</th><th>理由</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _format_value(value: Any) -> str:
    if isinstance(value, list):
        if value and all(isinstance(item, list) for item in value):
            return "".join(_tags(item) for item in value)
        return _tags(value)
    if isinstance(value, dict):
        return _esc(json.dumps(value, ensure_ascii=False))
    return _esc(value)


def _tags(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "<span class='meta'>未提供</span>"
    return "".join(f"<span class='tag'>{_esc(item)}</span>" for item in values)


def _domain_label(domain: str) -> str:
    return DOMAIN_CN.get(domain, domain)


def _find_by_id(items: Any, key: str, value: str) -> dict[str, Any]:
    if not isinstance(items, list):
        raise ValueError(f"Expected list while finding {key}={value}.")
    for item in items:
        if isinstance(item, dict) and str(item.get(key)) == value:
            return item
    raise ValueError(f"Cannot find {key}={value}.")


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
