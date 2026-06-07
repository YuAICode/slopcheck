"""加载 Python 项目的依赖清单 + 本地模块，用于判断某 import 是否"已知"。

未知 import = 可能是 AI 幻觉的包 / 未声明依赖（slopsquatting 供应链风险）。
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

# import 名 → 分发包名 的常见别名（import 名与 PyPI 名不一致的情况）
IMPORT_ALIASES = {
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "jose": "python-jose",
    "attr": "attrs",
    "jwt": "pyjwt",
}


def _normalize(name: str) -> str:
    """PEP 503 风格归一化：统一分隔符 + 小写。"""
    return re.sub(r"[-_.]+", "-", name).lower()


def _req_name(spec: str) -> str:
    """从 "requests>=2.0 ; extra == 'x'" 提取出 "requests"。"""
    spec = spec.split(";")[0].strip()
    return re.split(r"[<>=!~\[\s]", spec, maxsplit=1)[0].strip()


class PythonDeps:
    def __init__(self, declared: set[str], local: set[str]):
        self.declared = declared  # 归一化后的分发名集合
        self.local = local  # 本地顶层模块名

    def is_known(self, mod: str) -> bool:
        if mod in sys.stdlib_module_names:
            return True
        if mod in self.local:
            return True
        if _normalize(mod) in self.declared:
            return True
        alias = IMPORT_ALIASES.get(mod)
        if alias and _normalize(alias) in self.declared:
            return True
        return False


def load_python_deps(repo: Path) -> PythonDeps:
    declared: set[str] = set()

    pp = repo / "pyproject.toml"
    if pp.exists():
        try:
            data = tomllib.loads(pp.read_text())
        except Exception:
            data = {}
        project = data.get("project", {}) or {}
        for dep in project.get("dependencies", []) or []:
            declared.add(_normalize(_req_name(dep)))
        for grp in (project.get("optional-dependencies", {}) or {}).values():
            for dep in grp or []:
                declared.add(_normalize(_req_name(dep)))
        # poetry
        poetry = (data.get("tool", {}) or {}).get("poetry", {}) or {}
        for k in poetry.get("dependencies", {}) or {}:
            if k.lower() != "python":
                declared.add(_normalize(k))
        # uv / PEP 735 dependency-groups
        for grp in (data.get("dependency-groups", {}) or {}).values():
            for dep in grp or []:
                if isinstance(dep, str):
                    declared.add(_normalize(_req_name(dep)))

    for req in repo.glob("requirements*.txt"):
        for line in req.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                declared.add(_normalize(_req_name(line)))

    return PythonDeps(declared, _scan_local_modules(repo))


def _scan_local_modules(repo: Path) -> set[str]:
    """扫描仓库顶层（含 src/ layout）的本地包 / 模块名。"""
    names: set[str] = set()
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "graphify-out"}
    for root in (repo, repo / "src"):
        if not root.is_dir():
            continue
        for p in root.iterdir():
            if p.name in skip:
                continue
            if p.is_dir() and (p / "__init__.py").exists():
                names.add(p.name)
            elif p.is_dir() and any(p.glob("*.py")):
                names.add(p.name)  # 命名空间包 / 普通含 py 目录（宽松，降误报）
            elif p.suffix == ".py":
                names.add(p.stem)
    return names
