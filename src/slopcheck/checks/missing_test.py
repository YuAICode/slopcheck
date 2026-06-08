"""A 层检查（图谱）：缺测试覆盖。

新增的**已知公共函数**（图谱里已存在的，即被本次改动的函数），若图谱中没有
任何测试调用它，提示补测试。标 INFO。

只对图谱已知函数报——全新函数跳过（同一个 PR 里可能正好加了它的测试，而图谱是
改动前的快照，报了会误伤）。
"""

from __future__ import annotations

import re

from ..astutil import is_test_file
from ..models import Finding, Severity
from .base import Check, CheckContext

_DEF = re.compile(r"^\s*(?:async\s+)?def\s+([a-zA-Z]\w*)\s*\(")


class MissingTest(Check):
    id = "missing-test"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        graph = ctx.graph
        if graph is None:
            return findings
        for f in files:
            if f.language != "python" or is_test_file(f.path):
                continue
            for al in f.added:
                m = _DEF.match(al.text)
                if not m:
                    continue
                name = m.group(1)
                if not graph.has_symbol(name):  # 全新函数 → 跳过（同 PR 可能已加测试）
                    continue
                if graph.is_tested(name):
                    continue
                findings.append(
                    Finding(
                        check=self.id,
                        severity=Severity.INFO,
                        path=f.path,
                        line=al.lineno,
                        message=f"公共函数 '{name}' 似乎没有测试覆盖",
                        evidence=al.text.strip(),
                        suggestion="补一个测试；图谱中未发现任何测试调用它",
                    )
                )
        return findings
