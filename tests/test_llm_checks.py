from slopcheck.checks.base import CheckContext
from slopcheck.checks.fake_test import FakeTest
from slopcheck.checks.scope_creep import ScopeCreep
from slopcheck.diff import parse_unified_diff


class FakeLLM:
    def __init__(self, is_issue):
        self._v = {"is_issue": is_issue, "reason": "测"}

    def judge(self, instruction, payload):
        return self._v


def _whole(path, content):
    lines = content.split("\n")
    body = "\n".join("+" + line for line in lines)
    return f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


FAKE_TEST_SRC = "def test_nothing():\n    assert True\n"


def test_fake_test_flags_when_llm_says_issue(tmp_path):
    (tmp_path / "test_x.py").write_text(FAKE_TEST_SRC)
    files = parse_unified_diff(_whole("test_x.py", FAKE_TEST_SRC))
    ctx = CheckContext(repo=tmp_path, python_deps=None, graph=None, llm=FakeLLM(True))
    findings = FakeTest().run(files, ctx)
    assert len(findings) == 1
    assert findings[0].check == "fake-test"


def test_fake_test_no_llm_skips(tmp_path):
    (tmp_path / "test_x.py").write_text(FAKE_TEST_SRC)
    files = parse_unified_diff(_whole("test_x.py", FAKE_TEST_SRC))
    ctx = CheckContext(repo=tmp_path, python_deps=None, graph=None, llm=None)
    assert FakeTest().run(files, ctx) == []


def test_fake_test_only_test_files(tmp_path):
    (tmp_path / "app.py").write_text(FAKE_TEST_SRC)
    files = parse_unified_diff(_whole("app.py", FAKE_TEST_SRC))
    ctx = CheckContext(repo=tmp_path, python_deps=None, graph=None, llm=FakeLLM(True))
    assert FakeTest().run(files, ctx) == []


def test_scope_creep_flags(tmp_path):
    files = parse_unified_diff(_whole("a.py", "x = 1"))
    ctx = CheckContext(
        repo=tmp_path, python_deps=None, graph=None, llm=FakeLLM(True), pr_description="只改 README"
    )
    findings = ScopeCreep().run(files, ctx)
    assert len(findings) == 1
    assert findings[0].check == "scope-creep"


def test_scope_creep_needs_description(tmp_path):
    files = parse_unified_diff(_whole("a.py", "x = 1"))
    ctx = CheckContext(
        repo=tmp_path, python_deps=None, graph=None, llm=FakeLLM(True), pr_description=""
    )
    assert ScopeCreep().run(files, ctx) == []
