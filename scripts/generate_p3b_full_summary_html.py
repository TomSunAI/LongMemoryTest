#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DAILY_PATH = DATA_DIR / "daily_interaction_units.json"
NATURALIZED_PATH = DATA_DIR / "daily_interaction_naturalized_candidates_deepseek_all440.json"
OUTPUT = REPO_ROOT / "docs/p3b_deepseek_full_summary.html"


def main() -> int:
    daily = _load_json(DAILY_PATH)
    naturalized = _load_json(NATURALIZED_PATH)
    units = _all_units(daily)
    unit_by_id = {str(unit.get("interaction_unit_id")): unit for unit in units}
    candidates = [
        candidate
        for candidate in naturalized.get("naturalized_dialogues", [])
        if isinstance(candidate, dict)
    ]
    candidate_by_id = {
        str(candidate.get("source_interaction_unit_id")): candidate
        for candidate in candidates
    }
    OUTPUT.write_text(
        _render(
            daily=daily,
            naturalized=naturalized,
            units=units,
            unit_by_id=unit_by_id,
            candidates=candidates,
            candidate_by_id=candidate_by_id,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")
    return 0


def _render(
    *,
    daily: dict[str, Any],
    naturalized: dict[str, Any],
    units: list[dict[str, Any]],
    unit_by_id: dict[str, dict[str, Any]],
    candidates: list[dict[str, Any]],
    candidate_by_id: dict[str, dict[str, Any]],
) -> str:
    daily_summary = daily.get("summary", {})
    p3b_summary = naturalized.get("summary", {})
    validation_counts = Counter(str(item.get("validation", {}).get("status", "unknown")) for item in candidates)
    followup_counts = Counter(len(item.get("followup_user_messages") or []) for item in candidates)
    fact_count_counts = Counter(len(item.get("fact_ids_used") or []) for item in candidates)
    stage_counts = Counter(str(unit.get("event_stage")) for unit in units)
    missing = sorted(set(unit_by_id) - set(candidate_by_id))
    extra = sorted(set(candidate_by_id) - set(unit_by_id))
    fact_usage = _fact_usage(candidates)
    persona_rows = _persona_rows(daily=daily, candidate_by_id=candidate_by_id)
    examples = _pick_examples(units=units, candidate_by_id=candidate_by_id)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>P3B 全量运行汇总</title>
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
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 18px 54px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
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
    .hero {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 18px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .metric, .section, .card, .box {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .metric {{ padding: 12px; }}
    .metric b {{ display: block; font-size: 24px; line-height: 1.2; }}
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
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .box {{ padding: 12px; background: var(--soft); }}
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
    .cards {{
      display: grid;
      gap: 12px;
    }}
    .card {{ overflow: hidden; }}
    .card header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    .card-body {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 12px;
      padding: 12px;
    }}
    .turn {{
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      white-space: pre-wrap;
    }}
    .label {{
      margin: 10px 0 4px;
      color: var(--muted);
      font-weight: 800;
      font-size: 12px;
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
    .tag.warn {{ background: #fef3f2; color: var(--warn); }}
    ul {{ margin: 0; padding-left: 18px; }}
    li + li {{ margin-top: 4px; }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 12px; }}
    @media (max-width: 920px) {{
      .summary, .grid, .card-body {{ grid-template-columns: 1fr; }}
      .section > header, .card header {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>P3B 全量运行汇总</h1>
      <p>本页总结当前全量 DeepSeek P3B 自然化结果。P3B 只负责把 I unit 自然化为用户话术候选，不覆盖 canonical I，也不新增事实边界之外的内容。</p>
      <div class="summary">
        {_metric("persona", daily_summary.get("persona_count"))}
        {_metric("canonical I", daily_summary.get("interaction_unit_count"))}
        {_metric("P3B candidates", p3b_summary.get("candidate_count"))}
        {_metric("pass", p3b_summary.get("pass_count"))}
        {_metric("fail", p3b_summary.get("fail_count"))}
        {_metric("missing", len(missing))}
      </div>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>1. 当前结论</h2>
          <p class="muted">先看是否完整、是否通过、是否仍保留结构化真值。</p>
        </div>
        <span class="tag p3b">{_esc(naturalized.get("llm_model"))}</span>
      </header>
      <div class="section-body">
        {_table(["检查项", "结果", "解释"], [
            ("覆盖完整性", f"{len(candidate_by_id)} / {len(unit_by_id)}", "每个 canonical I unit 都有一个 P3B 自然化候选。"),
            ("校验状态", _counter_text(validation_counts), "所有候选均经过 source id、fact id、follow-up budget、opening 改写校验。"),
            ("缺失/孤立候选", f"missing={len(missing)}；extra={len(extra)}", "missing 是 I 没有 P3B；extra 是 P3B 找不到对应 I。"),
            ("opening 改写", f"{_opening_rewritten(candidates)} / {len(candidates)}", "P3B opening 没有与 canonical opening 完全相同。"),
            ("候选层边界", "candidate only", "P3B 结果保存在 naturalized candidates 文件中，不写回 scripted_opening。"),
        ])}
      </div>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>2. 数据分布</h2>
          <p class="muted">看 P3B 的自然化长度、事实使用和阶段覆盖。</p>
        </div>
        <span class="tag">distribution</span>
      </header>
      <div class="section-body grid">
        <div class="box">
          <h3>运行分布</h3>
          {_table(["项目", "分布"], [
              ("event stage", _counter_text(stage_counts)),
              ("follow-up count", _counter_text(followup_counts)),
              ("fact_ids_used count", _counter_text(fact_count_counts)),
          ])}
        </div>
        <div class="box">
          <h3>事实使用</h3>
          {_table(["事实类型", "使用次数"], [
              ("current_state_change_fact", f"{fact_usage['current_state_change_fact']} / {len(candidates)}"),
              ("stage_delta_fact", f"{fact_usage['stage_delta_fact']} / {len(candidates)}"),
              ("latent concern", f"{fact_usage['latent_concern']} / {len(candidates)}"),
              ("event_title", f"{fact_usage['event_title']} / {len(candidates)}"),
              ("persona fact", f"{fact_usage['persona_fact']} / {len(candidates)}"),
          ])}
        </div>
      </div>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>3. Persona 概览</h2>
          <p class="muted">每个人 88 条 I，均已完成 P3B。</p>
        </div>
        <span class="tag">{_esc(daily_summary.get("persona_count"))} personas</span>
      </header>
      <div class="section-body">
        {_table(["persona", "I/P3B", "pass/fail", "stage 分布", "follow-up 分布", "probe 数"], persona_rows)}
      </div>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>4. 关键例子</h2>
          <p class="muted">抽取不同阶段和高信息量的 P3B 输出，用于人工检查。</p>
        </div>
        <span class="tag">examples</span>
      </header>
      <div class="section-body cards">
        {''.join(_example_card(unit=unit, candidate=candidate_by_id[str(unit.get("interaction_unit_id"))]) for unit in examples)}
      </div>
    </section>

    <section class="section">
      <header>
        <div>
          <h2>5. 文件位置</h2>
          <p class="muted">后续复查和继续实验时主要看这几个产物。</p>
        </div>
      </header>
      <div class="section-body">
        {_table(["文件", "作用"], [
            (str(DAILY_PATH.relative_to(REPO_ROOT)), "canonical I units，结构化真值。"),
            (str(NATURALIZED_PATH.relative_to(REPO_ROOT)), "DeepSeek 全量 P3B 自然化候选。"),
            ("docs/p3b_deepseek_all_rounds_report.html", "440 条全量明细报告。"),
            (str(OUTPUT.relative_to(REPO_ROOT)), "当前汇总页。"),
        ])}
      </div>
    </section>
  </main>
</body>
</html>
"""


def _example_card(*, unit: dict[str, Any], candidate: dict[str, Any]) -> str:
    opening = unit.get("scripted_opening", {}) if isinstance(unit.get("scripted_opening"), dict) else {}
    current_fact = unit.get("current_state_change_fact", {})
    followups = candidate.get("followup_user_messages", [])
    if not isinstance(followups, list):
        followups = []
    return f"""
      <article class="card">
        <header>
          <div>
            <p class="muted"><code>{_esc(unit.get("persona_id"))}</code> · <code>{_esc(unit.get("interaction_unit_id"))}</code> · Day {_esc(unit.get("day"))} · M{_esc(unit.get("within_day_index"))}</p>
            <h3>{_esc(_event_title(unit))}</h3>
          </div>
          <div>
            <span class="tag">{_esc(unit.get("event_stage"))}</span>
            <span class="tag">occurrence {_esc(unit.get("occurrence_index"))}</span>
            <span class="tag ok">{_esc(candidate.get("validation", {}).get("status"))}</span>
          </div>
        </header>
        <div class="card-body">
          <div>
            <p class="label">I 中文模板</p>
            <div class="turn">{_esc(opening.get("user_message_zh") or opening.get("user_message"))}</div>
            <p class="label">P3B opening</p>
            <div class="turn">{_esc(candidate.get("opening_user_message"))}</div>
            {_followup_html(followups)}
          </div>
          <div>
            <p class="label">current_state_change_fact</p>
            <div class="turn">{_esc(_fact_text(current_fact))}</div>
            <p class="label">fact_ids_used</p>
            {_ul(candidate.get("fact_ids_used", []))}
            <p class="label">notes</p>
            <div class="turn">{_esc(candidate.get("notes"))}</div>
          </div>
        </div>
      </article>
"""


def _persona_rows(*, daily: dict[str, Any], candidate_by_id: dict[str, dict[str, Any]]) -> list[tuple[Any, ...]]:
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
        candidates = [
            candidate_by_id[str(unit.get("interaction_unit_id"))]
            for unit in units
            if str(unit.get("interaction_unit_id")) in candidate_by_id
        ]
        validation = Counter(str(item.get("validation", {}).get("status", "unknown")) for item in candidates)
        stages = Counter(str(unit.get("event_stage")) for unit in units)
        followups = Counter(len(item.get("followup_user_messages") or []) for item in candidates)
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


def _pick_examples(
    *,
    units: list[dict[str, Any]],
    candidate_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for stage in ["initial", "recurrence", "partial_resolution", "turning_point", "reflection"]:
        stage_units = [
            unit
            for unit in units
            if str(unit.get("event_stage")) == stage
            and str(unit.get("interaction_unit_id")) in candidate_by_id
        ]
        if not stage_units:
            continue
        unit = sorted(
            stage_units,
            key=lambda item: _example_score(
                unit=item,
                candidate=candidate_by_id[str(item.get("interaction_unit_id"))],
            ),
            reverse=True,
        )[0]
        unit_id = str(unit.get("interaction_unit_id"))
        if unit_id not in seen:
            selected.append(unit)
            seen.add(unit_id)
    for unit in sorted(
        units,
        key=lambda item: _example_score(
            unit=item,
            candidate=candidate_by_id.get(str(item.get("interaction_unit_id")), {}),
        ),
        reverse=True,
    ):
        unit_id = str(unit.get("interaction_unit_id"))
        if unit_id in seen or unit_id not in candidate_by_id:
            continue
        selected.append(unit)
        seen.add(unit_id)
        if len(selected) >= 8:
            break
    return selected


def _example_score(*, unit: dict[str, Any], candidate: dict[str, Any]) -> tuple[int, int, int, int]:
    followups = candidate.get("followup_user_messages", [])
    followup_count = len(followups) if isinstance(followups, list) else 0
    fact_ids = candidate.get("fact_ids_used", [])
    if not isinstance(fact_ids, list):
        fact_ids = []
    stage_or_latent = sum(
        1
        for fact_id in fact_ids
        if "stage_delta_fact" in str(fact_id) or ":latent_" in str(fact_id)
    )
    current = 1 if any("current_state_change_fact" in str(fact_id) for fact_id in fact_ids) else 0
    day = int(unit.get("day") or 0)
    return followup_count, stage_or_latent, current, day


def _fact_usage(candidates: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "current_state_change_fact": sum(_candidate_uses(item, "current_state_change_fact") for item in candidates),
        "stage_delta_fact": sum(_candidate_uses(item, "stage_delta_fact") for item in candidates),
        "latent_concern": sum(_candidate_uses(item, ":latent_") for item in candidates),
        "event_title": sum(_candidate_uses(item, "event_title") for item in candidates),
        "persona_fact": sum(_candidate_uses(item, "persona_") for item in candidates),
    }


def _candidate_uses(candidate: dict[str, Any], needle: str) -> bool:
    fact_ids = candidate.get("fact_ids_used", [])
    return isinstance(fact_ids, list) and any(needle in str(fact_id) for fact_id in fact_ids)


def _opening_rewritten(candidates: list[dict[str, Any]]) -> int:
    return sum(
        str(candidate.get("opening_user_message") or "")
        != str(candidate.get("canonical_opening_user_message") or "")
        for candidate in candidates
    )


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


def _followup_html(followups: list[Any]) -> str:
    blocks = []
    for index, text in enumerate(followups, start=1):
        blocks.append(f'<p class="label">P3B follow-up {index}</p><div class="turn">{_esc(text)}</div>')
    return "".join(blocks)


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><b>{_esc(value)}</b><span>{_esc(label)}</span></div>'


def _table(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    header_html = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    row_html = []
    for row in rows:
        row_html.append("<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(row_html)}</tbody></table>"


def _counter_text(counter: Counter[Any]) -> str:
    if not counter:
        return "无"
    return "；".join(f"{key}: {value}" for key, value in counter.most_common())


def _ul(values: Any) -> str:
    if not isinstance(values, list):
        return '<p class="muted">无</p>'
    items = [f"<li>{_esc(value)}</li>" for value in values if value not in (None, "")]
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
