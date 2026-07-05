#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENT_LINES = (
    REPO_ROOT / "long_memory_experiment/data/generated/json_sourced_instance_p0001/event_lines.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "docs/json_sourced_instance_p0001_event_lines_report.html"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate P1 event-line HTML report.")
    parser.add_argument("--event-lines", type=Path, default=DEFAULT_EVENT_LINES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    event_lines = _load_json(args.event_lines)
    html_text = render_report(event_lines=event_lines, event_lines_path=args.event_lines)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(*, event_lines: dict[str, Any], event_lines_path: Path) -> str:
    lines = [item for item in event_lines.get("event_lines", []) if isinstance(item, dict)]
    total_stages = sum(len(line.get("stage_sequence", [])) for line in lines)
    persona = event_lines.get("persona_ref", {})
    cards = "".join(_line_card(line) for line in lines)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>P1 JSON 来源事件线报告</title>
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
    main {{ max-width: 1240px; margin: 0 auto; padding: 34px 26px 72px; }}
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
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
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
    @media (max-width: 900px) {{
      main {{ padding: 24px 14px 56px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>P1 JSON 来源事件线报告</h1>
  <p class="meta">事件线文件：<code>{_esc(_rel(event_lines_path))}</code></p>

  <section>
    <h2>构建状态</h2>
    <div class="grid">
      {_metric("persona", persona.get("persona_id", "-"), "实例人")}
      {_metric("event lines", len(lines), "事件线")}
      {_metric("stages", total_stages, "阶段总数")}
      {_metric("timeline", "未生成", "下一步")}
    </div>
    <div class="callout">
      这一步已经完成 P1 的 <code>event_lines.json</code>：
      每条接受事件类别被展开成 5 个阶段。
      还没有安排具体日期，所以这不是 timeline；day-level timeline 是下一步。
    </div>
  </section>

  <section>
    <h2>人物引用</h2>
    <table>
      <tbody>
        <tr><th>persona_id</th><td><code>{_esc(persona.get("persona_id"))}</code></td></tr>
        <tr><th>source_archetype</th><td><code>{_esc(persona.get("source_archetype"))}</code></td></tr>
        <tr><th>occupation</th><td>{_esc(persona.get("occupation"))}</td></tr>
        <tr><th>family_structure</th><td>{_esc(persona.get("family_structure"))}</td></tr>
        <tr><th>primary_life_domains</th><td>{_tags(persona.get("primary_life_domains", []))}</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>事件线明细</h2>
    {cards}
  </section>
</main>
</body>
</html>
"""


def _line_card(line: dict[str, Any]) -> str:
    stages = [item for item in line.get("stage_sequence", []) if isinstance(item, dict)]
    rows = "".join(
        "<tr>"
        f"<td>{_esc(stage.get('stage_index'))}</td>"
        f"<td>{_esc(stage.get('event_stage'))}</td>"
        f"<td>{_esc(stage.get('stage_goal'))}</td>"
        f"<td>{_esc(stage.get('user_message_seed'))}</td>"
        f"<td>{_esc(stage.get('assistant_memory_expectation'))}</td>"
        "</tr>"
        for stage in stages
    )
    return f"""
    <details class="line" open>
      <summary>
        <code>{_esc(line.get("event_line_id"))}</code>
        · {_esc(line.get("event_title", {}).get("zh"))}
        · {_esc(line.get("event_domain_zh"))}
      </summary>
      <div class="line-body">
        <table>
          <tbody>
            <tr><th>event_category_id</th><td><code>{_esc(line.get("event_category_id"))}</code></td></tr>
            <tr><th>persistent_event_summary</th><td>{_esc(line.get("persistent_event_summary"))}</td></tr>
            <tr><th>participants</th><td>{_tags(line.get("participants", []))}</td></tr>
            <tr><th>latent_concerns</th><td>{_tags(line.get("latent_concerns", []))}</td></tr>
          </tbody>
        </table>
        <table>
          <thead><tr><th>#</th><th>阶段</th><th>阶段目标</th><th>用户消息种子</th><th>助手记忆期待</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </details>
    """


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
