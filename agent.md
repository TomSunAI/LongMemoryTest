# LongMemoryTest Agent Notes

## 项目定位

本项目当前主线以《长期关系记忆实验 30 天脚本实现方案（细化版）M1 修正版》为准。后续实现不再走 `S0/S1/S2/S3` 非累积 overlay 路线，也不再把旧 `M0=no long-term memory` 当正式 baseline。

核心研究问题：

> 即使使用主流 agent 框架自带的普通长短期记忆，如果没有针对长期陪伴/关系连续性的记忆写入体系，agent 是否仍会无法稳定完成 ToM-like interaction？

因此，正式实验不是“无记忆 vs 有记忆”，而是：

> `M0 generic agent memory baseline` vs `M1/M2/M3 关系性记忆写入层级`。

本项目要证明的是：长期陪伴型 conversational agent 需要记住什么、记到什么层级，才能在跨天互动中维持熟悉感、正确识别隐含意图，并避免陌生化、机械复述和编造式亲密。

## 当前记忆实验条件

正式条件分成一个独立 baseline 和一条累计关系记忆线：

- `M0`：Generic Agent Memory Baseline。主流 agent 框架自带普通长短期记忆强基线，不读人工设计的关系记忆、BEI、事件轨迹或关系锚点。
- `M1`：Conclusion-level Relational Memory。只读结论级关系记忆，保存稳定偏好、回应风格、关系期待、关键判断和不要做什么；不叠加 M0 Letta 默认记忆。
- `M2`：Summary-level Relational Memory。M1 + 摘要级记忆，保存关键事件线、跨天主题进展、用户状态变化和处理结果摘要。
- `M3`：Detail-level / Relational Anchor Memory。M2 + 必要细节、具体场景、共同语言、关系锚点、回应边界和误用风险。

主实验采用关系记忆累计条件：`M2` 包含 `M1`，`M3` 包含 `M1 + M2`。`M0` 不参与这个累计链，只作为 Letta generic memory 的独立强基线。这样实验问题是“关系记忆写入层级逐步加深是否提升长期陪伴 ToM-like 表现”，同时用 `M0` 单独检验通用 agent memory 是否已经足够。

### 当前 M0 Letta 实现边界

当前实现中，`M0` 必须调用 Letta 默认 memory，不能再用手工构造的 generic 摘要模拟。只有运行 `M0` 条件时才需要提供 `--m0-letta-agent-id` 或环境变量 `LETTA_M0_AGENT_ID`；如果只跑 `M1/M2/M3`，不需要 Letta agent id。

M0 的职责是提供 Letta 自带的普通 agent memory baseline，包括 Letta runtime 可返回的 core memory、普通用户画像、普通历史检索或普通摘要。M0 不能读取本实验人工整理的 `timeline.json`、`bei_annotations.json`、事件轨迹、关系锚点、failure mode 或 gold strategy。

M1/M2/M3 与 M0 没有读取继承关系。它们不读 Letta M0 baseline，只读本实验构造的关系记忆 payload：M1 读结论，M2 读 M1+事件摘要，M3 读 M1+M2+必要细节和调用边界。

`timeline.json` 是实验脚本和评测用的 ground truth：它决定每天问什么、哪些天是复现/升级/转折、probe 如何插入，以及最终如何评分。它不是被测模型回答时的可读记忆。正式运行时流程是：

```text
timeline / probe plan 决定 user_message
↓
同一个 user_message 发给 M0/M1/M2/M3
↓
M0 只读 Letta 默认 memory
M1 只读结论级关系记忆
M2 读 M1 + 摘要级事件记忆
M3 读 M1 + M2 + 细节级关系锚点
↓
评测器再用 timeline / BEI / probe metadata 评分
```

当前 runner 使用 `shared_user_turns_only` 作为短期上下文策略：四个条件看到相同的历史 user turns，不再把各自不同的 assistant answer 带入后续 probe。这样后续回合的差异尽量只来自长期记忆权限，而不是前文回复分叉。

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

第一版 B 可以先用规则和结构化 schema 实现，后续再接入 Letta 或其他 stateful agent 框架。

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

- `M0`：A 可读同窗口共享 user turns + Letta 默认普通记忆；B 不返回人工设计的关系记忆、BEI、事件轨迹或关系锚点。
- `M1`：A 可读结论级关系记忆；不读 Letta M0 baseline。
- `M2`：A 可读 M1 + 摘要级事件线/状态变化记忆；不读 Letta M0 baseline。
- `M3`：A 可读 M1 + M2 + 必要细节、共同语言、关系锚点和调用边界；不读 Letta M0 baseline。

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
- `memory_actions`：本轮由 B 产生的记忆写入、更新或忽略动作。当前 M0/M1 probe 暂为空，后续 B-V0.1 会填充。

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

LLM_PROVIDER=poixe
```

共享模型客户端位于 `src/long_memory_test/llm.py`。A 后续做自然语言润色、B 后续接 Letta 或做记忆判断时，都应从该模块读取统一配置，避免散落多个 API key 和 base URL。当前 `LLM_PROVIDER` 支持 `poixe` 和 `deepseek`。

Poixe smoke test 位于 `scripts/poixe_smoke_test.py`，用于验证本地 key、base URL 和模型名是否可用。

本地 Letta server 作为 B 的记忆底座运行在 `http://127.0.0.1:8283`。DeepSeek 在 Letta 中按 OpenAI-compatible provider 接入：

- `OPENAI_API_KEY <- DEEPSEEK_API_KEY`
- `OPENAI_API_BASE <- DEEPSEEK_BASE_URL`
- 默认 B 模型：`openai-proxy/deepseek-v4-pro`
- 默认 embedding：`letta/letta-free`

B 的 Letta 配置入口位于 `src/long_memory_test/letta_memory.py`。基础连通性测试位于 `scripts/letta_memory_smoke.py`，用于验证 B agent 可以创建，并且 memory block 可以被修改和读回。

当前正式 Letta 记忆结构以 `docs/letta_current_memory_structure.md` 为准。`docs/letta_memory_levels.md` 只作为历史 pilot 文档保留。

最近已完成的 docx 路线基础改造：

- `scripts/annotate_bei.py` 已能从现有 probe 生成 `sample_output/bei_annotations.json`。
- `scripts/build_memory_conditions.py` 已能生成 `sample_output/memory_conditions.json`，其中 M0 是 generic agent memory baseline，M1/M2/M3 为累计关系记忆层级。
- `scripts/run_dialogue_conditions.py` 已能按同一用户输入运行 M0/M1/M2/M3，并为每轮记录 memory payload、input hash、模型参数和四组回答。
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
