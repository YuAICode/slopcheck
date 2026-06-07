from slopcheck.graph import GraphIndex

# 模拟 graphify 真实节点格式（函数 label 带 ()，文件 label 带扩展名）
DATA = {
    "nodes": [
        {"label": "parse_diff()", "source_file": "src/diff.py"},
        {"label": "GraphIndex", "source_file": "src/graph.py"},
        {"label": "diff.py", "source_file": "src/diff.py"},
    ],
    "links": [],
}


def test_from_data_symbols():
    idx = GraphIndex.from_data(DATA)
    assert idx.has_symbol("parse_diff")  # 去掉尾部 ()
    assert idx.has_symbol("GraphIndex")  # 类
    assert idx.has_symbol("diff")  # 文件模块 stem
    assert not idx.has_symbol("nonexistent")


def test_defined_in():
    idx = GraphIndex.from_data(DATA)
    assert idx.defined_in("parse_diff") == ["src/diff.py"]
    assert idx.defined_in("ghost") == []


def test_missing_graph_returns_none(tmp_path):
    assert GraphIndex.load(tmp_path) is None
