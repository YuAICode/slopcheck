"""加载 Python 项目的依赖清单 + 本地模块，用于判断某 import 是否"已知"。

未知 import = 可能是 AI 幻觉的包 / 未声明依赖（slopsquatting 供应链风险）。
"""

from __future__ import annotations

import json
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


# ---- JS / TS ----

_NODE_BUILTINS = {
    "assert", "buffer", "child_process", "cluster", "console", "crypto", "dgram",
    "dns", "events", "fs", "http", "http2", "https", "module", "net", "os", "path",
    "perf_hooks", "process", "punycode", "querystring", "readline", "stream",
    "string_decoder", "timers", "tls", "tty", "url", "util", "v8", "vm",
    "worker_threads", "zlib",
}


class JsDeps:
    def __init__(self, declared: set[str]):
        self.declared = declared  # package.json 声明的包名

    def is_known(self, pkg: str) -> bool:
        if pkg.startswith("node:"):
            return True
        return pkg in _NODE_BUILTINS or pkg in self.declared


def load_js_deps(repo: Path) -> JsDeps | None:
    pj = repo / "package.json"
    if not pj.exists():
        return None
    try:
        data = json.loads(pj.read_text())
    except (ValueError, OSError):
        return JsDeps(set())
    declared: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            declared.update(section.keys())
    return JsDeps(declared)


# ---- Go ----

_GOMOD_REQUIRE = re.compile(r"^([^\s()]+)\s+v\S+")


class GoDeps:
    def __init__(self, modules: set[str], own: str):
        self.modules = modules  # go.mod require 的 module path
        self.own = own  # 本项目 module path

    def is_known(self, imp: str) -> bool:
        first = imp.split("/")[0]
        if "." not in first:
            return True  # 无域名段 → 标准库（fmt / os / net/http ...）
        if self.own and (imp == self.own or imp.startswith(self.own + "/")):
            return True  # 本项目内部包
        return any(imp == m or imp.startswith(m + "/") for m in self.modules)


def load_go_deps(repo: Path) -> GoDeps | None:
    gm = repo / "go.mod"
    if not gm.exists():
        return None
    own = ""
    modules: set[str] = set()
    in_block = False
    for line in gm.read_text().splitlines():
        s = line.strip()
        if s.startswith("module "):
            own = s[len("module ") :].strip()
        elif s.startswith("require ("):
            in_block = True
        elif in_block and s == ")":
            in_block = False
        elif in_block:
            m = _GOMOD_REQUIRE.match(s)
            if m:
                modules.add(m.group(1))
        elif s.startswith("require "):
            m = _GOMOD_REQUIRE.match(s[len("require ") :].strip())
            if m:
                modules.add(m.group(1))
    return GoDeps(modules, own)
