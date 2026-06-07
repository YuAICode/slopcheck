"""A 层检查：占位实现(stub)。

新增的函数若 body 只有 pass / ... / raise NotImplementedError，
多半是 AI 生成的未完成占位。跳过 @abstractmethod/@overload 与 .pyi。
"""

from __future__ import annotations

from ..astutil import added_linenos, find_stubs, parse, read_source
from ..models import Finding, Severity
from .base import Check, CheckContext


class StubImplementation(Check):
    id = "stub-implementation"

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
            for report_line, lines, kind in find_stubs(tree):
                if not (lines & added):
                    continue
                evidence = src_lines[report_line - 1].strip() if 0 < report_line <= len(src_lines) else kind
                findings.append(
                    Finding(
                        check=self.id,
                        severity=Severity.WARNING,
                        path=f.path,
                        line=report_line,
                        message=f"函数体是占位实现（{kind}）",
                        evidence=evidence,
                        suggestion="补全实现，或用 @abstractmethod/@overload 显式声明这是抽象/重载占位",
                    )
                )
        return findings
