"""对接 graphify 的知识图谱（graphify-out/graph.json，networkx node-link 格式）。

真实结构：
- nodes: {id, label, norm_label, source_file, source_location, ...}
  函数/方法节点 label 以 "()" 结尾；文件节点 label 以代码扩展名结尾。
- links: {relation, confidence, source, target, ...}，relation ∈
  {calls, contains, imports_from, uses, method, inherits, ...}

用途：
- 符号存在性（hallucinated-symbol）
- 符号定义位置（reuse-existing）
- 测试覆盖（missing-test）：被 test 文件节点 `calls` 的目标即视为有测试覆盖
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .astutil import is_test_file

_CODE_EXT = {"py", "pyi", "js", "jsx", "ts", "tsx", "go", "java", "rb", "rs", "c", "cpp", "h"}


def _is_file_label(label: str) -> bool:
    return "." in label and label.rsplit(".", 1)[-1].lower() in _CODE_EXT


def _strip_call(label: str) -> str:
    return label[:-2] if label.endswith("()") else label


class GraphIndex:
    def __init__(self, symbols: set[str], defs: dict[str, list[str]], tested: set[str] | None = None):
        self.symbols = symbols  # 所有函数/类符号名（含文件模块名 stem）
        self.defs = defs  # name -> 定义所在 source_file 列表
        self.tested = tested or set()  # 被测试调用覆盖的符号名

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
        nodes = data.get("nodes", []) or []
        links = data.get("links") or data.get("edges") or []
        symbols: set[str] = set()
        defs: dict[str, list[str]] = defaultdict(list)
        id_meta: dict[object, tuple[str | None, str]] = {}  # node id -> (符号名, source_file)
        for n in nodes:
            if not isinstance(n, dict):
                continue
            label = n.get("label") or n.get("norm_label")
            if not isinstance(label, str) or not label:
                continue
            sf = n.get("source_file") if isinstance(n.get("source_file"), str) else ""
            nid = n.get("id")
            if _is_file_label(label):
                symbols.add(label.rsplit(".", 1)[0])
                if nid is not None:
                    id_meta[nid] = (None, sf)
                continue
            name = _strip_call(label).split(".")[-1]
            if not name:
                continue
            symbols.add(name)
            if sf:
                defs[name].append(sf)
            if nid is not None:
                id_meta[nid] = (name, sf)

        tested: set[str] = set()
        for e in links:
            if not isinstance(e, dict) or e.get("relation") != "calls":
                continue
            src = id_meta.get(e.get("source"))
            tgt = id_meta.get(e.get("target"))
            if not src or not tgt:
                continue
            # 调用方在 test 文件 → 被调目标视为有测试覆盖
            if tgt[0] and is_test_file(src[1]):
                tested.add(tgt[0])

        return cls(symbols, dict(defs), tested)

    def has_symbol(self, name: str) -> bool:
        return name in self.symbols

    def defined_in(self, name: str) -> list[str]:
        return self.defs.get(name, [])

    def is_tested(self, name: str) -> bool:
        return name in self.tested
