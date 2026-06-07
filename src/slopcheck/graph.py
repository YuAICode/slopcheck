"""对接 graphify 的知识图谱（graphify-out/graph.json，networkx node-link 格式）。

真实结构：
- nodes: {label, norm_label, source_file, source_location, id, ...}
  函数/方法节点的 label 以 "()" 结尾；文件节点 label 以代码扩展名结尾。
- links: {relation, confidence, source, target, ...}，relation ∈
  {calls, contains, imports_from, uses, method, inherits, ...}

M1.x 用到：符号存在性（hallucinated-symbol）+ 符号定义位置（reuse）。
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

_CODE_EXT = {"py", "pyi", "js", "jsx", "ts", "tsx", "go", "java", "rb", "rs", "c", "cpp", "h"}


def _is_file_label(label: str) -> bool:
    return "." in label and label.rsplit(".", 1)[-1].lower() in _CODE_EXT


def _strip_call(label: str) -> str:
    return label[:-2] if label.endswith("()") else label


class GraphIndex:
    def __init__(self, symbols: set[str], defs: dict[str, list[str]]):
        self.symbols = symbols  # 所有函数/类符号名（含文件模块名 stem）
        self.defs = defs  # name -> 定义所在的 source_file 列表

    @classmethod
    def load(cls, repo: Path) -> "GraphIndex | None":
        gp = repo / "graphify-out" / "graph.json"
        if not gp.exists():
            return None
        try:
            data = json.loads(gp.read_text())
        except Exception:
            return None
        return cls.from_data(data)

    @classmethod
    def from_data(cls, data: dict) -> "GraphIndex":
        symbols: set[str] = set()
        defs: dict[str, list[str]] = defaultdict(list)
        for n in data.get("nodes", []) or []:
            if not isinstance(n, dict):
                continue
            label = n.get("label") or n.get("norm_label")
            if not isinstance(label, str) or not label:
                continue
            if _is_file_label(label):
                # 文件节点：模块名（去扩展名）也算已知，避免 `from pkg import submod` 误报
                symbols.add(label.rsplit(".", 1)[0])
                continue
            name = _strip_call(label).split(".")[-1]
            if not name:
                continue
            symbols.add(name)
            sf = n.get("source_file")
            if isinstance(sf, str):
                defs[name].append(sf)
        return cls(symbols, dict(defs))

    def has_symbol(self, name: str) -> bool:
        return name in self.symbols

    def defined_in(self, name: str) -> list[str]:
        return self.defs.get(name, [])
