"""验证 inline 行级评论用的坏样例。"""

import os  # noqa: F401  —— stdlib，不应被报
import another_fake_pkg_qwe  # noqa: F401  —— 幻觉包，应被报


def todo_here():
    raise NotImplementedError  # 占位实现，应被报


def eats_error():
    try:
        int("nope")
    except Exception:
        pass  # 静默吞异常，应被报
