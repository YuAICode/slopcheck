"""A 层检查（图谱）：幻觉的内部符号。

`from <本地模块> import <name>` 时，若 name 在代码图谱中不存在，
多半是 AI 幻觉了项目里并不存在的内部函数/类。只对本地模块做（外部库的
顶层包由 hallucinated-import 负责），因此图谱能确定性回答"存不存在"。
"""

from __future__ import annotations

import re

from ..models import Finding, Severity
from .base import Check, CheckContext

_FROM = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+(.+)")


class HallucinatedSymbol(Check):
    id = "hallucinated-symbol"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        graph, deps = ctx.graph, ctx.python_deps
        if graph is None or deps is None:
            return findings
        for f in files:
            if f.language != "python":
                continue
            for al in f.added:
                m = _FROM.match(al.text)
                if not m:
                    continue
                module, names_part = m.group(1), m.group(2)
                if not self._is_local(module, deps):
                    continue
                for name in self._names(names_part):
                    if name == "*" or not name:
                        continue
                    if not graph.has_symbol(name):
                        findings.append(
                            Finding(
                                check=self.id,
                                severity=Severity.WARNING,
                                path=f.path,
                                line=al.lineno,
                                message=f"从本地模块 '{module}' import 的 '{name}' 在代码图谱中不存在",
                                evidence=al.text.strip(),
                                suggestion="确认该符号真实存在；AI 常幻觉项目内并不存在的内部函数/类",
                            )
                        )
        return findings

    @staticmethod
    def _is_local(module: str, deps) -> bool:
        if module.startswith("."):  # 相对 import 必为本地
            return True
        return module.split(".")[0] in deps.local

    @staticmethod
    def _names(part: str) -> list[str]:
        part = part.split("#")[0].strip().strip("()")
        out = []
        for tok in part.split(","):
            tok = tok.strip()
            if tok:
                out.append(tok.split(" as ")[0].strip())
        return out
