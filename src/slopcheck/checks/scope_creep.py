"""B 层检查（LLM）：超范围改动（scope creep）。

给定 PR 描述 + 变更文件清单，让 LLM 判断本次改动是否明显超出 PR 描述的范围。
需 ctx.llm 且 ctx.pr_description 非空；否则跳过。PR 级发现（line=1）。
"""

from __future__ import annotations

from ..models import Finding, Severity
from .base import Check, CheckContext

_INSTRUCTION = (
    "下面给出 PR 描述和本次变更涉及的文件清单。判断这些改动是否明显超出了 PR 描述声明的范围"
    "（例如顺手改了无关模块、夹带了未提及的重构）。明显超范围 is_issue=true；契合或合理关联 is_issue=false。"
)


class ScopeCreep(Check):
    id = "scope-creep"

    def run(self, files, ctx: CheckContext):
        if ctx.llm is None or not ctx.pr_description.strip() or not files:
            return []
        file_list = "\n".join(f"- {f.path}（新增 {len(f.added)} 行）" for f in files)
        payload = f"PR 描述：\n{ctx.pr_description}\n\n变更文件：\n{file_list}"
        verdict = ctx.llm.judge(_INSTRUCTION, payload)
        if not verdict.get("is_issue"):
            return []
        return [
            Finding(
                check=self.id,
                severity=Severity.INFO,
                path=files[0].path,
                line=1,
                message="改动可能超出 PR 描述范围：" + (verdict.get("reason", "") or "")[:160],
                evidence=f"{len(files)} 个文件变更",
                suggestion="确认是否应拆分 PR，或在描述中说明这些改动",
            )
        ]
