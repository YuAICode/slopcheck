from slopcheck.diff import parse_unified_diff

DIFF = """diff --git a/foo.py b/foo.py
index e69de29..1234567 100644
--- a/foo.py
+++ b/foo.py
@@ -0,0 +1,3 @@
+import os
+import requests
+x = 1
"""


def test_parse_added_lines_and_numbers():
    files = parse_unified_diff(DIFF)
    assert len(files) == 1
    f = files[0]
    assert f.path == "foo.py"
    assert f.language == "python"
    texts = [a.text for a in f.added]
    assert texts == ["import os", "import requests", "x = 1"]
    assert [a.lineno for a in f.added] == [1, 2, 3]


def test_dev_null_ignored():
    diff = """--- a/gone.py
+++ /dev/null
@@ -1,1 +0,0 @@
-print('bye')
"""
    assert parse_unified_diff(diff) == []
