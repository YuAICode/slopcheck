"""核心数据模型：Finding（发现）/ AddedLine / FileDiff。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# 文件扩展名 → 语言
_LANG_BY_EXT = {
    ".py": "python",
    ".js": "js",
    ".jsx": "js",
    ".ts": "js",
    ".tsx": "js",
    ".go": "go",
}


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    """一条审查发现。每条都要尽量带 evidence（证据）以降低误报争议。"""

    check: str  # 检查项 id，如 "hallucinated-import"
    severity: Severity
    path: str
    line: int
    message: str
    evidence: str = ""  # 命中的代码行 / 图谱依据
    suggestion: str = ""  # 修复建议


@dataclass
class AddedLine:
    """diff 中的一行新增代码及其在新文件里的行号。"""

    lineno: int
    text: str


@dataclass
class FileDiff:
    """单个文件的变更：路径 + 新增行集合。"""

    path: str
    added: list[AddedLine] = field(default_factory=list)

    @property
    def language(self) -> str:
        dot = self.path.rfind(".")
        ext = self.path[dot:] if dot != -1 else ""
        return _LANG_BY_EXT.get(ext, "other")
