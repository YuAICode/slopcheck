"""命令行入口：取 diff → 跑检查 → 输出，返回 CI 友好退出码。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import ALL_CHECKS
from .checks.base import CheckContext
from .deps import load_python_deps
from .diff import get_git_diff, parse_unified_diff
from .graph import GraphIndex
from .models import Severity
from .output import json_output
from .output.terminal import render


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="slopcheck",
        description="AI-aware code review —— 专审 AI 生成代码的验证工具",
    )
    ap.add_argument("--repo", default=".", help="仓库根目录（默认当前目录）")
    ap.add_argument("--diff-file", help="从文件读取 unified diff（默认跑 git diff）")
    ap.add_argument("--git-args", default="", help="附加给 git diff 的参数，如 'HEAD~1'")
    ap.add_argument("--strict", action="store_true", help="warning 也算失败（退出码 1）")
    ap.add_argument(
        "--format",
        choices=["terminal", "json"],
        default="terminal",
        help="输出格式（json 供 CI / Action 集成）",
    )
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    if args.diff_file:
        diff_text = Path(args.diff_file).read_text()
    else:
        diff_text = get_git_diff(str(repo), args.git_args.split() if args.git_args else [])

    files = parse_unified_diff(diff_text)
    ctx = CheckContext(
        repo=repo,
        python_deps=load_python_deps(repo),
        graph=GraphIndex.load(repo),
    )

    findings = []
    for check in ALL_CHECKS:
        findings.extend(check.run(files, ctx))

    print(json_output.render(findings) if args.format == "json" else render(findings))

    has_error = any(f.severity == Severity.ERROR for f in findings)
    has_warn = any(f.severity == Severity.WARNING for f in findings)
    return 1 if (has_error or (args.strict and has_warn)) else 0


if __name__ == "__main__":
    sys.exit(main())
