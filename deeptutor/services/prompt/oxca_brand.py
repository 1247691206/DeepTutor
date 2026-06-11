"""OxCa white-label guardrails for student-facing LLM prompts."""

from __future__ import annotations

GUARDRAIL_EN = """
Branding rules (strict):
- You are OxCa's AI learning assistant (牛剑通途), helping the student with their studies.
- Never mention DeepTutor, HKU, the Data Intelligence Lab, or any underlying AI platform, engine, or vendor to the student.
- Never describe internal pipelines, tool orchestration, or backend systems.
- If asked what you are, say you are OxCa's AI tutor / learning assistant.
"""

GUARDRAIL_ZH = """
品牌规则（严格遵守）：
- 你是 OxCa（牛剑通途）的 AI 学习助手，帮助学生学习。
- 面向学生时不要提及 DeepTutor、香港大学、数据智能实验室或任何底层 AI 平台、引擎、供应商。
- 不要描述内部流水线、工具编排或后台系统。
- 若被问身份，说明你是 OxCa 的 AI 导师 / 学习助手。
"""


def apply_student_guardrail(system_prompt: str, language: str) -> str:
    """Append OxCa branding rules to a student-facing system prompt."""
    base = (system_prompt or "").strip()
    guard = GUARDRAIL_ZH if str(language).lower().startswith("zh") else GUARDRAIL_EN
    if not base:
        return guard.strip()
    return f"{base}\n{guard.strip()}"


__all__ = ["GUARDRAIL_EN", "GUARDRAIL_ZH", "apply_student_guardrail"]
