import json

from slopcheck.models import Finding, Severity
from slopcheck.output import json_output
from slopcheck.output.terminal import render

_F = [
    Finding(
        check="x",
        severity=Severity.WARNING,
        path="a.py",
        line=3,
        message="m",
        evidence="e",
        suggestion="s",
    )
]


def test_terminal_empty():
    assert "未发现问题" in render([])


def test_terminal_nonempty():
    out = render(_F)
    assert "a.py:3" in out
    assert "[x]" in out


def test_json_roundtrip():
    data = json.loads(json_output.render(_F))
    assert data[0]["check"] == "x"
    assert data[0]["severity"] == "warning"
    assert data[0]["line"] == 3


def test_json_empty():
    assert json.loads(json_output.render([])) == []
