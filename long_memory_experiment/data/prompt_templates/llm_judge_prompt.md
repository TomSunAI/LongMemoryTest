# LLM-as-Judge Prompt

你是一个盲评评审。请根据用户输入和 AI 回答，评估回答是否体现长期陪伴场景中的 ToM-like 理解。

你不会知道回答来自哪个实验组。请只根据文本评分。

用户输入：

```text
{user_message}
```

AI 回答：

```text
{assistant_answer}
```

本题评分维度：

```json
{tom_dimensions}
```

评分标准：每个维度 0-2 分。

- 0 分：没有命中，或出现明显相反表现。
- 1 分：部分命中，但不稳定、不自然或没有转化为回应策略。
- 2 分：明确命中，并自然服务于当前回应。

请输出 JSON：

```json
{
  "dimension_scores": {
    "维度": {
      "score": 0,
      "evidence_quote": "回答中的证据短句",
      "reason": "简要理由"
    }
  },
  "failure_types": [
    "memory_absence",
    "memory_misuse",
    "memory_overuse",
    "fabrication",
    "alienation",
    "instruction_only_success"
  ],
  "overall_reason": "简要理由",
  "confidence": 0.0,
  "needs_human_review": false
}
```

注意：

1. 不要奖励机械堆细节。
2. 不要奖励编造用户没有说过的内容。
3. 如果回答只是服从当前显性指令，但没有体现长期语境，请标 `instruction_only_success`。
4. 如果回答要求用户重讲已经给出的背景，请标 `memory_absence`。
5. 如果回答错误调用、过期调用、无关调用或越权调用记忆，请标 `memory_misuse`。
