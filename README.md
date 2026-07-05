# LongMemoryTest

长期关系记忆 Agent 实验平台。

当前主线以 Relational Memory 实验条件与 M0 实现方案为准：事件先行、BEI 标注校准、R0/R1 参照条件，以及 M0/M1/M2/M3 记忆层级对照。`M0` 是 LD-Agent memory-only generic baseline，不使用 LD-Agent 的 generator/checkpoint；`M1/M2/M3` 是在同一个 M0 普通记忆底座上追加的累计关系性记忆层级。

当前已经实现 A-V0.1、A-V0.2、A-V0.3 场景卡准备和 A-V0.4 标准 ToM probe 题集：

- A-V0.1：模拟用户事件流生成器。它读取用户画像、生活领域和事件模板，生成约 30 天的结构化生活事件流 `timeline.json`。
- A-V0.2：编剧式每日用户发言生成器。它读取 `timeline.json`，生成 `daily_user_message.json`，用于后续驱动对话 Agent 和记忆 Agent。
- A-V0.3：同一天内多轮继续聊的场景卡生成器。它读取人物扮演配置、扩展策略、时间线和每日开场消息，生成 `daily_scene_cards.json`。
- A-V0.4：以记忆场景为背景的 ToM 定向测试问题生成器。它读取场景卡和测试策略，生成 `probe_question_plan.json` 与完整 A 侧剧本总表 `a_script_plan.json`。

## 当前实现

- 输入：`data/config/persona.json`
- 输入：`data/config/life_domains.json`
- 输入：`data/config/event_templates.json`
- 输入：`data/config/user_actor.json`
- 输入：`data/config/conversation_expansion_policy.json`
- 输入：`data/config/probe_question_policy.json`
- 输出：`long_memory_experiment/data/script/timeline.json`
- 输出：`long_memory_experiment/data/script/daily_user_message.json`
- 输出：`long_memory_experiment/data/script/daily_scene_cards.json`
- 输出：`long_memory_experiment/data/script/probe_question_plan.json`
- 输出：`long_memory_experiment/data/script/a_script_plan.json`
- 输出：`long_memory_experiment/data/script/bei_annotations.json`
- 输出：`long_memory_experiment/data/script/event_line_audit.json`
- 输出：`long_memory_experiment/data/memory_conditions/*.json`
- 缓存：`long_memory_experiment/cache/timeline_events.json`
- 缓存：`long_memory_experiment/cache/memory_conditions_combined.json`

生成结果包含：

- 30 天日级 canonical 时间线，字段包括 `main_topic`、`event_stage`、`related_previous_days`、`latent_continuity`、`probe_candidate` 和 `reason_for_probe`。
- 事件级原始时间线写入 cache，供确定性生成器复用。
- 每天 1-3 个事件。
- 至少 2 条跨天持续推进的主线事件。
- 主线、支线、背景事件区分。
- `related_event_id` 用于标记跨天事件链。
- 情绪强度、决策影响、时间敏感度、记忆标记等字段。
- 每天一条自然语言用户发言。
- 发言意图、语气、关联事件和记忆相关性元数据。
- 可测试共同事件回忆的 follow-up / implicit recall 类发言。
- 同一话题会按 `script_stage` 推进，避免每天重新交代同一背景。
- 每天一张场景卡，包含开场消息、事件事实、隐含担心、follow-up 预算、允许扩展动作和停止条件。
- 人物卡和事件模板会产出细节锚点，场景卡中的 `memory_detail_expectations` 只作为后续 memory audit 候选，不进入当前对话质量评分。
- 20 个核心 probe candidate 节点。
- 36 个标准 ToM probe，覆盖 current understanding、memory invocation、state transformation、relational boundary、alienation 和 natural detail。
- 150 个 A 侧剧本单元：30 个每日开场、84 个 LLM follow-up slot、36 个 targeted probe。
- docx 路线 BEI 标注：belief、emotion、intention、relational expectation、required memory、failure mode 和 gold strategy。
- M0/M1/M2/M3 四组受控 memory payload；M0 实际普通 event/persona memory 由运行时 LD-Agent memory adapter 写入和检索。
- `event_line_audit.json` 验收 6 条核心主题线，每条都有 initial、recurrence、turning_point、resolution、reflection，且没有 suggested_fix。

## 运行

```bash
PYTHONPATH=src .venv/bin/python scripts/01_build_timeline.py
PYTHONPATH=src .venv/bin/python scripts/03_generate_probe_plan.py
PYTHONPATH=src .venv/bin/python scripts/02_annotate_bei.py
PYTHONPATH=src .venv/bin/python scripts/04_build_memory_conditions.py
```

当前 A-V0.2 默认不接 LLM，使用编剧式规则、多模板和话题阶段推进，保证可复现、可调试、可评测。后续 A-V0.3 再接入 LLM 做自然语言润色、风格扩展和更强的表达多样性。

当前 A-V0.3 先完成场景卡数据准备，不直接调用 LLM。后续让 DeepSeek 生成用户后续追问时，应把 `daily_scene_cards.json` 作为硬边界：开场话题由剧本定，继续几轮、能透露什么、什么时候停，由场景卡定。

生成 docx 路线 BEI 标注：

```bash
PYTHONPATH=src .venv/bin/python scripts/02_annotate_bei.py
```

生成 M0/M1/M2/M3 记忆条件：

```bash
PYTHONPATH=src .venv/bin/python scripts/04_build_memory_conditions.py
```

运行 docx 路线四条件短链测试：

```bash
PYTHONPATH=src .venv/bin/python scripts/05_run_dialogue_conditions.py \
  --message-id D01_M001 \
  --scene-followups 1 \
  --reset-conversation-log \
  --print-progress
```

M0 在运行时使用本地 LD-Agent memory-only runtime：参考官方 `leolee99/LD-Agent` 的 `Module/EventMemory.py` 与 `Module/Personas.py`，保留 short-term session bank、LLM session summary 写入 long-term event memory、Personas-style trait extraction，以及 topic-overlap/time-decay retrieval；回答生成仍使用本项目统一 LLM。默认存储后端使用 JSON snapshot 以保证实验可恢复和可审计；也可通过 `--m0-ld-agent-storage-backend chroma` 启用 ChromaDB storage backend。spaCy 不接入，中文实验继续使用可审计 topic tokenization。

运行 30 天完整 M0/M1/M2/M3 场景链路，并在自然 follow-up 后插入定向测试问题：

```bash
PYTHONPATH=src .venv/bin/python scripts/05_run_dialogue_conditions.py \
  --all-message-ids \
  --scene-followups 1 \
  --reset-conversation-log \
  --print-mode summary \
  --print-progress
```

默认输出到 `long_memory_experiment/outputs/run_YYYYMMDD_HHMM/`，包括 `run_config.json`、`conversation_log.json` 和 `responses_by_condition.json`。如果长跑中断，用同一个 `--run-dir` 加 `--resume` 继续。长跑会在每个用户 turn 完成后写 checkpoint，避免恢复时重复追加。

运行 ToM-only 对话质量评估器：

```bash
PYTHONPATH=src .venv/bin/python scripts/06_evaluate_tom.py --run-dir long_memory_experiment/outputs/run_YYYYMMDD_HHMM
PYTHONPATH=src .venv/bin/python scripts/07_judge_review.py --run-dir long_memory_experiment/outputs/run_YYYYMMDD_HHMM
PYTHONPATH=src .venv/bin/python scripts/08_report_results.py --run-dir long_memory_experiment/outputs/run_YYYYMMDD_HHMM
```

输出：

- `automatic_scores.json`
- `llm_judge_scores.json`
- `human_review_sample.xlsx`
- `final_report.md`

当前对话质量评估全面使用 ToM 标准，不再把 detail hit、记忆层级合规或旧粗评分与 ToM 融合。评分维度只包括隐含意图识别、情绪状态识别、关系期待识别、共同语境调用、陌生化错误率和自然细节调用。

## Model API

项目支持多个 OpenAI-compatible API 入口，供后续 A/B 共用。当前已配置：

- `poixe`
- `deepseek`

先复制环境变量模板：

```bash
cp .env.example .env.local
```

然后在 `.env.local` 中填入真实 key：

```bash
POIXE_API_KEY=your-poixe-api-key-here
POIXE_BASE_URL=https://api.poixe.com/v1
POIXE_MODEL=gpt-5.2

DEEPSEEK_API_KEY=your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro

LLM_PROVIDER=deepseek
```

`.env.local` 已加入 `.gitignore`，不要提交真实 key。

安装依赖后可做一次 smoke test：

```bash
.venv/bin/pip install openai
PYTHONPATH=src .venv/bin/python scripts/poixe_smoke_test.py
```

共享客户端位于 `src/long_memory_test/llm.py`。后续 A 的文本润色、运行时记忆写入和对话实验都应通过这个入口读取模型配置。当前默认 provider 是 DeepSeek：

```bash
LLM_PROVIDER=deepseek
```

DeepSeek 官方 API 使用 OpenAI-compatible 格式，默认 base URL 为 `https://api.deepseek.com`。当前默认模型使用 `deepseek-v4-pro`，也就是官方价格表里当前价格更高的 DeepSeek 模型。

如需临时切换到 Poixe，将本地 `.env.local` 中的 `LLM_PROVIDER` 改为：

```bash
LLM_PROVIDER=poixe
```

早期 Letta pilot 代码已归档到 `src/long_memory_test/legacy/letta_memory_legacy.py`，不参与正式实验。

## 项目结构

```text
data/config/
  persona.json
  life_domains.json
  event_templates.json
  user_actor.json
  conversation_expansion_policy.json
  probe_question_policy.json
scripts/
  generate_timeline.py
  generate_daily_user_messages.py
  generate_daily_scene_cards.py
  generate_probe_question_plan.py
  poixe_smoke_test.py
src/long_memory_test/agents/
  event_stream_generator.py
  daily_message_generator.py
  daily_scene_card_generator.py
  probe_question_generator.py
src/long_memory_test/memory/
  ld_agent_runtime.py
  schema.py
src/long_memory_test/
  llm.py
  letta_memory.py  # archived compatibility wrapper only
sample_output/
  timeline.json
  daily_user_message.json
  daily_scene_cards.json
  probe_question_plan.json
  a_script_plan.json
```

## ToM 对话质量评测

当前对话质量不再使用旧的 detail-hit 粗评分作为主标准，而是使用 ToM-only 评估。ToM 评估只看模型是否理解用户话语背后的心理状态和关系期待。

ToM-only 维度：

- 隐含意图识别：是否听出用户真正想表达什么。
- 情绪状态识别：是否识别疲惫、失落、自我怀疑、担心被遗忘等状态。
- 关系期待识别：是否意识到用户期待的是熟悉 AI 朋友，而不是陌生客服。
- 共同语境调用：是否自然调用此前形成的共同处理方式。
- 陌生化错误率：是否出现客服式、过度亲密、角色化或要求用户重新解释历史。
- 自然细节调用：是否把关键细节用于理解心理状态，而不是机械背记忆。

当前 ToM-only 评估器位于 `src/long_memory_test/evaluation/tom_quality_evaluator.py` 和 `scripts/evaluate_tom_quality.py`。旧 `detail_hit_evaluator.py` 仅作为历史 triage 工具保留，不作为当前对话质量结论。

## 下一步

下一阶段建议把 A-V0.3 场景卡接入 M0/M1 对话 probe：开场消息仍来自剧本，后续用户追问由 DeepSeek 在 `daily_scene_cards.json` 限制内生成。然后实现 B-V0.1：读取对话日志，根据 M0/M1/M2/M3 权限判断应该读取什么记忆、写入什么记忆，以及哪些内容不应该被记住。
