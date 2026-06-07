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


class Check:
    id = "base"

    def run(self, files: list[FileDiff], ctx: CheckContext) -> list[Finding]:
        raise NotImplementedError
