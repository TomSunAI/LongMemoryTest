#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


FIELD_LABELS = {
    "age_range_options": "年龄范围",
    "occupation_options": "职业选项",
    "occupation_status_options": "职业状态",
    "education_options": "教育背景",
    "family_structure_options": "家庭结构",
    "life_stage_options": "人生阶段",
    "economic_condition_options": "经济状态",
    "social_support_options": "社会支持",
    "likely_life_domains": "高概率生活领域",
    "long_term_goal_options": "长期目标",
    "communication_style_options": "沟通风格",
    "stress_response_options": "压力反应",
    "decision_style_options": "决策风格",
    "memory_relevant_trait_options": "记忆相关特征",
    "excluded_event_domains": "排除事件领域",
}


ARCHETYPE_CN = {
    "A01_early_career_renter": {
        "label": "早期职业阶段的城市租房者",
        "description": (
            "有稳定但收入不高的工作，正在应对房租、通勤、职场适应和本地支持薄弱。"
        ),
        "basis": [
            "适合生成初入城市或早期职业阶段的人物，不适合退休、育婴或主要照护长辈事件。",
            "核心压力来自工作适应、住房成本、预算紧张、通勤和本地社交支持不足。",
            "记忆测试重点是区分真实风险与想象风险，并承接具体、低成本的下一步计划。",
        ],
    },
    "A02_service_emotional_labor": {
        "label": "承受情绪劳动的一线服务人员",
        "description": (
            "从事服务或客户接触工作，经常吸收顾客情绪，并担心投诉、被责备或绩效评价。"
        ),
        "basis": [
            "适合生成酒店、餐饮、客服、门店等一线服务场景。",
            "核心压力来自客户冲突、边界表达、绩效压力、收入和住房稳定性。",
            "记忆测试重点是是否记住用户不需要空泛安慰，而需要事实拆解和边界措辞。",
        ],
    },
    "A03_gig_worker_parent": {
        "label": "收入波动且承担育儿压力的平台劳动者家长",
        "description": (
            "以平台或灵活工作为主，收入随订单变化，同时要平衡工作时长、家庭需求、"
            "孩子照护和身体精力。"
        ),
        "basis": [
            "适合生成外卖、网约车、零工等收入不稳定但需要照顾孩子的人物。",
            "核心压力来自订单收入、照护安排、时间不可控和身体消耗。",
            "记忆测试重点是能否在钱、孩子和精力之间给出真实可执行的优先级。",
        ],
    },
    "A04_small_business_owner": {
        "label": "在客流、现金流和家庭时间之间平衡的小生意经营者",
        "description": (
            "经营小店或服务型生意，面对客流不稳定、租金压力和家庭期待。"
        ),
        "basis": [
            "适合生成小餐馆、便利店、美容美发、维修店等小经营主体。",
            "核心压力来自现金流、房租、顾客关系、家庭时间和个人价值感。",
            "记忆测试重点是区分经营风险与自我否定，并延续此前的现金流处理策略。",
        ],
    },
    "A05_single_parent_service_worker": {
        "label": "独自育儿且从事服务工作的单亲家长",
        "description": (
            "有学龄或学前孩子，既要做服务工作，又要处理学校安排、有限预算和情绪责任。"
        ),
        "basis": [
            "适合生成单亲、服务业、学校安排、住房和钱高度耦合的人物。",
            "核心压力来自工作排班、孩子学校稳定性、照护备份和预算限制。",
            "记忆测试重点是能否同时保留照顾孩子和保护自身边界，而不是只给道德化建议。",
        ],
    },
    "A06_midlife_caregiver": {
        "label": "同时维持工作和长辈照护的中年照护协调者",
        "description": (
            "中年工作者，需要帮助照顾年迈父母或亲属，同时维持工作和家庭稳定。"
        ),
        "basis": [
            "适合生成长辈照护、医疗流程、兄弟姐妹分工、费用和家庭协调事件。",
            "核心压力来自责任边界、医疗事实、照护安排和家庭成员意见不一致。",
            "记忆测试重点是区分事实、物流和家庭协商，避免把照护责任无限扩大。",
        ],
    },
    "A07_unemployed_job_seeker": {
        "label": "正在重建信心的中期职业求职者",
        "description": (
            "失去或离开工作后，正在寻找稳定工作，同时承受金钱压力和自我价值感波动。"
        ),
        "basis": [
            "适合生成失业、简历、面试受挫、技能更新和日常开支压力。",
            "核心压力来自收入中断、比较心理、拒绝后的羞耻感和行动停滞。",
            "记忆测试重点是把求职失败与个人价值分开，并推动小步重启。",
        ],
    },
    "A08_shift_worker_family_pressure": {
        "label": "排班不稳定且家庭压力较高的轮班工作者",
        "description": (
            "工作时间不规律，睡眠、家庭沟通和日常节奏经常被打断。"
        ),
        "basis": [
            "适合生成夜班、倒班、疲劳、家庭误解、健康习惯和临时排班事件。",
            "核心压力来自睡眠剥夺、体力消耗、收入需求和家庭期待之间的冲突。",
            "记忆测试重点是注意低能量状态，给短、现实、不过载的回应。",
        ],
    },
    "A09_retirement_adjustment": {
        "label": "刚退休、正在重建生活节奏和身份感的人",
        "description": (
            "刚退休不久，生活条件稳定但不宽裕，正在重建日常节奏、社交联系和有用感。"
        ),
        "basis": [
            "适合生成退休身份转换、社区参与、成人子女联系节奏和健康日常。",
            "核心压力来自时间结构消失、孤独、克制表达需求和不想成为负担。",
            "记忆测试重点是延续低负担的日常锚点，而不是把退休问题泛化成鸡汤。",
        ],
    },
    "A10_international_student_admin_pressure": {
        "label": "承受行政手续和适应压力的留学生",
        "description": (
            "离家在外学习，需要处理学业、文件、金钱、本地支持薄弱和远距离关系。"
        ),
        "basis": [
            "适合生成签证/学校文件、搬迁适应、学业压力、预算和异地关系事件。",
            "核心压力来自规则不确定、支持系统薄弱、费用压力和跨文化生活适应。",
            "记忆测试重点是分清已知规则与猜测，并提供步骤化行政处理路径。",
        ],
    },
    "A11_adult_child_boundary_family": {
        "label": "与成年子女重新协商边界的中年父母",
        "description": (
            "成年子女回家或仍有经济/情感依赖，带来边界和责任张力。"
        ),
        "basis": [
            "适合生成成年子女经济依赖、同住冲突、亲子边界和家庭钱的问题。",
            "核心压力来自爱与责任、帮助与纵容、夫妻意见差异之间的拉扯。",
            "记忆测试重点是同时保留关心和限制，避免把设边界说成冷漠。",
        ],
    },
    "A12_early_parenthood_return_to_work": {
        "label": "育婴后重返工作的早期父母",
        "description": (
            "新手父母试图回到工作中，同时处理婴儿照护、睡眠不足、家务协调和钱的压力。"
        ),
        "basis": [
            "适合生成育婴、夜间照护、返工、伴侣分工、托育安排和睡眠压力。",
            "核心压力来自照护强度、工作恢复、家庭分工和预算收紧。",
            "记忆测试重点是识别低睡眠状态下的承受边界，不给复杂计划。",
        ],
    },
}


TERM_CN = {
    "20s": "20多岁",
    "30s": "30多岁",
    "40s": "40多岁",
    "50s": "50多岁",
    "60s": "60多岁",
    "70s": "70多岁",
    "employed": "在职",
    "unemployed": "失业或待业",
    "retired": "退休",
    "part_time": "兼职",
    "self_employed": "自雇",
    "student": "学生",
    "employed_shift_work": "轮班在职",
    "returning_from_parental_leave": "育儿假后返岗",
    "vocational college graduate": "高职/职业学院毕业",
    "associate degree": "副学士或大专学历",
    "bachelor's degree": "本科学历",
    "master's student": "硕士在读",
    "undergraduate student": "本科在读",
    "high school graduate": "高中毕业",
    "vocational training": "职业培训背景",
    "single, rents a room": "单身，租住单间",
    "single, lives with roommates": "单身，与室友合租",
    "newly married, no children": "新婚，无子女",
    "married, no children": "已婚，无子女",
    "married with one child": "已婚，有一个孩子",
    "married with one preschool child": "已婚，有一个学前儿童",
    "married with one school-age child": "已婚，有一个学龄儿童",
    "married with an infant": "已婚，有一个婴儿",
    "partnered with an infant": "有伴侣，共同照顾婴儿",
    "single parent with one preschool child": "单亲，有一个学前儿童",
    "single parent with one school-age child": "单亲，有一个学龄儿童",
    "single parent with one elementary-school child": "单亲，有一个小学阶段孩子",
    "single parent with an infant and some family help": "单亲，有婴儿且有少量家人帮助",
    "single, lives alone": "单身，独居",
    "single, family abroad": "单身，家人在海外",
    "single, temporarily living with family": "单身，暂时与家人同住",
    "lives with roommates abroad": "在海外与室友合住",
    "lives with family": "与家人同住",
    "living with extended family": "与大家庭同住",
    "married, household depends on two incomes": "已婚，家庭依赖双收入",
    "married, caring for an elderly parent part-time": "已婚，兼职照护年迈父母",
    "married, coordinates care with siblings": "已婚，与兄弟姐妹协调照护",
    "widowed, adult children live in other cities": "丧偶，成年子女在外地",
    "married, adult children live elsewhere": "已婚，成年子女不在身边",
    "married, adult child recently returned home": "已婚，成年子女近期回家同住",
    "married, adult child asks for repeated help": "已婚，成年子女反复需要帮助",
    "single parent, adult child still financially dependent": "单亲，成年子女仍有经济依赖",
    "administration": "行政手续",
    "adult_child_boundary": "成年子女边界",
    "business": "小生意经营",
    "childcare": "儿童照护",
    "community": "社区生活",
    "commuting": "通勤",
    "consumer_issue": "消费纠纷",
    "daily_life": "日常生活",
    "digital_life": "数字生活",
    "education": "教育/学业",
    "eldercare": "长辈照护",
    "family": "家庭",
    "finance": "财务",
    "gig_work": "平台/零工工作",
    "health_routine": "健康日常",
    "housing": "住房",
    "infant_care": "婴儿照护",
    "job_search": "求职",
    "learning": "学习转型",
    "neighborhood": "邻里",
    "personal_boundary": "个人边界",
    "personal_planning": "个人规划",
    "pet_care": "宠物照护",
    "relationship": "亲密/重要关系",
    "relocation": "搬迁适应",
    "retirement": "退休适应",
    "self_worth": "自我价值感",
    "social_connection": "社会连接",
    "visa_administration": "签证/留学行政",
    "work": "工作",
    "work_family_intersection": "工作-家庭交叉",
    "family_coordination": "家庭协调",
    "family_connection": "家庭连接",
    "customer_conflict": "客户冲突",
    "customer_relationship": "客户关系",
    "housing_rent": "住房/租金",
    "sleep": "睡眠",
    "school": "学校安排",
    "career": "职业发展",
    "healthcare_navigation": "医疗流程导航",
    "skill_learning": "技能学习",
    "identity_transition": "身份转换",
    "plain": "朴素直接",
    "plainspoken": "直白表达",
    "cautious": "谨慎",
    "detail-seeking": "重视细节",
    "self-questioning": "容易自我追问",
    "direct": "直接",
    "polite": "礼貌克制",
    "guarded": "有所保留",
    "brief when ashamed": "感到羞耻时话少",
    "emotionally expressive": "情绪表达较外显",
    "emotionally restrained": "情绪表达较克制",
    "compressed": "表达压缩",
    "concrete": "偏具体",
    "short": "偏短句",
    "structured": "偏结构化",
    "context-rich": "会补充上下文",
    "practical": "务实",
    "pragmatic": "现实取向",
    "solution-first": "先找解决办法",
    "step-by-step": "偏步骤化",
    "risk-averse": "规避风险",
    "budget-aware": "预算敏感",
    "evidence-seeking": "重视证据",
    "cashflow-sensitive": "现金流敏感",
    "responsibility-driven": "责任感驱动",
    "resource-constrained": "受资源限制",
    "rule-conscious": "重视规则",
    "planning-heavy": "计划倾向强",
    "tired": "疲惫状态明显",
    "energy-limited": "精力有限",
    "careful": "谨慎细致",
    "approval-seeking": "容易寻求确认",
    "boundary-hesitant": "边界表达犹豫",
    "confidence-dependent": "信心容易受影响",
    "duty-oriented": "责任/义务取向",
    "protective": "保护性强",
    "risk-aware": "风险意识强",
    "cashflow-driven": "受现金流驱动",
    "risk-management-oriented": "风险管理取向",
    "administrative assistant": "行政助理",
    "junior office clerk": "初级办公室文员",
    "junior software engineer": "初级软件工程师",
    "sales assistant": "销售助理",
    "property service assistant": "物业服务助理",
    "hotel front desk worker": "酒店前台",
    "restaurant server": "餐厅服务员",
    "call center customer service agent": "呼叫中心客服",
    "retail staff": "零售店员",
    "clinic receptionist": "诊所前台",
    "delivery driver": "配送员",
    "ride-hailing driver": "网约车司机",
    "part-time courier": "兼职配送员",
    "platform-based service worker": "平台服务从业者",
    "small restaurant owner": "小餐馆经营者",
    "convenience store owner": "便利店经营者",
    "barber shop owner": "理发店经营者",
    "beauty salon owner": "美容店经营者",
    "home repair shop owner": "家电/维修店经营者",
    "school cafeteria worker": "学校食堂工作人员",
    "supermarket cashier": "超市收银员",
    "office assistant": "办公室助理",
    "community worker": "社区工作者",
    "office clerk": "办公室文员",
    "junior accountant": "初级会计",
    "factory line supervisor": "工厂产线主管",
    "hospital nurse": "护士",
    "security guard": "保安",
    "warehouse shift worker": "仓库轮班工人",
    "retail shift worker": "零售轮班员工",
    "convenience store night-shift worker": "便利店夜班员工",
    "unemployed former office assistant": "待业，曾任办公室助理",
    "unemployed former restaurant manager": "待业，曾任餐厅经理",
    "unemployed former sales associate": "待业，曾任销售",
    "unemployed former warehouse worker": "待业，曾任仓库员工",
    "recently retired office clerk": "刚退休的办公室文员",
    "recently retired bus driver": "刚退休的公交司机",
    "recently retired shop worker": "刚退休的店员",
    "recently retired civil engineer": "刚退休的土木工程师",
    "international undergraduate student": "国际本科生",
    "international master's student": "国际硕士生",
    "exchange student with part-time work": "有兼职的交换生",
    "accounting clerk": "会计文员",
    "apartment property assistant": "公寓物业助理",
    "shop manager": "门店经理",
    "product manager": "产品经理",
}


STATIC_CN = {
    "Support ordinary-life, public-facing, non-autobiographical persona generation.": (
        "支持普通生活、面向大众、非自传式的人物生成。"
    ),
    "Cover diverse occupations, family structures, life stages, and stress patterns.": (
        "覆盖多样的职业、家庭结构、人生阶段和压力模式。"
    ),
    "Keep personas plausible enough for persistent event-line construction.": (
        "保证人物足够可信，能够承载跨天持续事件线。"
    ),
    "Avoid over-concentration around researcher / young child / paper deadline / spouse coordination trajectories.": (
        "避免过度集中到研究者、幼儿、论文截稿、伴侣分工这类单一轨迹。"
    ),
    "political affiliation": "政治立场",
    "religion": "宗教信仰",
    "race or ethnicity unless explicitly required by a study design": (
        "种族或族裔，除非研究设计明确需要"
    ),
    "medical or psychiatric diagnosis": "医学或精神诊断",
    "precise real address": "精确真实地址",
    "real person identity": "真实人物身份",
    "highly identifiable private details": "高度可识别的私人细节",
    "At least 4 age ranges in a 20-persona batch.": "20 人批次中至少覆盖 4 个年龄段。",
    "At least 6 occupation types in a 20-persona batch.": "20 人批次中至少覆盖 6 种职业。",
    "At least 5 family structures in a 20-persona batch.": "20 人批次中至少覆盖 5 种家庭结构。",
    "No more than 25% of personas should be students or researchers.": (
        "学生或研究者比例不超过 25%。"
    ),
    "No more than 35% of personas should have child-related life domains.": (
        "儿童相关生活领域的人物比例不超过 35%。"
    ),
}


SENSITIVE_POLICY_CN = {
    "gender": "性别",
    "health_status": "健康状态",
    "family_details": "家庭细节",
    "income": "收入",
    "optional; default to unprovided unless needed for a specific experimental design": (
        "可选；除非特定实验设计需要，否则默认不提供。"
    ),
    "do not assign diagnosis; only ordinary fatigue, stress, or routine pressure may be described": (
        "不分配诊断；只描述普通疲劳、压力或日常负担。"
    ),
    "use general structure only; avoid excessive private details": (
        "只使用一般结构，避免过度私人化细节。"
    ),
    "use broad economic condition, not exact salary": "使用宽泛经济状态，不写精确薪资。",
}


REQUIRED_FIELD_CN = {
    "persona_id": "人物 ID",
    "source_archetype": "来源人物原型",
    "age_range": "年龄范围",
    "occupation": "职业",
    "occupation_status": "职业状态",
    "education_background": "教育背景",
    "family_structure": "家庭结构",
    "life_stage": "人生阶段",
    "economic_condition": "经济状态",
    "social_support": "社会支持",
    "primary_life_domains": "主要生活领域",
    "long_term_goals": "长期目标",
    "communication_style": "沟通风格",
    "stress_response": "压力反应",
    "decision_style": "决策风格",
    "memory_relevant_traits": "记忆相关特征",
    "sensitive_fields": "敏感字段",
}


IMPLEMENTATION_DOC_PATH = "/Users/tom/Desktop/Archetype_Guided_Persona_Event_Sampling_Implementation.docx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate persona archetype pool HTML report.")
    parser.add_argument(
        "--persona-archetype-pool",
        type=Path,
        default=(
            REPO_ROOT
            / "long_memory_experiment/data/sampling/persona_archetype_pool_v0.1.json"
        ),
    )
    parser.add_argument(
        "--realism-report",
        type=Path,
        default=(
            REPO_ROOT
            / "long_memory_experiment/data/generated/realism_validation_report.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs/persona_archetype_pool_v0_1_report.html",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pool = _load_json(args.persona_archetype_pool)
    realism = _load_json(args.realism_report) if args.realism_report.exists() else {}
    html_text = render_report(
        pool=pool,
        realism_report=realism,
        pool_path=args.persona_archetype_pool,
        realism_path=args.realism_report,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def render_report(
    *,
    pool: dict[str, Any],
    realism_report: dict[str, Any],
    pool_path: Path,
    realism_path: Path,
) -> str:
    archetypes = [item for item in pool.get("archetypes", []) if isinstance(item, dict)]
    feasibility = {
        str(item.get("archetype_id")): item
        for item in realism_report.get("pool_report", {}).get("archetype_feasibility", [])
        if isinstance(item, dict)
    }
    summary = realism_report.get("pool_report", {}).get("summary", {})
    goals = [str(item) for item in pool.get("design_goals", [])]
    global_rules = pool.get("global_generation_rules", {})
    sampling = pool.get("sampling_config_recommendation", {})
    implementation_basis = render_implementation_basis()

    archetype_cards = "".join(
        render_archetype_card(
            item,
            feasibility.get(str(item.get("archetype_id")), {}),
        )
        for item in archetypes
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>人物原型池 v0.1 中文审阅报告</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #5b6670;
      --line: #d8e0e7;
      --soft: #f6f8fb;
      --accent: #1558d6;
      --ok: #137333;
      --warn: #8a5a00;
      --chip: #eef4ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #fff;
      font: 15px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1220px; margin: 0 auto; padding: 34px 26px 72px; }}
    h1, h2, h3 {{ margin: 0; line-height: 1.25; }}
    h1 {{ font-size: 30px; }}
    h2 {{
      margin-top: 34px;
      padding-top: 22px;
      border-top: 1px solid var(--line);
      font-size: 22px;
    }}
    h3 {{ margin-top: 18px; font-size: 17px; }}
    p {{ margin: 8px 0; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0 20px;
      table-layout: fixed;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 9px;
      vertical-align: top;
      word-break: break-word;
    }}
    th {{ background: var(--soft); text-align: left; font-weight: 650; }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: #edf1f5;
      padding: 1px 4px;
      border-radius: 4px;
    }}
    .meta {{ color: var(--muted); font-size: 13px; margin-top: 10px; }}
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
    .doc-note {{
      margin: 12px 0 16px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--muted);
    }}
    .tech-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin: 12px 0 18px;
    }}
    .tech-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      background: #fff;
    }}
    .tech-card strong {{ display: block; margin-bottom: 5px; }}
    .flow {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0 18px;
    }}
    .flow-step {{
      min-height: 74px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      background: #fbfcfe;
    }}
    .flow-step code {{ display: inline-block; margin-bottom: 4px; }}
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
    .tag-muted {{
      background: #f4f6f8;
      border-color: var(--line);
      color: #374151;
    }}
    .archetype {{
      margin-top: 20px;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    .archetype-header {{
      padding: 14px 16px;
      background: #fbfcfe;
      border-bottom: 1px solid var(--line);
    }}
    .archetype-body {{ padding: 14px 16px 16px; }}
    .basis {{
      margin: 12px 0;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .basis ul {{ margin: 6px 0 0 20px; padding: 0; }}
    .basis li {{ margin: 3px 0; }}
    .field-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .field {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fff;
    }}
    .field-title {{ font-weight: 650; margin-bottom: 5px; }}
    details.raw-fields {{
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    details.raw-fields summary {{
      cursor: pointer;
      padding: 10px 12px;
      font-weight: 650;
      background: var(--soft);
    }}
    details.raw-fields .field-grid {{ padding: 12px; margin-top: 0; }}
    ul.compact {{ margin: 6px 0 0 20px; padding: 0; }}
    li {{ margin: 3px 0; }}
    @media (max-width: 900px) {{
      main {{ padding: 24px 14px 56px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .tech-grid {{ grid-template-columns: 1fr; }}
      .flow {{ grid-template-columns: 1fr; }}
      .field-grid {{ grid-template-columns: 1fr; }}
      table {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>人物原型池 v0.1 中文审阅报告</h1>
  <p class="meta">
    数据源：<code>{_esc(_rel(pool_path))}</code>；
    可行性报告：<code>{_esc(_rel(realism_path))}</code>
  </p>

  <section>
    <h2>总体结论</h2>
    <div class="grid">
      {_metric("人物原型", summary.get("archetype_count", len(archetypes)), "原型数量")}
      {_metric("事件类别", summary.get("event_category_count", "-"), "事件池规模")}
      {_metric("事件领域", summary.get("event_domain_count", "-"), "领域覆盖")}
      {_metric("可用原型", summary.get("archetypes_ready", "-"), "满足 P0 采样约束")}
    </div>
    <div class="callout">
      当前真实性检验状态：
      <span class="status-pass">{_esc(realism_report.get("status", "unknown"))}</span>。
      P0 含义：每类人物都有足够的兼容事件，
      可支持后续每人 4-6 条事件、
      至少 3 个事件领域、同领域最多 2 条，并保留非工作/家庭类事件余量。
    </div>
  </section>

  {implementation_basis}

  <section>
    <h2>生成标准依据</h2>
    <h3>设计目标</h3>
    {_list(goals, translate=True)}
    <h3>禁止生成内容</h3>
    {_list(global_rules.get("do_not_generate", []), translate=True)}
    <h3>敏感字段策略</h3>
    {_key_value_table(global_rules.get("sensitive_fields_policy", {}), translate=True)}
    <h3>Persona Instance 必填字段</h3>
    {_tags(global_rules.get("persona_instance_required_fields", []), field_key="required_field")}
    <h3>批量采样约束</h3>
    {_key_value_table(_sampling_table(sampling), translate=True)}
  </section>

  <section>
    <h2>12 个原型总览</h2>
    {render_overview_table(archetypes, feasibility)}
  </section>

  <section>
    <h2>逐项详细信息</h2>
    {archetype_cards}
  </section>
</main>
</body>
</html>
    """


def render_implementation_basis() -> str:
    techniques = [
        (
            "受控多样性",
            "人物差异来自 archetype 覆盖、事件领域覆盖和批量比例约束，而不是让大模型随机编故事。",
        ),
        (
            "人物-事件一致性",
            "事件必须匹配年龄、职业状态、家庭结构、经济状态和高概率生活领域；不匹配的候选事件要记录拒绝原因。",
        ),
        (
            "事件中心记忆",
            "事件类别不是聊天主题，而是会跨天延续的 persistent event object，后续才能形成事件线和探针绑定。",
        ),
        (
            "可复现采样",
            "使用 random_seed、候选数量、每人事件数、领域上限等配置，使同一实验批次可以复核和重跑。",
        ),
        (
            "三层真实性检验",
            "先做 hard rule，再做 domain diversity，再做 autobiography risk 检查；LLM sanity check 在 P0 中默认关闭。",
        ),
        (
            "全链路可审计",
            "采样候选、接受理由、拒绝理由、事件线、时间线、交互单元和 probe 绑定都要落盘。",
        ),
        (
            "场景边界",
            "daily interaction 只能使用 scene card 中允许的事实，follow-up 不能凭空引入新事实。",
        ),
        (
            "tau 合约",
            "最终实验对象是 tau=(z,T,L,I,P)，其中 z 是人物、T 是接受事件集合、L 是事件线、I 是日常交互、P 是探针计划。",
        ),
        (
            "同一 tau 下比较",
            "M0/M1/M2/M3 使用同一 tau，差异只来自记忆机制边界，而不是人物或事件不同。",
        ),
    ]
    tech_cards = "".join(
        "<div class='tech-card'>"
        f"<strong>{_esc(title)}</strong>"
        f"<p>{_esc(body)}</p>"
        "</div>"
        for title, body in techniques
    )

    flow_steps = [
        ("01", "sampled_personas.json", "从 12 类人物原型采样 z，保留 source_archetype。"),
        ("02", "candidate_event_sets.json", "按 compatible_archetypes 和领域分层抽取候选事件。"),
        ("03", "compatibility_report.json", "执行硬规则、领域多样性和自传风险检查。"),
        ("03", "accepted_persona_event_sets.json", "为每个人接受 4-6 条事件，形成 T。"),
        ("04", "event_lines.json", "把事件类别展开为 3-6 阶段的持续事件线 L。"),
        ("05", "timeline.json", "把事件线交织安排到 30/60 天时间轴。"),
        ("06", "daily_interaction_units.json", "生成受 scene boundary 约束的日常交互 I。"),
        ("07/08", "probe_plan + tau_contract", "生成探针 P，并汇总 tau=(z,T,L,I,P)。"),
    ]
    flow = "".join(
        "<div class='flow-step'>"
        f"<code>{_esc(step)}</code>"
        f"<strong>{_esc(output)}</strong>"
        f"<p>{_esc(description)}</p>"
        "</div>"
        for step, output, description in flow_steps
    )

    priority_rows = "".join(
        "<tr>"
        f"<th>{_esc(level)}</th>"
        f"<td>{_esc(scope)}</td>"
        f"<td>{_esc(output)}</td>"
        "</tr>"
        for level, scope, output in [
            (
                "P0",
                "人物采样、事件候选采样、人物-事件兼容性验证。",
                "sampled_personas / candidate_event_sets / compatibility_report / accepted sets。",
            ),
            (
                "P1",
                "把已接受事件转换成持续事件线，并安排跨天时间线。",
                "event_lines / timeline。",
            ),
            (
                "P2",
                "生成每日交互、目标探针和 tau 合约。",
                "daily_interaction_units / probe_plan / tau_contract。",
            ),
            (
                "P3",
                "生成 HTML/Markdown 报告和多样性统计。",
                "可审阅报告、批次分布、风险统计。",
            ),
        ]
    )

    acceptance_questions = [
        "每个人物能否追溯到明确的 source_archetype？",
        "每条接受事件为什么适配？被拒绝的候选事件为什么被拒绝？",
        "每个人物的事件是否覆盖至少 3 个领域，且同领域不超过 2 条？",
        "每条事件线是否有 3-6 次跨天出现，而不是一次性聊天主题？",
        "daily interaction 是否只使用 scene card 允许事实？",
        "probe 是否绑定到具体 event_line_id、event_stage 和 target_memory_type？",
        "M0 是否只写回 M0 回答，probe 是否保持 read-only？",
        "是否避免研究者、幼儿、论文截稿、伴侣分工等过度自传化组合？",
    ]

    return f"""
  <section>
    <h2>依据文档与关键技术</h2>
    <div class="doc-note">
      依据文档：<code>{_esc(IMPLEMENTATION_DOC_PATH)}</code>。
      本节提炼自你提供的
      <strong>Archetype-Guided Persona-Event Sampling 工程实现设计文档</strong>；
      这里不引用外部网页或额外文献。
    </div>
    <div class="callout">
      这套方案不是让大模型自由写完整故事，也不是手写固定人物和事件。
      “采样”指的是：从受控的人物原型池和事件类别池中，
      按随机种子、兼容关系、领域覆盖、数量上限和拒绝规则选择候选，
      再把接受/拒绝过程写成可审计记录。
    </div>

    <h3>工程目标</h3>
    {_list([
        "避免实验轨迹围绕一个真实个人或单一 Wendy 式故事线展开。",
        "保持普通生活真实性：工作、钱、住房、家庭、照护、关系、睡眠、行政手续、学习与转型。",
        "事件必须是跨天持续对象，而不是日/session 摘要或泛泛话题。",
        "人物-事件组合必须可解释：为什么接受、为什么拒绝，都要落盘。",
        "M0/M1/M2/M3 使用同一 tau，保证比较变量是记忆机制，而不是样本差异。",
    ])}

    <h3>方法框架</h3>
    <div class="flow">{flow}</div>

    <h3>关键技术</h3>
    <div class="tech-grid">{tech_cards}</div>

    <h3>P0-P3 实施优先级</h3>
    <table>
      <thead><tr><th>阶段</th><th>工作范围</th><th>主要产物</th></tr></thead>
      <tbody>{priority_rows}</tbody>
    </table>

    <h3>验收标准</h3>
    {_list(acceptance_questions)}
  </section>
"""


def render_overview_table(
    archetypes: list[dict[str, Any]],
    feasibility: dict[str, dict[str, Any]],
) -> str:
    rows = []
    for item in archetypes:
        archetype_id = str(item.get("archetype_id"))
        stats = feasibility.get(archetype_id, {})
        rows.append(
            "<tr>"
            f"<td><code>{_esc(archetype_id)}</code></td>"
            f"<td>{_esc(_archetype_label(item))}</td>"
            f"<td>{_tags(item.get('likely_life_domains', []), field_key='event_domain')}</td>"
            f"<td>{_esc(stats.get('compatible_event_count', '-'))}</td>"
            f"<td>{_esc(stats.get('domain_count', '-'))}</td>"
            f"<td>{_status(stats.get('can_satisfy_p0_sampling_constraints'))}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr>"
        "<th>ID</th><th>中文名称</th><th>高概率生活领域</th><th>兼容事件数</th>"
        "<th>兼容事件领域数</th><th>P0 状态</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_archetype_card(item: dict[str, Any], stats: dict[str, Any]) -> str:
    archetype_id = str(item.get("archetype_id"))
    field_blocks = []
    for key, label in FIELD_LABELS.items():
        values = item.get(key)
        if values:
            field_blocks.append(
                "<div class='field'>"
                f"<div class='field-title'>{_esc(label)}</div>"
                f"{_tags(values, muted=key == 'excluded_event_domains', field_key=key)}"
                "</div>"
            )
    return f"""
    <article class="archetype" id="{_esc(archetype_id)}">
      <div class="archetype-header">
        <h3><code>{_esc(archetype_id)}</code> · {_esc(_archetype_label(item))}</h3>
        <p>{_esc(_archetype_description(item))}</p>
      </div>
      <div class="archetype-body">
        <div class="basis">
          <strong>本 archetype 的生成标准依据</strong>
          {_list(_archetype_basis(item))}
          <ul>
            <li>以 <code>source_archetype={_esc(archetype_id)}</code>
              作为后续事件兼容性判断主键。</li>
            <li>事件选择必须以事件池中的
              <code>compatible_archetypes</code> 为准，不能由大模型自由决定。</li>
            <li>当前兼容事件数为 {_esc(stats.get("compatible_event_count", "-"))}，
              覆盖 {_esc(stats.get("domain_count", "-"))} 个事件领域；
              P0 检验结果：{_status(stats.get("can_satisfy_p0_sampling_constraints"))}。</li>
          </ul>
        </div>
        <table>
          <tr><th>兼容事件容量</th>
            <td>{_esc(stats.get("compatible_event_count", "-"))}</td></tr>
          <tr><th>兼容事件领域数</th>
            <td>{_esc(stats.get("domain_count", "-"))}</td></tr>
          <tr><th>领域上限后容量</th>
            <td>{_esc(stats.get("capped_event_capacity_under_domain_limit", "-"))}</td></tr>
          <tr><th>非 work/family 事件余量</th>
            <td>{_esc(stats.get("non_work_family_event_count", "-"))}</td></tr>
          <tr><th>兼容事件领域</th>
            <td>{_tags(stats.get("domains", []), field_key="event_domain")}</td></tr>
        </table>
        <details class="raw-fields">
          <summary>展开查看原始候选字段与可追溯值</summary>
          <p class="meta" style="padding: 0 12px;">
            这里保留 JSON 原始候选项；已覆盖的值会显示中文，未覆盖的值保留原始写法，
            用于后续采样脚本精确回连。
          </p>
          <div class="field-grid">
            {''.join(field_blocks)}
          </div>
        </details>
      </div>
    </article>
    """


def _sampling_table(sampling: dict[str, Any]) -> dict[str, Any]:
    result = {
        "demo 推荐人数": sampling.get("recommended_num_personas_for_demo"),
        "主实验推荐人数": sampling.get("recommended_num_personas_for_main_experiment"),
        "每人最少主生活领域": sampling.get("min_primary_life_domains_per_persona"),
        "每人最少长期目标": sampling.get("min_long_term_goals_per_persona"),
        "每人最少沟通风格": sampling.get("min_communication_styles_per_persona"),
        "每人最少压力反应": sampling.get("min_stress_responses_per_persona"),
        "同 archetype 最大比例": sampling.get("max_same_archetype_ratio_in_batch"),
        "批量多样性检查": sampling.get("diversity_checks", []),
    }
    return {key: value for key, value in result.items() if value is not None and value != []}


def _metric(value: str, number: Any, label: str) -> str:
    return (
        "<div class='metric'>"
        f"<strong>{_esc(number)}</strong>"
        f"<span>{_esc(value)} · {_esc(label)}</span>"
        "</div>"
    )


def _key_value_table(data: dict[str, Any], *, translate: bool = False) -> str:
    if not isinstance(data, dict) or not data:
        return "<p class='meta'>未提供。</p>"
    rows = []
    for key, value in data.items():
        display_key = _cn(key) if translate else key
        rows.append(
            "<tr>"
            f"<th>{_esc(display_key)}</th>"
            f"<td>{_format_value(value, translate=translate)}</td>"
            "</tr>"
        )
    return f"<table><tbody>{''.join(rows)}</tbody></table>"


def _format_value(value: Any, *, translate: bool = False) -> str:
    if isinstance(value, list):
        return _list(value, translate=translate)
    if isinstance(value, dict):
        return _key_value_table(value, translate=translate)
    return _esc(_cn(value) if translate else value)


def _list(values: Any, *, translate: bool = False) -> str:
    if not isinstance(values, list) or not values:
        return "<p class='meta'>未提供。</p>"
    items = [_cn(item) if translate else item for item in values]
    return "<ul class='compact'>" + "".join(f"<li>{_esc(item)}</li>" for item in items) + "</ul>"


def _tags(values: Any, *, muted: bool = False, field_key: str | None = None) -> str:
    if not isinstance(values, list) or not values:
        return "<span class='meta'>未提供</span>"
    class_name = "tag tag-muted" if muted else "tag"
    return "".join(
        f"<span class='{class_name}'>{_esc(_cn(item, field_key=field_key))}</span>"
        for item in values
    )


def _status(value: Any) -> str:
    if value is True:
        return "<span class='status-pass'>通过</span>"
    if value is False:
        return "<span style='color: var(--warn); font-weight: 700'>未通过</span>"
    return _esc(value if value is not None else "-")


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _archetype_label(item: dict[str, Any]) -> str:
    archetype_id = str(item.get("archetype_id"))
    return ARCHETYPE_CN.get(archetype_id, {}).get("label", str(item.get("label", "")))


def _archetype_description(item: dict[str, Any]) -> str:
    archetype_id = str(item.get("archetype_id"))
    return ARCHETYPE_CN.get(archetype_id, {}).get(
        "description",
        str(item.get("core_description", "")),
    )


def _archetype_basis(item: dict[str, Any]) -> list[str]:
    archetype_id = str(item.get("archetype_id"))
    return ARCHETYPE_CN.get(archetype_id, {}).get("basis", [])


def _cn(value: Any, *, field_key: str | None = None) -> str:
    text = str(value if value is not None else "")
    if text in STATIC_CN:
        return STATIC_CN[text]
    if text in SENSITIVE_POLICY_CN:
        return SENSITIVE_POLICY_CN[text]
    if text in TERM_CN:
        return TERM_CN[text]
    if field_key == "required_field":
        return REQUIRED_FIELD_CN.get(text, text)
    if field_key == "event_domain":
        return TERM_CN.get(text, text.replace("_", "/"))
    return text


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
