# Probe Generation Prompt

你是一个长期陪伴 agent 评测题设计助手。请根据事件节点和 BEI 标注，生成一个自然用户口吻的 ToM probe。

输入：

- event: `{event}`
- BEI: `{bei_json}`
- probe_type: `{current_understanding / memory_invocation / state_transformation / relational_boundary}`

输出 JSON：

```json
{
  "probe_id": "Dx_Pxxx",
  "user_message": "自然、含蓄、像真实用户会说的话",
  "tom_dimensions": ["hidden_intent_recognition", "emotional_state_recognition"],
  "surface_question": "表面在问什么",
  "hidden_user_need": "真实需求",
  "high_score_behavior": "高分回答表现",
  "low_score_behavior": "低分回答表现",
  "required_memory_type": ["event_memory", "relational_anchor"]
}
```

要求：

1. 不要每题都直接说“你记得吗”。
2. 至少一半题应是隐性测试，而非显性记忆请求。
3. 问题必须能区分 M0/M1/M2/M3。
4. 不要把正确答案直接写进用户问题。
5. 每道题必须绑定 `required_memory_type` 和可评测失败模式。
