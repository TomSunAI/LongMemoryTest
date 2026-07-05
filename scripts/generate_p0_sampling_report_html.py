#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = (
    REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
)
DEFAULT_OUTPUT = REPO_ROOT / "docs/p0_persona_event_sampling_demo5_report.html"


ARCHETYPE_CN = {
    "A01_early_career_renter": "早期职业阶段的城市租房者",
    "A02_service_emotional_labor": "承受情绪劳动的一线服务人员",
    "A03_gig_worker_parent": "收入波动且承担育儿压力的平台劳动者家长",
    "A04_small_business_owner": "在客流、现金流和家庭时间之间平衡的小生意经营者",
    "A05_single_parent_service_worker": "独自育儿且从事服务工作的单亲家长",
    "A06_midlife_caregiver": "同时维持工作和长辈照护的中年照护协调者",
    "A07_unemployed_job_seeker": "正在重建信心的中期职业求职者",
    "A08_shift_worker_family_pressure": "排班不稳定且家庭压力较高的轮班工作者",
    "A09_retirement_adjustment": "刚退休、正在重建生活节奏和身份感的人",
    "A10_international_student_admin_pressure": "承受行政手续和适应压力的留学生",
    "A11_adult_child_boundary_family": "与成年子女重新协商边界的中年父母",
    "A12_early_parenthood_return_to_work": "育婴后重返工作的早期父母",
}


DOMAIN_CN = {
    "administration": "行政手续",
    "adult_child_boundary": "成年子女边界",
    "business": "小生意经营",
    "childcare": "儿童照护",
    "community": "社区",
    "commuting": "通勤",
    "consumer_issue": "消费纠纷",
    "daily_life": "日常生活",
    "digital_life": "数字生活",
    "education": "教育/学业",
    "eldercare": "长辈照护",
    "family": "家庭",
    "finance": "财务",
    "gig_work": "平台/零工",
    "health_routine": "健康日常",
    "housing": "住房",
    "infant_care": "婴儿照护",
    "job_search": "求职",
    "learning": "学习转型",
    "neighborhood": "邻里",
    "personal_boundary": "个人边界",
    "personal_planning": "个人规划",
    "pet_care": "宠物照护",
    "relationship": "关系",
    "relocation": "搬迁适应",
    "retirement": "退休适应",
    "self_worth": "自我价值感",
    "social_connection": "社会连接",
    "visa_administration": "签证/留学行政",
    "work": "工作",
    "work_family_intersection": "工作-家庭交叉",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Chinese HTML report for P0 sampling.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads = {
        "sampled": _load_json(args.input_dir / "sampled_personas.json"),
        "candidates": _load_json(args.input_dir / "candidate_event_sets.json"),
        "accepted": _load_json(args.input_dir / "accepted_persona_event_sets.json"),
        "compatibility": _load_json(args.input_dir / "compatibility_report.json"),
        "realism": _load_json(args.input_dir / "realism_validation_report.json"),
    }
    html_text = render_report(input_dir=args.input_dir, payloads=payloads)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(*, input_dir: Path, payloads: dict[str, dict[str, Any]]) -> str:
    sampled = payloads["sampled"]
    accepted = payloads["accepted"]
    candidates = payloads["candidates"]
    compatibility = payloads["compatibility"]
    summary = compatibility.get("summary", {})
    personas = sampled.get("personas", [])
    persona_count = summary.get("persona_count", len(personas))
    title = f"P0 {persona_count} 人 Persona-Event 采样报告"
    accepted_by_persona = {
        str(item.get("persona_id")): item
        for item in accepted.get("accepted_persona_event_sets", [])
        if isinstance(item, dict)
    }
    candidates_by_persona = {
        str(item.get("persona_id")): item
        for item in candidates.get("candidate_event_sets", [])
        if isinstance(item, dict)
    }
    cards = "".join(
        _persona_card(
            persona=persona,
            accepted=accepted_by_persona.get(str(persona.get("persona_id")), {}),
            candidates=candidates_by_persona.get(str(persona.get("persona_id")), {}),
        )
        for persona in personas
        if isinstance(persona, dict)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)}</title>
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
    h3 {{ margin-top: 12px; font-size: 17px; }}
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
    .status-pass {{ color: var(--ok); font-weight: 700; }}
    .tag {{
      display: inline-block;
      margin: 2px 4px 2px 0;
      padding: 2px 7px;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid #d6e5ff;
      font-size: 12px;
    }}
    details.persona {{
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }}
    details.persona summary {{
      cursor: pointer;
      padding: 11px 13px;
      background: #fbfcfe;
      font-weight: 650;
    }}
    .persona-body {{ padding: 12px 14px 14px; }}
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
  <h1>{_esc(title)}</h1>
  <p class="meta">输入目录：<code>{_esc(_rel(input_dir))}</code></p>

  <section>
    <h2>当前生成进度</h2>
    <div class="grid">
      {_metric("P0 状态", compatibility.get("status", "-"), "兼容性验证")}
      {_metric("Persona", persona_count, "已生成")}
      {_metric("候选事件", summary.get("candidate_events_total", "-"), "P0 候选池")}
      {_metric("接受事件", summary.get("accepted_events_total", "-"), "进入 T")}
      {_metric("问题/警告", f"{summary.get('realism_issue_count', '-')}/{summary.get('realism_warning_count', '-')}", "realism")}
    </div>
    <div class="callout">
      当前完成到 <strong>P0</strong>：
      已生成 <code>z</code> 人物、候选事件集、兼容性报告和接受事件集合 <code>T</code>。
      <strong>P1 还没有开始</strong>，也就是尚未把接受事件展开成持续事件线 <code>L</code>、
      timeline、daily interactions 或 probe plan。
    </div>
  </section>

  <section>
    <h2>输出文件</h2>
    {_file_table(input_dir, persona_count=persona_count)}
  </section>

  <section>
    <h2>批量分布</h2>
    <h3>人物原型分布</h3>
    {_count_table(summary.get("source_archetype_counts", {}), labeler=_archetype_label)}
    <h3>接受事件领域分布</h3>
    {_count_table(summary.get("accepted_event_domain_counts", {}), labeler=_domain_label)}
  </section>

  <section>
    <h2>{_esc(persona_count)} 个 Persona 明细</h2>
    <p class="meta">
      每个卡片展示具体 persona 字段、接受事件，以及候选事件接受/拒绝理由。
      原始事件标题保留事件池英文写法，方便回连 JSON。
    </p>
    {cards}
  </section>
</main>
</body>
</html>
"""


def _persona_card(
    *,
    persona: dict[str, Any],
    accepted: dict[str, Any],
    candidates: dict[str, Any],
) -> str:
    persona_id = str(persona.get("persona_id", ""))
    archetype_id = str(persona.get("source_archetype", ""))
    accepted_events = accepted.get("accepted_events", [])
    candidate_items = candidates.get("candidates", [])
    accepted_rows = "".join(
        "<tr>"
        f"<td><code>{_esc(event.get('event_category_id'))}</code></td>"
        f"<td>{_esc(_domain_label(str(event.get('event_domain'))))}</td>"
        f"<td>{_esc(event.get('title'))}</td>"
        f"<td>{_esc(event.get('core_issue'))}</td>"
        "</tr>"
        for event in accepted_events
        if isinstance(event, dict)
    )
    candidate_rows = "".join(
        "<tr>"
        f"<td><code>{_esc(event.get('event_category_id'))}</code></td>"
        f"<td>{_esc(_domain_label(str(event.get('event_domain'))))}</td>"
        f"<td>{_esc(event.get('decision_after_validation'))}</td>"
        f"<td>{_list(event.get('decision_reasons', []))}</td>"
        "</tr>"
        for event in candidate_items
        if isinstance(event, dict)
    )
    return f"""
    <details class="persona">
      <summary>
        <code>{_esc(persona_id)}</code> · {_esc(_archetype_label(archetype_id))}
        · 接受事件 {_esc(accepted.get("accepted_event_count", "-"))}
        · 候选事件 {_esc(candidates.get("candidate_event_count", "-"))}
      </summary>
      <div class="persona-body">
        <table>
          <tbody>
            <tr><th>来源原型</th><td><code>{_esc(archetype_id)}</code> · {_esc(_archetype_label(archetype_id))}</td></tr>
            <tr><th>年龄/职业</th><td>{_esc(persona.get("age_range"))} · {_esc(persona.get("occupation"))} · {_esc(persona.get("occupation_status"))}</td></tr>
            <tr><th>教育/家庭</th><td>{_esc(persona.get("education_background"))} · {_esc(persona.get("family_structure"))}</td></tr>
            <tr><th>经济/支持</th><td>{_esc(persona.get("economic_condition"))} · {_esc(persona.get("social_support"))}</td></tr>
            <tr><th>主要生活领域</th><td>{_tags(persona.get("primary_life_domains", []), labeler=_domain_label)}</td></tr>
            <tr><th>长期目标</th><td>{_list(persona.get("long_term_goals", []))}</td></tr>
            <tr><th>沟通/压力/决策</th><td>
              {_tags(persona.get("communication_style", []))}
              {_tags(persona.get("stress_response", []))}
              {_tags(persona.get("decision_style", []))}
            </td></tr>
            <tr><th>记忆相关特征</th><td>{_list(persona.get("memory_relevant_traits", []))}</td></tr>
          </tbody>
        </table>
        <h3>接受事件</h3>
        <table>
          <thead><tr><th>ID</th><th>领域</th><th>标题</th><th>核心问题</th></tr></thead>
          <tbody>{accepted_rows}</tbody>
        </table>
        <h3>候选事件决策</h3>
        <table>
          <thead><tr><th>ID</th><th>领域</th><th>决策</th><th>理由</th></tr></thead>
          <tbody>{candidate_rows}</tbody>
        </table>
      </div>
    </details>
    """


def _file_table(input_dir: Path, *, persona_count: Any) -> str:
    rows = []
    for filename, meaning in [
        ("sampled_personas.json", f"{persona_count} 个具体 persona，即 tau 中的 z。"),
        ("candidate_event_sets.json", "每人 8-12 个候选事件。"),
        ("accepted_persona_event_sets.json", "每人 4-6 个接受事件，即 tau 中的 T。"),
        ("compatibility_report.json", "候选事件接受/拒绝理由和 batch 摘要。"),
        ("realism_validation_report.json", "真实性、领域覆盖、自传风险和批量多样性检验。"),
        ("realism_validation_report.recheck.json", "独立校验脚本重新生成的复核报告。"),
    ]:
        rows.append(
            "<tr>"
            f"<td><code>{_esc(_rel(input_dir / filename))}</code></td>"
            f"<td>{_esc(meaning)}</td>"
            "</tr>"
        )
    return f"<table><thead><tr><th>文件</th><th>含义</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _count_table(data: Any, *, labeler) -> str:
    if not isinstance(data, dict) or not data:
        return "<p class='meta'>未提供。</p>"
    rows = []
    for key, count in sorted(data.items(), key=lambda item: (-int(item[1]), str(item[0]))):
        rows.append(
            "<tr>"
            f"<td><code>{_esc(key)}</code></td>"
            f"<td>{_esc(labeler(str(key)))}</td>"
            f"<td>{_esc(count)}</td>"
            "</tr>"
        )
    return f"<table><thead><tr><th>ID</th><th>中文说明</th><th>数量</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _metric(value: str, number: Any, label: str) -> str:
    return (
        "<div class='metric'>"
        f"<strong>{_esc(number)}</strong>"
        f"<span>{_esc(value)} · {_esc(label)}</span>"
        "</div>"
    )


def _list(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "<span class='meta'>未提供</span>"
    return "<ul class='compact'>" + "".join(f"<li>{_esc(item)}</li>" for item in values) + "</ul>"


def _tags(values: Any, *, labeler=None) -> str:
    if not isinstance(values, list) or not values:
        return "<span class='meta'>未提供</span>"
    return "".join(
        f"<span class='tag'>{_esc(labeler(str(item)) if labeler else item)}</span>"
        for item in values
    )


def _archetype_label(archetype_id: str) -> str:
    return ARCHETYPE_CN.get(archetype_id, archetype_id)


def _domain_label(domain: str) -> str:
    return DOMAIN_CN.get(domain, domain)


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
