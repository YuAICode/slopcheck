from slopcheck.checks.base import CheckContext
from slopcheck.checks.hallucinated_import import HallucinatedImport
from slopcheck.deps import load_go_deps, load_js_deps, load_python_deps
from slopcheck.diff import parse_unified_diff


def _ctx(repo):
    return CheckContext(repo=repo, python_deps=load_python_deps(repo), graph=None)


def _make_diff(lines):
    body = "\n".join("+" + line for line in lines)
    return f"--- a/m.py\n+++ b/m.py\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


def test_flags_unknown_import_only(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0"\ndependencies = ["requests>=2"]\n'
    )
    diff = _make_diff(
        ["import os", "import requests", "import nonexistent_xyz_pkg", "from . import foo"]
    )
    findings = HallucinatedImport().run(parse_unified_diff(diff), _ctx(tmp_path))
    assert len(findings) == 1
    assert "nonexistent_xyz_pkg" in findings[0].message
    assert findings[0].line == 3  # 第三行新增


def test_alias_counts_as_known(tmp_path):
    # 依赖声明 PyYAML，代码 import yaml —— 通过别名表识别为已知
    (tmp_path / "requirements.txt").write_text("PyYAML\n")
    findings = HallucinatedImport().run(
        parse_unified_diff(_make_diff(["import yaml"])), _ctx(tmp_path)
    )
    assert findings == []


def test_local_module_known(tmp_path):
    (tmp_path / "mypkg").mkdir()
    (tmp_path / "mypkg" / "__init__.py").write_text("")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0"\ndependencies = []\n'
    )
    findings = HallucinatedImport().run(
        parse_unified_diff(_make_diff(["from mypkg import thing", "import mypkg"])),
        _ctx(tmp_path),
    )
    assert findings == []


def test_multi_import_split(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0"\ndependencies = []\n'
    )
    # "import os, fakepkg" 应只报 fakepkg
    findings = HallucinatedImport().run(
        parse_unified_diff(_make_diff(["import os, fakepkg_zzz"])), _ctx(tmp_path)
    )
    assert len(findings) == 1
    assert "fakepkg_zzz" in findings[0].message


def _make_js_diff(lines):
    body = "\n".join("+" + line for line in lines)
    return f"--- a/m.js\n+++ b/m.js\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


def test_js_flags_unknown_imports(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"react": "^18"}}')
    diff = _make_js_diff(
        [
            "import a from 'react';",  # 已声明 → 不报
            "import b from 'ghost-pkg-zz';",  # 未声明 → 报
            "const fs = require('fs');",  # node 内置 → 不报
            "import c from './local';",  # 相对路径 → 跳过
            "import d from '@scope/missing';",  # scoped 未声明 → 报
        ]
    )
    ctx = CheckContext(
        repo=tmp_path, python_deps=None, graph=None, js_deps=load_js_deps(tmp_path)
    )
    findings = HallucinatedImport().run(parse_unified_diff(diff), ctx)
    msgs = " ".join(f.message for f in findings)
    assert len(findings) == 2
    assert "ghost-pkg-zz" in msgs
    assert "@scope/missing" in msgs
    assert "react" not in msgs
    assert "'fs'" not in msgs


def _make_go_diff(lines):
    body = "\n".join("+" + line for line in lines)
    return f"--- a/m.go\n+++ b/m.go\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


def test_go_flags_unknown_imports(tmp_path):
    (tmp_path / "go.mod").write_text(
        "module github.com/me/proj\n\nrequire (\n\tgithub.com/real/dep v1.2.3\n)\n"
    )
    diff = _make_go_diff(
        [
            'import "fmt"',  # std → 不报
            '\t"github.com/real/dep"',  # 已声明 → 不报
            '\t"github.com/real/dep/sub"',  # 子包 → 不报
            '\t"github.com/ghost/missing"',  # 未声明 → 报
            '\t"github.com/me/proj/internal"',  # 本项目 → 不报
        ]
    )
    ctx = CheckContext(
        repo=tmp_path, python_deps=None, graph=None, go_deps=load_go_deps(tmp_path)
    )
    findings = HallucinatedImport().run(parse_unified_diff(diff), ctx)
    msgs = " ".join(f.message for f in findings)
    assert len(findings) == 1
    assert "github.com/ghost/missing" in msgs
