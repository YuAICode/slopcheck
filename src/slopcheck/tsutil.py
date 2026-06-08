"""tree-sitter 适配层。

封装 language-pack 自带 binding 的"方法风格"API（node.kind() / start_byte() /
child_count() / child(i) / root_node() 都是方法）。

未安装 [multilang] 时 parser_for 返回 None，调用方据此跳过 —— 核心保持零依赖。
"""

from __future__ import annotations


def parser_for(lang: str):
    """lang: 'javascript' | 'go' 等。未装 tree-sitter 或不支持则返回 None。"""
    try:
        from tree_sitter_language_pack import get_parser
    except Exception:
        return None
    try:
        return get_parser(lang)
    except Exception:
        return None


def root_node(parser, src: str):
    return parser.parse(src).root_node()


def kind(n) -> str:
    return n.kind()


def children(n) -> list:
    return [n.child(i) for i in range(n.child_count())]


def named_children(n) -> list:
    return [n.named_child(i) for i in range(n.named_child_count())]


def text_of(n, src_bytes: bytes) -> str:
    return src_bytes[n.start_byte() : n.end_byte()].decode("utf8", "ignore")


def line_of(n, src_bytes: bytes) -> int:
    return src_bytes[: n.start_byte()].count(b"\n") + 1


def iter_kind(root, kinds: set[str]):
    stack = [root]
    while stack:
        n = stack.pop()
        if kind(n) in kinds:
            yield n
        stack.extend(children(n))


def body_block(fn):
    """函数节点的 body（JS: statement_block / Go: block）。"""
    for c in children(fn):
        if kind(c) in ("statement_block", "block"):
            return c
    return None
