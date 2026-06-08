from slopcheck.checks.base import CheckContext
from slopcheck.checks.missing_test import MissingTest
from slopcheck.diff import parse_unified_diff
from slopcheck.graph import GraphIndex


def _diff(path, lines):
    body = "\n".join("+" + line for line in lines)
    return f"--- a/{path}\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


def test_flags_untested_known_public(tmp_path):
    graph = GraphIndex(symbols={"public_fn", "tested_fn"}, defs={}, tested={"tested_fn"})
    ctx = CheckContext(repo=tmp_path, python_deps=None, graph=graph)
    files = parse_unified_diff(
        _diff(
            "app.py",
            [
                "def public_fn():",  # 图谱已知、未测 → 报
                "def tested_fn():",  # 已测 → 不报
                "def brand_new():",  # 图谱未知 → 跳过（同 PR 可能加了测试）
                "def _private():",  # 私有 → 跳过
            ],
        )
    )
    findings = MissingTest().run(files, ctx)
    assert len(findings) == 1
    assert "public_fn" in findings[0].message


def test_skips_test_files(tmp_path):
    graph = GraphIndex(symbols={"helper"}, defs={}, tested=set())
    ctx = CheckContext(repo=tmp_path, python_deps=None, graph=graph)
    files = parse_unified_diff(_diff("tests/test_x.py", ["def helper():"]))
    assert MissingTest().run(files, ctx) == []


def test_no_graph_skips(tmp_path):
    ctx = CheckContext(repo=tmp_path, python_deps=None, graph=None)
    files = parse_unified_diff(_diff("app.py", ["def public_fn():"]))
    assert MissingTest().run(files, ctx) == []
