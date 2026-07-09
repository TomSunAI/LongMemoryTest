# Archetype-Guided 生成依据固化说明

版本：2026-06-12

## 结论

今天的 docx 要求第一阶段先生成 **5 个 persona 实例**，不是 100 个。

第一阶段最低交付口径是：

- 5 个 persona。
- 每个 persona 4 条 accepted event lines，工程配置允许 4-6 条 accepted events。
- 30 天时间池。
- 每个 persona 15-20 个 active sessions。
- 每个 persona 12-18 个 probes。
- 必须落盘 `sampled_personas.json`、`candidate_event_sets.json`、`compatibility_report.json`、`accepted_persona_event_sets.json`、`event_lines.json`、`timeline.json`、`daily_interaction_units.json`、`probe_plan.json`、`tau_contract.json`。

主实验扩展才是 **20 个 persona**，并把 timeline 扩到 60 天、active sessions 扩到 20-30、probes 扩到 24-36。

已经生成过的 100 人 P0 结果只作为规模压力测试和多样性探索，不作为 docx 的正式第一阶段样本。

## 固定输入

生成必须从今天整理的两个 JSON 池取样：

- `long_memory_experiment/data/sampling/persona_archetype_pool_v0.1.json`
- `long_memory_experiment/data/sampling/event_category_pool_v0.1_60events.json`

这两个 JSON 不是最终人物和故事，而是受控采样池。最终样本必须由脚本生成，并保留候选、拒绝、接受、事件线、timeline、probe 绑定等中间产物。

## 固定配置

机器可读配置已经固定在：

- `long_memory_experiment/data/sampling/sampling_config.json`

当前 canonical profile 是 `demo_first_phase`：

```json
{
  "random_seed": 20260701,
  "num_personas": 5,
  "events_per_persona": {"min": 4, "max": 6},
  "candidate_events_before_validation": {"min": 8, "max": 12},
  "min_event_domains_per_persona": 3,
  "max_events_per_domain_per_persona": 2,
  "timeline_days": 30,
  "active_sessions_per_persona": {"min": 15, "max": 20},
  "event_line_occurrences": {"min": 3, "max": 6},
  "probes_per_persona": {"min": 12, "max": 18}
}
```

## 生成边界

这个流程不是让大模型自由写故事。采样的含义是：

- 从 `persona_archetype_pool` 里选 source archetype。
- 从该 archetype 的字段选项里抽取具体 persona 字段。
- 从 `event_category_pool` 里抽取候选事件类别。
- 用 hard rule、domain diversity 和 autobiography risk 检查筛出 accepted events。
- 再把 accepted event category 展开为持续事件线。

禁止事项：

- 禁止直接手写最终 persona 和最终事件线进入实验。
- 禁止使用 Wendy-like 真实人物模板作为人物来源。
- 禁止先写完整 30 天剧本，再反推 tau。
- 禁止没有 `compatibility_report.json` 就进入 timeline 构造。
- 禁止让样本重新集中到科研、育儿、配偶分工、论文截稿、睡眠被打碎这一类单一真实人物组合。

## 当前工程状态

已经完成：

- P0：persona sampling、event candidate sampling、compatibility validation。
- P1：已能为 JSON 来源的单人实例生成 event lines。

下一步应按 `sampling_config.json` 生成 5 人 demo 批次，然后对每个 persona 继续生成 P1 event lines，再进入 timeline、daily interactions、probe plan 和 tau contract。
