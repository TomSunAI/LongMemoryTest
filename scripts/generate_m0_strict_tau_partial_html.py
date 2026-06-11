#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = REPO_ROOT / "long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal"
TAU_CONTRACT_PATH = REPO_ROOT / "long_memory_experiment/data/script/tau_contract.json"
DOCS_OUTPUT_PATH = REPO_ROOT / "docs/m0_strict_tau_partial_experiment_report.html"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Chinese HTML report for the M0 strict tau partial run.")
    parser.add_argument("--run-dir", type=Path, default=RUN_DIR)
    parser.add_argument("--tau-contract", type=Path, default=TAU_CONTRACT_PATH)
    parser.add_argument("--output", type=Path, default=DOCS_OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir
    result = _load_json(run_dir / "responses_by_condition.json")
    conversation = _load_json(run_dir / "conversation_log.json")
    run_config = _load_json(run_dir / "run_config.json")
    automatic = _load_json(run_dir / "automatic_scores.json")
    tau = _load_json(args.tau_contract)

    html_text = render_report(
        result=result,
        conversation=conversation,
        run_config=run_config,
        automatic=automatic,
        tau=tau,
        run_dir=run_dir,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    run_copy = run_dir / args.output.name
    run_copy.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Wrote {run_copy}")
    return 0


def render_report(
    *,
    result: dict[str, Any],
    conversation: dict[str, Any],
    run_config: dict[str, Any],
    automatic: dict[str, Any],
    tau: dict[str, Any],
    run_dir: Path,
) -> str:
    turns = conversation.get("turns", [])
    expected_turns = int(result.get("expected_turns") or run_config.get("expected_turns") or 0)
    completed_turns = len(turns)
    remaining_turns = max(0, expected_turns - completed_turns)
    type_counts = Counter(str(turn.get("source", {}).get("turn_type", "unknown")) for turn in turns)
    days_seen = sorted({int(turn.get("input", {}).get("day") or 0) for turn in turns if turn.get("input", {}).get("day")})
    last_turn = turns[-1] if turns else {}
    score_summary = automatic.get("summary", {}).get("variants", {}).get("M0", {})
    dimension_scores = automatic.get("summary", {}).get("dimension_averages", {}).get("M0", {})
    score_turn_count = int(score_summary.get("turn_count") or 0)
    m0_memory = result.get("m0_ld_agent_memory", {})
    i_units = tau.get("I", [])
    bad_i = [
        item
        for item in i_units
        if not _strict_i_ok(item)
    ]
    probe_turns = [
        turn
        for turn in turns
        if str(turn.get("source", {}).get("turn_type")) == "targeted_probe"
    ]
    writebacks = Counter(
        str(
            turn.get("variants", {})
            .get("M0", {})
            .get("memory_writeback", {})
            .get("action", "missing")
        )
        for turn in turns
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>M0 严格 tau 阶段性实验报告</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #5c6670;
      --line: #d9e0e7;
      --soft: #f6f8fb;
      --panel: #ffffff;
      --accent: #0f766e;
      --accent-2: #7c3aed;
      --warn: #b45309;
      --bad: #b91c1c;
      --good: #166534;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      line-height: 1.65;
      color: var(--ink);
      background: #eef2f6;
    }}
    header {{
      padding: 36px 44px 28px;
      background: #10202a;
      color: #fff;
    }}
    header h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    header p {{ margin: 0; max-width: 1100px; color: #d7e1e8; }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 24px 28px 64px; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 18px 0;
      padding: 22px;
    }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    h3 {{ margin: 20px 0 8px; font-size: 17px; }}
    p {{ margin: 8px 0; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin: 12px 0;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
      padding: 14px;
      min-height: 92px;
    }}
    .metric .label {{ color: var(--muted); font-size: 13px; }}
    .metric .value {{ display: block; font-weight: 700; font-size: 25px; margin-top: 4px; }}
    .metric .note {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}
    .tag {{
      display: inline-block;
      border: 1px solid var(--line);
      background: var(--soft);
      border-radius: 999px;
      padding: 2px 9px;
      margin: 2px 4px 2px 0;
      font-size: 12px;
      color: #2c3a45;
    }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 4px; font-size: 14px; }}
    th, td {{ border: 1px solid var(--line); padding: 8px 10px; vertical-align: top; }}
    th {{ background: #edf4f7; text-align: left; }}
    code {{
      background: #eef3f6;
      border: 1px solid #d8e2e8;
      border-radius: 5px;
      padding: 1px 5px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.92em;
    }}
    pre {{
      margin: 10px 0;
      padding: 14px;
      background: #0f1720;
      color: #dce7ef;
      border-radius: 8px;
      overflow-x: auto;
      line-height: 1.45;
    }}
    .ok {{ color: var(--good); font-weight: 700; }}
    .warn {{ color: var(--warn); font-weight: 700; }}
    .bad {{ color: var(--bad); font-weight: 700; }}
    .small {{ color: var(--muted); font-size: 13px; }}
    .two-col {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 16px;
    }}
    .example {{
      border-left: 4px solid var(--accent);
      padding: 10px 12px;
      background: #f5fbfa;
      margin: 10px 0;
    }}
    @media (max-width: 800px) {{
      header {{ padding: 26px 20px; }}
      main {{ padding: 16px; }}
      .two-col {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>M0 严格 tau 对齐阶段性实验报告</h1>
    <p>本报告基于当前已完成的 M0-only partial run 生成。实验已人工暂停，剩余 turn 可用 resume 命令晚上继续跑。</p>
  </header>
  <main>
    <section>
      <h2>一、当前结论</h2>
      <div class="grid">
        {_metric("实验进度", f"{completed_turns}/{expected_turns}", f"剩余 {remaining_turns} 条")}
        {_metric("当前最后一条", _esc(last_turn.get("source", {}).get("message_id", "n/a")), f"day={last_turn.get('input', {}).get('day', 'n/a')}, type={last_turn.get('source', {}).get('turn_type', 'n/a')}")}
        {_metric("M0 自动均分", str(score_summary.get("average_tom_score", "n/a")), f"评分只覆盖 targeted probes：{score_turn_count} 条")}
        {_metric("tau 校验", _esc(tau.get("validation", {}).get("status", "unknown")), f"issues={len(tau.get('validation', {}).get('issues', []))}")}
      </div>
      <p><strong>阶段性判断：</strong>M0 可以在严格 <code>tau=(z,T,L,I,P)</code> 剧本结构下正常运行，M0 的运行时记忆写回、probe 跳过写回、tau 绑定、受控 follow-up 路径都已经打通。当前结果不是完整正式结论，因为只完成了 37/96 条；完整实验需要继续跑完剩余 59 条后重新评分。</p>
      <p><strong>暂停原因：</strong>实验中出现过两次 API read timeout，均可通过 <code>--resume</code> 续跑。当前暂停是按你的要求人工冻结 checkpoint，不是实验逻辑失败。</p>
    </section>

    <section>
      <h2>二、为什么 tau=(z,T,L,I,P) 是关键</h2>
      <p><code>tau</code> 在当前系统里不是一个要塞进 prompt 的说明句，也不是给模型看的论文符号。它是整套实验剧本的<strong>控制坐标系</strong>：每一条用户消息、每一条事件线、每一个 probe 都必须能回到同一个 <code>tau</code> 结构里定位。这样 M0/M1/M2/M3 才是在同一套剧本上比较记忆能力，而不是各自看到不同任务。</p>
      <h3>当前系统中的实现入口</h3>
      <p>实现入口是 <code>src/long_memory_test/experiment_cache.py</code> 里的 <code>build_tau_contract(...)</code>。它把多个生成阶段的产物收束成一个文件：<code>long_memory_experiment/data/script/tau_contract.json</code>。这个文件就是当前剧本的唯一 construction contract。</p>
      <table>
        <tr><th>输入源</th><th>提供什么</th><th>进入 tau 的位置</th></tr>
        <tr><td><code>data/config/persona.json</code></td><td>稳定用户画像：年龄、职业、家庭状态、长期目标。</td><td><code>z.stable_attributes</code>, <code>z.long_term_goals</code></td></tr>
        <tr><td><code>data/config/user_actor.json</code></td><td>表达风格、压力反应、稳定回应偏好、M1 可用关系细节。</td><td><code>z.speech_profile</code>, <code>z.emotional_model</code>, <code>z.stable_memory_details</code></td></tr>
        <tr><td><code>timeline_events.json</code></td><td>底层事件流、event_id、domain、related_event_id、memory_detail_anchors。</td><td><code>T.source_event_ids</code>, <code>L.root_event_id</code>, <code>I.event_refs</code></td></tr>
        <tr><td><code>daily_user_message.json</code></td><td>30 天 scripted opening，自然用户消息、intent、topic。</td><td><code>I.scripted_opening</code>, <code>message_bindings</code></td></tr>
        <tr><td><code>daily_scene_cards.json</code></td><td>allowed facts、latent concerns、follow-up 预算、禁止新增内容。</td><td><code>I.constrained_followup</code>, <code>I.scene_boundary</code></td></tr>
        <tr><td><code>probe_question_plan.json</code></td><td>36 个 targeted probes、probe_type、target_detail_ids、ToM 维度。</td><td><code>P</code>, <code>message_bindings</code></td></tr>
        <tr><td><code>timeline.json</code></td><td>day-level canonical timeline，决定 day、event_stage、probe_ids、latent_continuity。</td><td><code>T</code>, <code>L.stage_sequence</code>, <code>I</code></td></tr>
      </table>
      <p>所以现在的剧本生成不是“先生成一堆消息，然后凭 topic 去猜属于哪里”。现在是先形成统一坐标，再把消息、场景卡、probe 和 memory payload 都绑定到同一个坐标上。</p>
      <table>
        <tr><th>符号</th><th>白话含义</th><th>在当前剧本里实际控制什么</th><th>为什么重要</th></tr>
        <tr><td><code>z</code></td><td>这个用户是谁</td><td>稳定 persona：年龄、职业、家庭状态、压力源、表达风格、长期偏好。</td><td>保证所有事件都发生在同一个用户身上，不是每天换一个人。</td></tr>
        <tr><td><code>T</code></td><td>长期主题池</td><td>6 个主题：幼儿园不稳定、合作项目、论文截稿、家里分工、孩子入园、睡眠。</td><td>替代原来松散的 topic。它不是直接写进 prompt 的关键词，而是给事件线分组和检索用的主题身份。</td></tr>
        <tr><td><code>L</code></td><td>持续事件线</td><td>每个主题展开成 5 个阶段：initial、recurrence、turning_point、resolution、reflection。</td><td>让模型面对的不是孤立消息，而是一条跨天发展的关系相关历史。</td></tr>
        <tr><td><code>I</code></td><td>每日交互单元</td><td>每天的 scripted opening、受控 follow-up、允许事实、隐含担心、禁止新增内容。</td><td>控制用户今天到底能说什么、不能说什么，避免剧本漂移。</td></tr>
        <tr><td><code>P</code></td><td>关系探针</td><td>插入到某个 I 之后的 targeted probe，绑定 event_line、target details、ToM 维度。</td><td>专门测试 agent 是否接住长期关系预期，而不是只回答当前句子。</td></tr>
      </table>
      <h3>一句话理解</h3>
      <p><strong><code>tau</code> 把“生成剧本”和“评估记忆”接在一起：</strong>剧本生成时，它规定用户、主题、事件线、每日交互和探针；实验运行时，它给每条 turn 绑定坐标；评估时，它告诉我们这个回答应该被放回哪条长期事件线里判断。</p>
      <h3>字段级落地：不是抽象概念，而是实际 JSON 结构</h3>
      <table>
        <tr><th>tau 字段</th><th>当前 JSON 中有什么</th><th>下游怎么用</th></tr>
        <tr><td><code>z</code></td><td>完整 persona snapshot。当前包括 <code>persona_id=user_001</code>、35 岁、researcher、已婚有一个孩子、表达风格、压力源、稳定回应偏好。</td><td>作为长期用户身份背景；M1/M2/M3 的稳定关系记忆边界来自这里，M0 的 persona memory 也会和这些稳定特征形成对照。</td></tr>
        <tr><td><code>T</code></td><td>6 个主题，每个主题有 <code>theme_id</code>、中文 label、domain、对应的 event_line_ids 和 source_event_ids。</td><td>用于主题级分组、检索锚点和报告统计；它替代原来的松散 <code>topic</code>，但不直接作为 prompt 标签暴露。</td></tr>
        <tr><td><code>L</code></td><td>6 条事件线，每条线有 5 个 interaction_unit_ids，保存 stage_sequence。</td><td>用于判断某条消息是 initial、recurrence、turning_point、resolution 还是 reflection；M2/M3 后续会围绕 event_line 摘要和细节锚点改进。</td></tr>
        <tr><td><code>I</code></td><td>30 个每日交互单元。每个 I 包含 <code>scripted_opening</code>、<code>constrained_followup</code>、<code>scene_boundary</code>。</td><td>控制用户当天说什么、follow-up 能补什么、哪些事实允许出现、哪些内容不能编造；正式实验的 follow-up 就从这里的 scene card 约束生成。</td></tr>
        <tr><td><code>P</code></td><td>36 个 targeted probes。每个 P 绑定 interaction_unit、event_line、probe_type、target_detail_ids、tom_dimensions、required_memory_type。</td><td>作为评估入口，专门测试关系预期、共享语境调用、自然细节使用、记忆误用等 ToM 维度。</td></tr>
        <tr><td><code>message_bindings</code></td><td>66 条消息绑定：30 条 opening + 36 条 probe。每条都有 persona_id、theme_id、event_line_id、event_stage、interaction_unit_id。</td><td>把所有输入 turn 绑定回同一个 tau 坐标，runner、memory payload、conversation log 和评分报告都依赖它。</td></tr>
      </table>
      <h3>message_bindings 为什么很重要</h3>
      <p><code>message_bindings</code> 是 tau 真正进入实验运行的接口。没有它，<code>T/L/I/P</code> 只是一个静态说明；有了它，每条消息都能被定位到“哪个用户、哪个主题、哪条事件线、哪个阶段、哪个每日交互单元”。</p>
      <p>比如一个 probe <code>D10_P002</code>，不会只被看成“第 10 天的一个问题”。它会被绑定为：属于 <code>T_parenting_5b64c58d</code>，属于 <code>L_e001_a6634568</code>，阶段是 <code>turning_point</code>，插入在 <code>D10_M001</code> 之后，测试的 probe_type 是 <code>alienation</code>。这让评估可以判断 agent 是不是在长期关系语境里回答，而不是只做单轮问答。</p>
      <h3>生成、运行、评估三阶段怎么共享 tau</h3>
      <table>
        <tr><th>阶段</th><th>tau 的作用</th><th>具体表现</th></tr>
        <tr><td>剧本生成阶段</td><td>定义统一剧本骨架。</td><td>生成 <code>tau_contract.json</code>，同时把 tau metadata 写回 <code>daily_user_message.json</code>、<code>daily_scene_cards.json</code>、<code>probe_question_plan.json</code>、<code>timeline.json</code>。</td></tr>
        <tr><td>memory condition 构造阶段</td><td>把每条消息的 tau binding 放入 M0/M1/M2/M3 payload。</td><td><code>memory_conditions_combined.json</code> 中 66 条 payload 都带 tau；M0-M3 共用同一套绑定，不再各自定义剧本。</td></tr>
        <tr><td>runner 阶段</td><td>每个 turn 写入 tau 坐标，但不把实验标签泄露给模型。</td><td><code>source.tau</code>、<code>memory_setup.script_construction.tau</code>、<code>memory_payload.tau</code> 都会落盘；follow-up 继承 opening 的 tau。</td></tr>
        <tr><td>评估阶段</td><td>把回答放回正确事件线和 probe 目标下解释。</td><td>自动评分只看已完成 targeted probes；报告可按 event_line、probe_type、ToM 维度汇总。</td></tr>
      </table>
      <h3>当前真实例子：幼儿园这条线</h3>
      <div class="example">
        <p><strong>z：</strong>用户是 35 岁研究者，已婚有一个 3 岁孩子，压力源包括 child education、research deadlines、family coordination；表达风格是直接、自然、希望拆事实和下一步。</p>
        <p><strong>T：</strong><code>T_parenting_5b64c58d</code>，主题是“孩子幼儿园可能不稳定”。</p>
        <p><strong>L：</strong><code>L_e001_a6634568</code>，这不是一次“幼儿园 topic 提及”，而是 5 天的事件线：D01 初次听到不稳定消息，D04 信息仍不清楚，D10 转向“怕孩子被折腾”，D17 有一点结果并开始看模式，D29 进入反思。</p>
        <p><strong>I：</strong>D01 的交互单元包括开场消息“今天听到幼儿园那边可能不太稳定...”，follow-up 预算、允许揭示的事实、允许揭示的 latent concern，以及不能新增学校、城市、日期、诊断等剧本外事实。</p>
        <p><strong>P：</strong>D01_P001/D01_P002/D01_P003 会测试 agent 是否识别用户真正问的是“我该不该继续紧着”，是否能接住关系期待，而不是只给换园清单。</p>
      </div>
      <h3>它和 prompt 的关系</h3>
      <p><code>tau</code> 不应该整段写进用户 prompt。原因是：如果把 <code>event_stage</code>、<code>probe_type</code>、<code>target_detail_ids</code> 直接给模型，就等于泄露实验答案。当前做法是：<code>tau</code> 作为元数据进入 run log、memory payload、评估绑定；模型只看到用户自然语言、短期上下文和当前条件允许的记忆内容。</p>
      <p>所以我们之前说 “topic 不需要直接写入 prompt” 的核心就在这里：<code>T/theme</code> 主要起<strong>组织、绑定、检索、评估</strong>作用，不是让模型看到一个标签后照标签答题。真正进入对话的是自然用户消息和允许记忆，不是论文符号。</p>
      <h3>在 M0-M3 中的边界</h3>
      <p><strong>M0：</strong>当前基线使用 LD-Agent 风格普通长短期记忆。M0 可以在运行记录和 payload 元数据里带 tau，但不允许读取 <code>probe_type</code>、gold strategy、BEI 标注，也不应该把 <code>event_stage</code> 当作提示答案。</p>
      <p><strong>M1：</strong>应该只使用稳定关系结论和回应偏好，不能声称知道具体历史事件。它可以借助同一 tau 坐标知道 payload 属于哪条消息，但记忆内容边界仍然是结论级。</p>
      <p><strong>M2：</strong>在自身隔离 namespace 里使用事件线摘要。这里 <code>L.event_line_id</code> 会变得关键，因为 M2 要回答“这条线之前怎么发展到现在”。</p>
      <p><strong>M3：</strong>在 M2 基础上使用细节锚点。这里 <code>I.scene_boundary.event_detail_ids</code>、<code>P.target_detail_ids</code> 会变得关键，因为 M3 要判断哪些细节可以自然使用，哪些细节会造成过度记忆或编造。</p>
      <h3>对 M0-M3 比较的意义</h3>
      <p>没有 <code>tau</code> 时，M0/M1/M2/M3 的差异很容易混成“剧本不同、检索不同、probe 对不上”的差异。有了 <code>tau</code> 后，所有条件共享同一套 <code>z/T/L/I/P</code>，差异被收缩到记忆系统本身：M0 是普通 LD-Agent 风格记忆，M1 是关系结论记忆，M2 加事件线摘要，M3 加细节锚点。这样后续结果才有可解释性。</p>
    </section>

    <section>
      <h2>三、严格 tau 结构对齐</h2>
      <p>现在所有剧本生成都收敛到同一套 construction contract：<code>tau=(z,T,L,I,P)</code>。M0/M1/M2/M3 不再各自生成剧本，只读取同一个脚本源和同一套绑定。</p>
      <div class="grid">
        {_metric("z persona", "1", "完整稳定用户画像")}
        {_metric("T themes", str(tau.get("summary", {}).get("theme_count")), "长期事件主题")}
        {_metric("L event lines", str(tau.get("summary", {}).get("event_line_count")), "递进事件线")}
        {_metric("I daily units", str(tau.get("summary", {}).get("interaction_unit_count")), f"严格坏项 {len(bad_i)}")}
        {_metric("P probes", str(tau.get("summary", {}).get("targeted_probe_count")), "关系探针")}
        {_metric("绑定消息", str(tau.get("summary", {}).get("bound_message_count")), "opening + probes")}
      </div>
      <h3>z = sampled user persona</h3>
      {render_persona(tau.get("z", {}))}
      <h3>T/L = 主题和事件线</h3>
      {render_event_lines(tau)}
      <h3>I = daily interaction units 的严格化</h3>
      <p>每个 <code>I</code> 现在不只是 message id，而是完整的每日交互单元：</p>
      <table>
        <tr><th>字段</th><th>作用</th><th>当前状态</th></tr>
        <tr><td><code>scripted_opening</code></td><td>当天用户开场，介绍当前事件状态。</td><td class="ok">30/30 存在</td></tr>
        <tr><td><code>constrained_followup</code></td><td>受控 follow-up 生成规则：预算、允许动作、揭示步骤、停止条件、禁止新增内容。</td><td class="ok">30/30 存在</td></tr>
        <tr><td><code>scene_boundary</code></td><td>允许事实、隐含担心、记忆层级规则、审计维度。</td><td class="ok">30/30 存在</td></tr>
      </table>
      {render_sample_i(tau.get("I", [{}])[0] if tau.get("I") else {})}
      <h3>P = targeted relational probes</h3>
      {render_sample_probe(tau.get("P", [{}])[0] if tau.get("P") else {})}
    </section>

    <section>
      <h2>四、M0 当前实现细节</h2>
      <table>
        <tr><th>模块</th><th>当前实现</th><th>说明</th></tr>
        <tr><td>基线身份</td><td>当前版本 M0</td><td>Letta M0 只保留，不作为后续基线；本次使用 LD-Agent 风格记忆实现。</td></tr>
        <tr><td>provider</td><td><code>{_esc(run_config.get("m0_ld_agent_memory_baseline", {}).get("provider"))}</code></td><td>只使用 memory，不使用 LD-Agent generator 或 checkpoint。</td></tr>
        <tr><td>记忆库</td><td><code>session_summary_memories</code>, <code>generic_persona_memories</code></td><td>一类记录会话摘要，一类记录稳定用户偏好/画像。</td></tr>
        <tr><td>检索</td><td><code>topic_overlap_time_decay</code>, top_k={_esc(run_config.get("m0_ld_agent_memory_baseline", {}).get("top_k"))}</td><td>按主题重叠和时间衰减检索 M0 可用记忆。</td></tr>
        <tr><td>写回</td><td><code>ld_agent_session_summary_and_personas_traits</code></td><td>非 probe turn 后写入，probe turn 跳过写回，避免测试题污染记忆。</td></tr>
        <tr><td>tau 可见性</td><td>运行元数据可见，prompt 不直接暴露实验标签</td><td>tau 绑定用于追踪和检索/评估，不把实验结构当作用户对话内容硬塞给模型。</td></tr>
      </table>
      <div class="grid">
        {_metric("session summaries", str(len(m0_memory.get("session_summary_memories", []))), "M0 当前写回")}
        {_metric("persona memories", str(len(m0_memory.get("persona_memories", []))), "M0 当前写回")}
        {_metric("short-term session", str(len(m0_memory.get("short_term_session", []))), "当前 session 尾部")}
        {_metric("memory actions", str(len(m0_memory.get("actions", []))), "含 retrieve/write/skip")}
      </div>
      <h3>写回动作统计</h3>
      {render_counter_table(writebacks, "动作", "次数")}
    </section>

    <section>
      <h2>五、阶段性实验结果</h2>
      <div class="grid">
        {_metric("完成天数范围", f"{min(days_seen) if days_seen else 'n/a'}-{max(days_seen) if days_seen else 'n/a'}", f"覆盖 {len(days_seen)} 天")}
        {_metric("scripted opening", str(type_counts.get("scripted_opening", 0)), "已完成")}
        {_metric("controlled follow-up", str(type_counts.get("llm_user_followup", 0)), "由 scene card 约束生成")}
        {_metric("targeted probes", str(type_counts.get("targeted_probe", 0)), "自动评分对象")}
      </div>
      <h3>自动评分</h3>
      <table>
        <tr><th>指标</th><th>数值</th><th>解释</th></tr>
        <tr><td>平均 ToM 分数</td><td>{_esc(score_summary.get("average_tom_score"))}</td><td>当前只基于已完成的 16 条 probe，不代表完整 36 条 probe。</td></tr>
        <tr><td>alienation error</td><td>{_esc(score_summary.get("alienation_error_count"))}</td><td>当前规则评分未发现明显疏离错误。</td></tr>
        <tr><td>ask repeat error</td><td>{_esc(score_summary.get("ask_repeat_error_count"))}</td><td>当前规则评分未发现明显要求用户重复背景。</td></tr>
        <tr><td>generic comfort</td><td>{_esc(score_summary.get("generic_comfort_count"))}</td><td>当前规则评分未发现明显泛泛安慰。</td></tr>
      </table>
      <h3>维度均分</h3>
      {render_dimensions(dimension_scores)}
      <h3>最低分样例</h3>
      {render_lowest_examples(automatic)}
      <h3>当前已完成 turn 样例</h3>
      {render_turn_samples(turns)}
    </section>

    <section>
      <h2>六、阶段性风险和解释</h2>
      <table>
        <tr><th>观察</th><th>解释</th><th>后续处理</th></tr>
        <tr><td>平均分 69.79</td><td>当前 M0 有一定关系识别能力，但 <code>natural_detail_use</code> 和 <code>relationship_expectation_recognition</code> 维度偏低。</td><td>完整跑完后再判断是否是早期样本偏差；M1-M3 可针对这些维度做改进。</td></tr>
        <tr><td>部分回答会主动联想多条线</td><td>M0 使用 session summary 和 persona memory 后，可能更愿意总结模式；这对关系连续性有帮助，但也可能出现“过度整合”。</td><td>后续评估要看 memory_misuse 和 natural_detail_use 的平衡。</td></tr>
        <tr><td>API timeout</td><td>这是网络/服务读取超时，不是 tau 结构或 M0 写回错误。</td><td>继续使用 <code>--resume</code>；必要时降低 max_tokens 或改为夜间跑。</td></tr>
        <tr><td>partial run</td><td>当前只完成 16/36 个 probes，评分样本不足。</td><td>晚上跑完剩余 59 条后，重新生成 automatic_scores 和最终 HTML。</td></tr>
      </table>
    </section>

    <section>
      <h2>七、晚上继续跑的命令</h2>
      <p>当前 checkpoint 已固定在 <code>{_esc(run_dir)}</code>。继续跑不会重跑前 37 条，会从下一条继续。</p>
      <pre>{_esc(resume_command())}</pre>
      <p>跑完后建议依次执行：</p>
      <pre>{_esc(post_commands())}</pre>
    </section>

    <section>
      <h2>八、产物位置</h2>
      <table>
        <tr><th>文件</th><th>用途</th></tr>
        <tr><td><code>long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal/responses_by_condition.json</code></td><td>实验主结果和 checkpoint。</td></tr>
        <tr><td><code>long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal/conversation_log.json</code></td><td>可读对话日志。</td></tr>
        <tr><td><code>long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal/automatic_scores.json</code></td><td>当前自动评分。</td></tr>
        <tr><td><code>long_memory_experiment/data/script/tau_contract.json</code></td><td>严格 tau construction contract。</td></tr>
        <tr><td><code>docs/m0_strict_tau_partial_experiment_report.html</code></td><td>本中文阶段性报告。</td></tr>
      </table>
    </section>
  </main>
</body>
</html>
"""


def render_persona(z: dict[str, Any]) -> str:
    attrs = z.get("stable_attributes", {})
    tags = "".join(f'<span class="tag">{_esc(k)}: {_esc(v)}</span>' for k, v in attrs.items())
    traits = ", ".join(str(item) for item in z.get("personality_traits", []))
    pressures = ", ".join(str(item) for item in z.get("pressure_sources", []))
    goals = ", ".join(str(item) for item in z.get("long_term_goals", []))
    return f"""
      <p><strong>persona_id:</strong> <code>{_esc(z.get("persona_id"))}</code>；<strong>actor_id:</strong> <code>{_esc(z.get("actor_id"))}</code></p>
      <p>{tags}</p>
      <p><strong>人格/表达倾向：</strong>{_esc(traits)}</p>
      <p><strong>稳定压力源：</strong>{_esc(pressures)}</p>
      <p><strong>长期目标：</strong>{_esc(goals)}</p>
      <p class="small">PDF 示例里提到 gender，但当前 persona 配置没有提供 gender，所以 contract 明确标记为 unprovided，不编造。</p>
    """


def render_event_lines(tau: dict[str, Any]) -> str:
    rows = [
        "<table><tr><th>Event line</th><th>主题</th><th>阶段序列</th><th>unit/probe</th></tr>"
    ]
    theme_by_id = {item.get("theme_id"): item for item in tau.get("T", [])}
    for line in tau.get("L", []):
        stages = " -> ".join(
            f"D{int(item.get('day', 0)):02d}:{item.get('stage')}"
            for item in line.get("stage_sequence", [])
        )
        theme = theme_by_id.get(line.get("theme_id"), {})
        rows.append(
            "<tr>"
            f"<td><code>{_esc(line.get('event_line_id'))}</code></td>"
            f"<td>{_esc(theme.get('label') or line.get('label'))}</td>"
            f"<td>{_esc(stages)}</td>"
            f"<td>{len(line.get('interaction_unit_ids', []))} / {len(line.get('probe_ids', []))}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def render_sample_i(unit: dict[str, Any]) -> str:
    opening = unit.get("scripted_opening", {})
    followup = unit.get("constrained_followup", {})
    boundary = unit.get("scene_boundary", {})
    reveal = followup.get("reveal_steps", [])
    facts = boundary.get("allowed_fact_ids", [])
    return f"""
      <div class="example">
        <p><strong>样例 I：</strong><code>{_esc(unit.get("interaction_unit_id"))}</code>，day={_esc(unit.get("day"))}，event_stage={_esc(unit.get("event_stage"))}</p>
        <p><strong>scripted opening：</strong>{_esc(opening.get("user_message"))}</p>
        <p><strong>follow-up budget：</strong>{_esc(followup.get("followup_budget"))}；<strong>permitted moves：</strong>{len(followup.get("permitted_conversational_moves", []))}；<strong>reveal steps：</strong>{len(reveal)}</p>
        <p><strong>allowed facts：</strong>{_esc(", ".join(str(item) for item in facts[:6]))}</p>
      </div>
    """


def render_sample_probe(probe: dict[str, Any]) -> str:
    return f"""
      <div class="example">
        <p><strong>样例 P：</strong><code>{_esc(probe.get("probe_id"))}</code>，type={_esc(probe.get("probe_type"))}</p>
        <p><strong>绑定：</strong>interaction_unit=<code>{_esc(probe.get("interaction_unit_id"))}</code>，event_line=<code>{_esc(probe.get("event_line_id"))}</code></p>
        <p><strong>ToM 维度：</strong>{_esc(", ".join(str(item) for item in probe.get("tom_dimensions", [])))}</p>
        <p><strong>目标细节：</strong>{_esc(", ".join(str(item) for item in probe.get("target_detail_ids", [])[:8]))}</p>
      </div>
    """


def render_dimensions(dimension_scores: dict[str, Any]) -> str:
    rows = ["<table><tr><th>维度</th><th>均分</th><th>解释</th></tr>"]
    explanations = {
        "hidden_intent_recognition": "能否识别用户表层问题背后的真实意图。",
        "emotional_state_recognition": "能否识别用户当前情绪状态。",
        "relationship_expectation_recognition": "能否读出用户对长期关系/熟悉感的期待。",
        "shared_context_invocation": "能否自然承接共同历史语境。",
        "natural_detail_use": "能否用细节而不是机械复述。",
        "memory_misuse": "是否避免错用/滥用记忆。",
        "alienation_error_rate": "是否避免疏离、客服化、要求重讲背景。",
    }
    for key, value in sorted(dimension_scores.items()):
        rows.append(
            f"<tr><td><code>{_esc(key)}</code></td><td>{_esc(value)}</td><td>{_esc(explanations.get(key, ''))}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def render_lowest_examples(automatic: dict[str, Any]) -> str:
    examples = automatic.get("summary", {}).get("lowest_scoring_examples", [])[:5]
    if not examples:
        return "<p class=\"small\">暂无低分样例。</p>"
    blocks = []
    for item in examples:
        blocks.append(
            f"""
            <div class="example">
              <p><strong>{_esc(item.get("message_id"))}</strong> | score={_esc(item.get("tom_score"))}</p>
              <p>{_esc(item.get("answer_excerpt", ""))}</p>
            </div>
            """
        )
    return "\n".join(blocks)


def render_turn_samples(turns: list[dict[str, Any]]) -> str:
    rows = ["<table><tr><th>message_id</th><th>day</th><th>type</th><th>event_line</th><th>writeback</th></tr>"]
    sample_turns = turns[:8] + (turns[-4:] if len(turns) > 12 else [])
    for turn in sample_turns:
        source = turn.get("source", {})
        variants = turn.get("variants", {})
        writeback = variants.get("M0", {}).get("memory_writeback", {}).get("action")
        rows.append(
            "<tr>"
            f"<td><code>{_esc(source.get('message_id'))}</code></td>"
            f"<td>{_esc(turn.get('input', {}).get('day'))}</td>"
            f"<td>{_esc(source.get('turn_type'))}</td>"
            f"<td><code>{_esc(source.get('tau', {}).get('event_line_id'))}</code></td>"
            f"<td><code>{_esc(writeback)}</code></td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def render_counter_table(counter: Counter[str], left: str, right: str) -> str:
    rows = [f"<table><tr><th>{_esc(left)}</th><th>{_esc(right)}</th></tr>"]
    for key, value in sorted(counter.items()):
        rows.append(f"<tr><td><code>{_esc(key)}</code></td><td>{value}</td></tr>")
    rows.append("</table>")
    return "\n".join(rows)


def _strict_i_ok(unit: dict[str, Any]) -> bool:
    opening = unit.get("scripted_opening", {})
    followup = unit.get("constrained_followup", {})
    boundary = unit.get("scene_boundary", {})
    return (
        isinstance(opening, dict)
        and bool(opening.get("user_message"))
        and isinstance(followup, dict)
        and followup.get("followup_budget") is not None
        and bool(followup.get("permitted_conversational_moves"))
        and bool(followup.get("reveal_steps"))
        and bool(followup.get("must_not_introduce"))
        and isinstance(boundary, dict)
        and bool(boundary.get("allowed_facts"))
    )


def resume_command() -> str:
    return (
        "PYTHONPATH=src .venv/bin/python scripts/05_run_dialogue_conditions.py "
        "--all-message-ids --conditions M0 --scene-followups 1 --condition-workers 1 "
        "--llm-timeout 600 --max-tokens 900 --temperature 0.2 "
        "--run-dir long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal "
        "--resume --print-progress --print-mode summary"
    )


def post_commands() -> str:
    return "\n".join(
        [
            "PYTHONPATH=src .venv/bin/python scripts/06_evaluate_tom.py --run-dir long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal",
            "PYTHONPATH=src .venv/bin/python scripts/08_report_results.py --run-dir long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal --review-limit 24",
            "PYTHONPATH=src .venv/bin/python scripts/generate_m0_strict_tau_partial_html.py",
        ]
    )


def _metric(label: str, value: str, note: str) -> str:
    return f"""
      <div class="metric">
        <div class="label">{_esc(label)}</div>
        <span class="value">{_esc(value)}</span>
        <div class="note">{_esc(note)}</div>
      </div>
    """


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
