import textwrap

from slopcheck.checks.base import CheckContext
from slopcheck.checks.stub import StubImplementation
from slopcheck.checks.swallow import SwallowedException
from slopcheck.diff import parse_unified_diff

SAMPLE = textwrap.dedent(
    '''\
    from abc import abstractmethod


    def todo_func():
        pass


    def not_impl():
        raise NotImplementedError


    def ellipsis_func():
        ...


    def real_func():
        return 42


    class Base:
        @abstractmethod
        def absm(self):
            ...


    def swallows():
        try:
            risky()
        except Exception:
            pass


    def handles():
        try:
            risky()
        except Exception as exc:
            log(exc)
    '''
)


def _whole_file_diff(path: str, content: str) -> str:
    lines = content.split("\n")
    body = "\n".join("+" + line for line in lines)
    return f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


def _ctx(repo):
    return CheckContext(repo=repo, python_deps=None, graph=None)


def _setup(tmp_path):
    (tmp_path / "m.py").write_text(SAMPLE)
    files = parse_unified_diff(_whole_file_diff("m.py", SAMPLE))
    return files, _ctx(tmp_path)


def test_stub_detects_three_kinds_skips_abstract(tmp_path):
    files, ctx = _setup(tmp_path)
    findings = StubImplementation().run(files, ctx)
    kinds = {f.message for f in findings}
    # pass / ... / raise NotImplementedError 三种各一；absm 被 @abstractmethod 跳过；real_func 不报
    assert len(findings) == 3
    assert any("pass" in k for k in kinds)
    assert any("..." in k for k in kinds)
    assert any("NotImplementedError" in k for k in kinds)


def test_swallow_detects_only_silent_except(tmp_path):
    files, ctx = _setup(tmp_path)
    findings = SwallowedException().run(files, ctx)
    # 仅 swallows() 的 except: pass 命中；handles() 有真实处理不报
    assert len(findings) == 1
    assert "pass" in findings[0].message


def test_skips_when_file_absent(tmp_path):
    # diff 指向不存在的文件 → 优雅降级，不报错不命中
    files = parse_unified_diff(_whole_file_diff("ghost.py", "def f():\n    pass\n"))
    assert StubImplementation().run(files, _ctx(tmp_path)) == []
