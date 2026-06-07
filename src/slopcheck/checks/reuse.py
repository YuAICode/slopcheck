"""A 层检查（图谱）：重复造轮子。

新增的函数/类，若图谱中已存在同名定义（在别的文件），提示考虑复用。
天然易误报，故从严：跳过 dunder / 短名 / 常见约定名，且同名广泛存在
（>3 处=约定而非复用目标）时不报。标 INFO（建议性，不影响 CI）。
"""

from __future__ import annotations

import re

from ..models import Finding, Severity
from .base import Check, CheckContext

_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(")
_CLASS = re.compile(r"^\s*class\s+(\w+)\b")
_STOP = {
    "run", "main", "setup", "teardown", "handle", "init", "build",
    "load", "save", "parse", "render", "create", "update", "delete",
}


class ReuseExisting(Check):
    id = "reuse-existing"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        graph = ctx.graph
        if graph is None:
            return findings
        for f in files:
            if f.language != "python":
                continue
            for al in f.added:
                name = self._def_name(al.text)
                if not name or name.startswith("__") or len(name) <= 3 or name in _STOP:
                    continue
                all_defs = graph.defined_in(name)
                elsewhere = [d for d in all_defs if d != f.path]
                if not elsewhere or len(all_defs) > 3:
                    continue
                findings.append(
                    Finding(
                        check=self.id,
                        severity=Severity.INFO,
                        path=f.path,
                        line=al.lineno,
                        message=f"图谱中已存在同名定义 '{name}'（{elsewhere[0]}）",
                        evidence=al.text.strip(),
                        suggestion="确认是否应复用已有实现，而非重新造一个同名函数/类",
                    )
                )
        return findings

    @staticmethod
    def _def_name(line: str) -> str | None:
        m = _DEF.match(line) or _CLASS.match(line)
        return m.group(1) if m else None
