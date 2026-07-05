#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"
EVENT_LINES_PATH = DATA_DIR / "event_lines_batch.json"
TAU_CONTRACT_PATH = DATA_DIR / "tau_contract.json"
PROBE_PLAN_PATH = DATA_DIR / "probe_plan.json"
EVENT_POOL_PATH = REPO_ROOT / "long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json"
OUTPUT_PATH = REPO_ROOT / "docs/l_evaluation_discriminability_audit.html"
AAAI_PAPER_PATH = str(REPO_ROOT / "docs/references/aaai2027_remem_re.pdf")


CONTINUITY_TERMS = ("前面", "之前", "从头", "这条线", "已经聊过", "不想从头")
STATE_TERMS = ("状态", "变化", "相比", "校准")
DETAIL_TERMS = ("具体细节", "泛泛", "前面已经出现过")
STAGE_HINT_TERMS = ("新变化", "已经处理", "回头看", "又出现", "最近卡在", "反复")


def main() -> int:
    event_lines_doc = _load_json(EVENT_LINES_PATH)
    tau_contract = _load_json(TAU_CONTRACT_PATH)
    probe_plan = _load_json(PROBE_PLAN_PATH)
    event_pool_doc = _load_json(EVENT_POOL_PATH)

    report = build_report(
        event_lines_doc=event_lines_doc,
        tau_contract=tau_contract,
        probe_plan=probe_plan,
        event_pool_doc=event_pool_doc,
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    return 0


def build_report(
    *,
    event_lines_doc: dict[str, Any],
    tau_contract: dict[str, Any],
    probe_plan: dict[str, Any],
    event_pool_doc: dict[str, Any],
) -> str:
    lines = _all_event_lines(event_lines_doc)
    interactions = [item for item in tau_contract.get("I", []) if isinstance(item, dict)]
    probes = [
        item
        for item in probe_plan.get("probe_questions", tau_contract.get("P", []))
        if isinstance(item, dict)
    ]
    line_stats = _line_stats(lines)
    interaction_stats = _interaction_stats(interactions)
    probe_stats = _probe_stats(probes)
    target_stats = _target_stats(lines)
    e_relationship = _e_allowed_fact_relationship(
        lines=lines,
        event_pool_doc=event_pool_doc,
    )
    issue_rows = _issue_rows(
        line_stats=line_stats,
        interaction_stats=interaction_stats,
        probe_stats=probe_stats,
        target_stats=target_stats,
    )
    risk_level = _overall_risk(issue_rows)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>L 评测可分辨性审计</title>
  <style>
    :root {{
      --ink: #18212f;
      --muted: #667085;
      --line: #d8e0ea;
      --soft: #f6f8fb;
      --panel: #ffffff;
      --accent: #176b5f;
      --warn: #9a4d00;
      --warn-bg: #fff6e7;
      --bad: #a83232;
      --bad-bg: #fff0f0;
      --ok: #2c7a4b;
      --ok-bg: #edf8f1;
      --chip: #eef6f5;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #fff;
      font: 15px/1.68 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 34px 24px 72px; }}
    h1, h2, h3 {{ margin: 0; line-height: 1.28; }}
    h1 {{ font-size: 30px; }}
    h2 {{ margin-top: 34px; padding-top: 22px; border-top: 1px solid var(--line); font-size: 22px; }}
    h3 {{ margin-top: 20px; font-size: 17px; }}
    p {{ margin: 8px 0; }}
    code {{
      padding: 1px 5px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #f2f5f8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin: 14px 0 20px; }}
    th, td {{ border: 1px solid var(--line); padding: 8px 9px; vertical-align: top; word-break: break-word; }}
    th {{ background: var(--soft); text-align: left; }}
    ul, ol {{ margin: 10px 0 18px; padding-left: 22px; }}
    li {{ margin: 7px 0; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }}
    .metric {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: var(--panel); min-height: 82px; }}
    .metric strong {{ display: block; font-size: 24px; line-height: 1.2; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .callout {{ margin: 16px 0; padding: 13px 15px; background: var(--soft); border-left: 4px solid var(--accent); }}
    .warning {{ margin: 16px 0; padding: 13px 15px; background: var(--warn-bg); border-left: 4px solid var(--warn); }}
    .bad {{ margin: 16px 0; padding: 13px 15px; background: var(--bad-bg); border-left: 4px solid var(--bad); }}
    .ok {{ margin: 16px 0; padding: 13px 15px; background: var(--ok-bg); border-left: 4px solid var(--ok); }}
    .pill {{ display: inline-block; margin: 2px 5px 2px 0; padding: 2px 7px; border-radius: 999px; background: var(--chip); border: 1px solid #cfe7e2; font-size: 12px; font-weight: 700; }}
    .risk-high {{ color: var(--bad); font-weight: 800; }}
    .risk-mid {{ color: var(--warn); font-weight: 800; }}
    .risk-low {{ color: var(--ok); font-weight: 800; }}
    .example-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .example {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fff; }}
    .small {{ font-size: 13px; color: var(--muted); }}
    @media (max-width: 900px) {{
      main {{ padding: 24px 14px 56px; }}
      .grid, .example-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      table {{ font-size: 13px; }}
    }}
    @media (max-width: 640px) {{
      .grid, .example-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>L 评测可分辨性审计</h1>
  <p class="meta">基于当前 demo5 生成物自动统计。来源：<code>{_esc(_rel(EVENT_LINES_PATH))}</code>、<code>{_esc(_rel(TAU_CONTRACT_PATH))}</code>、<code>{_esc(_rel(PROBE_PLAN_PATH))}</code>。论文依据：<code>{_esc(AAAI_PAPER_PATH)}</code></p>

  <section>
    <h2>结论</h2>
    <div class="bad">
      当前 L 可以用于流程验证，但不适合作为 M0-M3 的强区分实验。主要原因是：
      <strong>事件线阶段缺少递增事实、关系记忆目标高度模板化、probe/opening 显式泄漏连续性要求</strong>。
      这会抬高 M0，压平 M2/M3，让测评看起来稳定，但无法证明不同记忆层级的真实贡献。
    </div>
    <div class="grid">
      {_metric("总风险", risk_level, "当前可分辨性判断")}
      {_metric("L 数量", line_stats["line_count"], "当前事件线")}
      {_metric("阶段事实变化", f"{line_stats['lines_with_stage_fact_variation']}/{line_stats['line_count']}", "有阶段新增事实的 L")}
      {_metric("模板化关系目标", f"{target_stats['top_target_count']}/{line_stats['line_count']}", "最高频目标覆盖")}
      {_metric("I 显式连续性", _pct(interaction_stats["continuity_explicit"], interaction_stats["interaction_count"]), "opening 含前序提示")}
      {_metric("P 显式连续性", _pct(probe_stats["continuity_explicit"], probe_stats["probe_count"]), "probe 含前序提示")}
      {_metric("P 细节泄漏", _pct(probe_stats["detail_request_explicit"], probe_stats["probe_count"]), "直接要求具体细节")}
      {_metric("P 状态泄漏", _pct(probe_stats["state_explicit"], probe_stats["probe_count"]), "直接要求状态变化")}
      {_metric("原始 E 池", e_relationship["raw_event_count"], "event category 总数")}
      {_metric("当前使用 E", e_relationship["used_event_count"], "进入 5 人 demo")}
      {_metric("多 L 复用 E", e_relationship["multi_line_event_count"], "一个 E 生成多条 L")}
      {_metric("E facts 变化", f"{e_relationship['event_with_multiple_fact_sets']}/{e_relationship['used_event_count']}", "同一 E 是否有多组 facts")}
    </div>
  </section>

  <section>
    <h2>E / L / allowed_new_facts 实际关系</h2>
    <div class="callout">
      当前实现里，<code>allowed_new_facts</code> 不是从 L 的每个阶段单独生成的“新事实”，而是从原始 E 的
      <code>core_issue</code>、前两个 <code>possible_uncertainties</code>、前两个
      <code>possible_actions</code> 拼出的基础事实包。实际关系是：
      <strong>E -> allowed_new_facts 近似 1:1；E -> L 是 1:N；L -> stage allowed_new_facts 是同一组 facts 重复。</strong>
    </div>
    <table>
      <thead>
        <tr>
          <th>层级</th>
          <th>当前关系</th>
          <th>当前数量</th>
          <th>含义</th>
          <th>对评测的影响</th>
        </tr>
      </thead>
      <tbody>
        <tr><td><code>E</code> 原始事件类别</td><td>候选池</td><td>{_esc(e_relationship["raw_event_count"])} 个</td><td>来自原始 event category pool。</td><td>只是主题池，不直接等于最终故事线。</td></tr>
        <tr><td><code>E</code> 当前使用</td><td>被 5 人采样接受</td><td>{_esc(e_relationship["used_event_count"])} 个</td><td>当前 44 条 L 实际覆盖的 E。</td><td>未使用 E 不参与当前测评。</td></tr>
        <tr><td><code>E -> L</code></td><td>1:N</td><td>{_esc(e_relationship["line_count"])} 条 L</td><td>同一个 E 可被多个 persona 采用，形成多条 L。</td><td>如果不 persona 化，同一 E 下多条 L 会高度相似。</td></tr>
        <tr><td><code>E -> allowed_new_facts</code></td><td>当前近似 1:1</td><td>{_esc(e_relationship["event_with_multiple_fact_sets"])} 个 E 产生多组 facts</td><td>同一个 E 在不同 L 中 facts 没有变化。</td><td>无法体现 persona 差异，也难区分 M2/M3。</td></tr>
        <tr><td><code>L -> stage facts</code></td><td>当前 1:1 重复</td><td>{_esc(e_relationship["line_with_stage_variation"])} 条 L 有 stage facts 变化</td><td>同一 L 的 5 个阶段复用同一组 facts。</td><td>阶段推进主要靠话术，不靠事实递增。</td></tr>
      </tbody>
    </table>
    <h3>当前 E 到 allowed_new_facts 明细</h3>
    <table>
      <thead>
        <tr>
          <th>E</th>
          <th>事件</th>
          <th>派生 L</th>
          <th>persona</th>
          <th>facts 组数</th>
          <th>allowed_new_facts</th>
        </tr>
      </thead>
      <tbody>
        {''.join(_e_allowed_fact_row(row) for row in e_relationship["rows"])}
      </tbody>
    </table>
  </section>

  <section>
    <h2>评测目标应该是什么</h2>
    <p>
      以 AAAI 论文的 ReMem-RE 口径，M0-M3 的评测不应只看回答是否自然，而应看同一条
      <code>tau=(z,T,L,I,P)</code> 下，agent 是否能在不同记忆条件中表现出可解释差异：
    </p>
    <table>
      <thead><tr><th>条件</th><th>应当考察的能力</th><th>如果 L 设计合理，应看到的差异</th><th>当前风险</th></tr></thead>
      <tbody>
        <tr><td><code>M0</code></td><td>普通 LD-Agent 记忆基线，依赖当前对话和普通检索。</td><td>能处理当前问题，但在隐性跨天 continuity、细节锚点和边界题上下降。</td><td>题面已明示“前面/这条线”，M0 可靠当前 prompt 模仿连续性。</td></tr>
        <tr><td><code>M1</code></td><td>结论级关系记忆：稳定偏好、回应风格、关系期待。</td><td>比 M0 更懂语气和边界，但不能声称知道具体事件细节。</td><td>所有 L 的关系目标相同，M1 变成通用模板而非人物化关系记忆。</td></tr>
        <tr><td><code>M2</code></td><td>事件线摘要记忆：知道同一 L 的进展和阶段。</td><td>能接上这条 L 的摘要进展，但无法使用具体 episode anchor。</td><td>每阶段事实不递增，M2 只拿 summary 就和 M3 接近。</td></tr>
        <tr><td><code>M3</code></td><td>细节级关系锚点：自然调用具体场景、共享措辞、边界敏感细节。</td><td>在 D3/P4、D4/P3、P5/P6 上显著优于 M2，同时不乱编。</td><td>缺少只有 M3 可读的细节锚点，M3 优势难体现。</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>当前统计证据</h2>
    <h3>1. L 阶段事实没有递增</h3>
    <p>
      当前 {_esc(line_stats["line_count"])} 条 L 中，有阶段事实变化的 L 为
      <strong>{_esc(line_stats["lines_with_stage_fact_variation"])}</strong> 条。
      也就是说，每条 L 的 5 个阶段基本使用同一组 <code>allowed_new_facts</code>。
    </p>
    <table>
      <thead><tr><th>指标</th><th>当前值</th><th>解释</th><th>对评测的影响</th></tr></thead>
      <tbody>
        <tr><td>总 L 数</td><td>{_esc(line_stats["line_count"])}</td><td>5 人当前事件线总数。</td><td>数量够流程验证，但不是区分力保证。</td></tr>
        <tr><td>每条 L 阶段数均值</td><td>{_esc(line_stats["avg_stage_count"])}</td><td>通常为 initial、recurrence、turning_point、partial_resolution、reflection。</td><td>阶段标签存在，但事实推进不足。</td></tr>
        <tr><td>阶段事实集合变化</td><td>{_esc(line_stats["lines_with_stage_fact_variation"])} / {_esc(line_stats["line_count"])}</td><td>同一 L 内不同 stage 的 allowed facts 是否不同。</td><td>如果为 0，M2/M3 无法靠阶段事实拉开差距。</td></tr>
        <tr><td>每阶段 allowed facts 均值</td><td>{_esc(line_stats["avg_allowed_fact_count"])}</td><td>每阶段可用事实数量。</td><td>数量稳定，但缺少递增/冲突/转折细节。</td></tr>
      </tbody>
    </table>

    <h3>2. 关系记忆目标高度模板化</h3>
    <p>
      最高频关系目标覆盖 <strong>{_esc(target_stats["top_target_count"])}</strong> 条 L。
      当前前三个关系目标几乎覆盖全部 L：
    </p>
    <table>
      <thead><tr><th>关系记忆目标</th><th>覆盖 L 数</th><th>风险</th></tr></thead>
      <tbody>
        {''.join(_target_row(item) for item in target_stats["top_targets"])}
      </tbody>
    </table>

    <h3>3. I 和 P 对连续性提示过强</h3>
    <table>
      <thead><tr><th>对象</th><th>总数</th><th>含连续性显性词</th><th>含状态/阶段提示</th><th>含细节请求提示</th><th>影响</th></tr></thead>
      <tbody>
        <tr><td><code>I scripted_opening</code></td><td>{_esc(interaction_stats["interaction_count"])}</td><td>{_esc(interaction_stats["continuity_explicit"])} ({_pct(interaction_stats["continuity_explicit"], interaction_stats["interaction_count"])})</td><td>{_esc(interaction_stats["stage_hint_explicit"])} ({_pct(interaction_stats["stage_hint_explicit"], interaction_stats["interaction_count"])})</td><td>不适用</td><td>模型从用户句子就能判断应“承接前文”。</td></tr>
        <tr><td><code>P targeted_probe</code></td><td>{_esc(probe_stats["probe_count"])}</td><td>{_esc(probe_stats["continuity_explicit"])} ({_pct(probe_stats["continuity_explicit"], probe_stats["probe_count"])})</td><td>{_esc(probe_stats["state_explicit"])} ({_pct(probe_stats["state_explicit"], probe_stats["probe_count"])})</td><td>{_esc(probe_stats["detail_request_explicit"])} ({_pct(probe_stats["detail_request_explicit"], probe_stats["probe_count"])})</td><td>M0 可按题面生成“记得”的回答，削弱 M2/M3 差异。</td></tr>
      </tbody>
    </table>

    <h3>4. Probe 类型泄漏分布</h3>
    <table>
      <thead><tr><th>Probe 类型</th><th>数量</th><th>连续性显性词</th><th>状态显性词</th><th>细节显性词</th><th>主要风险</th></tr></thead>
      <tbody>
        {''.join(_probe_type_row(item) for item in probe_stats["by_type"])}
      </tbody>
    </table>
  </section>

  <section>
    <h2>当前会区分不清的具体位置</h2>
    <table>
      <thead><tr><th>问题</th><th>证据</th><th>最受影响的比较</th><th>为什么会混淆</th><th>修正方向</th></tr></thead>
      <tbody>
        {''.join(_issue_row(row) for row in issue_rows)}
      </tbody>
    </table>
  </section>

  <section>
    <h2>样例对比</h2>
    <div class="example-grid">
      {_current_line_example(lines)}
      {_probe_leak_example(probes)}
    </div>
    <h3>应改成的 L 结构</h3>
    <div class="example">
      <p><strong>现在：</strong>同一条 L 的五个 stage 反复使用同一组 allowed facts。</p>
      <p><strong>建议：</strong>每个 occurrence 必须产生阶段 delta，并且给出记忆层级归属：</p>
      <table>
        <thead><tr><th>阶段</th><th>应新增的信息</th><th>可读层级</th><th>评测用途</th></tr></thead>
        <tbody>
          <tr><td>initial</td><td>触发点、当前约束、第一反应。</td><td>M0 可从当前 turn 看到；M2/M3 后续可记。</td><td>建立事件线起点。</td></tr>
          <tr><td>recurrence</td><td>上次采用过的处理方式、这次为什么又出现。</td><td>M2 summary 可见。</td><td>测连续性，不让用户从头解释。</td></tr>
          <tr><td>turning_point</td><td>一个真正改变判断的新事实或新体感。</td><td>M2 summary 可见，关键措辞 M3 可见。</td><td>测状态变化识别。</td></tr>
          <tr><td>partial_resolution</td><td>已经尝试过的动作、结果、剩余担心。</td><td>M2 summary 可见，具体动作/措辞 M3 可见。</td><td>测是否核对进展而非泛泛建议。</td></tr>
          <tr><td>reflection</td><td>用户抽取出的关系偏好、边界、下次复用方式。</td><td>M1 可见结论；M3 可见具体锚点。</td><td>测关系记忆与自然细节使用。</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>修正方案</h2>
    <h3>第一步：重构 L 的生成合同</h3>
    <ol>
      <li>为每条 L 增加 <code>stage_delta_facts[]</code>，禁止五个 stage 复用完全相同的 facts。</li>
      <li>为每个 delta fact 标记 <code>memory_level</code>：<code>M1_stable</code>、<code>M2_event_summary</code>、<code>M3_detail_anchor</code>。</li>
      <li>每条 L 至少包含 1 个 recurrence delta、1 个 turning point delta、1 个 partial resolution delta、1 个 reflection delta。</li>
      <li>每条 L 至少包含 2 个 M3-only 细节锚点，例如具体用户措辞、具体尝试动作、具体犹豫边界。</li>
      <li>每条 L 至少包含 1 个 forbidden/decoy detail，用于测 memory misuse 和 parallel event isolation。</li>
    </ol>

    <h3>第二步：降低 probe/opening 泄漏</h3>
    <ol>
      <li>把至少 50% 的 P3/P4 改为隐性 probe，不直接出现“前面、具体细节、这条线、状态变化”。</li>
      <li>保留一部分显性 probe 作为 easy condition，但必须单独标记 <code>probe_difficulty=explicit</code>，不能和隐性题混算。</li>
      <li>给每个 probe 增加 <code>answerable_from_current_prompt_only</code> 标记；若为 true，则不应用于证明长期记忆优势。</li>
      <li>加入 decoy probe：同一天并行事件中相似主题但不同 L，测试是否串线。</li>
    </ol>

    <h3>第三步：改评分逻辑</h3>
    <ol>
      <li>LLM judge 仍保留 D1-D4，但要新增 memory-dependency rubric：当前回答是否命中目标层级的证据。</li>
      <li>M2 高分必须命中事件线摘要中的阶段进展；M3 高分必须命中 M3-only 细节锚点，并且不能机械背日志。</li>
      <li>如果回答只依据当前问题即可完成，则给 <code>instruction_only_success</code>，不能算长期记忆成功。</li>
      <li>引入 <code>current-prompt-only baseline</code>：不给任何历史记忆，只给当前 user message；若该 baseline 与 M2/M3 接近，说明 probe 不可区分。</li>
    </ol>

    <h3>第四步：增加质量门禁</h3>
    <table>
      <thead><tr><th>门禁</th><th>建议阈值</th><th>不通过时含义</th></tr></thead>
      <tbody>
        <tr><td><code>stage_fact_variation_rate</code></td><td>≥ 80%</td><td>多数 L 有阶段递增事实。</td></tr>
        <tr><td><code>m3_only_anchor_per_line</code></td><td>≥ 2</td><td>每条 L 有足够细节锚点区分 M3。</td></tr>
        <tr><td><code>explicit_probe_ratio</code></td><td>≤ 50%</td><td>probe 不应大多明示“用记忆”。</td></tr>
        <tr><td><code>relationship_target_uniqueness</code></td><td>每 persona 至少 3 类</td><td>M1 不能只是同一套通用关系模板。</td></tr>
        <tr><td><code>current_prompt_only_gap</code></td><td>M2/M3 至少高 10-15 分</td><td>否则说明题目靠当前句子即可答对。</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>建议的下一步执行顺序</h2>
    <div class="callout">
      不建议现在继续扩人。先把当前 5 人 demo 的 L 变成可区分的实验样本，再扩到 100 人。
    </div>
    <ol>
      <li>先改 <code>run_p1_event_line_batch_construction.py</code> / event line constructor：生成 stage delta facts 和 memory-level labels。</li>
      <li>再改 <code>probe_constructor.py</code>：区分 explicit / implicit probe，降低题面泄漏。</li>
      <li>更新 <code>tau_contract</code>：把 target detail 从抽象的 <code>stage_3</code>、<code>previous_days</code> 改为真实可命中的 detail IDs。</li>
      <li>更新 judge case：加入 <code>current_prompt_only</code>、<code>required_memory_level</code>、<code>forbidden_decoy_details</code>。</li>
      <li>重新生成 HTML 审计报告，要求上述质量门禁通过后再跑 M0-M3。</li>
    </ol>
  </section>
</main>
</body>
</html>
"""


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _all_event_lines(doc: dict[str, Any]) -> list[dict[str, Any]]:
    lines = [item for item in doc.get("event_lines", []) if isinstance(item, dict)]
    if lines:
        return lines
    result: list[dict[str, Any]] = []
    for persona_doc in doc.get("personas", []):
        if isinstance(persona_doc, dict):
            result.extend(
                item for item in persona_doc.get("event_lines", []) if isinstance(item, dict)
            )
    return result


def _line_stats(lines: list[dict[str, Any]]) -> dict[str, Any]:
    stage_counts = []
    allowed_counts = []
    changed = 0
    for line in lines:
        stages = [item for item in line.get("stage_sequence", []) if isinstance(item, dict)]
        stage_counts.append(len(stages))
        signatures = []
        for stage in stages:
            allowed = [str(item) for item in stage.get("allowed_new_facts", [])]
            allowed_counts.append(len(allowed))
            signatures.append(tuple(sorted(allowed)))
        if len(set(signatures)) > 1:
            changed += 1
    return {
        "line_count": len(lines),
        "avg_stage_count": round(sum(stage_counts) / len(stage_counts), 2) if stage_counts else 0,
        "avg_allowed_fact_count": round(sum(allowed_counts) / len(allowed_counts), 2)
        if allowed_counts
        else 0,
        "lines_with_stage_fact_variation": changed,
    }


def _interaction_stats(interactions: list[dict[str, Any]]) -> dict[str, Any]:
    continuity = 0
    stage_hint = 0
    by_stage: Counter[str] = Counter()
    for unit in interactions:
        opening = unit.get("scripted_opening", {})
        text = str(opening.get("user_message", "")) if isinstance(opening, dict) else ""
        if _contains_any(text, CONTINUITY_TERMS):
            continuity += 1
        if _contains_any(text, STAGE_HINT_TERMS):
            stage_hint += 1
        by_stage[str(unit.get("event_stage", ""))] += 1
    return {
        "interaction_count": len(interactions),
        "continuity_explicit": continuity,
        "stage_hint_explicit": stage_hint,
        "by_stage": dict(sorted(by_stage.items())),
    }


def _probe_stats(probes: list[dict[str, Any]]) -> dict[str, Any]:
    continuity = 0
    state = 0
    detail = 0
    by_type: dict[str, Counter[str]] = {}
    for probe in probes:
        text = str(probe.get("question") or probe.get("user_message") or "")
        probe_type = str(probe.get("paper_probe_id") or probe.get("probe_type") or "")
        item = by_type.setdefault(probe_type, Counter())
        item["count"] += 1
        if _contains_any(text, CONTINUITY_TERMS):
            continuity += 1
            item["continuity"] += 1
        if _contains_any(text, STATE_TERMS):
            state += 1
            item["state"] += 1
        if _contains_any(text, DETAIL_TERMS):
            detail += 1
            item["detail"] += 1
    return {
        "probe_count": len(probes),
        "continuity_explicit": continuity,
        "state_explicit": state,
        "detail_request_explicit": detail,
        "by_type": [
            {
                "type": key,
                "count": counter.get("count", 0),
                "continuity": counter.get("continuity", 0),
                "state": counter.get("state", 0),
                "detail": counter.get("detail", 0),
            }
            for key, counter in sorted(by_type.items())
        ],
    }


def _target_stats(lines: list[dict[str, Any]]) -> dict[str, Any]:
    targets: Counter[str] = Counter()
    for line in lines:
        for target in line.get("relational_memory_targets", []):
            if isinstance(target, dict) and target.get("target"):
                targets[str(target["target"])] += 1
    top_targets = [
        {"target": target, "count": count}
        for target, count in targets.most_common(6)
    ]
    return {
        "target_count": len(targets),
        "top_target_count": top_targets[0]["count"] if top_targets else 0,
        "top_targets": top_targets,
    }


def _e_allowed_fact_relationship(
    *,
    lines: list[dict[str, Any]],
    event_pool_doc: dict[str, Any],
) -> dict[str, Any]:
    raw_events = [
        item for item in event_pool_doc.get("event_categories", []) if isinstance(item, dict)
    ]
    grouped: dict[str, dict[str, Any]] = {}
    line_with_stage_variation = 0
    for line in lines:
        event_id = str(line.get("event_category_id") or "")
        if not event_id:
            continue
        row = grouped.setdefault(
            event_id,
            {
                "event_category_id": event_id,
                "title": _line_title(line),
                "line_ids": [],
                "personas": [],
                "fact_sets": [],
                "source_core_issue": _source_core_issue(line),
                "source_uncertainties": _source_list(line, "possible_uncertainties"),
                "source_actions": _source_list(line, "possible_actions"),
            },
        )
        row["line_ids"].append(str(line.get("event_line_id") or ""))
        row["personas"].append(str(line.get("persona_id") or ""))
        stage_fact_sets = []
        for stage in line.get("stage_sequence", []):
            if not isinstance(stage, dict):
                continue
            facts = [str(item) for item in stage.get("allowed_new_facts", [])]
            stage_fact_sets.append(tuple(facts))
            row["fact_sets"].append(tuple(facts))
        if len(set(stage_fact_sets)) > 1:
            line_with_stage_variation += 1

    rows = []
    for event_id, row in sorted(grouped.items()):
        unique_fact_sets = _unique_tuples(row["fact_sets"])
        rows.append(
            {
                "event_category_id": event_id,
                "title": row["title"],
                "line_ids": _unique_strings(row["line_ids"]),
                "personas": _unique_strings(row["personas"]),
                "unique_fact_sets": [list(item) for item in unique_fact_sets],
                "source_core_issue": row["source_core_issue"],
                "source_uncertainties": row["source_uncertainties"],
                "source_actions": row["source_actions"],
            }
        )

    return {
        "raw_event_count": len(raw_events),
        "used_event_count": len(rows),
        "line_count": len(lines),
        "multi_line_event_count": sum(1 for row in rows if len(row["line_ids"]) > 1),
        "event_with_multiple_fact_sets": sum(
            1 for row in rows if len(row["unique_fact_sets"]) > 1
        ),
        "line_with_stage_variation": line_with_stage_variation,
        "rows": rows,
    }


def _issue_rows(
    *,
    line_stats: dict[str, Any],
    interaction_stats: dict[str, Any],
    probe_stats: dict[str, Any],
    target_stats: dict[str, Any],
) -> list[dict[str, str]]:
    line_count = int(line_stats["line_count"])
    return [
        {
            "issue": "L 阶段事实没有递增",
            "evidence": f"{line_stats['lines_with_stage_fact_variation']}/{line_count} 条 L 有阶段事实变化。",
            "comparison": "M2 vs M3",
            "why": "M2 只看摘要、M3 看细节，但当前没有足够阶段 delta 和 M3-only anchor。",
            "fix": "每个 stage 生成独立 delta facts，并标记 M2/M3 可读边界。",
            "risk": "high",
        },
        {
            "issue": "关系记忆目标模板化",
            "evidence": f"最高频关系目标覆盖 {target_stats['top_target_count']}/{line_count} 条 L。",
            "comparison": "M0 vs M1, M1 vs M2",
            "why": "M1 记住的是通用风格，不是人物/事件线特异关系期待。",
            "fix": "按 persona 和 L 生成差异化 relationship expectations。",
            "risk": "high",
        },
        {
            "issue": "Probe 显式提示连续性",
            "evidence": f"{probe_stats['continuity_explicit']}/{probe_stats['probe_count']} 个 probe 含前序/这条线提示。",
            "comparison": "M0 vs M2/M3",
            "why": "M0 可根据当前题面猜出应承接前文，形成 instruction-only success。",
            "fix": "引入 implicit probes，并标记 explicit/implicit 分层评估。",
            "risk": "high",
        },
        {
            "issue": "Opening 显式提示阶段",
            "evidence": f"{interaction_stats['stage_hint_explicit']}/{interaction_stats['interaction_count']} 个 opening 含阶段提示词。",
            "comparison": "M0 vs 全部增强条件",
            "why": "事件阶段被自然语言直接暴露，降低 event_stage memory 的价值。",
            "fix": "部分 opening 使用自然但不暴露阶段标签的用户表达。",
            "risk": "medium",
        },
        {
            "issue": "Target detail 过抽象",
            "evidence": "probe target 多为 stage_N / occurrence_N / previous_days。",
            "comparison": "M2 vs M3, judge 评分",
            "why": "评分很难判断回答是否命中真实细节，只能判断是否泛称前文。",
            "fix": "把 target_detail_ids 改成可审计的具体事实/锚点 ID。",
            "risk": "high",
        },
    ]


def _overall_risk(issue_rows: list[dict[str, str]]) -> str:
    high = sum(1 for item in issue_rows if item["risk"] == "high")
    if high >= 3:
        return "高"
    if high:
        return "中"
    return "低"


def _current_line_example(lines: list[dict[str, Any]]) -> str:
    line = lines[0] if lines else {}
    title = _line_title(line)
    stages = [item for item in line.get("stage_sequence", []) if isinstance(item, dict)]
    facts = stages[0].get("allowed_new_facts", []) if stages else []
    rows = []
    for stage in stages[:5]:
        rows.append(
            "<tr>"
            f"<td>{_esc(stage.get('source_stage_label') or stage.get('event_stage'))}</td>"
            f"<td>{_esc(stage.get('user_state_hint'))}</td>"
            f"<td>{_esc('；'.join(str(item) for item in stage.get('allowed_new_facts', [])[:3]))}</td>"
            "</tr>"
        )
    return f"""
    <div class="example">
      <h3>当前 L 样例：{_esc(title)}</h3>
      <p class="small">示例显示：阶段 hint 在变，但 allowed facts 基本复用。</p>
      <p><span class="pill">{_esc(line.get('event_line_id'))}</span></p>
      <p><strong>第一阶段 facts：</strong>{_esc('；'.join(str(item) for item in facts))}</p>
      <table>
        <thead><tr><th>阶段</th><th>用户状态 hint</th><th>allowed facts 摘要</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def _probe_leak_example(probes: list[dict[str, Any]]) -> str:
    example = None
    for probe in probes:
        text = str(probe.get("question") or probe.get("user_message") or "")
        if _contains_any(text, CONTINUITY_TERMS) and _contains_any(text, DETAIL_TERMS + STATE_TERMS):
            example = probe
            break
    if example is None:
        example = probes[0] if probes else {}
    question = str(example.get("question") or example.get("user_message") or "")
    return f"""
    <div class="example">
      <h3>当前 Probe 泄漏样例</h3>
      <p><span class="pill">{_esc(example.get('probe_id'))}</span><span class="pill">{_esc(example.get('paper_probe_id'))}</span></p>
      <p>{_esc(question)}</p>
      <p class="small">
        风险：如果题目直接说“前面”“具体细节”“状态变化”，模型可以在没有真实长期记忆的情况下按指令生成高分风格回答。
      </p>
    </div>
    """


def _target_row(item: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{_esc(item['target'])}</td>"
        f"<td>{_esc(item['count'])}</td>"
        "<td>覆盖过高会把 M1 变成通用回应风格，而不是人物/事件特异关系记忆。</td>"
        "</tr>"
    )


def _e_allowed_fact_row(row: dict[str, Any]) -> str:
    facts_sets = row.get("unique_fact_sets", [])
    facts = facts_sets[0] if facts_sets else []
    source_parts = [
        f"<p><strong>生成 facts：</strong>{_fact_list(facts)}</p>",
        f"<p class=\"small\"><strong>原始 core_issue：</strong>{_esc(row.get('source_core_issue'))}</p>",
        f"<p class=\"small\"><strong>原始 uncertainties：</strong>{_esc('；'.join(row.get('source_uncertainties', [])))}</p>",
        f"<p class=\"small\"><strong>原始 actions：</strong>{_esc('；'.join(row.get('source_actions', [])))}</p>",
    ]
    if len(facts_sets) > 1:
        source_parts.insert(
            0,
            f"<p class=\"risk-high\">同一 E 当前产生 {len(facts_sets)} 组 allowed_new_facts。</p>",
        )
    return (
        "<tr>"
        f"<td><code>{_esc(row.get('event_category_id'))}</code></td>"
        f"<td>{_esc(row.get('title'))}</td>"
        f"<td>{_esc(len(row.get('line_ids', [])))}<br><span class=\"small\">{_esc(' / '.join(row.get('line_ids', [])))}</span></td>"
        f"<td>{_esc('、'.join(row.get('personas', [])))}</td>"
        f"<td>{_esc(len(facts_sets))}</td>"
        f"<td>{''.join(source_parts)}</td>"
        "</tr>"
    )


def _probe_type_row(item: dict[str, Any]) -> str:
    count = int(item["count"])
    risk = "中"
    if item["continuity"] / count >= 0.8 if count else False:
        risk = "高"
    if item["detail"] / count >= 0.8 if count else False:
        risk = "高"
    return (
        "<tr>"
        f"<td><code>{_esc(item['type'])}</code></td>"
        f"<td>{_esc(count)}</td>"
        f"<td>{_esc(item['continuity'])} ({_pct(item['continuity'], count)})</td>"
        f"<td>{_esc(item['state'])} ({_pct(item['state'], count)})</td>"
        f"<td>{_esc(item['detail'])} ({_pct(item['detail'], count)})</td>"
        f"<td>{_esc(risk)}</td>"
        "</tr>"
    )


def _issue_row(row: dict[str, str]) -> str:
    risk_class = {
        "high": "risk-high",
        "medium": "risk-mid",
        "low": "risk-low",
    }.get(row["risk"], "")
    risk_label = {"high": "高", "medium": "中", "low": "低"}.get(row["risk"], row["risk"])
    return (
        "<tr>"
        f"<td><strong>{_esc(row['issue'])}</strong><br><span class=\"{risk_class}\">风险：{_esc(risk_label)}</span></td>"
        f"<td>{_esc(row['evidence'])}</td>"
        f"<td>{_esc(row['comparison'])}</td>"
        f"<td>{_esc(row['why'])}</td>"
        f"<td>{_esc(row['fix'])}</td>"
        "</tr>"
    )


def _line_title(line: dict[str, Any]) -> str:
    title = line.get("event_title")
    if isinstance(title, dict):
        return str(title.get("zh") or title.get("source") or "")
    return str(title or line.get("event_type") or "")


def _source_core_issue(line: dict[str, Any]) -> str:
    source = line.get("source_event_category", {})
    if isinstance(source, dict):
        return str(source.get("core_issue") or "")
    return ""


def _source_list(line: dict[str, Any], key: str) -> list[str]:
    source = line.get("source_event_category", {})
    if not isinstance(source, dict):
        return []
    value = source.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _unique_tuples(values: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    result = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result


def _unique_strings(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result


def _fact_list(facts: list[str]) -> str:
    if not facts:
        return "<span class=\"small\">无</span>"
    return "<ol>" + "".join(f"<li>{_esc(item)}</li>" for item in facts) + "</ol>"


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _metric(value: str, number: Any, note: str) -> str:
    return (
        '<div class="metric">'
        f"<strong>{_esc(number)}</strong>"
        f"<span>{_esc(value)} · { _esc(note) }</span>"
        "</div>"
    )


def _pct(part: int | float, total: int | float) -> str:
    if not total:
        return "0.0%"
    return f"{(float(part) / float(total)) * 100:.1f}%"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
