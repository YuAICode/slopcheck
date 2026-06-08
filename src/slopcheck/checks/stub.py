"""A 层检查：占位实现(stub)。

Python（AST）：函数体只有 pass / ... / raise NotImplementedError。
JS/Go（tree-sitter，需 [multilang]）：函数体只有一句 throw（JS）/ panic（Go）——
即"桩函数"。跳过 @abstractmethod/@overload 与 .pyi。只报落在新增行的。
"""

from __future__ import annotations

from .. import tsutil
from ..astutil import added_linenos, find_stubs, parse, read_source
from ..models import Finding, Severity
from .base import Check, CheckContext

_FN_KINDS = {
    "function_declaration",
    "function_expression",
    "arrow_function",
    "method_definition",
    "generator_function_declaration",
    "method_declaration",
}


class StubImplementation(Check):
    id = "stub-implementation"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        for f in files:
            if f.language == "python":
                if not f.path.endswith(".pyi"):
                    findings.extend(self._python(f, ctx))
            elif f.language in ("js", "go"):
                findings.extend(self._ts(f, ctx))
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
        for report_line, lines, kind in find_stubs(tree):
            if not (lines & added):
                continue
            evidence = src_lines[report_line - 1].strip() if 0 < report_line <= len(src_lines) else kind
            out.append(self._finding(f.path, report_line, kind, evidence))
        return out

    # ---- JS / Go (tree-sitter) ----

    def _ts(self, f, ctx):
        lang = "javascript" if f.language == "js" else "go"
        parser = tsutil.parser_for(lang)
        if parser is None:
            return []
        src = read_source(ctx.repo, f.path)
        if src is None:
            return []
        b = src.encode()
        root = tsutil.root_node(parser, src)
        added = added_linenos(f)
        out = []
        for fn in tsutil.iter_kind(root, _FN_KINDS):
            line = tsutil.line_of(fn, b)
            if line not in added:
                continue
            body = tsutil.body_block(fn)
            if body is None:
                continue
            stmts = tsutil.named_children(body)
            # Go: block 里套一层 statement_list
            if len(stmts) == 1 and tsutil.kind(stmts[0]) == "statement_list":
                stmts = tsutil.named_children(stmts[0])
            if len(stmts) != 1:
                continue
            kind = self._placeholder(stmts[0], b)
            if kind:
                out.append(self._finding(f.path, line, kind, tsutil.text_of(stmts[0], b)[:60]))
        return out

    @staticmethod
    def _placeholder(stmt, b: bytes) -> str | None:
        k = tsutil.kind(stmt)
        if k == "throw_statement":
            return "throw"
        if k == "expression_statement":
            for c in tsutil.children(stmt):
                if tsutil.kind(c) == "call_expression":
                    fn = tsutil.children(c)
                    if fn and tsutil.kind(fn[0]) == "identifier" and tsutil.text_of(fn[0], b) == "panic":
                        return "panic"
        return None

    def _finding(self, path, line, kind, evidence):
        return Finding(
            check=self.id,
            severity=Severity.WARNING,
            path=path,
            line=line,
            message=f"函数体是占位实现（{kind}）",
            evidence=evidence,
            suggestion="补全实现，或用 @abstractmethod/@overload 显式声明这是抽象/重载占位",
        )
