import pytest

pytest.importorskip("tree_sitter_language_pack")  # 未装 [multilang] 则跳过整个文件

from slopcheck.checks.base import CheckContext  # noqa: E402
from slopcheck.checks.stub import StubImplementation  # noqa: E402
from slopcheck.checks.swallow import SwallowedException  # noqa: E402
from slopcheck.diff import parse_unified_diff  # noqa: E402


def _whole(path, content):
    lines = content.split("\n")
    body = "\n".join("+" + line for line in lines)
    return f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


def _ctx(repo):
    return CheckContext(repo=repo, python_deps=None, graph=None)


JS = (
    'function notDone() {\n'
    '  throw new Error("not implemented");\n'
    '}\n'
    'function ok() {\n'
    '  return 1;\n'
    '}\n'
    'function risky() {\n'
    '  try { foo(); } catch (e) {}\n'
    '}\n'
)

GO = (
    'package m\n'
    'func notDone() {\n'
    '\tpanic("not implemented")\n'
    '}\n'
    'func ok() int {\n'
    '\treturn 1\n'
    '}\n'
)


def test_js_stub_throw_only(tmp_path):
    (tmp_path / "a.js").write_text(JS)
    findings = StubImplementation().run(parse_unified_diff(_whole("a.js", JS)), _ctx(tmp_path))
    assert len(findings) == 1
    assert findings[0].line == 1  # notDone（throw-only）；ok/risky 不报


def test_js_swallow_empty_catch(tmp_path):
    (tmp_path / "a.js").write_text(JS)
    findings = SwallowedException().run(parse_unified_diff(_whole("a.js", JS)), _ctx(tmp_path))
    assert len(findings) == 1  # risky 里的空 catch


def test_go_stub_panic_only(tmp_path):
    (tmp_path / "a.go").write_text(GO)
    findings = StubImplementation().run(parse_unified_diff(_whole("a.go", GO)), _ctx(tmp_path))
    assert len(findings) == 1  # notDone（panic-only）；ok 不报
