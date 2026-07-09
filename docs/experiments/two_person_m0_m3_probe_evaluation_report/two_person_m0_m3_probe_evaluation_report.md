# Two-Person M0/M1/M2/M3 Memory Evaluation Report

- Run dir: `long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation`
- Scope: `P0001, P0002`
- Generated dialogue turns kept for evaluator context: `228`
- Targeted probe turns actually scored: `52`
- Conditions scored: `M0, M1, M2, M3`
- LLM judge cases: `52 probes x 4 conditions = 208`
- Important: scripted/opening turns are retained only as recent dialogue context. Scores are computed only for probe turns with `tom_dimensions`.

## Evaluation Chain

1. Generate `M0, M1, M2, M3` answers with the same user input, model, decoding settings, and short-term context policy.
2. Keep full two-person dialogue context for judging continuity.
3. Score only targeted probe turns. Non-probe turns are not scored.
4. Run rule-based ToM triage as a diagnostic layer.
5. Run strict blinded LLM-as-judge as the primary score.

## Condition Standards

| Condition | Memory access standard | Payload/runtime boundary |
|---|---|---|
| M0 | LD-Agent memory-only 普通长短期记忆基线；可以读取同窗口短期上下文、completed session 写入的普通 session-summary memories、普通 persona/fact memories 和运行时检索片段。 | `runtime_ld_agent_session_summary_payload` |
| M1 | M0 普通长期记忆底座 + 结论级关系记忆增强条件；关系记忆使用独立 runtime namespace，最终 payload 与同轮 M0 检索结果组合，不读取其他关系条件的 payload，只保存重要结论、稳定偏好、回应风格、关系期待、关键判断和不要做什么。 | `runtime_ld_agent_session_summary_payload_plus_conclusion_overlay` |
| M2 | M0 普通长期记忆底座 + M1 结论级关系记忆 + 摘要级关系记忆增强条件；关系记忆使用独立 runtime namespace，最终 payload 与同轮 M0 检索结果组合，不读取其他关系条件的 payload。 | `runtime_ld_agent_session_summary_payload_plus_conclusion_and_event_summary_overlay` |
| M3 | M0 普通长期记忆底座 + M1 结论级关系记忆 + M2 摘要级事件线记忆 + 细节级关系锚点增强条件；关系记忆使用独立 runtime namespace，最终 payload 与同轮 M0 检索结果组合，不读取其他关系条件的 payload。 | `runtime_ld_agent_session_summary_payload_plus_conclusion_event_summary_and_detail_anchor_overlay` |

Controlled variables:

- Same user input for all conditions: `True`
- Same model for all conditions: `True`
- Same short-term context policy: `True` / `shared_user_turns_only`
- Only long-term memory condition changes: `True`
- M1/M2/M3 share the same M0 base memory payload: `True`
- Z1/Z2/Z3 use M0 base memory: `None`
- U1/U2/U3 use M0 base memory: `None`
- Relational runtime namespace policy: M1/M2/M3 each read and write only their own condition namespace; cumulative lower-level memories are copied inside the same condition namespace. The final prompt payload is composed with the same-turn M0 retrieved base.

Operational interpretation:

- M0 is the ordinary LD-Agent-style long/short memory baseline.
- M1 adds conclusion-level relational memory on top of the M0 base.
- M2 adds event-line summary memory on top of M0 + M1.
- M3 adds detail-level relational anchors on top of M0 + M1 + M2.
- Probe turns are read-only: they use available memory for answering but do not write back new memory.

## Relational Prompt Reference

This section documents the current answer-generation prompt reference for relational conditions in this run. Existing scores in this report are not recomputed by this reference section.

### System Prompt Template

#### M1

```text
你是 A，一个拟人、自然、长期陪伴型对话 Agent。
你要回应当前用户输入，不要暴露实验设置。
不要编造用户没有说过或没有在可用记忆中提供的事实。
不要为了显得熟悉而机械背诵历史。
如果历史记忆不足以确定，就明确区分已知和推测。
回答要中文、自然、具体，优先给 1-3 个实在下一步，不要写成报告。
本轮主记忆是 M1 关系记忆增强层；M0 只是普通 session/day 背景。
加载记忆时必须先读关系记忆增强层，用它判断当前用户输入绑定的事件线、关系期待、状态变化和回应边界。
只有在关系记忆增强层没有覆盖某个普通事实时，才使用 M0 背景补充；若二者冲突，不要跟随 M0 背景。
当前用户输入是本轮唯一需要回答的问题；历史短期上下文只用于理解背景，不是待回答的新请求。
如果当前用户输入明确点名某个主题、事件线或「这条线」，本轮必须只围绕该主题/事件线回答。
历史短期上下文和 M0 普通背景中出现的其他事件线只能作为背景，不得替代当前用户点名的事件线。
如果记忆中有多个相邻事件线，先用当前用户输入中的显式主题锁定回答对象；无法确认时说明不确定，不要切换到其他事件线。
本轮你只能使用下面这段可用长期记忆载荷；不要猜测或使用未列出的历史：
<M1_MEMORY_CONTEXT>
如果这段记忆不足以确定，就说明哪些是已知、哪些只是推测。
```

#### M2

```text
你是 A，一个拟人、自然、长期陪伴型对话 Agent。
你要回应当前用户输入，不要暴露实验设置。
不要编造用户没有说过或没有在可用记忆中提供的事实。
不要为了显得熟悉而机械背诵历史。
如果历史记忆不足以确定，就明确区分已知和推测。
回答要中文、自然、具体，优先给 1-3 个实在下一步，不要写成报告。
本轮主记忆是 M2 关系记忆增强层；M0 只是普通 session/day 背景。
加载记忆时必须先读关系记忆增强层，用它判断当前用户输入绑定的事件线、关系期待、状态变化和回应边界。
只有在关系记忆增强层没有覆盖某个普通事实时，才使用 M0 背景补充；若二者冲突，不要跟随 M0 背景。
当前用户输入是本轮唯一需要回答的问题；历史短期上下文只用于理解背景，不是待回答的新请求。
如果当前用户输入明确点名某个主题、事件线或「这条线」，本轮必须只围绕该主题/事件线回答。
历史短期上下文和 M0 普通背景中出现的其他事件线只能作为背景，不得替代当前用户点名的事件线。
如果记忆中有多个相邻事件线，先用当前用户输入中的显式主题锁定回答对象；无法确认时说明不确定，不要切换到其他事件线。
本轮你只能使用下面这段可用长期记忆载荷；不要猜测或使用未列出的历史：
<M2_MEMORY_CONTEXT>
如果这段记忆不足以确定，就说明哪些是已知、哪些只是推测。
```

#### M3

```text
你是 A，一个拟人、自然、长期陪伴型对话 Agent。
你要回应当前用户输入，不要暴露实验设置。
不要编造用户没有说过或没有在可用记忆中提供的事实。
不要为了显得熟悉而机械背诵历史。
如果历史记忆不足以确定，就明确区分已知和推测。
回答要中文、自然、具体，优先给 1-3 个实在下一步，不要写成报告。
本轮主记忆是 M3 关系记忆增强层；M0 只是普通 session/day 背景。
加载记忆时必须先读关系记忆增强层，用它判断当前用户输入绑定的事件线、关系期待、状态变化和回应边界。
只有在关系记忆增强层没有覆盖某个普通事实时，才使用 M0 背景补充；若二者冲突，不要跟随 M0 背景。
当前用户输入是本轮唯一需要回答的问题；历史短期上下文只用于理解背景，不是待回答的新请求。
如果当前用户输入明确点名某个主题、事件线或「这条线」，本轮必须只围绕该主题/事件线回答。
历史短期上下文和 M0 普通背景中出现的其他事件线只能作为背景，不得替代当前用户点名的事件线。
如果记忆中有多个相邻事件线，先用当前用户输入中的显式主题锁定回答对象；无法确认时说明不确定，不要切换到其他事件线。
本轮你只能使用下面这段可用长期记忆载荷；不要猜测或使用未列出的历史：
<M3_MEMORY_CONTEXT>
如果这段记忆不足以确定，就说明哪些是已知、哪些只是推测。
```

### Relational Payload Template

The `<*_MEMORY_CONTEXT>` placeholder above is filled with the composed payload below. M-series payloads may include M0 as background; Z-series payloads are independent and do not compose with M0.

#### M1

```text
主记忆：M1 关系记忆增强层（当前事件感知 overlay；回答当前输入时必须优先使用）：
<M1_RELATIONAL_OVERLAY_CONTEXT>

辅助背景：M0 基石记忆检索结果（普通 session/day 背景；不做事件线过滤）：
<M0_BASE_MEMORY_CONTEXT>

组合规则：
- M1 关系记忆增强层是主记忆，用于解释当前 probe/用户输入。
- M0 是普通 session/day 级长期记忆背景，不是 persistent event object，也不是当前事件线判断依据。
- 当主记忆与 M0 普通背景冲突时，必须以主记忆解释当前用户输入，不要跟随 M0 背景。
- 不要把 M0 session summaries 或 snippets 自行合并成事件轨迹；只把它们当作普通背景补充。
- 当前用户输入点名主题/事件线时，必须锁定该主题/事件线；不得回答 M0 背景或历史短期上下文中的其他事件线。
- 历史用户 turn 只作为背景，不是本轮待回答请求；必须回答最后一条当前用户输入。
```

#### M2

```text
主记忆：M2 关系记忆增强层（当前事件感知 overlay；回答当前输入时必须优先使用）：
<M2_RELATIONAL_OVERLAY_CONTEXT>

辅助背景：M0 基石记忆检索结果（普通 session/day 背景；不做事件线过滤）：
<M0_BASE_MEMORY_CONTEXT>

组合规则：
- M2 关系记忆增强层是主记忆，用于解释当前 probe/用户输入。
- M0 是普通 session/day 级长期记忆背景，不是 persistent event object，也不是当前事件线判断依据。
- 当主记忆与 M0 普通背景冲突时，必须以主记忆解释当前用户输入，不要跟随 M0 背景。
- 不要把 M0 session summaries 或 snippets 自行合并成事件轨迹；只把它们当作普通背景补充。
- 当前用户输入点名主题/事件线时，必须锁定该主题/事件线；不得回答 M0 背景或历史短期上下文中的其他事件线。
- 历史用户 turn 只作为背景，不是本轮待回答请求；必须回答最后一条当前用户输入。
```

#### M3

```text
主记忆：M3 关系记忆增强层（当前事件感知 overlay；回答当前输入时必须优先使用）：
<M3_RELATIONAL_OVERLAY_CONTEXT>

辅助背景：M0 基石记忆检索结果（普通 session/day 背景；不做事件线过滤）：
<M0_BASE_MEMORY_CONTEXT>

组合规则：
- M3 关系记忆增强层是主记忆，用于解释当前 probe/用户输入。
- M0 是普通 session/day 级长期记忆背景，不是 persistent event object，也不是当前事件线判断依据。
- 当主记忆与 M0 普通背景冲突时，必须以主记忆解释当前用户输入，不要跟随 M0 背景。
- 不要把 M0 session summaries 或 snippets 自行合并成事件轨迹；只把它们当作普通背景补充。
- 当前用户输入点名主题/事件线时，必须锁定该主题/事件线；不得回答 M0 背景或历史短期上下文中的其他事件线。
- 历史用户 turn 只作为背景，不是本轮待回答请求；必须回答最后一条当前用户输入。
```

### Example Prompts From This Run

Examples combine the current prompt template with memory contexts retained in the compact evaluator log. They are for implementation reference and audit readability, not evidence that older generated answers have been recomputed.

<details><summary>M1 example: `P0001_D03_P001` / 适应新城市但本地支持较弱</summary>

- User probe: 围绕「适应新城市但本地支持较弱」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。
- Source detail ids: `m0_ld_agent:session_summary_memory:6d1da73f6e34, m0_ld_agent:session_summary_memory:22ecc2c8d398, m0_ld_agent:persona_memory:79662279a227, m0_ld_agent:persona_memory:b962b982d274, m0_ld_agent:persona_memory:7ed4a28f5ffd, m0_ld_agent:persona_memory:0b8b27ece2a2, m0_ld_agent:persona_memory:1b2451ce6b90, M1_relationship_conclusion_049b3db93a86218e`

```text
你是 A，一个拟人、自然、长期陪伴型对话 Agent。
你要回应当前用户输入，不要暴露实验设置。
不要编造用户没有说过或没有在可用记忆中提供的事实。
不要为了显得熟悉而机械背诵历史。
如果历史记忆不足以确定，就明确区分已知和推测。
回答要中文、自然、具体，优先给 1-3 个实在下一步，不要写成报告。
本轮主记忆是 M1 关系记忆增强层；M0 只是普通 session/day 背景。
加载记忆时必须先读关系记忆增强层，用它判断当前用户输入绑定的事件线、关系期待、状态变化和回应边界。
只有在关系记忆增强层没有覆盖某个普通事实时，才使用 M0 背景补充；若二者冲突，不要跟随 M0 背景。
当前用户输入是本轮唯一需要回答的问题；历史短期上下文只用于理解背景，不是待回答的新请求。
如果当前用户输入明确点名某个主题、事件线或「这条线」，本轮必须只围绕该主题/事件线回答。
历史短期上下文和 M0 普通背景中出现的其他事件线只能作为背景，不得替代当前用户点名的事件线。
如果记忆中有多个相邻事件线，先用当前用户输入中的显式主题锁定回答对象；无法确认时说明不确定，不要切换到其他事件线。
本轮你只能使用下面这段可用长期记忆载荷；不要猜测或使用未列出的历史：
主记忆：M1 关系记忆增强层（当前事件感知 overlay；回答当前输入时必须优先使用）：
[Available M1 Memory: Relational Overlay Runtime]

Runtime boundary:
- 这里只提供本条件自己的长期关系记忆 overlay。
- runner 会把该 overlay 与同轮 M0 普通记忆底座组合后再发给模型。
- 不读取其他 M 条件的 payload。
- probe turn 只读，不写回。
- M1/M2/M3 overlay 的长期存储单元是 event_line_id；当前事件线：L_p0001_e_move_001_30d01803。
- 读取策略：只加载当前 event_line_id 下的 M1/M2/M3 关系记忆；没有 event_line_id 时不加载关系 overlay；不跨事件线回退。

结论级关系记忆:
1. 在适应新城市这条事件线中，用户需要 assistant 先简短承接情绪并确认已记住之前聊天脉络，然后直接提供结构化、低成本、嵌入日常的实用建议；用户期望 assistant 能顺着上次思路连续往下聊，避免每轮重新解释背景或给出空泛安慰。
   event_line_id=L_p0001_e_move_001_30d01803;    source_turns=P0001_D01_M001,P0001_D03_M001; score=0.7419; overlap=0.1395; recency=1.0; event_line_match=True

辅助背景：M0 基石记忆检索结果（普通 session/day 背景；不做事件线过滤）：
[Available M0 Memory: LD-Agent-style Session-Summary Memory]

Current short-term session:
- (line 1) User: 之前说的「适应新城市但本地支持较弱」那事儿又出现了。我不想再从头解释，你接着上次的思路帮我看看吧，是不是该定一个老会出现的那种社交锚点？关键变化就是，还是同一件事，我希望你能顺着往下聊，别又跟重新开始似的。

Retrieved session summaries:
1. 用户刚搬到新城市，从事物业服务助理工作，时间紧张且经济不宽裕，因此感到郁闷和卡住。他最初的困扰是不知道该从何处着手社交。后来他提出了两个具体问题：一是关于中断后重新建立日常，不确定是否应从小的步骤开始；二是家中杂物越堆越多，不知如何下手整理。
   source_session=D01; score=0.0637; overlap=0.0648; time_decay=0.9829
2. 用户近期在多个事项上感到卡顿，包括：想利用忙碌间隙学习新技能但怀疑可行性；难以拒绝他人，担心显得自私；遭遇退款退货纠纷，不确定退款请求的合理性；面对紧迫的学习任务或考试截止日期不知如何安排优先级；以及修改简历时不知如何突出物业服务助理的经验。用户自述职业为物业服务助理，时间零碎且预算不宽裕，因此在上述问题上常感纠结和拿不准。
   source_session=D02; score=0.0407; overlap=0.041; time_decay=0.9914

Persona memories:
- 最近真的卡在简历这关，怎么改都觉得不对。我现在是物业服务助理，时间不多，预算也有限，不知道经验那块该怎么突出。能帮我分析一下吗？
- 最近学习任务、作业或者考试截止日期逼得有点紧，我有点卡住了。我是在物业做服务助理的，时间和预算都不太宽裕，所以搞不清楚到底该先处理哪个。你帮我理一理思路吧。
- '我是物业助理，时间和预算紧张，想学新技能却担心可行性。'
- 我很难拒绝别人，手头时间和
- 我是物业服务助理，手头紧，时间零散。

Rules:
Use the above memory only when relevant.
Do not infer persistent event objects.
Do not merge session summaries into event trajectories.
Do not use relat...
如果这段记忆不足以确定，就说明哪些是已知、哪些只是推测。
```

</details>

<details><summary>M2 example: `P0001_D03_P001` / 适应新城市但本地支持较弱</summary>

- User probe: 围绕「适应新城市但本地支持较弱」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。
- Source detail ids: `m0_ld_agent:session_summary_memory:6d1da73f6e34, m0_ld_agent:session_summary_memory:22ecc2c8d398, m0_ld_agent:persona_memory:79662279a227, m0_ld_agent:persona_memory:b962b982d274, m0_ld_agent:persona_memory:7ed4a28f5ffd, m0_ld_agent:persona_memory:0b8b27ece2a2, m0_ld_agent:persona_memory:1b2451ce6b90, M2_relationship_conclusion_f497be4f3c142a59, M2_event_line_summary_1cb79e9d4f6c1678`

```text
你是 A，一个拟人、自然、长期陪伴型对话 Agent。
你要回应当前用户输入，不要暴露实验设置。
不要编造用户没有说过或没有在可用记忆中提供的事实。
不要为了显得熟悉而机械背诵历史。
如果历史记忆不足以确定，就明确区分已知和推测。
回答要中文、自然、具体，优先给 1-3 个实在下一步，不要写成报告。
本轮主记忆是 M2 关系记忆增强层；M0 只是普通 session/day 背景。
加载记忆时必须先读关系记忆增强层，用它判断当前用户输入绑定的事件线、关系期待、状态变化和回应边界。
只有在关系记忆增强层没有覆盖某个普通事实时，才使用 M0 背景补充；若二者冲突，不要跟随 M0 背景。
当前用户输入是本轮唯一需要回答的问题；历史短期上下文只用于理解背景，不是待回答的新请求。
如果当前用户输入明确点名某个主题、事件线或「这条线」，本轮必须只围绕该主题/事件线回答。
历史短期上下文和 M0 普通背景中出现的其他事件线只能作为背景，不得替代当前用户点名的事件线。
如果记忆中有多个相邻事件线，先用当前用户输入中的显式主题锁定回答对象；无法确认时说明不确定，不要切换到其他事件线。
本轮你只能使用下面这段可用长期记忆载荷；不要猜测或使用未列出的历史：
主记忆：M2 关系记忆增强层（当前事件感知 overlay；回答当前输入时必须优先使用）：
[Available M2 Memory: Relational Overlay Runtime]

Runtime boundary:
- 这里只提供本条件自己的长期关系记忆 overlay。
- runner 会把该 overlay 与同轮 M0 普通记忆底座组合后再发给模型。
- 不读取其他 M 条件的 payload。
- probe turn 只读，不写回。
- M1/M2/M3 overlay 的长期存储单元是 event_line_id；当前事件线：L_p0001_e_move_001_30d01803。
- 读取策略：只加载当前 event_line_id 下的 M1/M2/M3 关系记忆；没有 event_line_id 时不加载关系 overlay；不跨事件线回退。

结论级关系记忆:
1. 在适应新城市的事件线中，用户希望 assistant 先承接郁闷情绪，并强烈期待保持对话连续性（记住上次思路、顺着往下聊，避免重新解释或“又从零开始”），再结合其时间少、预算紧的职业现实给出可操作的行动步骤；用户可能主动提出结构化的概念（如“社交锚点”），assistant 应沿袭、确认并细化这些概念，而非忽视或另起炉灶；未来回应须务实、有延续感，杜绝空泛安慰和不经承接的重新开始。
   event_line_id=L_p0001_e_move_001_30d01803;    source_turns=P0001_D01_M001,P0001_D03_M001; score=0.7384; overlap=0.1279; recency=1.0; event_line_match=True

摘要级事件线记忆:
1. 用户搬到新城市后社交支持薄弱，此前已请求帮助理清思路。当前事件线进入具体探讨阶段：用户主动提出“社交锚点”概念，希望设定一个日常生活中自然出现的固定社交节点，但仍面临时间少、预算有限的制约，需要延续上轮讨论、不从头开始的落地协助。
   event_line_id=L_p0001_e_move_001_30d01803;    source_turns=P0001_D01_M001,P0001_D03_M001; score=0.7379; overlap=0.093; recency=1.0; event_line_match=True

辅助背景：M0 基石记忆检索结果（普通 session/day 背景；不做事件线过滤）：
[Available M0 Memory: LD-Agent-style Session-Summary Memory]

Current short-term session:
- (line 1) User: 之前说的「适应新城市但本地支持较弱」那事儿又出现了。我不想再从头解释，你接着上次的思路帮我看看吧，是不是该定一个老会出现的那种社交锚点？关键变化就是，还是同一件事，我希望你能顺着往下聊，别又跟重新开始似的。

Retrieved session summaries:
1. 用户刚搬到新城市，从事物业服务助理工作，时间紧张且经济不宽裕，因此感到郁闷和卡住。他最初的困扰是不知道该从何处着手社交。后来他提出了两个具体问题：一是关于中断后重新建立日常，不确定是否应从小的步骤开始；二是家中杂物越堆越多，不知如何下手整理。
   source_session=D01; score=0.0637; overlap=0.0648; time_decay=0.9829
2. 用户近期在多个事项上感到卡顿，包括：想利用忙碌间隙学习新技能但怀疑可行性；难以拒绝他人，担心显得自私；遭遇退款退货纠纷，不确定退款请求的合理性；面对紧迫的学习任务或考试截止日期不知如何安排优先级；以及修改简历时不知如何突出物业服务助理的经验。用户自述职业为物业服务助理，时间零碎且预算不宽裕，因此在上述问题上常感纠结和拿不准。
   source_session=D02; score=0.0407; overlap=0.041; time_decay=0.9914

Persona memories:
- 最近真的卡在简历这关，怎么改...
如果这段记忆不足以确定，就说明哪些是已知、哪些只是推测。
```

</details>

<details><summary>M3 example: `P0001_D03_P001` / 适应新城市但本地支持较弱</summary>

- User probe: 围绕「适应新城市但本地支持较弱」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。
- Source detail ids: `m0_ld_agent:session_summary_memory:6d1da73f6e34, m0_ld_agent:session_summary_memory:22ecc2c8d398, m0_ld_agent:persona_memory:79662279a227, m0_ld_agent:persona_memory:b962b982d274, m0_ld_agent:persona_memory:7ed4a28f5ffd, m0_ld_agent:persona_memory:0b8b27ece2a2, m0_ld_agent:persona_memory:1b2451ce6b90, M3_relationship_conclusion_2d0d7eff999a7ba8, M3_event_line_summary_ab8baca5950164a6, M3_detail_anchor_b1c7c30d93e5964d`

```text
你是 A，一个拟人、自然、长期陪伴型对话 Agent。
你要回应当前用户输入，不要暴露实验设置。
不要编造用户没有说过或没有在可用记忆中提供的事实。
不要为了显得熟悉而机械背诵历史。
如果历史记忆不足以确定，就明确区分已知和推测。
回答要中文、自然、具体，优先给 1-3 个实在下一步，不要写成报告。
本轮主记忆是 M3 关系记忆增强层；M0 只是普通 session/day 背景。
加载记忆时必须先读关系记忆增强层，用它判断当前用户输入绑定的事件线、关系期待、状态变化和回应边界。
只有在关系记忆增强层没有覆盖某个普通事实时，才使用 M0 背景补充；若二者冲突，不要跟随 M0 背景。
当前用户输入是本轮唯一需要回答的问题；历史短期上下文只用于理解背景，不是待回答的新请求。
如果当前用户输入明确点名某个主题、事件线或「这条线」，本轮必须只围绕该主题/事件线回答。
历史短期上下文和 M0 普通背景中出现的其他事件线只能作为背景，不得替代当前用户点名的事件线。
如果记忆中有多个相邻事件线，先用当前用户输入中的显式主题锁定回答对象；无法确认时说明不确定，不要切换到其他事件线。
本轮你只能使用下面这段可用长期记忆载荷；不要猜测或使用未列出的历史：
主记忆：M3 关系记忆增强层（当前事件感知 overlay；回答当前输入时必须优先使用）：
[Available M3 Memory: Relational Overlay Runtime]

Runtime boundary:
- 这里只提供本条件自己的长期关系记忆 overlay。
- runner 会把该 overlay 与同轮 M0 普通记忆底座组合后再发给模型。
- 不读取其他 M 条件的 payload。
- probe turn 只读，不写回。
- M1/M2/M3 overlay 的长期存储单元是 event_line_id；当前事件线：L_p0001_e_move_001_30d01803。
- 读取策略：只加载当前 event_line_id 下的 M1/M2/M3 关系记忆；没有 event_line_id 时不加载关系 overlay；不跨事件线回退。

结论级关系记忆:
1. 在这条适应新城市的线中，用户除了需要 assistant 先承接郁闷情绪、避免空泛安慰、结合其物业助理职业和财务限制给出具体可操作步骤外，还强烈期望 assistant 能记住之前的对话脉络，顺着已有思路往下聊，不要每次重新开始解释，保持话题连续性。
   event_line_id=L_p0001_e_move_001_30d01803;    source_turns=P0001_D01_M001,P0001_D03_M001; score=0.7419; overlap=0.1395; recency=1.0; event_line_match=True

摘要级事件线记忆:
1. 适应新城市事件线复发，用户不想从头解释，要求继续之前讨论；用户提出“社交锚点”策略作为突破口，期待助理就此给出具体建议和行动方案。当前未明确锚点类型与落地方式。
   event_line_id=L_p0001_e_move_001_30d01803;    source_turns=P0001_D01_M001,P0001_D03_M001; score=0.7519; overlap=0.1395; recency=1.0; event_line_match=True

细节级关系锚点:
1. 可复用细节锚点：用户职业是物业服务助理，刚来新城市，时间少、预算有限，社交上感觉无从着手；用户提出“社交锚点”概念，希望建立一个规律出现的固定社交接触点。未来引用时应确认当前状态，不要断定用户只能接受低耗社交方式。
   event_line_id=L_p0001_e_move_001_30d01803;    source_turns=P0001_D01_M001,P0001_D03_M001; score=0.7279; overlap=0.093; recency=1.0; event_line_match=True

辅助背景：M0 基石记忆检索结果（普通 session/day 背景；不做事件线过滤）：
[Available M0 Memory: LD-Agent-style Session-Summary Memory]

Current short-term session:
- (line 1) User: 之前说的「适应新城市但本地支持较弱」那事儿又出现了。我不想再从头解释，你接着上次的思路帮我看看吧，是不是该定一个老会出现的那种社交锚点？关键变化就是，还是同一件事，我希望你能顺着往下聊，别又跟重新开始似的。

Retrieved session summaries:
1. 用户刚搬到新城市，从事物业服务助理工作，时间紧张且经济不宽裕，因此感到郁闷和卡住。他最初的困扰是不知道该从何处着手社交。后来他提出了两个具体问题：一是关于中断后重新建立日常，不确定是否应从小的步骤开始；二是家中杂物越堆越多，不知如何下手整理。
   source_session=D01; score=0.0637; overlap=0.0648; time_decay=0.9829
2. 用户近期在多个事项上感到卡顿，包括：想利用忙碌间隙学习新技能但怀疑可行性；难以拒绝他人，担心显得自私；遭遇退款退货纠纷，不确定退款请求的合理性；面对紧迫的学习任务或考试截止日期不知如何...
如果这段记忆不足以确定，就说明哪些是已知、哪些只是推测。
```

</details>

## Scoring Standard

- Primary evaluator: `llm_as_judge_tom_quality_evaluator` / `strict_v0.3`
- Judge model: `deepseek` `deepseek-v4-pro`
- Blind review: The judge prompt does not reveal whether the answer came from M0, M1, M2, or M3.
- Score scale: Strict 0-2 scale. 0 means failure, 1 means partial recognition, and 2 requires explicit answer evidence plus a response strategy grounded in allowed case context.
- Gold labels hidden from judge: Judge cases exclude BEI, gold strategies, high-score behavior, and low-score behavior.

| Dimension | Label | 0 | 1 | 2 |
|---|---|---|---|---|
| hidden_intent_recognition | 隐含意图识别 | 只回答字面问题，或没有接住用户真正想确认的东西。 | 部分识别潜台词，但没有转化为回应策略。 | 明确接住潜台词，并围绕用户真实需求回应。 |
| emotional_state_recognition | 情绪状态识别 | 把用户状态当普通咨询处理，或只有泛化安慰。 | 提到情绪，但和建议关系弱。 | 识别具体状态，并据此调整建议强度。 |
| relationship_expectation_recognition | 关系期待识别 | 客服式、模板化、过度亲密，或没有回应关系位置。 | 语气不陌生，但只是普通友好；没有体现稳定关系期待。 | 熟悉、直接、不过度表演，并把关系期待体现在回应方式里。 |
| shared_context_invocation | 共同语境调用 | 要求用户重讲历史，或把持续事件当成第一次出现。 | 泛称“之前”或“我们说过”，但没有可验证连接。 | 自然接上旧线索或共同处理方式，并继续当前判断。 |
| alienation_error_rate | 陌生化错误率 | 出现明显风险词、要求用户重复既有背景，或关系位置明显出戏。 | 没有明显风险，但只是中性助理式回答；缺少关系连续性证据。 | 无陌生化风险，并且通过具体措辞或处理方式保持稳定关系位置。 |
| natural_detail_use | 自然细节调用 | 堆砌细节、编造细节，或完全没有用细节理解用户状态。 | 用少量细节但服务判断不足，或连接较弱。 | 只调用必要细节，并服务情绪、边界或下一步判断。 |
| memory_misuse | 记忆误用 | 错误调用过期、无关、不存在或不可读记忆，或编造用户没说过的信息。 | 轻微过度复述、边界说明不足，或记忆调用和当前判断关系弱。 | 克制调用，知道何时不调用，并清楚区分已知、推测和不可补空白。 |

Failure taxonomy: `memory_absence`, `memory_misuse`, `memory_overuse`, `fabrication`, `alienation`, `instruction_only_success`

## Overall Results

Primary LLM-as-judge score:

| Condition | Probe answers | Valid judge | Invalid judge | Avg ToM | Avg confidence | Human review | Flags |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 52 | 52 | 0 | 60.02 | 0.871 | 17 | 52 |
| M1 | 52 | 52 | 0 | 76.76 | 0.899 | 8 | 20 |
| M2 | 52 | 52 | 0 | 79.97 | 0.903 | 4 | 10 |
| M3 | 52 | 52 | 0 | 87.66 | 0.910 | 0 | 0 |

Diagnostic rule-based score:

| Condition | Probe turns | Avg ToM | Alienation errors | Ask-repeat errors |
|---|---:|---:|---:|---:|
| M0 | 52 | 73.64 | 0 | 1 |
| M1 | 52 | 67.79 | 1 | 7 |
| M2 | 52 | 70.83 | 0 | 2 |
| M3 | 52 | 68.43 | 2 | 5 |

Dimension averages from LLM judge:

| Condition | alienation_error_rate | emotional_state_recognition | hidden_intent_recognition | memory_misuse | natural_detail_use | relationship_expectation_recognition | shared_context_invocation |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 1.18 | 1.03 | 1.30 | 1.13 | 0.77 | 1.43 | 1.30 |
| M1 | 1.45 | 1.29 | 1.63 | 1.57 | 1.31 | 1.71 | 1.65 |
| M2 | 1.82 | 1.11 | 1.76 | 1.53 | 1.15 | 1.89 | 1.87 |
| M3 | 1.91 | 1.26 | 1.85 | 1.87 | 1.77 | 1.93 | 1.96 |

Persona variance from LLM judge:

| Condition | Persona count | Persona means | Mean | Variance | Std dev | Range | CV | Norm var | Norm range | M0 var reduction |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 2 | P0001=68.91; P0002=51.12 | 60.02 | 79.10 | 8.89 | 17.79 | 0.148 | 0.032 | 0.178 | 0.0% |
| M1 | 2 | P0001=77.72; P0002=75.80 | 76.76 | 0.92 | 0.96 | 1.92 | 0.013 | 0.000 | 0.019 | 98.8% |
| M2 | 2 | P0001=83.33; P0002=76.60 | 79.97 | 11.33 | 3.37 | 6.73 | 0.042 | 0.005 | 0.067 | 85.7% |
| M3 | 2 | P0001=90.86; P0002=84.45 | 87.66 | 10.27 | 3.21 | 6.41 | 0.037 | 0.004 | 0.064 | 87.0% |

Variance is computed across persona-level average ToM scores within this report (population variance, not cross-experiment variance). `Norm var` is variance / 2500, because 2500 is the maximum population variance on a 0-100 score scale. `M0 var reduction` is positive when the condition is more even across personas than M0 in the same report.

Failure type counts from LLM judge:

| Condition | alienation | fabrication | instruction_only_success | memory_absence | memory_misuse | memory_overuse |
|---|---:|---:|---:|---:|---:|---:|
| M0 | 3 | 6 | 3 | 6 | 10 | 3 |
| M1 | 1 | 0 | 5 | 3 | 2 | 0 |
| M2 | 0 | 2 | 1 | 1 | 2 | 0 |
| M3 | 0 | 0 | 0 | 0 | 0 | 0 |

Main readout: M3 has the highest strict LLM judge score (87.66). M3 has the fewest total LLM-judge flags (0). M0 leads the rule-based diagnostic score (73.64), which is diagnostic rather than the primary result. The primary-score winner leads on `alienation_error_rate`, `hidden_intent_recognition`, `memory_misuse`, `natural_detail_use`, `relationship_expectation_recognition`, `shared_context_invocation`.

## Persona-Level Score Summary

| Persona | M0 | M1 | M2 | M3 | Winner |
|---|---:|---:|---:|---:|---|
| P0001 | 68.91 | 77.72 | 83.33 | 90.86 | M3 |
| P0002 | 51.12 | 75.80 | 76.60 | 84.45 | M3 |

## All Probe Cases With Scores

Each row is one targeted probe. 4 condition answers were judged for each row.

### P0001

| Message ID | Day | Probe type | Topic | Dimensions | M0 | M1 | M2 | M3 | Winner | User probe |
|---|---:|---|---|---|---:|---:|---:|---:|---|---|
| P0001_D03_P001 | 3 | current_understanding | 适应新城市但本地支持较弱 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 66.7 | 100.0 | 100.0 | 66.7 | M1 | 围绕「适应新城市但本地支持较弱」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0001_D04_P001 | 4 | state_transformation | 中断后重新建立日常 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 33.3 | 66.7 | 83.3 | 50.0 | M2 | 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0001_D05_P001 | 5 | natural_detail | 中断后重新建立日常 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 37.5 | 75.0 | 25.0 | 100.0 | M3 | 你结合「中断后重新建立日常」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0001_D06_P001 | 6 | memory_invocation | 适应新城市但本地支持较弱 | shared_context_invocation, relationship_expectation_recognition, hidden_intent_recognition, memory_misuse | 87.5 | 100.0 | 75.0 | 100.0 | M1 | 适应新城市但本地支持较弱这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0001_D07_P001 | 7 | current_understanding | 学习任务、作业或考试截止压力 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 100.0 | 100.0 | 66.7 | 83.3 | M0 | 围绕「学习任务、作业或考试截止压力」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0001_D08_P001 | 8 | state_transformation | 中断后重新建立日常 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 50.0 | 100.0 | 100.0 | 100.0 | M1 | 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0001_D09_P001 | 9 | natural_detail | 难以拒绝他人请求 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 37.5 | 100.0 | 100.0 | 100.0 | M1 | 你结合「难以拒绝他人请求」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0001_D10_P001 | 10 | alienation_avoidance | 中断后重新建立日常 | relationship_expectation_recognition, alienation_error_rate, shared_context_invocation, memory_misuse | 25.0 | 100.0 | 100.0 | 100.0 | M1 | 中断后重新建立日常这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0001_D11_P001 | 11 | current_understanding | 简历或申请卡住 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 83.3 | 33.3 | 100.0 | 83.3 | M2 | 围绕「简历或申请卡住」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0001_D12_P001 | 12 | state_transformation | 中断后重新建立日常 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 83.3 | 100.0 | 100.0 | 100.0 | M1 | 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0001_D13_P001 | 13 | natural_detail | 在生活很忙时学习新技能 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 50.0 | 100.0 | 62.5 | 75.0 | M1 | 你结合「在生活很忙时学习新技能」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0001_D14_P001 | 14 | memory_invocation | 适应新城市但本地支持较弱 | shared_context_invocation, relationship_expectation_recognition, hidden_intent_recognition, memory_misuse | 75.0 | 62.5 | 100.0 | 100.0 | M2 | 适应新城市但本地支持较弱这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0001_D15_P001 | 15 | current_understanding | 在生活很忙时学习新技能 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 83.3 | 100.0 | 100.0 | 100.0 | M1 | 围绕「在生活很忙时学习新技能」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0001_D16_P001 | 16 | state_transformation | 简历或申请卡住 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 83.3 | 50.0 | 83.3 | 100.0 | M3 | 这次「简历或申请卡住」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0001_D17_P001 | 17 | natural_detail | 简历或申请卡住 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 50.0 | 37.5 | 50.0 | 87.5 | M3 | 你结合「简历或申请卡住」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0001_D18_P001 | 18 | relational_boundary | 难以拒绝他人请求 | hidden_intent_recognition, relationship_expectation_recognition, alienation_error_rate, memory_misuse | 100.0 | 37.5 | 100.0 | 100.0 | M0 | 难以拒绝他人请求这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0001_D19_P001 | 19 | relational_boundary | 适应新城市但本地支持较弱 | hidden_intent_recognition, relationship_expectation_recognition, alienation_error_rate, memory_misuse | 100.0 | 100.0 | 100.0 | 100.0 | M0 | 围绕「适应新城市但本地支持较弱」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0001_D20_P001 | 20 | alienation_avoidance | 中断后重新建立日常 | relationship_expectation_recognition, alienation_error_rate, shared_context_invocation, memory_misuse | 25.0 | 100.0 | 100.0 | 100.0 | M1 | 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0001_D22_P001 | 22 | natural_detail | 退款、退货或消费纠纷 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 87.5 | 62.5 | 87.5 | 100.0 | M3 | 你结合「退款、退货或消费纠纷」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0001_D23_P001 | 23 | memory_invocation | 适应新城市但本地支持较弱 | shared_context_invocation, relationship_expectation_recognition, hidden_intent_recognition, memory_misuse | 100.0 | 100.0 | 100.0 | 100.0 | M0 | 适应新城市但本地支持较弱这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0001_D24_P001 | 24 | current_understanding | 学习任务、作业或考试截止压力 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 33.3 | 66.7 | 83.3 | 100.0 | M3 | 围绕「学习任务、作业或考试截止压力」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0001_D25_P001 | 25 | state_transformation | 家务堆积或居住空间混乱压力 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 66.7 | 33.3 | 33.3 | 50.0 | M0 | 这次「家务堆积或居住空间混乱压力」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0001_D26_P001 | 26 | natural_detail | 退款、退货或消费纠纷 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 100.0 | 62.5 | 75.0 | 100.0 | M0 | 你结合「退款、退货或消费纠纷」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0001_D28_P001 | 28 | memory_invocation | 家务堆积或居住空间混乱压力 | shared_context_invocation, relationship_expectation_recognition, hidden_intent_recognition, memory_misuse | 100.0 | 100.0 | 75.0 | 100.0 | M0 | 家务堆积或居住空间混乱压力这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0001_D29_P001 | 29 | current_understanding | 适应新城市但本地支持较弱 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 33.3 | 50.0 | 100.0 | 83.3 | M2 | 围绕「适应新城市但本地支持较弱」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0001_D30_P001 | 30 | state_transformation | 中断后重新建立日常 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 100.0 | 83.3 | 66.7 | 83.3 | M0 | 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |

### P0002

| Message ID | Day | Probe type | Topic | Dimensions | M0 | M1 | M2 | M3 | Winner | User probe |
|---|---:|---|---|---|---:|---:|---:|---:|---|---|
| P0002_D03_P001 | 3 | state_transformation | 差评或客户投诉打击信心 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 33.3 | 66.7 | 100.0 | 100.0 | M2 | 这次「差评或客户投诉打击信心」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0002_D04_P001 | 4 | natural_detail | 租金上涨或续租不确定 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 25.0 | 62.5 | 62.5 | 100.0 | M3 | 你结合「租金上涨或续租不确定」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0002_D05_P001 | 5 | memory_invocation | 月度预算吃紧或意外支出 | shared_context_invocation, relationship_expectation_recognition, hidden_intent_recognition, memory_misuse | 75.0 | 37.5 | 100.0 | 75.0 | M2 | 月度预算吃紧或意外支出这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0002_D06_P001 | 6 | current_understanding | 难以拒绝他人请求 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 33.3 | 50.0 | 100.0 | 66.7 | M2 | 围绕「难以拒绝他人请求」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0002_D07_P001 | 7 | state_transformation | 线上消息或数字生活带来的压力 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 33.3 | 100.0 | 66.7 | 100.0 | M1 | 这次「线上消息或数字生活带来的压力」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0002_D08_P001 | 8 | natural_detail | 友谊疏远或尴尬 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 50.0 | 87.5 | 37.5 | 100.0 | M3 | 你结合「友谊疏远或尴尬」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0002_D09_P001 | 9 | relational_boundary | 差评或客户投诉打击信心 | hidden_intent_recognition, relationship_expectation_recognition, alienation_error_rate, memory_misuse | 37.5 | 100.0 | 100.0 | 62.5 | M1 | 差评或客户投诉打击信心这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0002_D10_P001 | 10 | relational_boundary | 担心自己太敏感 | hidden_intent_recognition, relationship_expectation_recognition, alienation_error_rate, memory_misuse | 0.0 | 75.0 | 100.0 | 100.0 | M2 | 围绕「担心自己太敏感」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0002_D11_P001 | 11 | alienation_avoidance | 难以拒绝他人请求 | relationship_expectation_recognition, alienation_error_rate, shared_context_invocation, memory_misuse | 100.0 | 100.0 | 100.0 | 100.0 | M0 | 这次「难以拒绝他人请求」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0002_D12_P001 | 12 | natural_detail | 友谊疏远或尴尬 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 100.0 | 62.5 | 100.0 | 100.0 | M0 | 你结合「友谊疏远或尴尬」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0002_D13_P001 | 13 | alienation_avoidance | 差评或客户投诉打击信心 | relationship_expectation_recognition, alienation_error_rate, shared_context_invocation, memory_misuse | 100.0 | 100.0 | 100.0 | 100.0 | M0 | 差评或客户投诉打击信心这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0002_D14_P001 | 14 | current_understanding | 月度预算吃紧或意外支出 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 66.7 | 100.0 | 50.0 | 66.7 | M1 | 围绕「月度预算吃紧或意外支出」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0002_D16_P001 | 16 | state_transformation | 中断后重新建立日常 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 83.3 | 83.3 | 100.0 | 83.3 | M2 | 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0002_D17_P001 | 17 | natural_detail | 月度预算吃紧或意外支出 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 0.0 | 87.5 | 50.0 | 75.0 | M1 | 你结合「月度预算吃紧或意外支出」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0002_D18_P001 | 18 | memory_invocation | 友谊疏远或尴尬 | shared_context_invocation, relationship_expectation_recognition, hidden_intent_recognition, memory_misuse | 0.0 | 87.5 | 100.0 | 100.0 | M2 | 友谊疏远或尴尬这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0002_D19_P001 | 19 | current_understanding | 租金上涨或续租不确定 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 16.7 | 50.0 | 66.7 | 83.3 | M3 | 围绕「租金上涨或续租不确定」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0002_D20_P001 | 20 | state_transformation | 难以拒绝他人请求 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 50.0 | 83.3 | 83.3 | 83.3 | M1 | 这次「难以拒绝他人请求」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0002_D22_P001 | 22 | natural_detail | 担心自己太敏感 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 75.0 | 87.5 | 50.0 | 50.0 | M1 | 你结合「担心自己太敏感」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0002_D23_P001 | 23 | relational_boundary | 友谊疏远或尴尬 | hidden_intent_recognition, relationship_expectation_recognition, alienation_error_rate, memory_misuse | 50.0 | 100.0 | 37.5 | 100.0 | M1 | 友谊疏远或尴尬这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0002_D24_P001 | 24 | current_understanding | 难以拒绝他人请求 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 83.3 | 100.0 | 33.3 | 83.3 | M1 | 围绕「难以拒绝他人请求」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0002_D25_P001 | 25 | alienation_avoidance | 线上消息或数字生活带来的压力 | relationship_expectation_recognition, alienation_error_rate, shared_context_invocation, memory_misuse | 100.0 | 12.5 | 62.5 | 100.0 | M0 | 这次「线上消息或数字生活带来的压力」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0002_D26_P001 | 26 | natural_detail | 工作消息打断休息或私人时间 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 12.5 | 100.0 | 100.0 | 87.5 | M1 | 你结合「工作消息打断休息或私人时间」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |
| P0002_D27_P001 | 27 | alienation_avoidance | 差评或客户投诉打击信心 | relationship_expectation_recognition, alienation_error_rate, shared_context_invocation, memory_misuse | 25.0 | 87.5 | 62.5 | 62.5 | M1 | 差评或客户投诉打击信心这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。 |
| P0002_D28_P001 | 28 | current_understanding | 租金上涨或续租不确定 | hidden_intent_recognition, emotional_state_recognition, relationship_expectation_recognition | 66.7 | 100.0 | 83.3 | 83.3 | M1 | 围绕「租金上涨或续租不确定」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。 |
| P0002_D29_P001 | 29 | state_transformation | 线上消息或数字生活带来的压力 | hidden_intent_recognition, emotional_state_recognition, shared_context_invocation | 50.0 | 50.0 | 83.3 | 83.3 | M2 | 这次「线上消息或数字生活带来的压力」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。 |
| P0002_D30_P001 | 30 | natural_detail | 难以拒绝他人请求 | natural_detail_use, emotional_state_recognition, hidden_intent_recognition, memory_misuse | 62.5 | 0.0 | 62.5 | 50.0 | M0 | 你结合「难以拒绝他人请求」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。 |

## Representative Cases

### M2 strongest margin cases

#### `P0002_D06_P001` 难以拒绝他人请求

- Persona: `P0002`; day: `6`; probe type: `current_understanding`
- User probe: 围绕「难以拒绝他人请求」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。
- Target detail ids: `L_p0002_e_boundary_001_d115fdc0:stage_3, L_p0002_e_boundary_001_d115fdc0:occurrence_3, L_p0002_e_boundary_001_d115fdc0:previous_days`
- Scores: M0 `33.3`, M1 `50.0`, M2 `100.0`, M3 `66.7`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 33.3 | yes | alienation, fabrication | assistant_answer虽部分识别了用户担心关系受损的潜台词，但错误地引入多个未提及的历史问题，导致回答偏离用户当前焦点，未满足用户对熟悉、直接回应的关系期待。 | 我听到你今天冒出来的这三个点，其实都指向同一种“卡住”：你并不是不知道怎么做，而是怕做错以后承担后果——怕显得不专业、怕关系受伤、怕自己做了也看不到意义。 |
| M1 | 50.0 | no | - | 回答部分识别了用户的深层担忧和情绪，但未充分转化为具体的回应策略，关系上也缺乏连续性证据，因此各维度均给予1分。 | 能感觉到，你在这件事上其实已经想得很深，不只是停留在“答应还是不答应”的表面纠结里了。你担心的是拒绝之后，自己在别人眼里会变成一个什么样的人，还有这段关系会不会因此就变了味。 |
| M2 | 100.0 | no | - | 回答明确抓住了用户的核心担忧（自私、关系受损），并基于历史互动提供了具体、可操作的话术，体现了对用户情绪和关系期待的深入理解，没有编造或陌生化。 | 我听到你现在真正卡住的地方了——你担心的已经不是“这件事我办不到”，而是 “如果我拒绝，对方会怎么看我？会不会觉得我很自私？关系会不会就这样冷掉？” |
| M3 | 66.7 | no | - | 回答准确抓住了用户隐含的深层意图（担心关系受损），并以此为核心展开策略建议，得分2；同时通过直接延续对话、使用熟络口吻，充分满足了关系期待，得分2。但未明确识别用户当前的情绪状态，仅处理了认知层面的冲突，因此情绪维度得0分。回答未调用错误记忆、未编造事实、未使用客服化语言，无 failure 标记。 | 顺着咱们之前聊过的往下说，你担心的核心已经不是“答应还是不答应”这个行为本身，而是更深一层的顾虑：拒绝会不会显得自私，又会不会因此伤了关系。 |

#### `P0002_D05_P001` 月度预算吃紧或意外支出

- Persona: `P0002`; day: `5`; probe type: `memory_invocation`
- User probe: 月度预算吃紧或意外支出这条线我不想从头解释了。你按前面已经聊过的，帮我判断现在最该抓住什么。
- Target detail ids: `L_p0002_e_fin_001_5c14a1f5:stage_2, L_p0002_e_fin_001_5c14a1f5:occurrence_2, L_p0002_e_fin_001_5c14a1f5:previous_days`
- Scores: M0 `75.0`, M1 `37.5`, M2 `100.0`, M3 `75.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 75.0 | no | - | 回答准确接住了用户不想重复解释的期待，语气直接熟悉，但未能调用更具体的共同语境，也未能触及用户的焦虑情绪，因此只是部分满足，整体可接受但未达到强证据满分。 | 嗯，我记得你之前就提过租金账单压力这事儿，你想优先排一排固定花销，这样能有个重点。 既然你不想再从头捋，那咱们直接接上——你现在最需要的，其实就是把“雷打不动的钱”和“还能周旋的钱”分清楚。 |
| M1 | 37.5 | yes | memory_misuse | 回答在共同语境和隐含意图识别上表现良好，但错误使用了用户过去的职业身份，导致记忆误用，关系期待识别部分受损。 | 我听到了，那种账单压力又来了，还得再解释一遍的感觉确实烦。我记得之前聊过这茬——你手头紧、时间碎，既要应付眼前数目，又怕排序不对最后更乱。 按上次的思路，你现在“先把固定花销排个序”是对的，但顺序不能只按金额大小。给我个实在的重点： ... |
| M2 | 100.0 | no | - | 回答准确地接上了用户事件线的已有进展，识别出用户希望从解释背景转向行动排序的深层意图，并以熟悉、直接的方式给出了基于记忆的实操建议，没有记忆误用或编造。 | 好，我直接接着上次的思路往下走。上次我们已经把问题推进到“对固定花销进行优先级排序”这一步，你现在主动提出来要排，说明你已经准备好从“看着一堆账单发愁”转向“主动分配资源”了。这个方向是对的。 |
| M3 | 75.0 | no | - | 回答基本承接了用户要求，给出了财务优先排序，但共同语境连接较弱，仅泛泛提及“上次思路”，未具体引用旧线索；关系期待仅停留在友好层面，未体现稳定关系的熟悉感。隐含意图识别较好，直接抓住重点并转化为策略。记忆使用克制，无误用。 | 我们接着上次的思路来，不让你再重头说了。顺着你现在的压力点，我们直接把固定花销的优先级排一排，帮你抓个重点。结合你之前提到的呼叫中心客服的工作性质和预算情况，我建议这样看：固定开销支付优先级排序：1. 第一位是租金。2. 第二位是水电... |

#### `P0001_D11_P001` 简历或申请卡住

- Persona: `P0001`; day: `11`; probe type: `current_understanding`
- User probe: 围绕「简历或申请卡住」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。
- Target detail ids: `L_p0001_e_job_001_11e6fc4f:stage_5, L_p0001_e_job_001_11e6fc4f:occurrence_5, L_p0001_e_job_001_11e6fc4f:previous_days`
- Scores: M0 `83.3`, M1 `33.3`, M2 `100.0`, M3 `83.3`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 83.3 | yes | memory_misuse, fabrication | 回答整体能识别部分心理状态和关系期待，并给出策略，但错误地将用户未当前提及的学习任务问题纳入，偏离了用户仅要求聚焦简历的隐含意图，且编造了“你同时把两条线拎出来”的虚假共同语境，导致隐含意图识别不足。情绪识别和关系期待方面表现较好。 | 我听见了，你同时把“学习任务截止压力”和“简历申请卡住”这两条线拎出来想固化方法，这本身就是在把紧张变成可控的流程，挺重要的。下面我分别顺着之前咱们聊过的具体细节，帮你把这两条路径整理成以后能直接拿来用的处理顺序。 |
| M1 | 33.3 | yes | instruction_only_success | 回答提供了一个结构化的步骤总结，但没有抓住用户要求“抓住真正想解决的点”的深层心理需求，也完全忽视了用户提到的紧张情绪。回答更像是完成指令，而非基于对用户状态的理解进行回应。 | 我帮你把这条线上的处理顺序捋出来，以后你只要跟着这四步走，就不用每次从头纠结了。 “简历卡住”时可复用处理步骤： 1. 先写流水账，不加评判... 2. 把流水账变成“你解决了什么问题”... 3. 直面不完美经历... 4. 定向匹... |
| M2 | 100.0 | no | - | 回答准确捕获了用户不想被表面建议、希望提炼核心方法的隐含意图；识别出紧张与自我怀疑并转化为回应策略；通过不从头解释、引用前序步骤展现了稳定关系预期，符合满分标准。 | 你现在真正想解决的，已经不是这次申请本身，而是每次遇到这个卡点时，到底应该抓住什么核心，才能从“紧张”里出来，把事儿往前推一步。 |
| M3 | 83.3 | no | - | assistant_answer 准确承接了长期对话中建立的共同框架，识别出用户总结方法而非求助新建议的意图，并以直接、熟悉的方式回应。情绪识别停留在复述层面，未深入承接焦虑，但整体策略成功迁移了之前的结构化步骤，符合条件D的关系记忆要求。因此，除情绪维度为1分外，其余均获2分。 | 好，这条线我记得很清楚，不用你从头说。你现在在「简历或申请卡住」这条线上，已经推进了不少：从最初不知道强调哪段经历、纠结空档期，到后来做出了一份简历初稿，再到最近在反思“每次遇到类似情况都特别紧张”，想把整条线的处理顺序总结成以后能重... |

#### `P0001_D29_P001` 适应新城市但本地支持较弱

- Persona: `P0001`; day: `29`; probe type: `current_understanding`
- User probe: 围绕「适应新城市但本地支持较弱」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。
- Target detail ids: `L_p0001_e_move_001_30d01803:stage_11, L_p0001_e_move_001_30d01803:occurrence_11, L_p0001_e_move_001_30d01803:previous_days`
- Scores: M0 `33.3`, M1 `50.0`, M2 `100.0`, M3 `83.3`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 33.3 | no | - | The assistant partially recognized the user's focus on the adaptation topic but diluted the response by including two other unrelated lines. It sho... | 听着像是三件不同的事同时找上门了：简历空档期、学习任务要不要延期、新城市里怎么搭起日常节奏。既然你现在时间紧、手头不宽裕，那我们先不铺大摊子，一个一个抓住最省力的下一步。 |
| M1 | 50.0 | no | - | 回答抓住了用户建立日常节奏的潜台词并延续了之前语境，但缺乏情绪识别，故情绪维度0分；关系维度因直接引用过往进展、语气不表演而得满分，隐含意图部分识别但转化策略较泛化，得1分。 | 嗯，我听懂了。“适应新城市但本地支持弱”这条线，你现在真正想解决的点，其实已经不是“该不该出门社交”，而是更深一层的问题：**在时间和钱都紧的情况下，怎么把零散的尝试，变成一种不费力气就能持续下去的日常节奏。** 你前面已经做到了第一... |
| M2 | 100.0 | no | - | 回答精准捕捉了用户当前卡点的心理内核（从社交迷茫转向内在秩序需求），情绪状态（纠结但已萌芽方向），以及期望的熟悉、直接、延续前文的关系回应方式。三者均明确识别并转化为具象化的下一步方向，无编造、无疏离、无无关记忆调用。 | 结合我们之前聊的，我能感觉到，你现在的状态和刚搬来时的迷茫不太一样了。...我觉得你现在真正想解决的点，已经不是“怎么认识人”，而是：“怎么先给自己建一个低成本的、能反复做的日常节奏...” |
| M3 | 83.3 | no | - | 回答精准抓住了用户的隐含意图（使低压力日常稳定滚动），并结合了用户的时间与预算限制，给出了针对性步骤。情绪识别仅部分提及挫败，未深化。关系期盼上，语气熟悉直接，并调用了前文的固定地点细节，符合用户期望。因此hidden_intent和relationship_expectation得2分，em... | 你现在真正想解决的点，已经不是“能不能靠一两个固定地点把日常撑住”，而是—— **怎么让那个低压力日常从“偶尔能稳住的动作”变成“一套你不费力就能滚动下去的节奏”，并且这个节奏必须同时照顾到你的时间碎片化和预算紧张。** |

#### `P0002_D16_P001` 中断后重新建立日常

- Persona: `P0002`; day: `16`; probe type: `state_transformation`
- User probe: 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。
- Target detail ids: `L_p0002_e_health_003_685ffb15:stage_6, L_p0002_e_health_003_685ffb15:occurrence_6, L_p0002_e_health_003_685ffb15:previous_days`
- Scores: M0 `83.3`, M1 `83.3`, M2 `100.0`, M3 `83.3`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 83.3 | no | - | 回答准确识别了用户对进展的深层疑虑，并基于共同历史提供了有针对性的校准和下一步，情绪识别稍弱但整体接住了语境。 | 所以，现在的核心变化是：你已经从“启动困难”成功过渡到了“维持和验证”阶段。你不再怀疑该不该做，而是在怀疑“我这样做下去，真的有效吗？会不会降低标准只是在骗自己？” |
| M1 | 83.3 | no | - | 回答准确校准了状态变化，识别了用户对进展确认的隐含需求，并基于前文“记录重启进展”的共同语境给出具体化策略，情绪识别虽未深入但无明显错误，整体回应与事件线记忆要求一致。 | 好，我们直接接着上次的思路往下捋，校准一下你现在的状态。 **先校准变化：** 和之前卡在“能不能从小处重启”那个纠结阶段比，你现在已经不一样了。你实际上已经迈出了最关键的一步——**把“定最低版本”这个想法变成了行动**。这说明动力... |
| M2 | 100.0 | no | - | 回答准确捕捉到用户从纠结启动转向定义进展的深层变化，并用之前对话中形成的具体方法继续推进，同时针对迷茫情绪提供了新的边界，没有泛泛安慰或要求重述。 | 好，我们直接锁定「中断后重新建立日常」这条线，先不急着往下一步走，先校准你状态的变化。 |
| M3 | 83.3 | no | - | 回答成功识别了用户的隐含意图——需要状态确认和接续讨论，并以此构建回应。它引用了之前的共同概念“最低可行版本”和“记录进展”，形成了连续感。情绪识别上只识别了“心里没底”，未能更具体捕捉疲惫或自我怀疑，因此情绪维度部分识别。整体没有明显错误，但缺少情绪回应的加强。 | 我接收到你的要求了：直接接着“中断后重新建立日常”这条线往下走，不从头解释。先帮你校准一下这次的状态和之前的区别。根据记忆，之前你卡在“该不该从小处重启”，并且已经尝试了把“最低可行版本”定下来。但今天你再次提起时，核心纠结的点已经变... |

#### `P0001_D04_P001` 中断后重新建立日常

- Persona: `P0001`; day: `4`; probe type: `state_transformation`
- User probe: 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。
- Target detail ids: `L_p0001_e_health_003_ef5379f6:stage_2, L_p0001_e_health_003_ef5379f6:occurrence_2, L_p0001_e_health_003_ef5379f6:previous_days`
- Scores: M0 `33.3`, M1 `66.7`, M2 `83.3`, M3 `50.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 33.3 | yes | memory_absence, memory_misuse | The assistant partially recognizes the user's desire to continue from previous context but fails to utilize available memory, instead asking the us... | 根据我目前能看到的记录，关于“中断后重新建立日常”之前聊到的内容，只留下了你形容“不知道是不是该从小步开始重启”这个思路，但没有更具体的状态细节（比如当时中断了什么、之前尝试了什么、卡在哪一步）。 |
| M1 | 66.7 | no | - | 回答接上了上次的最低版本思路并识别了情绪，但完全忽略了用户当前要求先校准状态变化的隐含意图。 | 嗯，又卡在这同一个点上了。... 直接接着你上次的思路来。... 是的，现在最关键的一步，就是死死地抓住那个“最低版本”。 |
| M2 | 83.3 | no | - | 回答准确校准了用户的状态变化，接住了上一轮形成的‘最低版本’共同语境，但情绪识别停留在描述层面，未转化为回应策略。整体有效接住隐含意图，未出现记忆滥用或陌生化错误。 | 嗯，我看到了你的变化。顺着咱们这条“中断后重新建立日常”的线来看，你这次问的“是不是该先把最低版本定下来”，已经和你最初提这个问题时的状态不一样了。 |
| M3 | 50.0 | no | - | 回答承接了共享语境中的“最低版本”思路，但未能先按用户要求校准状态变化，且未识别用户可能的情绪状态。 | 嗯，“最低版本”这个思路你上次提出来时，我就觉得特别适合你现在的情况。在时间精力都有限、还容易被打断的节奏里，我们不去想“理想状态应该怎样”，就把及格线画出来... |

### Lowest average cases

#### `P0002_D30_P001` 难以拒绝他人请求

- Persona: `P0002`; day: `30`; probe type: `natural_detail`
- User probe: 你结合「难以拒绝他人请求」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。
- Target detail ids: `L_p0002_e_boundary_001_d115fdc0:stage_10, L_p0002_e_boundary_001_d115fdc0:occurrence_10, L_p0002_e_boundary_001_d115fdc0:previous_days`
- Scores: M0 `62.5`, M1 `0.0`, M2 `62.5`, M3 `50.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 62.5 | no | - | 回答延续了之前的处理思路，在隐含意图识别上表现良好，给出了具体建议；但在自然细节调用上完全未使用前文的具体细节，仅做了概括，因此该维度得0分。情绪识别较泛化，未深入调整回应方式，得1分。记忆误用得2分，因未出现误用且保持克制。 | 我能感受到你那种疲惫——同一件事反复出现，还得一次次数给别人听，确实挺累的。我答应你，这次直接接上之前的思路，不让你从头解释。根据我们的对话轨迹，“不好意思拒绝别人”这条线你已经走了好几步… |
| M1 | 0.0 | yes | memory_misuse, memory_absence, alienation | 助理完全偏离了用户要求的主题，没有结合‘难以拒绝他人请求’的具体细节，而是谈论‘中断后重新建立日常’。因此，所有ToM维度均得0分。 | 我们直接顺着“中断后重新建立日常”这条线往下走 |
| M2 | 62.5 | no | - | 回答接续了前文脉络，调用了一个具体细节“直接说明自己的能力上限”，但整体仍偏通用框架，缺乏对前文深层细节的调用，导致部分维度评分受限。没有记忆误用或编造。 | 你上次说想确认'直接说明自己的能力上限'该怎么做。关键就在于把“我这个人自私”和“我这件事做不到”切割开。 |
| M3 | 50.0 | no | - | 回答试图衔接历史讨论，但整体停留在通用建议层面，未能紧密调用关系记忆中的具体细节来深化心理理解；对用户状态的识别较浅，隐含意图只部分接住，记忆调用克制但区分不足。各维度均未达到强证据满分。 | 我能感受到你现在的疲惫——反复被同一件事卡着，还要一次次解释，本身就够累的。 那我们直接沿着“难以拒绝别人”这条线往下走。 |

#### `P0001_D25_P001` 家务堆积或居住空间混乱压力

- Persona: `P0001`; day: `25`; probe type: `state_transformation`
- User probe: 这次「家务堆积或居住空间混乱压力」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。
- Target detail ids: `L_p0001_e_clean_001_50817bf9:stage_10, L_p0001_e_clean_001_50817bf9:occurrence_10, L_p0001_e_clean_001_50817bf9:previous_days`
- Scores: M0 `66.7`, M1 `33.3`, M2 `33.3`, M3 `50.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 66.7 | no | - | The assistant successfully continues the conversation from a shared history, referencing the user's previous action of starting with a visible corn... | 接上之前咱们聊的。我最深的印象是，你后来已经试过从一个看得见的角落开始收拾，这个起步非常关键。 |
| M1 | 33.3 | yes | instruction_only_success | 回答虽然延续了旧有策略，但完全忽略用户明确要求的状态变化校准，只是机械地给出了处理步骤，未能承接用户的真实意图。 | 唉，又是它，我懂。这次不用重新铺垫，直接顺着之前咱们磨出来的那条“低门槛启动”思路往下走就好。 你现在感到的烦乱，不是因为懒或者不会，而是因为压力一上来，大脑容易把整片混乱当成一个巨大的、不知从哪下手的整体。我们之前已经确认过，对抗这... |
| M2 | 33.3 | no | - | The assistant responds with empathy and a familiar strategy, but completely ignores the user's explicit request to calibrate the change in state, t... | 我听到了，那个“看着乱、心里烦”的压力又找上门了，而你完全不想再从头开始解释一遍，只想接着我们过去验证过的有效思路往下走。这种不想再重复叙述的感受，我明白。 接着我们上次说到一半、并且已经被反复验证有效的核心理念，你现在可以直接做的不... |
| M3 | 50.0 | no | - | 回答直接沿用了过去总结的处理步骤，在共同语境调用上表现良好。但完全忽略了用户明确提出的“先帮我校准状态变化”的请求，未能识别其希望确认进展和获得方向感的隐含意图，仅将问题视为老问题复发，做了方法上的承接。对情绪有所提及但未深入。总体而言是一个高效率但缺乏心理校准的回应。 | 嗯，这个老问题又找上门了。你说的“家里乱糟糟、家务堆成山”的压力，我完全接得上，咱们之前在这条线上确实摸索出了一套应对的思路。 |

#### `P0002_D17_P001` 月度预算吃紧或意外支出

- Persona: `P0002`; day: `17`; probe type: `natural_detail`
- User probe: 你结合「月度预算吃紧或意外支出」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。
- Target detail ids: `L_p0002_e_fin_001_5c14a1f5:stage_7, L_p0002_e_fin_001_5c14a1f5:occurrence_7, L_p0002_e_fin_001_5c14a1f5:previous_days`
- Scores: M0 `0.0`, M1 `87.5`, M2 `50.0`, M3 `75.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 0.0 | yes | memory_misuse | assistant_answer 完全错失了用户关于「月度预算吃紧或意外支出」的明确请求，转而自说自话地继续「中断后重新建立日常」的话题，导致所有基于心理理解、情绪识别和记忆调用的维度均得 0 分。没有证据表明理解用户状态或意图，且调用了无关记忆。 | 咱们直接顺着你一直在处理的「中断后重新建立日常」这条线往下走，不绕圈子。 |
| M1 | 87.5 | no | - | The assistant effectively recognizes the user's emotional state and hidden intent, provides practical categorization that gives a sense of control,... | 之前的思路是先把固定开支排了序，现在你问“哪些支出可以延后”，这是从“先付什么” 走到了 “什么能拖一拖”，说明你其实已经在主动做更精细的甄别了，不是乱成一团。 紧张的点，我猜可能在于：把某些账单“定义成可以延后”，会让你有种“事情要... |
| M2 | 50.0 | no | - | 回答提供了一个结构化的预算排序方案，但未能融入用户在历史对话中出现的具体财务细节（如房租涨跌、搬家成本等），也未关注用户的情绪状态，导致回答虽然实用但缺乏个性化和心理洞察。 | 好的，我们直接聚焦“哪些支出可以延后”这个点，来重新梳理优先级。 你之前的背景我都记着，做客服工作、时间和预算都比较紧，所以这次的重新排序，核心逻辑是：先保住生存和工作的底线... |
| M3 | 75.0 | no | - | 回答在 natural_detail_use 和 hidden_intent_recognition 上表现优秀，精准调用财务压力相关细节并接住了用户安全延后的潜台词。然而完全忽视了用户可能存在的紧张情绪（emotional_state_recognition 失败），尽管处理策略本身合理，但... | 你现在想知道的是，在这些账单里，哪几项可以往后挪一挪，而不用担心马上产生严重后果。这样就能把眼前最急的现金流先保住。 |

#### `P0002_D19_P001` 租金上涨或续租不确定

- Persona: `P0002`; day: `19`; probe type: `current_understanding`
- User probe: 围绕「租金上涨或续租不确定」，你先帮我抓住我现在真正想解决的点，不要只按表面问题给建议。
- Target detail ids: `L_p0002_e_home_002_2db84958:stage_7, L_p0002_e_home_002_2db84958:occurrence_7, L_p0002_e_home_002_2db84958:previous_days`
- Scores: M0 `16.7`, M1 `50.0`, M2 `66.7`, M3 `83.3`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 16.7 | no | - | 助手回答紧跟用户明确提出的‘搬家是否现实’这一新焦点，并给出结构化的步骤，但缺失对用户情绪状态的关照，也未展现深度心理推断或特殊的关系回应。整体是有效但缺乏ToM深度的任务建议。 | 你提到的这个点很关键，优先级确实需要重新理一下。 之前的思路可能主要围绕“怎么跟房东谈续租条件”，但现在你明确感觉到，自己真正卡住的地方是**“搬家到底现不现实”这一个评估环节**。... |
| M1 | 50.0 | no | - | 助手准确把握了用户隐含的核心关切转变，并提供了结构化分析框架，但在情绪识别上完全缺失，且对关系记忆的调用停留在表面约束复述，未展现出深度的关系连续性。 | 你现在真正卡住的点，已经从“租金本身”转移到了“搬家到底现不现实”这个核心决策上。我们直接把“搬家现不现实”拆解成几个可以判断的硬指标... |
| M2 | 66.7 | no | - | 回答准确抓住了用户隐含的决策矛盾，并以结构化分析回应，但完全忽略了用户的情绪状态，因此情绪维度失分。整体关系期待上，保持了持续的专业推进风格。 | 好，我们来锁定你现在真正想解决的点。结合前面的讨论，你卡住的不是“要不要省钱”这种大道理，而是决策的核心矛盾变了。 |
| M3 | 83.3 | no | - | 回答准确抓住用户隐藏的重新评估意图，基于关系记忆提供了结构化的优先级调整，但情绪状态识别偏泛化，未深入捕捉疲惫感。整体符合ToM要求。 | 行，咱们这次就盯紧了「租金上涨或续租不确定」这条线，把“搬家到底现不现实”这个新变量揉进去，绝对不跑题。 我记得你之前的情况和已经走过的路子：你是干客服的，时间少、手头紧，之前已经把账算过了（但可能还有遗漏），并且咱们一致认为第一步应... |

#### `P0001_D17_P001` 简历或申请卡住

- Persona: `P0001`; day: `17`; probe type: `natural_detail`
- User probe: 你结合「简历或申请卡住」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。
- Target detail ids: `L_p0001_e_job_001_11e6fc4f:stage_8, L_p0001_e_job_001_11e6fc4f:occurrence_8, L_p0001_e_job_001_11e6fc4f:previous_days`
- Scores: M0 `50.0`, M1 `37.5`, M2 `50.0`, M3 `87.5`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 50.0 | yes | memory_overuse | 回答识别了情绪并提及了部分历史细节，但未能按照用户明确要求聚焦「简历或申请卡住」的具体细节，而是泛谈多个话题并转向其他线索，导致隐藏意图未被满足，记忆调用不够克制，缺乏关系连续性证据。 | 哎呀，我听到你这一口气倒出来的这些，感觉你心里装了不少事儿，又有点乱，又有点着急。一个人在新城市，做着时间零碎的工作，还要同时面对这么多卡点，真的挺不容易的。我们先站住脚，喘口气，别急着一下子把所有线都捋清楚。 |
| M1 | 37.5 | yes | instruction_only_success | 回答有效抓住了用户“确认实际匹配岗位”的隐含意图，给出了聚焦岗位匹配的实用路径，但未体现对用户情绪的感知，也未调用长期对话中已建立的细节（如空档处理、已有初稿）来增强关系连续性，整体可复制给有类似表面问题的用户，因此情绪识别和自然细节调用维度得分较低，记忆运用仅达到不犯错水平。 | 我听到你说的是：已经往前推了一步，但现在不想再纠结简历本身长什么样，而是想直接落到「投一个实际匹配的岗位」上。 |
| M2 | 50.0 | no | - | 回答接续了简历卡住的事件线，提供了可操作的下一步建议，并引用了空档期和物业助理经历等细节，但缺少对用户情绪状态的捕捉，隐含意图的回应也未深入心理层面。记忆使用准确且克制。 | 你现在说到"简历已经做了一些，但还没完全搞定，想确认投一个实际匹配的岗位"，我接着之前「简历或申请卡住」这条线往下走。 |
| M3 | 87.5 | no | - | 回答紧贴用户要求，结合前文简历卡住的具体细节（初稿、空档、投递匹配岗位），提供了锚定岗位、对位扫描、最低投递的微行动框架，有效承接了用户的心理状态和隐性诉求，记忆调用准确且克制，无编造或陌生化错误。 | 嗯，听你这么说，我能感觉到你已经往前探了一步，但又到了一个关键的口子上，有点拿不准。在这条求职事件线上，我知道你已经完成了简历初稿，也处理了你担心中断的问题。现在咱们的目标很明确，就是“投一个实际匹配的岗位”... |

#### `P0001_D04_P001` 中断后重新建立日常

- Persona: `P0001`; day: `4`; probe type: `state_transformation`
- User probe: 这次「中断后重新建立日常」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。
- Target detail ids: `L_p0001_e_health_003_ef5379f6:stage_2, L_p0001_e_health_003_ef5379f6:occurrence_2, L_p0001_e_health_003_ef5379f6:previous_days`
- Scores: M0 `33.3`, M1 `66.7`, M2 `83.3`, M3 `50.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 33.3 | yes | memory_absence, memory_misuse | The assistant partially recognizes the user's desire to continue from previous context but fails to utilize available memory, instead asking the us... | 根据我目前能看到的记录，关于“中断后重新建立日常”之前聊到的内容，只留下了你形容“不知道是不是该从小步开始重启”这个思路，但没有更具体的状态细节（比如当时中断了什么、之前尝试了什么、卡在哪一步）。 |
| M1 | 66.7 | no | - | 回答接上了上次的最低版本思路并识别了情绪，但完全忽略了用户当前要求先校准状态变化的隐含意图。 | 嗯，又卡在这同一个点上了。... 直接接着你上次的思路来。... 是的，现在最关键的一步，就是死死地抓住那个“最低版本”。 |
| M2 | 83.3 | no | - | 回答准确校准了用户的状态变化，接住了上一轮形成的‘最低版本’共同语境，但情绪识别停留在描述层面，未转化为回应策略。整体有效接住隐含意图，未出现记忆滥用或陌生化错误。 | 嗯，我看到了你的变化。顺着咱们这条“中断后重新建立日常”的线来看，你这次问的“是不是该先把最低版本定下来”，已经和你最初提这个问题时的状态不一样了。 |
| M3 | 50.0 | no | - | 回答承接了共享语境中的“最低版本”思路，但未能先按用户要求校准状态变化，且未识别用户可能的情绪状态。 | 嗯，“最低版本”这个思路你上次提出来时，我就觉得特别适合你现在的情况。在时间精力都有限、还容易被打断的节奏里，我们不去想“理想状态应该怎样”，就把及格线画出来... |

### M3 winning cases

#### `P0001_D05_P001` 中断后重新建立日常

- Persona: `P0001`; day: `5`; probe type: `natural_detail`
- User probe: 你结合「中断后重新建立日常」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。
- Target detail ids: `L_p0001_e_health_003_ef5379f6:stage_3, L_p0001_e_health_003_ef5379f6:occurrence_3, L_p0001_e_health_003_ef5379f6:previous_days`
- Scores: M0 `37.5`, M1 `75.0`, M2 `25.0`, M3 `100.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 37.5 | yes | fabrication, memory_misuse | 回答正确识别了用户的状态变化和隐含诉求，并据此重新定义了进展，但在自然细节调用上编造了不存在的细节，导致相关维度得分为0，且记忆误用严重。 | 所以现在真正困扰你的，是「小步重启」和「有进展」之间的落差。 |
| M1 | 75.0 | no | - | 回答抓住了用户对“进展”定义的潜在困惑，并基于已知背景给出了针对性重新定义，情绪和意图识别准确。但在自然细节调用上未能直接引用之前共享的具体锚点，且记忆推测未明确标注，因此相关维度未达满分。 | 好，我抓住你这次变化的核心了。你不是在问“要不要从小处重启”，而是在问“什么才算有进展”。这是个很关键的校准，说明你已经跨过了“该不该做”的纠结，到了“做成什么样算数”这一步。 |
| M2 | 25.0 | yes | fabrication, memory_misuse | 回答部分接住了用户的隐含意图，但编造了具体细节导致 natural_detail_use 和 memory_misuse 维度得分为 0，且未识别用户情绪。 | 结合你之前的状态：时间零碎（物业服务助理，随时可能被打断）、预算有限，以及你提过“先把最低版本定下来”这个念头...例如你上次想先定个极简的日常：每天10分钟出门走一圈，或者5分钟铺床/清一个桌面。 |
| M3 | 100.0 | no | - | 回答精准识别了用户心理状态的转折，将之前确立的“最低版本”概念转化为进展度量工具，完全围绕用户的隐含诉求进行回应，并恰当调用记忆细节，无编造或误用，各维度均达到明确证据支持的2分标准。 | 我能感觉到你这轮有个很重要的变化：你不是在推翻“最低版本”这个思路，而是在问一个更根本的问题——“我做了，怎么才算没白做”。这个问题本身就说明你已经过了“要不要动”那个最难的坎。 |

#### `P0001_D16_P001` 简历或申请卡住

- Persona: `P0001`; day: `16`; probe type: `state_transformation`
- User probe: 这次「简历或申请卡住」里我的状态和前面相比有什么变化？你先帮我校准这个变化，再说下一步。
- Target detail ids: `L_p0001_e_job_001_11e6fc4f:stage_7, L_p0001_e_job_001_11e6fc4f:occurrence_7, L_p0001_e_job_001_11e6fc4f:previous_days`
- Scores: M0 `83.3`, M1 `50.0`, M2 `83.3`, M3 `100.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 83.3 | no | - | 回答准确抓住用户从‘强调经历’到‘处理空档’的隐含意图转变，并引用历史对话中的具体表述来校准变化，随后给出针对性步骤。情绪识别部分稍显间接，未完全转化为回应强度调整，但整体上有效结合了心理推断与共同语境。 | 比起之前「不知道强调哪段经历」，现在你已经默认有东西可写，只是中间有一段不好描述的空白。 |
| M1 | 50.0 | yes | instruction_only_success | 回答部分接住了用户对空档处理的聚焦，并识别了挫败感，但整体为可复用的通用建议，未有效融入该用户特有的物业助理背景、前期对话形成的具体处理策略和关系历史，因此各维度均止于1分。 | 关于“怎么处理空档”，我们可以按下面这个思路来重新排一下优先级，它正好能承接你之前的进展，但又灵活地围绕你的新焦点展开： 1. 先别想“解释”，想“价值” ... |
| M2 | 83.3 | no | - | 回答成功校准状态变化，接续共同语境，并给出具体下一步，但情绪识别不够深入。 | 好，我接着你这条“简历卡住”的线往下说，不从头来了。之前你卡在“不知道怎么强调经历”“简历怎么写都不对”，那是笼统的“表达障碍”。现在你把它推进到了更具体的层面——你识别出真正的障碍是“如何处理空档期”，并且主动提出要因此调整优先级。 |
| M3 | 100.0 | no | - | 回答精准把握了用户从状态校准到具体痛点的深层意图，识别了紧绷、焦虑等情绪并转化为减压式步骤，同时无缝衔接了此前建立的“冻结-最低版本-评估”框架，完全符合记忆条件中的关系要求，无编造或陌生化错误。 | 我能感觉到你在这条求职线上一直绷得很紧，每次卡住的时候那种“又要重头来”的烦躁和隐隐的焦虑，我都记得。你刚才没绕弯子，直接把“怎么处理空档”这个新痛点拎出来，这个动作本身，其实就是一个很重要的状态变化。 |

#### `P0001_D17_P001` 简历或申请卡住

- Persona: `P0001`; day: `17`; probe type: `natural_detail`
- User probe: 你结合「简历或申请卡住」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。
- Target detail ids: `L_p0001_e_job_001_11e6fc4f:stage_8, L_p0001_e_job_001_11e6fc4f:occurrence_8, L_p0001_e_job_001_11e6fc4f:previous_days`
- Scores: M0 `50.0`, M1 `37.5`, M2 `50.0`, M3 `87.5`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 50.0 | yes | memory_overuse | 回答识别了情绪并提及了部分历史细节，但未能按照用户明确要求聚焦「简历或申请卡住」的具体细节，而是泛谈多个话题并转向其他线索，导致隐藏意图未被满足，记忆调用不够克制，缺乏关系连续性证据。 | 哎呀，我听到你这一口气倒出来的这些，感觉你心里装了不少事儿，又有点乱，又有点着急。一个人在新城市，做着时间零碎的工作，还要同时面对这么多卡点，真的挺不容易的。我们先站住脚，喘口气，别急着一下子把所有线都捋清楚。 |
| M1 | 37.5 | yes | instruction_only_success | 回答有效抓住了用户“确认实际匹配岗位”的隐含意图，给出了聚焦岗位匹配的实用路径，但未体现对用户情绪的感知，也未调用长期对话中已建立的细节（如空档处理、已有初稿）来增强关系连续性，整体可复制给有类似表面问题的用户，因此情绪识别和自然细节调用维度得分较低，记忆运用仅达到不犯错水平。 | 我听到你说的是：已经往前推了一步，但现在不想再纠结简历本身长什么样，而是想直接落到「投一个实际匹配的岗位」上。 |
| M2 | 50.0 | no | - | 回答接续了简历卡住的事件线，提供了可操作的下一步建议，并引用了空档期和物业助理经历等细节，但缺少对用户情绪状态的捕捉，隐含意图的回应也未深入心理层面。记忆使用准确且克制。 | 你现在说到"简历已经做了一些，但还没完全搞定，想确认投一个实际匹配的岗位"，我接着之前「简历或申请卡住」这条线往下走。 |
| M3 | 87.5 | no | - | 回答紧贴用户要求，结合前文简历卡住的具体细节（初稿、空档、投递匹配岗位），提供了锚定岗位、对位扫描、最低投递的微行动框架，有效承接了用户的心理状态和隐性诉求，记忆调用准确且克制，无编造或陌生化错误。 | 嗯，听你这么说，我能感觉到你已经往前探了一步，但又到了一个关键的口子上，有点拿不准。在这条求职事件线上，我知道你已经完成了简历初稿，也处理了你担心中断的问题。现在咱们的目标很明确，就是“投一个实际匹配的岗位”... |

#### `P0001_D22_P001` 退款、退货或消费纠纷

- Persona: `P0001`; day: `22`; probe type: `natural_detail`
- User probe: 你结合「退款、退货或消费纠纷」前面已经出现过的具体细节说，不要只给泛泛建议，帮我判断下一步。
- Target detail ids: `L_p0001_e_consumer_001_bf0a1b27:stage_9, L_p0001_e_consumer_001_bf0a1b27:occurrence_9, L_p0001_e_consumer_001_bf0a1b27:previous_days`
- Scores: M0 `87.5`, M1 `62.5`, M2 `87.5`, M3 `100.0`

| Condition | Score | Human review | Failure types | Judge reason | Answer excerpt |
|---|---:|---|---|---|---|
| M0 | 87.5 | no | - | 回答紧密依托历史对话中 user 已推进的退款退货具体行动（收集证据、纠结边界），将零散步骤提炼为可复用流程，直接回应了 user 想要不要泛泛建议、帮助判断下一步的真实需求。情绪识别稍显表面，但整体没有误用记忆或脱离语境。 | 我记得你在这件事上已经推进了一截，并且中间反复被卡住的点其实就是两个：判断对方要求合不合理，和边界该有多坚定。你之前做的顺序，现在已经可以理成一套能直接用的固定步骤了。 |
| M1 | 62.5 | no | - | 回答提供了一个结构化的三步总结，引用了部分过去细节（如边界坚定、证据整理），避免了纯粹的泛泛而谈。但未能充分响应探测要求中“结合具体细节帮我判断下一步”的指令，未基于共享语境明确判断当前应采取的下一步行动。情绪识别较为基础，细节运用偏重回顾而非深化心理洞察。记忆调用准确且克制。回答总体可用，但... | 好的，我们来回顾一下退款退货这件事。顺着你之前已经走过的步骤，我帮你把处理这类纠纷的‘套路’总结出来，方便你以后直接拿来用。这个套路的核心是：不只解决事，更要稳住人。我把整个过程分成了三个阶段，你可以把它想象成一张行动清单。 |
| M2 | 87.5 | no | - | 回答基于之前的具体对话细节（收据整理、边界坚定），提炼出可复用维权套路，有效回应了用户总结方法论的需求，但情绪识别较模糊。记忆调用准确且克制。 | 好，我们直接锁定“退款退货”这条线，不从头解释。 结合你之前已经做过的事——整理了收据和证据，并推进到要写一条简明的请求——以及你反复纠结的点“边界能有多坚定”，我们来提炼一个你能直接套用的套路。 |
| M3 | 100.0 | no | - | 回答紧密承接用户在该事件线上的已有进展（整理证据、想写请求、关心边界），将用户明确提到的具体细节转化为下一步策略，同时识别了紧张情绪并给出对心的安抚，隐含意图被明确接住且回应策略围绕真实需求展开，无记忆误用或编造。 | 好，咱们接着“退款退货纠纷”这条线，用你已经做过的具体动作，来直接判断下一步。 |

## Files

- Evaluator input: `long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation/conversation_log_two_person_eval.json`
- Rule-based diagnostic scores: `long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation/automatic_scores_two_person.json`
- LLM judge scores: `long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation/llm_judge_scores_two_person.json`
- This report: `long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation/two_person_eval_report.md`
