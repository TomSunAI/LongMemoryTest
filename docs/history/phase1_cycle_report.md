# LongMemoryTest 第一阶段周期文档

生成日期：2026-05-26  
阶段范围：A-V0.1 / A-V0.2 / A-V0.3 场景卡准备 + M0/M1 30 天对话链路  
当前状态：第一阶段闭环已跑通，后续可转换为 Word 版本

## 1. 阶段目标

第一阶段目标是验证一个最小但完整的“长期关系记忆 Agent”实验链路：

1. 构造一个稳定的模拟用户画像。
2. 生成 30 天生活事件流。
3. 将事件流转成每日用户开场消息。
4. 为同一天内继续聊生成可控场景卡。
5. 使用 DeepSeek 生成 M0/M1 两组 Agent 回复。
6. 保存完整 `conversation_log.json`，让后续评测可以复盘原始对话。
7. 明确当前记忆层级边界，避免短期上下文、长期记忆、剧本事实混在一起。

第一阶段不追求完整 M2/M3 记忆写入，也不追求自动评分系统。重点是把 A/B 架构、数据产物、M0/M1 对照链路和日志格式固定下来。

## 2. 当前技术架构

### 2.1 总体架构

当前系统拆成两个核心角色：

| 角色 | 当前职责 | 当前实现状态 |
|---|---|---|
| A：拟人对话 Agent | 面向用户生成自然回复；在实验中按不同记忆权限回答同一用户消息 | 已跑通 M0/M1 |
| B：统一记忆 Agent | 管理记忆层级、记忆权限、Letta blocks 和后续记忆动作 | Letta 底座已接入，M0/M1 seed memory 已跑通 |
| 模拟用户生成器 | 生成 30 天生活事件、每日开场消息、同日追问场景卡 | 已完成 A-V0.1/V0.2/V0.3 数据准备 |

当前实验比较的不是不同 Agent 人格，而是同一个 A 在不同记忆权限下的表现差异。

## 3. 第一阶段实验方法

本阶段采用“剧本约束 + 受控记忆变量 + 完整日志复盘”的方法，而不是让模型自由生成一个不可复现的长对话。

### 3.1 方法总览

第一阶段方法分为四层：

| 方法层 | 目的 | 当前实现 |
|---|---|---|
| 用户生活事件生成 | 构造一个月内用户可能经历的生活事件 | `timeline.json`，30 天，63 个事件 |
| 用户发言剧本化 | 把结构化事件转为每日自然语言开场 | `daily_user_message.json`，每天 1 条开场 |
| 同日追问受控扩展 | 让某一天的话题可以继续聊，但不越出剧本事实 | `daily_scene_cards.json` + DeepSeek follow-up 生成 |
| 记忆层级对照 | 同一用户 turn 分别喂给 M0/M1，比较记忆权限影响 | `run_m0_m1_dialogue_probe.py` |

这套方法的核心是：用户侧事实由剧本和场景卡控制，Agent 侧差异只来自记忆层级。这样才能判断“记忆层级”本身带来的差异，而不是被用户输入变化或模型自由发挥污染。

### 3.2 变量控制方法

当前 M0/M1 对照实验控制了以下变量：

| 变量 | 控制方式 |
|---|---|
| 用户画像 | 两组共享同一个 `persona.json` / `user_actor.json` |
| 用户事件 | 两组共享同一个 `timeline.json` |
| 用户开场消息 | 两组共享同一个 `daily_user_message.json` |
| 用户追问 | 使用 `controlled_user_replay`，同一条追问同时喂给 M0/M1 |
| 同窗口短期上下文 | M0/M1 都开启，各自只看到本组前文 |
| 长期关系记忆 | 仅 M1 可读 `m1_relationship` |
| 具体事件长期记忆 | M0/M1 都不可读 M2/M3 |
| 模型能力 | M0/M1 使用同一 DeepSeek 模型 |

因此，当前实验中的主要自变量是：

```text
是否向 A 暴露 M1 结论级关系记忆。
```

### 3.3 用户追问生成方法

同一天内的用户追问不是完全自由生成，而是由 `daily_scene_cards.json` 控制。每张 scene card 包含：

- 当天开场消息。
- 当前 active events。
- 允许使用的事实 `allowed_facts`。
- 可逐步透露的隐含担心 `latent_concerns`。
- follow-up 预算。
- 每一轮 follow-up 的 reveal schedule。
- 禁止编造项 `must_not_invent`。

用户追问生成时使用 hard factual boundary：

1. 只能使用 scene card 和此前用户发言中的事实。
2. 不能把 assistant 回复里的例子、假设或建议转写成用户新增事实。
3. 如果 scene card 没有写明具体原因，只能表达“消息还很模糊/没有正式通知”。
4. 不允许新增人物、地点、诊断、金额、日期或剧本外重大事件。

这个方法是第一阶段的重要修正。早期测试发现，模型会把 assistant 的条件示例吸收成用户事实，例如把“幼儿园可能不稳定”具体化成“换园长/换承办方”。加入 hard factual boundary 后，30 天实验中禁用具体传言命中数为 0。

### 3.4 长时间对话执行方法

长时间对话必须可恢复。当前脚本采用 checkpoint 方法：

- 每完成一个用户 turn，立即写入 `--output`。
- 写入采用临时文件替换，避免半写入文件。
- `conversation_log.json` 按 `run_id` 同步当前 run 的 turns。
- 恢复时从 `--output` 读取已完成 turns。
- 恢复时重建 M0/M1 各自的短期上下文。
- 已完成的 message_id 会被跳过。
- 如果中断发生在某一次模型请求中间，只重跑那一个未完成 turn。

这一点对一个月或更长时间跨度的模拟是必要条件，否则一次网络波动就会导致整条链路从头重跑，且可能产生不同的用户追问。

## 4. 实验记录格式

本阶段将实验记录视为一等产物。后续评测、记忆写入、错误定位都应从结构化日志中读取，而不是依赖终端输出。

### 4.1 输出文件层级

当前实验记录分为四类：

| 文件 | 记录范围 | 用途 |
|---|---|---|
| `timeline.json` | 30 天生活事件 | 事实源，定义发生了什么 |
| `daily_user_message.json` | 每日开场用户消息 | 剧本入口，定义每天先聊什么 |
| `daily_scene_cards.json` | 每日可扩展场景卡 | 限制同日追问如何继续 |
| `m0_m1_30day_scene_probe.json` | 一次 M0/M1 run 的完整输出 | 可恢复主状态文件 |
| `conversation_log.json` | 多次实验 run 的统一对话日志 | 后续查询、评测、记忆动作输入 |
| `m0_m1_30day_scene_dialogue_readable.md` | 人类可读原文 | 人工复盘 |

### 4.2 `conversation_log.json` 顶层格式

当前 `conversation_log.json` 顶层结构：

```json
{
  "schema_version": "conversation_log_v0.1",
  "description": "Structured dialogue records for M0/M1/M2/M3/LN memory experiments.",
  "turns": []
}
```

`turns` 是所有对话轮次的数组。每个 turn 代表一次用户输入，以及 M0/M1 对这条用户输入的各自回复。

### 4.3 turn 记录格式

每条 turn 至少包含以下字段：

| 字段 | 说明 |
|---|---|
| `run_id` | 当前实验运行 ID |
| `created_at` | run 创建时间 |
| `turn_index` | 当前 run 内的顺序编号 |
| `probe` | 当前 probe 类型，如 `m0_vs_m1_chain` |
| `conversation_context_policy` | M0/M1 上下文和记忆权限说明 |
| `source` | 本 turn 来源文件、message_id、scene_id、turn_type |
| `input` | 完整用户输入和元数据 |
| `b_agent` | Letta B agent 配置 |
| `llm` | A 使用的 LLM provider/model/max_tokens |
| `memory_setup` | 本轮使用的受控记忆设置 |
| `variants` | M0/M1 回复结果 |
| `memory_actions` | B 后续应产生的记忆动作；当前为空 |

示意结构：

```json
{
  "run_id": "m0_m1_probe_...",
  "turn_index": 1,
  "source": {
    "daily_messages_path": "sample_output/daily_user_message.json",
    "scene_cards_path": "sample_output/daily_scene_cards.json",
    "message_id": "D01_M001",
    "scene_id": "D01_SCENE",
    "turn_type": "scripted_opening"
  },
  "input": {
    "message_id": "D01_M001",
    "day": 1,
    "user_message": "...",
    "event_refs": ["E001"],
    "topic": "孩子幼儿园可能不稳定",
    "intent": "problem_solving",
    "memory_relevance": "possible_memory_candidate"
  },
  "variants": {
    "M0": {
      "memory_available": false,
      "short_term_context": {
        "enabled": true,
        "previous_turn_count": 0
      },
      "assistant_answer": "..."
    },
    "M1": {
      "memory_available": true,
      "memory_context": {
        "block_label": "m1_relationship",
        "content": "..."
      },
      "short_term_context": {
        "enabled": true,
        "previous_turn_count": 0
      },
      "assistant_answer": "..."
    }
  },
  "memory_actions": []
}
```

### 4.4 `source.turn_type`

当前 turn type 有两类：

| turn_type | 说明 |
|---|---|
| `scripted_opening` | 当天剧本开场，来自 `daily_user_message.json` |
| `llm_user_followup` | 同一天内由 DeepSeek 在 scene card 约束内生成的用户追问 |

当前 30 天实验中：

```text
scripted_opening = 30
llm_user_followup = 30
```

### 4.5 `variants` 记录格式

`variants` 是实验对照的核心字段。当前包含 M0/M1 两组。

M0：

```json
{
  "memory_available": false,
  "memory_context": null,
  "short_term_context": {
    "enabled": true,
    "previous_turn_count": 0,
    "previous_message_ids": []
  },
  "assistant_answer": "..."
}
```

M1：

```json
{
  "memory_available": true,
  "memory_context": {
    "block_label": "m1_relationship",
    "content": "..."
  },
  "short_term_context": {
    "enabled": true,
    "previous_turn_count": 0,
    "previous_message_ids": []
  },
  "assistant_answer": "..."
}
```

这个格式保证后续可以逐 turn 对比：

- 同一用户输入下，M0 和 M1 的回复差异。
- 同窗口短期上下文是否正确增长。
- M1 是否只使用结论级关系记忆。
- 是否出现越权调用 M2/M3 的行为。
- 用户话语背后的隐含意图、情绪状态和关系期待是否被识别。

### 4.6 ToM 对话质量评测目标

当前对话质量评估全面切换为 ToM-only 标准，不再使用细节命中、层级合规或旧粗评分作为主结论，也不把它们和 ToM 分数融合。ToM 评估只看模型是否理解用户话语背后的心理状态、关系期待和共同语境。

| 字段 | 来源 | 用途 |
|---|---|---|
| `probe_question_plan[].tom_dimensions` | 定向 probe | 定义本轮要评估的 ToM 维度 |
| `probe_question_plan[].tom_assessment` | 定向 probe | 定义表面问题、隐含需求、低分表现和高分表现 |
| `turn.evaluation_targets.tom_quality` | 对话日志 | 记录本轮 ToM 质量评估目标 |
| `tom_quality_evaluation.json/md` | 评估输出 | 记录 M0/M1 的 ToM-only 评分和低分样例 |

当前 ToM-only 维度：

1. `hidden_intent_recognition`：是否识别用户字面表达背后的真实诉求。
2. `emotional_state_recognition`：是否识别疲惫、失落、自我怀疑、不安等状态。
3. `relationship_expectation_recognition`：是否识别用户期待熟悉关系，而不是陌生客服。
4. `shared_context_invocation`：是否自然调用此前共同语境。
5. `alienation_error_rate`：是否出现陌生化、客服化、过度亲密或要求用户重讲历史。
6. `natural_detail_use`：是否把关键细节用于理解心理状态，而不是机械背记忆。

当前 ToM-only 评估器：

```bash
PYTHONPATH=src .venv/bin/python scripts/evaluate_tom_quality.py \
  --conversation-log sample_output/conversation_log_tom_probe.json \
  --output-json sample_output/tom_quality_evaluation_tom_probe.json \
  --output-md sample_output/tom_quality_evaluation_tom_probe.md
```

输出：

| 文件 | 作用 |
|---|---|
| `sample_output/tom_quality_evaluation_tom_probe.json` | 逐 ToM probe / variant 的 ToM-only 评分 |
| `sample_output/tom_quality_evaluation_tom_probe.md` | 汇总表、维度均值和低分样例 |

该评分器仍是规则启发式 triage，不等于最终语义判定；但当前主口径已经切换为 ToM-only，不再使用旧 detail-hit 分数。

### 4.7 `m0_m1_30day_scene_probe.json` 恢复格式

`m0_m1_30day_scene_probe.json` 是当前 run 的主状态文件。它除了保存 turns，还保存 checkpoint：

```json
{
  "run_id": "...",
  "message_ids": ["D01_M001", "..."],
  "scene_followups": 1,
  "expected_turns": 60,
  "resume_supported": true,
  "checkpoint": {
    "status": "complete",
    "updated_at": "...",
    "completed_turns": 60,
    "expected_turns": 60,
    "last_message_id": "D30_M001_F001"
  },
  "turns": []
}
```

恢复时，脚本以该文件为准，而不是以终端输出或 `conversation_log.json` 为准。

### 4.8 记录格式设计原则

当前记录格式遵循以下原则：

1. 每个 turn 必须可追溯到剧本输入和场景卡。
2. 每个 variant 必须明确记录记忆权限。
3. M0/M1 的短期上下文计数必须可复核。
4. 对话原文和实验元数据必须在同一 turn 中保存。
5. 记忆动作暂时为空，但字段必须保留，为 B-V0.1 接入做准备。
6. 长跑必须可以从主状态文件恢复。

## 5. 当前执行链路

### 5.1 A 侧数据链路

当前 A 侧已经形成三段生成链路：

```text
data/config/persona.json
data/config/life_domains.json
data/config/event_templates.json
  -> scripts/generate_timeline.py
  -> sample_output/timeline.json

sample_output/timeline.json
  -> scripts/generate_daily_user_messages.py
  -> sample_output/daily_user_message.json

sample_output/timeline.json
sample_output/daily_user_message.json
data/config/user_actor.json
data/config/conversation_expansion_policy.json
  -> scripts/generate_daily_scene_cards.py
  -> sample_output/daily_scene_cards.json

sample_output/daily_scene_cards.json
data/config/probe_question_policy.json
  -> scripts/generate_probe_question_plan.py
  -> sample_output/probe_question_plan.json
  -> sample_output/a_script_plan.json
```

关键数据文件：

| 文件 | 作用 |
|---|---|
| `data/config/persona.json` | 模拟用户稳定画像 |
| `data/config/life_domains.json` | 生活领域与采样权重 |
| `data/config/event_templates.json` | 可采样事件模板 |
| `data/config/user_actor.json` | 模拟用户 A 的说话方式、压力反应和披露节奏 |
| `data/config/conversation_expansion_policy.json` | 同一天内 LLM 追问扩展边界 |
| `data/config/probe_question_policy.json` | ToM 定向测试问题策略 |
| `sample_output/timeline.json` | 30 天结构化生活事件 |
| `sample_output/daily_user_message.json` | 每天一条剧本开场用户消息 |
| `sample_output/daily_scene_cards.json` | 每天一张场景卡，用于限制 LLM 追问扩展 |
| `sample_output/probe_question_plan.json` | 12 个 ToM 定向测试问题，带 ToM 指标、隐含需求和高低分表现 |
| `sample_output/a_script_plan.json` | 106 个 A 侧剧本单元总表 |

当前定向问题覆盖：

- M1 回应风格：1 条。
- 记忆边界：1 条。
- M2 事件连续性：2 条。
- 自然细节调用：7 条。
- 称呼风格：1 条。
- ToM 指标：隐含意图识别、情绪状态识别、关系期待识别、共同语境调用、陌生化错误率、自然细节调用。

### 5.2 M0/M1 对话链路

当前 M0/M1 对话脚本：

```text
scripts/run_m0_m1_dialogue_probe.py
```

当前 30 天完整运行命令：

```bash
PYTHONPATH=src .venv/bin/python scripts/run_m0_m1_dialogue_probe.py \
  --all-message-ids \
  --scene-followups 1 \
  --output sample_output/m0_m1_30day_scene_probe.json \
  --reset-conversation-log \
  --print-mode summary \
  --print-progress
```

插入定向测试问题后的 30 天运行命令：

```bash
PYTHONPATH=src .venv/bin/python scripts/run_m0_m1_dialogue_probe.py \
  --all-message-ids \
  --scene-followups 1 \
  --probe-questions sample_output/probe_question_plan.json \
  --output sample_output/m0_m1_30day_scene_probe_with_probes.json \
  --reset-conversation-log \
  --print-mode summary \
  --print-progress
```

长跑恢复命令：

```bash
PYTHONPATH=src .venv/bin/python scripts/run_m0_m1_dialogue_probe.py \
  --all-message-ids \
  --scene-followups 1 \
  --output sample_output/m0_m1_30day_scene_probe.json \
  --conversation-log sample_output/conversation_log.json \
  --resume \
  --print-mode summary \
  --print-progress
```

脚本已经支持可恢复执行：

- `--output` 是主状态文件。
- 每完成一个用户 turn，脚本会原子写入 checkpoint。
- `conversation_log.json` 按 `run_id` 同步当前 run，避免恢复时重复追加。
- `--resume` 会从已有 `--output` 重建 M0/M1 短期上下文。
- 恢复时不能更换 `message_ids`、`--scene-followups` 或 `--probe-questions`；如需更换实验条件，应使用新的 `--output`。
- 定向 probe 在每个开场消息的同日 follow-up 后插入；每条 probe 的 `tom_assessment` 会进入本轮 `evaluation_targets.tom_quality`，当前质量评分只看 ToM 目标。

## 6. 当前模型与 Letta 配置

当前主要使用 DeepSeek API。

| 项 | 当前值 |
|---|---|
| A 回复 provider | `deepseek` |
| A 回复模型 | `deepseek-v4-pro` |
| DeepSeek base URL | `https://api.deepseek.com` |
| Letta base URL | `http://127.0.0.1:8283` |
| Letta B 模型 | `openai-proxy/deepseek-v4-pro` |
| Letta embedding | `letta/letta-free` |

安全约定：

- API key 只保存在本地 `.env.local`。
- 文档和日志不写真实 key。
- DeepSeek 的 token 上限不做低额度人工截断，`deepseek-v4-*` 默认使用 `384000` 作为请求上限。

## 7. 当前使用的记忆层级

当前实际运行的是 M0/M1。

| 层级 | 当前是否执行 | 当前可读内容 | 当前禁止内容 | 当前写入策略 |
|---|---:|---|---|---|
| M0 | 是 | 当前用户消息 + 同窗口短期上下文 | 任何跨 session 长期记忆、Letta memory blocks | 不写长期记忆 |
| M1 | 是 | 当前用户消息 + 同窗口短期上下文 + `m1_relationship` | M2/M3 具体事件记忆、archival memory | 当前使用受控 seed memory，尚未自动更新 |
| M2 | 否 | 设计为 M1 + 共同事件记忆 | M3 细节记忆 | 尚未执行 |
| M3 | 否 | 设计为 M1 + M2 + 高价值事件细节 | 过度暴露低价值细节 | 尚未执行 |

当前 M1 seed memory：

```text
用户偏好直接、自然、少废话的回应；不喜欢客服式寒暄和空泛安慰。
当用户焦虑时，更需要先拆事实、选项、风险和下一步，而不是被泛泛安抚。
用户希望 Agent 像长期朋友一样回应，语气可以真诚但不要过度解释。
```

重要边界：

- M0 并不是“完全无上下文”，而是“无长期关系记忆”。它可以看同一窗口前文。
- M1 不知道具体事件历史，只知道结论级关系偏好。
- 当前 `memory_actions` 仍为空，B-V0.1 的写入/更新判断还未实现。

## 8. 第一阶段实验数据

本节数据来自当前 `sample_output/` 下的 JSON 产物。

### 8.1 事件时间线数据

| 指标 | 数值 |
|---|---:|
| 模拟天数 | 30 |
| 事件总数 | 63 |
| 应被记住事件数 | 42 |
| 需要 follow-up 事件数 | 58 |
| 跨天事件链 root | `E007`, `E020` |

领域分布：

| 领域 | 事件数 |
|---|---:|
| parenting | 18 |
| self_management | 16 |
| career | 13 |
| intimate_relationship | 11 |
| friendship | 5 |

事件类型分布：

| 类型 | 数量 |
|---|---:|
| side | 36 |
| background | 21 |
| mainline | 6 |

### 8.2 每日用户开场消息数据

| 指标 | 数值 |
|---|---:|
| 每日开场消息数 | 30 |
| 生成模式 | `scripted_v0.2_no_llm` |

主题分布：

| 主题 | 消息数 |
|---|---:|
| 孩子幼儿园可能不稳定 | 8 |
| 合作项目推进不顺 | 5 |
| 家里分工和伴侣沟通 | 5 |
| 睡眠被打碎 | 4 |
| 孩子入园适应 | 4 |
| 论文截稿前的取舍 | 3 |
| 朋友约我见面 | 1 |

意图分布：

| 意图 | 消息数 |
|---|---:|
| light_check_in | 8 |
| reflection | 6 |
| problem_solving | 4 |
| emotional_support | 3 |
| casual_share | 2 |
| follow_up_update | 2 |
| pattern_check | 2 |
| planning | 1 |
| decision_support | 1 |
| implicit_recall | 1 |

记忆相关性分布：

| memory_relevance | 消息数 |
|---|---:|
| possible_memory_candidate | 21 |
| shared_event_memory | 4 |
| background_context | 3 |
| new_shared_event_candidate | 2 |

### 8.3 场景卡数据

| 指标 | 数值 |
|---|---:|
| 场景卡数量 | 30 |
| actor_ref | `user_actor_wendy_v0.1` |
| expansion_policy_ref | `script_anchored_expansion_v0.1` |
| event_detail_target_count | 126 |
| long_term_event_detail_target_count | 84 |
| latent_detail_target_count | 60 |

follow-up 预算分布：

| followup_budget | 场景卡数量 |
|---:|---:|
| 1 | 10 |
| 2 | 6 |
| 3 | 14 |

当前实际实验为了控制成本和长度，每天只执行 1 条 LLM 用户追问，即：

```text
1 scripted opening + 1 llm_user_followup
```

### 8.4 30 天 M0/M1 对话实验数据

| 指标 | 数值 |
|---|---:|
| 实际对话天数 | 30 |
| 用户 turns | 60 |
| scripted_opening | 30 |
| llm_user_followup | 30 |
| 第一条 message_id | `D01_M001` |
| 最后一条 message_id | `D30_M001_F001` |
| M0 最后一轮短期上下文轮数 | 59 |
| M1 最后一轮短期上下文轮数 | 59 |
| LLM provider | `deepseek` |
| LLM model | `deepseek-v4-pro` |
| forbidden_followup_hits | 0 |

主要输出文件：

| 文件 | 说明 |
|---|---|
| `sample_output/conversation_log.json` | 结构化对话日志 |
| `sample_output/m0_m1_30day_scene_probe.json` | 30 天 M0/M1 probe 输出 |
| `sample_output/m0_m1_30day_scene_dialogue_readable.md` | 30 天对话可读版 |
| `/Users/tom/Desktop/m0_m1_30day_scene_dialogue_readable.md` | 桌面可读版 |
| `/Users/tom/Desktop/conversation_log_30day.json` | 桌面 JSON 副本 |

## 9. 当前工程质量与测试

当前已加入无网络单元测试，覆盖：

- 场景卡生成数量和字段完整性。
- `--all-message-ids` 解析。
- LLM follow-up 消息构造。
- JSON fenced output 解析。
- 用户追问 hard factual boundary prompt。
- checkpoint 写入与 conversation log 同步。
- resume 状态重建 M0/M1 短期上下文。

当前测试结果：

```text
10 tests passed
compileall passed
JSON validation passed
line-length check passed
```

长跑稳定性改进：

- 已支持 `--print-progress`。
- 已支持 `--resume`。
- 已支持每 turn checkpoint。
- 已避免恢复时重复追加 conversation log。

## 10. 第一阶段观察结论

### 10.1 M0 与 M1 的差异

当前 M0/M1 的差异主要体现在回应风格和切入方式。

M0：

- 能使用同窗口短期上下文。
- 没有长期关系记忆。
- 更容易像通用咨询助手，建议可能更发散。

M1：

- 能使用同窗口短期上下文。
- 额外读取 `m1_relationship`。
- 更倾向直接、少铺垫、先拆事实和下一步。
- 不应引入具体历史事件。

这符合第一阶段设计：M1 的作用不是“记得具体事件”，而是让 A 的回应方式更贴合用户的稳定偏好。

### 10.2 场景卡边界是必要的

在短链测试中曾发现：如果不限制用户追问生成器，LLM 可能会把 assistant 回复里的示例转写成用户事实，例如把“幼儿园不稳定”具体化成“换园长/换承办方”。

当前已加入 hard factual boundary：

- 用户追问只能使用 scene card 和已有用户发言中的事实。
- assistant 回复中的例子、假设和建议不是用户事实。
- 如果 scene card 没有给出具体原因，用户只能说“消息还很模糊/没有正式通知”。

当前 30 天实验中，LLM 用户追问没有命中禁止词：

```text
forbidden_followup_hits = 0
```

### 10.3 短期上下文与长期记忆必须分开

当前实验确认：

- 同窗口短期上下文是必要的，否则无法模拟一个月内同一 session 的自然聊天。
- M0 可以使用短期上下文，但不能使用长期关系记忆。
- M1 可以使用短期上下文 + 结论级关系记忆，但不能知道具体事件历史。

这个边界后续必须继续保持，否则 M0/M1/M2/M3 的比较会失真。

## 11. 当前限制

第一阶段仍有明确限制：

1. 只实际跑通 M0/M1，M2/M3 尚未执行。
2. `memory_actions` 仍为空，B-V0.1 的记忆判断和写入还未实现。
3. M1 目前使用受控 seed memory，没有从对话中自动更新。
4. 已有 ToM-only 规则评分器，但还没有 LLM-as-judge 和完整人工复核表。
5. 还没有 Letta Native baseline。
6. 当前对话每一天只跑 1 条 LLM follow-up，未用满每张 scene card 的 follow-up budget。
7. 当前没有 Word 版，本文件先作为 Markdown 源文档。

## 12. 第二阶段建议

第二阶段建议按以下顺序推进：

1. 实现 B-V0.1 `memory_actions.json`。
2. 从 30 天 `conversation_log.json` 中抽取 M1/M2/M3 写入建议。
3. 将 M1/M2/M3 动作写入 Letta blocks。
4. 跑 M2/M3 对照链路。
5. 建立 `tom_evaluation_table`，围绕隐含意图、情绪状态、关系期待、共同语境和陌生化错误做人审。
6. 后续如果需要评估记忆事实准确性，单独做 memory audit，不与 ToM 质量评分融合。
7. 增加 Letta Native baseline。
8. 将本 Markdown 周期文档转换为 Word 版本。

## 13. 附录：当前核心文件

| 路径 | 说明 |
|---|---|
| `agent.md` | 项目当前协作与架构说明 |
| `README.md` | 运行入口和项目结构 |
| `docs/letta_memory_levels.md` | M0/M1/M2/M3 记忆层级设计 |
| `docs/phase1_cycle_report.md` | 第一阶段周期文档 |
| `scripts/generate_timeline.py` | 生成 30 天事件流 |
| `scripts/generate_daily_user_messages.py` | 生成每日用户开场消息 |
| `scripts/generate_daily_scene_cards.py` | 生成每日场景卡 |
| `scripts/run_m0_m1_dialogue_probe.py` | M0/M1 对话 probe，支持 checkpoint/resume |
| `src/long_memory_test/agents/event_stream_generator.py` | 事件流生成器 |
| `src/long_memory_test/agents/daily_message_generator.py` | 每日用户发言生成器 |
| `src/long_memory_test/agents/daily_scene_card_generator.py` | 场景卡生成器 |
| `src/long_memory_test/llm.py` | OpenAI-compatible LLM 客户端 |
| `src/long_memory_test/letta_memory.py` | Letta B memory agent 配置 |
| `tests/test_daily_scene_card_generator.py` | 场景卡测试 |
| `tests/test_run_m0_m1_dialogue_probe.py` | M0/M1 probe 与恢复机制测试 |
