"""解析 unified diff，提取每个文件的新增行（含正确的新文件行号）。"""

from __future__ import annotations

import re
import subprocess

from .models import AddedLine, FileDiff

# @@ -a,b +c,d @@ —— 取新文件起始行号 c
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_unified_diff(text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    cur: FileDiff | None = None
    new_lineno = 0

    for line in text.splitlines():
        if line.startswith("\\"):  # "\ No newline at end of file"
            continue
        if line.startswith("+++ "):
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            if path == "/dev/null":
                cur = None
                continue
            cur = FileDiff(path=path)
            files.append(cur)
            continue
        if line.startswith("--- ") or line.startswith("diff ") or line.startswith("index "):
            continue
        m = _HUNK.match(line)
        if m:
            new_lineno = int(m.group(1))
            continue
        if cur is None:
            continue
        if line.startswith("+"):
            cur.added.append(AddedLine(lineno=new_lineno, text=line[1:]))
            new_lineno += 1
        elif line.startswith("-"):
            pass  # 删除行不推进新文件行号
        else:
            new_lineno += 1  # 上下文行

    return files


def get_git_diff(repo: str, args: list[str]) -> str:
    """跑 `git -C <repo> diff <args>` 取 working tree 变更。"""
    proc = subprocess.run(
        ["git", "-C", repo, "diff", *args],
        capture_output=True,
        text=True,
    )
    return proc.stdout
