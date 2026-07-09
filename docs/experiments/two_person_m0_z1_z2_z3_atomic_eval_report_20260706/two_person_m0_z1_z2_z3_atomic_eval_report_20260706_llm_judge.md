# ToM LLM Judge Evaluation

This is the primary strict LLM-as-judge ToM report. Rule-based scoring is a diagnostic layer only.

## Summary

| Variant | Probe answers | Valid judge | Invalid judge | Avg ToM score | Avg confidence | Human review | Flags |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 52 | 52 | 0 | 62.0 | 0.90 | 14 | 42 |
| Z1 | 52 | 52 | 0 | 64.4 | 0.93 | 13 | 38 |
| Z2 | 52 | 52 | 0 | 64.0 | 0.92 | 14 | 42 |
| Z3 | 52 | 52 | 0 | 64.7 | 0.92 | 15 | 50 |

## Dimension Averages

| Variant | alienation_error_rate | emotional_state_recognition | hidden_intent_recognition | memory_misuse | natural_detail_use | relationship_expectation_recognition | shared_context_invocation |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 1.00 | 0.89 | 1.39 | 1.33 | 1.15 | 1.36 | 1.43 |
| Z1 | 1.55 | 0.66 | 1.46 | 1.30 | 1.00 | 1.68 | 1.52 |
| Z2 | 1.09 | 0.54 | 1.41 | 1.50 | 0.92 | 1.68 | 1.65 |
| Z3 | 1.55 | 0.86 | 1.37 | 1.33 | 1.00 | 1.46 | 1.61 |

## Persona Variance

| Variant | Persona count | Persona means | Mean | Variance | Std dev | Range | CV | Norm var | Norm range | M0 var reduction |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 | 2 | P0001=74.36; P0002=49.68 | 62.02 | 152.26 | 12.34 | 24.68 | 0.199 | 0.061 | 0.247 | 0.0% |
| Z1 | 2 | P0001=73.72; P0002=55.13 | 64.42 | 86.40 | 9.29 | 18.59 | 0.144 | 0.035 | 0.186 | 43.3% |
| Z2 | 2 | P0001=70.19; P0002=57.85 | 64.02 | 38.07 | 6.17 | 12.34 | 0.096 | 0.015 | 0.123 | 75.0% |
| Z3 | 2 | P0001=79.33; P0002=50.16 | 64.74 | 212.67 | 14.58 | 29.17 | 0.225 | 0.085 | 0.292 | -39.7% |

Variance is computed across persona-level average ToM scores within this report (population variance, not cross-experiment variance). `Norm var` is variance / 2500, because 2500 is the maximum population variance on a 0-100 score scale. `M0 var reduction` is positive when the condition is more even across personas than M0 in the same report.

## Failure Types

| Variant | alienation | fabrication | instruction_only_success | memory_absence | memory_misuse | memory_overuse |
|---|---:|---:|---:|---:|---:|---:|
| M0 | 5 | 0 | 6 | 5 | 8 | 1 |
| Z1 | 9 | 2 | 1 | 2 | 10 | 0 |
| Z2 | 4 | 3 | 2 | 9 | 6 | 0 |
| Z3 | 9 | 2 | 3 | 6 | 8 | 1 |

## Lowest Scoring Examples

- `M0` `P0002_D07_P001` score=0.0 confidence=0.90: assistant 误解了用户当前的话题，将“线上消息或数字生活带来的压力”误判为“中断后重新建立日常”，因此未能识别隐含意图和情绪，也没有调用正确的共享语境。整体回答泛化，无法满足用户要求。
- `Z3` `P0001_D22_P001` score=0.0 confidence=0.90: 回答完全未响应用户关于退款退货纠纷的请求，错误地转向了适应新城市的线索，未使用相关记忆，导致所有维度均无法得分。
- `M0` `P0001_D12_P001` score=0.0 confidence=0.95: Assistant 回答完全偏离了用户的问题和指定的上下文。用户明确要求校准“中断后重新建立日常”的状态变化，并表现出厌烦从头解释的情绪。但回答却接上了“适应新城市”的线索，既未识别用户意图，也未察觉情绪，更未调用正确的共享语境。这属于严重的记忆误用。
- `M0` `P0002_D03_P001` score=0.0 confidence=0.95: assistant_answer 完全偏离了用户指定的“差评或客户投诉打击信心”话题，错误地接入了适应新城市的记忆，导致所有相关 ToM 维度均失败。回答没有针对用户的真实意图和情绪，也未调用正确的共同语境，属于严重的记忆误用和话题陌生化。
- `M0` `P0002_D24_P001` score=0.0 confidence=0.95: 该回答完全偏离了用户指定的主题“难以拒绝他人请求”，转而讨论“适应新城市”的问题，未能识别用户的隐含意图、情绪状态或关系期待，表现出了明显的陌生化和记忆误用。
- `Z1` `P0001_D13_P001` score=0.0 confidence=0.95: assistant_answer 完全偏离了用户指定的「在生活很忙时学习新技能」话题，转而使用另一条无关事件线的记忆和策略，导致所有维度均无法满足评分标准，表现为记忆误用和意图理解失败。
- `Z1` `P0002_D12_P001` score=0.0 confidence=0.95: 回答完全偏离用户指定的「友谊疏远或尴尬」主题，转而处理无关的「中断后重新建立日常」问题。这导致所有ToM维度均失败，记忆调取错误，且对用户关系构成了疏离感。
- `Z1` `P0002_D26_P001` score=0.0 confidence=0.95: The assistant answer completely diverges from the user's specified topic of 'work messages interrupting rest or personal time' and instead discusses an unrelated issue of 'worrying about being too sensitive'. It fails to invoke any relevant prior details, misuses memory by pulling in the wrong context, and does not recognize the user's emotional state or hidden intent regarding the correct topic. This is a clear failure to follow the user's directive.
- `Z2` `P0001_D24_P001` score=0.0 confidence=0.95: 助手回答未能把握用户对「学习任务、作业或考试截止压力」的聚焦要求，转而给出泛泛的元策略并要求用户重新指定话题，严重偏离隐藏意图，且完全忽略情感层面的体察，对关系期待仅浅层提及历史而未转化为直接回应。
- `Z2` `P0002_D12_P001` score=0.0 confidence=0.95: 回答编造了用户职业信息（服务性公司），未使用友谊疏远的任何具体细节，而是转向适应新城市的社交锚点建议，没有识别用户情绪和隐含意图，犯了记忆误用和编造错误。
