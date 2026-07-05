#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter, defaultdict
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
    zh_text,
    zh_value,
)

DEFAULT_BASE_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
DEFAULT_OUTPUT = REPO_ROOT / "docs/l_event_line_generation_report.html"
DEFAULT_PERSONA_POOL = REPO_ROOT / "long_memory_experiment/data/sampling/persona_archetype_pool_v0.1.json"
DEFAULT_EVENT_POOL = REPO_ROOT / "long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json"
AAAI_PAPER_PATH = str(REPO_ROOT / "docs/references/aaai2027_remem_re.pdf")
DOCX_PATH = "/Users/tom/Desktop/Archetype_Guided_Persona_Event_Sampling_Implementation.docx"


STAGE_LABELS = {
    "initial": "初始提出",
    "recurrence": "再次出现",
    "turning_point": "转折判断",
    "partial_resolution": "部分处理",
    "reflection": "回看总结",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate focused L/event-line HTML report.")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = args.base_dir
    payload = {
        "persona_pool": _load_json(DEFAULT_PERSONA_POOL),
        "sampled_personas": _load_json(base / "sampled_personas.json"),
        "candidate_event_sets": _load_json(base / "candidate_event_sets.json"),
        "accepted": _load_json(base / "accepted_persona_event_sets.json"),
        "event_pool": _load_json(DEFAULT_EVENT_POOL),
        "event_lines_batch": _load_json(base / "event_lines_batch.json"),
        "timeline": _load_json(base / "timeline.json"),
        "tau_contract": _load_json(base / "tau_contract.json"),
    }
    html_text = render_report(payload=payload, base_dir=base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(*, payload: dict[str, dict[str, Any]], base_dir: Path) -> str:
    persona_pool = payload["persona_pool"]
    sampled_personas = payload["sampled_personas"]
    candidate_event_sets = payload["candidate_event_sets"]
    accepted = payload["accepted"]
    event_pool = payload["event_pool"]
    event_lines_batch = payload["event_lines_batch"]
    timeline = payload["timeline"]
    tau_contract = payload["tau_contract"]
    lines = _event_lines(event_lines_batch)
    stats = _line_runtime_stats(timeline=timeline, tau_contract=tau_contract)
    overview = _overview(lines=lines, event_lines_batch=event_lines_batch, timeline=timeline, tau_contract=tau_contract)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>L Event Line 生成逻辑与明细</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #5b6670;
      --line: #d8e0e7;
      --soft: #f6f8fb;
      --chip: #eef4ff;
      --accent: #1558d6;
      --ok: #1f7a45;
      --warn: #8a4b00;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #fff;
      font: 15px/1.62 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 34px 26px 72px; }}
    h1, h2, h3 {{ margin: 0; line-height: 1.25; }}
    h1 {{ font-size: 30px; }}
    h2 {{ margin-top: 34px; padding-top: 22px; border-top: 1px solid var(--line); font-size: 22px; }}
    h3 {{ margin-top: 18px; font-size: 17px; }}
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
    ol {{ margin: 10px 0 18px; padding-left: 24px; }}
    li {{ margin: 7px 0; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; }}
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
    .ok {{
      margin: 16px 0;
      padding: 13px 15px;
      background: #edf7f0;
      border-left: 4px solid var(--ok);
    }}
    .warn {{
      margin: 16px 0;
      padding: 13px 15px;
      background: #fff7e8;
      border-left: 4px solid var(--warn);
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
    .code-block {{
      margin: 12px 0 18px;
      padding: 12px 14px;
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f7f9fc;
      font: 13px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre-wrap;
    }}
    details.line {{
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    details.line > summary {{
      cursor: pointer;
      padding: 12px 14px;
      font-weight: 700;
      background: var(--soft);
    }}
    .details-body {{ padding: 0 14px 14px; }}
    .small td:first-child {{ width: 22%; }}
    @media (max-width: 920px) {{
      main {{ padding: 24px 14px 52px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>L Event Line 生成逻辑与具体情况</h1>
  <p class="meta">输入目录：<code>{_esc(_rel(base_dir))}</code></p>
  <p class="meta">核心产物：<code>{_esc(_rel(base_dir / "event_lines_batch.json"))}</code>；后续引用：<code>{_esc(_rel(base_dir / "timeline.json"))}</code>、<code>{_esc(_rel(base_dir / "tau_contract.json"))}</code></p>

  {_status_block(event_lines_batch, timeline, tau_contract)}

  <section class="grid">
    {_metric("L lines", overview["line_count"], "事件线数量")}
    {_metric("Personas", overview["persona_count"], "人物数量")}
    {_metric("Stages/line", overview["stage_length_mode"], "每条阶段数")}
    {_metric("Occurrences", overview["occurrence_total"], "timeline 出现")}
    {_metric("Probes", overview["probe_total"], "挂载 probe")}
    {_metric("Domains", overview["domain_count"], "事件领域")}
  </section>

  <h2>1. L 是什么</h2>
  {_definition_section(event_lines_batch)}

  <h2>2. 候选池数量总览</h2>
  {_pool_count_section(persona_pool=persona_pool, sampled_personas=sampled_personas, candidate_event_sets=candidate_event_sets, accepted=accepted, event_pool=event_pool, event_lines_batch=event_lines_batch)}

  <h2>3. L 生成逻辑</h2>
  {_logic_section(sampled_personas=sampled_personas, accepted=accepted, event_pool=event_pool, event_lines_batch=event_lines_batch)}

  <h2>4. 当前 L 的整体统计</h2>
  {_stats_section(lines=lines, stats=stats, event_lines_batch=event_lines_batch)}

  <h2>5. L 字段解释</h2>
  {_field_section()}

  <h2>6. L 到 Timeline / I / P / M 的关系</h2>
  {_downstream_section(timeline=timeline, tau_contract=tau_contract)}

  <h2>7. 具体 L 明细</h2>
  {_line_details(lines=lines, stats=stats)}
</main>
</body>
</html>
"""


def _overview(
    *,
    lines: list[dict[str, Any]],
    event_lines_batch: dict[str, Any],
    timeline: dict[str, Any],
    tau_contract: dict[str, Any],
) -> dict[str, Any]:
    stage_lengths = Counter(len(line.get("stage_sequence", [])) for line in lines)
    runtime_stats = _line_runtime_stats(timeline=timeline, tau_contract=tau_contract)
    return {
        "line_count": len(lines),
        "persona_count": event_lines_batch.get("summary", {}).get("persona_count"),
        "stage_length_mode": stage_lengths.most_common(1)[0][0] if stage_lengths else "-",
        "occurrence_total": sum(item["occurrence_count"] for item in runtime_stats.values()),
        "probe_total": sum(item["probe_count"] for item in runtime_stats.values()),
        "domain_count": len({str(line.get("event_domain")) for line in lines}),
    }


def _definition_section(event_lines_batch: dict[str, Any]) -> str:
    summary = event_lines_batch.get("summary", {})
    rows = [
        ("论文 tau 口径", AAAI_PAPER_PATH, "L = recurring event lines；它把长期主题 T 实例化成跨多天推进的事件线。"),
        ("当前工程输入", "accepted_persona_event_sets.json + event_category_pool_v0.1_60events.json + sampled_personas.json", "每个 persona 的 accepted event ids 决定哪些 T 会生成 L。"),
        ("当前工程输出", "event_lines_batch.json", f"5 人合计 {summary.get('event_line_count')} 条 L；每条 L 当前有 5 个 source stage。"),
        ("关键边界", "P1 只构建事件线合同", "L 本身不安排 day，不决定 probe；day-level timeline、I、P 是后续阶段。"),
    ]
    return f"""
  <div class="callout">
    <code>L</code> 不是一天的事件，也不是用户原话；它是一条“可以跨多天反复出现的持续事件线”。
    后续 <code>timeline</code> 会决定这条线第几次在哪一天出现，<code>I</code> 会把那次出现转成用户问题。
  </div>
  {_table(["层级", "来源", "说明"], rows)}
"""


def _pool_count_section(
    *,
    persona_pool: dict[str, Any],
    sampled_personas: dict[str, Any],
    candidate_event_sets: dict[str, Any],
    accepted: dict[str, Any],
    event_pool: dict[str, Any],
    event_lines_batch: dict[str, Any],
) -> str:
    archetypes = persona_pool.get("archetypes", [])
    event_categories = event_pool.get("event_categories", [])
    personas = sampled_personas.get("personas", [])
    candidate_sets = candidate_event_sets.get("candidate_event_sets", [])
    accepted_sets = accepted.get("accepted_persona_event_sets", [])
    lines = _event_lines(event_lines_batch)
    candidate_total = sum(int(item.get("candidate_event_count", 0) or 0) for item in candidate_sets if isinstance(item, dict))
    accepted_total = sum(int(item.get("accepted_event_count", 0) or 0) for item in accepted_sets if isinstance(item, dict))
    rejected_total = sum(
        sum(
            1
            for event in item.get("candidates", [])
            if isinstance(event, dict) and event.get("decision_after_validation") == "reject"
        )
        for item in candidate_sets
        if isinstance(item, dict)
    )
    pool_rows = [
        (
            "persona_archetype_pool",
            _rel(DEFAULT_PERSONA_POOL),
            len(archetypes) if isinstance(archetypes, list) else 0,
            "原始人物原型池。P0 从这里采样出当前 demo 的 persona。",
        ),
        (
            "event_category_pool",
            _rel(DEFAULT_EVENT_POOL),
            len(event_categories) if isinstance(event_categories, list) else 0,
            "原始事件类别池。文件名写 60events，但当前 JSON 实际包含 73 个 event_categories。",
        ),
        (
            "sampled_personas",
            "sampled_personas.json",
            len(personas) if isinstance(personas, list) else 0,
            "当前 demo 实际采样人物数。",
        ),
        (
            "candidate_event_sets",
            "candidate_event_sets.json",
            candidate_total,
            "当前 5 人合计候选事件数；每个候选都已经通过兼容性初筛或带有拒绝原因。",
        ),
        (
            "accepted_persona_event_sets",
            "accepted_persona_event_sets.json",
            accepted_total,
            "最终进入 L 生成的 accepted events 数。",
        ),
        (
            "event_lines_batch",
            "event_lines_batch.json",
            len(lines),
            "P1 生成的 L 数；当前等于 accepted events 数，一条 accepted event 生成一条 L。",
        ),
        (
            "rejected candidates",
            "candidate_event_sets.json",
            rejected_total,
            "候选池中未进入 accepted set 的事件，主要因为 8-10 条事件预算和领域覆盖优先级。",
        ),
    ]
    persona_rows = []
    accepted_by_persona = {
        str(item.get("persona_id")): item
        for item in accepted_sets
        if isinstance(item, dict)
    }
    lines_by_persona = Counter(str(line.get("persona_id")) for line in lines)
    for item in candidate_sets:
        if not isinstance(item, dict):
            continue
        persona_id = str(item.get("persona_id"))
        candidates = [event for event in item.get("candidates", []) if isinstance(event, dict)]
        accepted_item = accepted_by_persona.get(persona_id, {})
        accept_count = int(accepted_item.get("accepted_event_count", 0) or 0)
        reject_count = sum(1 for event in candidates if event.get("decision_after_validation") == "reject")
        domain_count = len(
            {
                str(event.get("event_domain"))
                for event in accepted_item.get("accepted_events", [])
                if isinstance(event, dict) and event.get("event_domain")
            }
        )
        persona_rows.append(
            (
                persona_id,
                item.get("source_archetype"),
                int(item.get("candidate_event_count", len(candidates)) or 0),
                accept_count,
                reject_count,
                domain_count,
                lines_by_persona.get(persona_id, 0),
                ", ".join(str(event_id) for event_id in accepted_item.get("accepted_event_ids", [])),
            )
        )
    event_domain_rows = [
        (event_domain_zh(domain), count)
        for domain, count in Counter(
            str(event.get("event_domain"))
            for event in event_categories
            if isinstance(event, dict) and event.get("event_domain")
        ).most_common()
    ]
    accepted_domain_rows = [
        (event_domain_zh(domain), count)
        for domain, count in Counter(
            str(event.get("event_domain"))
            for item in accepted_sets
            if isinstance(item, dict)
            for event in item.get("accepted_events", [])
            if isinstance(event, dict) and event.get("event_domain")
        ).most_common()
    ]
    return f"""
  <div class="callout">
    当前 L 不是从 73 个事件类别池里全量生成，而是先经过 P0 人物采样和 persona-event 兼容性筛选。
    对每个 persona，<code>candidate_event_sets</code> 是候选池，<code>accepted_persona_event_sets</code>
    是最终进入 L 的池子；当前 <strong>{candidate_total}</strong> 个候选里接受 <strong>{accepted_total}</strong> 个，
    因此生成 <strong>{len(lines)}</strong> 条 L。
  </div>
  <h3>2.1 总池子数量</h3>
  {_table(["池子", "文件", "数量", "说明"], pool_rows)}
  <h3>2.2 每个人物的候选/接受/拒绝数量</h3>
  {_table(["Persona", "Archetype", "Candidates", "Accepted", "Rejected", "Accepted domains", "L lines", "Accepted event ids"], persona_rows)}
  <h3>2.3 原始 event_category_pool 领域分布</h3>
  {_table(["event_domain", "count in event pool"], event_domain_rows)}
  <h3>2.4 当前 accepted events 领域分布</h3>
  {_table(["event_domain", "accepted count"], accepted_domain_rows)}
"""


def _logic_section(
    *,
    sampled_personas: dict[str, Any],
    accepted: dict[str, Any],
    event_pool: dict[str, Any],
    event_lines_batch: dict[str, Any],
) -> str:
    step_rows = [
        (
            "1. 批处理入口",
            "scripts/run_p1_event_line_batch_construction.py",
            "读取 sampled_personas.json、accepted_persona_event_sets.json、event_category_pool_v0.1_60events.json。",
            "lines 35-48",
        ),
        (
            "2. 找到 persona 和 accepted events",
            "construct_event_lines_for_persona(...)",
            "按 persona_id 找到 P0 人物，再读取该人物 accepted_event_ids。",
            "event_line_constructor.py:321-345",
        ),
        (
            "3. 对每个 accepted event 生成一条 L",
            "_construct_event_line(...)",
            "event_category_id + persona_id 决定唯一 event_line_id；一条 accepted event 对应一条 L。",
            "event_line_constructor.py:426-479",
        ),
        (
            "4. 读取 stage_patterns",
            "_stage_labels(...)",
            "优先使用 event_category_pool 中的 stage_patterns；否则 fallback 到 initial/recurrence/turning point/partial resolution/reflection。",
            "event_line_constructor.py:570-577",
        ),
        (
            "5. 构造每个 stage",
            "_construct_stage(...)",
            "为每个 stage 写入 stage_goal、allowed_new_facts、user_state_hint、user_message_seed、assistant_memory_expectation、prohibited_facts。",
            "event_line_constructor.py:482-526",
        ),
        (
            "6. 约束可用事实",
            "_allowed_facts(...)",
            "只保留 persona 字段和 event category 字段，防止把旧剧本或未提供事实带入 L。",
            "event_line_constructor.py:529-550",
        ),
        (
            "7. 写关系记忆目标",
            "_relational_memory_targets(...)",
            "每条 L 固定写 response_preference、event_continuity、boundary 三类目标。",
            "event_line_constructor.py:553-567",
        ),
        (
            "8. 批量汇总",
            "construct_event_lines_for_batch(...)",
            "遍历全部 5 个 persona，输出 personas[] 和 flattened event_lines[]。",
            "event_line_constructor.py:371-423",
        ),
    ]
    pseudo = """for persona in sampled_personas:
  accepted_event_ids = accepted_persona_event_sets[persona_id].accepted_event_ids
  for event_id in accepted_event_ids:
    event = event_category_pool[event_id]
    L = {
      event_line_id = sha1(persona_id:event_id),
      persona_ref + event_category_ref,
      persistent_event_summary,
      relational_memory_targets,
      stage_sequence[1..5]
    }"""
    boundary_rows = [
        ("确定性", "当前 L 生成不调用 LLM；同样输入会得到同样 event_line_id 和 stage_sequence。"),
        ("事实来源", "只来自 sampled persona、accepted event set、event category pool，以及代码中的中文映射表。"),
        ("不做的事", "P1 L 不排日历、不插 probe、不生成完整自然对话、不写 assistant 答案。"),
        ("后续作用", "Timeline 用 L.stage_sequence 排阶段；I 用 L 的 occurrence 转用户问题；M2/M3 用 L 摘要和目标构造记忆。"),
    ]
    input_rows = [
        (
            "sampled_personas.json",
            sampled_personas.get("schema_version"),
            "personas[]",
            "提供 persona_id、source_archetype、occupation、family_structure、经济/支持/目标/沟通风格等稳定人物字段。",
            "L 中的 persona_id、source_archetype、allowed_facts.persona_facts、user_message_seed 的职业表述。",
        ),
        (
            "accepted_persona_event_sets.json",
            accepted.get("schema_version"),
            "accepted_persona_event_sets[].accepted_event_ids",
            "提供每个 persona 最终通过兼容性筛选的事件类别 ID 列表。",
            "决定每个人生成几条 L；一条 accepted_event_id 生成一条 L。",
        ),
        (
            "event_category_pool_v0.1_60events.json",
            event_pool.get("schema_version"),
            "event_categories[]",
            "提供 event_category_id、event_domain、event_type、title、core_issue、stage_patterns、uncertainties、emotional_load、actions、memory_risks。",
            "决定 L 的事件主题、stage_sequence 原型、allowed_new_facts、state hint、message seed 和 source_event_category。",
        ),
        (
            "event_line_constructor.py 映射表",
            "代码常量",
            "EVENT_CN / DOMAIN_CN / STAGE_CN / TERM_CN / OCCUPATION_CN",
            "补中文标题、中文术语、阶段中文目标、职业中文化；没有映射时回退到原始英文字段。",
            "提高可读性，但也意味着当前 L 有一部分中文化逻辑来自代码，不是 JSON 原文。",
        ),
    ]
    match_rows = [
        (
            "遍历 persona",
            "construct_event_lines_for_batch(...) 读取 sampled_personas.personas[]，只保留有 persona_id 的对象。",
            "event_line_constructor.py:378-386",
        ),
        (
            "找人物",
            "_find_by_id(sampled_personas.personas, 'persona_id', cfg.persona_id)。找不到直接 raise ValueError。",
            "event_line_constructor.py:329, 662-668",
        ),
        (
            "找 accepted set",
            "_find_by_id(accepted_persona_event_sets, 'persona_id', cfg.persona_id)。找不到直接 raise ValueError。",
            "event_line_constructor.py:330-334, 662-668",
        ),
        (
            "建 event 索引",
            "events_by_id = {event_category_id: event for event in event_pool.event_categories}。",
            "event_line_constructor.py:335-339",
        ),
        (
            "逐个 accepted_event_id 生成 L",
            "for event_id in accepted.accepted_event_ids: event = events_by_id[event_id]；找不到 event 直接报错。",
            "event_line_constructor.py:340-345",
        ),
        (
            "L 数量关系",
            "len(event_lines for persona) == accepted_event_count；batch 的 event_line_count 是全部 persona 的总和。",
            "event_line_constructor.py:366-367, 413-420",
        ),
    ]
    output_field_rows = [
        (
            "event_line_id",
            "persona_id + event_category_id",
            "sha1(f'{persona_id}:{event_id}') 前 8 位，格式 L_{persona_id_lower}_{event_id_lower}_{digest}",
            "_event_line_id(...)；保证同一 persona/event 对稳定唯一。",
        ),
        (
            "persona_id",
            "sampled_personas.personas[].persona_id",
            "直接复制",
            "用于后续 timeline、I、P、M payload 坐标。",
        ),
        (
            "source_archetype",
            "sampled_personas.personas[].source_archetype",
            "直接复制",
            "保留人物原型来源。",
        ),
        (
            "event_category_id",
            "accepted_event_ids 中的 event_id / event_pool.event_category_id",
            "直接复制",
            "T/L 的事件类别锚点。",
        ),
        (
            "event_domain / event_type",
            "event_pool.event_domain / event_pool.event_type",
            "直接复制",
            "用于领域统计和兼容性审计。",
        ),
        (
            "event_domain_zh",
            "DOMAIN_CN[event_domain]",
            "有映射用中文；否则回退 event_domain 原文",
            "当前是代码映射。",
        ),
        (
            "event_title.zh",
            "EVENT_CN[event_id].title 或 event_pool.title",
            "优先代码中文映射；否则使用 event_pool 原始 title",
            "这是为什么部分 title 是中文，部分仍是英文。",
        ),
        (
            "event_title.source",
            "event_pool.title",
            "直接复制",
            "保留原始事件池标题。",
        ),
        (
            "persistent_event_summary",
            "EVENT_CN[event_id].summary 或 event_pool.core_issue",
            "优先中文增强摘要；否则用 core_issue",
            "后续 M2 / I scene_boundary 的重要来源。",
        ),
        (
            "participants",
            "EVENT_CN[event_id].participants",
            "有映射则使用；否则默认 ['自己']",
            "当前不是 event_pool 原生字段。",
        ),
        (
            "allowed_facts.persona_facts",
            "sampled_personas 人物字段",
            "选取 age_range、occupation、status、family_structure、economic_condition、social_support、life_domains、goals、communication_style",
            "严格限制 L 可以引用的人物事实。",
        ),
        (
            "allowed_facts.event_category_facts",
            "event_pool 事件字段",
            "选取 event_category_id、event_domain、event_type、core_issue、possible_uncertainties、possible_actions",
            "严格限制 L 可以引用的事件事实。",
        ),
        (
            "latent_concerns",
            "EVENT_CN[event_id].latent_concerns 或 event_pool.possible_emotional_load",
            "优先中文增强隐忧；否则使用情绪负载列表",
            "后续 I.scene_boundary latent concerns 的来源之一。",
        ),
        (
            "relational_memory_targets",
            "代码固定模板",
            "每条 L 固定三项：response_preference、event_continuity、boundary",
            "当前没有按 persona/event 个性化生成。",
        ),
        (
            "stage_sequence",
            "event_pool.stage_patterns + stage 构造函数",
            "取第一组 stage_patterns，并截断到 stages_per_event_line=5；每个 stage 再展开字段",
            "L 的核心轨迹结构。",
        ),
        (
            "source_event_category",
            "event_pool 原始字段",
            "保留 core_issue、possible_uncertainties、possible_emotional_load、possible_actions、memory_risks",
            "用于审计 L 从哪里来。",
        ),
    ]
    stage_field_rows = [
        (
            "source_stage_label",
            "event_pool.stage_patterns[0][index]",
            "例如 initial concern / recurrence / turning point / partial resolution / reflection。",
        ),
        (
            "event_stage",
            "STAGE_CN[source_stage_label][0]",
            "归一化为 initial、recurrence、turning_point、partial_resolution、reflection；未知 label 则把空格换成下划线。",
        ),
        (
            "stage_goal",
            "STAGE_CN[source_stage_label][1]",
            "归一化阶段目标；未知 label 用“沿着事件线推进一次”。",
        ),
        (
            "allowed_new_facts",
            "event_summary + possible_uncertainties[:2] + possible_actions[:2]",
            "event_summary 优先 EVENT_CN.summary，否则 core_issue；uncertainties/actions 会经过 TERM_CN 中文化，缺映射则保留原文。",
        ),
        (
            "user_state_hint",
            "event_stage + possible_emotional_load[:2]",
            "initial/recurrence 会写入情绪负载；turning_point/partial_resolution/reflection 使用固定阶段描述。",
        ),
        (
            "user_message_seed",
            "event_stage 模板 + event_title_zh + persona.occupation + 第一个 uncertainty/action",
            "这是 L 中的用户句子种子；后续 timeline occurrence.surface_event 会基于它进入 I.scripted_opening。",
        ),
        (
            "assistant_memory_expectation",
            "event_stage 固定映射",
            "initial 拆事实；recurrence 承接同一事件线；turning_point 识别变化；partial_resolution 核对剩余风险；reflection 提炼模式。",
        ),
        (
            "prohibited_facts",
            "代码固定三条",
            "禁止真实姓名/精确地址/精确收入/医学诊断；禁止迁移旧单人剧本事实；禁止引入 persona/event category 外重大事件。",
        ),
    ]
    example_html = _trace_example(
        sampled_personas=sampled_personas,
        accepted=accepted,
        event_pool=event_pool,
        event_lines_batch=event_lines_batch,
    )
    return f"""
  <h3>2.1 三个输入分别提供什么</h3>
  {_table(["输入", "schema", "关键字段", "提供什么", "进入 L 的位置"], input_rows)}
  <h3>2.2 匹配与生成顺序</h3>
  {_table(["环节", "具体逻辑", "代码位置"], match_rows)}
  <h3>2.3 执行步骤</h3>
  {_table(["步骤", "函数/文件", "做什么", "位置"], step_rows)}
  <div class="code-block">{_esc(pseudo)}</div>
  <h3>2.4 输出 L 字段逐项来源</h3>
  {_table(["L 输出字段", "输入来源", "转换逻辑", "说明"], output_field_rows)}
  <h3>2.5 stage_sequence 内部字段逐项来源</h3>
  {_table(["stage 字段", "输入来源", "转换逻辑"], stage_field_rows)}
  <h3>2.6 一个真实 L 的字段追踪例子</h3>
  {example_html}
  <h3>2.7 生成边界</h3>
  {_table(["边界", "说明"], boundary_rows)}
"""


def _stats_section(
    *,
    lines: list[dict[str, Any]],
    stats: dict[str, dict[str, Any]],
    event_lines_batch: dict[str, Any],
) -> str:
    by_persona = Counter(str(line.get("persona_id")) for line in lines)
    by_domain = Counter(str(line.get("event_domain")) for line in lines)
    stage_lengths = Counter(len(line.get("stage_sequence", [])) for line in lines)
    target_types = Counter(
        str(target.get("target_type"))
        for line in lines
        for target in line.get("relational_memory_targets", [])
        if isinstance(target, dict)
    )
    stage_types = Counter(
        str(stage.get("event_stage"))
        for line in lines
        for stage in line.get("stage_sequence", [])
        if isinstance(stage, dict)
    )
    occurrence_counts = Counter(item["occurrence_count"] for item in stats.values())
    probe_counts = Counter(item["probe_count"] for item in stats.values())
    rows = [
        ("event_lines_per_persona", _counter_text(by_persona), "每个人物的长期事件线数量。"),
        ("event_domain_counts", _counter_text(by_domain), "当前 L 覆盖的事件领域。"),
        ("stage_length_counts", _counter_text(stage_lengths), "每条 L 的 source stage 数量。"),
        ("stage_type_counts", _counter_text(stage_types), "所有 L 的 source stage 类型。"),
        ("relational_memory_target_types", _counter_text(target_types), "每条 L 固定写 3 类关系记忆目标。"),
        ("timeline_occurrence_counts_per_L", _counter_text(occurrence_counts), "每条 L 后续在 timeline 中出现次数的分布。"),
        ("probe_counts_per_L", _counter_text(probe_counts), "每条 L 后续被 probe 评测的次数分布。"),
    ]
    config_rows = [
        ("schema_version", event_lines_batch.get("schema_version"), "当前 L 批处理 schema。"),
        ("sampling_stage", event_lines_batch.get("sampling_stage"), "阶段名称。"),
        ("stages_per_event_line", event_lines_batch.get("construction_config", {}).get("stages_per_event_line"), "构造阶段数配置。"),
        ("persona_count", event_lines_batch.get("summary", {}).get("persona_count"), "人物数量。"),
        ("event_line_count", event_lines_batch.get("summary", {}).get("event_line_count"), "L 总数。"),
    ]
    return f"""
  {_table(["配置字段", "当前值", "说明"], config_rows, class_name="small")}
  {_table(["统计项", "当前值", "解释"], rows)}
"""


def _trace_example(
    *,
    sampled_personas: dict[str, Any],
    accepted: dict[str, Any],
    event_pool: dict[str, Any],
    event_lines_batch: dict[str, Any],
) -> str:
    lines = _event_lines(event_lines_batch)
    if not lines:
        return '<div class="warn">没有可展示的 L 示例。</div>'
    line = lines[0]
    persona_id = str(line.get("persona_id"))
    event_id = str(line.get("event_category_id"))
    persona = _find_first(sampled_personas.get("personas", []), "persona_id", persona_id)
    accepted_set = _find_first(accepted.get("accepted_persona_event_sets", []), "persona_id", persona_id)
    event = _find_first(event_pool.get("event_categories", []), "event_category_id", event_id)
    stage = next(
        (item for item in line.get("stage_sequence", []) if isinstance(item, dict)),
        {},
    )
    trace_rows = [
        (
            "选中 persona",
            f"{persona_id} / {persona.get('source_archetype')}",
            "来自 sampled_personas.personas[]。",
        ),
        (
            "accepted_event_ids",
            ", ".join(str(item) for item in accepted_set.get("accepted_event_ids", [])),
            "这一串 ID 决定该 persona 会生成哪些 L。",
        ),
        (
            "当前 event_id",
            event_id,
            "事件 ID 在 accepted_event_ids 中；constructor 用它去 event_pool 查完整 event。",
        ),
        (
            "event_pool.title/core_issue",
            f"{event_category_title_zh(event)} / {event_category_summary_zh(event)}",
            "进入 event_title.source 和 persistent_event_summary fallback。",
        ),
        (
            "event_pool.stage_patterns",
            _short_json(_stage_patterns_zh(event.get("stage_patterns"))),
            "进入 stage_sequence 的 source_stage_label。",
        ),
        (
            "生成 event_line_id",
            line.get("event_line_id"),
            "sha1(persona_id:event_id) 稳定生成。",
        ),
        (
            "生成 event_title",
            _short_json(zh_value(line.get("event_title"))),
            "zh 优先来自 EVENT_CN；source 保留 event_pool.title。",
        ),
        (
            "生成 allowed_facts.persona_facts",
            _short_json(zh_value(line.get("allowed_facts", {}).get("persona_facts", {}))),
            "从 sampled_personas 选取允许引用的人物事实。",
        ),
        (
            "生成 allowed_facts.event_category_facts",
            _short_json(zh_value(line.get("allowed_facts", {}).get("event_category_facts", {}))),
            "从 event_pool 选取允许引用的事件事实。",
        ),
        (
            "第 1 个 stage",
            _short_json(zh_value(stage)),
            "展示 source_stage_label 如何被展开成 stage_goal、allowed_new_facts、message_seed 等。",
        ),
    ]
    return _table(["追踪点", "当前值", "说明"], trace_rows)


def _field_section() -> str:
    rows = [
        ("event_line_id", "L 的主键，由 persona_id + event_category_id 经过 sha1 短摘要构成。", "_event_line_id(...)"),
        ("persona_id / source_archetype", "绑定人物和原型来源。", "sampled_personas.json"),
        ("event_category_id / event_domain / event_type", "绑定事件池中的事件类别。", "event_category_pool_v0.1_60events.json"),
        ("event_title", "中文 title 优先来自代码映射 EVENT_CN，否则用 event pool 原始 title。", "_construct_event_line(...)"),
        ("persistent_event_summary", "该事件线长期摘要；用于 M2 和 I scene boundary。", "EVENT_CN.summary 或 event.core_issue"),
        ("participants", "参与者边界；多数为自己，部分事件有明确对象。", "EVENT_CN.participants fallback"),
        ("allowed_facts", "允许使用的人物事实和事件类别事实。", "_allowed_facts(...)"),
        ("latent_concerns", "隐含担心；优先 EVENT_CN，否则 possible_emotional_load。", "_construct_event_line(...)"),
        ("relational_memory_targets", "关系记忆目标：回应偏好、事件连续性、边界。", "_relational_memory_targets(...)"),
        ("stage_sequence", "5 个 source stage；后续 timeline 按 occurrence_index 推进。", "_construct_stage(...)"),
        ("source_event_category", "保留原始 event pool 字段，便于审计。", "_construct_event_line(...)"),
        ("construction_notes", "说明该 L 来自 P0 accepted event category，不来自旧单人剧本。", "_construct_event_line(...)"),
    ]
    return _table(["字段", "含义", "来源/生成函数"], rows)


def _downstream_section(*, timeline: dict[str, Any], tau_contract: dict[str, Any]) -> str:
    timeline_summary = timeline.get("summary", {})
    tau_summary = tau_contract.get("summary", {})
    rows = [
        ("L -> Timeline", f"{tau_summary.get('event_line_count')} 条 L 被排成 {timeline_summary.get('event_occurrence_total')} 个 occurrence。", "timeline_constructor.py 负责日历排布，不是 P1 L 阶段决定。"),
        ("L -> I", f"每个 occurrence 后续生成一个 I；当前 I={tau_summary.get('interaction_unit_count')}。", "I 中保留 event_line_id、event_stage、stage_goal、allowed_facts。"),
        ("L -> P", f"部分 I 后面插入 P；当前 P={tau_summary.get('targeted_probe_count')}。", "probe 的 target_detail_ids 会包含 event_line_id:stage_N / occurrence_N。"),
        ("L -> M2", "M2 使用 persistent_event_summary 和 observed_stage_sequence。", "让 agent 能知道这条线之前怎么发展。"),
        ("L -> M3", "M3 使用 I.scene_boundary.allowed_facts、latent_concerns 和 probe target detail。", "让 agent 可自然使用必要细节，但不补事实。"),
        ("L -> tau", "tau_contract.L 是 source L + observed_stage_sequence 的合并视图。", "P4 阶段把 event_lines_batch、timeline、I、P 聚合。"),
    ]
    return _table(["下游", "当前情况", "作用"], rows)


def _line_details(lines: list[dict[str, Any]], stats: dict[str, dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in lines:
        grouped[str(line.get("persona_id"))].append(line)
    sections = []
    for persona_id in sorted(grouped):
        sections.append(f"<h3>{_esc(persona_id)}</h3>")
        for line in sorted(grouped[persona_id], key=lambda item: str(item.get("event_line_id"))):
            sections.append(_line_detail(line=line, stats=stats.get(str(line.get("event_line_id")), {})))
    return "\n".join(sections)


def _line_detail(*, line: dict[str, Any], stats: dict[str, Any]) -> str:
    stages = [
        (
            stage.get("stage_index"),
            STAGE_LABELS.get(str(stage.get("event_stage")), stage.get("event_stage")),
            zh_text(stage.get("stage_goal")),
            "<br>".join(_esc(zh_text(item)) for item in stage.get("allowed_new_facts", [])),
            zh_text(stage.get("user_state_hint")),
            zh_text(stage.get("user_message_seed")),
            zh_text(stage.get("assistant_memory_expectation")),
        )
        for stage in line.get("stage_sequence", [])
        if isinstance(stage, dict)
    ]
    targets = [
        (target.get("target_type"), target.get("target"))
        for target in line.get("relational_memory_targets", [])
        if isinstance(target, dict)
    ]
    facts = line.get("allowed_facts", {})
    persona_facts = facts.get("persona_facts", {}) if isinstance(facts, dict) else {}
    event_facts = facts.get("event_category_facts", {}) if isinstance(facts, dict) else {}
    runtime_rows = [
        ("timeline occurrence count", stats.get("occurrence_count", 0)),
        ("days", ", ".join(f"D{int(day):02d}" for day in stats.get("days", [])) or "-"),
        ("observed stages", _counter_text(Counter(stats.get("observed_stages", [])))),
        ("probe count", stats.get("probe_count", 0)),
        ("probe ids", ", ".join(str(item) for item in stats.get("probe_ids", [])) or "-"),
    ]
    field_rows = [
        ("event_line_id", f"<code>{_esc(str(line.get('event_line_id')))}</code>"),
        ("event title", _esc(_title(line))),
        ("event domain", _esc(event_domain_zh(line.get("event_domain")))),
        ("summary", _esc(zh_text(line.get("persistent_event_summary")))),
        ("latent concerns", _esc('；'.join(zh_text(item) for item in line.get("latent_concerns", [])))),
        ("persona facts", _esc(_fact_summary(persona_facts))),
        ("event facts", _esc(_fact_summary(event_facts))),
    ]
    return f"""
<details class="line">
  <summary>{_esc(_title(line))} · <code>{_esc(str(line.get("event_line_id")))}</code> · occurrences={_esc(str(stats.get("occurrence_count", 0)))} · probes={_esc(str(stats.get("probe_count", 0)))}</summary>
  <div class="details-body">
    <h3>基础字段</h3>
    {_table(["字段", "值"], field_rows, class_name="small", escape_cells=False)}
    <h3>关系记忆目标</h3>
    {_table(["target_type", "target"], targets)}
    <h3>后续运行中的实际情况</h3>
    {_table(["项", "值"], runtime_rows, class_name="small")}
    <h3>source stage_sequence</h3>
    {_table(["index", "stage", "stage_goal", "allowed_new_facts", "user_state_hint", "user_message_seed", "assistant_memory_expectation"], stages, escape_cells=False)}
  </div>
</details>
"""


def _line_runtime_stats(*, timeline: dict[str, Any], tau_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "occurrence_count": 0,
            "days": [],
            "observed_stages": [],
            "probe_count": 0,
            "probe_ids": [],
        }
    )
    for persona_timeline in timeline.get("timelines", []):
        if not isinstance(persona_timeline, dict):
            continue
        for day in persona_timeline.get("days", []):
            if not isinstance(day, dict):
                continue
            occurrences = day.get("event_occurrences", [])
            if not isinstance(occurrences, list):
                continue
            for occurrence in occurrences:
                if not isinstance(occurrence, dict):
                    continue
                line_id = str(occurrence.get("event_line_id") or "")
                if not line_id:
                    continue
                item = stats[line_id]
                item["occurrence_count"] += 1
                item["days"].append(int(day.get("day", occurrence.get("day", 0)) or 0))
                item["observed_stages"].append(str(occurrence.get("event_stage") or ""))
                for probe_id in occurrence.get("probe_ids", []) or []:
                    item["probe_ids"].append(str(probe_id))
    for probe in tau_contract.get("P", []):
        if not isinstance(probe, dict):
            continue
        line_id = str(probe.get("event_line_id") or "")
        if not line_id:
            continue
        item = stats[line_id]
        item["probe_count"] += 1
        probe_id = str(probe.get("probe_id") or probe.get("message_id") or "")
        if probe_id and probe_id not in item["probe_ids"]:
            item["probe_ids"].append(probe_id)
    for item in stats.values():
        item["days"] = sorted(set(item["days"]))
        item["probe_ids"] = sorted(set(item["probe_ids"]))
    return stats


def _status_block(
    event_lines_batch: dict[str, Any],
    timeline: dict[str, Any],
    tau_contract: dict[str, Any],
) -> str:
    rows = [
        ("event_lines_batch schema", event_lines_batch.get("schema_version", "unknown"), "无 validation 字段；以 summary 和下游校验交叉检查。"),
        ("timeline validation", timeline.get("validation", {}).get("status", "unknown"), "; ".join(str(item) for item in timeline.get("validation", {}).get("issues", [])) or "无"),
        ("tau validation", tau_contract.get("validation", {}).get("status", "unknown"), "; ".join(str(item) for item in tau_contract.get("validation", {}).get("issues", [])) or "无"),
    ]
    ok = all(str(row[1]) in {"event_lines_batch_v0.1", "pass"} for row in rows)
    return f"""
  <div class="{'ok' if ok else 'warn'}"><strong>当前状态：{'pass' if ok else 'check'}。</strong> L 已进入 timeline 和 tau，并通过下游 validation 交叉校验。</div>
  {_table(["层级", "状态", "问题/说明"], rows, class_name="small")}
"""


def _metric(label: str, value: Any, caption: str) -> str:
    return f'<div class="metric"><strong>{_esc(str(value))}</strong><span>{_esc(label)} / {_esc(caption)}</span></div>'


def _event_lines(event_lines_batch: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        line
        for line in event_lines_batch.get("event_lines", [])
        if isinstance(line, dict) and line.get("event_line_id")
    ]


def _table(
    headers: list[str],
    rows: list[tuple[Any, ...]],
    *,
    class_name: str = "",
    escape_cells: bool = True,
) -> str:
    cls = f' class="{class_name}"' if class_name else ""
    header_html = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    row_html = []
    for row in rows:
        cells = []
        for cell in row:
            text = "" if cell is None else str(cell)
            cells.append(f"<td>{_esc(text) if escape_cells else text}</td>")
        row_html.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table{cls}><tr>{header_html}</tr>{''.join(row_html)}</table>"


def _counter_text(counter: Counter[Any]) -> str:
    if not counter:
        return "-"
    return ", ".join(
        f"{_counter_key_zh(key)}:{count}"
        for key, count in sorted(counter.items(), key=lambda item: str(item[0]))
    )


def _counter_key_zh(key: Any) -> str:
    text = str(key)
    if text.isdigit() or text.startswith("P000") or text.startswith("L_") or text.startswith("E_"):
        return text
    if text in STAGE_LABELS:
        return STAGE_LABELS[text]
    target_types = {
        "response_preference": "回应偏好",
        "event_continuity": "事件连续性",
        "boundary": "事实边界",
    }
    if text in target_types:
        return target_types[text]
    return event_domain_zh(text)


def _fact_summary(value: dict[str, Any]) -> str:
    parts = []
    for key, item in value.items():
        if isinstance(item, list):
            item_text = ", ".join(zh_text(part) for part in item[:4])
        else:
            item_text = zh_text(item)
        if item_text:
            parts.append(f"{key}={item_text}")
    return "；".join(parts)


def _find_first(items: Any, key: str, value: str) -> dict[str, Any]:
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and str(item.get(key)) == value:
            return item
    return {}


def _short_json(value: Any) -> str:
    text = json.dumps(zh_value(value), ensure_ascii=False, indent=2)
    if len(text) > 1200:
        return text[:1200] + "\n..."
    return text


def _title(line: dict[str, Any]) -> str:
    event_id = str(line.get("event_category_id") or "")
    if event_id:
        mapped = event_category_title_zh({"event_category_id": event_id})
        if mapped != "待中文化描述":
            return mapped
    title = line.get("event_title", {})
    if isinstance(title, dict):
        return zh_text(title.get("zh") or title.get("source") or "")
    return zh_text(title or "")


def _stage_patterns_zh(value: Any) -> Any:
    label_map = {
        "initial concern": "初始担心",
        "recurrence": "再次出现",
        "turning point": "转折判断",
        "partial resolution": "部分处理",
        "reflection": "回看总结",
    }
    if isinstance(value, list):
        return [_stage_patterns_zh(item) for item in value]
    if isinstance(value, str):
        return label_map.get(value, zh_text(value))
    return value


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
