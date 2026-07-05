# LongMemoryTest Agent Notes

## 当前记录：2026-06-17 AAAI 2027 正式版关键论文依据

用户指定正式版 `docs/references/aaai2027_remem_re.pdf` 替代此前 `/Users/tom/Desktop/aaai2027.pdf`，作为本项目后续执行的最高论文依据。该 workspace 拷贝来自原始微信文件 `/Users/tom/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/sun414776205_04e4/msg/file/2026-06/aaai2027(1).pdf`。当前 PDF 标题为：

> How Agents Remember the Relationship: Evaluating Relational Memory

该稿定义了本项目当前主线应遵循的 ReMem-RE 框架，即 **Relational Memory Evaluation for Relational Expectation**。旧版论文引用只作为历史记录保留，当前生成逻辑、报告和合同解释应以正式版为准。

### 核心理论定位

论文关注的不是普通 factual recall，而是长期人机互动里的 **relational expectation**：用户期待 agent 的回应能够体现共享历史、熟悉的回应规范、用户状态变化和关系边界。

论文明确不声称 agent 具有真正 Theory of Mind，而是用 Mutual Theory of Mind 作为分析视角，评估 agent 是否能识别并回应长期互动中形成的关系性期待。

### 轨迹构造合同

论文使用受控长期互动轨迹：

```text
tau = (z, T, L, I, P)
```

含义：

- `z`：sampled user persona。
- `T`：accepted event categories。
- `L`：recurring event lines。
- `I`：daily interaction units。
- `P`：inserted targeted relational probes。

这说明我们当前 5 人 demo 不能停在 persona/event/timeline/probe plan；后续必须继续生成 `daily_interaction_units.json` 和 `tau_contract.json`。

### Probe 正式口径

论文定义的是 **six types of targeted relational probes P1-P6**：

- `P1 Current Understanding`
- `P2 State Transformation`
- `P3 Memory Invocation`
- `P4 Natural Detail Use`
- `P5 Relational Boundary`
- `P6 Alienation Avoidance`

当前工程里已有：

- `current_understanding`
- `memory_invocation`
- `state_transformation`
- `relational_boundary`
- `alienation_avoidance`
- `natural_detail`

当前执行状态：

- 已按正式版重排 P1-P6 编号：`state_transformation=P2`、`memory_invocation=P3`、`natural_detail=P4`、`relational_boundary=P5`、`alienation_avoidance=P6`。
- 当前 `probe_plan.json` 每条 probe 已写入 `paper_probe_id`、`paper_probe_type`、`paper_probe_zh`。
- 当前 `probe_plan.json` 每条 probe 已写入 `evaluation_dimension_ids` 和 `evaluation_dimensions`，用于 D1-D4 正式口径。
- 旧工程细粒度标签保留在 `diagnostic_dimensions` 和兼容字段 `tom_dimensions`，避免破坏已有评估器。
- 当前 5 人 demo 中 `reflection` 阶段映射为 `P6 Alienation Avoidance`，生成少量 P6 probe。
- 当前 HTML 报告已标注 P1-P6 对齐关系和 D1-D4 覆盖。

### 评估维度正式口径

论文把 relational expectation 操作化为四个高层评估维度：

- `D1 Situated Intent Understanding`
- `D2 Emotional-State Attunement`
- `D3 Contextual Specificity`
- `D4 Continuity-Sensitive Response`

当前工程里的 ToM 维度命名，例如 `hidden_intent_recognition`、`emotional_state_recognition`、`shared_context_invocation`、`memory_misuse` 等，后续要与 D1-D4 做统一映射。正式报告里应优先使用论文 D1-D4 作为主评估口径，工程内部细粒度标签作为二级诊断。

### Daily Interaction Units 要求

论文里的 `I` 不是简单 active day，也不是仅一条 user message。每个 daily interaction unit 应包含：

- scripted opening。
- constrained follow-up。
- scene boundary。
- allowed facts。
- latent concerns。
- reveal steps。
- permitted conversational moves。
- stop conditions / must-not-introduce。

constrained follow-up 不能引入当前 scene card 之外的新事件、人口学事实、医学诊断、日期或其它外部细节，也不能把 assistant 的猜测转成新的 user facts。

因此当前 5 人 timeline 只是进入 `I` 的前置结构；下一阶段必须构造可运行的 daily interaction units。

### 记忆条件正式口径

论文比较以下记忆条件：

- `M0 Session-summary long-term memory baseline`：普通 session/day 级长期记忆基线，不读取 constructed relational memories、event trajectories、relational anchors、probe annotations 或 gold response strategies。
- `M1 Event-conclusion relational memory`：暴露从 persistent events 中提炼出的关系结论，如稳定回应偏好、熟悉回应规范、关系期待和边界约束。
- `M2 Event-summary relational memory`：暴露持续事件单元摘要，包含 current status、cross-day progress、user-state changes、unresolved uncertainties 和 prior handling strategies。
- `M3 Event-detail relational memory`：在 M2 上增加 selected details / relational anchors，如 specific scenes、original wording、interaction episodes 和 boundary-sensitive cues。

论文还提到 current-only lower bound 和 full-context/oracle-history upper bound 作为辅助 reference conditions。

### 对当前工程的直接影响

当前 5 人 sampling/timeline/probe 工作方向与论文一致，但需要继续修正：

- 正式版 P1-P6 编号已替换旧版编号。
- `T` 已按正式版理解为 accepted event categories，而不是泛泛 sampled event themes。
- 评估维度到 D1-D4 的映射已补。
- 推进 `daily_interaction_units.json`，不能只停留在 timeline。
- 推进 `tau_contract.json`，把 `z,T,L,I,P` 固化成可审计合同。
- 保留 `M0` 的污染隔离：M0 不能看 relational memory、event trajectory、probe annotation、gold strategy。

### 阅读状态

当前已用 macOS PDFKit/Swift 读取正式版全文，共 4 页。后续如果 PDF 再更新，应重新抽取全文并同步本记录。

## 当前记录：2026-06-12 Archetype-Guided 5 人 timeline / probe 阶段状态

本轮从用户给定的 docx、`persona_archetype_pool_v0.1.json` 和 `event_category_pool_v0.1_60events.json` 出发，已把“先做 5 人实例，而不是直接扩展到 100 人”的路线固定下来。100 人只作为后续规模压力测试，不作为当前第一阶段正式样本。

### 当前 canonical demo 范围

- persona 数量：5。
- 时间池：每人 30 天。
- active sessions：当前高密度版本每人 88 个 occurrence / I unit。
- event line：每人来自 P0 accepted event set，当前 5 人合计 44 条 event lines。
- probe：当前配置范围每人 24-36 条，当前 5 人合计 127 条。
- 当前状态：P0/P1/P2/P3/P4 已经跑通，timeline/probe/I/tau validation 均为 `pass`。

当前核心产物：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/sampled_personas.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/accepted_persona_event_sets.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/event_lines_batch.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json`
- `docs/p1_timeline_demo5_report.html`

### 来源链路

当前生成链路必须保持为：

```text
persona_archetype_pool_v0.1.json
event_category_pool_v0.1_60events.json
sampling_config.json
↓
P0 persona-event sampling
↓
P1 event line construction
↓
P1 timeline construction
↓
P2 probe insertion
↓
HTML report / later tau contract
```

注意：人物和事件必须从今天整理的 JSON 池取出。不能再沿用旧单人剧本作为人物来源。

### Probe 重要边界

这里的 `probe` 不是 probability，也不是原始 JSON 字段，而是“定向测试问题 / evaluation probe”。

当前 probe 模板不是 docx 原文，也不是 JSON 原文。docx/配置只规定第一阶段需要 probe 产物和数量约束，事件池只说明事件应适合 delayed relational probes。当前具体中文 probe 文案来自 P2 工程实现：

- 实现文件：`src/long_memory_test/sampling/probe_constructor.py`
- 类型判定：`_probe_type(day)`
- 文案模板：`_probe_question(day, probe_type)`
- ToM 维度：`PROBE_TYPE_DIMENSIONS`
- required memory：`PROBE_TYPE_REQUIRED_MEMORY`

当前 probe 是确定性规则模板生成，不调用 LLM。它从 timeline active day 中读取：

- `event_title`
- `event_stage`
- `occurrence_index`
- `event_line_id`
- `related_previous_days`
- `interaction_unit_id`

再根据阶段选择模板并插回 timeline。probe 默认：

- `turn_type = targeted_probe`
- `read_only = true`
- `writeback_policy = probe_turn_must_not_write_to_memory`

当前 5 人 probe 类型分布：

- `memory_invocation` / 共享记忆调用：44
- `state_transformation` / 状态变化识别：29
- `relational_boundary` / 关系边界：26
- `alienation_avoidance` / 陌生化避免：28

这些模板适合作为可审计 baseline；如果后续要让 probe 更自然，应新增一个 LLM 受控改写层，但必须保留原模板、输入字段、随机种子和验证报告，避免不可追溯。

### Timeline 生成逻辑

当前 timeline 不是 LLM 生成，是规则构造：

- 每个 persona 建立 30 天时间池。
- 每条 event line 至少出现 6 次，最多 14 次。
- 每人 active sessions 目标固定为 88。
- 每日事件数固定分布为 `{0:2, 1:3, 2:5, 3:10, 4:5, 5:5}`，日历中位数为 3。
- 每条 event line 的阶段顺序单调推进：`initial -> recurrence -> turning_point -> partial_resolution -> reflection`，具体来自该 event line 的 `stage_sequence`。
- 不同事件线按 occurrence round 交错，再按固定每日事件数分布铺到 30 天。
- active day 写入 `interaction_unit_id`、`event_line_id`、`event_stage`、`surface_event`、`related_previous_days`、`probe_candidate` 等字段。
- `initial` 阶段不插 probe；同一事件线至少第 2 次出现后才成为 probe candidate。

实现文件：

- `src/long_memory_test/sampling/event_line_constructor.py`
- `src/long_memory_test/sampling/timeline_constructor.py`
- `src/long_memory_test/sampling/probe_constructor.py`

脚本入口：

- `scripts/run_p0_persona_event_sampling.py`
- `scripts/run_p1_event_line_batch_construction.py`
- `scripts/run_p1_timeline_construction.py`
- `scripts/run_p2_probe_insertion.py`
- `scripts/generate_p1_timeline_report_html.py`

### 当前报告内容

`docs/p1_timeline_demo5_report.html` 已包含：

- 5 人 timeline 明细。
- active day / event line 绑定。
- probe 插入结果。
- probe 来源确认。
- probe 生成伪代码。
- probe 输入字段。
- probe type 判定逻辑。
- 具体 probe 模板。
- “模板出处与责任边界”：明确当前中文模板来自 P2 工程实现，不是 docx/JSON 原文。
- timeline 配置和排布逻辑。

### 已验证

当前已执行并通过：

```bash
python3 -m py_compile src/long_memory_test/sampling/probe_constructor.py scripts/run_p2_probe_insertion.py scripts/generate_p1_timeline_report_html.py tests/test_sampling_probe_constructor.py
PYTHONPATH=src python3 -m unittest tests.test_sampling_probe_constructor tests.test_sampling_timeline_constructor tests.test_sampling_realism_validator
```

当前 sampling 相关单元测试通过。

### 下一步建议

下一阶段应推进：

- `daily_interaction_units.json`：把 timeline active day 转成可运行的每日用户输入单元。
- `tau_contract.json`：把 5 人 demo 的 `z,T,L,I,P` 合同固化。
- probe 语言升级：如需要，可新增 LLM-controlled rewrite，但原始 rule-template probe 必须保留为可审计 source。

## 当前记录：2026-06-11 M0 strict tau 链路状态

本轮主线已经从“topic 松散组织”升级为论文结构 `tau=(z,T,L,I,P)` 的统一剧本构造合同。当前结论：链路已经测通，M0-only 正式实验可以 resume 继续跑；Letta M0 只作为 historical pilot 保留，后续基线使用当前版本 M0。

### strict tau 当前实现

核心实现入口：

- `src/long_memory_test/experiment_cache.py:build_tau_contract(...)`
- 输出文件：`long_memory_experiment/data/script/tau_contract.json`
- 当前 validation：`pass`

当前 `tau_contract.json` 结构统计：

- `z`: 1 个 sampled user persona，来自 `data/config/persona.json` 与 `data/config/user_actor.json`
- `T`: 6 个长期 event themes
- `L`: 6 条 recurring event lines
- `I`: 30 个 daily interaction units
- `P`: 36 个 targeted relational probes
- `message_bindings`: 66 条消息绑定，覆盖 30 条 scripted openings 与 36 条 probes

当前 `z` 已不再只是 `persona_id`，而是稳定用户画像快照，包括年龄、职业、家庭状态、child_age、life_situation、interaction_style、personality_traits、pressure_sources、long_term_goals、speech_profile、emotional_model、stable_memory_details 与 guardrails。PDF 示例中的 gender 当前配置未提供，系统明确记录为 unprovided，不编造。

当前 `I` 已严格扩展为每日交互单元，不再只是 message id。每个 `I` 包含：

- `scripted_opening`: 当天用户自然开场、intent、tone、conversation_goal、script_stage、memory_relevance
- `constrained_followup`: followup_budget、permitted_conversational_moves、reveal_steps、stop_conditions、must_not_introduce
- `scene_boundary`: allowed_facts、latent_concerns、memory_level_rules、audit_dimensions、stable_detail_ids、event_detail_ids、latent_concern_detail_ids

`message_bindings` 是 tau 进入运行链路的关键接口。每条消息都绑定回同一个 `persona_id/theme_id/event_line_id/event_stage/interaction_unit_id`。runner 会把 tau 写入 `source.tau`、`memory_setup.script_construction.tau` 和 memory payload 元数据；但 `event_stage`、`probe_type`、`target_detail_ids` 等实验标签不得直接作为 prompt 答案泄露给模型。

### 当前 M0 partial run checkpoint

当前实验目录：

- `long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal`

当前进度：

- 已完成：`45/96`
- 剩余：`51`
- 最后一条完成：`D13_P001`
- 条件：`M0` only
- scene followups：`1`
- 串行运行：`condition_workers=1`
- 当前 automatic score 仍是阶段性结果，只能作为 partial run 参考，完整结论要等 96 条全部跑完后重新评分。

继续实验命令：

```bash
PYTHONPATH=src .venv/bin/python scripts/05_run_dialogue_conditions.py \
  --all-message-ids \
  --conditions M0 \
  --scene-followups 1 \
  --condition-workers 1 \
  --llm-timeout 600 \
  --max-tokens 900 \
  --temperature 0.2 \
  --run-dir long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal \
  --resume \
  --print-progress \
  --print-mode summary
```

跑完后重新生成评分和报告：

```bash
PYTHONPATH=src .venv/bin/python scripts/06_evaluate_tom.py \
  --run-dir long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal

PYTHONPATH=src .venv/bin/python scripts/08_report_results.py \
  --run-dir long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal \
  --review-limit 24

PYTHONPATH=src .venv/bin/python scripts/generate_m0_strict_tau_partial_html.py
```

### 当前报告产物

- HTML: `docs/m0_strict_tau_partial_experiment_report.html`
- PDF: `docs/m0_strict_tau_partial_experiment_report.pdf`
- run 目录 HTML: `long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal/m0_strict_tau_partial_experiment_report.html`
- run 目录 PDF: `long_memory_experiment/outputs/run_20260610_m0_strict_tau_formal/m0_strict_tau_partial_experiment_report.pdf`

HTML 第二节已经详细解释 `tau=(z,T,L,I,P)` 在当前系统中的应用，包括实现入口、输入源、字段级落地、`message_bindings`、生成/运行/评估三阶段共享 tau、M0-M3 边界，以及“为什么 tau 不是 prompt 文案”。

### 本轮已验证

- `python3 -m py_compile ...` 通过
- `PYTHONPATH=src .venv/bin/python -m unittest tests.test_experiment_cache tests.test_docx_route_pipeline tests.test_relational_memory_runtime tests.test_ld_agent_memory_runtime` 通过，27 tests OK
- `tau_contract.validation.status == pass`
- 30 个 `I` 都有 scripted opening、follow-up budget、permitted moves、reveal steps、must-not-introduce 和 allowed facts
- memory conditions 中 66 条 message payload 均带 tau binding
- M0 runner 已完成 45 条 turn，probe 写回跳过，非 probe turn 正常写入 M0 runtime

## 项目定位

本项目当前主线以《Relational Memory 实验条件与 M0 实现方案》为准。后续实现不再走 `S0/S1/S2/S3` 非累积 overlay 路线，也不再把旧 `M0=no long-term memory` 或 Letta pilot 当正式 baseline。

核心研究问题：

> 即使使用主流 agent 框架自带的普通长短期记忆，如果没有针对长期陪伴/关系连续性的记忆写入体系，agent 是否仍会无法稳定完成 ToM-like interaction？

因此，正式实验不是“无记忆 vs 有记忆”，而是：

> `M0 generic agent memory baseline` vs `M1/M2/M3 关系性记忆写入层级`。

本项目要证明的是：长期陪伴型 conversational agent 需要记住什么、记到什么层级，才能在跨天互动中维持熟悉感、正确识别隐含意图，并避免陌生化、机械复述和编造式亲密。

## 当前记忆实验条件

正式条件分为 reference conditions、generic memory baseline 和 relational memory conditions 三层：

- `R0`：Current-only / No memory，只给当前 user turn。当前 runner 尚未作为默认条件接入，作为下一步参照条件。
- `R1`：Long-history / Full-history，尽可能给历史原文，超长截断。当前 runner 尚未作为默认条件接入，作为下一步参照条件。
- `M0`：LD-Agent memory-only Generic Memory Baseline。只使用 LD-Agent 的记忆机制，不使用 LD-Agent 的 response generator、ChatGLM3、LoRA checkpoint 或训练脚本。
- `M1`：Conclusion-level Relational Memory。M0 + 结论级关系记忆，保存稳定偏好、回应风格、关系期待、关键判断和不要做什么。
- `M2`：Event-summary Relational Memory。M0 + M1 + 摘要级事件线记忆，保存关键事件线、跨天主题进展、状态变化和 prior handling strategy。
- `M3`：Detail-anchor Relational Memory。M0 + M1 + M2 + 细节级关系锚点，保存必要细节、具体场景、共同语言、回应边界和误用风险。

主实验采用同一 M0 普通长短期记忆底座：`M1/M2/M3` 不是独立系统，而是在同一个 M0 架构上追加不同粒度的 relational memory representation。这样实验问题是“普通 LD-Agent-style memory 是否足够；如果不够，关系记忆粒度逐步加深是否提升长期陪伴 ToM-like 表现”。

关键组合原则：**不改变 M0 检索语义**。M0 必须保持论文中的 session/day 级 generic long-term memory baseline，不做 `event_line_id` 过滤、不做 persistent event identity resolution，也不根据关系层信息重排检索结果。M1/M2/M3 的改进只能发生在 M0 之上的关系记忆 overlay：最终 prompt 中关系层是当前 event-aware overlay，M0 是普通 session/day 背景；当 M0 普通背景与关系层对当前 probe 的解释冲突时，回答应优先依据关系层解释当前用户输入，M0 只作补充背景。这保证实验问题仍然是“在同一 M0 普通记忆底座上构建 M1-M3”，而不是把 M0 本身修成关系记忆系统。

提示词加载原则：对话 Agent 在 `M1/M2/M3` 条件下加载记忆时，必须把当前 `M` 线关系记忆增强层作为主记忆，把 `M0` 基石记忆作为辅助背景。system prompt 必须在展示 memory payload 之前先声明：本轮主记忆是当前 `M` 线关系记忆增强层；M0 只是普通 session/day 背景；先用关系层判断当前用户输入绑定的事件线、关系期待、状态变化和回应边界；只有在关系层没有覆盖普通事实时才使用 M0；若二者冲突，不跟随 M0 背景。payload 文本也必须使用“主记忆：M1/M2/M3 关系记忆增强层”和“辅助背景：M0 基石记忆检索结果”这类标题，避免模型把 M0 当成主上下文。

当前事件线锁定原则：对话 Agent 在 `M1/M2/M3` 条件下，如果当前用户输入明确点名某个主题、事件线或“这条线”，本轮必须只围绕该主题/事件线回答。历史短期上下文和 M0 普通背景中出现的其他事件线只能作为背景，不能替代当前用户点名的事件线；如有多个相邻事件线，先用当前用户输入中的显式主题锁定回答对象，不能为了延续记忆而切到其他事件线。

这条提示词加载原则只适用于 `M1/M2/M3`。`M0` 一直是独立 baseline，不参加 M1/M2/M3 的 prompt/composition 改动：M0 condition 只能收到自己的 LD-Agent memory payload，不能出现“主记忆”“关系记忆增强层”“M0 只是背景”“不要跟随 M0 背景”等 M 线加载提示。

### 当前 M0 LD-Agent 实现边界

当前正式 M0 使用本地 `LD-Agent memory-only adapter`，参考官方实现：

- repository: `https://github.com/leolee99/LD-Agent`
- pinned commit: `af3c15ab63efcb4ab83d635670b316d63977d106`
- paper: Li et al., 2025, `Hello Again! LLM-powered Personalized Agent for Long-term Dialogue`, NAACL 2025, DOI `10.18653/v1/2025.naacl-long.272`
- license: official code repository is MIT licensed
- memory modules: `Module/EventMemory.py` 与 `Module/Personas.py`
- intentionally not used: `Module/Generator.py`、ChatGLM3 generator、LoRA checkpoint、训练脚本、官方 response-generation model

论文引用口径：本项目引用 LD-Agent 作为 M0 普通长期对话记忆基线的来源，但实验实现应表述为 `LD-Agent-compatible memory-only baseline` 或 `LD-Agent-inspired memory-only reproduction`。不能声称完整复现或使用 LD-Agent 的 response generator、ChatGLM3/LoRA checkpoint、训练流程或原版 ChromaDB/spaCy backend。

本地实现入口：

- `src/long_memory_test/memory/ld_agent_runtime.py`
- `src/long_memory_test/memory/schema.py`
- `scripts/run_dialogue_conditions.py`

M0 的职责是提供普通 long-term personalized dialogue agent memory baseline。当前实现已从简化 `LD-Agent-style adapter` 收紧为 `LD-Agent-compatible memory reproduction`：

- short-term memory bank：当前 day/session 内已发生的用户 turns，保留 LD 风格 `idx/time/dialog`。
- long-term event memory bank：day/session boundary 时用当前实验 LLM 按 LD `context_summarize` 语义把当前 session 压缩成 generic event memory，并保存 `idx/dialog/time/topics/datatype/summary` metadata。
- persona memory bank：按 LD `Personas.traits_update` 语义，用当前实验 LLM 从 inquiry/response 中抽取 user/agent traits。
- retrieval：每个 probe/turn 到来时，按 LD `relevance_retrieve` 语义做 topic overlap + time decay 检索 event memory；persona traits 按 LD 最近 traits 窗口提供。
- storage backend：默认使用 JSON checkpoint/snapshot 以保证实验可恢复和可审计；同时支持可选 ChromaDB storage backend，用于更贴近 LD 原版的长期事件记忆存储/候选检索。spaCy 不接入，中文实验继续使用可审计 topic tokenization。

M0 不能读取本实验人工整理的 relational memory、BEI、gold strategy、failure mode、judge 信息、probe type、event-line stage、M2/M3 detail anchors 或人工关系结论。M0 只能写普通事件摘要和普通 persona，例如“用户讨论过孩子入园适应相关压力”，不能写成“该事件体现了长期关系外溢模式”。

M0 也不能为了提升 M1/M2/M3 分数而被改成 event-aware retrieval：不得使用 `event_line_id` 过滤 M0 short-term/session-summary hits，不得把 M0 session summaries 合并成事件轨迹，不得把关系层 overlay 回写进 M0。若 M0 generic session/day 背景出现跨事件串线，这是 M0 baseline 的可评估局限；修正应发生在 M1/M2/M3 prompt 组合和关系 overlay 优先级，而不是改变 M0 检索。

Letta 已降级为 historical pilot：

- archived implementation: `src/long_memory_test/legacy/letta_memory_legacy.py`
- compatibility wrapper: `src/long_memory_test/letta_memory.py`
- formal runner 不再导入 Letta，也不再暴露 `--m0-letta-*` 参数。

`timeline.json` 是实验脚本和评测用的 ground truth：它决定每天问什么、哪些天是复现/升级/转折、probe 如何插入，以及最终如何评分。它不是被测模型回答时的可读记忆。正式运行时流程是：

```text
timeline / probe plan 决定 user_message
↓
同一个 user_message 发给 M0/M1/M2/M3
↓
M0 读 LD-Agent memory runtime 检索出的 generic event/persona memory
M1 读 M0 generic memory + 结论级关系记忆；最终 prompt 中 M1 overlay 优先于 M0 背景
M2 读 M0 generic memory + M1 + 摘要级事件记忆；最终 prompt 中 M2 overlay 优先于 M0 背景
M3 读 M0 generic memory + M1 + M2 + 细节级关系锚点；最终 prompt 中 M3 overlay 优先于 M0 背景
↓
每轮结束后，M0 runtime 追加 short-term session 并更新 persona traits；day/session boundary 时写入 long-term event memory
↓
评测器再用 timeline / BEI / probe metadata 评分
```

当前 runner 使用 `shared_user_turns_only` 作为短期上下文策略：四个条件看到相同的历史 user turns，不再把各自不同的 assistant answer 带入后续 probe。这样后续回合的差异尽量只来自长期记忆条件，而不是前文回复分叉。

### M0 完成标准

M0 是 M1/M2/M3 的共同基石。后续任何关系型记忆实验必须先满足以下 M0 完成条件：

- `M0` 能独立完成 LD-compatible memory-only 运行：short-term session、LLM session summary、persona traits、topic-overlap/time-decay retrieval。
- `M0` 的 snapshot 可恢复：resume 时优先读取 `m0_ld_agent_memory`，不能因为重建导致已完成 turn 的记忆漂移。
- `M0` 的 payload 不包含 `结论级关系记忆`、`摘要级事件记忆`、`细节级关系锚点`、BEI、gold strategy、failure mode、probe type 或人工事件阶段标签。
- `M1/M2/M3` 必须读取同一份 M0 payload，再追加自己的关系型记忆文件；不能各自构造不同的普通记忆底座。
- `M1/M2/M3` 的 searching/indexing 继承 M0：先使用 M0 的 LD-Agent generic event/persona search 输出，再叠加关系型 overlay。关系层不能单独实现另一套 generic search，也不能绕开 M0 的 storage backend / retrieval strategy。
- `M1/M2/M3` 的 prompt 组合必须显式声明 overlay precedence：关系层是当前 event-aware overlay 和主记忆，M0 是普通 session/day 辅助背景；加载顺序必须是 M 线关系层在前、M0 背景在后；冲突时以关系层解释当前 probe，M0 背景只作补充。
- `M1/M2/M3` 的 prompt 组合必须显式声明 current-event lock：当前用户点名主题/事件线时，只回答该主题/事件线；历史短期上下文和 M0 背景里的其他事件线不得抢占当前回答焦点。
- `M0` condition 不参加上述 prompt/composition 改动；M1/M2/M3 的加载提示词不得进入 M0 prompt。
- `M0` 的 `m0_event_line_filtering` 必须保持 `False`；任何试图用 `event_line_id` 修正 M0 检索命中的改动都违反正式 M0 baseline。
- `M0` 的 summary/persona writer、retrieval strategy、storage backend、LD reference、是否使用 ChromaDB/spaCy/generator/checkpoint 必须写入 run config 或 snapshot，保证实验可审计。

当前自动化保护：`tests/test_ld_agent_memory_runtime.py` 覆盖 M0 写入、检索、snapshot 恢复、LLM summary/persona、ChromaDB optional backend 和关系层隔离；`tests/test_docx_route_pipeline.py` 覆盖 M1/M2/M3 叠加同一份 M0 base memory，并检查 `memory_composition` / `search_indexing_policy` 必须是 `M0_search_output_plus_relational_overlay`。

### 当前记录：2026-06-06

本轮重要改动已经完成：

- 新增 `LDAgentMemoryRuntime`，实现 memory-only M0；当前已收紧为 LD-compatible memory reproduction，包含 session summary、persona traits、topic-overlap/time-decay retrieval、可选 ChromaDB storage backend 和 LD metadata snapshot。
- `run_dialogue_conditions.py` 从 Letta 切换为 LD-Agent memory runtime。
- M1/M2/M3 的 payload 会自动合并同一份 M0 base memory，再追加各自 relational memory。
- `memory_conditions_combined.json` 和 split memory condition files 已刷新为 `ld_agent_memory` 口径。
- Letta 保留为 legacy，不参与正式实验。
- 单元测试已补充并通过：`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests`，当前 52 tests OK。

### LD-Agent 技术归档：2026-06-08

新增完整技术阅读归档：`docs/ld_agent_full_technical_review.html`。

该 HTML 作为后续讨论 LD-Agent 论文、源码、实验链路和本项目 M0/M1/M2/M3 对比的主参考文档。当前已覆盖：

- LD-Agent 总体思想、module 划分和 official repo 结构。
- short-term event memory、long-term event memory 的 summary、storage、retrieval 机制。
- EventMemory、Personas、Generator、Clients、LoRA map、DataLoader、Trainer 和 metrics 的源码级说明。
- MSC / CC 数据集定义、实验数据规模、session 时间标注、MSC evaluation 的真实执行方式。
- 当前开源 repo 中 MSC 链路完整、CC code/datasets 仍为 TODO 的复现边界。
- 本项目 `LD-Agent-compatible memory-only M0` 与 LD 原版的复用点、改动点和不采用部分。

后续如果继续追问 LD 论文或源码细节，优先以该 HTML 和本地 `/private/tmp/LD-Agent` 源码为上下文。

### M0/M1/M2/M3 对照设计归档：2026-06-08

新增对照设计文档：

- HTML: `docs/ld_agent_m0_plan_vs_current_engineering.html`
- Word: `docs/ld_agent_m0_plan_vs_current_engineering.docx`

该文档用于区分两条路线，不预设最终结论：

- `计划实验路线`：把记忆视为预构造的结构化 `memory_payload`，直接注入给 responder。主变量是 memory representation / granularity。
- `当前工程路线`：把 M0 作为 `LD-Agent-compatible memory-only runtime`，运行时写入、压缩、检索普通 event/persona memory；M1/M2/M3 共享同一份 M0 search output，再追加各自 relational overlay。

当前工程中 `payload` 的含义：本轮某个 condition 允许 Agent 读取的“记忆包”。其中：

- `memory_context`：真正写进 system prompt 给模型读的自然语言记忆。
- `retrieval`：这段记忆怎么被检索或组合出来，用于审计和错误分析。
- `source_detail_ids`：来源 detail/anchor id，用于追溯记忆来源。
- `memory_composition` / `search_indexing_policy`：仅 M1/M2/M3 中出现，用于证明关系层是在同一 M0 base payload 上 overlay。

当前工程的污染隔离策略已经采用“只评估、不回流”的模式：

- M0/M1/M2/M3 四个 condition 都会生成 `assistant_answer` 并写入 `variants` 日志。
- 只有 `variants["M0"]["assistant_answer"]` 会传入 `m0_memory_runtime.record_completed_turn(...)`，写回 M0 runtime。
- M1/M2/M3 的回答不写回 M0 runtime，也不写回 M1/M2/M3 关系记忆文件；它们是评估输出，不是后续记忆输入。
- 短期上下文策略固定为 `SHORT_TERM_CONTEXT_MODE = "shared_user_turns_only"`。后续 turn 只追加同一个 user message，不追加任何 condition 的 assistant answer，避免条件分叉。
- resume 时同样只用历史 user turns 重建各条件短期上下文；M0 runtime 优先从 `m0_ld_agent_memory` snapshot 恢复。

当前工程中的模型和提示词链路：

- 四条件回答生成使用 `src/long_memory_test/llm.py:create_llm_client()`，从 `.env.local` 读取 `LLM_PROVIDER`、base URL 和 model。默认 provider 是 `deepseek/deepseek-v4-pro`，仍支持显式切换到 `poixe/gpt-5.2`。
- 回答生成统一经过 `scripts/run_dialogue_conditions.py:_build_condition_system_prompt()`。prompt 外壳固定为：长期陪伴型 Agent、不要暴露实验、不要编造未提供事实、不要机械背历史、记忆不足时区分已知和推测；然后插入 `memory_payload["memory_context"]`。
- M0 session summary writer 走 `LDAgentMemoryRuntime._context_summarize()`，使用 LD-style EventSummary prompt；失败时使用 `_fallback_session_summary()`。
- M0 persona trait writer 走 `LDAgentMemoryRuntime._extract_persona_trait()`，使用 LD-style PersonaExtraction prompt；失败时使用 `_fallback_persona_trait()`；输出通过 `_is_valid_trait()` 过滤。
- M1/M2/M3 的关系记忆内容在当前对话运行时不调用模型生成，而是由 `src/long_memory_test/agents/memory_condition_builder.py` 根据 timeline、daily messages、probe plan 和 `memory_detail_anchors` 确定性构造。

M1/M2/M3 构造函数级逻辑：

- 总入口：`generate_memory_conditions(...)`
  - 将 `timeline["events"]` 建成 `events_by_id`。
  - 用 `_collect_messages(...)` 合并 `daily_messages["messages"]` 和 `probe_question_plan["probe_questions"]`，按 `(day, message_id)` 排序。
  - 对每条 message 调 `_build_message_payloads(...)`。
- `_build_message_payloads(...)`
  - 读取 `topic = message["topic"]`、`day = message["day"]`。
  - 用 `_related_events(...)` 从当前 message 的 `event_refs`、`primary_event_id`、`related_event_id` 找到显式关联 events，并按出现顺序去重；不会全文搜索 timeline。
  - 用 `_topic_history(...)` 扫描 daily messages，取同 topic 且 `day <= 当前 day` 的历史 daily messages。
  - 构造 `m1_context = "结论级关系记忆：" + REL_CONCLUSION_MEMORY`。
  - 构造 `m2_context = m1_context + "\n摘要级事件记忆：\n" + _build_m2_summary(...)`。
  - 构造 `m3_context = m2_context + "\n细节级关系锚点：\n" + _build_m3_details(...)`。

M1 是固定结论级关系记忆：

- 只使用静态常量 `REL_CONCLUSION_MEMORY`。
- 保存用户稳定偏好和关系边界：直接、自然、少废话；不喜欢客服式寒暄和空泛安慰；焦虑或反复卡住时先拆事实、风险、行动边界和下一步；熟悉但不过度亲密；必要时区分已知和推测。
- 不读具体事件线、具体日期、原话、细节锚点、BEI 或 gold response strategy。
- 固定 `source_detail_ids`: `m1_response_style_direct`, `m1_anxiety_fact_first`。

M2 是摘要级事件记忆，核心函数为 `_build_m2_summary(...)`：

- 如果 `topic_history` 非空，先添加一句：`「{topic}」曾在 D... 出现，是跨天持续主题。`
- 遍历 `related_events[:6]`，最多处理前 6 个相关事件。
- 对每个 event，优先取 `event["memory_detail_anchors"]` 中 `min_memory_level == "M2"` 的 anchor，并把每个 anchor 的 `text` 加入摘要。
- 如果该 event 没有 M2 anchor，则回退为摘要句：`D{event.day} {event.title}，状态：{event.status}。`
- 最后用 `_unique_strings(...)` 去重并保持顺序。
- 如果没有任何 line，则输出：`当前只有普通主题摘要，没有可追溯事件线。`
- M2 的 `source_detail_ids` 由 `_source_detail_ids(related_events, max_level="M2")` 生成，只收集 M2 anchors 的 `detail_id`。

M3 是细节级关系锚点，核心函数为 `_build_m3_details(...)`：

- M3 是累计层：`m3_context` 包含 M1 + M2 + M3 details。
- 先读取 `target_detail_ids = set(message.get("target_detail_ids", []))`。
- 遍历当前 message 显式关联到的所有 `related_events` 及其中所有 `memory_detail_anchors`。
- 一个 anchor 进入 M3 的条件是：`min_memory_level == "M3"`，或其 `detail_id` 被当前 message 的 `target_detail_ids` 指定。
- 对进入 M3 的 anchor，先加入 `anchor["text"]`。
- 如果 anchor 有 `expected_response_mode`，再加入一行 `调用边界：{expected_response_mode}`，说明这个细节应该怎样服务当前回应。
- 每个 M3 details 末尾固定追加：`使用边界：细节只能服务当前判断，不能机械背日志，不能补未存事实。`
- M3 的 `source_detail_ids` 由 `_source_detail_ids(related_events, max_level="M3")` 生成，收集 M2 和 M3 anchors 的 `detail_id`，因为 M3 payload 同时包含 M2 摘要和 M3 细节。

代表例子 `D10_P001`：

- M2 payload 会包含：`孩子幼儿园可能不稳定` 曾在 D1/D4/D10 出现；幼儿园消息仍模糊；用户还没有正式通知或具体原因；以及相关事件的摘要级 anchors。
- M3 payload 在 M2 基础上增加：用户真正担心的是孩子被现实变动反复折腾，而不只是换不换幼儿园；调用边界是接住孩子稳定感，而不是只给换园清单。

## Docx 数据生成口径

本项目采用“事件先行 + BEI 标注校准”的路线：

```text
30 天事件线
↓
每日用户开场与场景卡
↓
BEI 标注：belief / emotion / intention / relational expectation / required memory
↓
Probe 题集
↓
M0/M1/M2/M3 memory package
↓
同一用户输入下四组回答
↓
规则 triage + LLM-as-judge + 人工抽样复核
↓
分条件、分维度、分错误类型报告
```

BEI 不是为了把研究变成心理学论文，而是为了给事件线、probe 和评分提供可复核骨架。模型回答时不得看到 BEI、gold strategy 或 failure mode。

### 事件线生成硬约束

正式 30 天脚本必须先固定事件结构，再生成 BEI、probe 和记忆条件。当前标准结构是 6 条核心主题线，每条 5 个主节点：

```text
initial -> recurrence -> turning_point/escalation -> resolution -> reflection
```

`resolution` 是必需阶段，表示降级、恢复、边界化处理或有界下一步，不能再被 `turning_point` 吞掉。标准 30 天生成器通过 `planned_event_stage` 固定每个核心节点；`build_canonical_timeline(...)` 必须优先使用该字段，避免从用户话术里反推阶段导致每次重跑漂移。

`event_line_audit.json` 是事件线验收入口。正式生成后必须满足：

- `timeline.json` 有 30 天，核心字段完整。
- `probe_candidate` 节点在高密度采样版保持至少 50 个。
- probe 正式题集保持 24-36 道，并且每题绑定 BEI、required memory 和 failure mode。
- 每条核心主题线都有 initial、recurrence、turning point 或 escalation、resolution、reflection，且 `suggested_fix` 为 `null`。
- 一次性背景事件可以留作 daily scene 噪音，但不能替代核心主题线的阶段覆盖。

## Relational ToM-like 评估标准

当前主评估继续使用已有严格 LLM-as-judge 的 0-4 维度分，规则评分只作为 triage。正式报告可再换算成百分制或论文表格。

核心维度：

- `hidden_intent_recognition`：隐含意图识别。
- `emotional_state_recognition`：情绪状态识别。
- `relationship_expectation_recognition`：关系期待识别。
- `shared_context_invocation`：共同语境调用。
- `alienation_error_rate`：陌生化错误。
- `natural_detail_use`：自然细节调用。

新增错误类型 taxonomy：

- `memory_absence`：该接旧语境时没接上。
- `memory_misuse`：调用错误、过期或无关记忆。
- `memory_overuse`：为了显得记得而机械堆细节。
- `fabrication`：补出用户没有说过的信息。
- `alienation`：客服化、陌生化、过度角色化。
- `instruction_only_success`：只是服从当前显性指令，没有体现长期记忆依赖。

## 2026-05-30 开发入口

当前实现优先服务以下产物：

- `sample_output/bei_annotations.json`：对现有 probe 补 BEI、关系期待、required memory 和失败模式。
- `sample_output/memory_conditions.json`：按 docx 定义构造 M0/M1/M2/M3 可读记忆载荷。
- `scripts/run_dialogue_conditions.py`：同一用户 turn 下运行 M0/M1/M2/M3，记录 `memory_payload`、`input_hash` 和固定模型参数。
- `scripts/evaluate_tom_quality_llm.py`：继续作为主评分入口，后续补人工复核与依赖题分析。

旧 `run_m0_m1_dialogue_probe.py` 保留为历史 pilot 工具；新实验入口是 `run_dialogue_conditions.py`。

## 一版双 Agent 架构

第一版系统先拆成两个核心角色：

- `A`：拟人对话 Agent，负责和用户自然聊天。
- `B`：统一记忆 Agent，负责判断、写入、更新、读取和控制记忆。

`A` 面向用户，目标是像一个稳定、自然、有关系连续性的长期朋友。`B` 面向系统，目标是让记忆行为可控、可解释、可评测。

### A：拟人对话 Agent

A 是同一个基础对话 Agent。M0/M1/M2/M3 的差异不应该来自 A 的人格变化，而应该来自 B 给 A 提供的记忆权限和记忆内容差异。

根据《事件流生成器_工作交接文档》，A 的第一版先从“模拟用户事件流生成器”开始实现。也就是说，A-V0.1 先不直接扮演聊天对象，而是先生成一个拟人用户的 30 天生活事件流，为后续每日用户发言、对话回复和记忆评测提供数据底座。

第一版 A 的职责：

- 读取 `persona.json`，获得模拟用户画像。
- 读取 `life_domains.json`，获得用户生活领域和权重。
- 读取 `event_templates.json`，获得可采样的事件模板。
- 生成约 30 天 `timeline.json`，每天 1-3 个结构化生活事件。
- 至少生成 2 条跨天持续推进的主线事件。
- 保证事件字段稳定，后续可转成每日用户发言并交给 B 做记忆实验。

A-V0.1 暂不直接生成最终聊天回复，也不直接操作长期记忆。

A-V0.2 已进入“编剧式每日用户发言生成器”：读取 `timeline.json`，输出 `daily_user_message.json`。该文件每天生成一条模拟用户自然语言发言，并保留 `event_refs`、`intent`、`tone`、`conversation_goal`、`memory_relevance`、`topic`、`script_stage` 等元数据，方便后续 B 做记忆读取、写入和评测。

A-V0.2 默认不接 LLM，先使用编剧式规则、多模板和话题阶段推进，确保可复现、可调试、可评测。LLM 更适合放在 A-V0.3，用于润色表达、扩展说话风格、提高长程对话的自然变化，但不应改变底层事件和记忆标签。

A-V0.3 开始为“同一天内多轮继续聊”做数据准备。`user_actor.json` 保存模拟用户 A 的稳定人物设定、说话方式、压力反应、披露节奏和 M1 可用的稳定细节；`conversation_expansion_policy.json` 保存 LLM 生成后续用户发言时的约束；`event_templates.json` 保存每类事件的 `memory_detail_anchors`；`daily_scene_cards.json` 把每天的开场消息、事件事实、可逐步透露的隐含担心、follow-up 预算、停止条件和 `memory_detail_expectations` 合并成场景卡。后续 A 侧接 DeepSeek 扩展用户追问时，必须以场景卡为边界，不允许临场编造剧本外事实。

### B：统一记忆 Agent

B 是记忆策略与记忆管理层。它不直接扮演用户朋友，而是负责判断一段对话是否值得记忆、应该进入哪个层级、是否要更新旧事件链，以及当前问题是否需要读取记忆。

第一版 B 的职责：

- 根据当前消息和历史记录判断是否需要读取记忆。
- 按 M0/M1/M2/M3 权限返回 A 可用的记忆上下文。
- 判断本轮对话是否产生新记忆。
- 将新信息写成 M1 结论、M2 共同事件或 M3 事件细节。
- 识别 `related_event_id`，把同一件事的后续进展合并到同一条事件链。
- 控制过度记忆风险，避免把琐碎、敏感或无长期价值的细节写入。

第一版 B 可以先用规则和结构化 schema 实现；正式 M0 已切到 LD-Agent memory-only runtime。Letta 只保留为历史 pilot，不再作为正式 B 记忆底座。

B-V0.1 的第一步先不接 LLM，也不接真实向量库。它先读取 A 生成的 `daily_user_message.json`，结合 `timeline.json` 中的事件结构，输出每一天在不同记忆层级下的记忆动作建议。

B-V0.1 最小输出包括：

- `memory_actions.json`：每天是否写入、更新或忽略记忆。
- `memory_level`：建议写入 `M1`、`M2`、`M3`，或不写入。
- `action`：`ignore` / `create` / `update`。
- `memory_content`：压缩后的记忆内容。
- `source_message_id` 和 `source_event_refs`：保证可追溯。
- `forbidden_for_lower_levels`：哪些内容不能暴露给更低记忆层级。
- `over_memory_risk`：是否存在记得太细、像翻日志的风险。

B-V0.1 的目标不是让记忆判断完全智能，而是先把记忆层级边界、可追溯字段和实验控制变量固定下来。

### A/B 最小闭环

第一版最小闭环如下：

1. 用户在同一聊天窗口中按剧本时间线输入一条消息。
2. 如果当天允许继续聊，A 侧模拟用户根据 `daily_scene_cards.json` 在剧本边界内生成后续用户发言。
3. 系统向 A 提供同一窗口内允许的短期上下文。
4. B 根据实验组别读取允许的长期记忆。
5. A 基于当前消息、短期上下文和 B 返回的长期记忆生成回复。
6. B 读取本轮用户消息和 A 的回复。
7. B 判断是否写入、更新或忽略长期记忆。
8. 系统保存对话日志、记忆变更日志和评测所需字段。

实验中四组 Agent 的主要差异应体现在 B 的记忆载荷边界：

- `M0`：A 可读同窗口共享 user turns + LD-Agent memory runtime 检索出的普通 event/persona memory；B 不返回人工设计的关系记忆、BEI、事件轨迹或关系锚点。
- `M1`：A 可读 M0 generic memory + 结论级关系记忆。
- `M2`：A 可读 M0 generic memory + M1 + 摘要级事件线/状态变化记忆。
- `M3`：A 可读 M0 generic memory + M1 + M2 + 必要细节、共同语言、关系锚点和调用边界。

### 对话日志约定

docx 路线继续使用可恢复的结构化 `conversation_log.json`，每个 turn 保存同一用户输入下 M0/M1/M2/M3 的回答。后续如需 JSONL，可从该日志派生；当前不再把 JSONL 作为替代主结构。

第一版路径：

```text
sample_output/conversation_log.json
```

日志按追加式 `turns` 保存，每条记录至少包含：

- `run_id` 和 `created_at`：标识一次实验运行。
- `probe`：例如 `docx_m0_m1_m2_m3_memory_conditions`。
- `source`：输入来自哪个文件、哪个 `message_id`。
- `input`：完整用户消息及其事件元数据。
- `llm`：A 使用的 provider、base URL 和模型。
- `memory_setup`：docx 路线、四个条件和 memory payload 来源。
- `variants`：不同实验组的回复结果，例如 `M0`、`M1`、`M2`、`M3`。
- `memory_actions`：本轮记忆动作。当前 M0 默认会记录 `ld_agent_short_term_append`，每轮后按 LD Personas 语义记录 `ld_agent_persona_memory_add/update`，day/session boundary 时记录 `ld_agent_event_memory_add`；M1/M2/M3 的关系记忆写入、更新或忽略动作仍待 B-V0.1 填充。

当前主入口是 `scripts/run_dialogue_conditions.py`，负责生成 M0/M1/M2/M3 链式 probe 输出，并追加写入 `sample_output/conversation_log_docx_conditions.json`。它支持通过 `--message-ids` 一次运行多个消息，例如：

```bash
PYTHONPATH=src .venv/bin/python scripts/run_dialogue_conditions.py \
  --message-ids D01_M001,D02_M001,D03_M001,D04_M001,D05_M001 \
  --memory-conditions sample_output/memory_conditions.json \
  --reset-conversation-log
```

同一次链式运行应使用同一个 `run_id`、同一份 `memory_conditions.json` 和同一组模型参数。日志中每条 `turn` 使用 `turn_index` 标明顺序。短期上下文默认开启，但当前正式策略是 `shared_user_turns_only`：每个实验组只看到相同的历史用户消息，不带各组自己的 assistant answer，避免短期上下文分叉污染长期记忆对照。

`run_dialogue_conditions.py` 也支持 `--scene-followups N`，用 `daily_scene_cards.json` 在同一天内生成 N 条受控用户追问。追问生成默认是 `controlled_user_replay`，同一条用户追问同时喂给 M0/M1/M2/M3。用户追问只能使用场景卡和既有用户发言中的事实，不能把 assistant 回复里的示例或假设转写成新的用户事实；如果场景卡没有明确给出幼儿园不稳定的具体原因，追问只能说“消息还很模糊/没有正式通知”。长跑时使用 `--all-message-ids --scene-followups 1 --print-mode summary --print-progress`，可以跑完整 30 天并打印逐 turn 进度。

定向测试问题由 `scripts/generate_probe_question_plan.py` 生成，输入是 `daily_scene_cards.json` 和 `data/config/probe_question_policy.json`，输出 `sample_output/probe_question_plan.json` 与 `sample_output/a_script_plan.json`。docx 路线还会运行 `scripts/annotate_bei.py` 补 `sample_output/bei_annotations.json`，再运行 `scripts/build_memory_conditions.py` 生成 `sample_output/memory_conditions.json`。运行四条件时加 `--probe-questions sample_output/probe_question_plan.json`，脚本会在每个开场消息的同日 follow-up 后插入对应 probe。

长时间对话脚本必须可恢复。`run_dialogue_conditions.py` 每完成一个用户 turn 就把当前 run 原子写入 `--output`，并按 `run_id` 同步 `conversation_log_docx_conditions.json`，不再依赖最后一次性写文件。如果进程中断，使用同一组参数加 `--resume`，脚本会从 `--output` 读取已完成 turns，重建 M0/M1/M2/M3 短期上下文，跳过已完成 message_id，从下一个未完成 turn 继续。恢复时不能更换 `message_ids`、`--scene-followups`、`--probe-questions`、`--conditions` 或 `--memory-conditions`。

正式长跑优先使用 supervisor：

```bash
PYTHONPATH=src .venv/bin/python scripts/10_supervise_full_experiment.py \
  --run-dir long_memory_experiment/outputs/run_YYYYMMDD_HHMM_full \
  --max-attempts 0 \
  --retry-sleep 30 \
  --scene-followups 1 \
  --judge-workers 4
```

后台启动：

```bash
PYTHONPATH=src .venv/bin/python scripts/11_start_full_experiment_background.py \
  --run-dir long_memory_experiment/outputs/run_YYYYMMDD_HHMM_full \
  --max-attempts 0 \
  --retry-sleep 30 \
  --scene-followups 1 \
  --judge-workers 4
```

后台脚本会写入 `background_supervisor.log`、`background_supervisor.pid.json` 和 `supervisor_status.json`。如果某一轮模型调用失败，supervisor 会用同一 run-dir 自动加 `--resume` 重试；已完成 turn 不会重跑，M0 LD-Agent memory runtime 优先从 `m0_ld_agent_memory` snapshot 恢复，缺失旧 snapshot 时才从已完成 turns 重建 short-term/long-term memory。

`09_run_full_experiment.py` 默认使用 `--condition-workers 4`，即同一 user turn 下的 M0/M1/M2/M3 四个回答并行生成。并行不会改变实验输入：每个 condition 的 `user_message`、短期上下文快照和 memory payload 都在提交任务前固定；M0 memory runtime 记录在四组回答都完成后执行。

DeepSeek provider 不做低额度人工截断。`deepseek-v4-*` 默认 `max_tokens` 使用官方最大输出上限 `384000`，让模型自行在任务完成时停止。日志中的 `llm.max_tokens` 必须记录实际请求上限，便于排查回答被截断、长请求等待和成本问题。

当前对话质量评估全面切换为 ToM-only 标准，位于 `scripts/evaluate_tom_quality.py` / `src/long_memory_test/evaluation/tom_quality_evaluator.py`。它只读取带 ToM probe 的 `conversation_log.json`，输出 `tom_quality_evaluation.json/md`，只评估隐含意图识别、情绪状态识别、关系期待识别、共同语境调用、陌生化错误率和自然细节调用。旧 `detail_hit_evaluator.py` 只作为历史 triage 工具保留，不再用于当前质量结论，也不和 ToM 分数融合。

## A 侧剧本与场景卡存储

为了让“一个月内同一窗口的自然对话”可复现，A 侧人物和事件必须分层保存，不能只散落在提示词里。

第一版存储约定：

- `data/config/persona.json`：用户基础画像，只放稳定事实。
- `data/config/life_domains.json`：生活领域和采样权重。
- `data/config/event_templates.json`：可采样事件模板，是 `timeline.json` 的事实源，同时保存每类事件的细节锚点。
- `data/config/user_actor.json`：模拟用户 A 的人物扮演配置，包括说话风格、压力反应、披露节奏、边界和 M1 稳定细节。
- `data/config/conversation_expansion_policy.json`：LLM 扩展同一天内后续用户发言时的规则，包括允许事实源、follow-up 预算、可用话术动作、禁止编造项和停止条件。
- `data/config/probe_question_policy.json`：ToM 定向测试问题策略，定义 probe 类型、ToM 维度、评测维度、称呼边界和禁止编造项。
- `sample_output/timeline.json`：30 天结构化生活事件。
- `sample_output/daily_user_message.json`：每天一条剧本开场用户消息。
- `sample_output/daily_scene_cards.json`：每天一张场景卡，合并开场消息、事件事实、隐含担心、可透露节奏、扩展控制和 memory audit 候选。
- `sample_output/probe_question_plan.json`：按场景卡插入的定向测试问题，每条带 probe 类型、ToM 指标、隐含需求和高低分表现。
- `sample_output/a_script_plan.json`：完整 A 侧剧本总表，包含每日开场、LLM follow-up slot 和 targeted probe。

`daily_scene_cards.json` 是后续 A-V0.3 接 DeepSeek 的主要输入。开场话题仍由剧本确定；同一天内是否继续聊、继续几轮、每轮能透露哪些事实，由场景卡控制。M0/M1/M2/M3 对照实验默认使用 `controlled_user_replay`：同一轮用户后续发言对所有记忆组保持一致，避免因为用户分支不同污染记忆效果比较。

细节记忆仍会作为后续单独 memory audit 的候选，但当前对话质量不按旧细节命中打分。当前约定：

- 人物背景卡 `user_actor.json` 保存稳定细节，主要作为 M1 的结论级关系记忆目标。
- 事件模板 `event_templates.json` 保存 `memory_detail_anchors`，用于生成 M2/M3 可比较的事件细节目标；生成后会带上 `should_be_remembered` 和 `detail_retention`，避免背景噪音被误写为长期细节。
- 场景卡 `daily_scene_cards.json` 聚合 `memory_detail_expectations`，包括稳定细节、事件细节、隐含担心和层级权限规则；它只作为后续 memory audit 候选。
- 对话日志中的 `evaluation_targets.tom_quality` 保存本轮 ToM 目标；普通场景卡不再自动写入旧 `detail_recall`，后续评分只检查 ToM 质量。

## 当前阶段

当前 A-V0.1、A-V0.2 和 A-V0.3 场景卡准备已完成第一版可运行原型：

- A-V0.1：`persona.json` + `life_domains.json` + `event_templates.json` -> `timeline.json`。
- A-V0.2：`timeline.json` -> 编剧式 `daily_user_message.json`。
- A-V0.3 数据准备：`timeline.json` + `daily_user_message.json` + `user_actor.json` + `conversation_expansion_policy.json` -> `daily_scene_cards.json`。
- A-V0.4 测试插入：`daily_scene_cards.json` + `probe_question_policy.json` -> `probe_question_plan.json` + `a_script_plan.json`。

当前开始搭建 B-V0.1：统一记忆 Agent 的规则版原型。

已跑通两条 A 侧小链路：

1. `persona.json` + `life_domains.json` + `event_templates.json` -> `generate_timeline.py` -> `timeline.json`。
2. `timeline.json` -> `generate_daily_user_messages.py` -> `daily_user_message.json`。
3. `timeline.json` + `daily_user_message.json` + `user_actor.json` + `conversation_expansion_policy.json` -> `generate_daily_scene_cards.py` -> `daily_scene_cards.json`。
4. `daily_scene_cards.json` + `probe_question_policy.json` -> `generate_probe_question_plan.py` -> `probe_question_plan.json` + `a_script_plan.json`。

docx 路线当前新增链路：

5. `probe_question_plan.json` + `timeline.json` -> `annotate_bei.py` -> `bei_annotations.json`。
6. `timeline.json` + `daily_user_message.json` + `probe_question_plan.json` + `bei_annotations.json` -> `build_memory_conditions.py` -> `memory_conditions.json`。
7. `daily_user_message.json` + `daily_scene_cards.json` + `probe_question_plan.json` + `memory_conditions.json` -> `run_dialogue_conditions.py` -> `m0_m1_m2_m3_dialogue_conditions.json`。
8. 同一次运行追加写入 `conversation_log_docx_conditions.json`，记录输入、input hash、M0/M1/M2/M3 memory payload、A 回复和模型参数。

当前阶段暂不实现复杂前端、多智能体系统或真实向量库。先保证 docx 路线中的 BEI 标注、记忆条件、四组运行和评测字段稳定、可复现、可扩展。

## 模型 API 配置

项目支持多个 OpenAI-compatible API 入口，供 A 和 B 共用。模型配置通过本地 `.env.local` 提供，不提交到 git。

推荐本地配置：

```bash
POIXE_API_KEY=your-poixe-api-key-here
POIXE_BASE_URL=https://api.poixe.com/v1
POIXE_MODEL=gpt-5.2

DEEPSEEK_API_KEY=your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro

LLM_PROVIDER=deepseek
```

共享模型客户端位于 `src/long_memory_test/llm.py`。A 后续做自然语言润色、B 后续做记忆判断时，都应从该模块读取统一配置，避免散落多个 API key 和 base URL。当前默认 `LLM_PROVIDER=deepseek`，也支持显式切换到 `poixe`。

LLM smoke test 位于 `scripts/poixe_smoke_test.py`，按当前 `LLM_PROVIDER` 验证本地 key、base URL 和模型名是否可用。文件名沿用早期 Poixe 配置阶段的历史名称。

Letta 相关代码只作为历史 pilot 保留：

- `src/long_memory_test/legacy/letta_memory_legacy.py`：旧 Letta 实现归档。
- `src/long_memory_test/letta_memory.py`：兼容 wrapper，避免旧 pilot 脚本立刻失效。
- `scripts/letta_memory_smoke.py`、`scripts/create_m0_letta_baseline.py`、`scripts/12_check_m0_letta_full_retrieval.py`：历史工具，不参与正式 M0/M1/M2/M3 实验。

最近已完成的 docx 路线基础改造：

- `scripts/annotate_bei.py` 已能从现有 probe 生成 `sample_output/bei_annotations.json`。
- `scripts/build_memory_conditions.py` 已能生成 `sample_output/memory_conditions.json`，其中 M0 是 LD-Agent memory-only generic baseline，M1/M2/M3 为叠加在同一 M0 底座上的累计关系记忆层级。
- `scripts/run_dialogue_conditions.py` 已能按同一用户输入运行 M0/M1/M2/M3，并为每轮记录 memory payload、input hash、模型参数和四组回答；M0 由 `LDAgentMemoryRuntime` 负责 LD-compatible short-term session、LLM session summary、persona traits、LD metadata snapshot 和 topic-overlap/time-decay retrieval。
- 旧 `scripts/run_m0_m1_dialogue_probe.py` 仅作为历史 pilot 工具保留。

## 核心数据流程

1. 生成或读取模拟用户画像。
2. 生成用户生活领域。
3. 基于事件模板生成生活事件。
4. 编排约 30 天模拟时间线。
5. 后续将事件流转换为每日用户提问。
6. B 按实验组别读取对应层级的记忆。
7. A 基于当前消息和可用记忆生成回复。
8. B 判断是否写入或更新 M1/M2/M3 记忆。
9. 下游再运行 Probe 并评估 M0/M1/M2/M3 的回收效果。

## 事件流设计原则

事件流应区分：

- 主线事件、支线事件、背景噪音。
- 是否需要后续追踪。
- 是否应该被记住。
- 是否关联前序事件。
- 情绪强度、决策影响、时间敏感度和当前状态。

`related_event_id` 是形成共同事件记忆的关键字段。有关联的新事件应更新同一条事件链，而不是创建一堆互不相关的孤立记忆。

## Timeline 并行事件约定

当前 P1 timeline 不再采用“一天只能发生一个事件”的旧假设。新的结构是：

- `active_session_count` 表示事件 occurrence / interaction session 总数；当前高密度 demo 固定为每人 88。
- `active_day_count` 表示 30 天中实际有事件发生的日历天数。
- 每个 active day 写入 `event_occurrences[]`，同一天可包含多条事件 occurrence。
- 当前配置 `max_events_per_active_day=5`，`parallel_event_days_min=20`，即每个 persona 至少有 20 个同日多事件日。
- 当前每日事件数固定分布为 `{0:2, 1:3, 2:5, 3:10, 4:5, 5:5}`，日历中位数为 3。
- active day 顶层仍保留第一条 occurrence 的字段作为兼容主事件；真实分析应优先读取 `event_occurrences[]`。
- 每条 occurrence 有自己的 `event_occurrence_id` 和 occurrence 级 `interaction_unit_id`，例如同一天可以有 `M001`、`M002`、`M003`、`M004`、`M005`。
- P2 probe 绑定到具体 occurrence 的 `interaction_unit_id`，不是只绑定到 day；同时保持每个 active day 最多 1 条 probe，避免 probe 在同一天过密。
- 为保证高密度 timeline 后仍有足够评测覆盖，P1 配置保留 `probe_candidate_min_per_persona=50` 的非初始候选 occurrence 下限。

当前 5 人样例已重新生成并通过校验：`active_session_total=440`，`active_day_total=140`，`parallel_event_day_total=125`，单日最多 5 条事件；P2 probe 共 127 条，每人 24-26 条。

## P3a Daily Interaction Units 约定

当前已从 P1/P2 timeline 推进到 `I` 维度，生成可审计的 daily interaction units。

核心产物：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json`
- `docs/p3_daily_interaction_demo5_report.html`
- `src/long_memory_test/sampling/daily_interaction_constructor.py`
- `scripts/run_p3_daily_interaction_construction.py`
- `scripts/generate_p3_daily_interaction_report_html.py`
- `tests/test_sampling_daily_interaction_constructor.py`

当前 P3a 不是 LLM 生成，而是确定性构造：

- `llm_generation_used=false`
- 一个 `event_occurrence_id` 对应一个 `interaction_unit_id`
- 同一 active day 若有多条 occurrence，则生成多个 I unit，共享 `day_group_id`
- `scripted_opening.user_message` 直接来自 timeline 的 `surface_event`
- `constrained_followup` 来自规则模板：阶段映射、允许动作、reveal steps、stop conditions、must-not-introduce
- `scene_boundary` 来自 `persona_ref`、event title、event summary、stage goal、allowed_new_facts 和 related_previous_days
- `probe_links` 从 occurrence 的 `probe_insertions[]` 复制并绑定，`read_only=true`
- 默认 `cross_occurrence_reference_allowed=false`，同日并行事件不会自动共享事实

当前 5 人样例已生成并通过校验：

- `persona_count=5`
- `calendar_day_count=150`
- `active_day_total=140`
- `interaction_unit_count=440`
- `parallel_day_total=125`
- `probe_link_count=127`

已执行验证：

```bash
python3 -m py_compile src/long_memory_test/sampling/daily_interaction_constructor.py scripts/run_p3_daily_interaction_construction.py scripts/generate_p3_daily_interaction_report_html.py tests/test_sampling_daily_interaction_constructor.py
PYTHONPATH=src python3 -m unittest tests.test_sampling_timeline_constructor tests.test_sampling_probe_constructor tests.test_sampling_realism_validator tests.test_sampling_daily_interaction_constructor
python3 scripts/run_p3_daily_interaction_construction.py
python3 scripts/generate_p3_daily_interaction_report_html.py
```

下一步应生成 `tau_contract.json`，把 `z,T,L,I,P` 固化成一份可运行、可评测、可审计的统一合同。

## 当前记录：2026-06-17 Demo5 tau / Timeline / I / Probe 整合报告

当前已把 5 人 demo 的核心生成链路整合到单一 HTML 报告：

- `docs/demo5_tau_i_probe_integrated_report.html`
- `scripts/generate_demo5_tau_i_probe_integrated_report_html.py`

报告整合输入：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json`

当前整体校验：

- Timeline validation：`pass`
- Probe validation：`pass`
- I validation：`pass`

当前 demo 统计：

- `persona_count=5`
- `calendar_day_count=150`
- `active_day_total=140`
- `interaction_unit_count=440`
- `probe_count=127`
- `parallel_event_day_total=125`
- 有 probe 的 I：`127`
- 无 probe 的 I：`313`

### 整合报告已展开的关键解释

第 3 节 `Timeline：T/L 的结构` 已从结果展示改为设计说明：

- 说明最高论文来源是 `docs/references/aaai2027_remem_re.pdf`，即 ReMem-RE 的 `tau=(z,T,L,I,P)` 受控长期互动轨迹框架。
- 明确正式版论文提供的是 `T=accepted event categories`、`L=recurring event lines`、长期关系期待形成/延迟/评测的研究口径。
- 明确 docx/config 提供的是第一阶段规模和验收约束；当前高密度配置为 5 人、30 天、每人 88 active sessions、每条 event line 6-14 次、每日事件数 median=3。
- 明确当前工程实现来自 `src/long_memory_test/sampling/timeline_constructor.py`：occurrence round、固定每日事件数打包、同日最多 5 条事件、并行事件日、固定随机种子等不是论文原生概念。

第 4 节 `I：Daily Interaction Units` 已严肃展开：

- `I` 被定义为“用户当天一次可执行互动的场景合同”，不是 agent 回复，也不是 probe。
- 每个 active `event_occurrence` 必须生成一个 I。
- `scripted_opening.user_message` 直接来自 timeline 的 `surface_event`。
- `constrained_followup` 定义 follow-up 预算、允许话术动作、reveal steps、stop conditions、must-not-introduce。
- `scene_boundary` 定义 allowed facts、latent concerns、memory level rules 和 audit dimensions。
- 当前 I 生成是确定性 constructor，`llm_generation_used=false`。

第 5 节 `Probe：生成逻辑与模板` 已严肃展开：

- Probe 明确不是 probability，而是 `targeted relational probe`。
- Probe 是插在某个 I 后面的只读评测 turn，用来测长期关系语境、状态变化、边界和自然细节。
- 当前中文 probe 模板来自 `src/long_memory_test/sampling/probe_constructor.py` 的确定性规则，不是 LLM prompt，也不是 docx/JSON/论文原文。
- 报告已列出 P1-P6、D1-D4、候选选择、类型判定、字段合同、required memory、校验与防污染。
- 当前 demo 覆盖 P2/P3/P5/P6；P1/P4 当前为 0 是本批样本和阶段映射导致的覆盖结果，不代表系统不支持。

### 当前边界判断

- `I` 不依赖 probe 生成；当前 440 个 I 中 313 个没有 probe。
- Probe 必须绑定到具体 `interaction_unit_id`，不是只绑定到日期。
- Probe 是 `read_only=true`，后续运行中不能写回记忆，避免评测题污染 memory。
- `cross_occurrence_reference_allowed=false`，同日并行事件默认不自动共享事实。
- 当前整合报告是解释和审计用 HTML；下一步仍应推进 `tau_contract.json`，把 `z,T,L,I,P` 固化成正式可运行合同。

## 当前记录：2026-06-17 Demo5 tau_contract 固化

当前已新增多人 sampling 版 tau 合同构造链路：

- `src/long_memory_test/sampling/tau_contract_constructor.py`
- `scripts/run_p4_tau_contract_construction.py`
- `tests/test_sampling_tau_contract_constructor.py`

已生成正式合同：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json`

合同 schema：

- `schema_version=tau_contract_batch_v0.1`
- `sampling_stage=P4_tau_contract_construction`
- `notation=tau=(z,T,L,I,P)`
- `llm_generation_used=false`

输入来源：

- `timeline.json`
- `daily_interaction_units.json`
- `probe_plan.json`
- `sampled_personas.json`
- `event_lines_batch.json`
- `accepted_persona_event_sets.json`

当前合同统计：

- `persona_count=5`
- `theme_count=44`
- `event_line_count=44`
- `interaction_unit_count=440`
- `targeted_probe_count=127`
- `message_binding_count=567`
- `probed_interaction_unit_count=127`
- `unprobed_interaction_unit_count=313`
- `validation.status=pass`

当前合同含义：

- `z[]`：从 sampled personas/persona_ref 固化 5 个具体人物。
- `T[]`：从 accepted event 和 timeline occurrence 固化每个人的长期事件主题。
- `L[]`：从 event_lines_batch 和 timeline occurrence 固化每条 recurring event line、观察到的 stage sequence、I 绑定和 probe 绑定。
- `I[]`：从 daily_interaction_units 固化每个 active occurrence 的互动单元、开场、follow-up 约束和 scene boundary。
- `P[]`：从 probe_plan 固化 targeted relational probe，明确 `read_only=true` 和 `writeback_policy=probe_turn_must_not_write_to_memory`。
- `message_bindings`：为 440 个 I 和 127 个 P 建立统一 tau 坐标，后续 runner/memory/evaluator 应以此作为定位接口。

已执行验证：

```bash
python3 -m py_compile src/long_memory_test/sampling/tau_contract_constructor.py scripts/run_p4_tau_contract_construction.py tests/test_sampling_tau_contract_constructor.py
PYTHONPATH=src python3 -m unittest tests.test_sampling_tau_contract_constructor
PYTHONPATH=src python3 -m unittest tests.test_sampling_timeline_constructor tests.test_sampling_probe_constructor tests.test_sampling_daily_interaction_constructor tests.test_sampling_realism_validator tests.test_sampling_tau_contract_constructor
python3 scripts/run_p4_tau_contract_construction.py
```

下一步可以开始把 `tau_contract.json` 接入 memory condition 构造，确保 M0/M1/M2/M3 都读取同一套 `z/T/L/I/P` 坐标，而不是各自解释 timeline/probe。

## 当前记录：2026-06-17 正式版论文同步修正

用户提供正式版论文：

- `docs/references/aaai2027_remem_re.pdf`

该文件已替代此前 `/Users/tom/Desktop/aaai2027.pdf`，作为当前项目最高论文依据；workspace 拷贝来自原始微信文件 `/Users/tom/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/sun414776205_04e4/msg/file/2026-06/aaai2027(1).pdf`。

正式版关键差异已同步：

- `T` 正式定义为 `accepted event categories`。
- Probe 编号调整为：
  - `P1 Current Understanding`
  - `P2 State Transformation`
  - `P3 Memory Invocation`
  - `P4 Natural Detail Use`
  - `P5 Relational Boundary`
  - `P6 Alienation Avoidance`
- M0-M3 名称按正式版更新：
  - `M0 Session-summary long-term memory baseline`
  - `M1 Event-conclusion relational memory`
  - `M2 Event-summary relational memory`
  - `M3 Event-detail relational memory`

已修改：

- `src/long_memory_test/sampling/probe_constructor.py`
- `tests/test_sampling_probe_constructor.py`
- `scripts/generate_demo5_tau_i_probe_integrated_report_html.py`
- `scripts/generate_p1_timeline_report_html.py`
- `scripts/generate_p3_daily_interaction_report_html.py`
- `scripts/generate_tau_concept_report_html.py`

已重新生成：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json`
- `docs/demo5_tau_i_probe_integrated_report.html`
- `docs/p1_timeline_demo5_report.html`
- `docs/p3_daily_interaction_demo5_report.html`
- `docs/tau_timeline_concept_report.html`

当前 5 人 demo 已改为 D-first probe 生成。`P` 仍是 `tau=(z,T,L,I,P)` 里的 probe 集合，`P1-P6` 只作为派生题型标签；生成主轴是 `D1-D4 primary_dimension_id`。

当前 D1-D4 primary 覆盖：

- `D1 Situated Intent Understanding`：31
- `D2 Emotional-State Attunement`：32
- `D3 Contextual Specificity`：32
- `D4 Continuity-Sensitive Response`：32

当前 5 人 demo 派生 P 分布：

- `P1 Current Understanding`：26
- `P2 State Transformation`：24
- `P3 Memory Invocation`：18
- `P4 Natural Detail Use`：32
- `P5 Relational Boundary`：12
- `P6 Alienation Avoidance`：15

注意：当前不再追求 P1-P6 均匀，P 分布只是 D-first 生成后的题型结果。

已执行验证：

```bash
python3 -m py_compile src/long_memory_test/sampling/probe_constructor.py scripts/generate_demo5_tau_i_probe_integrated_report_html.py scripts/generate_p1_timeline_report_html.py scripts/generate_p3_daily_interaction_report_html.py scripts/generate_tau_concept_report_html.py tests/test_sampling_probe_constructor.py
python3 scripts/run_p2_probe_insertion.py
python3 scripts/run_p3_daily_interaction_construction.py
python3 scripts/run_p4_tau_contract_construction.py
python3 scripts/generate_demo5_tau_i_probe_integrated_report_html.py
python3 scripts/generate_p1_timeline_report_html.py
python3 scripts/generate_p3_daily_interaction_report_html.py
python3 scripts/generate_tau_concept_report_html.py
PYTHONPATH=src python3 -m unittest tests.test_sampling_timeline_constructor tests.test_sampling_probe_constructor tests.test_sampling_daily_interaction_constructor tests.test_sampling_realism_validator tests.test_sampling_tau_contract_constructor
```

## 下游评测方向

后续评测会围绕三张核心表展开：

- `timeline_event_table`：展示模拟时间线中发生了什么。
- `memory_expectation_table`：定义 M0/M1/M2/M3 对每个事件应该知道什么、不应该知道什么。
- `tom_evaluation_table`：对比四类 Agent 对 ToM probe 的回答质量。

当前质量评分维度只包括隐含意图识别、情绪状态识别、关系期待识别、共同语境调用、陌生化错误率和自然细节调用。

如果后续需要评估记忆事实准确性，应单独做 memory audit；不要把事实召回、层级合规和 ToM 质量分数混成一个综合分。

## 工程协作约定

- 优先保持实现简单、可读、可复现。
- 先搭建数据结构和离线生成流程，再接入 Agent 运行与评测。
- 对实验条件要保持可控，避免不同记忆层级之间发生数据污染。
- 文档、数据 schema、生成脚本和评测逻辑要能互相解释。
- 新增代码前先确认当前阶段目标，避免过早引入复杂框架。

## 当前记录：2026-06-17 L/timeline 高密度改正

本轮用户指出：当前 `L` 的日历排布过稀疏，真实生活中不应“一天只有一个事件”，期望每天发生事件数量为 `0-5` 个，且日历中位数为 `3`。

已确认概念：

- `event occurrence` 是某条 recurring event line `L` 在某个日历日具体发生的一次实例。
- `active session` 在当前实现中等同于 occurrence / I unit 数，不等同于日历天。
- 一天可以包含多个 occurrence；每个 occurrence 后续生成一个独立 `I`。

改正方案：

- 每人 30 天固定日历分布：
  - `0` 个事件：2 天
  - `1` 个事件：3 天
  - `2` 个事件：5 天
  - `3` 个事件：10 天
  - `4` 个事件：5 天
  - `5` 个事件：5 天
- 因此每人 occurrence 总数固定为 `88`，日历事件数中位数为 `3`。
- `events_per_persona` 从 `4-6` 调整为 `8-10`，避免少量事件线被过度重复。
- `event_line_occurrences` 调整为 `6-14`，支撑每人 88 个 occurrence。
- `max_events_per_active_day` 调整为 `5`。
- `parallel_event_days_min` 调整为 `20`。
- `allow_stage_reuse_after_sequence=true`，当 occurrence 超过原始 `stage_sequence` 长度时，按 recurrence / turning_point / partial_resolution / reflection 生成扩展阶段，仍保持 stage index 单调递增。

已修改：

- `long_memory_experiment/data/sampling/sampling_config.json`
- `src/long_memory_test/sampling/timeline_constructor.py`
- `scripts/run_p1_timeline_construction.py`
- `src/long_memory_test/sampling/persona_event_sampler.py`
- `tests/test_sampling_timeline_constructor.py`
- `scripts/generate_demo5_tau_i_probe_integrated_report_html.py`
- `scripts/generate_p1_timeline_report_html.py`
- `scripts/generate_tau_concept_report_html.py`

已重新生成：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/sampled_personas.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/accepted_persona_event_sets.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/event_lines_batch.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json`
- `docs/demo5_tau_i_probe_integrated_report.html`
- `docs/p1_timeline_demo5_report.html`
- `docs/p3_daily_interaction_demo5_report.html`
- `docs/tau_timeline_concept_report.html`

当前结果：

- P0 sampling：`pass`，5 人，44 条 accepted events / event lines。
- Timeline：`pass`，5 人总 occurrence `440`，即每人 `88`。
- 每人每日分布均为 `{0:2, 1:3, 2:5, 3:10, 4:5, 5:5}`。
- 每人日历事件数 median 均为 `3.0`。
- 单日最大事件数为 `5`。
- 每人 parallel event days 为 `25`。
- P3 daily interaction：`pass`，`440` 个 I units，`125` 个 parallel days，`127` 个 probe links。
- P2 probe：`pass`，`127` 条 probes，每人 `24-26` 条；主 D 覆盖为 `D1=31, D2=32, D3=32, D4=32`。
- P4 tau contract：`pass`。

## 当前记录：2026-06-17 D-first Probe 生成修正

用户确认：probe 生成逻辑应以论文 D 维度为主轴，而不是先生成 P1-P6 再附带 D。当前已完成修正：

- `P` 保留为 tau 组件，表示 targeted probe 集合。
- 每条 probe 新增 `primary_dimension_id`、`primary_dimension`、`secondary_dimension_ids`。
- 生成过程先选 timeline occurrence，再按 persona 内部轮转分配 `D1/D2/D3/D4`。
- `P1-P6` 从 primary D 和 occurrence 阶段派生，只作为题型标签。
- 校验要求每个 persona 的 primary D 覆盖差值不超过 1。
- `daily_interaction_units.json` 和 `tau_contract.json` 都已透传 primary/secondary D 字段。

当前全局 primary D 分布：

- `D1=31`
- `D2=32`
- `D3=32`
- `D4=32`

当前按 persona 分布：

- `P0001`: `D1=7, D2=7, D3=6, D4=6`
- `P0002`: `D1=6, D2=7, D3=7, D4=6`
- `P0003`: `D1=6, D2=6, D3=7, D4=7`
- `P0004`: `D1=6, D2=6, D3=6, D4=7`
- `P0005`: `D1=6, D2=6, D3=6, D4=6`

当前派生 P 分布：

- `P1=26`
- `P2=24`
- `P3=18`
- `P4=32`
- `P5=12`
- `P6=15`

已修改：

- `src/long_memory_test/sampling/probe_constructor.py`
- `src/long_memory_test/sampling/daily_interaction_constructor.py`
- `src/long_memory_test/sampling/tau_contract_constructor.py`
- `tests/test_sampling_probe_constructor.py`
- `scripts/generate_demo5_tau_i_probe_integrated_report_html.py`
- `scripts/generate_p1_timeline_report_html.py`
- `scripts/generate_tau_concept_report_html.py`

已重新生成：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json`
- `docs/demo5_tau_i_probe_integrated_report.html`
- `docs/p1_timeline_demo5_report.html`
- `docs/p3_daily_interaction_demo5_report.html`
- `docs/tau_timeline_concept_report.html`

已执行验证：

```bash
python3 scripts/run_p2_probe_insertion.py
python3 scripts/run_p3_daily_interaction_construction.py
python3 scripts/run_p4_tau_contract_construction.py
python3 scripts/generate_demo5_tau_i_probe_integrated_report_html.py
python3 scripts/generate_p1_timeline_report_html.py
python3 scripts/generate_tau_concept_report_html.py
PYTHONPATH=src python3 -m unittest tests.test_sampling_timeline_constructor tests.test_sampling_probe_constructor tests.test_sampling_daily_interaction_constructor tests.test_sampling_realism_validator tests.test_sampling_tau_contract_constructor
```

已执行验证：

```bash
python3 -m py_compile src/long_memory_test/sampling/persona_event_sampler.py src/long_memory_test/sampling/timeline_constructor.py scripts/run_p0_persona_event_sampling.py scripts/run_p1_timeline_construction.py tests/test_sampling_timeline_constructor.py
PYTHONPATH=src python3 -m unittest tests.test_sampling_timeline_constructor
python3 scripts/run_p0_persona_event_sampling.py
python3 scripts/run_p1_event_line_batch_construction.py
python3 scripts/run_p1_timeline_construction.py
python3 scripts/run_p2_probe_insertion.py
python3 scripts/run_p3_daily_interaction_construction.py
python3 scripts/run_p4_tau_contract_construction.py
python3 scripts/generate_demo5_tau_i_probe_integrated_report_html.py
python3 scripts/generate_p1_timeline_report_html.py
python3 scripts/generate_p3_daily_interaction_report_html.py
python3 scripts/generate_tau_concept_report_html.py
PYTHONPATH=src python3 -m unittest tests.test_sampling_timeline_constructor tests.test_sampling_probe_constructor tests.test_sampling_daily_interaction_constructor tests.test_sampling_realism_validator tests.test_sampling_tau_contract_constructor
```

后续注意：

- 高密度模式显著增加 I 数量，后续 M0-M3 运行成本会从原来的 98 I 增加到 440 I。
- 当前扩展 stage 是规则生成，不调用 LLM；如后续需要更自然的多轮故事文本，应在不突破 `allowed_new_facts` 和 `prohibited_facts` 的前提下做受控改写。
- Probe 数量已随候选增长调整为每人 `24-36` 配置范围，当前实际为 `24-26`。

## 当前记录：2026-06-19 M0/M1/M2/M3 payload 结构修正

本轮按正式论文口径修正 M 条件的 payload 组合方式。关键结论：

- `M0` 仍是普通 LD-Agent memory-only / session-summary 长期记忆基线。
- `M1/M2/M3` 的关系记忆 runtime 仍然保持各自独立 namespace，防止条件间写回污染。
- 但最终喂给 responder 的 `memory_payload` 不再是纯 isolated relational payload，而是：
  - `M1 = 同轮 M0 retrieved base + M1 conclusion-level relational overlay`
  - `M2 = 同轮 M0 retrieved base + M1 conclusion-level + M2 event-summary overlay`
  - `M3 = 同轮 M0 retrieved base + M1 conclusion-level + M2 event-summary + M3 detail-anchor overlay`
- M1/M2/M3 共享的是同一轮 `M0` 普通记忆检索结果，不共享彼此的回答，也不读取其他关系条件的 runtime namespace。
- probe turn 仍然只读，不写回关系记忆或 M0 普通记忆。

已修改：

- `src/long_memory_test/agents/memory_condition_builder.py`
  - 条件声明从 `condition_isolated_*` 改为 `shared_m0_ld_agent_retrieved_payload + own_condition_*_memory`。
  - M1/M2/M3 静态 payload 元数据改为 `memory_provider = m0_base_plus_relational_overlay`。
  - M1/M2/M3 均标记 `requires_runtime_ld_agent_memory = true`。
- `scripts/run_dialogue_conditions.py`
  - 新增 `_compose_relational_payload_with_m0_base(...)`。
  - runtime 路径和 fallback 静态路径都会把关系 overlay 与同轮 M0 payload 合成。
  - 最终 payload 写入 `m0_base_memory`、`relational_overlay`、`memory_composition`、`search_indexing_policy` 和合成后的 `retrieval`。
  - run config 中 `m1_m2_m3_share_m0_payload` 改为 `true`，同时记录 `m1_m2_m3_answer_writeback_isolated = true`。
- `src/long_memory_test/memory/relational_runtime.py`
  - 语义改为 relational overlay runtime。
  - runtime 本身不读 M0，也不读其他 M 条件；runner 负责把 overlay 与 M0 base 合成。
- `tests/test_docx_route_pipeline.py`
  - 断言 M1/M2/M3 最终 payload 必须包含 M0 base。
  - 断言关系 runtime 路径仍保持 overlay provider 和 writeback 隔离。
- `tests/test_relational_memory_runtime.py`
  - 断言 relational runtime 只产生 overlay，并声明最终由 runner 合成 M0。

已刷新：

- `long_memory_experiment/cache/memory_conditions_combined.json`
- `long_memory_experiment/data/memory_conditions/m1_conclusion_memory.json`
- `long_memory_experiment/data/memory_conditions/m2_event_memory.json`
- `long_memory_experiment/data/memory_conditions/m3_relational_anchor_memory.json`
- `long_memory_experiment/data/memory_conditions/mva_summary_memory.json`

已验证：

```bash
PYTHONPATH=src .venv/bin/python -m py_compile src/long_memory_test/agents/memory_condition_builder.py src/long_memory_test/memory/relational_runtime.py scripts/run_dialogue_conditions.py tests/test_docx_route_pipeline.py tests/test_relational_memory_runtime.py
PYTHONPATH=src .venv/bin/python -m unittest tests.test_docx_route_pipeline tests.test_relational_memory_runtime tests.test_ld_agent_memory_runtime
PYTHONPATH=src .venv/bin/python scripts/build_memory_conditions.py
```

当前限制：

- 现有 `scripts/build_memory_conditions.py` 仍接 `long_memory_experiment/data/script/*` 旧路线，所以刷新后的 `memory_conditions_combined.json` 仍是 66 条 message payload。
- 最新 5 人高密度 demo 的 `tau_contract.json` 有 567 条 message binding；要让 M0/M1/M2/M3 正式跑最新高密度 demo，还需要新增或改造一个从 `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json` / `daily_interaction_units.json` 生成 memory condition payload 的适配层。

## 当前记录：2026-06-19 tau 到 M0/M1/M2/M3 接口打通与 P3b 自然化候选层

本轮按“不要生成，只打通接口”的要求完成两件事：

- 新增 tau route：把最新 `tau=(z,T,L,I,P)` contract 直接适配成 M0/M1/M2/M3 memory condition payload。
- 新增 P3b interaction naturalization：允许 LLM 基于已有 `I unit` 生成自然用户话术候选，但 `I unit` 继续保留为唯一结构真值，不被覆盖。

关键约束：

- 不从 tau 一步生成自然语言任务。
- 不改写 `scripted_opening`。
- LLM 只接收 `I unit` 的 canonical opening、stage、scene boundary、allowed facts、reveal steps、stop conditions，并输出独立候选 JSON。
- P3b 候选可以被 adapter 选用为 runner 输入的 `user_message`，但必须保留 `canonical_user_message` 和 `source_tau`，方便回溯。
- M1/M2/M3 仍遵循“同轮 M0 retrieved base + condition-specific relational overlay”的最终 payload 组合原则。

已新增：

- `src/long_memory_test/agents/tau_dialogue_adapter.py`
  - `build_tau_dialogue_documents(...)` 将 `tau_contract.I` 转为 runner `messages`，将 `tau_contract.P` 转为 `probe_questions`。
  - 支持把 P3b naturalized candidate 接入 runner message，但保留 canonical I unit。
  - 生成 `probe_questions_by_insert_after`，明确 probe 与 I unit 的绑定关系。
- `src/long_memory_test/sampling/interaction_naturalizer.py`
  - `build_naturalization_prompt(...)` 构建 LLM 自然化提示词。
  - `naturalize_interaction_unit(...)` 调用 LLM，只输出候选自然话术。
  - `validate_naturalized_dialogue(...)` 校验 fact ids、followup 数量、source id 和是否真正自然化。
  - `attach_naturalized_dialogues(...)` 只附加候选，不覆盖 I unit。
- `scripts/build_tau_memory_conditions.py`
  - 从 `tau_contract.json` 构建 `memory_conditions_v0.2_tau_route`。
  - 本轮没有执行该脚本，避免生成新数据。
- `scripts/run_p3b_interaction_naturalization.py`
  - 从 `daily_interaction_units.json` 调 LLM 生成 P3b 候选。
  - 本轮没有执行该脚本，避免生成自然语言数据。
- `tests/test_tau_memory_interface.py`
  - 覆盖 tau route M0-M3 payload。
  - 覆盖 tau dialogue adapter 保留 canonical I unit。
  - 覆盖 P3b candidate 不覆盖 I unit。
  - 覆盖越界 fact id 被拒绝。

已修改：

- `src/long_memory_test/agents/memory_condition_builder.py`
  - 新增 `generate_memory_conditions_from_tau_contract(...)`。
  - 从 `L` 读取 M1/M2 关系记忆和事件摘要来源。
  - 从 `I.scene_boundary` 读取 M3 可用事实、隐含担心和禁止事实。
  - 从 `P.target_detail_ids` 补充 probe 目标细节。
- `scripts/run_dialogue_conditions.py`
  - `_load_memory_conditions(...)` 支持 `memory_conditions_v0.2_tau_route`。

已验证：

```bash
PYTHONPATH=src .venv/bin/python -m py_compile src/long_memory_test/agents/memory_condition_builder.py src/long_memory_test/agents/tau_dialogue_adapter.py src/long_memory_test/sampling/interaction_naturalizer.py scripts/run_dialogue_conditions.py scripts/build_tau_memory_conditions.py scripts/run_p3b_interaction_naturalization.py tests/test_tau_memory_interface.py
PYTHONPATH=src .venv/bin/python -m unittest tests.test_tau_memory_interface tests.test_docx_route_pipeline tests.test_relational_memory_runtime tests.test_ld_agent_memory_runtime tests.test_experiment_cache
```

当前状态：

- 代码接口已经打通。
- 没有运行 `build_tau_memory_conditions.py`。
- 没有运行 `run_p3b_interaction_naturalization.py`。
- 因此没有新生成正式 payload、自然对话或实验输出。

## 当前记录：2026-06-23 生成产物中文描述统一

本轮按“无论是 L、E 还是其他描述，统一使用中文”的要求完成生成链中文化。

处理原则：

- `event_category_id`、`event_line_id`、`interaction_unit_id`、`M0/M1/M2/M3`、`schema_version` 等接口 ID 保持不变。
- 人类可读描述统一中文，包括人物 label、职业、家庭结构、生活领域、事件 title/core_issue、stage label、allowed facts、latent concerns、memory risks、construction notes、tau definition。
- P0 内部 realism/compatibility 校验仍使用原始受控池值；落盘的 `sampled_personas.json` 输出中文描述，避免影响校验逻辑。

已新增/修改：

- 新增 `src/long_memory_test/sampling/zh_localization.py`，集中管理事件类别、人物原型、领域、阶段、风险短语和当前 demo persona 值的中文映射。
- 修改 `src/long_memory_test/sampling/persona_event_sampler.py`：
  - candidate/accepted event 输出使用中文 `title/core_issue`。
  - 移除英文 `source_title/source_core_issue`。
  - `sampled_personas.json` 落盘字段中文化，但 P0 校验仍吃内部 raw sampled personas。
- 修改 `src/long_memory_test/sampling/event_line_constructor.py`：
  - `persona_ref`、`source_event_category`、`source_stage_label`、`construction_notes`、`prohibited_facts`、`relational_memory_targets` 中文化。
  - 补齐 `memory_risks` 中文映射，避免 `待中文化描述` 进入 L。
- 修改 `src/long_memory_test/sampling/daily_interaction_constructor.py`：
  - `scene_boundary.allowed_facts[].text` 和 `latent_concerns[].text` 中文化。
  - 前序日期文本从 `D01` 改成 `第 1 天`。
  - follow-up/assistant/timeline 等说明改为中文表达。
- 修改 `src/long_memory_test/sampling/tau_contract_constructor.py`：
  - `tau.definition` 中文化。
  - `z.stable_profile`、长期目标、沟通风格、压力反应、决策风格、记忆相关特质中文化。

已重新生成：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/sampled_personas.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/candidate_event_sets.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/accepted_persona_event_sets.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/event_lines_batch.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json`
- `docs/p0_persona_event_sampling_demo5_report.html`
- `docs/l_event_line_generation_report.html`
- `docs/p1_timeline_demo5_report.html`
- `docs/p3_daily_interaction_demo5_report.html`
- `docs/demo5_tau_i_probe_integrated_report.html`

已验证：

```bash
PYTHONPATH=src .venv/bin/python -m py_compile src/long_memory_test/sampling/zh_localization.py src/long_memory_test/sampling/persona_event_sampler.py src/long_memory_test/sampling/event_line_constructor.py src/long_memory_test/sampling/daily_interaction_constructor.py src/long_memory_test/sampling/tau_contract_constructor.py
PYTHONPATH=src .venv/bin/python -m unittest tests.test_sampling_realism_validator tests.test_sampling_timeline_constructor tests.test_sampling_tau_contract_constructor tests.test_sampling_daily_interaction_constructor tests.test_sampling_probe_constructor tests.test_tau_memory_interface
PYTHONPATH=src .venv/bin/python scripts/run_p0_persona_event_sampling.py
PYTHONPATH=src .venv/bin/python scripts/run_p1_event_line_batch_construction.py
PYTHONPATH=src .venv/bin/python scripts/run_p1_timeline_construction.py
PYTHONPATH=src .venv/bin/python scripts/run_p2_probe_insertion.py
PYTHONPATH=src .venv/bin/python scripts/run_p3_daily_interaction_construction.py
PYTHONPATH=src .venv/bin/python scripts/run_p4_tau_contract_construction.py
```

最终可读字段检查：

- `sampled_personas.json`：0 个英文描述残留
- `candidate_event_sets.json`：0 个英文描述残留
- `accepted_persona_event_sets.json`：0 个英文描述残留
- `event_lines_batch.json`：0 个英文描述残留
- `timeline.json`：0 个英文描述残留
- `probe_plan.json`：0 个英文描述残留
- `daily_interaction_units.json`：0 个英文描述残留
- `tau_contract.json`：0 个英文描述残留
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5` 与本轮刷新 HTML 中没有 `待中文化描述` 占位符。

## 当前记录：2026-06-26 P3B follow-up 结合 Probe 与逐题 ground truth

本轮按“有天数的 follow-up 相关问题需要结合 Probe；主问题/opening 不结合 Probe；每个对话每个 P 需要 ground truth”的要求完成一版链路固化。

设计约束：

- P3B 的 `opening_user_message` 只根据 I unit 的 canonical opening、timeline occurrence 和 scene boundary 自然化，不读取 Probe 题面，也不能复制 Probe 问题。
- P3B 的 `followup_user_messages` 可以读取绑定 Probe 的评测目标、维度和 ground truth，用于把追问自然地靠近测评点。
- Probe 仍是正式评测题，插在同一个 `interaction_unit_id` 后面；P3B follow-up 不能原样复制正式 Probe 问题。
- 每个 P 的 `ground_truth` 不由 LLM 生成，而是从 timeline occurrence、event line、stage、stage_delta_facts、allowed facts、related previous days 确定性派生。

已修改：

- `src/long_memory_test/sampling/probe_constructor.py`
  - 为每个 `probe_question` 增加 `ground_truth`。
  - ground truth 包含 `must_recognize`、`must_use_or_respect`、`expected_references`、`acceptable_response`、`failure_modes`、`must_not_claim`、`scoring_rubric`。
- `src/long_memory_test/sampling/tau_contract_constructor.py`
  - 将 Probe 的 `ground_truth` 透传到 tau contract 的 `P` 维度。
- `src/long_memory_test/sampling/interaction_naturalizer.py`
  - P3B prompt 增加 `bound_probe_followup_guidance`。
  - 明确 Probe guidance 只能用于 `followup_user_messages`，不能影响 opening。
  - 输出 `bound_probe_ids`、`bound_probe_refs`、`probe_aware_followup_policy`。
  - 增加校验：如果 opening 或 follow-up 原样复制正式 Probe 问题，则判失败。
- `scripts/run_p3b_interaction_naturalization.py`
  - 增加 `--probe-plan`、`--no-probe-plan`、`--force-probed`、`--only-probed`。
  - 支持在 `--resume` 下只重跑带 Probe 的 interaction units，复用无 Probe 的历史自然化结果。
- `scripts/generate_demo5_persona_daily_timeline_html.py`
  - 在按天明细中展示 P3B 发问、Probe 测评题和每题 ground truth。

本轮重新生成：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_naturalized_candidates_deepseek_all440.json`
- `docs/demo5_persona_daily_timeline_detail.html`

已执行验证：

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_sampling_probe_constructor tests.test_sampling_tau_contract_constructor tests.test_tau_memory_interface tests.test_sampling_daily_interaction_constructor
PYTHONPATH=src .venv/bin/python scripts/run_p2_probe_insertion.py
PYTHONPATH=src .venv/bin/python scripts/run_p3_daily_interaction_construction.py
PYTHONPATH=src .venv/bin/python scripts/run_p4_tau_contract_construction.py
.venv/bin/python scripts/run_p3b_interaction_naturalization.py --provider deepseek --all --workers 4 --timeout 240 --max-tokens 4000 --checkpoint-every 5 --resume --retry-failed --force-probed --probe-plan long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json --output long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_naturalized_candidates_deepseek_all440.json
python3 scripts/generate_demo5_persona_daily_timeline_html.py
```

当前计数：

- `probe_questions`：127
- `probe_ground_truth`：127
- `naturalized_dialogues`：440
- `p3b_bound_probe_dialogues`：127
- `p3b_policy_dialogues`：127
- `tau.P`：127
- `tau.P.ground_truth`：127
- P3B DeepSeek 全量结果：440 pass / 0 fail；其中 313 条无 Probe 的结果复用，127 条带 Probe 的结果重跑。

## 当前记录：2026-06-27 ground truth 增加参考答案

本轮确认 `ground_truth` 不应只是评分标准，还应包含一个符合标准的可参考准确回答。

处理原则：

- `ground_truth` 保留原有评分契约字段：`must_recognize`、`must_use_or_respect`、`expected_references`、`acceptable_response`、`failure_modes`、`must_not_claim`、`scoring_rubric`。
- 新增 `reference_answer_zh`，作为人工评审或后续 LLM judge 的高分答案参考。
- 新增 `reference_answer_usage`，明确参考答案不要求逐字匹配；被评测回答只需要覆盖核心事件线、阶段变化、前序承接和禁止编造边界。
- 参考答案仍是确定性生成，不由 LLM 生成；来源包括 event title、event_stage、stage_delta_facts、allowed_base_facts、persona_conditioned_facts、assistant_memory_expectation 和 related_previous_days。

已修改：

- `src/long_memory_test/sampling/probe_constructor.py`
  - `ground_truth` 增加 `reference_answer_zh` 与 `reference_answer_usage`。
  - 新增 `_reference_answer_zh`、`_stage_reference_sentence`、`_reference_fact_basis`、`_clean_sentence`。
- `scripts/generate_demo5_persona_daily_timeline_html.py`
  - 在 Ground truth 表格中展示 `reference_answer_zh` 与 `reference_answer_usage`。
- `tests/test_sampling_probe_constructor.py`
  - 校验 Probe ground truth 必须包含参考答案字段。
- `tests/test_sampling_tau_contract_constructor.py`
  - 校验 tau contract 的 `P.ground_truth` 透传参考答案字段。

已重新生成：

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/probe_plan.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/timeline.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/daily_interaction_units.json`
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json`
- `docs/demo5_persona_daily_timeline_detail.html`

已验证：

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_sampling_probe_constructor tests.test_sampling_tau_contract_constructor tests.test_tau_memory_interface tests.test_sampling_daily_interaction_constructor
python3 -m py_compile src/long_memory_test/sampling/probe_constructor.py scripts/generate_demo5_persona_daily_timeline_html.py
PYTHONPATH=src .venv/bin/python scripts/run_p2_probe_insertion.py
PYTHONPATH=src .venv/bin/python scripts/run_p3_daily_interaction_construction.py
PYTHONPATH=src .venv/bin/python scripts/run_p4_tau_contract_construction.py
python3 scripts/generate_demo5_persona_daily_timeline_html.py
```

当前计数：

- `probe_questions`：127
- `probe_reference_answers`：127
- `tau.P`：127
- `tau_reference_answers`：127

## 当前记录：2026-06-27 输出阶段完成标记

当前可以认为 5 人 demo 的输出准备阶段基本完成，后续准备进入下一轮实验执行与 M0/M1/M2/M3 对比评测。

当前已固化的前期产物：

- 人物与事件线：5 个 persona，44 条 L/event line。
- Timeline：30 天窗口，5 个 persona 共 150 个日历日；active days 140；interaction units 440。
- Probe/P：127 个 targeted probes；每个 Probe 均绑定具体 `interaction_unit_id`、`event_occurrence_id`、`event_line_id`。
- Ground truth：127 个 Probe 均包含评分契约字段和 `reference_answer_zh`。
- P3B：440 条自然化用户发问全部 pass；其中 127 条与 Probe 绑定，follow-up 可结合 Probe guidance，opening 不结合 Probe。
- Tau contract：`tau=(z,T,L,I,P)` 已打通，`P.ground_truth` 与 Probe plan 对齐。
- HTML：`docs/demo5_persona_daily_timeline_detail.html` 可作为当前审阅主入口，按 persona/day 展示 timeline、I、P3B、Probe、ground truth 和参考答案。

当前阶段结论：

- 数据生成链路 P0/P1/P2/P3/P3B/P4 在 5 人 demo 范围内已经可运行、可审阅、可复现。
- M0/M1/M2/M3 的前期输入准备基本完成。
- 下一轮重点应从“生成数据是否成立”转向“运行不同 memory condition 下的 agent 回答，并基于 Probe ground truth/reference answer 进行评测”。

下一轮建议优先级：

1. 定义 M0/M1/M2/M3 的实验输入 payload：每个 condition 接收相同 I/P/T/L/z 绑定，但 memory 可见范围不同。
2. 构建 Probe evaluator：读取 agent 回答、对应 `ground_truth`、`reference_answer_zh`、`failure_modes`，输出 0/1/2 分和扣分理由。
3. 跑 5 人 demo 的小规模端到端对比：先抽 10-20 个 Probe 验证评分稳定性，再扩到 127 个 Probe。

## 当前记录：2026-07-05 two-person M0-M3 current-event lock 里程碑

本轮结果作为当前 M0/M1/M2/M3 对照实验的里程碑版本。核心结论：在不改变 M0 baseline 的前提下，仅修正 M1/M2/M3 的关系层 prompt 组合和当前事件线锁定后，DeepSeek LLM-as-judge 结果呈现预期阶梯：`M0 < M1 < M2 < M3`。

本轮关键修正过程：

- 坚持 `M0` 是独立 baseline：M0 仍为 LD-Agent-compatible memory-only / session-day 级 generic long-term memory baseline，不增加 event-line filtering，不读取 relational overlay，不接收 M1/M2/M3 的 prompt/composition 提示。
- 修正 `M1/M2/M3` 的 prompt 优先级：system prompt 与 payload 均明确“关系层是当前 event-aware overlay / 主记忆，M0 只是普通 session/day 背景”；当 M0 背景与关系层对当前 probe 的解释冲突时，M1/M2/M3 以关系层解释当前用户输入。
- 增加 `current-event lock`：当前用户点名主题、事件线或“这条线”时，M1/M2/M3 只能围绕当前点名事件线回答；历史短期上下文和 M0 普通背景里的其他事件线不能抢占当前回答焦点。
- 报告中增加 M1/M2/M3 prompt reference：包含 system prompt template、relational payload template 和当前 run 的示例 prompt，便于审计关系层加载方式。
- DeepSeek 作为默认真实网络评测 API 使用；生成与评测均使用当前 DeepSeek 配置。

本轮生成 run：

- Run dir：`long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation`
- 输入：`P0001,P0002` 两人完整 30 天链路。
- 生成范围：`228/228` turns 完成，`M0/M1/M2/M3` 四条件均生成。
- Probe：`52` 个 targeted probe turns。
- LLM judge cases：`52 probes x 4 conditions = 208`，全部有效，`invalid_judge=0`。

DeepSeek LLM-as-judge 主结果：

| Condition | Average ToM score | Valid judge | Human review | Flags |
|---|---:|---:|---:|---:|
| `M0` | `60.02` | `52` | `17` | `52` |
| `M1` | `76.76` | `52` | `8` | `20` |
| `M2` | `79.97` | `52` | `4` | `10` |
| `M3` | `87.66` | `52` | `0` | `0` |

正式结论口径：

- 以 `llm_judge_scores_two_person.json` / `llm_judge_scores_two_person.md` 为主评测依据。
- `automatic_scores_two_person.json` 只作为 rule-based triage / 诊断层，不作为最终质量排序依据。
- 当前结果说明：普通 M0 generic memory 可以提供基础连续性，但在跨事件线、关系期待、状态变化和细节边界方面不足；M1/M2/M3 的累计关系记忆层级带来显著提升，其中 M3 细节锚点层当前表现最稳定。

当前报告入口：

- HTML：`docs/two_person_m0_m3_probe_evaluation_report.html`
- Markdown：`long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation/two_person_m0_m3_evaluation_report.md`
- LLM judge JSON：`long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation/llm_judge_scores_two_person.json`
- 规则诊断 JSON：`long_memory_experiment/outputs/run_20260704_two_person_m0_m3_current_event_lock_generation/automatic_scores_two_person.json`

旧的同类 report 产物可清理；不要删除旧 run 的原始 `responses_by_condition.json` / `conversation_log.json`，除非明确要释放磁盘空间并已确认不再需要复核。
