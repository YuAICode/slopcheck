"""JSON 输出（机器可读，供 CI / GitHub Action 集成）。"""

from __future__ import annotations

import json

from ..models import Finding


def render(findings: list[Finding]) -> str:
    return json.dumps(
        [
            {
                "check": f.check,
                "severity": f.severity.value,
                "path": f.path,
                "line": f.line,
                "message": f.message,
                "evidence": f.evidence,
                "suggestion": f.suggestion,
            }
            for f in findings
        ],
        ensure_ascii=False,
        indent=2,
    )
