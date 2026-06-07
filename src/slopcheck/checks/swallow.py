"""A 层检查：吞异常(swallow)。

新增的 except 块若块体只有 pass / ...，异常被静默吞掉——常见 AI slop，
也是真实隐患（错误被无声咽下）。
"""

from __future__ import annotations

from ..astutil import added_linenos, find_swallows, parse, read_source
from ..models import Finding, Severity
from .base import Check, CheckContext


class SwallowedException(Check):
    id = "swallowed-exception"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        for f in files:
            if f.language != "python" or f.path.endswith(".pyi"):
                continue
            src = read_source(ctx.repo, f.path)
            if src is None:
                continue
            tree = parse(src)
            if tree is None:
                continue
            src_lines = src.splitlines()
            added = added_linenos(f)
            for report_line, lines, kind in find_swallows(tree):
                if not (lines & added):
                    continue
                evidence = src_lines[report_line - 1].strip() if 0 < report_line <= len(src_lines) else kind
                findings.append(
                    Finding(
                        check=self.id,
                        severity=Severity.WARNING,
                        path=f.path,
                        line=report_line,
                        message=f"except 块只有 {kind} —— 静默吞掉异常",
                        evidence=evidence,
                        suggestion="至少记录日志或重新抛出；要刻意忽略请加注释说明，并尽量缩小捕获范围",
                    )
                )
        return findings
