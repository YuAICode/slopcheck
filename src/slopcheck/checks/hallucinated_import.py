"""A 层检查：幻觉 / 未声明 import。

在新增代码里发现的 import，若其顶层包不在 stdlib / 依赖清单 / 本地模块中，
判为可疑——AI 常幻觉不存在的包名，也可能踩到 slopsquatting 供应链风险。
确定性判定，附证据；为控误报先标 WARNING（--strict 时才致失败）。
"""

from __future__ import annotations

import re

from ..models import Finding, Severity
from .base import Check, CheckContext

_PY_FROM = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+")
_PY_IMPORT = re.compile(r"^\s*import\s+(.+)")


class HallucinatedImport(Check):
    id = "hallucinated-import"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        deps = ctx.python_deps
        if deps is None:
            return findings
        for f in files:
            if f.language != "python":
                continue
            for al in f.added:
                for mod in self._imports(al.text):
                    if not deps.is_known(mod):
                        findings.append(
                            Finding(
                                check=self.id,
                                severity=Severity.WARNING,
                                path=f.path,
                                line=al.lineno,
                                message=f"import '{mod}' 未在 stdlib / 依赖清单 / 本地模块中找到",
                                evidence=al.text.strip(),
                                suggestion=(
                                    "确认该包真实存在且已声明依赖；"
                                    "AI 常幻觉不存在的包名（slopsquatting 供应链风险）"
                                ),
                            )
                        )
        return findings

    @staticmethod
    def _imports(line: str) -> list[str]:
        """从一行代码提取被 import 的顶层包名（相对 import 跳过）。"""
        m_from = _PY_FROM.match(line)
        if m_from:
            top = m_from.group(1)
            if top.startswith("."):
                return []
            return [top.split(".")[0]]

        m_imp = _PY_IMPORT.match(line)
        if not m_imp:
            return []
        rest = m_imp.group(1).split("#")[0]  # 去行尾注释
        mods: list[str] = []
        for part in rest.split(","):
            part = part.strip()
            if not part:
                continue
            name = part.split(" as ")[0].strip()  # "x as y" → x
            if name.startswith("."):
                continue
            mods.append(name.split(".")[0])
        return mods
