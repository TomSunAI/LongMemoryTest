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

from long_memory_test.sampling.zh_localization import (  # noqa: E402
    event_category_summary_zh,
    event_category_title_zh,
    event_domain_zh,
    zh_list,
)


EVENT_POOL = REPO_ROOT / "long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json"
OUTPUT = REPO_ROOT / "docs/original_event_category_pool_e.html"


def main() -> int:
    pool = _load_json(EVENT_POOL)
    events = [
        event for event in pool.get("event_categories", []) if isinstance(event, dict)
    ]
    html_text = _page(pool=pool, events=events)
    OUTPUT.write_text(html_text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


def _page(*, pool: dict[str, Any], events: list[dict[str, Any]]) -> str:
    domain_counts = Counter(str(event.get("event_domain")) for event in events)
    cards = "\n".join(_event_card(event, index) for index, event in enumerate(events, start=1))
    domain_tags = "".join(
        f'<span class="tag">{_esc(event_domain_zh(domain))} <b>{count}</b></span>'
        for domain, count in sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>原始 E 事件类别池</title>
  <style>
    :root {{
      --ink: #18212f;
      --muted: #687386;
      --line: #d9e1ea;
      --panel: #ffffff;
      --band: #f5f7fb;
      --accent: #176b87;
      --accent-2: #806118;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--band);
      font: 14px/1.58 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 18px 48px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ margin-bottom: 8px; font-size: 28px; letter-spacing: 0; }}
    .meta {{ color: var(--muted); }}
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
      gap: 12px;
      margin: 18px 0;
    }}
    .metric {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .metric b {{ display: block; font-size: 24px; }}
    .domains {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .tag {{
      display: inline-block;
      margin: 0 6px 6px 0;
      padding: 3px 8px;
      border-radius: 999px;
      background: #eef6fa;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    .event {{
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      overflow: hidden;
    }}
    .event header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .event h2 {{ margin-top: 4px; font-size: 18px; }}
    .body {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 0;
    }}
    .raw, .zh {{
      padding: 14px 16px;
    }}
    .raw {{ border-right: 1px solid var(--line); }}
    .raw h3, .zh h3 {{
      margin-bottom: 8px;
      font-size: 14px;
      color: var(--muted);
    }}
    .row {{
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed var(--line);
    }}
    .row b {{
      display: block;
      margin-bottom: 4px;
      color: var(--muted);
      font-size: 12px;
    }}
    .list {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .pill {{
      padding: 2px 7px;
      border-radius: 999px;
      background: #f1f5f9;
      color: #374151;
      font-size: 12px;
    }}
    .zh .pill {{ background: #fff4df; color: var(--accent-2); }}
    @media (max-width: 900px) {{
      .summary, .body {{ grid-template-columns: 1fr; }}
      .raw {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .event header {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>原始 E 事件类别池</h1>
    <p class="meta">来源：<code>{_esc(_rel(EVENT_POOL))}</code></p>
    <section class="summary">
      <div class="metric"><b>{_esc(pool.get("schema_version"))}</b><span>schema_version</span></div>
      <div class="metric"><b>{len(events)}</b><span>event_categories</span></div>
      <div class="metric"><b>{len(domain_counts)}</b><span>event_domain 数</span></div>
      <div class="metric"><b>{_esc(pool.get("name"))}</b><span>name</span></div>
    </section>
    <section class="domains">{domain_tags}</section>
    {cards}
  </main>
</body>
</html>
"""


def _event_card(event: dict[str, Any], index: int) -> str:
    raw_uncertainties = _pills(event.get("possible_uncertainties", []))
    raw_actions = _pills(event.get("possible_actions", []))
    raw_emotions = _pills(event.get("possible_emotional_load", []))
    raw_risks = _pills(event.get("memory_risks", []))
    zh_uncertainties = _pills(zh_list(event.get("possible_uncertainties", [])))
    zh_actions = _pills(zh_list(event.get("possible_actions", [])))
    zh_emotions = _pills(zh_list(event.get("possible_emotional_load", [])))
    zh_risks = _pills(zh_list(event.get("memory_risks", [])))
    stage_patterns = event.get("stage_patterns", [])
    return f"""
    <article class="event" id="{_esc(event.get("event_category_id"))}">
      <header>
        <div>
          <p><code>#{index:02d}</code> <code>{_esc(event.get("event_category_id"))}</code> <code>{_esc(event.get("event_type"))}</code></p>
          <h2>{_esc(event_category_title_zh(event))}</h2>
        </div>
        <div><span class="tag">{_esc(event_domain_zh(event.get("event_domain")))}</span></div>
      </header>
      <div class="body">
        <section class="raw">
          <h3>原始 JSON 字段</h3>
          {_row("title", event.get("title"))}
          {_row("core_issue", event.get("core_issue"))}
          {_row("event_domain", event.get("event_domain"))}
          {_row("stage_patterns", stage_patterns)}
          {_row("possible_uncertainties", raw_uncertainties, raw_html=True)}
          {_row("possible_actions", raw_actions, raw_html=True)}
          {_row("possible_emotional_load", raw_emotions, raw_html=True)}
          {_row("memory_risks", raw_risks, raw_html=True)}
          {_row("compatible_archetypes", _pills(event.get("compatible_archetypes", [])), raw_html=True)}
          {_row("incompatible_archetypes", _pills(event.get("incompatible_archetypes", [])), raw_html=True)}
        </section>
        <section class="zh">
          <h3>当前工程中文展示</h3>
          {_row("中文 title", event_category_title_zh(event))}
          {_row("中文 core_issue", event_category_summary_zh(event))}
          {_row("中文 domain", event_domain_zh(event.get("event_domain")))}
          {_row("possible_uncertainties", zh_uncertainties, raw_html=True)}
          {_row("possible_actions", zh_actions, raw_html=True)}
          {_row("possible_emotional_load", zh_emotions, raw_html=True)}
          {_row("memory_risks", zh_risks, raw_html=True)}
        </section>
      </div>
    </article>
"""


def _row(label: str, value: Any, *, raw_html: bool = False) -> str:
    if isinstance(value, list):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value if value is not None else "")
    if not raw_html:
        text = _esc(text)
    return f'<div class="row"><b>{_esc(label)}</b><span>{text}</span></div>'


def _pills(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    items = [str(item) for item in values if item is not None and str(item)]
    return '<div class="list">' + "".join(f'<span class="pill">{_esc(item)}</span>' for item in items) + "</div>"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


if __name__ == "__main__":
    raise SystemExit(main())
