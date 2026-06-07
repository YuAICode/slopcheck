from slopcheck.checks.base import CheckContext
from slopcheck.checks.hallucinated_import import HallucinatedImport
from slopcheck.deps import load_python_deps
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
