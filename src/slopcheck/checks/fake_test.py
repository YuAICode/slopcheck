"""B 层检查（LLM）：假测试。

新增的测试函数若断言恒真 / 无实质断言 / 没覆盖被测逻辑，交给 LLM judge 判定。
需 ctx.llm（--enable-llm 且有 key）；否则跳过。
"""

from __future__ import annotations

import ast

from ..astutil import added_linenos, is_test_file, parse, read_source
from ..models import Finding, Severity
from .base import Check, CheckContext

_INSTRUCTION = (
    "下面是一个新增的单元测试函数。判断它是否是『假测试』："
    "断言恒真（如 assert True）、完全没有断言、或没有真正验证被测行为。"
    "若是假测试 is_issue=true。"
)


class FakeTest(Check):
    id = "fake-test"

    def run(self, files, ctx: CheckContext):
        findings: list[Finding] = []
        if ctx.llm is None:
            return findings
        for f in files:
            if f.language != "python" or not is_test_file(f.path):
                continue
            src = read_source(ctx.repo, f.path)
            if src is None:
                continue
            tree = parse(src)
            if tree is None:
                continue
            added = added_linenos(f)
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test"):
                    continue
                end = node.end_lineno or node.lineno
                if not (set(range(node.lineno, end + 1)) & added):
                    continue
                segment = ast.get_source_segment(src, node) or ""
                verdict = ctx.llm.judge(_INSTRUCTION, segment)
                if verdict.get("is_issue"):
                    findings.append(
                        Finding(
                            check=self.id,
                            severity=Severity.WARNING,
                            path=f.path,
                            line=node.lineno,
                            message="疑似假测试：" + (verdict.get("reason", "") or "")[:120],
                            evidence=f"{node.name}()",
                            suggestion="补充对实际行为的实质断言，确保测试会因 bug 失败",
                        )
                    )
        return findings
