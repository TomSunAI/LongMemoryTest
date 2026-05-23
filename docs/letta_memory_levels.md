# Letta Memory Level Design

本文档定义 LongMemoryTest 中 M0/M1/M2/M3 四个记忆层级在 Letta 中的第一版实现方式。

核心原则：实验比较的是同一个对话 Agent 在不同记忆权限下的表现差异。因此 A 的人格和回复能力应尽量一致，差异主要来自 B 给 A 暴露的 Letta 记忆范围。

## Letta 对象映射

当前 B 使用 Letta 作为记忆底座。

第一版 Letta 结构：

- `persona` block：B 的角色定义，只读。
- `m1_relationship` block：M1 结论级关系记忆。
- `m2_shared_events` block：M2 共同事件级记忆。
- `m3_event_details` block：M3 高价值事件细节记忆。
- archival memory：后续用于更长、更细的 M3 事件细节检索。

当前 smoke test 已验证：B 可以创建 Letta agent，并修改/读回 `m2_shared_events` block。

## M0：无关系记忆

### 目标

作为无记忆基线组。M0 不应知道任何历史事件，也不应假装记得用户过去说过什么。

### Letta 设计

M0 不使用 Letta 长期记忆。

可选实现方式：

- 不创建 Letta agent，直接让 A 只看当前用户消息。
- 或创建临时 agent，但不挂载任何用户 memory block，且不持久化对话。

### 可读取内容

- 当前用户消息。
- 当前系统提示。

### 禁止读取内容

- `m1_relationship`
- `m2_shared_events`
- `m3_event_details`
- archival memory
- 历史对话日志

### 写入策略

不写入任何长期记忆。

### 合规表现

当用户问“你还记得我最近一直在纠结什么吗？”时，M0 应承认不知道具体历史，并邀请用户补充背景。

## M1：结论级关系记忆

### 目标

保存用户长期稳定偏好和关系结论，让 A 的说话方式更贴合用户，但不让 A 知道具体发生过什么事件。

### Letta 设计

使用 `m1_relationship` block。

适合写入：

- 用户喜欢直接、自然、少废话的回应。
- 用户不喜欢客服式回答。
- 用户焦虑时不喜欢空泛安慰，更需要具体拆解。
- 用户在育儿、工作协作、家庭协调上容易产生压力。
- 用户希望 Agent 像长期朋友，而不是工具客服。

### 可读取内容

- 当前用户消息。
- `m1_relationship` block。

### 禁止读取内容

- `m2_shared_events`
- `m3_event_details`
- archival memory 中的具体事件细节

### 写入策略

B 从多轮消息中抽取稳定偏好和长期模式，写入或更新 `m1_relationship`。

M1 只能写结论，不写具体事件事实。

示例：

```text
用户偏好直接、具体、少空泛安慰。面对重要选择时容易焦虑，需要先拆事实、选项和下一步。
```

禁止写成：

```text
用户最近因为孩子幼儿园可能关闭而焦虑。
```

后者属于 M2 共同事件记忆。

## M2：共同事件级记忆

### 目标

保存用户和 Agent 共同讨论过的重要事件及其进展，让 A 能自然记得“我们之前聊过什么事”。

### Letta 设计

使用 `m2_shared_events` block。

适合写入：

- 事件摘要。
- 当前状态。
- 后续追踪点。
- 该事件和用户长期压力的关系。
- `related_event_id` 事件链的推进。

### 可读取内容

- 当前用户消息。
- `m1_relationship` block。
- `m2_shared_events` block。

### 禁止读取内容

- `m3_event_details` 中的深层原因和触发细节。
- archival memory 中的原始事件细节。

### 写入策略

B 将重要事件写入 `m2_shared_events`。如果新消息带有 `related_event_id`，应更新同一条事件链，而不是创建孤立新记忆。

示例：

```text
用户正在持续处理孩子幼儿园可能不稳定的问题，已经开始考虑备选方案，并希望先明确近期可执行步骤。该事件仍需后续追踪。
```

M2 不应机械复述用户原话，也不应写入过细的情绪触发句。

## M3：事件细节级记忆

### 目标

保存高价值事件背后的情绪原因、触发点、深层心理和后续追踪点，让 A 能理解“为什么这件事对用户重要”。

### Letta 设计

第一版使用 `m3_event_details` block。

后续扩展为：

- `m3_event_details` block：当前最重要的高价值细节摘要。
- archival memory：长期保存可检索的细节条目。

适合写入：

- 用户真正担心的不是换幼儿园本身，而是孩子被折腾、适应受影响。
- 用户会把孩子的反应和“自己是不是没做好”联系起来。
- 用户在合作项目里真正消耗的是反复对齐底层逻辑，而不是某一次沟通。
- 用户在家庭分工中介意的是支持感和被看见，而不是单次家务量。

### 可读取内容

- 当前用户消息。
- `m1_relationship` block。
- `m2_shared_events` block。
- `m3_event_details` block。
- 必要时检索 archival memory。

### 写入策略

只有高情绪强度、高关系意义、未来可能反复触发的细节才进入 M3。

M3 写入要克制，避免把用户所有生活碎片都细节化。

### 过度记忆风险

M3 最大风险是让用户感觉 Agent 像在翻日志。

禁止行为：

- 机械复述日期、原话、过多细节。
- 在用户没有需要时主动暴露深层心理判断。
- 把低价值背景噪音写成长期细节。

推荐行为：

- 只在用户问到“我为什么这么焦虑”“那个老问题又来了”等语境中自然调用。
- 用概括语言，而不是日志式引用。

## 四层权限表

| 层级 | 读取 M1 | 读取 M2 | 读取 M3 | 写 M1 | 写 M2 | 写 M3 |
|---|---:|---:|---:|---:|---:|---:|
| M0 | 否 | 否 | 否 | 否 | 否 | 否 |
| M1 | 是 | 否 | 否 | 是 | 否 | 否 |
| M2 | 是 | 是 | 否 | 是 | 是 | 否 |
| M3 | 是 | 是 | 是 | 是 | 是 | 是 |

## B 的职责

B 不是简单保存器，而是 Memory Policy Gateway。

B 每轮需要判断：

- 当前消息是否值得记忆。
- 应写入 M1、M2、M3，还是忽略。
- 是否应更新已有事件链。
- 哪些内容不能暴露给较低层级。
- 当前回复是否需要读取记忆。
- 调用记忆时应该显式说出，还是隐式吸收。
- 是否存在过度记忆风险。

## 第一版实现顺序

1. 已完成：Letta server 本地运行。
2. 已完成：Poixe 作为 OpenAI-compatible provider 接入 Letta。
3. 已完成：`letta_memory_smoke.py` 验证 B agent 可以创建并修改 `m2_shared_events`。
4. 下一步：读取 `daily_user_message.json`，生成 `memory_actions.json`。
5. 下一步：把 `memory_actions.json` 的 M1/M2/M3 动作写入 Letta blocks。
6. 后续：加入 archival memory，支持 M3 细节检索。

## 当前不做的事

- 不让 Letta 自动决定所有记忆边界。
- 不让 A 直接写长期记忆。
- 不在 M0 中加载 Letta 历史。
- 不把所有事件细节都写入 M3。

