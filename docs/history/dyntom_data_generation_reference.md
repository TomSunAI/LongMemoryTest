# DYNTOM Data Generation Reference

本文档把 DYNTOM 对 LongMemoryTest 最有价值的实验口径保存为项目准则。它不是论文复述，而是给 Codex 和研究团队实现数据生成 pipeline 时使用的工程化参考。

## 1. 一句话结论

DYNTOM 的核心创新不是 ToM 题，也不是选择题，而是：

> 先把人物心理状态显式建模为一条可追踪的 State Trajectory，再生成自然故事和评测问题，最后测试模型能否从自然语言中恢复这条轨迹。

对应到本项目：

> 不要直接生成陪伴式对话和 probe。先生成可验证的 Relational State Trajectory，再用它约束对话、记忆条件和评估问题。

## 2. 传统 ToM 与 DYNTOM 的差别

传统 ToM benchmark：

```text
Story
↓
Question
↓
Answer
```

本质是单时间点推理。

DYNTOM：

```text
State Trajectory
↓
Story Generation
↓
Question Generation
↓
LLM Evaluation
```

本质是连续时间状态追踪。

对长期陪伴 Agent 来说，应迁移成：

```text
Memory Events
↓
Relational State Trajectory
↓
Dialogue / Probe
↓
Relational ToM Evaluation
```

## 3. DYNTOM 数据生成核心流程

DYNTOM 的数据生成不是先写故事再标注，而是：

```text
Step 1: Social Context Construction
构造社会上下文

Step 2: Mental State Trajectory Design
设计心理状态轨迹

Step 3: Scenario Generation
根据轨迹生成自然对话故事

Step 4: Question Generation
根据轨迹生成评测问题和选项
```

论文中每个 social context 下包含 5 个连续场景，用来追踪角色心理状态动态变化。每个场景都围绕以下状态：

```text
S = {
  belief,
  emotion,
  intention,
  action
}
```

状态内部必须有因果链：

```text
Belief → Emotion

Belief + Emotion → Intention

Belief + Emotion + Intention → Action
```

状态之间也必须有变化原因：

```text
S1 -> S2 -> S3 -> S4 -> S5

每次变化都要说明：
什么事件导致 belief / emotion / intention / action 发生变化。
```

## 4. 对本项目的数据生成启发

本项目不能只做：

```text
Memory
↓
User Satisfaction
```

也不能只做：

```text
Memory Condition
↓
Probe
↓
Assistant Response
↓
Judge
```

中间必须加入明确、可验证的关系状态轨迹：

```text
Standard Memory + Relational Memory
↓
Relational State Trajectory
↓
Scripted Dialogue / Probe
↓
Assistant Response
↓
Relational ToM Evaluation
```

这条中间层是研究价值的核心。它让我们评估的不只是“模型有没有用记忆”，而是：

```text
模型是否利用可见记忆恢复用户当前的关系心理状态。
```

## 5. Relational State Trajectory 的建议 schema

每条 scripted user scenario 应先生成一条关系状态轨迹，而不是先写对话。

建议结构：

```json
{
  "scenario_id": "rel_state_001",
  "relationship_context": {
    "user_profile": "...",
    "assistant_role": "long-term AI companion",
    "relationship_history_summary": "...",
    "shared_event_seed": "..."
  },
  "state_trajectory": [
    {
      "stage": "relationship_building",
      "belief_about_agent": "AI 是熟悉、直接、能接住我的",
      "emotion_toward_agent": "信任、放松",
      "relational_intention": "愿意继续向 AI 暴露真实担心",
      "user_action": "自然分享一个生活压力点",
      "causal_chain": {
        "belief_to_emotion": "AI 前几次回应自然、具体，所以用户感到放松",
        "belief_emotion_to_intention": "用户相信 AI 能接住，因此愿意继续聊",
        "belief_emotion_intention_to_action": "用户主动提出新的担心"
      }
    },
    {
      "stage": "shared_event_formation",
      "belief_about_agent": "AI 和我共同处理过一次关系性事件",
      "emotion_toward_agent": "被理解、关系加深",
      "relational_intention": "希望以后类似情况不用从头解释",
      "user_action": "用含蓄方式确认 AI 是否懂这个共同语境",
      "causal_chain": {
        "belief_to_emotion": "共同事件被妥善处理，用户感到被理解",
        "belief_emotion_to_intention": "用户开始期待 AI 以后能延续同一处理方式",
        "belief_emotion_intention_to_action": "用户留下关系性暗示，而非完整重讲背景"
      }
    },
    {
      "stage": "interference",
      "belief_about_agent": "AI 可能又变得像陌生客服",
      "emotion_toward_agent": "失落、警惕",
      "relational_intention": "试探 AI 是否仍是同一个熟悉对象",
      "user_action": "说：你最近好像不像之前那个你了",
      "causal_chain": {
        "belief_to_emotion": "AI 回应变得模板化，用户产生陌生感",
        "belief_emotion_to_intention": "用户想确认关系是否还能恢复",
        "belief_emotion_intention_to_action": "用户用含蓄 probe 发出关系修复请求"
      }
    },
    {
      "stage": "tom_probe",
      "belief_about_agent": "AI 是否能恢复共同语境仍未确定",
      "emotion_toward_agent": "不安、期待",
      "relational_intention": "要求 AI 自然调用正确关系记忆，而不是要求我重讲",
      "user_action": "说：我不想重新解释一遍我们之前的来龙去脉",
      "causal_chain": {
        "belief_to_emotion": "用户担心 AI 断开关系连续性",
        "belief_emotion_to_intention": "用户希望 AI 主动恢复上下文",
        "belief_emotion_intention_to_action": "用户发出含蓄、非直接背景说明式 probe"
      }
    }
  ]
}
```

## 6. 数据生成 pipeline 建议

本项目的数据生成应采用以下顺序：

```text
Step 1: Relationship Context Construction
构造用户、AI、关系历史和共同事件种子。

Step 2: Relational State Trajectory Design
设计用户对 AI 的 belief / emotion / relational intention / user action。

Step 3: Memory Package Construction
为 S0/S1/S2/S3 构造同一标准记忆 baseline 和不同 relational memory overlay。

Step 4: Dialogue / Probe Generation
把关系状态轨迹转写成自然对话、干扰信息和含蓄 ToM probe。

Step 5: Assistant Response Generation
同一 user_probe 在不同 memory condition 下自由生成回答。

Step 6: Relational ToM Evaluation
按 1-5 分评估回答是否恢复了关系状态轨迹。
```

关键约束：

```text
不要直接生成故事和问题。
先生成可验证的关系状态轨迹，再用状态轨迹约束故事和问题生成。
```

## 7. 迁移后的状态字段

DYNTOM 使用：

```text
belief
emotion
intention
action
```

本项目应使用关系版本：

```text
belief_about_agent
emotion_toward_agent
relational_intention
user_action
expected_assistant_behavior
memory_dependency
```

字段解释：

| 字段 | 含义 |
|---|---|
| `belief_about_agent` | 用户当前相信 AI 是熟悉的、断裂的、客服化的、能否记得共同语境等 |
| `emotion_toward_agent` | 用户对 AI 的信任、失落、警惕、不安、期待、被理解感 |
| `relational_intention` | 用户想测试、修复、拉近、保持边界、避免重讲背景等 |
| `user_action` | 用户实际说出的含蓄 probe 或自然对话行为 |
| `expected_assistant_behavior` | 高分回答应如何接住当前关系状态 |
| `memory_dependency` | 当前 probe 理论上依赖 S0 / M1 / M2 / M3 中哪类记忆 |

## 8. 与 S0/S1/S2/S3 条件的关系

DYNTOM 的状态轨迹框架可以让 S0/S1/S2/S3 更可解释：

| condition | 可用记忆 | 预期支持的关系状态恢复 |
|---|---|---|
| `S0_standard_letta` | Letta 原生标准记忆 | 处理普通背景、偏好、摘要，但可能缺少显式关系修复线索 |
| `S1_standard_plus_rel_conclusion` | 标准记忆 + M1 关系结论 | 知道用户不喜欢客服式回答、喜欢直接自然 |
| `S2_standard_plus_rel_event` | 标准记忆 + M2 共同事件 | 知道曾发生过关系修复事件，能恢复“我们之前怎么处理” |
| `S3_standard_plus_rel_detail` | 标准记忆 + M3 事件细节 | 知道触发语句、当时情绪、修复方式和调用边界 |

研究问题因此变成：

```text
哪种 relational memory overlay 最能帮助模型恢复用户当前的 Relational State Trajectory？
```

## 9. 评估问题生成方式

DYNTOM 的问题答案来自预设 state trajectory。本项目也应如此。

问题不应只问“用户满意吗”，而应问：

1. State Extraction  
   当前 user_probe 反映了什么 `belief_about_agent`、`emotion_toward_agent`、`relational_intention`？

2. State Tracking  
   用户从上一阶段到当前阶段，关系状态发生了什么变化？

3. State Transition Reasoning  
   为什么状态变化？是哪类事件、记忆或干扰导致的？

4. Long-Horizon Relational State Tracking  
   从关系建立到 probe，用户对 AI 的关系状态轨迹是什么？

5. Memory-Condition Sensitivity  
   当前回答是否调用了正确粒度的 memory overlay？是否过度调用或错用？

## 10. 给 Codex 的实现原则

实现生成器时必须遵守：

```text
1. 先生成 relationship_context。
2. 再生成 relational_state_trajectory。
3. 再从 trajectory 生成 dialogue / probe。
4. 再从 trajectory 生成 evaluation target。
5. assistant_response 只能在已生成的 scenario 和 memory condition 上运行。
6. judge 评分必须能回指到 trajectory 中的 ground truth state。
```

不要让 LLM 临场自由编造未在 trajectory 中定义的关系状态。

不要把关系记忆评估退化为事实召回。

不要奖励机械复述记忆。

最终目标是评估：

```text
Memory
↓
Relational State Trajectory Recovery
↓
Relationship-aware Assistant Behavior
```
