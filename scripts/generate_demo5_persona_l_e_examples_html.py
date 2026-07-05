#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.sampling.zh_localization import event_domain_zh  # noqa: E402


DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
OUTPUT = REPO_ROOT / "docs/demo5_persona_l_e_examples.html"


def main() -> int:
    personas = _load_json(DATA_DIR / "sampled_personas.json").get("personas", [])
    accepted_sets = _load_json(DATA_DIR / "accepted_persona_event_sets.json").get(
        "accepted_persona_event_sets", []
    )
    event_line_batch = _load_json(DATA_DIR / "event_lines_batch.json").get("personas", [])

    accepted_by_persona = {
        str(item.get("persona_id")): item.get("accepted_events", [])
        for item in accepted_sets
        if isinstance(item, dict)
    }
    lines_by_persona = {
        str(item.get("construction_scope", {}).get("persona_id") or item.get("persona_id")): item.get(
            "event_lines", []
        )
        for item in event_line_batch
        if isinstance(item, dict)
    }

    html_text = _page(
        personas=personas,
        accepted_by_persona=accepted_by_persona,
        lines_by_persona=lines_by_persona,
    )
    OUTPUT.write_text(html_text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


def _page(
    *,
    personas: list[dict[str, Any]],
    accepted_by_persona: dict[str, list[dict[str, Any]]],
    lines_by_persona: dict[str, list[dict[str, Any]]],
) -> str:
    cards = []
    for persona in personas:
        persona_id = str(persona.get("persona_id"))
        lines = lines_by_persona.get(persona_id, [])
        line_by_event_id = {
            str(line.get("event_category_id")): line
            for line in lines
            if isinstance(line, dict)
        }
        examples = []
        for event in accepted_by_persona.get(persona_id, [])[:3]:
            event_id = str(event.get("event_category_id"))
            line = line_by_event_id.get(event_id, {})
            examples.append(_example_block(event=event, line=line))
        cards.append(
            f"""
      <section class="persona">
        <header>
          <div>
            <p class="id">{_esc(persona_id)}</p>
            <h2>{_esc(persona.get("source_archetype_label"))}</h2>
          </div>
          <span>{_esc(persona.get("age_range"))}</span>
        </header>
        <div class="profile">
          {_field("职业", persona.get("occupation"))}
          {_field("家庭结构", persona.get("family_structure"))}
          {_field("生活领域", persona.get("primary_life_domains"))}
          {_field("长期目标", persona.get("long_term_goals"))}
          {_field("压力反应", persona.get("stress_response"))}
        </div>
        <div class="examples">
          {''.join(examples)}
        </div>
      </section>
"""
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>5 人 E/L 示例</title>
  <style>
    :root {{
      --ink: #18212f;
      --muted: #667085;
      --line: #d9e0ea;
      --panel: #ffffff;
      --band: #f5f7fb;
      --accent: #1b7f79;
      --accent-2: #8a5a14;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--band);
      font: 14px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 18px 48px;
    }}
    h1 {{
      margin: 0 0 18px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    h2, h3, p {{ margin: 0; }}
    code {{
      padding: 1px 5px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #f8fafc;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }}
    .persona {{
      margin-top: 18px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .persona header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 12px;
    }}
    .persona header span {{
      white-space: nowrap;
      color: var(--accent);
      font-weight: 700;
    }}
    .id {{
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }}
    .profile {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .field {{
      min-height: 76px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfe;
    }}
    .field b {{
      display: block;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .examples {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .example {{
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }}
    .e, .l {{ padding: 12px; }}
    .e {{
      border-bottom: 1px solid var(--line);
      background: #f8fbfb;
    }}
    .l {{ background: #fffaf3; }}
    .tag {{
      display: inline-block;
      margin: 0 6px 6px 0;
      padding: 2px 7px;
      border-radius: 999px;
      background: #eef6f5;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    .line-tag {{
      background: #fff2dc;
      color: var(--accent-2);
    }}
    .title {{
      margin: 4px 0 6px;
      font-size: 16px;
      font-weight: 800;
    }}
    .summary {{
      color: #3b4758;
    }}
    .stage {{
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed var(--line);
    }}
    .stage b {{
      display: inline-block;
      margin-bottom: 4px;
      color: var(--accent-2);
    }}
    @media (max-width: 920px) {{
      .profile, .examples {{ grid-template-columns: 1fr; }}
      .persona header {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>5 人具体例子 · E / L 示例</h1>
    {''.join(cards)}
  </main>
</body>
</html>
"""


def _example_block(*, event: dict[str, Any], line: dict[str, Any]) -> str:
    stages = [
        stage
        for stage in line.get("stage_sequence", [])[:3]
        if isinstance(stage, dict)
    ]
    stage_html = "".join(
        f"""
        <div class="stage">
          <b>{_esc(stage.get("source_stage_label") or stage.get("event_stage"))}</b>
          <p>{_esc(stage.get("user_message_seed"))}</p>
        </div>
"""
        for stage in stages
    )
    return f"""
      <article class="example">
        <div class="e">
          <span class="tag">E</span><code>{_esc(event.get("event_category_id"))}</code>
          <p class="title">{_esc(event.get("title"))}</p>
          <p class="summary">{_esc(event.get("core_issue"))}</p>
          <p><span class="tag">{_esc(event_domain_zh(event.get("event_domain")))}</span></p>
        </div>
        <div class="l">
          <span class="tag line-tag">L</span><code>{_esc(line.get("event_line_id"))}</code>
          <p class="title">{_esc(_title(line))}</p>
          <p class="summary">{_esc(line.get("persistent_event_summary"))}</p>
          {stage_html}
        </div>
      </article>
"""


def _title(line: dict[str, Any]) -> str:
    title = line.get("event_title", {})
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or "")
    return str(title or "")


def _field(label: str, value: Any) -> str:
    if isinstance(value, list):
        text = "、".join(str(item) for item in value)
    else:
        text = str(value or "")
    return f'<div class="field"><b>{_esc(label)}</b><span>{_esc(text)}</span></div>'


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


if __name__ == "__main__":
    raise SystemExit(main())
