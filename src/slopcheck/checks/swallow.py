"""A 层检查：吞异常(swallow)。

Python（AST）：except 块只有 pass / ...。
JS（tree-sitter，需 [multilang]）：catch 块为空。
Go 无 try/catch，不适用。只报落在新增行的。
"""

from __future__ import annotations

from .. import tsutil
from ..astutil import added_linenos, find_swallows, parse, read_source
from ..models import Finding, Severity
from .base import Check, CheckContext


class SwallowedException(Check):
    id = "swallowed-exception"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        for f in files:
            if f.language == "python":
                if not f.path.endswith(".pyi"):
                    findings.extend(self._python(f, ctx))
            elif f.language == "js":
                findings.extend(self._js(f, ctx))
        return findings

    # ---- Python (AST) ----

    def _python(self, f, ctx):
        out = []
        src = read_source(ctx.repo, f.path)
        if src is None:
            return out
        tree = parse(src)
        if tree is None:
            return out
        src_lines = src.splitlines()
        added = added_linenos(f)
        for report_line, lines, kind in find_swallows(tree):
            if not (lines & added):
                continue
            evidence = src_lines[report_line - 1].strip() if 0 < report_line <= len(src_lines) else kind
            out.append(self._finding(f.path, report_line, f"except 块只有 {kind} —— 静默吞掉异常", evidence))
        return out

    # ---- JS (tree-sitter) ----

    def _js(self, f, ctx):
        parser = tsutil.parser_for("javascript")
        if parser is None:
            return []
        src = read_source(ctx.repo, f.path)
        if src is None:
            return []
        b = src.encode()
        root = tsutil.root_node(parser, src)
        added = added_linenos(f)
        out = []
        for cc in tsutil.iter_kind(root, {"catch_clause"}):
            body = tsutil.body_block(cc)
            if body is None or tsutil.named_children(body):  # 非空 catch 跳过
                continue
            line = tsutil.line_of(cc, b)
            if line not in added:
                continue
            out.append(self._finding(f.path, line, "catch 块为空 —— 静默吞掉异常", tsutil.text_of(cc, b)[:40]))
        return out

    def _finding(self, path, line, message, evidence):
        return Finding(
            check=self.id,
            severity=Severity.WARNING,
            path=path,
            line=line,
            message=message,
            evidence=evidence,
            suggestion="至少记录日志或重新抛出；要刻意忽略请加注释说明",
        )
