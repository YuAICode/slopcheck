"""AST 辅助：读源码、解析、检测占位实现(stub)与吞异常(swallow)。

约定：检测在整文件 AST 上做，调用方再用 diff 的新增行号过滤，只报本次引入的。
"""

from __future__ import annotations

import ast
from pathlib import Path

from .models import FileDiff

# 这些装饰器下的占位 body 是合法的，跳过
_SKIP_STUB_DECORATORS = {"abstractmethod", "abstractproperty", "overload"}


def read_source(repo: Path, rel: str) -> str | None:
    try:
        return (repo / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def parse(src: str) -> ast.Module | None:
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def added_linenos(f: FileDiff) -> set[int]:
    return {al.lineno for al in f.added}


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _is_ellipsis(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and stmt.value.value is Ellipsis
    )


def _name_of(node: ast.AST | None) -> str | None:
    """取 raise/装饰器表达式的名字：foo / foo() / a.b / a.b()。"""
    if node is None:
        return None
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _has_skip_decorator(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(_name_of(d) in _SKIP_STUB_DECORATORS for d in fn.decorator_list)


def find_stubs(tree: ast.Module) -> list[tuple[int, set[int], str]]:
    """找占位函数。返回 (报告行号, 相关行号集合, 占位类型)。"""
    out: list[tuple[int, set[int], str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _has_skip_decorator(node):
            continue
        real = _strip_docstring(node.body)
        if len(real) != 1:
            continue
        s = real[0]
        if isinstance(s, ast.Pass):
            kind = "pass"
        elif _is_ellipsis(s):
            kind = "..."
        elif isinstance(s, ast.Raise) and _name_of(s.exc) in {
            "NotImplementedError",
            "NotImplemented",
        }:
            kind = "raise NotImplementedError"
        else:
            continue
        out.append((s.lineno, {node.lineno, s.lineno}, kind))
    return out


def find_swallows(tree: ast.Module) -> list[tuple[int, set[int], str]]:
    """找吞异常的 except 块（块体仅 pass / ...）。"""
    out: list[tuple[int, set[int], str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if len(node.body) != 1:
            continue
        s = node.body[0]
        if isinstance(s, ast.Pass):
            kind = "pass"
        elif _is_ellipsis(s):
            kind = "..."
        else:
            continue
        out.append((node.lineno, {node.lineno, s.lineno}, kind))
    return out
