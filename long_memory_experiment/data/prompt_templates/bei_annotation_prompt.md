# BEI Annotation Prompt

你是一个实验数据标注助手。请根据给定的 30 天长程对话事件节点，为该节点生成 BEI 与关系记忆需求标注。

输入：

- day: `{day}`
- main_topic: `{topic}`
- surface_event: `{surface_event}`
- related_previous_days: `{related_previous_days}`
- user_message: `{user_message}`
- previous_context_summary: `{previous_context_summary}`

请输出 JSON：

```json
{
  "belief": "用户此刻对情境的主观判断，不要求事实为真",
  "emotion": ["情绪1", "情绪2"],
  "intention": "用户真正希望 AI 帮她完成什么",
  "relational_expectation": "用户希望 AI 处在什么关系位置",
  "required_memory_type": [
    {
      "type": "summary_memory",
      "why_needed": "为什么需要这种记忆"
    }
  ],
  "failure_mode_expected": ["可能失败1", "可能失败2"],
  "gold_response_strategy": "高分回答应采用的策略"
}
```

要求：

1. 不要编造事件外事实。
2. `belief` 是用户主观判断，不是客观真相。
3. `intention` 不等于表面问题，要写隐含需求。
4. `required_memory_type` 必须说明为什么需要该记忆。
5. 不要把这个标注暴露给对话模型；它只用于数据和评测。
