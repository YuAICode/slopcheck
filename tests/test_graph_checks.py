from slopcheck.checks.base import CheckContext
from slopcheck.checks.hallucinated_symbol import HallucinatedSymbol
from slopcheck.checks.reuse import ReuseExisting
from slopcheck.deps import PythonDeps
from slopcheck.diff import parse_unified_diff
from slopcheck.graph import GraphIndex


def _diff(path, lines):
    body = "\n".join("+" + line for line in lines)
    return f"--- a/{path}\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


# ---- hallucinated-symbol ----

def test_hallucinated_symbol_flags_ghost(tmp_path):
    graph = GraphIndex(symbols={"real_func"}, defs={"real_func": ["app/x.py"]})
    deps = PythonDeps(declared=set(), local={"app"})
    ctx = CheckContext(repo=tmp_path, python_deps=deps, graph=graph)
    files = parse_unified_diff(
        _diff(
            "m.py",
            [
                "from app.x import real_func",  # 本地、存在 → 不报
                "from app.x import ghost_func",  # 本地、图谱无 → 报
                "from requests import get",  # 非本地 → 跳过
            ],
        )
    )
    findings = HallucinatedSymbol().run(files, ctx)
    assert len(findings) == 1
    assert "ghost_func" in findings[0].message


def test_hallucinated_symbol_relative(tmp_path):
    graph = GraphIndex(symbols={"helper"}, defs={})
    deps = PythonDeps(declared=set(), local=set())
    ctx = CheckContext(repo=tmp_path, python_deps=deps, graph=graph)
    files = parse_unified_diff(_diff("m.py", ["from . import helper", "from . import nope"]))
    findings = HallucinatedSymbol().run(files, ctx)
    assert len(findings) == 1
    assert "nope" in findings[0].message


def test_hallucinated_symbol_no_graph_skips(tmp_path):
    deps = PythonDeps(declared=set(), local={"app"})
    ctx = CheckContext(repo=tmp_path, python_deps=deps, graph=None)
    files = parse_unified_diff(_diff("m.py", ["from app import ghost"]))
    assert HallucinatedSymbol().run(files, ctx) == []


# ---- reuse-existing ----

def test_reuse_flags_duplicate(tmp_path):
    graph = GraphIndex(symbols={"process_order"}, defs={"process_order": ["app/a.py"]})
    ctx = CheckContext(repo=tmp_path, python_deps=None, graph=graph)
    files = parse_unified_diff(_diff("app/b.py", ["def process_order(x):"]))
    findings = ReuseExisting().run(files, ctx)
    assert len(findings) == 1
    assert "process_order" in findings[0].message


def test_reuse_skips_same_file_and_dunder(tmp_path):
    graph = GraphIndex(
        symbols={"process_order", "__init__"},
        defs={"process_order": ["app/b.py"], "__init__": ["app/a.py"]},
    )
    ctx = CheckContext(repo=tmp_path, python_deps=None, graph=graph)
    # process_order 仅定义在当前文件 → 非复用；__init__ 是 dunder → 跳过
    files = parse_unified_diff(_diff("app/b.py", ["def process_order(x):", "def __init__(self):"]))
    assert ReuseExisting().run(files, ctx) == []
