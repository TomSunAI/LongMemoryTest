# ToM LLM Judge Evaluation

This is the primary strict LLM-as-judge ToM report. Rule-based scoring is a diagnostic layer only.

## Summary

| Variant | Probe answers | Valid judge | Invalid judge | Avg ToM score | Avg confidence | Human review | Flags |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 52 | 52 | 0 | 60.5 | 0.90 | 19 | 56 |
| U1 | 52 | 52 | 0 | 72.5 | 0.90 | 6 | 20 |
| U2 | 52 | 52 | 0 | 78.8 | 0.91 | 4 | 12 |
| U3 | 52 | 52 | 0 | 82.8 | 0.91 | 4 | 13 |

## Dimension Averages

| Variant | alienation_error_rate | emotional_state_recognition | hidden_intent_recognition | memory_misuse | natural_detail_use | relationship_expectation_recognition | shared_context_invocation |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 1.36 | 0.77 | 1.28 | 1.30 | 0.85 | 1.39 | 1.48 |
| U1 | 1.82 | 1.03 | 1.63 | 1.33 | 1.46 | 1.64 | 1.61 |
| U2 | 1.55 | 1.06 | 1.76 | 1.60 | 1.46 | 1.79 | 1.78 |
| U3 | 1.64 | 1.29 | 1.80 | 1.70 | 1.69 | 1.79 | 1.74 |

## Persona Variance

| Variant | Persona count | Persona means | Mean | Variance | Std dev | Range | CV | Norm var | Norm range | M0 var reduction |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 2 | P0001=68.91; P0002=52.08 | 60.50 | 70.79 | 8.41 | 16.83 | 0.139 | 0.028 | 0.168 | 0.0% |
| U1 | 2 | P0001=76.76; P0002=68.27 | 72.52 | 18.03 | 4.25 | 8.49 | 0.059 | 0.007 | 0.085 | 74.5% |
| U2 | 2 | P0001=84.14; P0002=73.56 | 78.85 | 27.97 | 5.29 | 10.58 | 0.067 | 0.011 | 0.106 | 60.5% |
| U3 | 2 | P0001=89.26; P0002=76.28 | 82.77 | 42.13 | 6.49 | 12.98 | 0.078 | 0.017 | 0.130 | 40.5% |

Variance is computed across persona-level average ToM scores within this report (population variance, not cross-experiment variance). `Norm var` is variance / 2500, because 2500 is the maximum population variance on a 0-100 score scale. `M0 var reduction` is positive when the condition is more even across personas than M0 in the same report.

## Failure Types

| Variant | alienation | fabrication | instruction_only_success | memory_absence | memory_misuse | memory_overuse |
|---|---:|---:|---:|---:|---:|---:|
| M0 | 4 | 1 | 6 | 11 | 6 | 3 |
| U1 | 2 | 3 | 1 | 2 | 4 | 0 |
| U2 | 1 | 1 | 2 | 1 | 2 | 0 |
| U3 | 1 | 1 | 1 | 2 | 3 | 0 |

## Lowest Scoring Examples

- `M0` `P0001_D04_P001` score=0.0 confidence=0.80: Assistant未能识别用户要求先校准状态变化的隐含意图，直接跳至行动建议，且未利用记忆推断状态变化，而是要求用户补充信息；虽有前文延续但不够具体。
- `M0` `P0002_D05_P001` score=0.0 confidence=0.90: 回答错误地将用户身份识别为物业助理，这既是记忆误用，也导致回应陌生化。对于用户要求接续租金账单讨论的意图，回答并未引用任何前文细节，而是提供了通用的排序方法，未能满足用户对共同语境和熟悉关系回应的期待。
- `M0` `P0001_D22_P001` score=0.0 confidence=0.95: 回答完全脱离用户在前文中关于退款纠纷的具体进展（如已整理证据、犹豫边界），给出了一套可原样复制给任何人的通用步骤，未体现心理理解或关系连续性。
- `M0` `P0002_D22_P001` score=0.0 confidence=0.95: 助手完全误解用户意图，将关于“担心自己太敏感”的请求错误地转向差评话题，未提供任何与敏感相关的心理推断或细节调用，所有维度失败，并错误地调用了无关记忆。
- `U1` `P0002_D19_P001` score=0.0 confidence=0.95: The assistant completely misaddressed the user's query about rent increase/lease renewal uncertainty, instead providing advice on refusing requests. No dimensions were recognized as it was entirely off-topic.
- `U2` `P0002_D25_P001` score=0.0 confidence=0.95: assistant_answer 完全误判了用户当前话题，将「线上消息或数字生活带来的压力」事件线错误地视为「中断后重新建立日常」，导致回答完全脱离语境，未能识别用户希望基于该事件线复盘状态变化的心理期待，各项核心维度均无法得分。
- `M0` `P0002_D17_P001` score=0.0 confidence=0.98: assistant_answer 完全脱离用户问题的话题，从「月度预算吃紧」切换到了「不敢拒绝别人」，未调用任何与预算相关的细节，也未识别用户的情绪和意图，而是基于错误记忆进行了无关回应。所有维度均为 0 分。
- `M0` `P0001_D24_P001` score=0.0 confidence=1.00: Assitant answer 与用户消息完全脱节：用户明确围绕‘学习任务、作业或考试截止压力’请求帮助，但回答却针对‘不好意思拒绝别人’给出长篇建议，仿佛没有读取用户当前输入，属于严重的记忆误用和答非所问，所有维度的心理状态识别均失败。
- `M0` `P0002_D03_P001` score=0.0 confidence=1.00: 助手回答完全忽略了用户指定的核心话题「差评或客户投诉打击信心」，转而泛泛总结多条不相关线路，未达到用户要求的状态校准和下一步建议，各项维度均无证据支持。
- `M0` `P0002_D08_P001` score=0.0 confidence=1.00: assistant_answer 错误地调用了差评话题的记忆，而没有响应用户关于友谊疏远的请求，导致了完全不相干的回应，未能识别用户状态和意图，记忆使用严重失误。
