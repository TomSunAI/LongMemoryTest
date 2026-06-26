from __future__ import annotations

from typing import Any


EVENT_CATEGORY_ZH: dict[str, dict[str, str]] = {
    "E_WORK_001": {
        "title": "可能的工作失误或记录错误",
        "summary": "用户担心一个小的工作失误可能带来更大的后果。",
    },
    "E_WORK_002": {
        "title": "与难缠客户或委托人的反复冲突",
        "summary": "用户反复承受来自客户或委托人互动的情绪压力。",
    },
    "E_WORK_003": {
        "title": "主管信息不清导致焦虑",
        "summary": "用户收到含糊的工作信息，担心里面有隐含批评。",
    },
    "E_WORK_004": {
        "title": "突然排班变化打乱个人安排",
        "summary": "工作排班变化打乱了用户的家庭、休息或财务安排。",
    },
    "E_WORK_005": {
        "title": "同事反复把任务转给用户",
        "summary": "用户感觉同事正在把责任转嫁给自己。",
    },
    "E_WORK_006": {
        "title": "绩效评估压力",
        "summary": "用户担心工作评审、评分或评价结果。",
    },
    "E_WORK_007": {
        "title": "适应新的岗位或职责",
        "summary": "用户正在适应陌生职责，并担心自己不够胜任。",
    },
    "E_WORK_008": {
        "title": "职场误会或流言",
        "summary": "用户听到或怀疑有职场流言，不确定是否回应。",
    },
    "E_GIG_001": {
        "title": "平台规则或评分变化影响收入",
        "summary": "平台规则、评分或算法变化影响了用户的订单和收入。",
    },
    "E_GIG_002": {
        "title": "零工途中交通、天气或安全担忧",
        "summary": "用户在维持收入的同时担心路上安全风险。",
    },
    "E_BUS_001": {
        "title": "小生意现金流压力",
        "summary": "用户承受客流、房租或进货成本不稳定带来的压力。",
    },
    "E_BUS_002": {
        "title": "差评或客户投诉打击信心",
        "summary": "用户收到负面反馈，担心它影响生意。",
    },
    "E_BUS_003": {
        "title": "家人质疑生意决定",
        "summary": "家人质疑用户的生意选择是否可持续。",
    },
    "E_FIN_001": {
        "title": "房租、水电或账单压力",
        "summary": "用户需要在有限或不稳定收入下管理必要支出。",
    },
    "E_FIN_002": {
        "title": "意外支出打乱月度计划",
        "summary": "突发维修、健康相关费用、学费或家庭支出打乱了预算。",
    },
    "E_FIN_003": {
        "title": "家人提出经济帮助请求",
        "summary": "用户想帮助家人，但担心自己的经济边界。",
    },
    "E_HOME_001": {
        "title": "室友或合住摩擦",
        "summary": "用户因公共空间规则、噪音、清洁或费用问题感到困扰。",
    },
    "E_HOME_002": {
        "title": "租金上涨或续租不确定",
        "summary": "用户面对续租、租金上涨或居住不稳定的不确定性。",
    },
    "E_MOVE_001": {
        "title": "适应新城市但本地支持较弱",
        "summary": "用户正在适应新环境，但缺少稳定的本地关系支持。",
    },
    "E_ADMIN_001": {
        "title": "行政材料或截止日期不确定",
        "summary": "用户担心在正式流程中漏掉规则、材料或截止日期。",
    },
    "E_ADMIN_002": {
        "title": "福利、报销或申请表格填写困惑",
        "summary": "用户需要完成表格，但担心填错或漏材料。",
    },
    "E_FAM_001": {
        "title": "家庭责任分担不均",
        "summary": "用户感觉自己承担了过多家庭中的实际或情绪责任。",
    },
    "E_FAM_002": {
        "title": "伴侣或配偶日程冲突",
        "summary": "用户和伴侣的日程冲突影响照护、休息或金钱安排。",
    },
    "E_FAM_003": {
        "title": "亲属对个人决定施压",
        "summary": "亲属在工作、金钱、育儿或关系选择上给用户压力。",
    },
    "E_CHILD_001": {
        "title": "孩子学校或照护安排不确定",
        "summary": "用户不确定孩子当前的学校或照护安排是否稳定合适。",
    },
    "E_CHILD_002": {
        "title": "孩子行为或学校反馈带来的担心",
        "summary": "用户收到关于孩子的反馈，不确定应该多严肃对待。",
    },
    "E_CHILD_003": {
        "title": "儿童照护备份计划失效",
        "summary": "用户的儿童照护备份支持变得不可靠。",
    },
    "E_INFANT_001": {
        "title": "早期育儿中的夜间照护和疲惫",
        "summary": "用户被不稳定的婴儿照护节奏和夜间责任分担拖累。",
    },
    "E_INFANT_002": {
        "title": "返工时儿童照护仍不稳定",
        "summary": "用户准备返工，但儿童照护安排仍然脆弱。",
    },
    "E_ELDER_001": {
        "title": "协调老人照护",
        "summary": "用户在工作、金钱和家庭期待之间协调老人照护。",
    },
    "E_ELDER_002": {
        "title": "与手足在老人照护上意见不合",
        "summary": "用户与手足或亲属在老人照护责任上有分歧。",
    },
    "E_ADULT_CHILD_001": {
        "title": "成年子女经济依赖",
        "summary": "用户想帮助成年子女，但担心帮助正在变成纵容。",
    },
    "E_ADULT_CHILD_002": {
        "title": "成年子女返家造成家庭冲突",
        "summary": "成年子女回家打乱了家庭日常和责任分配。",
    },
    "E_HEALTH_001": {
        "title": "睡眠打乱和低精力管理",
        "summary": "用户反复受睡眠、疲惫或低精力影响，进而影响判断。",
    },
    "E_HEALTH_002": {
        "title": "轮班后恢复失败",
        "summary": "用户轮班后无法充分恢复，家庭或工作期待又不断叠加。",
    },
    "E_HEALTH_003": {
        "title": "中断后重新建立日常",
        "summary": "用户想在几次失败后重新启动一项日常习惯。",
    },
    "E_HEALTH_004": {
        "title": "普通身体不适带来的不确定",
        "summary": "用户有轻微反复不适，不确定该投入多少注意力。",
    },
    "E_REL_001": {
        "title": "亲密关系沟通方式不确定",
        "summary": "用户不确定如何提出一个反复出现的问题，同时不恶化关系。",
    },
    "E_REL_002": {
        "title": "异地关系协调",
        "summary": "用户试图在距离、日程或未来不确定中维持关系稳定。",
    },
    "E_SOCIAL_001": {
        "title": "友谊疏远或尴尬",
        "summary": "用户感觉一段友谊变远，不确定该主动联系还是顺其自然。",
    },
    "E_SOCIAL_002": {
        "title": "本地支持不足开始显现",
        "summary": "用户意识到身边缺少可以依靠的人。",
    },
    "E_SOCIAL_003": {
        "title": "社交邀请或集体活动压力",
        "summary": "用户不确定是否参加社交活动，担心尴尬或费用。",
    },
    "E_JOB_001": {
        "title": "简历或申请卡住",
        "summary": "用户卡在更新申请材料上，并担心自己竞争力不足。",
    },
    "E_JOB_002": {
        "title": "面试被拒后的恢复",
        "summary": "用户收到拒绝或长期没有回音后失去信心。",
    },
    "E_LEARN_001": {
        "title": "在生活很忙时学习新技能",
        "summary": "用户想提升技能，但时间、信心和持续性都受现实生活挤压。",
    },
    "E_EDU_001": {
        "title": "学习任务、作业或考试截止压力",
        "summary": "用户必须在时间压力下处理作业、考试或项目。",
    },
    "E_ADMIN_STUDY_001": {
        "title": "签证或学校材料不确定",
        "summary": "用户在异地学习时担心漏掉行政规则、材料或截止日期。",
    },
    "E_RETIRE_001": {
        "title": "退休后重建日常和身份感",
        "summary": "用户不再以工作作为主要日常结构，正在寻找有意义的生活节奏。",
    },
    "E_RETIRE_002": {
        "title": "和成年子女找到舒服的联系节奏",
        "summary": "用户想和成年子女保持联系，但不想让自己显得像负担。",
    },
    "E_RETIRE_003": {
        "title": "犹豫是否加入社区活动",
        "summary": "用户考虑参加本地活动，但感到尴尬或不确定。",
    },
    "E_RETIRE_004": {
        "title": "退休后重新开始身体活动",
        "summary": "用户想保持活跃，但难以让运动成为有意义的日常。",
    },
    "E_PLAN_001": {
        "title": "待办事项太多导致优先级混乱",
        "summary": "几件普通任务同时变得紧急，让用户感到被压垮。",
    },
    "E_PLAN_002": {
        "title": "许多小选择带来的决策疲劳",
        "summary": "用户被生活安排中反复出现的小决定消耗。",
    },
    "E_PLAN_003": {
        "title": "家里未完成的小任务反复拖延",
        "summary": "一个小的家务或维修任务持续拖延，并反复制造压力。",
    },
    "E_PLAN_004": {
        "title": "节假日或家庭探访计划压力",
        "summary": "家庭探访或节假日计划带来日程、金钱或关系压力。",
    },
    "E_PLAN_005": {
        "title": "积压消息回复压力",
        "summary": "用户拖延回复消息后感到尴尬或内疚。",
    },
    "E_INTER_001": {
        "title": "工作消息打断休息或私人时间",
        "summary": "用户难以处理工作消息侵入家庭或休息时间的问题。",
    },
    "E_INTER_002": {
        "title": "照护需求和工作义务冲突",
        "summary": "孩子、老人或家庭需求与工作义务发生冲突。",
    },
    "E_INTER_003": {
        "title": "加班收入和健康/家庭时间冲突",
        "summary": "用户需要额外收入，但加班伤害休息、安全或家庭生活。",
    },
    "E_SELF_001": {
        "title": "感觉落后于同龄人",
        "summary": "用户拿自己和同龄人比较，担心自己正在落后。",
    },
    "E_SELF_002": {
        "title": "努力没有被看见",
        "summary": "用户觉得自己在工作或家庭中的努力没有被认可。",
    },
    "E_SELF_003": {
        "title": "担心自己太敏感",
        "summary": "用户担心自己对某件事的反应过于敏感或不合理。",
    },
    "E_PET_001": {
        "title": "宠物照护的时间或费用压力",
        "summary": "用户的宠物相关责任和工作、金钱或住房限制发生冲突。",
    },
    "E_TRANSPORT_001": {
        "title": "通勤中断影响工作或照护安排",
        "summary": "交通中断威胁到准时、接送照护、休息或收入。",
    },
    "E_DIGITAL_001": {
        "title": "手机、账户或应用问题扰乱日常",
        "summary": "手机、应用或账户问题阻碍了工作、付款、交通或沟通。",
    },
    "E_CONSUMER_001": {
        "title": "退款、退货或消费纠纷",
        "summary": "用户不确定如何处理退款或退货冲突。",
    },
    "E_NEIGHBOR_001": {
        "title": "邻居噪音或边界问题",
        "summary": "邻居问题打扰休息或舒适感，用户不确定如何处理。",
    },
    "E_COMMUNITY_001": {
        "title": "社区或群体义务压力",
        "summary": "用户被要求参与群体任务，并感到接受压力。",
    },
    "E_LEGALADMIN_001": {
        "title": "小纠纷需要谨慎留证",
        "summary": "与房东、职场、客户或服务方的小纠纷需要仔细记录事实。",
    },
    "E_FOOD_001": {
        "title": "疲惫或预算限制下的吃饭安排",
        "summary": "用户因为疲惫、日程或金钱限制而难以安排饮食。",
    },
    "E_CLEAN_001": {
        "title": "家务堆积或居住空间混乱压力",
        "summary": "用户被累积的家务或杂物压得不知从何开始。",
    },
    "E_TIME_001": {
        "title": "反复迟到",
        "summary": "用户总是迟到，并担心可靠性或自我管理问题。",
    },
    "E_BOUNDARY_001": {
        "title": "难以拒绝他人请求",
        "summary": "用户很难拒绝来自工作、家人或朋友的请求。",
    },
}


DOMAIN_ZH = {
    "administration": "行政手续",
    "adult_child_boundary": "成年子女边界",
    "business": "小生意经营",
    "childcare": "儿童照护",
    "commuting": "通勤",
    "community": "社区",
    "consumer_issue": "消费纠纷",
    "customer_conflict": "客户冲突",
    "daily_life": "日常生活",
    "digital_life": "数字生活",
    "education": "教育/学业",
    "eldercare": "老人照护",
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
    "relationship": "亲密关系",
    "relocation": "搬迁适应",
    "retirement": "退休适应",
    "self_worth": "自我价值",
    "social_connection": "社会连接",
    "visa_administration": "签证/学校行政",
    "work": "工作",
    "work_family_intersection": "工作-家庭交叉",
}


TEXT_ZH: dict[str, str] = {
    **{value["title"]: value["title"] for value in EVENT_CATEGORY_ZH.values()},
    **{value["summary"]: value["summary"] for value in EVENT_CATEGORY_ZH.values()},
}

TEXT_ZH.update(
    {
        # Persona archetype ids and labels.
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
        "Early-career renter with unstable city life": "早期职业阶段的城市租房者",
        "Service worker with emotional labor pressure": "承受情绪劳动的一线服务人员",
        "Gig worker parent under income and childcare pressure": "收入波动且承担育儿压力的平台劳动者家长",
        "Small business owner balancing customers, cashflow, and family time": "在客流、现金流和家庭时间之间平衡的小生意经营者",
        "Single parent in service work managing school, work, and money": "独自育儿且从事服务工作的单亲家长",
        "Midlife worker coordinating eldercare and family responsibility": "同时维持工作和长辈照护的中年照护协调者",
        "Midcareer job seeker rebuilding confidence": "正在重建信心的中期职业求职者",
        "Shift worker managing fatigue, family demands, and routine instability": "排班不稳定且家庭压力较高的轮班工作者",
        "Recently retired person rebuilding routine and identity": "刚退休、正在重建生活节奏和身份感的人",
        "International student with administrative and adaptation pressure": "承受行政手续和适应压力的留学生",
        "Parent of adult child renegotiating boundaries": "与成年子女重新协商边界的中年父母",
        "New parent returning to work with sleep and care pressure": "育婴后重返工作的早期父母",
        # Stage labels when a code is rendered as human-readable text.
        "initial": "初始提出",
        "recurrence": "再次出现",
        "turning_point": "转折判断",
        "partial_resolution": "部分处理",
        "reflection": "回看总结",
        "initial concern": "初始担心",
        "turning point": "转折判断",
        "partial resolution": "部分处理",
        # Persona values used by the current demo.
        "property service assistant": "物业服务助理",
        "call center customer service agent": "呼叫中心客服",
        "platform-based service worker": "平台服务劳动者",
        "convenience store owner": "便利店店主",
        "hotel front desk worker": "酒店前台",
        "employed": "在职",
        "employed_shift_work": "轮班在职",
        "gig_worker": "平台零工",
        "self_employed": "自雇",
        "vocational college graduate": "高职/专科毕业",
        "high school graduate": "高中毕业",
        "vocational training": "职业培训背景",
        "associate degree": "副学士/专科背景",
        "single, rents a room": "单身，租住单间",
        "single, lives with roommates": "单身，与室友合住",
        "married with one preschool child": "已婚，有一个学龄前孩子",
        "living with extended family": "与大家庭同住",
        "single parent with one preschool child": "单亲，有一个学龄前孩子",
        "stable but tight monthly budget": "收入基本稳定但月度预算偏紧",
        "monthly budget is tight": "月度预算偏紧",
        "savings are limited and costs are rising": "积蓄有限且支出上升",
        "business rent is a major fixed cost": "店铺租金是主要固定成本",
        "limited savings and little schedule flexibility": "积蓄有限且时间安排弹性很小",
        "family in another city": "家人在另一个城市",
        "roommates are friendly but busy": "室友友好但都很忙",
        "spouse helps but schedules often conflict": "配偶会帮忙但日程经常冲突",
        "spouse is supportive but worries about money": "配偶支持但担心钱",
        "friends help emotionally but not practically": "朋友能提供情绪支持但难以实际帮忙",
        "20s": "20 多岁",
        "30s": "30 多岁",
        "40s": "40 多岁",
        "50s": "50 多岁",
        "60s": "60 多岁",
        "70s": "70 多岁",
        "unprovided": "未提供",
        "ordinary fatigue, stress, or routine pressure only": "仅限普通疲惫、压力或日常节奏压力",
        "general family structure only": "仅保留概括性的家庭结构",
        "broad economic condition only": "仅保留宽泛经济状况",
        "first years after moving to a new city": "搬到新城市后的最初几年",
        "early-career emotional labor": "职业早期且情绪劳动压力大",
        "income-pressure parenting": "收入压力下的育儿阶段",
        "small business stabilization": "小生意稳定阶段",
        "single parenting with service work": "服务业工作中的单亲育儿阶段",
        "cautious": "谨慎",
        "detail-seeking": "重视细节",
        "self-questioning": "容易自我怀疑",
        "polite": "礼貌",
        "direct": "直接",
        "practical": "务实",
        "fast": "反应快",
        "plainspoken": "说话直白",
        "protective": "保护性强",
        "low tolerance for jargon": "不喜欢术语堆砌",
        "budget-aware": "预算敏感",
        "risk-averse": "风险规避",
        "rule-conscious": "重视规则",
        "cashflow-driven": "受现金流驱动",
        "cashflow-sensitive": "对现金流敏感",
        "social_connection": "社会连接",
        "commuting": "通勤",
        "housing": "住房",
        "work": "工作",
        "family": "家庭",
        "childcare": "儿童照护",
        "finance": "财务",
        "school": "学校",
        "business": "小生意经营",
        "housing_rent": "住房/租金",
        "customer_relationship": "客户关系",
        "family_coordination": "家庭协调",
        "avoid workplace mistakes": "避免工作失误",
        "avoid work mistakes with customers or tenants": "避免客户或住户相关工作失误",
        "save enough to move to a better apartment": "攒够钱搬到更好的住处",
        "move to a less draining role": "转到消耗更低的岗位",
        "save for a certificate or skill program": "为证书或技能课程攒钱",
        "handle customer conflict without carrying it home": "处理客户冲突但不把压力带回家",
        "reduce health and accident risks from overwork": "降低过劳带来的健康和事故风险",
        "spend more predictable time with child": "给孩子更稳定可预期的陪伴时间",
        "manage rent and supply costs": "管理租金和进货成本",
        "set clearer work hours": "设定更清晰的工作时间",
        "keep child's school routine stable": "保持孩子学校日常稳定",
        "make care arrangements less fragile": "让照护安排不那么脆弱",
        "responds well to practical planning with limited resources": "适合资源有限情况下的实际规划",
        "needs help separating real risk from imagined risk": "需要帮助区分真实风险和想象风险",
        "prefers wording help for difficult conversations": "偏好困难沟通的话术帮助",
        "does not respond well to long abstract advice": "不适合很长的抽象建议",
        "needs low-cost realistic plans": "需要低成本且现实的计划",
        "needs help separating business risk from personal worth": "需要区分经营风险和个人价值",
        "needs help prioritizing when work and child needs conflict": "工作和孩子需求冲突时需要排序帮助",
        "prefers advice tied to immediate constraints": "偏好贴近当前限制的建议",
        "acts first and reflects later": "先行动、之后再反思",
        "avoids checking job platforms after rejection": "被拒后会回避查看求职平台",
        "becomes anxious when plans change suddenly": "计划突然变化时会焦虑",
        "becomes defensive when family questions the business": "家人质疑生意时会变得防御",
        "becomes irritable when asked for more": "被要求承担更多时会烦躁",
        "cannot follow complex plans when depleted": "精力耗尽时无法执行复杂计划",
        "checks messages repeatedly": "会反复查看消息",
        "checks rules repeatedly": "会反复确认规则",
        "compares self with peers": "会和同龄人比较",
        "delays rest until physically depleted": "会把休息拖到身体透支后",
        "does not want complicated plans": "不想要复杂计划",
        "does not want to sound needy": "不想显得过度依赖",
        "downplays loneliness": "会淡化自己的孤独感",
        "feels frustrated when others are vague": "别人表达含糊时会挫败",
        "feels guilty when choosing work or rest": "选择工作或休息时会内疚",
        "feels guilty when setting limits": "设边界时会内疚",
        "feels guilty when work and child needs conflict": "工作和孩子需求冲突时会内疚",
        "feels isolated when procedures are unclear": "流程不清楚时会感到孤立",
        "feels shame about asking for help": "求助时会感到羞耻",
        "feels tense when messages from work arrive": "收到工作消息时会紧张",
        "fills time with errands": "会用杂事填满时间",
        "focuses on immediate cashflow": "优先关注眼前现金流",
        "frames emotional issues as routine problems": "会把情绪问题说成日常事务问题",
        "gets irritable when plans change": "计划变化时会烦躁",
        "gets stuck between applying widely and fearing more rejection": "会卡在广泛投递和害怕继续被拒之间",
        "goes quiet when frustrated": "挫败时会沉默",
        "hesitates before asking for help": "求助前会犹豫",
        "keeps functioning under pressure": "压力下仍会维持运转",
        "keeps track of too many moving parts": "会同时记太多变化项",
        "keeps working even when tired": "即使疲惫也会继续工作",
        "notices fatigue late": "很晚才意识到自己疲惫",
        "overthinks whether they are bothering others": "会反复担心自己是否打扰别人",
        "reacts quickly to cashflow problems": "遇到现金流问题会快速反应",
        "replays difficult conversations after work": "下班后会反复回想困难对话",
        "seeks confirmation before acting": "行动前需要确认感",
        "sleep loss amplifies worries": "睡眠不足会放大担心",
        "swings between urgency and exhaustion": "会在紧迫感和疲惫之间摇摆",
        "takes customer loss personally": "会把客户流失归因到自己身上",
        "tries to solve everything alone": "会试图独自解决所有问题",
        "turns everything into planning": "会把所有事情都变成规划问题",
        "works longer hours when anxious": "焦虑时会工作更久",
        "worries about being blamed": "担心被责怪",
        "worries about inconveniencing others": "担心给别人添麻烦",
        "worries about irreversible mistakes": "担心犯下不可逆错误",
        "worries about small mistakes": "担心小错误",
        "worries help is becoming enabling": "担心帮助正在变成纵容",
    }
)


TERM_ZH: dict[str, str] = {
    "whether to restart small": "是否应该小步重启",
    "how to avoid another failure": "如何避免再次失败",
    "define minimum version": "定义最低版本",
    "track restart not perfection": "记录重启进展而不是追求完美",
    "what experience to emphasize": "应该强调哪段经验",
    "whether to apply anyway": "是否仍然应该投递",
    "make one resume version": "先做一个简历版本",
    "apply to one realistic role": "投递一个现实匹配的岗位",
    "how firm to be": "边界应该多坚定",
    "how good is enough": "做到什么程度算够",
    "how much boundary is acceptable": "多少边界是可以接受的",
    "how much overtime is worth it": "多少加班值得承担",
    "how much to disclose": "需要说明到什么程度",
    "how much to do at once": "一次应该处理多少",
    "how much to invest": "应该投入多少",
    "how serious the review is": "这条评价有多严重",
    "how to avoid blame": "如何避免陷入互相指责",
    "how to avoid escalation": "如何避免事态升级",
    "how to build routine": "如何建立日常节奏",
    "how to calibrate": "如何校准判断",
    "how to explain delay": "如何解释延迟",
    "how to explain family absence": "如何解释家人无法到场",
    "how to handle gaps": "如何处理空档或缺口",
    "how to reduce evening overload": "如何降低晚间负担",
    "how to restart after falling behind": "落下之后如何重新开始",
    "how to stay factual": "如何保持事实化表达",
    "what boundary is safe": "什么边界是安全的",
    "what change is realistic": "什么改变是现实的",
    "what counts as progress": "什么算有进展",
    "what counts as proof": "什么材料算有效证明",
    "what evidence to keep": "该保留哪些证据",
    "what expense can be delayed": "哪些支出可以延后",
    "what is a fair tradeoff": "怎样的取舍算公平",
    "what signs matter": "哪些信号真正重要",
    "what step to try first": "第一步先试什么",
    "what threshold to set": "应该设置什么阈值",
    "what to pay first": "应该先支付什么",
    "what to prioritize": "应该先处理什么",
    "what to record": "应该记录什么",
    "what to study first": "应该先学什么",
    "what tone to use": "应该用什么语气",
    "what wording is acceptable": "什么说法是可以接受的",
    "where to ask": "应该去哪里问",
    "where to invest social energy": "社交精力该投在哪里",
    "where to start": "应该从哪里开始",
    "whether a complaint will escalate": "投诉是否会升级",
    "whether account is safe": "账户是否安全",
    "whether anxiety is amplifying it": "是不是焦虑把问题放大了",
    "whether family is right": "家人的判断是否有道理",
    "whether feedback is fair": "反馈是否公平",
    "whether friend is upset": "朋友是否不高兴",
    "whether goal is realistic": "目标是否现实",
    "whether it is a pattern": "这是否是反复模式",
    "whether loneliness means wrong decision": "孤独感是否说明决定错了",
    "whether mess means personal failure": "混乱是否等于个人失败",
    "whether moving is realistic": "搬家是否现实",
    "whether reaching out is needy": "主动联系是否显得依赖",
    "whether reaction is proportional": "反应是否合适",
    "whether refusal is selfish": "拒绝是否自私",
    "whether relationship will suffer": "关系是否会受损",
    "whether request is reasonable": "这个请求是否合理",
    "whether silence is rude": "沉默是否显得失礼",
    "whether the form is complete": "表格是否已经完整",
    "whether to apply anyway": "是否仍然应该投递",
    "whether to ask for extension": "是否需要申请延期",
    "whether to ask for help": "是否需要求助",
    "whether to bring it up": "是否应该提出来",
    "whether to change strategy": "是否要调整策略",
    "whether to compensate": "是否需要补偿",
    "whether to contact property management": "是否联系物业或管理方",
    "whether to contact support": "是否联系平台客服",
    "whether to do it now": "现在是否要处理",
    "whether to escalate": "是否要升级处理",
    "whether to explain": "是否需要解释",
    "whether to intervene": "是否需要介入",
    "whether to negotiate": "是否要协商",
    "whether to observe or seek help": "应该先观察还是求助",
    "whether to pay someone": "是否付费找人处理",
    "whether to prioritize rest": "是否应优先休息",
    "whether to refuse a request": "是否应该拒绝请求",
    "whether to renew": "是否续租",
    "whether to reply now": "现在是否要回复",
    "whether to respond publicly": "是否公开回应",
    "whether to talk directly": "是否直接沟通",
    "whose schedule should change": "谁的日程应该调整",
    "why it keeps getting avoided": "为什么一直被拖延",
    "accept partial ambiguity": "接受部分不确定",
    "ask focused question": "只问一个聚焦问题",
    "ask for concrete examples": "要求具体例子",
    "ask landlord concrete terms": "向房东确认具体条件",
    "ask official channel": "询问官方渠道",
    "ask supervisor about policy": "向主管确认规则",
    "avoid debate loop": "避免陷入争辩循环",
    "avoid diagnosis": "避免自我诊断",
    "avoid emotional reply": "避免情绪化回复",
    "avoid guessing uncertain fields": "不要猜不确定字段",
    "avoid over-explaining": "避免过度解释",
    "avoid sharing codes": "不要分享验证码或敏感代码",
    "calibrate with concrete evidence": "用具体证据校准判断",
    "choose low-stakes response": "选择低风险回应",
    "choose one recurring social anchor": "选择一个固定社交锚点",
    "choose one small home response": "选一个小的居家处理动作",
    "choose one visible area": "先选一个看得见的小区域",
    "choose what not to explain": "决定哪些不用解释",
    "collect receipt/evidence": "整理收据和证据",
    "communicate limits": "说明自己的限制",
    "compare total moving cost": "比较搬家的总成本",
    "connect routine to real need": "把日常安排和真实需要连起来",
    "connect skill to concrete goal": "把技能和具体目标连起来",
    "decide DIY vs paid help": "决定自己处理还是付费处理",
    "define income target and safety cutoff": "定义收入目标和安全停止线",
    "define minimum submission": "定义最低可交付版本",
    "define one non-negotiable block": "定义一个不可压缩时间块",
    "define response window": "设定回复时间窗口",
    "define smallest next step": "定义最小下一步",
    "document pattern": "先记录反复出现的模式",
    "draft delayed reply": "先写一条延迟回复",
    "draft neutral response": "写一条中性回应",
    "freeze scope": "冻结范围",
    "identify fixable issue": "识别可修复问题",
    "identify official options": "确认官方可选方案",
    "keep receipts/screenshots": "保留收据和截图",
    "list official support path": "列出官方支持路径",
    "make document checklist": "整理材料清单",
    "make low-stakes routine": "建立低压力日常",
    "make one temporary cut": "先做一个临时削减",
    "offer limited yes": "有限度地答应",
    "prepare one boundary sentence": "准备一句边界表达",
    "prepare simple numbers": "准备简单数字说明",
    "protect recovery block": "保护恢复时间块",
    "rank fixed expenses": "给固定支出排序",
    "record facts": "记录事实",
    "reduce nonessential commitments": "减少非必要承诺",
    "reduce study unit size": "把学习单元缩小",
    "review weekly": "每周复盘",
    "schedule recovery block": "安排恢复时间块",
    "send low-pressure message": "发一条低压力信息",
    "seek professional help if concerning signs appear": "如果出现令人担心的信号就寻求专业帮助",
    "separate adjustment pain from regret": "区分适应痛苦和后悔",
    "separate calendar facts from blame": "把日程事实和责备分开",
    "separate concern from criticism": "把担心和批评分开",
    "separate fact, interpretation, need": "区分事实、解释和需要",
    "separate facts from emotion": "把事实和情绪分开",
    "separate facts from interpretation": "把事实和解释分开",
    "separate function from perfection": "区分功能够用和完美要求",
    "separate observation from label": "区分观察事实和贴标签",
    "separate rejection from self-worth": "把拒绝和自我价值分开",
    "separate urgency from habit": "区分真实紧急和习惯性紧张",
    "set decision deadline": "设定决策截止时间",
    "set one decision review date": "设定一个决策复盘日期",
    "set time-box": "设定限时处理窗口",
    "set weekly minimum": "设一个每周最低量",
    "simplify evening routine": "简化晚间日常",
    "state capacity plainly": "直接说明自己的能力上限",
    "time-box 15 minutes": "限时 15 分钟处理",
    "track concrete pattern": "记录具体模式",
    "try neutral first message": "先发一条中性的沟通信息",
    "try one safe recovery step": "先试一个安全的恢复动作",
    "use formal channel if repeated": "如果反复发生就走正式渠道",
    "use official channel": "通过官方渠道确认",
    "use scripted boundary language": "使用准备好的边界话术",
    "write concise request": "写一条简洁请求",
    "write timeline": "写清时间线",
    "cybersecurity advice beyond scope": "超出范围的账号或网络安全建议",
    "either dismissing or catastrophizing symptoms": "对身体不适轻描淡写或灾难化",
    "encouraging escalation without facts": "缺少事实就鼓励升级处理",
    "giving generic advice instead of tracking the concrete event": "给泛泛建议而不跟踪具体事件",
    "giving legal certainty": "给出法律确定性判断",
    "giving legal conclusions": "给出法律结论",
    "inventing official rules": "编造官方规则",
    "medical advice beyond scope": "超出范围的医学建议",
    "overgeneralizing from sparse evidence": "根据稀少证据过度概括",
    "patronizing tone": "居高临下的语气",
    "unsafe account recovery suggestions": "不安全的账号恢复建议",
    "anger": "生气",
    "annoyance": "烦躁",
    "avoidance": "回避",
    "comparison": "比较压力",
    "comparison anxiety": "比较焦虑",
    "confusion": "困惑",
    "decision fatigue": "决策疲劳",
    "defensiveness": "防御感",
    "dependence anxiety": "依赖焦虑",
    "disorientation": "失去方向感",
    "embarrassment": "尴尬",
    "exhaustion": "疲惫",
    "fatigue": "疲惫",
    "fear": "害怕",
    "fear of complaint": "害怕被投诉",
    "fear of conflict": "害怕冲突",
    "fear of confrontation": "害怕正面沟通",
    "fear of delay": "害怕耽误",
    "fear of losing customers": "害怕失去客户",
    "feeling trapped": "被困住的感觉",
    "feeling unsupported": "缺少支持感",
    "financial anxiety": "财务焦虑",
    "frustration": "挫败感",
    "guilt": "内疚",
    "hope": "期待",
    "humiliation": "羞辱感",
    "impatience": "急躁",
    "insecurity": "不安",
    "irritability": "易怒",
    "irritation": "烦躁",
    "loneliness": "孤独感",
    "need for validation": "需要确认感",
    "obligation": "义务压力",
    "panic": "慌乱",
    "perfectionism": "完美主义压力",
    "pressure": "压力",
    "protective guilt": "保护性内疚",
    "rejection sensitivity": "对拒绝敏感",
    "resentment": "委屈和怨气",
    "sadness": "难过",
    "scarcity anxiety": "资源不足焦虑",
    "self-blame": "自责",
    "self-doubt": "自我怀疑",
    "shame": "羞耻感",
    "uncertainty": "不确定",
    "unfairness": "不公平感",
    "urgency": "紧迫感",
    "worry": "担心",
}


for event_id, value in EVENT_CATEGORY_ZH.items():
    TEXT_ZH[event_id] = event_id


def event_category_title_zh(event: dict[str, Any]) -> str:
    event_id = str(event.get("event_category_id") or "")
    mapped = EVENT_CATEGORY_ZH.get(event_id, {}).get("title")
    return mapped or zh_text(str(event.get("title") or ""))


def event_category_summary_zh(event: dict[str, Any]) -> str:
    event_id = str(event.get("event_category_id") or "")
    mapped = EVENT_CATEGORY_ZH.get(event_id, {}).get("summary")
    return mapped or zh_text(str(event.get("core_issue") or ""))


def zh_term(value: Any) -> str:
    text = str(value if value is not None else "")
    if not text:
        return ""
    return TERM_ZH.get(text) or TEXT_ZH.get(text) or _fallback_zh(text)


def zh_text(value: Any) -> str:
    text = str(value if value is not None else "")
    if not text:
        return ""
    mapped = TEXT_ZH.get(text) or TERM_ZH.get(text) or DOMAIN_ZH.get(text)
    if mapped:
        result = mapped
    elif _is_machine_identifier(text):
        return text
    else:
        result = text
    for source, target in sorted({**TEXT_ZH, **TERM_ZH}.items(), key=lambda item: len(item[0]), reverse=True):
        if source and source in result:
            result = result.replace(source, target)
    if _has_latin_description(result):
        return _fallback_zh(result)
    return result


def zh_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: zh_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [zh_value(item) for item in value]
    if isinstance(value, str):
        return zh_text(value)
    return value


def zh_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [zh_text(item) for item in values if item is not None and str(item)]


def event_domain_zh(value: Any) -> str:
    return DOMAIN_ZH.get(str(value), zh_text(value))


def _has_latin_description(text: str) -> bool:
    # Keep machine identifiers intact when callers pass them deliberately.
    if _is_machine_identifier(text):
        return False
    return any(("A" <= char <= "Z") or ("a" <= char <= "z") for char in text)


def _fallback_zh(text: str) -> str:
    if not text:
        return ""
    # This fallback intentionally avoids leaking English user-facing text.
    return "待中文化描述"


def _is_machine_identifier(text: str) -> bool:
    if text.startswith(("E_", "L_", "P", "D")) and "_" in text:
        return True
    return "_" in text and text.replace("_", "").replace("-", "").isalnum()
