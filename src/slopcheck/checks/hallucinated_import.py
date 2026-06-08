"""A 层检查：幻觉 / 未声明 import（多语言）。

新增代码里 import 的包，若不在该语言的"已知"集合（stdlib/内置 + 依赖清单 + 本地模块），
判为可疑——AI 常幻觉不存在的包名，也可能踩到 slopsquatting 供应链风险。
确定性判定，附证据，标 WARNING（--strict 时才致失败）。

支持：Python（stdlib + 依赖清单 + 本地模块 + 别名表）、JS/TS（node 内置 + package.json）。
"""

from __future__ import annotations

import re

from ..models import Finding, Severity
from .base import Check, CheckContext

# Python
_PY_FROM = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+")
_PY_IMPORT = re.compile(r"^\s*import\s+(.+)")

# JS/TS：import ... from 'x' / import 'x' / require('x') / export ... from 'x'
_JS_FROM = re.compile(r"""(?:from|require\s*\(|^\s*import\s+|^\s*export\s+.*\bfrom)\s*['"]([^'"]+)['"]""")

# Go：整行就是一个被引号包裹的 import 路径（可带 alias / import 前缀 / _ . 别名）
_GO_IMPORT = re.compile(r'^\s*(?:import\s+)?(?:[A-Za-z_.]\w*\s+|_\s+)?"([^"]+)"\s*$')


class HallucinatedImport(Check):
    id = "hallucinated-import"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        for f in files:
            if f.language == "python":
                findings.extend(self._python(f, ctx))
            elif f.language == "js":
                findings.extend(self._js(f, ctx))
            elif f.language == "go":
                findings.extend(self._go(f, ctx))
        return findings

    # ---- Python ----

    def _python(self, f, ctx: CheckContext):
        deps = ctx.python_deps
        if deps is None:
            return []
        out = []
        for al in f.added:
            for mod in self._py_imports(al.text):
                if not deps.is_known(mod):
                    out.append(self._finding(f.path, al, f"import '{mod}'", mod))
        return out

    @staticmethod
    def _py_imports(line: str) -> list[str]:
        m_from = _PY_FROM.match(line)
        if m_from:
            top = m_from.group(1)
            return [] if top.startswith(".") else [top.split(".")[0]]
        m_imp = _PY_IMPORT.match(line)
        if not m_imp:
            return []
        rest = m_imp.group(1).split("#")[0]
        mods = []
        for part in rest.split(","):
            part = part.strip()
            if not part:
                continue
            name = part.split(" as ")[0].strip()
            if not name.startswith("."):
                mods.append(name.split(".")[0])
        return mods

    # ---- JS / TS ----

    def _js(self, f, ctx: CheckContext):
        deps = ctx.js_deps
        if deps is None:
            return []
        out = []
        for al in f.added:
            for spec in self._js_specs(al.text):
                pkg = self._js_pkg(spec)
                if pkg and not deps.is_known(pkg):
                    out.append(self._finding(f.path, al, f"import '{pkg}'", pkg))
        return out

    @staticmethod
    def _js_specs(line: str) -> list[str]:
        out = []
        for m in _JS_FROM.finditer(line):
            out.append(m.group(1))
        return out

    @staticmethod
    def _js_pkg(spec: str) -> str | None:
        if spec.startswith(".") or spec.startswith("/"):
            return None  # 相对/绝对本地路径
        if spec.startswith("node:"):
            return spec
        if spec.startswith("@"):  # scoped: @scope/pkg
            parts = spec.split("/")
            return "/".join(parts[:2]) if len(parts) >= 2 else spec
        return spec.split("/")[0]

    # ---- Go ----

    def _go(self, f, ctx: CheckContext):
        deps = ctx.go_deps
        if deps is None:
            return []
        out = []
        for al in f.added:
            m = _GO_IMPORT.match(al.text)
            if not m:
                continue
            imp = m.group(1)
            if not deps.is_known(imp):
                out.append(self._finding(f.path, al, f'import "{imp}"', imp))
        return out

    @staticmethod
    def _finding(path, al, what, name):
        return Finding(
            check="hallucinated-import",
            severity=Severity.WARNING,
            path=path,
            line=al.lineno,
            message=f"{what} 未在 内置 / 依赖清单 / 本地模块中找到",
            evidence=al.text.strip(),
            suggestion="确认该包真实存在且已声明依赖；AI 常幻觉不存在的包名（slopsquatting 供应链风险）",
        )
