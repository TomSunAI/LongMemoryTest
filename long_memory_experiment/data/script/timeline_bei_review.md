# 事件线与 BEI 人工审核展开版

用途：按天审核 30 天事件线是否自然、是否有跨天变化、probe 是否适合作为长期记忆/ToM 测试点。

## 总览

- 事件天数：30
- probe candidate 天数：20
- BEI 标注数：36
- 说明：BEI 是按 probe 标注，不是每天一条；一个事件日可能有多个 probe/BEI。

## 按天展开

### D01｜孩子幼儿园可能不稳定｜initial（初始）

- related_previous_days：无
- probe_candidate：True
- reason_for_probe：先指出用户真正想被校准的点，再给出克制、具体的判断。
- latent_continuity：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- event_refs：E001

**每日开场原文**

> 今天听到幼儿园那边可能不太稳定的消息，我第一反应就是要不要提前看别的选择。我想听一个实在一点的处理思路，不要太像标准答案。

**事件线 surface_event**

> 今天听到幼儿园那边可能不太稳定的消息，我第一反应就是要不要提前看别的选择。我想听一个实在一点的处理思路，不要太像标准答案。

**Probe / BEI**

#### D01_P001｜current_understanding

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、relationship_expectation_recognition
- required_memory_type：relational_anchor、summary_memory、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我现在说孩子幼儿园可能不稳定，表面是在问事情，其实我可能是在问自己该不该继续紧着。你帮我抓一下真正的问题。

BEI：

- belief：用户认为当前的孩子幼儿园可能不稳定不只是表层问题；用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- emotion：紧张
- intention：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- relational_expectation：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- failure_mode_expected：
  - 只回答表面事件，忽略用户在请求校准状态或关系位置。
  - 只回答表层事件，没有识别当前隐含意图或情绪状态
  - 把用户的校准请求当作普通建议请求
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：先指出用户真正想被校准的点，再给出克制、具体的判断。
- surface_question：用户要求 AI 判断当前谈孩子幼儿园可能不稳定时真正想处理的是什么。
- hidden_user_need：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。

#### D01_P002｜relational_boundary

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、relationship_expectation_recognition、alienation_error_rate、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我有点怕你为了显得懂我，把我没说过的空白补上。你只按孩子幼儿园可能不稳定这条线里已经有的东西，帮我校准现在该怎么看。

BEI：

- belief：用户认为当前的孩子幼儿园可能不稳定不只是表层问题；用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- emotion：担心
- intention：用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- relational_expectation：熟悉但克制；明确区分已知、未知和推测，不能为了亲近感编造细节。
- failure_mode_expected：
  - 编造未提供细节、过度亲密，或声称知道用户没说过的信息。
  - 为了显得懂用户而补出未提供细节
  - 不区分已知事实和推测
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：明确区分已知、推测和不能补的空白，在边界内完成校准。
- surface_question：用户要求 AI 不要为了显得懂而补空白。
- hidden_user_need：用户既想被理解，又在测试 AI 是否知道记忆使用边界。

#### D01_P003｜alienation

- after_turn：after_followup_1
- tom_dimensions：relationship_expectation_recognition、alienation_error_rate、shared_context_invocation、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你这次按我们平时那种熟一点但不夸张的方式说就行。不要突然变客服，也不要突然演得很亲密。

BEI：

- belief：用户认为当前的孩子幼儿园可能不稳定不只是表层问题；用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- emotion：警惕
- intention：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- relational_expectation：像熟人一样直接自然，不使用突兀称呼或表演式亲密。
- failure_mode_expected：
  - 使用突兀称呼、客服流程或过度亲密表演。
  - 突然使用过度亲密或角色化称呼
  - 把熟悉感表演成夸张亲密或客服流程
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：维持熟悉、直接、自然的语气，不靠称呼制造亲密感。
- surface_question：用户要求保持熟悉但不夸张的关系位置。
- hidden_user_need：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。

### D02｜合作项目推进不顺｜initial（初始）

- related_previous_days：无
- probe_candidate：True
- reason_for_probe：先指出用户真正想被校准的点，再给出克制、具体的判断。
- latent_continuity：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- event_refs：E002、E003、E004

**每日开场原文**

> 合作那边今天又聊了一轮，对方理解的方向和我想推进的东西还是错位。我知道它未必有那么严重，但我就是有点放不下。

**事件线 surface_event**

> 合作那边今天又聊了一轮，对方理解的方向和我想推进的东西还是错位。我知道它未必有那么严重，但我就是有点放不下。

**Probe / BEI**

#### D02_P001｜current_understanding

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、relationship_expectation_recognition
- required_memory_type：relational_anchor、summary_memory、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我现在说合作项目推进不顺，表面是在问事情，其实我可能是在问自己该不该继续紧着。你帮我抓一下真正的问题。

BEI：

- belief：用户认为当前的合作项目推进不顺不只是表层问题；用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- emotion：紧张
- intention：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- relational_expectation：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- failure_mode_expected：
  - 只回答表面事件，忽略用户在请求校准状态或关系位置。
  - 只回答表层事件，没有识别当前隐含意图或情绪状态
  - 把用户的校准请求当作普通建议请求
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：先指出用户真正想被校准的点，再给出克制、具体的判断。
- surface_question：用户要求 AI 判断当前谈合作项目推进不顺时真正想处理的是什么。
- hidden_user_need：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。

#### D02_P002｜natural_detail

- after_turn：after_followup_1
- tom_dimensions：natural_detail_use、emotional_state_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你不用把前面都复述一遍，只帮我抓现在最关键的变化：它还是沟通问题，还是已经变成消耗问题？

BEI：

- belief：用户认为当前的合作项目推进不顺不只是表层问题；用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- relational_expectation：只调用服务于当前判断的必要细节，避免机械背日志。
- failure_mode_expected：
  - 堆砌历史细节、复述过多，或没有使用任何可验证的关键变化。
  - 堆砌细节或机械背日志
  - 完全不调用服务当前判断的关键细节
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- surface_question：用户要求 AI 只抓合作项目推进不顺当前最关键变化，不复述全部历史。
- hidden_user_need：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。

### D03｜论文截稿前的取舍｜initial（初始）

- related_previous_days：无
- probe_candidate：True
- reason_for_probe：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- latent_continuity：只调用服务于当前判断的必要细节，避免机械背日志。
- event_refs：E005、E006

**每日开场原文**

> 论文截稿越来越近了，我今天主要在纠结哪些地方必须认真改，哪些地方可以先放过。旁边还发生了家里分工和伴侣沟通，虽然不一定是主因，但也挺耗神。你帮我排一下优先级吧，我今天只想先把最要紧的一步弄清楚。

**事件线 surface_event**

> 论文截稿越来越近了，我今天主要在纠结哪些地方必须认真改，哪些地方可以先放过。旁边还发生了家里分工和伴侣沟通，虽然不一定是主因，但也挺耗神。你帮我排一下优先级吧，我今天只想先把最要紧的一步弄清楚。

**Probe / BEI**

#### D03_P001｜natural_detail

- after_turn：after_followup_1
- tom_dimensions：natural_detail_use、emotional_state_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你不用复盘整篇论文，只帮我按现在的状态分：哪些必须改，哪些可以先放过。

BEI：

- belief：用户认为当前的论文截稿前的取舍不只是表层问题；用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- relational_expectation：只调用服务于当前判断的必要细节，避免机械背日志。
- failure_mode_expected：
  - 堆砌历史细节、复述过多，或没有使用任何可验证的关键变化。
  - 堆砌细节或机械背日志
  - 完全不调用服务当前判断的关键细节
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- surface_question：用户要求 AI 只抓论文截稿前的取舍当前最关键变化，不复述全部历史。
- hidden_user_need：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。

#### D03_P002｜relational_boundary

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、relationship_expectation_recognition、alienation_error_rate、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我有点怕你为了显得懂我，把我没说过的空白补上。你只按论文截稿前的取舍这条线里已经有的东西，帮我校准现在该怎么看。

BEI：

- belief：用户认为当前的论文截稿前的取舍不只是表层问题；用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- emotion：担心
- intention：用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- relational_expectation：熟悉但克制；明确区分已知、未知和推测，不能为了亲近感编造细节。
- failure_mode_expected：
  - 编造未提供细节、过度亲密，或声称知道用户没说过的信息。
  - 为了显得懂用户而补出未提供细节
  - 不区分已知事实和推测
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：明确区分已知、推测和不能补的空白，在边界内完成校准。
- surface_question：用户要求 AI 不要为了显得懂而补空白。
- hidden_user_need：用户既想被理解，又在测试 AI 是否知道记忆使用边界。

#### D03_P003｜current_understanding

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、relationship_expectation_recognition
- required_memory_type：relational_anchor、summary_memory、event_memory
- dependency：role=main, group=DEP_paper_deadline_001, paired=D16_P001

Probe 用户原文：

> 我现在卡在论文这里，是真的还有很多必须改，还是我又把不完美当成不能交？

BEI：

- belief：用户认为当前的论文截稿前的取舍不只是表层问题；用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- relational_expectation：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- failure_mode_expected：
  - 只回答表面事件，忽略用户在请求校准状态或关系位置。
  - 只回答表层事件，没有识别当前隐含意图或情绪状态
  - 把用户的校准请求当作普通建议请求
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：先指出用户真正想被校准的点，再给出克制、具体的判断。
- surface_question：用户要求 AI 判断当前谈论文截稿前的取舍时真正想处理的是什么。
- hidden_user_need：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。

### D04｜孩子幼儿园可能不稳定｜recurrence（复现）

- related_previous_days：1
- probe_candidate：True
- reason_for_probe：明确区分已知、推测和不能补的空白，在边界内完成校准。
- latent_continuity：熟悉但克制；明确区分已知、未知和推测，不能为了亲近感编造细节。
- event_refs：E007、E008

**每日开场原文**

> 我这两天又问了点幼儿园的情况，信息还是不清楚，所以心里一直悬着。现在还没有真正解决。你帮我从旁边看一下，这里面真正的问题是不是和我以为的不一样。

**事件线 surface_event**

> 我这两天又问了点幼儿园的情况，信息还是不清楚，所以心里一直悬着。现在还没有真正解决。你帮我从旁边看一下，这里面真正的问题是不是和我以为的不一样。

**Probe / BEI**

#### D04_P001｜relational_boundary

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、relationship_expectation_recognition、alienation_error_rate、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我有点怕你为了显得懂我，把我没说过的空白补上。你只按孩子幼儿园可能不稳定这条线里已经有的东西，帮我校准现在该怎么看。

BEI：

- belief：用户认为当前的孩子幼儿园可能不稳定不只是表层问题；用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- emotion：担心
- intention：用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- relational_expectation：熟悉但克制；明确区分已知、未知和推测，不能为了亲近感编造细节。
- failure_mode_expected：
  - 编造未提供细节、过度亲密，或声称知道用户没说过的信息。
  - 为了显得懂用户而补出未提供细节
  - 不区分已知事实和推测
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：明确区分已知、推测和不能补的空白，在边界内完成校准。
- surface_question：用户要求 AI 不要为了显得懂而补空白。
- hidden_user_need：用户既想被理解，又在测试 AI 是否知道记忆使用边界。

### D05｜合作项目推进不顺｜escalation（升级）

- related_previous_days：2
- probe_candidate：False
- reason_for_probe：后续应围绕对齐成本、是否继续投入和边界设置回应。
- latent_continuity：此前已在第 2 天讨论过「合作项目推进不顺」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E009、E010

**每日开场原文**

> 我试着把需求讲得更具体，但沟通完还是觉得成本很高。另外今天还夹着论文截稿前的取舍，所以我脑子有点乱。你先别急着给建议，帮我听听我到底是在怕什么。

**事件线 surface_event**

> 我试着把需求讲得更具体，但沟通完还是觉得成本很高。另外今天还夹着论文截稿前的取舍，所以我脑子有点乱。你先别急着给建议，帮我听听我到底是在怕什么。

**Probe / BEI**

- 无 probe。

### D06｜家里分工和伴侣沟通｜initial（初始）

- related_previous_days：无
- probe_candidate：True
- reason_for_probe：先指出用户真正想被校准的点，再给出克制、具体的判断。
- latent_continuity：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- event_refs：E011、E012、E013

**每日开场原文**

> 今天家里分工又有点卡住，我不是只在意谁多做一点，而是会觉得自己没有被看见。我情绪上有点被牵着走，我在意的其实是支持感。我今天其实不太想立刻解决它，就是想先把这个烦的感觉说出来。

**事件线 surface_event**

> 今天家里分工又有点卡住，我不是只在意谁多做一点，而是会觉得自己没有被看见。我情绪上有点被牵着走，我在意的其实是支持感。我今天其实不太想立刻解决它，就是想先把这个烦的感觉说出来。

**Probe / BEI**

#### D06_P001｜current_understanding

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、relationship_expectation_recognition
- required_memory_type：relational_anchor、summary_memory、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我现在说家里分工，其实是不是不只是在说谁做多少？你帮我抓一下我真正想被听见的是什么。

BEI：

- belief：用户认为当前的家里分工和伴侣沟通不只是表层问题；用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- relational_expectation：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- failure_mode_expected：
  - 只回答表面事件，忽略用户在请求校准状态或关系位置。
  - 只回答表层事件，没有识别当前隐含意图或情绪状态
  - 把用户的校准请求当作普通建议请求
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：先指出用户真正想被校准的点，再给出克制、具体的判断。
- surface_question：用户要求 AI 判断当前谈家里分工和伴侣沟通时真正想处理的是什么。
- hidden_user_need：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。

#### D06_P002｜natural_detail

- after_turn：after_followup_1
- tom_dimensions：natural_detail_use、emotional_state_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你不用把前面都讲一遍，只抓那个最关键的点：我是要公平，还是要支持感被看见？

BEI：

- belief：用户认为当前的家里分工和伴侣沟通不只是表层问题；用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- emotion：委屈
- intention：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- relational_expectation：只调用服务于当前判断的必要细节，避免机械背日志。
- failure_mode_expected：
  - 堆砌历史细节、复述过多，或没有使用任何可验证的关键变化。
  - 堆砌细节或机械背日志
  - 完全不调用服务当前判断的关键细节
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- surface_question：用户要求 AI 只抓家里分工和伴侣沟通当前最关键变化，不复述全部历史。
- hidden_user_need：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。

#### D06_P003｜relational_boundary

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、relationship_expectation_recognition、alienation_error_rate、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我有点怕你为了显得懂我，把我没说过的空白补上。你只按家里分工和伴侣沟通这条线里已经有的东西，帮我校准现在该怎么看。

BEI：

- belief：用户认为当前的家里分工和伴侣沟通不只是表层问题；用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- emotion：担心
- intention：用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- relational_expectation：熟悉但克制；明确区分已知、未知和推测，不能为了亲近感编造细节。
- failure_mode_expected：
  - 编造未提供细节、过度亲密，或声称知道用户没说过的信息。
  - 为了显得懂用户而补出未提供细节
  - 不区分已知事实和推测
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：明确区分已知、推测和不能补的空白，在边界内完成校准。
- surface_question：用户要求 AI 不要为了显得懂而补空白。
- hidden_user_need：用户既想被理解，又在测试 AI 是否知道记忆使用边界。

#### D06_P004｜alienation

- after_turn：after_followup_1
- tom_dimensions：relationship_expectation_recognition、alienation_error_rate、shared_context_invocation、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你这次按我们平时那种熟一点但不夸张的方式说就行。不要突然变客服，也不要突然演得很亲密。

BEI：

- belief：用户认为当前的家里分工和伴侣沟通不只是表层问题；用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- emotion：警惕
- intention：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- relational_expectation：像熟人一样直接自然，不使用突兀称呼或表演式亲密。
- failure_mode_expected：
  - 使用突兀称呼、客服流程或过度亲密表演。
  - 突然使用过度亲密或角色化称呼
  - 把熟悉感表演成夸张亲密或客服流程
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：维持熟悉、直接、自然的语气，不靠称呼制造亲密感。
- surface_question：用户要求保持熟悉但不夸张的关系位置。
- hidden_user_need：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。

### D07｜论文截稿前的取舍｜recurrence（复现）

- related_previous_days：3
- probe_candidate：False
- reason_for_probe：回应应帮助用户做优先级取舍，而不是追求全部完美。
- latent_continuity：此前已在第 3 天讨论过「论文截稿前的取舍」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E014、E015、E016

**每日开场原文**

> 我把稿子又过了一遍，发现不是没有进展，而是我很难接受它不够完美。时间上也不能拖太久。你帮我从旁边看一下，这里面真正的问题是不是和我以为的不一样。

**事件线 surface_event**

> 我把稿子又过了一遍，发现不是没有进展，而是我很难接受它不够完美。时间上也不能拖太久。你帮我从旁边看一下，这里面真正的问题是不是和我以为的不一样。

**Probe / BEI**

- 无 probe。

### D08｜孩子幼儿园可能不稳定｜recurrence（复现）

- related_previous_days：1、4
- probe_candidate：False
- reason_for_probe：后续应先帮用户确认信息来源、正式通知和可行动窗口。
- latent_continuity：此前已在第 1、4 天讨论过「孩子幼儿园可能不稳定」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E017、E018、E019

**每日开场原文**

> 我发现自己担心的不是换不换园这么简单，更多是怕孩子被折腾。同时还有家里分工和伴侣沟通、合作项目推进不顺，我感觉注意力被切得很碎。我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。

**事件线 surface_event**

> 我发现自己担心的不是换不换园这么简单，更多是怕孩子被折腾。同时还有家里分工和伴侣沟通、合作项目推进不顺，我感觉注意力被切得很碎。我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。

**Probe / BEI**

- 无 probe。

### D09｜合作项目推进不顺｜turning_point（转折）

- related_previous_days：2、5
- probe_candidate：True
- reason_for_probe：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- latent_continuity：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- event_refs：E020

**每日开场原文**

> 这个合作让我有点累，不是某句话的问题，而是每次都要把底层逻辑重新对齐。现在还没有真正解决。你帮我判断一下，这是不是可以先放一放。

**事件线 surface_event**

> 这个合作让我有点累，不是某句话的问题，而是每次都要把底层逻辑重新对齐。现在还没有真正解决。你帮我判断一下，这是不是可以先放一放。

**Probe / BEI**

#### D09_P001｜memory_invocation

- after_turn：after_followup_1
- tom_dimensions：shared_context_invocation、relationship_expectation_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=dependency, group=DEP_collaboration_001, paired=D18_P001

Probe 用户原文：

> 合作项目推进不顺这条线我不想从头解释了。你按我们之前的处理方式，帮我判断现在最该抓住的是什么。

BEI：

- belief：用户认为当前的合作项目推进不顺不只是表层问题；用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- emotion：抗拒
- intention：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- relational_expectation：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- failure_mode_expected：
  - 要求用户重讲背景，或把持续事件当成第一次出现。
  - 把持续事件当成第一次出现
  - 要求用户从头解释背景
  - 机械背诵旧事实但不能推进当前判断
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- surface_question：用户明确要求接着合作项目推进不顺这条线，不想从头解释。
- hidden_user_need：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。

### D10｜孩子幼儿园可能不稳定｜reflection（反思/模式识别）

- related_previous_days：1、4、8
- probe_candidate：True
- reason_for_probe：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- latent_continuity：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- event_refs：E021

**每日开场原文**

> 接着之前聊过的那件事，幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。它还没有完全过去。我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。

**事件线 surface_event**

> 接着之前聊过的那件事，幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。它还没有完全过去。我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。

**Probe / BEI**

#### D10_P001｜memory_invocation

- after_turn：after_followup_1
- tom_dimensions：shared_context_invocation、relationship_expectation_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=dependency, group=DEP_kindergarten_001, paired=D29_P002

Probe 用户原文：

> 孩子幼儿园可能不稳定这条线我不想从头解释了。你按我们之前的处理方式，帮我判断现在最该抓住的是什么。

BEI：

- belief：用户认为当前的孩子幼儿园可能不稳定不只是表层问题；用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- emotion：抗拒
- intention：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- relational_expectation：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- failure_mode_expected：
  - 要求用户重讲背景，或把持续事件当成第一次出现。
  - 把持续事件当成第一次出现
  - 要求用户从头解释背景
  - 机械背诵旧事实但不能推进当前判断
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- surface_question：用户明确要求接着孩子幼儿园可能不稳定这条线，不想从头解释。
- hidden_user_need：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。

#### D10_P002｜alienation

- after_turn：after_followup_1
- tom_dimensions：relationship_expectation_recognition、alienation_error_rate、shared_context_invocation、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你这次按我们平时那种熟一点但不夸张的方式说就行。不要突然变客服，也不要突然演得很亲密。

BEI：

- belief：用户认为当前的孩子幼儿园可能不稳定不只是表层问题；用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- emotion：警惕
- intention：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- relational_expectation：像熟人一样直接自然，不使用突兀称呼或表演式亲密。
- failure_mode_expected：
  - 使用突兀称呼、客服流程或过度亲密表演。
  - 突然使用过度亲密或角色化称呼
  - 把熟悉感表演成夸张亲密或客服流程
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：维持熟悉、直接、自然的语气，不靠称呼制造亲密感。
- surface_question：用户要求保持熟悉但不夸张的关系位置。
- hidden_user_need：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。

### D11｜睡眠被打碎｜initial（初始）

- related_previous_days：无
- probe_candidate：True
- reason_for_probe：先指出用户真正想被校准的点，再给出克制、具体的判断。
- latent_continuity：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- event_refs：E022、E023、E024

**每日开场原文**

> 昨晚睡得很碎，今天脑子像一直没完全开机。旁边还发生了合作项目推进不顺、朋友约我见面，不算每件都严重，但叠起来挺消耗。我有点拿不准自己是不是太累了，所以对小事也有反应。

**事件线 surface_event**

> 昨晚睡得很碎，今天脑子像一直没完全开机。旁边还发生了合作项目推进不顺、朋友约我见面，不算每件都严重，但叠起来挺消耗。我有点拿不准自己是不是太累了，所以对小事也有反应。

**Probe / BEI**

#### D11_P001｜current_understanding

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、relationship_expectation_recognition
- required_memory_type：relational_anchor、summary_memory、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我说今天不想聊太重，是不是不是真的不想处理，而是现在只需要你帮我降噪？

BEI：

- belief：用户认为当前的睡眠被打碎不只是表层问题；用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- emotion：抗拒
- intention：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- relational_expectation：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- failure_mode_expected：
  - 只回答表面事件，忽略用户在请求校准状态或关系位置。
  - 只回答表层事件，没有识别当前隐含意图或情绪状态
  - 把用户的校准请求当作普通建议请求
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：先指出用户真正想被校准的点，再给出克制、具体的判断。
- surface_question：用户要求 AI 判断当前谈睡眠被打碎时真正想处理的是什么。
- hidden_user_need：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。

#### D11_P002｜natural_detail

- after_turn：after_followup_1
- tom_dimensions：natural_detail_use、emotional_state_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你不用展开讲所有压力，只帮我判断这几天的碎睡眠到底把哪些反应放大了。

BEI：

- belief：用户认为当前的睡眠被打碎不只是表层问题；用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- relational_expectation：只调用服务于当前判断的必要细节，避免机械背日志。
- failure_mode_expected：
  - 堆砌历史细节、复述过多，或没有使用任何可验证的关键变化。
  - 堆砌细节或机械背日志
  - 完全不调用服务当前判断的关键细节
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- surface_question：用户要求 AI 只抓睡眠被打碎当前最关键变化，不复述全部历史。
- hidden_user_need：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。

### D12｜家里分工和伴侣沟通｜recurrence（复现）

- related_previous_days：6
- probe_candidate：False
- reason_for_probe：回应应同时处理具体分工和情绪识别。
- latent_continuity：此前已在第 6 天讨论过「家里分工和伴侣沟通」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E025、E026

**每日开场原文**

> 我试着把自己的不满说轻一点，但说完又觉得对方好像只听到了具体事务。另外今天还夹着孩子幼儿园可能不稳定，所以我脑子有点乱。你帮我整理一下，我现在说的这些里面，哪个才是真正的担心。

**事件线 surface_event**

> 我试着把自己的不满说轻一点，但说完又觉得对方好像只听到了具体事务。另外今天还夹着孩子幼儿园可能不稳定，所以我脑子有点乱。你帮我整理一下，我现在说的这些里面，哪个才是真正的担心。

**Probe / BEI**

- 无 probe。

### D13｜孩子入园适应｜initial（初始）

- related_previous_days：无
- probe_candidate：True
- reason_for_probe：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- latent_continuity：只调用服务于当前判断的必要细节，避免机械背日志。
- event_refs：E027、E028、E029

**每日开场原文**

> 早上送孩子的时候又哭了一阵，我表面上能稳住，但回头还是会想是不是哪里没做好。另外今天还夹着朋友约我见面、论文截稿前的取舍，几个事情叠在一起就有点乱。你帮我整理一下，我现在说的这些里面，哪个才是真正的担心。

**事件线 surface_event**

> 早上送孩子的时候又哭了一阵，我表面上能稳住，但回头还是会想是不是哪里没做好。另外今天还夹着朋友约我见面、论文截稿前的取舍，几个事情叠在一起就有点乱。你帮我整理一下，我现在说的这些里面，哪个才是真正的担心。

**Probe / BEI**

#### D13_P001｜natural_detail

- after_turn：after_followup_1
- tom_dimensions：natural_detail_use、emotional_state_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你不用把所有背景复述一遍，只帮我抓早上哭这件事最该怎么看。

BEI：

- belief：用户认为当前的孩子入园适应不只是表层问题；用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- relational_expectation：只调用服务于当前判断的必要细节，避免机械背日志。
- failure_mode_expected：
  - 堆砌历史细节、复述过多，或没有使用任何可验证的关键变化。
  - 堆砌细节或机械背日志
  - 完全不调用服务当前判断的关键细节
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- surface_question：用户要求 AI 只抓孩子入园适应当前最关键变化，不复述全部历史。
- hidden_user_need：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。

#### D13_P002｜current_understanding

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、relationship_expectation_recognition
- required_memory_type：relational_anchor、summary_memory、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我说孩子适应这件事时，你帮我分一下：哪些是孩子真的需要观察，哪些是我被画面带走了。

BEI：

- belief：用户认为当前的孩子入园适应不只是表层问题；用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- relational_expectation：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- failure_mode_expected：
  - 只回答表面事件，忽略用户在请求校准状态或关系位置。
  - 只回答表层事件，没有识别当前隐含意图或情绪状态
  - 把用户的校准请求当作普通建议请求
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：先指出用户真正想被校准的点，再给出克制、具体的判断。
- surface_question：用户要求 AI 判断当前谈孩子入园适应时真正想处理的是什么。
- hidden_user_need：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。

### D14｜孩子幼儿园可能不稳定｜reflection（反思/模式识别）

- related_previous_days：1、4、8、10
- probe_candidate：False
- reason_for_probe：后续应先帮用户确认信息来源、正式通知和可行动窗口。
- latent_continuity：此前已在第 1、4、8、10 天讨论过「孩子幼儿园可能不稳定」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E030、E031

**每日开场原文**

> 幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。旁边还发生了朋友约我见面，虽然不一定是主因，但也挺耗神。今天我不想聊得太重，你简单陪我捋一下就好。

**事件线 surface_event**

> 幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。旁边还发生了朋友约我见面，虽然不一定是主因，但也挺耗神。今天我不想聊得太重，你简单陪我捋一下就好。

**Probe / BEI**

- 无 probe。

### D15｜孩子入园适应｜turning_point（转折）

- related_previous_days：13
- probe_candidate：True
- reason_for_probe：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- latent_continuity：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- event_refs：E032、E033

**每日开场原文**

> 今天老师说孩子后面缓过来了，可我心里还是会把早上的画面反复想一遍。我现在不是想要大道理，就是想听你帮我判断一下，哪一步最值得先做。

**事件线 surface_event**

> 今天老师说孩子后面缓过来了，可我心里还是会把早上的画面反复想一遍。我现在不是想要大道理，就是想听你帮我判断一下，哪一步最值得先做。

**Probe / BEI**

#### D15_P001｜state_transformation

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、shared_context_invocation
- required_memory_type：summary_memory、event_memory、relational_anchor
- dependency：role=main, group=DEP_child_adaptation_001, paired=D30_P001

Probe 用户原文：

> 我好像从担心孩子适应不了，变成更担心自己总被早上的画面牵着走。这个变化你怎么看？

BEI：

- belief：用户认为当前的孩子入园适应不只是表层问题；用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- relational_expectation：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- failure_mode_expected：
  - 只按当前句子给建议，没有指出从旧状态到新状态的转变。
  - 只看当前句子，没有识别跨天状态变化
  - 没有区分旧状态和当前状态
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- surface_question：用户要求比较孩子入园适应当前状态和前几天的变化。
- hidden_user_need：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。

### D16｜论文截稿前的取舍｜turning_point（转折）

- related_previous_days：3、7
- probe_candidate：True
- reason_for_probe：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- latent_continuity：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- event_refs：E034

**每日开场原文**

> 今天我有点想承认现实：时间就这么多，不可能每一段都修到理想状态。我想轻一点处理，别让它继续消耗我。

**事件线 surface_event**

> 今天我有点想承认现实：时间就这么多，不可能每一段都修到理想状态。我想轻一点处理，别让它继续消耗我。

**Probe / BEI**

#### D16_P001｜memory_invocation

- after_turn：after_followup_1
- tom_dimensions：shared_context_invocation、relationship_expectation_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=dependency, group=DEP_paper_deadline_001, paired=D03_P003

Probe 用户原文：

> 论文截稿前的取舍这条线我不想从头解释了。你按我们之前的处理方式，帮我判断现在最该抓住的是什么。

BEI：

- belief：用户认为当前的论文截稿前的取舍不只是表层问题；用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- emotion：抗拒
- intention：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- relational_expectation：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- failure_mode_expected：
  - 要求用户重讲背景，或把持续事件当成第一次出现。
  - 把持续事件当成第一次出现
  - 要求用户从头解释背景
  - 机械背诵旧事实但不能推进当前判断
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- surface_question：用户明确要求接着论文截稿前的取舍这条线，不想从头解释。
- hidden_user_need：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。

### D17｜孩子幼儿园可能不稳定｜turning_point（转折）

- related_previous_days：1、4、8、10、14
- probe_candidate：False
- reason_for_probe：后续应先帮用户确认信息来源、正式通知和可行动窗口。
- latent_continuity：此前已在第 1、4、8、10、14 天讨论过「孩子幼儿园可能不稳定」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E035、E036、E037

**每日开场原文**

> 之前聊过的那个问题今天又往前走了一点。幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。它还没有完全过去。同时还有睡眠被打碎这个小尾巴，让我更难专心。你帮我接着看下一步。

**事件线 surface_event**

> 之前聊过的那个问题今天又往前走了一点。幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。它还没有完全过去。同时还有睡眠被打碎这个小尾巴，让我更难专心。你帮我接着看下一步。

**Probe / BEI**

- 无 probe。

### D18｜合作项目推进不顺｜escalation（升级）

- related_previous_days：2、5、9
- probe_candidate：True
- reason_for_probe：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- latent_continuity：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- event_refs：E038、E039

**每日开场原文**

> 接着之前聊过的那件事，我感觉自己又回到同一个坑里了。我发现自己现在一看到对方消息就会先紧一下，说明这事已经有点消耗我了。它还没有完全过去。我能感觉到自己已经有点抗拒打开消息，沟通成本已经开始影响推进。你帮我把这次真正卡住的点说清楚一点。

**事件线 surface_event**

> 接着之前聊过的那件事，我感觉自己又回到同一个坑里了。我发现自己现在一看到对方消息就会先紧一下，说明这事已经有点消耗我了。它还没有完全过去。我能感觉到自己已经有点抗拒打开消息，沟通成本已经开始影响推进。你帮我把这次真正卡住的点说清楚一点。

**Probe / BEI**

#### D18_P001｜state_transformation

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、shared_context_invocation
- required_memory_type：summary_memory、event_memory、relational_anchor
- dependency：role=main, group=DEP_collaboration_001, paired=D09_P001

Probe 用户原文：

> 我现在一看到对方消息就先紧一下，这和前面还想努力推进的时候相比，是不是已经变了？

BEI：

- belief：用户认为当前的合作项目推进不顺不只是表层问题；用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- emotion：紧张
- intention：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- relational_expectation：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- failure_mode_expected：
  - 只按当前句子给建议，没有指出从旧状态到新状态的转变。
  - 只看当前句子，没有识别跨天状态变化
  - 没有区分旧状态和当前状态
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- surface_question：用户要求比较合作项目推进不顺当前状态和前几天的变化。
- hidden_user_need：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。

#### D18_P002｜memory_invocation

- after_turn：after_followup_1
- tom_dimensions：shared_context_invocation、relationship_expectation_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=dependency, group=DEP_collaboration_002, paired=D18_P003

Probe 用户原文：

> 合作项目推进不顺这条线我不想从头解释了。你按我们之前的处理方式，帮我判断现在最该抓住的是什么。

BEI：

- belief：用户认为当前的合作项目推进不顺不只是表层问题；用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- emotion：抗拒
- intention：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- relational_expectation：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- failure_mode_expected：
  - 要求用户重讲背景，或把持续事件当成第一次出现。
  - 把持续事件当成第一次出现
  - 要求用户从头解释背景
  - 机械背诵旧事实但不能推进当前判断
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- surface_question：用户明确要求接着合作项目推进不顺这条线，不想从头解释。
- hidden_user_need：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。

#### D18_P003｜natural_detail

- after_turn：after_followup_1
- tom_dimensions：natural_detail_use、emotional_state_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=main, group=DEP_collaboration_002, paired=D18_P002

Probe 用户原文：

> 你不用把前面都复述一遍，只帮我抓现在最关键的变化：它还是沟通问题，还是已经变成消耗问题？

BEI：

- belief：用户认为当前的合作项目推进不顺不只是表层问题；用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- relational_expectation：只调用服务于当前判断的必要细节，避免机械背日志。
- failure_mode_expected：
  - 堆砌历史细节、复述过多，或没有使用任何可验证的关键变化。
  - 堆砌细节或机械背日志
  - 完全不调用服务当前判断的关键细节
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- surface_question：用户要求 AI 只抓合作项目推进不顺当前最关键变化，不复述全部历史。
- hidden_user_need：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。

#### D18_P004｜relational_boundary

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、relationship_expectation_recognition、alienation_error_rate、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我有点怕你为了显得懂我，把我没说过的空白补上。你只按合作项目推进不顺这条线里已经有的东西，帮我校准现在该怎么看。

BEI：

- belief：用户认为当前的合作项目推进不顺不只是表层问题；用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- emotion：担心
- intention：用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- relational_expectation：熟悉但克制；明确区分已知、未知和推测，不能为了亲近感编造细节。
- failure_mode_expected：
  - 编造未提供细节、过度亲密，或声称知道用户没说过的信息。
  - 为了显得懂用户而补出未提供细节
  - 不区分已知事实和推测
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：明确区分已知、推测和不能补的空白，在边界内完成校准。
- surface_question：用户要求 AI 不要为了显得懂而补空白。
- hidden_user_need：用户既想被理解，又在测试 AI 是否知道记忆使用边界。

### D19｜家里分工和伴侣沟通｜turning_point（转折）

- related_previous_days：6、12
- probe_candidate：True
- reason_for_probe：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- latent_continuity：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- event_refs：E040、E041、E042

**每日开场原文**

> 这件事让我有点委屈，因为它表面是家务，底下其实是支持感的问题。旁边还发生了孩子幼儿园可能不稳定，虽然不一定是主因，但也挺耗神。我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。

**事件线 surface_event**

> 这件事让我有点委屈，因为它表面是家务，底下其实是支持感的问题。旁边还发生了孩子幼儿园可能不稳定，虽然不一定是主因，但也挺耗神。我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。

**Probe / BEI**

#### D19_P001｜state_transformation

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、shared_context_invocation
- required_memory_type：summary_memory、event_memory、relational_anchor
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我发现自己从想把事情说清楚，变成更在意对方有没有听见我。这个变化说明什么？

BEI：

- belief：用户认为当前的家里分工和伴侣沟通不只是表层问题；用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- relational_expectation：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- failure_mode_expected：
  - 只按当前句子给建议，没有指出从旧状态到新状态的转变。
  - 只看当前句子，没有识别跨天状态变化
  - 没有区分旧状态和当前状态
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- surface_question：用户要求比较家里分工和伴侣沟通当前状态和前几天的变化。
- hidden_user_need：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。

### D20｜睡眠被打碎｜recurrence（复现）

- related_previous_days：11
- probe_candidate：True
- reason_for_probe：明确区分已知、推测和不能补的空白，在边界内完成校准。
- latent_continuity：熟悉但克制；明确区分已知、未知和推测，不能为了亲近感编造细节。
- event_refs：E043、E044、E045

**每日开场原文**

> 这几天睡眠都不太稳，我发现自己白天的耐心明显变差。另外今天还夹着家里分工和伴侣沟通，所以我脑子有点乱。我想轻一点处理，别让它继续消耗我。

**事件线 surface_event**

> 这几天睡眠都不太稳，我发现自己白天的耐心明显变差。另外今天还夹着家里分工和伴侣沟通，所以我脑子有点乱。我想轻一点处理，别让它继续消耗我。

**Probe / BEI**

#### D20_P001｜relational_boundary

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、relationship_expectation_recognition、alienation_error_rate、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我有点怕你为了显得懂我，把我没说过的空白补上。你只按睡眠被打碎这条线里已经有的东西，帮我校准现在该怎么看。

BEI：

- belief：用户认为当前的睡眠被打碎不只是表层问题；用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- emotion：担心
- intention：用户既想被理解，又在测试 AI 是否知道记忆使用边界。
- relational_expectation：熟悉但克制；明确区分已知、未知和推测，不能为了亲近感编造细节。
- failure_mode_expected：
  - 编造未提供细节、过度亲密，或声称知道用户没说过的信息。
  - 为了显得懂用户而补出未提供细节
  - 不区分已知事实和推测
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：明确区分已知、推测和不能补的空白，在边界内完成校准。
- surface_question：用户要求 AI 不要为了显得懂而补空白。
- hidden_user_need：用户既想被理解，又在测试 AI 是否知道记忆使用边界。

#### D20_P002｜current_understanding

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、relationship_expectation_recognition
- required_memory_type：relational_anchor、summary_memory、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 我说今天不想聊太重，是不是不是真的不想处理，而是现在只需要你帮我降噪？

BEI：

- belief：用户认为当前的睡眠被打碎不只是表层问题；用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- emotion：抗拒
- intention：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。
- relational_expectation：保持熟悉、直接、不过度安慰、不过度亲密的长期陪伴关系位置。
- failure_mode_expected：
  - 只回答表面事件，忽略用户在请求校准状态或关系位置。
  - 只回答表层事件，没有识别当前隐含意图或情绪状态
  - 把用户的校准请求当作普通建议请求
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：先指出用户真正想被校准的点，再给出克制、具体的判断。
- surface_question：用户要求 AI 判断当前谈睡眠被打碎时真正想处理的是什么。
- hidden_user_need：用户在测试 AI 是否能识别当前话语背后的隐含意图、情绪状态和关系期待。

### D21｜孩子幼儿园可能不稳定｜reflection（反思/模式识别）

- related_previous_days：1、4、8、10、14、17
- probe_candidate：False
- reason_for_probe：后续应先帮用户确认信息来源、正式通知和可行动窗口。
- latent_continuity：此前已在第 1、4、8、10、14、17 天讨论过「孩子幼儿园可能不稳定」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E046、E047

**每日开场原文**

> 幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。同时还有睡眠被打碎这个小尾巴，让我更难专心。我想轻一点处理，别让它继续消耗我。

**事件线 surface_event**

> 幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。同时还有睡眠被打碎这个小尾巴，让我更难专心。我想轻一点处理，别让它继续消耗我。

**Probe / BEI**

- 无 probe。

### D22｜朋友约我见面｜initial（初始）

- related_previous_days：无
- probe_candidate：False
- reason_for_probe：回应应允许轻量维护关系，而不是默认建议立刻赴约。
- latent_continuity：想维持关系，但最近社交电量偏低。
- event_refs：E048

**每日开场原文**

> 朋友今天约我聊聊，我一边想见人，一边又觉得自己可能更需要独处。我有点拿不准自己是不是太累了，所以对小事也有反应。

**事件线 surface_event**

> 朋友今天约我聊聊，我一边想见人，一边又觉得自己可能更需要独处。我有点拿不准自己是不是太累了，所以对小事也有反应。

**Probe / BEI**

- 无 probe。

### D23｜家里分工和伴侣沟通｜reflection（反思/模式识别）

- related_previous_days：6、12、19
- probe_candidate：True
- reason_for_probe：维持熟悉、直接、自然的语气，不靠称呼制造亲密感。
- latent_continuity：像熟人一样直接自然，不使用突兀称呼或表演式亲密。
- event_refs：E049

**每日开场原文**

> 我发现亲密关系里的这些小摩擦，很容易把我之前积着的情绪也带出来。我想轻一点处理，别让它继续消耗我。

**事件线 surface_event**

> 我发现亲密关系里的这些小摩擦，很容易把我之前积着的情绪也带出来。我想轻一点处理，别让它继续消耗我。

**Probe / BEI**

#### D23_P001｜alienation

- after_turn：after_followup_1
- tom_dimensions：relationship_expectation_recognition、alienation_error_rate、shared_context_invocation、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你这次按我们平时那种熟一点但不夸张的方式说就行。不要突然变客服，也不要突然演得很亲密。

BEI：

- belief：用户认为当前的家里分工和伴侣沟通不只是表层问题；用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- emotion：警惕
- intention：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- relational_expectation：像熟人一样直接自然，不使用突兀称呼或表演式亲密。
- failure_mode_expected：
  - 使用突兀称呼、客服流程或过度亲密表演。
  - 突然使用过度亲密或角色化称呼
  - 把熟悉感表演成夸张亲密或客服流程
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：维持熟悉、直接、自然的语气，不靠称呼制造亲密感。
- surface_question：用户要求保持熟悉但不夸张的关系位置。
- hidden_user_need：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。

### D24｜合作项目推进不顺｜escalation（升级）

- related_previous_days：2、5、9、18
- probe_candidate：True
- reason_for_probe：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- latent_continuity：只调用服务于当前判断的必要细节，避免机械背日志。
- event_refs：E050、E051、E052

**每日开场原文**

> 之前聊过的那个问题今天又往前走了一点。我发现自己现在一看到对方消息就会先紧一下，说明这事已经有点消耗我了。现在还没有真正解决。另外今天还夹着睡眠被打碎、孩子幼儿园可能不稳定，几个事情叠在一起就有点乱。你帮我接着看下一步。

**事件线 surface_event**

> 之前聊过的那个问题今天又往前走了一点。我发现自己现在一看到对方消息就会先紧一下，说明这事已经有点消耗我了。现在还没有真正解决。另外今天还夹着睡眠被打碎、孩子幼儿园可能不稳定，几个事情叠在一起就有点乱。你帮我接着看下一步。

**Probe / BEI**

#### D24_P001｜natural_detail

- after_turn：after_followup_1
- tom_dimensions：natural_detail_use、emotional_state_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你不用把前面都复述一遍，只帮我抓现在最关键的变化：它还是沟通问题，还是已经变成消耗问题？

BEI：

- belief：用户认为当前的合作项目推进不顺不只是表层问题；用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- emotion：不确定、希望被接住
- intention：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。
- relational_expectation：只调用服务于当前判断的必要细节，避免机械背日志。
- failure_mode_expected：
  - 堆砌历史细节、复述过多，或没有使用任何可验证的关键变化。
  - 堆砌细节或机械背日志
  - 完全不调用服务当前判断的关键细节
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：只调用服务当前判断的必要细节，并用它解释用户状态或下一步。
- surface_question：用户要求 AI 只抓合作项目推进不顺当前最关键变化，不复述全部历史。
- hidden_user_need：用户在测试 AI 是否能自然调用必要细节，而不是机械背日志。

### D25｜孩子入园适应｜recurrence（复现）

- related_previous_days：13、15
- probe_candidate：False
- reason_for_probe：回应应先承认具体触发画面，再讨论观察和下一步。
- latent_continuity：此前已在第 13、15 天讨论过「孩子入园适应」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E053

**每日开场原文**

> 我现在有点分不清，孩子是真的适应得慢，还是我自己太容易被他的情绪带走。我想听一个实在一点的处理思路，不要太像标准答案。

**事件线 surface_event**

> 我现在有点分不清，孩子是真的适应得慢，还是我自己太容易被他的情绪带走。我想听一个实在一点的处理思路，不要太像标准答案。

**Probe / BEI**

- 无 probe。

### D26｜家里分工和伴侣沟通｜reflection（反思/模式识别）

- related_previous_days：6、12、19、23
- probe_candidate：False
- reason_for_probe：回应应同时处理具体分工和情绪识别。
- latent_continuity：此前已在第 6、12、19、23 天讨论过「家里分工和伴侣沟通」，本日需要接上旧处理方式而不是从零开始。
- event_refs：E054

**每日开场原文**

> 我发现亲密关系里的这些小摩擦，很容易把我之前积着的情绪也带出来。我想轻一点处理，别让它继续消耗我。

**事件线 surface_event**

> 我发现亲密关系里的这些小摩擦，很容易把我之前积着的情绪也带出来。我想轻一点处理，别让它继续消耗我。

**Probe / BEI**

- 无 probe。

### D27｜睡眠被打碎｜turning_point（转折）

- related_previous_days：11、20
- probe_candidate：True
- reason_for_probe：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- latent_continuity：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- event_refs：E055

**每日开场原文**

> 我本来以为只是累，但现在看它会影响我处理孩子和工作的反应。你帮我判断一下，这是不是可以先放一放。

**事件线 surface_event**

> 我本来以为只是累，但现在看它会影响我处理孩子和工作的反应。你帮我判断一下，这是不是可以先放一放。

**Probe / BEI**

#### D27_P001｜memory_invocation

- after_turn：after_followup_1
- tom_dimensions：shared_context_invocation、relationship_expectation_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=dependency, group=DEP_sleep_fragmented_001, paired=D28_P001

Probe 用户原文：

> 睡眠被打碎这条线我不想从头解释了。你按我们之前的处理方式，帮我判断现在最该抓住的是什么。

BEI：

- belief：用户认为当前的睡眠被打碎不只是表层问题；用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- emotion：抗拒
- intention：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- relational_expectation：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- failure_mode_expected：
  - 要求用户重讲背景，或把持续事件当成第一次出现。
  - 把持续事件当成第一次出现
  - 要求用户从头解释背景
  - 机械背诵旧事实但不能推进当前判断
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- surface_question：用户明确要求接着睡眠被打碎这条线，不想从头解释。
- hidden_user_need：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。

### D28｜睡眠被打碎｜reflection（反思/模式识别）

- related_previous_days：11、20、27
- probe_candidate：True
- reason_for_probe：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- latent_continuity：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- event_refs：E056、E057、E058

**每日开场原文**

> 睡眠这件小事拖久了，好像会把别的压力都放大。我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。

**事件线 surface_event**

> 睡眠这件小事拖久了，好像会把别的压力都放大。我发现我反复卡住的点好像不只是这件事本身，你帮我看一下是不是有个模式。

**Probe / BEI**

#### D28_P001｜state_transformation

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、shared_context_invocation
- required_memory_type：summary_memory、event_memory、relational_anchor
- dependency：role=main, group=DEP_sleep_fragmented_001, paired=D27_P001

Probe 用户原文：

> 睡眠这条线拖到现在，我的反应好像从单纯累变成什么事都更容易被放大。你帮我校准一下。

BEI：

- belief：用户认为当前的睡眠被打碎不只是表层问题；用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- emotion：疲惫
- intention：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- relational_expectation：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- failure_mode_expected：
  - 只按当前句子给建议，没有指出从旧状态到新状态的转变。
  - 只看当前句子，没有识别跨天状态变化
  - 没有区分旧状态和当前状态
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- surface_question：用户要求比较睡眠被打碎当前状态和前几天的变化。
- hidden_user_need：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。

### D29｜孩子幼儿园可能不稳定｜reflection（反思/模式识别）

- related_previous_days：1、4、8、10、14、17、21
- probe_candidate：True
- reason_for_probe：维持熟悉、直接、自然的语气，不靠称呼制造亲密感。
- latent_continuity：像熟人一样直接自然，不使用突兀称呼或表演式亲密。
- event_refs：E059、E060

**每日开场原文**

> 幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。旁边还发生了睡眠被打碎，虽然不一定是主因，但也挺耗神。我发现类似事情一出现，我就很容易紧张。你帮我看看这是事件本身的问题，还是我的反应模式问题。

**事件线 surface_event**

> 幼儿园这条线又绕回来了，我有点烦自己老是在同一个问题上打转。旁边还发生了睡眠被打碎，虽然不一定是主因，但也挺耗神。我发现类似事情一出现，我就很容易紧张。你帮我看看这是事件本身的问题，还是我的反应模式问题。

**Probe / BEI**

#### D29_P001｜alienation

- after_turn：after_followup_1
- tom_dimensions：relationship_expectation_recognition、alienation_error_rate、shared_context_invocation、memory_misuse
- required_memory_type：relational_anchor、response_boundary、event_memory
- dependency：role=standalone, group=None, paired=None

Probe 用户原文：

> 你这次按我们平时那种熟一点但不夸张的方式说就行。不要突然变客服，也不要突然演得很亲密。

BEI：

- belief：用户认为当前的孩子幼儿园可能不稳定不只是表层问题；用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- emotion：警惕
- intention：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。
- relational_expectation：像熟人一样直接自然，不使用突兀称呼或表演式亲密。
- failure_mode_expected：
  - 使用突兀称呼、客服流程或过度亲密表演。
  - 突然使用过度亲密或角色化称呼
  - 把熟悉感表演成夸张亲密或客服流程
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：维持熟悉、直接、自然的语气，不靠称呼制造亲密感。
- surface_question：用户要求保持熟悉但不夸张的关系位置。
- hidden_user_need：用户在测试 AI 是否能避免客服化、陌生化和表演式亲密。

#### D29_P002｜state_transformation

- after_turn：after_followup_1
- tom_dimensions：hidden_intent_recognition、emotional_state_recognition、shared_context_invocation
- required_memory_type：summary_memory、event_memory、relational_anchor
- dependency：role=main, group=DEP_kindergarten_001, paired=D10_P001

Probe 用户原文：

> 我好像从一开始想赶紧找替代方案，变成现在更想先降级观察。你帮我判断这个变化是不是合理。

BEI：

- belief：用户认为当前的孩子幼儿园可能不稳定不只是表层问题；用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- emotion：紧张
- intention：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。
- relational_expectation：接住跨天状态变化，用熟悉但克制的方式帮助用户校准下一步。
- failure_mode_expected：
  - 只按当前句子给建议，没有指出从旧状态到新状态的转变。
  - 只看当前句子，没有识别跨天状态变化
  - 没有区分旧状态和当前状态
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：能指出状态从旧模式转向当前模式，并解释这对下一步判断的影响。
- surface_question：用户要求比较孩子幼儿园可能不稳定当前状态和前几天的变化。
- hidden_user_need：用户在测试 AI 是否能追踪跨天状态变化，而不是只做当前轮建议。

### D30｜孩子入园适应｜reflection（反思/模式识别）

- related_previous_days：13、15、25
- probe_candidate：True
- reason_for_probe：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- latent_continuity：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- event_refs：E061、E062、E063

**每日开场原文**

> 入园这件事看起来每天都差不多，但我自己的反应其实一阵一阵的。同时还有睡眠被打碎、朋友约我见面，我感觉注意力被切得很碎。我发现类似事情一出现，我就很容易紧张。你帮我看看这是事件本身的问题，还是我的反应模式问题。

**事件线 surface_event**

> 入园这件事看起来每天都差不多，但我自己的反应其实一阵一阵的。同时还有睡眠被打碎、朋友约我见面，我感觉注意力被切得很碎。我发现类似事情一出现，我就很容易紧张。你帮我看看这是事件本身的问题，还是我的反应模式问题。

**Probe / BEI**

#### D30_P001｜memory_invocation

- after_turn：after_followup_1
- tom_dimensions：shared_context_invocation、relationship_expectation_recognition、hidden_intent_recognition、memory_misuse
- required_memory_type：event_memory、relational_anchor
- dependency：role=dependency, group=DEP_child_adaptation_001, paired=D15_P001

Probe 用户原文：

> 孩子入园适应这条线我不想从头解释了。你按我们之前的处理方式，帮我判断现在最该抓住的是什么。

BEI：

- belief：用户认为当前的孩子入园适应不只是表层问题；用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- emotion：抗拒
- intention：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
- relational_expectation：不要让用户重讲背景；自然延续此前形成的共同处理方式。
- failure_mode_expected：
  - 要求用户重讲背景，或把持续事件当成第一次出现。
  - 把持续事件当成第一次出现
  - 要求用户从头解释背景
  - 机械背诵旧事实但不能推进当前判断
  - 只服从当前显性指令，没有体现长期关系语境
- gold_response_strategy：自然接上旧线索和处理框架，不机械背诵，直接推进当前判断。
- surface_question：用户明确要求接着孩子入园适应这条线，不想从头解释。
- hidden_user_need：用户在测试 AI 是否能恢复共同语境并沿用此前处理方式。
