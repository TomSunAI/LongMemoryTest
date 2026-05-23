# LongMemoryTest

长期关系记忆 Agent 实验平台。

当前已经实现 A-V0.1 和 A-V0.2：

- A-V0.1：模拟用户事件流生成器。它读取用户画像、生活领域和事件模板，生成约 30 天的结构化生活事件流 `timeline.json`。
- A-V0.2：编剧式每日用户发言生成器。它读取 `timeline.json`，生成 `daily_user_message.json`，用于后续驱动对话 Agent 和记忆 Agent。

## 当前实现

- 输入：`data/config/persona.json`
- 输入：`data/config/life_domains.json`
- 输入：`data/config/event_templates.json`
- 输出：`sample_output/timeline.json`
- 输出：`sample_output/daily_user_message.json`

生成结果包含：

- 30 天模拟时间线。
- 每天 1-3 个事件。
- 至少 2 条跨天持续推进的主线事件。
- 主线、支线、背景事件区分。
- `related_event_id` 用于标记跨天事件链。
- 情绪强度、决策影响、时间敏感度、记忆标记等字段。
- 每天一条自然语言用户发言。
- 发言意图、语气、关联事件和记忆相关性元数据。
- 可测试共同事件回忆的 follow-up / implicit recall 类发言。
- 同一话题会按 `script_stage` 推进，避免每天重新交代同一背景。

## 运行

```bash
python3 scripts/generate_timeline.py
```

从 `timeline.json` 生成每日用户发言：

```bash
python3 scripts/generate_daily_user_messages.py
```

指定输出路径、天数和随机种子：

```bash
python3 scripts/generate_timeline.py \
  --output sample_output/timeline.json \
  --days 30 \
  --seed 42
```

指定每日用户发言输出路径和随机种子：

```bash
python3 scripts/generate_daily_user_messages.py \
  --timeline sample_output/timeline.json \
  --output sample_output/daily_user_message.json \
  --seed 142
```

当前 A-V0.2 默认不接 LLM，使用编剧式规则、多模板和话题阶段推进，保证可复现、可调试、可评测。后续 A-V0.3 再接入 LLM 做自然语言润色、风格扩展和更强的表达多样性。

## 项目结构

```text
data/config/
  persona.json
  life_domains.json
  event_templates.json
scripts/
  generate_timeline.py
  generate_daily_user_messages.py
src/long_memory_test/agents/
  event_stream_generator.py
  daily_message_generator.py
sample_output/
  timeline.json
  daily_user_message.json
```

## 下一步

下一阶段建议实现 B-V0.1：读取 `daily_user_message.json`，根据 M0/M1/M2/M3 权限判断应该读取什么记忆、写入什么记忆，以及哪些内容不应该被记住。
