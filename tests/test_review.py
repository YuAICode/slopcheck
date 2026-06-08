from slopcheck._review import MARKER, build_review_comments


def test_build_review_comments():
    findings = [
        {"check": "stub-implementation", "line": 11, "path": "a.py", "message": "占位"},
        {"check": "hallucinated-import", "line": 7, "path": "b.py", "message": "幻觉"},
    ]
    comments = build_review_comments(findings)
    assert len(comments) == 2
    assert comments[0]["path"] == "a.py"
    assert comments[0]["line"] == 11
    assert comments[0]["side"] == "RIGHT"
    assert "stub-implementation" in comments[0]["body"]
    assert MARKER in comments[0]["body"]  # sticky 去重靠它


def test_build_review_comments_empty():
    assert build_review_comments([]) == []
