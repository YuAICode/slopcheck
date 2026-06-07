"""GitHub PR 评论输出（sticky comment 的 markdown）。

带 MARKER 注释，便于 Action 端找到并更新同一条评论（避免刷屏）。
"""

from __future__ import annotations

from ..models import Finding

MARKER = "<!-- slopcheck -->"
_ICON = {"error": "🔴", "warning": "🟡", "info": "🔵"}


def render(findings: list[Finding]) -> str:
    if not findings:
        return f"{MARKER}\n### 🟢 slopcheck\n\nAI-aware review 未发现问题。"
    rows = [
        f"| {_ICON.get(f.severity.value, '⚪')} | `{f.check}` | `{f.path}:{f.line}` | {f.message} |"
        for f in findings
    ]
    return "\n".join(
        [
            MARKER,
            "### 🔎 slopcheck —— AI 代码审查",
            "",
            f"发现 **{len(findings)}** 处：",
            "",
            "| | 检查 | 位置 | 说明 |",
            "|---|---|---|---|",
            *rows,
            "",
            "<sub>由 [slopcheck](https://github.com/YuAICode/slopcheck) 自动生成</sub>",
        ]
    )
