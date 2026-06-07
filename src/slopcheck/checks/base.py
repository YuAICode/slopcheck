"""检查项抽象基类 + 运行上下文。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..deps import PythonDeps
from ..graph import GraphIndex
from ..models import FileDiff, Finding


@dataclass
class CheckContext:
    repo: Path
    python_deps: PythonDeps | None
    graph: GraphIndex | None
    llm: object | None = None  # B 层 judge（有 .judge() 的对象），None 则跳过 LLM 检查
    pr_description: str = ""


class Check:
    id = "base"

    def run(self, files: list[FileDiff], ctx: CheckContext) -> list[Finding]:
        raise NotImplementedError
