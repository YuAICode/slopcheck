"""把 findings 发成 GitHub PR 行级(inline)评论。

入口 `slopcheck-review`：读 stdin 的 findings JSON（slopcheck --format json），
用 GitHub review API 在对应行发评论；sticky——先删上次 slopcheck 发的行级评论再发新的。
纯标准库 urllib，无第三方依赖。env：GH_TOKEN/GITHUB_TOKEN、REPO、PR_NUMBER、COMMIT_SHA。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

MARKER = "<!-- slopcheck-line -->"
_API = "https://api.github.com"


def build_review_comments(findings: list[dict]) -> list[dict]:
    """findings → GitHub review comments（每条带 MARKER 便于 sticky 去重）。"""
    out = []
    for f in findings:
        body = f"**`{f['check']}`** {f['message']}\n\n{MARKER}"
        out.append({"path": f["path"], "line": f["line"], "side": "RIGHT", "body": body})
    return out


def _req(method: str, path: str, token: str, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(_API + path, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"GitHub API {method} {path} -> {e.code}: {e.read().decode()[:200]}\n")
        return None


def main() -> int:
    findings = json.load(sys.stdin)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("REPO")
    pr = os.environ.get("PR_NUMBER")
    sha = os.environ.get("COMMIT_SHA")
    if not (token and repo and pr and sha):
        sys.stderr.write("缺少 GH_TOKEN/REPO/PR_NUMBER/COMMIT_SHA，跳过 inline 评论\n")
        return 0

    # sticky：先删掉上次 slopcheck 发的行级评论
    for c in _req("GET", f"/repos/{repo}/pulls/{pr}/comments", token) or []:
        if isinstance(c, dict) and MARKER in (c.get("body") or ""):
            _req("DELETE", f"/repos/{repo}/pulls/comments/{c['id']}", token)

    comments = build_review_comments(findings)
    if comments:
        _req(
            "POST",
            f"/repos/{repo}/pulls/{pr}/reviews",
            token,
            {"commit_id": sha, "event": "COMMENT", "comments": comments},
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
