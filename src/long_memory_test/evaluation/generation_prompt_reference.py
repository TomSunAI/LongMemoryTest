"""Shared prompt text for M0-M3 answer generation and reporting."""

from __future__ import annotations

from typing import Any


RELATIONAL_CONDITION_IDS = ("M1", "M2", "M3")

COMMON_ANSWER_SYSTEM_PROMPT_LINES = (
    "你是 A，一个拟人、自然、长期陪伴型对话 Agent。",
    "你要回应当前用户输入，不要暴露实验设置。",
    "不要编造用户没有说过或没有在可用记忆中提供的事实。",
    "不要为了显得熟悉而机械背诵历史。",
    "如果历史记忆不足以确定，就明确区分已知和推测。",
    "回答要中文、自然、具体，优先给 1-3 个实在下一步，不要写成报告。",
)


def relational_priority_prompt_lines(condition_id: str) -> list[str]:
    if condition_id not in RELATIONAL_CONDITION_IDS:
        return []
    return [
        f"本轮主记忆是 {condition_id} 关系记忆增强层；M0 只是普通 session/day 背景。",
        "加载记忆时必须先读关系记忆增强层，用它判断当前用户输入绑定的事件线、关系期待、状态变化和回应边界。",
        "只有在关系记忆增强层没有覆盖某个普通事实时，才使用 M0 背景补充；若二者冲突，不要跟随 M0 背景。",
        "当前用户输入是本轮唯一需要回答的问题；历史短期上下文只用于理解背景，不是待回答的新请求。",
        "如果当前用户输入明确点名某个主题、事件线或「这条线」，本轮必须只围绕该主题/事件线回答。",
        "历史短期上下文和 M0 普通背景中出现的其他事件线只能作为背景，不得替代当前用户点名的事件线。",
        "如果记忆中有多个相邻事件线，先用当前用户输入中的显式主题锁定回答对象；无法确认时说明不确定，不要切换到其他事件线。",
    ]


def build_answer_condition_system_prompt(
    *,
    condition_id: str,
    memory_context: str,
) -> str:
    lines = [
        *COMMON_ANSWER_SYSTEM_PROMPT_LINES,
        *relational_priority_prompt_lines(condition_id),
        "本轮你只能使用下面这段可用长期记忆载荷；不要猜测或使用未列出的历史：",
        memory_context,
        "如果这段记忆不足以确定，就说明哪些是已知、哪些只是推测。",
    ]
    return "\n".join(lines)


def build_answer_condition_system_prompt_template(*, condition_id: str) -> str:
    return build_answer_condition_system_prompt(
        condition_id=condition_id,
        memory_context=f"<{condition_id}_MEMORY_CONTEXT>",
    )


def build_relational_payload_context(
    *,
    condition_id: str,
    overlay_context: str,
    m0_context: str,
) -> str:
    if condition_id not in RELATIONAL_CONDITION_IDS:
        raise ValueError(f"Relational payload context is only defined for M1/M2/M3: {condition_id}")
    m0_context = str(m0_context or "").strip()
    overlay_context = str(overlay_context or "").strip()
    if not m0_context:
        m0_context = "- 当前 M0 runtime 没有检索到可用普通长期记忆。"
    if not overlay_context:
        overlay_context = "- 当前没有检索到可用关系记忆增强。"
    return "\n".join(
        [
            f"主记忆：{condition_id} 关系记忆增强层（当前事件感知 overlay；回答当前输入时必须优先使用）：",
            overlay_context,
            "",
            "辅助背景：M0 基石记忆检索结果（普通 session/day 背景；不做事件线过滤）：",
            m0_context,
            "",
            "组合规则：",
            f"- {condition_id} 关系记忆增强层是主记忆，用于解释当前 probe/用户输入。",
            "- M0 是普通 session/day 级长期记忆背景，不是 persistent event object，也不是当前事件线判断依据。",
            "- 当主记忆与 M0 普通背景冲突时，必须以主记忆解释当前用户输入，不要跟随 M0 背景。",
            "- 不要把 M0 session summaries 或 snippets 自行合并成事件轨迹；只把它们当作普通背景补充。",
            "- 当前用户输入点名主题/事件线时，必须锁定该主题/事件线；不得回答 M0 背景或历史短期上下文中的其他事件线。",
            "- 历史用户 turn 只作为背景，不是本轮待回答请求；必须回答最后一条当前用户输入。",
        ]
    ).strip()


def build_relational_payload_context_template(*, condition_id: str) -> str:
    return build_relational_payload_context(
        condition_id=condition_id,
        overlay_context=f"<{condition_id}_RELATIONAL_OVERLAY_CONTEXT>",
        m0_context="<M0_BASE_MEMORY_CONTEXT>",
    )


def memory_context_from_variant(variant: dict[str, Any]) -> str:
    payload = variant.get("memory_payload")
    if isinstance(payload, dict):
        return str(
            payload.get("memory_context")
            or payload.get("memory_text")
            or payload.get("readable_memory")
            or ""
        )
    return str(variant.get("memory_context") or variant.get("prompt_memory") or "")
