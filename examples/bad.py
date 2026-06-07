"""故意写的"坏"样例，用于验证 slopcheck 能在 PR 上检出并评论。

预期命中：hallucinated-import（fake 包）/ stub-implementation / swallowed-exception。
"""

import os  # noqa: F401  —— stdlib，不应被报
import totally_fake_pkg_xyz  # noqa: F401  —— 幻觉/未声明包，应被报


def not_done():
    raise NotImplementedError  # 占位实现，应被报


def risky():
    try:
        int("not-a-number")
    except Exception:
        pass  # 静默吞异常，应被报
