"""检查项集合。

A 层（确定性）：
- hallucinated-import   幻觉/未声明 import（依赖清单）
- stub-implementation   占位实现（AST）
- swallowed-exception   吞异常（AST）
- hallucinated-symbol   幻觉的内部符号（图谱）
- reuse-existing        重复造轮子，建议复用（图谱，INFO）

B 层（LLM 语义，需 --enable-llm + key）：
- fake-test             假测试
- scope-creep           超范围改动（INFO）
"""

from .fake_test import FakeTest
from .hallucinated_import import HallucinatedImport
from .hallucinated_symbol import HallucinatedSymbol
from .reuse import ReuseExisting
from .scope_creep import ScopeCreep
from .stub import StubImplementation
from .swallow import SwallowedException

ALL_CHECKS = [
    HallucinatedImport(),
    StubImplementation(),
    SwallowedException(),
    HallucinatedSymbol(),
    ReuseExisting(),
    FakeTest(),
    ScopeCreep(),
]
