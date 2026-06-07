"""终端输出渲染。"""

from __future__ import annotations

from ..models import Finding, Severity

_ICON = {Severity.ERROR: "✖", Severity.WARNING: "⚠", Severity.INFO: "ℹ"}


def render(findings: list[Finding]) -> str:
    if not findings:
        return "✓ slopcheck: 未发现问题"
    lines: list[str] = []
    for f in findings:
        lines.append(f"{_ICON.get(f.severity, '?')} [{f.check}] {f.path}:{f.line}")
        lines.append(f"    {f.message}")
        if f.evidence:
            lines.append(f"    └ 证据: {f.evidence}")
        if f.suggestion:
            lines.append(f"    └ 建议: {f.suggestion}")
    lines.append(f"\nslopcheck: 共 {len(findings)} 处发现")
    return "\n".join(lines)
