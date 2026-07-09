# Docx-Route Memory Condition Structure

本文档记录当前正式路线的记忆条件定义。项目已经切到《长期关系记忆实验 30 天脚本实现方案（细化版）M1 修正版》：不再使用 `S0/S1/S2/S3` 非累积 overlay 作为主实验口径，也不再把 `M0` 定义为无长期记忆。

核心结论：`M0` 是 generic agent memory baseline；`M1/M2/M3` 是在普通记忆基线之上的累计关系性记忆层级。

## 1. 当前 Letta 状态

Letta 仍可作为 B memory agent 底座，入口保留：

- `src/long_memory_test/letta_memory.py`
- 默认 Letta base URL：`http://127.0.0.1:8283`
- 默认模型：`openai-proxy/deepseek-v4-pro`
- 默认 embedding：`letta/letta-free`

当前已有 blocks：

| block label | docx 路线用途 | 状态 |
|---|---|---|
| `persona` | B 的角色定义，只读 | 已实现 |
| `m1_relationship` | M1 结论级关系记忆 | 已实现 |
| `m2_shared_events` | M2 摘要级事件线/状态变化记忆 | 已实现，smoke test 已验证 |
| `m3_event_details` | M3 细节级关系锚点 | 已实现 |

当前第一版四条件 runner 使用 `sample_output/memory_conditions.json` 作为受控 memory payload，不直接依赖 Letta 在线读写。后续可以把该 JSON 中的 payload 写入 Letta blocks。

## 2. 正式实验条件

| condition | 名称 | 能读什么 | 不能读什么 | 理论用途 |
|---|---|---|---|---|
| `M0` | Generic Agent Memory Baseline | 同窗口短期上下文、普通 agent 用户画像、普通会话摘要、任务偏好 | BEI、gold strategy、人工整理的关系记忆、事件轨迹、关系锚点 | 检验 generic memory 是否足够支持长期陪伴 ToM-like interaction |
| `M1` | Conclusion-level Relational Memory | M0 + 稳定偏好、回应风格、关系期待、回应边界 | 事件摘要、日期、原话、细节场景 | 检验只记重要结论/关系画像是否足够 |
| `M2` | Summary-level Relational Memory | M1 + 关键事件线、跨天主题进展、用户状态变化、处理结果摘要 | 原话、完整历史、未经筛选细节 | 检验摘要级事件/状态记忆是否支持跨天接续 |
| `M3` | Detail-level / Relational Anchor Memory | M2 + 必要细节、共同语言、关系锚点、边界说明、误用风险 | 完整原始历史、无关私密细节、未存事实 | 检验细节级关系记忆是否提升熟悉感并降低陌生化 |

正式主实验采用累计条件：

```text
M0
M1 = M0 + conclusion-level relational memory
M2 = M1 + summary-level relational memory
M3 = M2 + detail-level relational anchor memory
```

当前 runtime 口径：`M0` 继续作为共享的 session/base memory；`M1`-`M3` 是叠加在 `M0` 之上的关系记忆 overlay。overlay 的长期存储单元显式绑定到 `event_line_id`：

- `M1` 存同一事件线上的关系结论/回应偏好总结。
- `M2` 在 M1 基础上存同一事件线的跨天进展摘要。
- `M3` 在 M2 基础上存同一事件线的关键细节锚点和边界风险。

因此 `M1`-`M3` 不是按普通 session 直接堆 turn，而是按事件线 upsert；同一 `event_line_id` 的后续轮次会更新同一条对应层级的 memory record，并保留 `source_turn_ids`。

M1/M2/M3 的总结器使用 LLM relational memory consolidation agent：

- 每个非 probe turn 写回时，LLM 分别为当前 condition 可见的层级生成结构化 JSON。
- `M1` prompt 只允许写结论级关系记忆，不写事件进展和细节锚点。
- `M2` prompt 只允许写事件线摘要，不写 raw quote 或细节锚点。
- `M3` prompt 只允许写必要细节锚点、使用边界和误用风险。
- 如果 LLM 调用失败，才降级到 deterministic fallback，并在 `memory_llm_failures` 中记录。

当前文件体系还会在每个 M1/M2/M3 runtime 目录下输出事件线主线文件：

```text
memory_runtimes/
  M1/
    event_lines/
      index.json
      <event_line_id>_<hash>.json
  M2/
    event_lines/
      index.json
      <event_line_id>_<hash>.json
  M3/
    event_lines/
      index.json
      <event_line_id>_<hash>.json
```

每个 `<event_line_id>_<hash>.json` 是一条事件线的自动归纳文件，包含该条件可见的层级内容、`source_turn_ids`、`event_stages`、观察到的 days 和 `mainline` 摘要。`summary_mode` 会标明该文件来自 `llm_event_line_memory_consolidation_rollup`、混合模式，还是 deterministic fallback。检索策略后续单独优化。

## 3. M0 不是 no-memory

旧 pilot 中的 M0 曾表示“同窗口短期上下文 + 无长期关系记忆”。该定义不再作为正式实验 baseline。

正式 `M0` 必须是强基线：

- 可以有普通 agent 框架的 user profile。
- 可以有普通 conversation summary。
- 可以有普通 task preference。
- 可以有普通 retrieved history snippets。
- 不能读取人工设计的 relational memory layer。
- 不能读取 BEI、required memory、failure mode、gold strategy。

这样才能证明：普通 memory management 仍不一定足以支持长期陪伴中的关系连续性和 ToM-like interaction。

## 4. 受控 Memory Payload 文件

当前受控记忆载荷由以下脚本生成：

```bash
PYTHONPATH=src .venv/bin/python scripts/annotate_bei.py
PYTHONPATH=src .venv/bin/python scripts/build_memory_conditions.py
```

主要产物：

- `sample_output/bei_annotations.json`
- `sample_output/memory_conditions.json`

`memory_conditions.json` 顶层结构：

```json
{
  "schema_version": "memory_conditions_v0.1_docx_route",
  "condition_specs": [],
  "default_payloads": {},
  "memory_payloads_by_message_id": {}
}
```

每个 message/probe 下都应有四组 payload：

```json
{
  "D10_P001": {
    "M0": {"memory_context": "..."},
    "M1": {"memory_context": "..."},
    "M2": {"memory_context": "..."},
    "M3": {"memory_context": "..."}
  }
}
```

## 5. 运行入口

正式四条件 runner：

```bash
PYTHONPATH=src .venv/bin/python scripts/run_dialogue_conditions.py \
  --all-message-ids \
  --scene-followups 1 \
  --probe-questions sample_output/probe_question_plan.json \
  --memory-conditions sample_output/memory_conditions.json \
  --output sample_output/m0_m1_m2_m3_dialogue_conditions.json \
  --conversation-log sample_output/conversation_log_docx_conditions.json \
  --print-mode summary \
  --print-progress
```

旧 `scripts/run_m0_m1_dialogue_probe.py` 仅保留为历史 pilot 工具。
