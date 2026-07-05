#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an HTML report for the A-side script.")
    parser.add_argument(
        "--daily-messages",
        type=Path,
        default=REPO_ROOT / "long_memory_experiment/data/script/daily_user_message.json",
    )
    parser.add_argument(
        "--scene-cards",
        type=Path,
        default=REPO_ROOT / "long_memory_experiment/data/script/daily_scene_cards.json",
    )
    parser.add_argument(
        "--probe-questions",
        type=Path,
        default=REPO_ROOT / "long_memory_experiment/data/script/probe_question_plan.json",
    )
    parser.add_argument(
        "--script-plan",
        type=Path,
        default=REPO_ROOT / "long_memory_experiment/data/script/a_script_plan.json",
    )
    parser.add_argument(
        "--tom-evaluation",
        type=Path,
        default=REPO_ROOT / "long_memory_experiment/outputs/latest/automatic_scores.json",
    )
    parser.add_argument(
        "--llm-tom-evaluation",
        type=Path,
        default=REPO_ROOT / "long_memory_experiment/outputs/latest/llm_judge_scores.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs/a_script_report_summary.html",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    daily_messages = _load_json(args.daily_messages)["messages"]
    scene_cards = _load_json(args.scene_cards)["scene_cards"]
    probe_plan = _load_json(args.probe_questions)
    script_plan = _load_json(args.script_plan)
    tom_evaluation = _load_json(args.tom_evaluation) if args.tom_evaluation.exists() else None
    llm_tom_evaluation = (
        _load_json(args.llm_tom_evaluation) if args.llm_tom_evaluation.exists() else None
    )

    scene_by_message_id = {
        card["opening_message_id"]: card
        for card in scene_cards
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        _render_html(
            daily_messages=daily_messages,
            scene_by_message_id=scene_by_message_id,
            probe_plan=probe_plan,
            script_plan=script_plan,
            tom_evaluation=tom_evaluation,
            llm_tom_evaluation=llm_tom_evaluation,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_html(
    *,
    daily_messages: list[dict[str, Any]],
    scene_by_message_id: dict[str, dict[str, Any]],
    probe_plan: dict[str, Any],
    script_plan: dict[str, Any],
    tom_evaluation: dict[str, Any] | None,
    llm_tom_evaluation: dict[str, Any] | None,
) -> str:
    summary = script_plan["summary"]
    probe_summary = probe_plan["summary"]
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            "  <title>ToM 指标口径与长程对话实验流程汇报</title>",
            f"  <style>{_css()}</style>",
            "</head>",
            "<body>",
            '  <main class="page">',
            "    <h1>ToM 指标口径与长程对话实验流程汇报</h1>",
            '    <p class="meta">更新时间：2026-05-28 · 本报告重点解释评价口径和实验流程</p>',
            _report_position_section(summary, probe_summary),
            _tom_standard_section(),
            _experiment_process_section(),
            _script_structure_section(summary, probe_summary),
            _probe_combined_section(probe_plan),
            _tom_evaluation_section(tom_evaluation, llm_tom_evaluation),
            _opening_table(daily_messages, scene_by_message_id),
            _unit_explanation_section(),
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _report_position_section(
    summary: dict[str, Any],
    probe_summary: dict[str, Any],
) -> str:
    return f"""
    <section>
      <h2>1. 报告定位与评价口径</h2>
      <p>这份 HTML 的主目标不是证明某个模型已经优于另一个模型，而是说明如何把“AI 是否理解用户”拆成可解释、可复查的 ToM 评价指标，并说明一条长程对话实验如何被组织、记录和评分。</p>
      <p>当前 A 侧剧本模拟“同一个聊天窗口内，一个月中用户持续和 AI 对话”的过程，共 <strong>{_e(summary["unit_count"])}</strong> 个剧本单元，其中包含 <strong>{_e(probe_summary["probe_count"])}</strong> 条 ToM 定向测试问题。</p>
      <p class="note">正式实验应使用 M0/M1/M2/M3 四组同题对照；旧样例分数只作为历史参考，不能代表新版模型结论。</p>
    </section>
    """


def _tom_standard_section() -> str:
    dimension_rows = [
        (
            "hidden_intent_recognition",
            "隐含意图识别",
            "用户没有直接说出口的真实诉求是什么。",
            "只回答字面问题，忽略用户其实在确认关系、状态或边界。",
            "先接住潜台词，再给具体判断或行动建议。",
        ),
        (
            "emotional_state_recognition",
            "情绪状态识别",
            "用户是疲惫、失落、自我怀疑、担心被忘记，还是普通询问。",
            "把用户状态处理成普通信息咨询，或只给空泛安慰。",
            "能说清用户当下状态，并把建议控制在这个状态能承受的范围内。",
        ),
        (
            "relationship_expectation_recognition",
            "关系期待识别",
            "用户期待的是熟悉关系中的回应，而不是陌生客服式服务。",
            "用模板话术、突兀称呼或过度亲密表演破坏关系连续性。",
            "保持熟悉、直接、自然的语气，不靠称呼制造亲密感。",
        ),
        (
            "shared_context_invocation",
            "共同语境调用",
            "用户希望 AI 接上此前形成的处理方式，而不是每次从零开始。",
            "要求用户重讲历史，或把持续事件当成第一次出现。",
            "自然接上此前语境，少量调用关键背景，并继续当前判断。",
        ),
        (
            "alienation_error_rate",
            "陌生化错误率",
            "是否出现客服化、角色化、过度亲密或要求重讲历史。",
            "出现“用户/亲爱的/主人”等出戏称呼，或把关系降级为客服流程。",
            "不制造距离，也不表演亲密，维持稳定关系位置。",
        ),
        (
            "natural_detail_use",
            "自然细节调用",
            "关键细节是否服务于心理理解，而不是机械背日志。",
            "堆砌日期、原话和细节，或为了显得记得而补用户没说过的内容。",
            "只调用必要细节，用来理解用户状态、边界和下一步。",
        ),
        (
            "memory_misuse",
            "记忆误用",
            "是否错误调用过期、无关、不可读或不存在的记忆。",
            "编造、过度复述，或把不可确定内容说成已知事实。",
            "克制调用，清楚区分已知、推测和不能补的空白。",
        ),
    ]
    return f"""
    <section>
      <h2>2. ToM 指标与评分口径</h2>
      <p>当前评价对象不是“模型记住了多少事实”，而是“模型是否理解用户为什么这样说、希望 AI 如何接住，以及如何在不编造的前提下恢复共同语境”。</p>
      {_table(["维度 id", "中文名", "测试问题", "低分表现", "高分表现"], dimension_rows, large=True)}
      <h3>0-2 分计分规则</h3>
      {_table(["指标", "评分问题", "0 分", "1 分", "2 分"], _scoring_metric_rows(), large=True)}
      <p class="note">单条回答的 ToM 分数 = 本题相关维度平均分 / 2 * 100。实验组平均 ToM 分 = 该实验组所有 ToM probe 分数的平均值。每个维度原始分为 0-2 分，其中 1 分代表部分识别，2 分必须有明确回答证据并转化为回应策略。</p>
      <h3>评分逻辑小结：LLM 主评 + 规则辅助</h3>
      <p>当前正式口径已经切换为 LLM-as-judge 主评测。LLM judge 负责语义判断和引用证据，规则评分只保留为辅助诊断，用来快速发现关键词命中、陌生化、要求重讲历史和泛化安慰等风险。</p>
      {_table(["环节", "当前实现", "解释口径"], _scoring_logic_summary_rows(), large=True)}
      <h3>单条回答如何由 LLM judge 评分</h3>
      {_table(["步骤", "处理方式", "分数影响"], _single_answer_scoring_rows(), large=True)}
      <h3>当前 LLM judge review 结论</h3>
      {_table(["检查项", "结论", "后续改进"], _scoring_review_rows(), large=True)}
    </section>
    """


def _experiment_process_section() -> str:
    rows = [
        ("1", "生成 30 天事件线", "`timeline.json` 保存用户一个月内的生活事件、主题和跨天关联。"),
        ("2", "生成每日开场", "`daily_user_message.json` 固定每天第一条用户原始发言，保证可复现。"),
        ("3", "生成场景卡", "`daily_scene_cards.json` 限定当天可继续聊的事实、隐含担心、follow-up 预算和禁止编造项。"),
        ("4", "扩展同日追问", "运行时由 DeepSeek 在场景卡边界内生成 follow-up；同一条用户追问同时喂给 M0/M1/M2/M3。"),
        ("5", "插入 ToM probe", "`probe_question_plan.json` 在自然 follow-up 后插入 ToM 定向问题。"),
        ("6", "运行对话实验", "`05_run_dialogue_conditions.py` 生成 M0/M1/M2/M3 回答，并持续写入 checkpoint 与 conversation log。"),
        ("7", "LLM-as-judge 主评分", "`07_judge_review.py` 只读取 targeted probe 轮，对 M0/M1/M2/M3 回答做盲评和结构化打分。"),
        ("8", "规则辅助与人工复核", "规则评分只用于 triage；正式实验应补充人工抽样复核和分歧样例复核。"),
    ]
    return f"""
    <section>
      <h2>3. 实验流程</h2>
      <p>实验流程的核心是把用户过程、模型回答和评价过程分开：用户剧本可复现，模型回答可记录，评分器只读日志做离线评价。</p>
      {_table(["步骤", "环节", "说明"], rows, large=True)}
    </section>
    """


def _script_structure_section(summary: dict[str, Any], probe_summary: dict[str, Any]) -> str:
    counts = summary["turn_type_counts"]
    rows = [
        ("每日开场 scripted opening", counts["scripted_opening"], "每天第一条用户原始发言，由剧本固定给出"),
        ("同日 LLM follow-up slot", counts["llm_user_followup_slot"], "同一天内可继续聊的扩展槽位，实际运行时由 DeepSeek 在场景卡边界内生成"),
        ("ToM 定向测试问题 targeted probe", counts["targeted_probe"], "插入自然对话之后，带 ToM 指标、隐含需求和高低分表现"),
    ]
    tom_dimension_rows = _tom_dimension_coverage_rows(probe_summary)
    return f"""
    <section>
      <h2>4. 当前示例剧本结构</h2>
      <p>当前 A 侧剧本用于模拟“用户在同一个聊天窗口中，在一个月内持续和 AI 对话”的过程。剧本不是单条问答，而是一条 30 天的连续用户生活线。</p>
      <p>当前完整剧本总表为 <code>sample_output/a_script_plan.json</code>，共 <strong>{_e(summary["unit_count"])}</strong> 个剧本单元。</p>
      {_table(["类型", "数量", "含义"], rows)}
      <p class="note">注意：64 个 follow-up slot 是“可扩展轮次”，不是已经生成的对话原文。实际跑对话时，脚本会根据 <code>--scene-followups N</code> 决定每一天生成几轮同日追问。</p>
      <h3>ToM 指标覆盖</h3>
      <p>当前共 <strong>{_e(probe_summary["probe_count"])}</strong> 条定向测试问题，分布在第 {_e(", ".join(str(day) for day in probe_summary["days_with_probes"]))} 天。覆盖摘要按 ToM 新标准统计，不再按旧 probe 类型作为主轴。</p>
      {_table(["ToM 指标", "覆盖题数", "主要测试点"], tom_dimension_rows)}
    </section>
    """


def _unit_explanation_section() -> str:
    return """
    <section>
      <h2>8. 附录：三类剧本单元解释</h2>
      <h3>8.1 每日开场是什么</h3>
      <p>每日开场是用户在某一天主动发给 AI 的第一条消息。它决定当天对话的主题、情绪、意图和 ToM 测试背景。</p>
      <ul>
        <li>每天 1 条，共 30 条。</li>
        <li>不由模型临场生成，属于固定剧本。</li>
        <li>每条开场都绑定 <code>day</code>、<code>message_id</code>、<code>topic</code>、<code>intent</code>、<code>event_refs</code>、<code>memory_relevance</code>。</li>
        <li>有些开场是第一次提出问题，有些是跨天回到旧问题，用来测试 AI 是否能接住长期关系中的连续性。</li>
      </ul>
      <h3>8.2 同日 LLM follow-up slot 是什么</h3>
      <p>follow-up slot 是“用户继续聊下去”的位置。它不直接写死用户原文，而是在运行时让 DeepSeek 生成下一条用户追问。</p>
      <ul>
        <li>只能使用当天场景卡、历史用户发言和允许透露的事实。</li>
        <li>不能把 assistant 的建议、假设或例子转写成用户事实。</li>
        <li>不能补剧本外事实，例如新学校、新诊断、新城市、新金额。</li>
        <li>同一条生成出的用户 follow-up 会同时喂给 M0 和 M1，保证对照实验公平。</li>
      </ul>
      <h3>8.3 定向测试问题是什么</h3>
      <p>定向测试问题是插入到自然对话之后的 ToM 检查点。它们不单独考事实背诵，而是观察 AI 是否能在既有场景背景下理解用户的潜台词、情绪状态、关系期待和共同语境。</p>
    </section>
    """


def _opening_table(
    daily_messages: list[dict[str, Any]],
    scene_by_message_id: dict[str, dict[str, Any]],
) -> str:
    rows = []
    for message in daily_messages:
        scene_card = scene_by_message_id.get(message["message_id"], {})
        expansion_controls = scene_card.get("expansion_controls", {})
        rows.append(
            (
                message["day"],
                message["topic"],
                message["intent"],
                expansion_controls.get("followup_budget", 0),
                message["user_message"],
            )
        )
    return f"""
    <section>
      <h2>7. 附录：30 天每日开场明细</h2>
      {_table(["天", "主题", "意图", "follow-up slot", "开场原文"], rows, large=True)}
    </section>
    """


def _probe_combined_section(probe_plan: dict[str, Any]) -> str:
    detail_rows = []
    for question in probe_plan["probe_questions"]:
        tom = question.get("tom_assessment", {})
        dimensions = list(question.get("tom_dimensions", []))
        primary_dimension = dimensions[0] if dimensions else ""
        secondary_dimensions = dimensions[1:]
        detail_rows.append(
            (
                question["day"],
                question["message_id"],
                _dimension_label(primary_dimension),
                ", ".join(_dimension_label(dimension) for dimension in secondary_dimensions),
                question["topic"],
                question["user_message"],
                tom.get("surface_question", ""),
                tom.get("hidden_user_need", ""),
                tom.get("low_score_behavior", ""),
                tom.get("high_score_behavior", ""),
            )
        )
    return f"""
    <section>
      <h2>5. 当前题集：{_e(probe_plan.get("summary", {}).get("probe_count", len(questions)))} 条 ToM 定向测试问题</h2>
      <p>这些问题的核心不是推进剧情，也不是单纯问模型要建议，而是作为以记忆场景为背景的 ToM 测试点。问题原文会故意更接近真实用户的含蓄表达，用来观察 AI 是否能识别用户的隐含意图、情绪状态、关系期待、共同语境、自然细节调用和记忆误用边界。</p>
      <h3>ToM 方式下的问题设计复核</h3>
      {_table(["复核项", "当前判断", "下一版建议"], _tom_question_design_review_rows(probe_plan), large=True)}
      <h3>逐条问题明细与测试意图</h3>
      {_table(["天", "probe id", "主 ToM 指标", "辅助 ToM 指标", "主题", "问题原文", "表面在问", "隐含需求", "低分表现", "高分表现"], detail_rows, large=True)}
    </section>
    """


def _tom_evaluation_section(
    tom_evaluation: dict[str, Any] | None,
    llm_tom_evaluation: dict[str, Any] | None,
) -> str:
    execution_logic_html = "\n".join(
        [
            "<h3>实验问题</h3>",
            _table(["项目", "实验口径"], _experiment_question_rows(), large=True),
            "<h3>对照组与控制变量</h3>",
            _table(["变量", "控制方式", "目的"], _experimental_control_rows(), large=True),
            "<h3>一次完整实验怎么执行</h3>",
            _table(["步骤", "操作", "产物/检查点"], _full_experiment_steps_rows(), large=True),
            "<h3>日志到评分的数据流</h3>",
            _table(["阶段", "输入", "输出", "复核点"], _evaluation_data_flow_rows(), large=True),
        ]
    )
    if not tom_evaluation and not llm_tom_evaluation:
        return f"""
        <section>
          <h2>6. 实验执行逻辑与示例结果（非严谨结论）</h2>
          <p>这一节先说明正式实验应该如何执行，再放当前样例结果。当前报告版本即使没有评分文件，也应能看清实验链路。</p>
          {execution_logic_html}
          <p class="note">当前未加载 LLM-as-judge 或规则评分结果，因此本 HTML 只展示方案标准和剧本结构。</p>
        </section>
        """
    primary_evaluation_html = ""
    if llm_tom_evaluation:
        primary_evaluation_html = f"""
      <h3>主评测结果：LLM-as-judge</h3>
      <p>当前主评测采用 DeepSeek 作为 LLM-as-judge。judge 对每个 targeted probe 下的 M0/M1/M2/M3 回答做盲评，只暴露 Condition A/B/C/D；每个维度要求给出严格 0-2 分、引用回答证据、标记失败类型并输出结构化 JSON。</p>
      {_table(["实验组", "probe 回答数", "平均 ToM 分", "平均置信度", "需人工复核", "失败标记"], _llm_variant_summary_rows(llm_tom_evaluation))}
      <h3>LLM judge 分维度均值</h3>
      {_table(["实验组", "隐含意图", "情绪状态", "关系期待", "共同语境", "陌生化", "自然细节调用", "记忆误用"], _llm_dimension_average_rows(llm_tom_evaluation))}
      <h3>LLM judge 低分样例</h3>
      {_table(["实验组", "probe id", "ToM 分", "置信度", "judge 理由"], _llm_lowest_example_rows(llm_tom_evaluation), large=True)}
        """
    auxiliary_evaluation_html = ""
    if tom_evaluation:
        auxiliary_evaluation_html = f"""
      <h3>辅助诊断：规则评分结果</h3>
      <p>规则评分保留为 triage 工具，用来快速定位关键词命中、陌生化风险、要求重讲历史和泛化安慰；它不再作为当前报告的主结论。</p>
      {_table(["实验组", "probe 数", "平均 ToM 分", "陌生化错误", "要求重讲历史", "泛化安慰"], _variant_summary_rows(tom_evaluation))}
      <h3>规则评分分维度均值</h3>
      {_table(["实验组", "隐含意图", "情绪状态", "关系期待", "共同语境", "陌生化", "自然细节调用", "记忆误用"], _dimension_average_rows(tom_evaluation))}
        """
    return f"""
    <section>
      <h2>6. 实验执行逻辑与示例结果（非严谨结论）</h2>
      <p>这一节说明完整实验应该怎么做：先固定用户剧本和 ToM 问题，再让 M0/M1/M2/M3 在同一输入下分别回答，最后只读取日志中的 targeted probe 做离线 ToM 评分。当前主评测已切换为 LLM-as-judge，规则评分只作为辅助诊断；新版正式结论需要先重跑四组同题对照。</p>
      {execution_logic_html}
      <h3>当前样例结果的边界</h3>
      <p>以下结果来自已有对话日志的离线评测。LLM-as-judge 重新调用 DeepSeek 对回答做结构化裁判；规则评分只作为辅助对照。由于本轮题集还没有按严谨实验设计做均衡覆盖，这里只作为流程示例和评分样例，不作为最终模型优劣结论。</p>
      <h3>评分来源</h3>
      {_table(["项目", "内容"], _evaluation_source_rows())}
      <h3>是否需要重跑实验</h3>
      {_table(["结论", "理由", "建议"], _rerun_decision_rows(), large=True)}
      {primary_evaluation_html}
      {auxiliary_evaluation_html}
    </section>
    """


def _experiment_question_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "研究问题",
            "在同一个 30 天用户过程里，不同记忆权限的 AI 是否能更稳定地识别用户的隐含意图、情绪状态、关系期待和共同语境。",
        ),
        (
            "当前比较对象",
            "M0/M1/M2/M3。四组只改变可读取的长期记忆类型：generic、结论级、摘要级事件、细节级关系锚点。",
        ),
        (
            "评分样本",
            "只把 targeted probe 作为 ToM 评分样本。每日开场和自然 follow-up 用来建立上下文，不直接进入当前 ToM 均分。",
        ),
        (
            "解释边界",
            "当前 ToM 分数只能说明这一版样例日志中的回应质量倾向；正式实验需要均衡题集、固定模型参数、重复运行和人工/强模型复核。",
        ),
    ]


def _experimental_control_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "用户输入",
            "同一条 scripted opening、同一条 DeepSeek 生成 follow-up、同一条 targeted probe 同时喂给 M0/M1/M2/M3。",
            "避免因用户问题不同导致结果不可比。",
        ),
        (
            "模型与调用参数",
            "M0/M1/M2/M3 使用同一 DeepSeek 模型和同一运行参数。",
            "把差异尽量收敛到记忆权限，而不是模型能力或采样差异。",
        ),
        (
            "同窗口短期上下文",
            "M0/M1/M2/M3 都保留相同长度的短期历史。",
            "模拟真实聊天窗口里的连续对话；M0 是 generic agent memory 基线，不是 no-memory。",
        ),
        (
            "长期记忆权限",
            "M0 只用 generic memory；M1 读结论级关系记忆；M2 增加摘要级事件线；M3 增加必要细节和关系锚点。",
            "把唯一变量限定为可读长期记忆层级。",
        ),
        (
            "用户扩展边界",
            "follow-up 由 DeepSeek 生成，但只能使用场景卡允许的事实、隐含担心和当天边界。",
            "让对话更自然，同时避免生成器引入剧本外事实。",
        ),
        (
            "可恢复性",
            "每个用户 turn 完成后写 checkpoint，并按 run_id 同步 conversation log。",
            "长跑中断后可以 resume，且不会重复追加已完成 turn。",
        ),
    ]


def _full_experiment_steps_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "1",
            "固定 A 侧 30 天剧本、每日开场、场景卡和 ToM probe 题集。",
            "long_memory_experiment/data/script/a_script_plan.json、daily_user_message.json、daily_scene_cards.json、probe_question_plan.json。",
        ),
        (
            "2",
            "确认 M0/M1/M2/M3 记忆权限和可读边界。",
            "long_memory_experiment/data/memory_conditions/*.json 中的 can_read/cannot_read 应与运行配置一致。",
        ),
        (
            "3",
            "执行 30 天 M0/M1/M2/M3 对话链路，并在自然 follow-up 后插入 ToM probe。",
            "运行脚本：scripts/05_run_dialogue_conditions.py，输出 run_YYYYMMDD_HHMM/conversation_log.json。",
        ),
        (
            "4",
            "如果中断，用同一 output 和 conversation log 路径执行 --resume。",
            "checkpoint.status、completed_message_ids、last_message_id 可复核恢复位置。",
        ),
        (
            "5",
            "抽查 conversation_log 原文，确认同一 message_id 下四组收到的是同一用户输入。",
            "检查 input_hash、turn.source、turn.user_message、turn.variants.*.assistant_answer。",
        ),
        (
            "6",
            "运行 LLM-as-judge 主评分器，只读取 targeted probe。",
            "输出 llm_judge_scores.json 和 llm_judge_scores.md。",
        ),
        (
            "7",
            "同步运行规则评分作为辅助诊断，汇总 LLM 主分、分维度均值、failure_types、依赖题分析和低分样例。",
            "正式结论再加盲化人工复核；当前未重跑时只展示结构。",
        ),
    ]


def _evaluation_data_flow_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "剧本层",
            "A 侧人物背景、30 天事件线、每日开场、场景卡、ToM probe。",
            "可复现的用户过程。",
            "检查问题是否都在剧本边界内，是否覆盖 ToM 指标。",
        ),
        (
            "运行层",
            "固定用户输入和记忆权限后调用 DeepSeek。",
            "M0/M1/M2/M3 每轮 assistant_answer 与运行 checkpoint。",
            "检查四组是否同题对照，是否存在恢复重复或缺 turn。",
        ),
        (
            "日志层",
            "每轮用户输入、来源、上下文策略、评估目标、M0/M1/M2/M3 回答。",
            "conversation_log.json / conversation_log_tom_probe.json。",
            "检查 targeted probe 是否带 tom_dimensions、required_memory_type 和 dependency_analysis。",
        ),
        (
            "评分层",
            "只读取 targeted probe 下的 assistant_answer。",
            "LLM judge ToM 维度分、平均分、confidence、failure_types、低分样例；规则评分为辅助输出。",
            "检查评分是否只看 ToM，不混入旧的事实细节命中指标；同时确认 judge 没有看到 M0/M1/M2/M3 标签。",
        ),
        (
            "解释层",
            "评分结果 + 原始回答摘录 + 题集设计边界。",
            "HTML 汇报。",
            "把样例结果和正式结论分开，避免过度解释。",
        ),
    ]


def _evaluation_source_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "输入日志",
            "long_memory_experiment/outputs/run_YYYYMMDD_HHMM/conversation_log.json；只读取带 tom_dimensions 的 targeted probe 轮。",
        ),
        (
            "主评分脚本",
            "scripts/07_judge_review.py 调用 src/long_memory_test/evaluation/llm_tom_judge.py，以 DeepSeek 做 LLM-as-judge。",
        ),
        (
            "主评分输出",
            "long_memory_experiment/outputs/run_YYYYMMDD_HHMM/llm_judge_scores.json 和 llm_judge_scores.md。",
        ),
        (
            "辅助评分脚本",
            "scripts/06_evaluate_tom.py 调用 src/long_memory_test/evaluation/tom_quality_evaluator.py。",
        ),
        (
            "评分对象",
            "每个 ToM probe 下 M0/M1/M2/M3 的 assistant_answer；普通每日开场和 LLM follow-up 不进入 ToM 评分。",
        ),
        (
            "辅助评分输出",
            "long_memory_experiment/outputs/run_YYYYMMDD_HHMM/automatic_scores.json 和 automatic_scores.md。",
        ),
        (
            "边界说明",
            "当前 LLM-as-judge 是主评测，但题集仍是样例设计；正式结论应补均衡题集、重复运行和人工复核。",
        ),
    ]


def _rerun_decision_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "旧样例结果只能留作历史参考",
            "本轮已把题集扩展到 36 条，并改为 M0/M1/M2/M3 四组同题对照；旧 M0/M1 样例不能代表新版题集。",
            "正式结果应按新版 run 目录重跑并重新生成 automatic_scores、llm_judge_scores 和 human_review_sample。",
        ),
        (
            "正式实验建议重跑一版",
            "新版题集已补 shared_context、alienation、state transformation、memory misuse 和依赖题/主问题配对。",
            "用相同模型、参数、短期上下文策略重跑 M0/M1/M2/M3，生成新版 conversation_log 和评分输出。",
        ),
        (
            "什么时候必须重跑",
            "只要修改 probe 问题原文、增加题数、改变模型、改变 M0/M1/M2/M3 记忆配置、改变短期上下文策略，评分输入就变了。",
            "这些情况下必须重新跑对话，而不是只重算评分。",
        ),
    ]


def _scoring_metric_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "隐含意图识别",
            "是否识别用户字面表达背后的真实诉求。",
            "只回答字面问题，或没有命中任何隐含需求证据。",
            "部分识别潜台词，但没有转化为回应策略。",
            "明确接住潜台词，并围绕真实需求回应。",
        ),
        (
            "情绪状态识别",
            "是否识别疲惫、失落、自我怀疑、不安、担心被遗忘等状态。",
            "把用户状态当普通咨询处理，或只有泛化安慰。",
            "提到情绪，但和建议关系弱。",
            "识别具体状态，并调整建议强度。",
        ),
        (
            "关系期待识别",
            "是否识别用户期待熟悉、直接、不过度表演的关系回应。",
            "客服式、模板化、过度亲密，或没有回应关系位置。",
            "语气不陌生，但只是普通友好；没有体现稳定关系期待。",
            "熟悉、直接、不过度表演，并体现在回应方式里。",
        ),
        (
            "共同语境调用",
            "是否接上此前形成的处理方式，而不是每次从零开始。",
            "要求用户重讲历史，或把持续事件当成第一次出现。",
            "泛称“之前”或“我们说过”，但没有可验证连接。",
            "自然接上旧线索或共同处理方式，并继续当前判断。",
        ),
        (
            "陌生化错误率",
            "是否出现客服化、角色化、过度亲密或要求重讲历史。",
            "出现明显风险词或要求用户重复既有背景。",
            "没有明显风险，但也缺少关系连续性证据。",
            "无陌生化风险，并通过具体措辞或处理方式保持稳定关系位置。",
        ),
        (
            "自然细节调用",
            "关键细节是否服务于心理理解，而不是机械背日志。",
            "堆砌细节、编造细节，或完全没有用细节理解用户状态。",
            "用少量细节但服务判断不足，或连接较弱。",
            "只调用必要细节，并服务情绪、边界或下一步判断。",
        ),
        (
            "记忆误用",
            "是否错误调用过期、无关、不可读或不存在的记忆。",
            "错误调用或编造记忆。",
            "轻微过度复述，或记忆边界说明不足。",
            "克制调用，清楚区分已知、推测和不能补的空白。",
        ),
    ]


def _scoring_logic_summary_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "评分输入",
            "LLM judge 只读取 conversation_log 中带 tom_dimensions 的 targeted probe turn；judge case 不给 BEI/gold label。",
            "每日开场和自然 follow-up 只用于建立上下文，不直接进入当前 ToM 均分。",
        ),
        (
            "评分对象",
            "同一个 probe turn 下分别读取 M0/M1/M2/M3 的 assistant_answer，但 judge prompt 只暴露 Condition A/B/C/D。",
            "同一用户输入下比较不同记忆权限的回答，避免把用户问题差异混进模型差异。",
        ),
        (
            "评分维度",
            "每条 probe 只评它声明的 tom_dimensions；LLM judge 按这些维度逐项给 0-2 分。",
            "例如关系边界题会重点评关系期待、陌生化和记忆误用，情绪校准题会重点评隐含意图和情绪状态。",
        ),
        (
            "证据来源",
            "LLM judge 必须为每个维度引用 assistant_answer 中的 evidence_quote，并给出 reason。",
            "主评测不再依赖关键词命中，而是要求裁判说明回答为什么满足或不满足该维度。",
        ),
        (
            "风险来源",
            "LLM judge 输出 failure_types：memory_absence、memory_misuse、memory_overuse、fabrication、alienation、instruction_only_success。",
            "这些风险用来发现没接旧语境、记忆误用、机械堆细节、编造、陌生化和只服从显性指令等失效表现。",
        ),
        (
            "最终输出",
            "输出每条回答的 tom_score、各维度 0-2 分、证据引用、理由、confidence、failure_types 和低分样例。",
            "报告主结论来自 LLM judge 输出；原始回答仍保留在 conversation_log 中，可回看复核。",
        ),
        (
            "规则辅助",
            "原规则评分器仍可离线运行，但只作为 triage 对照，不作为主结论。",
            "当 LLM judge 与规则评分差异很大时，差异样例应进入人工复核。",
        ),
    ]


def _single_answer_scoring_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "1. 过滤 turn",
            "如果一轮用户输入没有 tom_dimensions，LLM judge 直接跳过。",
            "保证当前 ToM 分数只来自定向测试问题，不混入普通聊天轮次。",
        ),
        (
            "2. 逐 variant 评分",
            "对同一 message_id 下的 M0/M1/M2/M3 回答分别构造 judge case；prompt 内只显示 Condition A/B/C/D。",
            "保留同题对照，同时避免裁判因组名产生预设。",
        ),
        (
            "3. 构造 judge case",
            "case 包含用户问题、tom_dimensions、rubric、盲化记忆条件说明、同一 variant 的前文上下文和 assistant_answer。",
            "裁判不能看到 BEI、gold strategy、高低分行为标签，也不应脑补未提供历史。",
        ),
        (
            "4. 维度打分",
            "LLM judge 对每个相关维度给 0-2 分，并必须输出 evidence_quote 和 reason。",
            "0 表示失败；1 表示部分识别；2 表示明确识别并转化为回应策略。",
        ),
        (
            "5. 风险标记",
            "LLM judge 同时标记记忆缺失、记忆误用、记忆过用、编造、陌生化和只服从显性指令。",
            "这些 failure_types 不直接替代维度分，但用于定位需要人工复核的样例。",
        ),
        (
            "6. 单题 ToM 分",
            "把本题相关维度的 0-2 分求平均，再换算成百分制：平均维度分 / 2 * 100。",
            "如果某题只声明 3 个维度，就只按这 3 个维度计算；不声明的维度不参与分母。",
        ),
        (
            "7. 实验组均分",
            "M0/M1/M2/M3 各自把所有被评分 probe 的 tom_score 求平均。",
            "这个均分是当前样例日志的 ToM triage 均分，不是严谨统计结论。",
        ),
        (
            "8. 低分样例",
            "按 tom_score 排出低分样例，并保留 judge 理由、置信度和回答摘录。",
            "低分样例比单个均分更适合进入人工复核。",
        ),
    ]


def _scoring_review_rows() -> list[tuple[Any, ...]]:
    return [
        (
            "与当前报告口径是否一致",
            "一致。当前主结论来自严格版 LLM-as-judge，规则评分降级为辅助诊断。",
            "继续保持 ToM 评分和事实细节审计分开；后续 memory audit 另起指标。",
        ),
        (
            "本轮已收紧",
            "评分固定为严格 0-2：1 分代表部分识别，2 分只给证据充分且转化为回应策略的回答。",
            "同时加入 response_format JSON 输出、解析失败重试、failure_types taxonomy，以及风险触发后的维度封顶。",
        ),
        (
            "当前效果",
            "新版结构能区分规则 triage、LLM judge 和人工复核，并把错误类型单独统计。",
            "正式结论应来自新 run 的 M0/M1/M2/M3 同题对照，而不是旧样例分数。",
        ),
        (
            "当前分数为什么仍只能是示例",
            "正式分数必须来自新版 36 题、四组同题运行、LLM judge 和盲化人工抽样复核。",
            "正式汇报模型差异前，应固定参数、重跑 M0/M1/M2/M3，再对低分/高分/分歧样例做人审。",
        ),
        (
            "下一版评分建议",
            "保留二阶段评审：先单答盲评，再按同一 probe 的四组回答做分歧复核，并要求说明差异。",
            "这样可以提高对不同记忆层级微小质量差异的敏感度。",
        ),
    ]


def _variant_summary_rows(tom_evaluation: dict[str, Any] | None) -> list[tuple[Any, ...]]:
    if not tom_evaluation:
        return []
    rows = []
    for variant_name, item in sorted(
        tom_evaluation.get("summary", {}).get("variants", {}).items()
    ):
        rows.append(
            (
                variant_name,
                item.get("turn_count", 0),
                f'{float(item.get("average_tom_score", 0.0)):.1f}',
                item.get("alienation_error_count", 0),
                item.get("ask_repeat_error_count", 0),
                item.get("generic_comfort_count", 0),
            )
        )
    return rows


def _llm_variant_summary_rows(llm_tom_evaluation: dict[str, Any]) -> list[tuple[Any, ...]]:
    rows = []
    for variant_name, item in sorted(
        llm_tom_evaluation.get("summary", {}).get("variants", {}).items()
    ):
        rows.append(
            (
                variant_name,
                item.get("turn_count", 0),
                f'{float(item.get("average_tom_score", 0.0)):.1f}',
                f'{float(item.get("average_confidence", 0.0)):.2f}',
                item.get("needs_human_review_count", 0),
                item.get("flag_count", 0),
            )
        )
    return rows


def _llm_dimension_average_rows(llm_tom_evaluation: dict[str, Any]) -> list[tuple[Any, ...]]:
    rows = []
    dimension_order = [
        "hidden_intent_recognition",
        "emotional_state_recognition",
        "relationship_expectation_recognition",
        "shared_context_invocation",
        "alienation_error_rate",
        "natural_detail_use",
        "memory_misuse",
    ]
    for variant_name, item in sorted(
        llm_tom_evaluation.get("summary", {}).get("dimension_averages", {}).items()
    ):
        rows.append(
            (
                variant_name,
                *[
                    f"{float(item.get(dimension, 0.0)):.2f}"
                    for dimension in dimension_order
                ],
            )
        )
    return rows


def _llm_lowest_example_rows(llm_tom_evaluation: dict[str, Any]) -> list[tuple[Any, ...]]:
    rows = []
    examples = llm_tom_evaluation.get("summary", {}).get("lowest_scoring_examples", [])
    for example in examples[:8]:
        rows.append(
            (
                example.get("variant", ""),
                example.get("message_id", ""),
                f'{float(example.get("tom_score", 0.0)):.1f}',
                f'{float(example.get("confidence", 0.0)):.2f}',
                example.get("overall_reason", ""),
            )
        )
    return rows


def _dimension_average_rows(tom_evaluation: dict[str, Any]) -> list[tuple[Any, ...]]:
    rows = []
    dimension_order = [
        "hidden_intent_recognition",
        "emotional_state_recognition",
        "relationship_expectation_recognition",
        "shared_context_invocation",
        "alienation_error_rate",
        "natural_detail_use",
        "memory_misuse",
    ]
    for variant_name, item in sorted(
        tom_evaluation.get("summary", {}).get("dimension_averages", {}).items()
    ):
        rows.append(
            (
                variant_name,
                *[
                    f"{float(item.get(dimension, 0.0)):.2f}"
                    for dimension in dimension_order
                ],
            )
        )
    return rows


def _lowest_example_rows(tom_evaluation: dict[str, Any]) -> list[tuple[Any, ...]]:
    rows = []
    examples = tom_evaluation.get("summary", {}).get("lowest_scoring_examples", [])
    for example in examples[:8]:
        rows.append(
            (
                example.get("variant", ""),
                example.get("message_id", ""),
                f'{float(example.get("tom_score", 0.0)):.1f}',
                example.get("answer_excerpt", ""),
            )
        )
    return rows


def _tom_dimension_coverage_rows(probe_summary: dict[str, Any]) -> list[tuple[Any, ...]]:
    counts = probe_summary.get("tom_dimension_counts", {})
    dimensions = [
        (
            "hidden_intent_recognition",
            "隐含意图识别",
            "测试 AI 是否听出用户字面表达背后的真实诉求。",
        ),
        (
            "emotional_state_recognition",
            "情绪状态识别",
            "测试 AI 是否识别疲惫、失落、自我怀疑、不安等状态。",
        ),
        (
            "relationship_expectation_recognition",
            "关系期待识别",
            "测试 AI 是否知道用户期待的是熟悉关系回应，而不是陌生客服。",
        ),
        (
            "shared_context_invocation",
            "共同语境调用",
            "测试 AI 是否能自然接上此前形成的处理方式。",
        ),
        (
            "alienation_error_rate",
            "陌生化错误率",
            "测试 AI 是否避免客服化、过度亲密、角色化或要求用户重讲历史。",
        ),
        (
            "natural_detail_use",
            "自然细节调用",
            "测试 AI 是否把关键细节用于理解心理状态，而不是机械背日志。",
        ),
        (
            "memory_misuse",
            "记忆误用",
            "测试 AI 是否避免错误、过期、无关、不可读或不存在的记忆调用。",
        ),
    ]
    return [
        (
            f"{label} ({dimension})",
            counts.get(dimension, 0),
            description,
        )
        for dimension, label, description in dimensions
    ]


def _tom_question_design_review_rows(probe_plan: dict[str, Any]) -> list[tuple[Any, ...]]:
    summary = probe_plan.get("summary", {})
    counts = summary.get("tom_dimension_counts", {})
    probe_count = int(summary.get("probe_count", 0))
    weak_dimensions = [
        _dimension_label(dimension)
        for dimension in [
            "shared_context_invocation",
            "alienation_error_rate",
            "relationship_expectation_recognition",
        ]
        if counts.get(dimension, 0) < max(4, probe_count // 3)
    ]
    weak_text = "、".join(weak_dimensions) if weak_dimensions else "暂无明显短板"
    return [
        (
            "总体是否需要重写",
            "已按新版结构扩展为 36 条；当前重点是验证覆盖和运行一致性。",
            "后续只做小幅均衡修正，避免在模型逻辑前反复改题集结构。",
        ),
        (
            "覆盖是否均衡",
            (
                "当前隐含意图识别覆盖较高，情绪状态、自然细节和记忆误用也已补强；"
                f"相对薄弱的是：{weak_text}。"
            ),
            "如果继续补题，优先补依赖题/主问题配对和低覆盖维度，避免继续堆隐含意图题。",
        ),
        (
            "问题表达是否符合 ToM",
            "大部分问题采用含蓄表达，例如“怕你变标准答案”“不想从头解释”“我是不是被情绪带走”。",
            "继续避免直接问“你记得吗”，改用关系期待、状态校准和共同语境暗示来触发 ToM。",
        ),
        (
            "建议新增题型",
            "当前已包含 current understanding、memory invocation、state transformation、relational boundary、alienation、natural detail。",
            "正式运行前只需确认每条核心主题至少有当前理解题和跨天变化/记忆调用题。",
        ),
    ]


def _dimension_label(dimension: str) -> str:
    labels = {
        "hidden_intent_recognition": "隐含意图识别",
        "emotional_state_recognition": "情绪状态识别",
        "relationship_expectation_recognition": "关系期待识别",
        "shared_context_invocation": "共同语境调用",
        "alienation_error_rate": "陌生化错误率",
        "natural_detail_use": "自然细节调用",
        "memory_misuse": "记忆误用",
    }
    return f"{labels.get(dimension, dimension)} ({dimension})" if dimension else ""


def _table(headers: list[str], rows: list[tuple[Any, ...]], *, large: bool = False) -> str:
    class_name = ' class="large-table"' if large else ""
    head = "".join(f"<th>{_e(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{_e(value)}</td>" for value in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<div class=\"table-wrap\"><table{class_name}><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _css() -> str:
    return """
    :root {
      color-scheme: light;
      --text: #1f2933;
      --muted: #667085;
      --line: #d9e2ec;
      --head: #eef5f8;
      --accent: #0f766e;
      --code: #f4f7f9;
      --quote: #f0fdfa;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: #ffffff;
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
      line-height: 1.65;
    }
    .page {
      width: min(1180px, calc(100% - 48px));
      margin: 0 auto;
      padding: 40px 0 64px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.25;
      letter-spacing: 0;
    }
    h2 {
      margin: 36px 0 14px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
      font-size: 22px;
      letter-spacing: 0;
    }
    h3 {
      margin: 24px 0 10px;
      font-size: 17px;
      letter-spacing: 0;
    }
    p { margin: 10px 0; }
    ul { margin: 8px 0 8px 24px; padding: 0; }
    li { margin: 5px 0; }
    code {
      padding: 2px 5px;
      border-radius: 4px;
      background: var(--code);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.92em;
    }
    .meta {
      margin-bottom: 24px;
      color: var(--muted);
    }
    .note {
      padding: 10px 12px;
      border-left: 4px solid var(--accent);
      background: var(--quote);
    }
    blockquote {
      margin: 14px 0;
      padding: 14px 18px;
      border-left: 4px solid var(--accent);
      background: var(--quote);
    }
    .table-wrap {
      width: 100%;
      overflow-x: auto;
      margin: 12px 0 22px;
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      border-right: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
    }
    th:last-child, td:last-child { border-right: 0; }
    tr:last-child td { border-bottom: 0; }
    th {
      background: var(--head);
      font-weight: 650;
      white-space: nowrap;
    }
    .large-table td:nth-child(1),
    .large-table td:nth-child(4) {
      white-space: nowrap;
      text-align: center;
    }
    .large-table td:nth-child(5),
    .large-table td:nth-child(7),
    .large-table td:nth-child(8),
    .large-table td:nth-child(9),
    .large-table td:nth-child(10) {
      min-width: 360px;
    }
    @media print {
      .page { width: auto; padding: 20px; }
      .table-wrap { overflow: visible; }
      table { font-size: 11px; }
      h2 { break-after: avoid; }
      tr { break-inside: avoid; }
    }
    """


if __name__ == "__main__":
    main()
