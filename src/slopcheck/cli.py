"""命令行入口：取 diff → 跑检查 → 输出，返回 CI 友好退出码。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .checks import ALL_CHECKS
from .checks.base import CheckContext
from .deps import load_python_deps
from .diff import get_git_diff, parse_unified_diff
from .graph import GraphIndex
from .models import Severity
from .output import github_output, json_output
from .output.terminal import render


def _build_llm(enable: bool, repo: Path):
    """构造 LLM judge：仅在显式启用且有 key 时；否则返回 None（B 层跳过）。"""
    if not enable or not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    from .llm import LLMJudge

    return LLMJudge()


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
        choices=["terminal", "json", "github"],
        default="terminal",
        help="输出格式（json 供 CI 集成；github 为 PR 评论 markdown）",
    )
    ap.add_argument(
        "--enable-llm",
        action="store_true",
        help="启用 B 层 LLM 检查（需 ANTHROPIC_API_KEY；默认关闭，不误花钱）",
    )
    ap.add_argument("--pr-description", default="", help="PR 描述，供 scope-creep 检查")
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
        llm=_build_llm(args.enable_llm, repo),
        pr_description=args.pr_description,
    )

    findings = []
    for check in ALL_CHECKS:
        findings.extend(check.run(files, ctx))

    renderers = {
        "terminal": render,
        "json": json_output.render,
        "github": github_output.render,
    }
    print(renderers[args.format](findings))

    has_error = any(f.severity == Severity.ERROR for f in findings)
    has_warn = any(f.severity == Severity.WARNING for f in findings)
    return 1 if (has_error or (args.strict and has_warn)) else 0


if __name__ == "__main__":
    sys.exit(main())
