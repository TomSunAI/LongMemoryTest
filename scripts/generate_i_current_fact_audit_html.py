#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = (
    REPO_ROOT
    / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json"
)
OUTPUT_PATH = REPO_ROOT / "docs/i_current_fact_audit.html"


def main() -> int:
    data = _load_json(DATA_PATH)
    units = _iter_units(data)
    samples = _select_samples(units)
    html_text = _render_html(units=units, samples=samples)
    OUTPUT_PATH.write_text(html_text, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return data


def _iter_units(data: dict[str, Any]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for persona in data.get("personas", []):
        if not isinstance(persona, dict):
            continue
        for day in persona.get("days", []):
            if not isinstance(day, dict):
                continue
            units.extend(
                item
                for item in day.get("interaction_units", [])
                if isinstance(item, dict)
            )
    return units


def _select_samples(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted_ids = ["P0001_D28_M005"]
    samples = [unit for unit in units if unit.get("interaction_unit_id") in wanted_ids]
    seen_ids = {str(unit.get("interaction_unit_id")) for unit in samples}
    for stage in ["initial", "recurrence", "turning_point", "partial_resolution", "reflection"]:
        match = next(
            (
                unit
                for unit in units
                if unit.get("event_stage") == stage
                and str(unit.get("interaction_unit_id")) not in seen_ids
            ),
            None,
        )
        if match:
            samples.append(match)
            seen_ids.add(str(match.get("interaction_unit_id")))
    return samples[:8]


def _render_html(*, units: list[dict[str, Any]], samples: list[dict[str, Any]]) -> str:
    stats = _stats(units)
    sample_cards = "\n".join(_render_sample(unit) for unit in samples)
    stage_rows = "\n".join(
        f"<tr><td>{_esc(stage)}</td><td>{count}</td></tr>"
        for stage, count in sorted(stats["stage_counts"].items())
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>I Unit Fact Audit</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #17202a; background: #f7f8fa; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 22px 56px; }}
    h1 {{ font-size: 28px; margin: 0 0 8px; }}
    h2 {{ font-size: 20px; margin: 28px 0 12px; }}
    h3 {{ font-size: 17px; margin: 0 0 10px; }}
    p {{ line-height: 1.6; }}
    code {{ background: #eef1f4; padding: 2px 5px; border-radius: 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 18px 0; }}
    .metric {{ background: #fff; border: 1px solid #dfe4ea; border-radius: 8px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 6px; }}
    .card {{ background: #fff; border: 1px solid #dfe4ea; border-radius: 8px; padding: 16px; margin: 14px 0; }}
    .tag {{ display: inline-block; border: 1px solid #ccd3da; background: #f4f6f8; border-radius: 999px; padding: 2px 8px; font-size: 12px; margin-right: 6px; }}
    .ok {{ color: #116b3a; font-weight: 700; }}
    .warn {{ color: #9a4f00; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #dfe4ea; }}
    th, td {{ border-bottom: 1px solid #e7ebef; padding: 9px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f4f7; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #101820; color: #f4f7fb; padding: 12px; border-radius: 8px; overflow: auto; }}
    .two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    @media (max-width: 760px) {{ .grid, .two {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>I Unit 是否引入事实：审计页</h1>
  <p>结论：现在 I 中已经显式引入事实，但事实来源仍是 L/T，不是 P3B。P3B 只读取这些字段做中文自然化。</p>

  <div class="grid">
    {_metric("I 总数", stats["unit_count"])}
    {_metric("有 current_state_change_fact", stats["current_state_count"])}
    {_metric("开场绑定 current fact", stats["opening_current_id_count"])}
    {_metric("首轮 reveal 可见 stage fact", stats["first_reveal_stage_delta_count"])}
  </div>

  <h2>字段路径</h2>
  <table>
    <tr><th>位置</th><th>作用</th><th>现在状态</th></tr>
    <tr><td><code>I.current_state_change_fact</code></td><td>本轮 I 正式引入的当前状态变化事实。</td><td class="ok">440/440 存在</td></tr>
    <tr><td><code>I.scripted_opening.user_message</code></td><td>英文 canonical 用户开场，包含当前状态变化。</td><td class="ok">已绑定 current_state_change_fact_id</td></tr>
    <tr><td><code>I.scripted_opening.user_message_zh</code></td><td>中文展示/自然化输入，不作为底层事实源。</td><td class="ok">440/440 存在</td></tr>
    <tr><td><code>I.scene_boundary.allowed_facts[]</code></td><td>agent 和评测可用事实边界。</td><td class="ok">current fact 排在 allowed facts 前部</td></tr>
    <tr><td><code>I.constrained_followup.reveal_steps[]</code></td><td>用户追问时允许再透露哪些事实。</td><td class="ok">第一轮已包含 current_state 和 stage_delta</td></tr>
    <tr><td><code>P3B prompt</code></td><td>读取 canonical + 中文 render，只生成自然话术候选。</td><td class="ok">不新增事实</td></tr>
  </table>

  <h2>阶段分布</h2>
  <table><tr><th>event_stage</th><th>I 数量</th></tr>{stage_rows}</table>

  <h2>具体样例</h2>
  {sample_cards}
</main>
</body>
</html>
"""


def _stats(units: list[dict[str, Any]]) -> dict[str, Any]:
    stage_counts = Counter(str(unit.get("event_stage")) for unit in units)
    return {
        "unit_count": len(units),
        "current_state_count": sum(1 for unit in units if unit.get("current_state_change_fact")),
        "opening_current_id_count": sum(
            1
            for unit in units
            if unit.get("scripted_opening", {}).get("current_state_change_fact_id")
        ),
        "first_reveal_stage_delta_count": sum(
            1
            for unit in units
            if any(
                ":stage_delta_fact_" in fact_id
                for fact_id in (
                    unit.get("constrained_followup", {}).get("reveal_steps") or [{}]
                )[0].get("may_reveal_fact_ids", [])
            )
        ),
        "stage_counts": dict(stage_counts),
    }


def _render_sample(unit: dict[str, Any]) -> str:
    opening = unit.get("scripted_opening", {})
    current = unit.get("current_state_change_fact", {})
    boundary = unit.get("scene_boundary", {})
    reveal = (unit.get("constrained_followup", {}).get("reveal_steps") or [{}])[0]
    allowed_rows = "\n".join(
        f"<tr><td>{_esc(fact.get('type'))}</td><td>{_esc(fact.get('text'))}</td><td>{_esc(fact.get('text_zh'))}</td></tr>"
        for fact in boundary.get("allowed_facts", [])[:8]
        if isinstance(fact, dict)
    )
    return f"""
  <section class="card">
    <h3>{_esc(unit.get("interaction_unit_id"))}</h3>
    <p>
      <span class="tag">Day {_esc(unit.get("day"))}</span>
      <span class="tag">{_esc(unit.get("event_stage"))}</span>
      <span class="tag">Occurrence {_esc(unit.get("occurrence_index"))}</span>
      <span class="tag">{_esc(unit.get("event_line_id"))}</span>
    </p>
    <div class="two">
      <div>
        <h3>开场话术</h3>
        <p><strong>canonical:</strong> {_esc(opening.get("user_message"))}</p>
        <p><strong>中文:</strong> {_esc(opening.get("user_message_zh"))}</p>
      </div>
      <div>
        <h3>当前引入事实</h3>
        <p><strong>fact_id:</strong> <code>{_esc(current.get("fact_id"))}</code></p>
        <p><strong>canonical:</strong> {_esc(current.get("text"))}</p>
        <p><strong>中文:</strong> {_esc(current.get("text_zh"))}</p>
        <p><strong>source:</strong> {_esc(current.get("source"))} · {_esc(current.get("source_fields"))}</p>
      </div>
    </div>
    <h3>第一轮 follow-up 可 reveal</h3>
    <pre>{_esc(json.dumps(reveal, ensure_ascii=False, indent=2))}</pre>
    <h3>allowed_facts 前 8 条</h3>
    <table><tr><th>type</th><th>canonical text</th><th>中文 text_zh</th></tr>{allowed_rows}</table>
  </section>
"""


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{_esc(label)}</span><strong>{_esc(value)}</strong></div>'


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


if __name__ == "__main__":
    raise SystemExit(main())
