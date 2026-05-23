# LongMemoryTest Agent Notes

## 项目定位

本项目用于实验“长期关系记忆 Agent”在不同记忆机制下的表现差异。核心问题是：一个对话型 Agent 需要记住用户到什么程度，才会让用户感觉它像长期朋友，而不是每次都像第一次见面的客服。

项目只比较同一个基础对话 Agent 在不同记忆条件下的表现，不研究多种不同 Agent 类型。

## 记忆实验分组

- `M0`：无关系记忆，只看当前输入，不读取历史记忆。
- `M1`：结论级记忆，只保留用户偏好、沟通方式、稳定性格、长期压力源等压缩结论。
- `M2`：共同事件级记忆，保留用户与 Agent 共同讨论过的重要事件及其进展。
- `M3`：事件细节级记忆，保留关键事件的背景、情绪原因、触发语句、深层心理和后续追踪点。

实验重点不是“记得越多越好”，而是评估不同记忆粒度在自然度、关系连续性、帮助效果和过度记忆风险之间的平衡。

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

1. 用户输入一条消息。
2. B 根据实验组别读取允许的记忆。
3. A 基于当前消息和 B 返回的记忆生成回复。
4. B 读取本轮用户消息和 A 的回复。
5. B 判断是否写入、更新或忽略记忆。
6. 系统保存对话日志、记忆变更日志和评测所需字段。

实验中四组 Agent 的主要差异应体现在 B 的权限控制：

- `M0`：B 不给 A 返回历史记忆，也不写长期记忆。
- `M1`：B 只返回和写入结论级关系记忆。
- `M2`：B 返回和写入 M1 + 共同事件级记忆。
- `M3`：B 返回和写入 M1 + M2 + 事件细节级记忆。

## 当前阶段

当前 A-V0.1 和 A-V0.2 已完成第一版可运行原型：

- A-V0.1：`persona.json` + `life_domains.json` + `event_templates.json` -> `timeline.json`。
- A-V0.2：`timeline.json` -> 编剧式 `daily_user_message.json`。

当前开始搭建 B-V0.1：统一记忆 Agent 的规则版原型。

已跑通两条 A 侧小链路：

1. `persona.json` + `life_domains.json` + `event_templates.json` -> `generate_timeline.py` -> `timeline.json`。
2. `timeline.json` -> `generate_daily_user_messages.py` -> `daily_user_message.json`。

B-V0.1 的下一条小链路是：

3. `daily_user_message.json` + `timeline.json` -> `run_memory_agent.py` -> `memory_actions.json`。

当前阶段暂不实现复杂前端、多智能体系统、真实向量库或完整自动评测。先保证 B 的记忆层级判断、记忆动作和实验字段稳定、可复现、可扩展。

## 模型 API 配置

项目使用 Poixe 作为 OpenAI-compatible API 入口，供 A 和 B 共用。模型配置通过本地 `.env.local` 提供，不提交到 git。

推荐本地配置：

```bash
POIXE_API_KEY=your-poixe-api-key-here
POIXE_BASE_URL=https://api.poixe.com/v1
POIXE_MODEL=gpt-5.2
LLM_PROVIDER=poixe
```

共享模型客户端位于 `src/long_memory_test/llm.py`。A 后续做自然语言润色、B 后续接 Letta 或做记忆判断时，都应从该模块读取统一配置，避免散落多个 API key 和 base URL。

Poixe smoke test 位于 `scripts/poixe_smoke_test.py`，用于验证本地 key、base URL 和模型名是否可用。

本地 Letta server 作为 B 的记忆底座运行在 `http://127.0.0.1:8283`。Poixe 在 Letta 中按 OpenAI-compatible provider 接入：

- `OPENAI_API_KEY <- POIXE_API_KEY`
- `OPENAI_API_BASE <- POIXE_BASE_URL`
- 默认 B 模型：`openai-proxy/gpt-5.2`
- 默认 embedding：`openai/text-embedding-3-small`

B 的 Letta 配置入口位于 `src/long_memory_test/letta_memory.py`。基础连通性测试位于 `scripts/letta_memory_smoke.py`，用于验证 B agent 可以创建，并且 M2 memory block 可以被修改和读回。

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
- `probe_evaluation_table`：对比四类 Agent 对 Probe 问题的回答效果。

评分维度包括召回准确性、层级合规性、关系连续性、情绪理解、自然度、有效帮助、过度记忆风险和综合得分。

其中 `level_compliance` 很重要。M0 不知道历史是合规表现；M3 能调用细节是能力，但机械复述或暴露过多细节需要扣分。

## 工程协作约定

- 优先保持实现简单、可读、可复现。
- 先搭建数据结构和离线生成流程，再接入 Agent 运行与评测。
- 对实验条件要保持可控，避免不同记忆层级之间发生数据污染。
- 文档、数据 schema、生成脚本和评测逻辑要能互相解释。
- 新增代码前先确认当前阶段目标，避免过早引入复杂框架。
