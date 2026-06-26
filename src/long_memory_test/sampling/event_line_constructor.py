from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from .zh_localization import (
    event_category_summary_zh,
    event_category_title_zh,
    event_domain_zh,
    zh_list,
    zh_term,
    zh_text,
    zh_value,
)


@dataclass(frozen=True)
class EventLineConstructionConfig:
    persona_id: str = "P0001"
    stages_per_event_line: int = 5
    include_user_message_seeds: bool = True


EVENT_CN = {
    "E_MOVE_001": {
        "title": "适应新城市但本地支持较弱",
    },
    "E_NEIGHBOR_001": {
        "title": "邻居噪音或边界问题",
    },
    "E_ADMIN_001": {
        "title": "行政材料或截止日期不确定",
    },
    "E_HOME_002": {
        "title": "租金上涨或续租不确定",
    },
    "E_PLAN_003": {
        "title": "家里未完成的小任务反复拖延",
    },
    "E_SOCIAL_002": {
        "title": "社交邀请和个人精力冲突",
    },
    "E_LEARN_001": {
        "title": "在生活很忙时学习新技能",
        "summary": "人物想提升技能，但时间、信心和持续性都受现实生活挤压。",
        "participants": ["自己", "课程/证书项目", "工作与生活安排"],
        "latent_concerns": ["怕自己坚持不下来", "担心投入时间后没有实际回报", "需要把目标拆小"],
    },
    "E_INTER_001": {
        "title": "工作消息打断休息或私人时间",
        "summary": "工作消息侵入休息时间，让人物难以判断哪些消息必须立刻回应。",
        "participants": ["自己", "同事或主管", "个人休息时间"],
        "latent_concerns": ["担心不及时回复会显得不负责", "需要建立可解释的回应边界", "习惯性紧张会消耗休息"],
    },
    "E_HEALTH_004": {
        "title": "普通身体不适带来的不确定",
        "summary": "人物遇到轻微反复的不适，不确定应该观察、求助，还是被焦虑放大。",
        "participants": ["自己", "日常健康记录", "必要时的专业帮助"],
        "latent_concerns": ["怕小问题被忽视", "也怕自己过度紧张", "需要避免自我诊断"],
    },
    "E_ADMIN_002": {
        "title": "福利、报销或申请表格填写困惑",
        "summary": "人物需要处理表格和材料，但担心填错、漏材料或不知道问谁。",
        "participants": ["自己", "表格/材料清单", "官方咨询渠道"],
        "latent_concerns": ["怕流程出错影响结果", "对规则不确定", "需要先整理证据和材料"],
    },
    "E_PET_001": {
        "title": "宠物照护的时间或费用压力",
        "summary": "宠物照护责任和工作、住房、预算安排发生冲突，需要做备份计划。",
        "participants": ["自己", "宠物", "可能的临时帮手"],
        "latent_concerns": ["担心照护安排不够稳", "怕额外花费打破预算", "需要区分紧急和可延后支出"],
    },
    "E_EDU_001": {
        "title": "学习任务、作业或考试截止压力",
        "summary": "人物面对学习任务截止，需要判断最低可交付范围和是否请求帮助。",
        "participants": ["自己", "课程任务", "老师/同学或学习平台"],
        "latent_concerns": ["怕质量不够", "不知道优先改哪里", "需要冻结范围并完成最低版本"],
    },
    "E_CLEAN_001": {
        "title": "家务堆积或居住空间混乱压力",
    },
    "E_GIG_002": {
        "title": "零工途中交通、天气或安全担忧",
    },
    "E_FAM_001": {
        "title": "家庭责任分担不均",
    },
    "E_CHILD_002": {
        "title": "孩子行为或学校反馈带来的担心",
    },
    "E_CONSUMER_001": {
        "title": "退款、退货或消费纠纷",
    },
    "E_PLAN_001": {
        "title": "重要决定前反复权衡",
    },
    "E_DIGITAL_001": {
        "title": "线上消息或数字生活带来的压力",
    },
    "E_FIN_001": {
        "title": "月度预算吃紧或意外支出",
    },
    "E_INTER_003": {
        "title": "家庭责任和工作安排相互挤压",
    },
    "E_TRANSPORT_001": {
        "title": "通勤延误或交通安排不稳定",
    },
    "E_PLAN_002": {
        "title": "待办事项太多导致优先级混乱",
    },
}

DOMAIN_CN = {
    "administration": "行政手续",
    "adult_child_boundary": "成年子女边界",
    "business": "小生意经营",
    "childcare": "儿童照护",
    "commuting": "通勤",
    "consumer_issue": "消费纠纷",
    "daily_life": "日常生活",
    "digital_life": "数字生活",
    "education": "教育/学业",
    "family": "家庭",
    "finance": "财务",
    "gig_work": "平台/零工",
    "health_routine": "健康日常",
    "housing": "住房",
    "learning": "学习转型",
    "neighborhood": "邻里",
    "personal_planning": "个人规划",
    "pet_care": "宠物照护",
    "relocation": "搬迁适应",
    "social_connection": "社会连接",
    "work_family_intersection": "工作-家庭交叉",
}

STAGE_CN = {
    "initial concern": ("initial", "第一次提出担心，说明触发点和不确定处。"),
    "recurrence": ("recurrence", "问题再次出现，人物希望不要从零解释。"),
    "turning point": ("turning_point", "出现新变化，人物开始重新判断优先级或边界。"),
    "partial resolution": ("partial_resolution", "有部分处理结果，但仍保留后续观察。"),
    "reflection": ("reflection", "回看这条线，抽取反复出现的模式或下次处理方式。"),
}

TERM_CN = {
    "whether goal is realistic": "这个目标是不是现实",
    "what to study first": "应该先学什么",
    "how to restart after falling behind": "落下之后怎么重新开始",
    "reduce study unit size": "把学习单元缩小",
    "set weekly minimum": "设一个每周最低量",
    "connect skill to concrete goal": "把技能和具体目标连起来",
    "whether to reply now": "现在要不要回复",
    "what boundary is safe": "什么边界是安全的",
    "how to explain delay": "怎么解释延迟回复",
    "define response window": "设定回复时间窗口",
    "draft delayed reply": "先写一条延迟回复",
    "separate urgency from habit": "区分真实紧急和习惯性紧张",
    "whether to observe or seek help": "应该先观察还是求助",
    "what signs matter": "哪些信号真正重要",
    "whether anxiety is amplifying it": "是不是焦虑把不适放大了",
    "avoid diagnosis": "避免自我诊断",
    "track concrete pattern": "记录具体模式",
    "seek professional help if concerning signs appear": "出现明确警讯时寻求专业帮助",
    "what counts as proof": "什么材料算有效证明",
    "whether the form is complete": "表格是否已经完整",
    "where to ask": "应该去哪里问",
    "make document checklist": "整理材料清单",
    "ask official channel": "询问官方渠道",
    "avoid guessing uncertain fields": "不要猜不确定字段",
    "whether care plan is enough": "照护安排是否足够",
    "whether cost is manageable": "费用是否可承受",
    "who can help": "谁可以临时帮忙",
    "list care needs": "列出照护需求",
    "identify backup helper": "找到备份帮手",
    "separate urgent from optional cost": "区分紧急支出和可选支出",
    "what to prioritize": "应该先处理什么",
    "what to do first": "第一步应该先做什么",
    "how good is enough": "做到什么程度算够",
    "whether to ask for extension": "是否需要申请延期",
    "define minimum submission": "定义最低可交付版本",
    "freeze scope": "冻结范围",
    "ask focused question": "只问一个聚焦问题",
    "shame": "羞耻感",
    "comparison": "比较压力",
    "hope": "期待",
    "guilt": "内疚",
    "irritation": "烦躁",
    "fear of being irresponsible": "怕显得不负责",
    "fear": "害怕",
    "uncertainty": "不确定",
    "hypervigilance": "过度警觉",
    "confusion": "困惑",
    "fear of mistakes": "怕出错",
    "administrative stress": "行政压力",
    "worry": "担心",
    "responsibility pressure": "责任压力",
    "fatigue": "疲惫",
    "where to invest social energy": "该把社交精力投在哪里",
    "whether loneliness means wrong choice": "孤独感是不是说明当初选择错了",
    "whether loneliness means wrong decision": "孤独感是不是说明这个决定错了",
    "choose one recurring social anchor": "选择一个固定出现的社交锚点",
    "which rule applies": "到底适用哪条规则",
    "list known requirements": "列出已经明确的要求",
    "use official channel": "通过官方渠道确认",
    "whether to talk directly": "要不要直接沟通",
    "whether to contact property management": "要不要联系物业或管理方",
    "document pattern": "先记录反复出现的模式",
    "try neutral first message": "先发一条中性的沟通信息",
    "whether to renew": "要不要续租",
    "whether to negotiate": "要不要谈条件",
    "whether moving is realistic": "搬家是否现实",
    "compare total moving cost": "比较搬家的总成本",
    "ask landlord concrete terms": "向房东确认具体条件",
    "whether to do it now": "现在要不要处理",
    "whether to pay someone": "要不要付费找人处理",
    "define smallest next step": "定义一个最小下一步",
    "set time-box": "设定限时处理窗口",
    "whether request is reasonable": "这个请求是否合理",
    "how direct to be": "应该说得多直接",
    "make social goal small": "把社交目标缩小",
    "contact one weak tie": "联系一个弱关系熟人",
    "where to start": "应该从哪里开始",
    "whether mess means personal failure": "混乱是否等于自己失败",
    "choose one visible area": "先选一个看得见的小区域",
    "time-box 15 minutes": "限时 15 分钟处理",
    "how much risk is acceptable": "多少风险是可以接受的",
    "which backup route is worth it": "哪条备选路线值得准备",
    "set safety cutoff": "设定安全停止线",
    "plan backup shift": "准备一个备用班次安排",
    "what is fair": "怎样才算公平",
    "how to explain family absence": "怎么解释家人缺席",
    "name invisible labor": "把看不见的劳动说出来",
    "make one concrete request": "提出一个具体请求",
    "whether feedback is fair": "反馈是否公平",
    "whether to intervene": "是否需要介入",
    "separate observation from label": "区分观察事实和贴标签",
    "ask for concrete examples": "要求具体例子",
    "what evidence to keep": "该保留哪些证据",
    "whether to contact support": "是否联系平台客服",
    "collect receipt/evidence": "整理收据和证据",
    "send clarification message": "发送澄清信息",
    "whether to ask for help": "是否需要求助",
    "what can be dropped": "哪些事情可以先放下",
    "choose good-enough threshold": "设定够用标准",
    "schedule recovery block": "安排恢复时间块",
    "whether account is safe": "账户是否安全",
    "whether to notify someone": "要不要提前通知别人",
    "whether to contact office": "是否联系办公室或相关部门",
    "identify official source": "确认官方来源",
    "avoid sharing codes": "不要分享验证码或敏感代码",
    "what expense can be delayed": "哪些支出可以延后",
    "what to pay first": "应该先支付什么",
    "rank fixed expenses": "给固定支出排序",
    "make one temporary cut": "先做一个临时削减",
    "how much overtime is worth it": "多少加班值得承担",
    "whether to stop early": "是否应该提前停止",
    "whether income target is worth it": "这个收入目标是否值得",
    "separate function from perfection": "区分功能够用和完美要求",
    "notify early": "提前通知相关人",
    "how firm to be": "边界应该多坚定",
    "how to avoid escalation": "如何避免升级冲突",
    "communicate limits": "说明自己的限制",
    "set default rule": "设定默认规则",
    "how much to do at once": "一次应该处理多少",
    "what threshold to set": "应该设置什么阈值",
    "choose backup threshold": "选择备选方案启动阈值",
    "write concise request": "写一条简洁请求",
    "how to reduce mental load": "怎么降低脑内负担",
    "choose first 20-minute action": "选一个 20 分钟内能做的动作",
    "avoid solving all at once": "不要一次解决所有问题",
    "which choice matters": "哪个选择真正重要",
    "triage must/should/can-wait": "区分必须做、应该做和可以等等",
    "how much effort to invest": "该投入多少精力",
    "whether to optimize": "是否值得继续优化",
    "reduce options": "减少选项",
    "set review time": "设定复盘时间",
    "what step to try first": "第一步先试什么",
    "whether it is a pattern": "这是不是一个反复模式",
    "use formal channel if repeated": "如果反复发生就走正式渠道",
    "try one safe recovery step": "先试一个安全的恢复动作",
    "how to avoid repeated issue": "如何避免问题反复",
    "define income target and safety cutoff": "定义收入目标和安全停止线",
    "separate income target from safety threshold": "区分收入目标和安全阈值",
    "choose recurring low-stakes activity": "选择一个低压力的固定活动",
    "make low-stakes routine": "建立低压力日常",
    "identify official options": "确认官方可选方案",
    "list official support path": "列出官方支持路径",
    "decide DIY vs paid help": "决定自己处理还是付费处理",
    "choose one small home response": "选一个小的居家处理动作",
    "annoyance": "烦躁",
    "anxiety": "焦虑",
    "avoidance": "回避",
    "bureaucratic frustration": "行政挫败感",
    "decision fatigue": "决策疲劳",
    "defensiveness": "防御感",
    "dependence anxiety": "依赖焦虑",
    "disorientation": "失去方向感",
    "embarrassment": "尴尬",
    "fear of conflict": "害怕冲突",
    "fear of confrontation": "害怕正面沟通",
    "fear of irreversible mistake": "害怕犯不可逆的错",
    "feeling trapped": "被困住的感觉",
    "financial anxiety": "财务焦虑",
    "helplessness": "无力感",
    "indecision": "犹豫不决",
    "insecurity": "不安",
    "overwhelm": "被压垮感",
    "panic": "慌乱",
    "perfectionism": "完美主义压力",
    "protective guilt": "保护性内疚",
    "resentment": "委屈和怨气",
    "scarcity anxiety": "资源不足焦虑",
    "self-blame": "自责",
    "self-doubt": "自我怀疑",
    "time pressure": "时间压力",
    "unfairness": "不公平感",
    "urgency": "紧迫感",
}

OCCUPATION_CN = {
    "property service assistant": "物业服务助理",
    "call center customer service agent": "呼叫中心客服",
    "platform-based service worker": "平台服务劳动者",
    "convenience store owner": "便利店店主",
    "hotel front desk worker": "酒店前台",
}


def construct_event_lines_for_persona(
    *,
    sampled_personas: dict[str, Any],
    accepted_event_sets: dict[str, Any],
    event_pool: dict[str, Any],
    config: EventLineConstructionConfig | None = None,
) -> dict[str, Any]:
    cfg = config or EventLineConstructionConfig()
    persona = _find_by_id(sampled_personas.get("personas", []), "persona_id", cfg.persona_id)
    accepted = _find_by_id(
        accepted_event_sets.get("accepted_persona_event_sets", []),
        "persona_id",
        cfg.persona_id,
    )
    events_by_id = {
        str(event.get("event_category_id")): event
        for event in event_pool.get("event_categories", [])
        if isinstance(event, dict)
    }
    event_lines = []
    for event_id in accepted.get("accepted_event_ids", []):
        event = events_by_id.get(str(event_id))
        if not event:
            raise ValueError(f"Accepted event {event_id} not found in event pool.")
        event_lines.append(_construct_event_line(persona=persona, event=event, cfg=cfg))

    return {
        "schema_version": "event_lines_v0.1",
        "sampling_stage": "P1_event_line_construction",
        "construction_scope": {
            "persona_id": cfg.persona_id,
            "from_p0_persona": True,
            "from_p0_accepted_event_set": True,
            "timeline_constructed": False,
            "daily_interactions_constructed": False,
            "probe_plan_constructed": False,
        },
        "construction_config": asdict(cfg),
        "persona_ref": {
            "persona_id": persona.get("persona_id"),
            "source_archetype": persona.get("source_archetype"),
            "source_archetype_label": persona.get("source_archetype_label"),
            "source_archetype_label_zh": zh_value(persona.get("source_archetype_label")),
            "occupation": persona.get("occupation"),
            "occupation_zh": zh_value(persona.get("occupation")),
            "family_structure": persona.get("family_structure"),
            "family_structure_zh": zh_value(persona.get("family_structure")),
            "primary_life_domains": persona.get("primary_life_domains", []),
            "primary_life_domains_zh": zh_value(persona.get("primary_life_domains", [])),
        },
        "event_line_count": len(event_lines),
        "event_lines": event_lines,
    }


def construct_event_lines_for_batch(
    *,
    sampled_personas: dict[str, Any],
    accepted_event_sets: dict[str, Any],
    event_pool: dict[str, Any],
    stages_per_event_line: int = 5,
) -> dict[str, Any]:
    personas = [
        item
        for item in sampled_personas.get("personas", [])
        if isinstance(item, dict) and item.get("persona_id")
    ]
    persona_payloads = []
    flattened_event_lines = []
    for persona in personas:
        persona_id = str(persona["persona_id"])
        payload = construct_event_lines_for_persona(
            sampled_personas=sampled_personas,
            accepted_event_sets=accepted_event_sets,
            event_pool=event_pool,
            config=EventLineConstructionConfig(
                persona_id=persona_id,
                stages_per_event_line=stages_per_event_line,
            ),
        )
        persona_payloads.append(payload)
        flattened_event_lines.extend(payload["event_lines"])

    return {
        "schema_version": "event_lines_batch_v0.1",
        "sampling_stage": "P1_event_line_construction_batch",
        "construction_scope": {
            "from_p0_personas": True,
            "from_p0_accepted_event_sets": True,
            "timeline_constructed": False,
            "daily_interactions_constructed": False,
            "probe_plan_constructed": False,
        },
        "construction_config": {
            "stages_per_event_line": stages_per_event_line,
            "persona_count": len(personas),
        },
        "summary": {
            "persona_count": len(personas),
            "event_line_count": len(flattened_event_lines),
            "event_lines_per_persona": {
                str(payload["persona_ref"]["persona_id"]): int(payload["event_line_count"])
                for payload in persona_payloads
            },
        },
        "personas": persona_payloads,
        "event_lines": flattened_event_lines,
    }


def _construct_event_line(
    *,
    persona: dict[str, Any],
    event: dict[str, Any],
    cfg: EventLineConstructionConfig,
) -> dict[str, Any]:
    event_id = str(event["event_category_id"])
    domain = str(event.get("event_domain", ""))
    cn = EVENT_CN.get(event_id, {})
    title_zh = cn.get("title", event_category_title_zh(event))
    title = str(event.get("title") or event_id)
    summary = str(event.get("core_issue") or "")
    summary_zh = cn.get("summary", event_category_summary_zh(event))
    stages = _stage_labels(event)[: cfg.stages_per_event_line]
    return {
        "event_line_id": _event_line_id(str(persona["persona_id"]), event_id),
        "persona_id": persona.get("persona_id"),
        "source_archetype": persona.get("source_archetype"),
        "event_category_id": event_id,
        "event_domain": domain,
        "event_domain_zh": DOMAIN_CN.get(domain, event_domain_zh(domain)),
        "event_type": event.get("event_type"),
        "event_title": {
            "source": title,
            "zh": title_zh,
        },
        "persistent_event_summary": summary,
        "persistent_event_summary_zh": summary_zh,
        "participants": ["self"],
        "participants_zh": cn.get("participants", ["自己"]),
        "allowed_facts": _allowed_facts(persona=persona, event=event),
        "allowed_facts_zh": _allowed_facts_zh(persona=persona, event=event),
        "latent_concerns": _string_list(event.get("possible_emotional_load")),
        "latent_concerns_zh": cn.get(
            "latent_concerns",
            zh_list(event.get("possible_emotional_load")),
        ),
        "relational_memory_targets": _relational_memory_targets(persona=persona, event=event),
        "stage_sequence": [
            _construct_stage(
                persona=persona,
                event=event,
                event_title=title,
                event_title_zh=title_zh,
                source_stage_label=stage,
                index=index,
            )
            for index, stage in enumerate(stages, start=1)
        ],
        "source_event_category": {
            "core_issue": event.get("core_issue"),
            "core_issue_zh": event_category_summary_zh(event),
            "possible_uncertainties": _string_list(event.get("possible_uncertainties", [])),
            "possible_uncertainties_zh": zh_list(event.get("possible_uncertainties", [])),
            "possible_emotional_load": _string_list(event.get("possible_emotional_load", [])),
            "possible_emotional_load_zh": zh_list(event.get("possible_emotional_load", [])),
            "possible_actions": _string_list(event.get("possible_actions", [])),
            "possible_actions_zh": zh_list(event.get("possible_actions", [])),
            "memory_risks": _string_list(event.get("memory_risks", [])),
            "memory_risks_zh": zh_list(event.get("memory_risks", [])),
        },
        "construction_notes": [
            "本事件线由 P0 已接受事件类别确定，不来自旧单人剧本。",
            "阶段序列使用事件类别池中的阶段模式。",
            "当前未安排具体日期；日期级时间线属于下一步。",
        ],
    }


def _construct_stage(
    *,
    persona: dict[str, Any],
    event: dict[str, Any],
    event_title: str,
    event_title_zh: str,
    source_stage_label: str,
    index: int,
) -> dict[str, Any]:
    normalized_stage, stage_goal_zh = STAGE_CN.get(
        source_stage_label,
        (source_stage_label.replace(" ", "_"), "沿着事件线推进一次。"),
    )
    stage_goal = _stage_goal_en(normalized_stage)
    uncertainties = _string_list(event.get("possible_uncertainties"))
    actions = _string_list(event.get("possible_actions"))
    emotional_load = _string_list(event.get("possible_emotional_load"))
    event_summary = str(event.get("core_issue") or "")
    event_summary_zh = event_category_summary_zh(event)
    allowed_base_facts = _allowed_base_facts(event_summary=event_summary)
    allowed_base_facts_zh = _allowed_base_facts(event_summary=event_summary_zh)
    event_candidate_facts = _event_candidate_facts(event=event)
    persona_conditioned_facts = _persona_conditioned_facts(persona=persona, event=event)
    stage_delta_facts = _stage_delta_facts(
        event_title=event_title,
        event_title_zh=event_title_zh,
        normalized_stage=normalized_stage,
        uncertainties=uncertainties,
        actions=actions,
        index=index,
    )
    allowed_new_facts = _dedupe_texts(
        [
            *allowed_base_facts,
            *[str(item["text"]) for item in persona_conditioned_facts],
            *[str(item["text"]) for item in stage_delta_facts],
        ]
    )
    allowed_new_facts_zh = _dedupe_texts(
        [
            *allowed_base_facts_zh,
            *[str(item.get("text_zh") or item["text"]) for item in persona_conditioned_facts],
            *[str(item.get("text_zh") or item["text"]) for item in stage_delta_facts],
        ]
    )
    return {
        "stage_index": index,
        "event_stage": normalized_stage,
        "source_stage_label": source_stage_label,
        "source_stage_label_zh": zh_text(source_stage_label),
        "stage_goal": stage_goal,
        "stage_goal_zh": stage_goal_zh,
        "allowed_base_facts": allowed_base_facts,
        "allowed_base_facts_zh": allowed_base_facts_zh,
        "event_candidate_facts": event_candidate_facts,
        "persona_conditioned_facts": persona_conditioned_facts,
        "stage_delta_facts": stage_delta_facts,
        "allowed_new_facts": allowed_new_facts,
        "allowed_new_facts_zh": allowed_new_facts_zh,
        "user_state_hint": _state_hint_en(
            stage=normalized_stage,
            emotional_load=emotional_load,
        ),
        "user_state_hint_zh": _state_hint_zh(
            stage=normalized_stage,
            emotional_load=emotional_load,
        ),
        "user_message_seed": _message_seed(
            persona=persona,
            event_title=event_title,
            normalized_stage=normalized_stage,
            uncertainties=uncertainties,
            actions=actions,
        ),
        "user_message_seed_zh": _message_seed_zh(
            persona=persona,
            event_title_zh=event_title_zh,
            normalized_stage=normalized_stage,
            uncertainties=uncertainties,
            actions=actions,
        ),
        "assistant_memory_expectation": _assistant_expectation_en(normalized_stage),
        "assistant_memory_expectation_zh": _assistant_expectation_zh(normalized_stage),
        "prohibited_facts": [
            "Do not add real names, precise addresses, exact income, medical diagnoses, or legal conclusions.",
            "Do not migrate facts from the old single-person script into this persona.",
            "Do not introduce major life events outside the event category and persona fields.",
        ],
        "prohibited_facts_zh": [
            "不能补充真实姓名、精确地址、精确收入、医学诊断或法律结论。",
            "不能把旧单人剧本中的事实迁移到本人物。",
            "不能引入事件类别和人物字段之外的新重大事件。",
        ],
    }


def _allowed_base_facts(*, event_summary: str) -> list[str]:
    return _dedupe_texts([event_summary])


def _event_candidate_facts(*, event: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    core_issue = str(event.get("core_issue") or "")
    if core_issue:
        candidates.append(
            {
                "source_field": "core_issue",
                "source_index": 0,
                "text": core_issue,
                "text_zh": event_category_summary_zh(event),
            }
        )
    for source_field in (
        "possible_uncertainties",
        "possible_actions",
        "possible_emotional_load",
    ):
        for index, value in enumerate(_string_list(event.get(source_field))):
            text = str(value)
            if not text:
                continue
            candidates.append(
                {
                    "source_field": source_field,
                    "source_index": index,
                    "text": text,
                    "text_zh": _cn_term(text),
                }
            )
    return _dedupe_fact_records(candidates)


def _persona_conditioned_facts(
    *,
    persona: dict[str, Any],
    event: dict[str, Any],
) -> list[dict[str, Any]]:
    domain = str(event.get("event_domain", ""))
    domain_zh = DOMAIN_CN.get(domain, event_domain_zh(domain))
    occupation = str(persona.get("occupation") or "")
    family = str(persona.get("family_structure") or "")
    economic = str(persona.get("economic_condition") or "")
    support = str(persona.get("social_support") or "")
    goals = _join_values(persona.get("long_term_goals", []), max_items=2)
    decision_style = _join_values(persona.get("decision_style", []), max_items=2)
    communication_style = _join_values(persona.get("communication_style", []), max_items=2)
    occupation_zh = str(zh_value(persona.get("occupation")) or "")
    family_zh = str(zh_value(persona.get("family_structure")) or "")
    economic_zh = str(zh_value(persona.get("economic_condition")) or "")
    support_zh = str(zh_value(persona.get("social_support")) or "")
    goals_zh = _join_values(zh_value(persona.get("long_term_goals", [])), max_items=2)
    decision_style_zh = _join_values(zh_value(persona.get("decision_style", [])), max_items=2)
    communication_style_zh = _join_values(
        zh_value(persona.get("communication_style", [])),
        max_items=2,
    )
    rows = [
        (
            ["event_domain", "occupation", "family_structure"],
            f"This {domain} event line must be handled within the persona's real-life position: {occupation}, {family}.",
            f"这条{domain_zh}事件线需要放在人物现实身份中处理：{occupation_zh}，{family_zh}。",
        ),
        (
            ["event_domain", "economic_condition"],
            f"Feasible options must respect the persona's economic condition: {economic}.",
            f"可行方案必须受人物经济条件约束：{economic_zh}。",
        ),
        (
            ["social_support"],
            f"Any help-seeking or external coordination must consider the support boundary: {support}.",
            f"是否求助或外部协同时，需要考虑支持边界：{support_zh}。",
        ),
    ]
    if goals:
        rows.append(
            (
                ["long_term_goals"],
                f"Advice must not drift away from the persona's long-term goals: {goals}.",
                f"建议不能偏离人物长期目标：{goals_zh}。",
            )
        )
    if decision_style:
        rows.append(
            (
                ["decision_style"],
                f"Option ordering should match the persona's decision style: {decision_style}.",
                f"方案排序要符合人物决策方式：{decision_style_zh}。",
            )
        )
    if communication_style:
        rows.append(
            (
                ["communication_style"],
                f"Dialogue wording should fit the persona's communication style: {communication_style}.",
                f"对话表达应贴合人物沟通风格：{communication_style_zh}。",
            )
        )
    facts = [
        {
            "source_fields": fields,
            "text": text,
            "text_zh": text_zh,
        }
        for fields, text, text_zh in rows
        if not _has_blank_fact_part(text)
    ]
    return _dedupe_fact_records(facts)


def _stage_delta_facts(
    *,
    event_title: str,
    event_title_zh: str,
    normalized_stage: str,
    uncertainties: list[str],
    actions: list[str],
    index: int,
) -> list[dict[str, Any]]:
    unc = [str(item) for item in uncertainties]
    act = [str(item) for item in actions]
    unc_zh = _cn_list(uncertainties)
    act_zh = _cn_list(actions)
    first_uncertainty = _pick(unc, 0, "当前最需要澄清的判断点")
    second_uncertainty = _pick(unc, 1, first_uncertainty)
    third_uncertainty = _pick(unc, 2, second_uncertainty)
    first_action = _pick(act, 0, "先拆一个低成本动作")
    second_action = _pick(act, 1, first_action)
    third_action = _pick(act, 2, second_action)
    first_uncertainty_zh = _pick(unc_zh, 0, "当前最需要澄清的判断点")
    second_uncertainty_zh = _pick(unc_zh, 1, first_uncertainty_zh)
    third_uncertainty_zh = _pick(unc_zh, 2, second_uncertainty_zh)
    first_action_zh = _pick(act_zh, 0, "先拆一个低成本动作")
    second_action_zh = _pick(act_zh, 1, first_action_zh)
    third_action_zh = _pick(act_zh, 2, second_action_zh)

    if normalized_stage == "initial":
        rows = [
            (
                ["possible_uncertainties[0]"],
                f"Stage {index} adds: the user first states the event line \"{event_title}\" clearly; the primary uncertainty is \"{first_uncertainty}\".",
                f"第 {index} 阶段新增：用户第一次把「{event_title_zh}」说清楚，首要不确定点是「{first_uncertainty_zh}」。",
            ),
            (
                ["possible_actions[0]"],
                f"This stage may advance only one low-cost starting action: \"{first_action}\".",
                f"本阶段只允许推进一个低成本起点：「{first_action_zh}」。",
            ),
        ]
    elif normalized_stage == "recurrence":
        rows = [
            (
                ["stage_recurrence"],
                f"Stage {index} adds: the same event line appears again; the user expects continuity rather than restarting the explanation.",
                f"第 {index} 阶段新增：同一事件线再次出现，用户期待助手承接前序而不是重启解释。",
            ),
            (
                ["possible_uncertainties[1]"],
                f"The new judgment pressure shifts toward \"{second_uncertainty}\".",
                f"新的判断压力转向「{second_uncertainty_zh}」。",
            ),
        ]
    elif normalized_stage == "turning_point":
        rows = [
            (
                ["possible_uncertainties[2]"],
                f"Stage {index} adds: the event reaches a turning point; the key issue moves from the initial concern toward \"{third_uncertainty}\".",
                f"第 {index} 阶段新增：事件出现转折，关键问题从初始担心推进到「{third_uncertainty_zh}」。",
            ),
            (
                ["stage_turning_point"],
                "This stage requires reprioritization rather than mechanically repeating the first advice.",
                "本阶段需要重新排序优先级，而不是机械重复第一次的建议。",
            ),
        ]
    elif normalized_stage == "partial_resolution":
        rows = [
            (
                ["possible_actions[1]"],
                f"Stage {index} adds: the user has already made partial progress and now needs to confirm \"{second_action}\".",
                f"第 {index} 阶段新增：用户已经推进过一部分处理，现在要确认「{second_action_zh}」。",
            ),
            (
                ["possible_actions[2]"],
                f"If there is still a gap, this stage may discuss whether \"{third_action}\" is needed.",
                f"如果仍有缺口，本阶段可以讨论是否需要「{third_action_zh}」。",
            ),
        ]
    elif normalized_stage == "reflection":
        rows = [
            (
                ["possible_actions[0]", "possible_actions[1]", "possible_actions[2]"],
                f"Stage {index} adds: reflection forms a reusable order: first \"{first_action}\", then \"{second_action}\", and if needed \"{third_action}\".",
                f"第 {index} 阶段新增：回看后形成可复用顺序：先「{first_action_zh}」，再「{second_action_zh}」，必要时「{third_action_zh}」。",
            ),
            (
                [
                    "possible_uncertainties[0]",
                    "possible_uncertainties[1]",
                    "possible_uncertainties[2]",
                ],
                f"Long-term memory should preserve this judgment pattern: from \"{first_uncertainty}\" to \"{second_uncertainty}\", then to \"{third_uncertainty}\".",
                f"长期记忆应保留这一类判断模式：从「{first_uncertainty_zh}」到「{second_uncertainty_zh}」，再到「{third_uncertainty_zh}」。",
            ),
        ]
    else:
        rows = [
            (
                ["stage_pattern"],
                f"Stage {index} adds: advance once more along \"{event_title}\".",
                f"第 {index} 阶段新增：沿着「{event_title_zh}」继续推进一次。",
            )
        ]
    return _dedupe_fact_records(
        [
            {
                "source_fields": source_fields,
                "text": text,
                "text_zh": text_zh,
            }
            for source_fields, text, text_zh in rows
            if text
        ]
    )


def _allowed_facts(*, persona: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    return {
        "persona_facts": {
            "age_range": persona.get("age_range"),
            "occupation": persona.get("occupation"),
            "occupation_status": persona.get("occupation_status"),
            "family_structure": persona.get("family_structure"),
            "economic_condition": persona.get("economic_condition"),
            "social_support": persona.get("social_support"),
            "primary_life_domains": persona.get("primary_life_domains", []),
            "long_term_goals": persona.get("long_term_goals", []),
            "communication_style": persona.get("communication_style", []),
        },
        "event_category_facts": {
            "event_category_id": event.get("event_category_id"),
            "event_domain": event.get("event_domain"),
            "event_domain_zh": event_domain_zh(event.get("event_domain")),
            "event_type": event.get("event_type"),
            "core_issue": event.get("core_issue"),
            "possible_uncertainties": _string_list(event.get("possible_uncertainties", [])),
            "possible_actions": _string_list(event.get("possible_actions", [])),
        },
    }


def _allowed_facts_zh(*, persona: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    return {
        "persona_facts": {
            "age_range": zh_value(persona.get("age_range")),
            "occupation": zh_value(persona.get("occupation")),
            "occupation_status": zh_value(persona.get("occupation_status")),
            "family_structure": zh_value(persona.get("family_structure")),
            "economic_condition": zh_value(persona.get("economic_condition")),
            "social_support": zh_value(persona.get("social_support")),
            "primary_life_domains": zh_value(persona.get("primary_life_domains", [])),
            "long_term_goals": zh_value(persona.get("long_term_goals", [])),
            "communication_style": zh_value(persona.get("communication_style", [])),
        },
        "event_category_facts": {
            "event_category_id": event.get("event_category_id"),
            "event_domain": event.get("event_domain"),
            "event_domain_zh": event_domain_zh(event.get("event_domain")),
            "event_type": event.get("event_type"),
            "core_issue": event_category_summary_zh(event),
            "possible_uncertainties": zh_list(event.get("possible_uncertainties", [])),
            "possible_actions": zh_list(event.get("possible_actions", [])),
        },
    }


def _relational_memory_targets(*, persona: dict[str, Any], event: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "target_type": "response_preference",
            "target": "The persona prefers concrete, low-cost, executable next steps rather than generic reassurance.",
            "target_zh": "人物偏好具体、低成本、可执行的下一步，而不是空泛安慰。",
        },
        {
            "target_type": "event_continuity",
            "target": "Later stages should continue the same event line and not require the persona to explain from scratch.",
            "target_zh": "后续阶段应承接同一事件线，不要求人物从零解释。",
        },
        {
            "target_type": "boundary",
            "target": "Use only allowed persona and event-category facts; do not fill gaps to appear familiar.",
            "target_zh": "只使用人物与事件类别允许事实；不为了显得懂而补空白。",
        },
    ]


def _stage_labels(event: dict[str, Any]) -> list[str]:
    patterns = event.get("stage_patterns")
    if not isinstance(patterns, list) or not patterns:
        return ["initial concern", "recurrence", "turning point", "partial resolution", "reflection"]
    for pattern in patterns:
        if isinstance(pattern, list) and pattern:
            return [str(item) for item in pattern if item is not None and str(item)]
    return ["initial concern", "recurrence", "turning point", "partial resolution", "reflection"]


def _stage_goal_en(stage: str) -> str:
    return {
        "initial": "Introduce the concern for the first time, including trigger and uncertainty.",
        "recurrence": "The issue appears again; the persona wants continuity rather than a restart.",
        "turning_point": "A new change appears; the persona needs to reprioritize or reset boundaries.",
        "partial_resolution": "Some progress exists, but follow-up observation or risk checking remains.",
        "reflection": "Review the line and extract a recurring pattern or reusable handling method.",
    }.get(stage, "Advance the event line one step.")


def _state_hint_en(*, stage: str, emotional_load: list[str]) -> str:
    load = ", ".join(str(item) for item in emotional_load[:2]) if emotional_load else "pressure"
    if stage == "initial":
        return f"The persona first notices the issue; the main emotional load is {load}."
    if stage == "recurrence":
        return f"The issue appears again; the persona starts worrying it is not isolated, and {load} increases."
    if stage == "turning_point":
        return "A new signal or felt change appears, and the persona needs to reconsider priority."
    if stage == "partial_resolution":
        return "The persona has taken partial action but still needs to check whether the next step is enough."
    return "The persona reviews this line and tries to extract their own response pattern."


def _state_hint_zh(*, stage: str, emotional_load: list[str]) -> str:
    load = "、".join(_cn_list(emotional_load[:2])) if emotional_load else "压力"
    if stage == "initial":
        return f"第一次意识到问题，主要情绪是{load}。"
    if stage == "recurrence":
        return f"问题再次出现，人物开始担心这不是偶发情况，{load}加重。"
    if stage == "turning_point":
        return "出现新信息或体感变化，人物需要重新判断优先级。"
    if stage == "partial_resolution":
        return "已经做过一部分处理，但还需要确认下一步是否继续。"
    return "人物回看这条线，尝试抽取自己的反应模式。"


def _message_seed(
    *,
    persona: dict[str, Any],
    event_title: str,
    normalized_stage: str,
    uncertainties: list[str],
    actions: list[str],
) -> str:
    occupation = str(persona.get("occupation") or "current job")
    uncertainty = uncertainties[0] if uncertainties else "下一步该怎么做"
    action = actions[0] if actions else "先拆一个小步骤"
    if normalized_stage == "initial":
        return (
            f"I am stuck on \"{event_title}\" recently. "
            f"I work as {occupation}, and my time and budget are limited, "
            f"so I am not sure about {uncertainty}. Please help me break it down."
        )
    if normalized_stage == "recurrence":
        return (
            f"The \"{event_title}\" issue we talked about before came up again. "
            f"I do not want to explain it from scratch; continue from the earlier approach and help me see "
            f"whether I should {action} now."
        )
    if normalized_stage == "turning_point":
        return (
            f"There is a new change in \"{event_title}\" today. "
            f"I realize the real sticking point may be {uncertainty}, not only the event itself. "
            "Please help me judge the priority."
        )
    if normalized_stage == "partial_resolution":
        return (
            f"I have made some progress on \"{event_title}\", for example I can {action} first, "
            "but I am not sure whether that is enough. Please check if I missed an obvious gap."
        )
    return (
        f"Looking back at \"{event_title}\", I notice I get repeatedly tense when similar things happen. "
        "Please help me summarize what handling method I should actually remember from this line."
    )


def _message_seed_zh(
    *,
    persona: dict[str, Any],
    event_title_zh: str,
    normalized_stage: str,
    uncertainties: list[str],
    actions: list[str],
) -> str:
    occupation = _cn_occupation(persona.get("occupation", "现在这份工作"))
    uncertainty = uncertainties[0] if uncertainties else "下一步该怎么做"
    action = actions[0] if actions else "先拆一个小步骤"
    if normalized_stage == "initial":
        return (
            f"我最近卡在「{event_title_zh}」这件事上。"
            f"我现在做{occupation}，时间和预算都不是很宽，"
            f"所以有点拿不准{_cn_term(uncertainty)}。你先帮我拆一下。"
        )
    if normalized_stage == "recurrence":
        return (
            f"之前说过的「{event_title_zh}」又出现了。"
            f"我不想从头解释一遍，你接着前面的思路帮我看，"
            f"现在是不是该{_cn_term(action)}。"
        )
    if normalized_stage == "turning_point":
        return (
            f"「{event_title_zh}」今天有点新变化，我发现自己真正卡住的"
            f"可能不是事情本身，而是{_cn_term(uncertainty)}。你帮我判断优先级。"
        )
    if normalized_stage == "partial_resolution":
        return (
            f"「{event_title_zh}」这条线我已经处理了一点，比如可以先{_cn_term(action)}，"
            "但我还不确定这样是不是够。你帮我看看还有没有明显漏项。"
        )
    return (
        f"回头看「{event_title_zh}」，我发现自己类似事情出现时会反复紧张。"
        "你帮我总结一下，这条线里我真正需要记住的处理方式是什么。"
    )


def _assistant_expectation_en(stage: str) -> str:
    if stage == "initial":
        return "Separate known facts, unknowns, risks, and one low-cost next step."
    if stage == "recurrence":
        return "Continue the same event line without asking the user to repeat the background."
    if stage == "turning_point":
        return "Identify the change point and help the user reorder priorities."
    if stage == "partial_resolution":
        return "Check completed actions and remaining risks without overstating progress."
    return "Extract a stable handling pattern without mechanically repeating the log."


def _assistant_expectation_zh(stage: str) -> str:
    if stage == "initial":
        return "先拆事实、未知、风险和一个低成本下一步。"
    if stage == "recurrence":
        return "承接同一事件线，不要求用户重讲背景。"
    if stage == "turning_point":
        return "指出变化点，并帮助用户重新排序。"
    if stage == "partial_resolution":
        return "核对已完成动作和剩余风险，不夸大结果。"
    return "提炼稳定处理模式，避免机械复述日志。"


def _event_line_id(persona_id: str, event_id: str) -> str:
    digest = hashlib.sha1(f"{persona_id}:{event_id}".encode("utf-8")).hexdigest()[:8]
    return f"L_{persona_id.lower()}_{event_id.lower()}_{digest}"


def _cn_list(values: list[str]) -> list[str]:
    return [_cn_term(value) for value in values]


def _cn_term(value: str) -> str:
    return TERM_CN.get(str(value), zh_term(value))


def _cn_occupation(value: Any) -> str:
    text = str(value if value is not None else "")
    return OCCUPATION_CN.get(text, text or "现在这份工作")


def _join_values(value: Any, *, max_items: int) -> str:
    if isinstance(value, list):
        return "、".join(str(item) for item in value[:max_items] if item not in (None, ""))
    return str(value or "")


def _pick(values: list[str], index: int, fallback: str) -> str:
    if index < len(values) and values[index]:
        return values[index]
    return fallback


def _has_blank_fact_part(text: str) -> bool:
    return any(part in text for part in ("：。", "：，", "None", "[]"))


def _dedupe_texts(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _dedupe_fact_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        text = str(record.get("text") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        copied = dict(record)
        copied["text"] = text
        result.append(copied)
    return result


def _find_by_id(items: Any, key: str, value: str) -> dict[str, Any]:
    if not isinstance(items, list):
        raise ValueError(f"Expected a list while looking up {key}={value}.")
    for item in items:
        if isinstance(item, dict) and str(item.get(key)) == value:
            return item
    raise ValueError(f"Cannot find {key}={value}.")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item)]
