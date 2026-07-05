#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAU = REPO_ROOT / "long_memory_experiment/data/script/tau_contract.json"
DEFAULT_TIMELINE = REPO_ROOT / "long_memory_experiment/data/script/timeline.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs/single_instance_persona_event_lines_report.html"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate focused single-instance event-line report.")
    parser.add_argument("--tau-contract", type=Path, default=DEFAULT_TAU)
    parser.add_argument("--timeline", type=Path, default=DEFAULT_TIMELINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tau = _load_json(args.tau_contract)
    timeline = _load_json(args.timeline)
    html_text = render_report(
        tau=tau,
        timeline=timeline,
        tau_path=args.tau_contract,
        timeline_path=args.timeline,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(
    *,
    tau: dict[str, Any],
    timeline: dict[str, Any],
    tau_path: Path,
    timeline_path: Path,
) -> str:
    z = tau.get("z", {})
    lines = [item for item in tau.get("L", []) if isinstance(item, dict)]
    days = [item for item in timeline.get("days", []) if isinstance(item, dict)]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>单人实例与事件线审阅</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #5b6670;
      --line: #d8e0e7;
      --soft: #f6f8fb;
      --accent: #1558d6;
      --ok: #137333;
      --chip: #eef4ff;
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
    th {{ background: var(--soft); text-align: left; font-weight: 650; }}
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
    .tag {{
      display: inline-block;
      margin: 2px 4px 2px 0;
      padding: 2px 7px;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid #d6e5ff;
      font-size: 12px;
    }}
    details.line {{
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }}
    details.line summary {{
      cursor: pointer;
      padding: 11px 13px;
      background: #fbfcfe;
      font-weight: 650;
    }}
    .line-body {{ padding: 12px 14px 14px; }}
    ul.compact {{ margin: 6px 0 0 20px; padding: 0; }}
    li {{ margin: 3px 0; }}
    @media (max-width: 900px) {{
      main {{ padding: 24px 14px 56px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>单人实例与事件线审阅</h1>
  <p class="meta">
    tau：<code>{_esc(_rel(tau_path))}</code>；
    timeline：<code>{_esc(_rel(timeline_path))}</code>
  </p>

  <section>
    <h2>结论</h2>
    <div class="grid">
      {_metric("实例人", z.get("persona_id", "-"), "z")}
      {_metric("主题", len(tau.get("T", [])), "T")}
      {_metric("事件线", len(lines), "L")}
      {_metric("交互单元", len(tau.get("I", [])), "I")}
      {_metric("探针", len(tau.get("P", [])), "P")}
    </div>
    <div class="callout">
      项目里已经有一个完整具体实例人和事件线：
      <code>{_esc(z.get("persona_id", "user_001"))}</code>，
      但它是早期 Wendy-like 单人剧本，不是从刚才 12 个 archetype pool 里重新采样出来的新人。
      因此它能证明链路形态，但不能证明“多样化人物采样”。
    </div>
  </section>

  <section>
    <h2>具体实例人 z</h2>
    {_persona_table(z)}
  </section>

  <section>
    <h2>事件线 L</h2>
    <p class="meta">每条事件线都有跨天阶段：initial、recurrence、turning_point、resolution、reflection。</p>
    {''.join(_event_line_card(line) for line in lines)}
  </section>

  <section>
    <h2>30 天时间轴</h2>
    {_timeline_table(days)}
  </section>
</main>
</body>
</html>
"""


def _persona_table(z: dict[str, Any]) -> str:
    attrs = z.get("stable_attributes", {}) if isinstance(z.get("stable_attributes"), dict) else {}
    return f"""
    <table>
      <tbody>
        <tr><th>persona_id</th><td><code>{_esc(z.get("persona_id"))}</code></td></tr>
        <tr><th>名称</th><td>{_esc(z.get("name"))}</td></tr>
        <tr><th>actor_id</th><td><code>{_esc(z.get("actor_id"))}</code></td></tr>
        <tr><th>年龄/职业</th><td>{_esc(attrs.get("age"))} · {_esc(attrs.get("occupation"))}</td></tr>
        <tr><th>家庭</th><td>{_esc(attrs.get("family_status"))}；孩子年龄 {_esc(attrs.get("child_age"))}</td></tr>
        <tr><th>生活处境</th><td>{_esc(attrs.get("life_situation"))}</td></tr>
        <tr><th>互动风格</th><td>{_esc(attrs.get("interaction_style"))}</td></tr>
        <tr><th>人格特征</th><td>{_tags(z.get("personality_traits", []))}</td></tr>
        <tr><th>压力来源</th><td>{_tags(z.get("pressure_sources", []))}</td></tr>
        <tr><th>长期目标</th><td>{_tags(z.get("long_term_goals", []))}</td></tr>
      </tbody>
    </table>
    """


def _event_line_card(line: dict[str, Any]) -> str:
    stages = line.get("stage_sequence", [])
    rows = "".join(
        "<tr>"
        f"<td>{_esc(stage.get('day'))}</td>"
        f"<td><code>{_esc(stage.get('message_id'))}</code></td>"
        f"<td>{_esc(stage.get('stage'))}</td>"
        f"<td>{_esc(stage.get('surface_event'))}</td>"
        f"<td>{_esc(stage.get('latent_continuity'))}</td>"
        "</tr>"
        for stage in stages
        if isinstance(stage, dict)
    )
    return f"""
    <details class="line" open>
      <summary>
        <code>{_esc(line.get("event_line_id"))}</code> · {_esc(line.get("label"))}
        · {len(stages)} 次出现
      </summary>
      <div class="line-body">
        <table>
          <tbody>
            <tr><th>theme_id</th><td><code>{_esc(line.get("theme_id"))}</code></td></tr>
            <tr><th>root_event_id</th><td><code>{_esc(line.get("root_event_id"))}</code></td></tr>
            <tr><th>source_event_ids</th><td>{_tags(line.get("source_event_ids", []))}</td></tr>
            <tr><th>interaction_unit_ids</th><td>{_tags(line.get("interaction_unit_ids", []))}</td></tr>
            <tr><th>probe_ids</th><td>{_tags(line.get("probe_ids", []))}</td></tr>
          </tbody>
        </table>
        <table>
          <thead><tr><th>天</th><th>message</th><th>阶段</th><th>用户表层事件</th><th>连续性约束</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </details>
    """


def _timeline_table(days: list[dict[str, Any]]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{_esc(day.get('day'))}</td>"
        f"<td>{_esc(day.get('main_topic'))}</td>"
        f"<td>{_esc(day.get('event_stage'))}</td>"
        f"<td><code>{_esc(day.get('opening_message_id'))}</code></td>"
        f"<td><code>{_esc(day.get('tau', {}).get('event_line_id'))}</code></td>"
        f"<td>{_esc(day.get('surface_event'))}</td>"
        "</tr>"
        for day in days
    )
    return (
        "<table><thead><tr><th>天</th><th>主题</th><th>阶段</th><th>message</th>"
        "<th>event_line</th><th>开场原文</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _metric(value: str, number: Any, label: str) -> str:
    return (
        "<div class='metric'>"
        f"<strong>{_esc(number)}</strong>"
        f"<span>{_esc(value)} · {_esc(label)}</span>"
        "</div>"
    )


def _tags(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "<span class='meta'>未提供</span>"
    return "".join(f"<span class='tag'>{_esc(item)}</span>" for item in values)


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
