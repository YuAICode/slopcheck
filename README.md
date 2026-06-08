# slopcheck

[![CI](https://github.com/YuAICode/slopcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/YuAICode/slopcheck/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/slopcheck.svg)](https://pypi.org/project/slopcheck/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://pypi.org/project/slopcheck/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

> AI-aware code review —— 专审 **AI 生成代码**的特有失败模式，用代码知识图谱做**确定性事实校验**。
> 通用 review 工具靠 LLM 读 diff（LLM 自己也会幻觉）；slopcheck 用 [graphify](https://github.com/) 的图谱确定性地回答"这个调用/包到底存不存在"。

详细设计见 [`docs/DESIGN.md`](./docs/DESIGN.md)。

## 状态：v0.1.0

A 层（确定性 + 图谱）+ B 层（LLM）+ 多语言（Python / JS / Go）+ GitHub Action 均已就位。

| 层 | 检查 | 状态 |
| --- | --- | --- |
| A（确定性） | hallucinated-import | ✅ M1 |
| A（纯 AST） | stub-implementation / swallowed-exception | ✅ M1.x |
| A（图谱） | hallucinated-symbol / reuse-existing / missing-test | ✅ |
| A（图谱） | signature-mismatch | ⬜ |
| B（LLM，需 `--enable-llm`） | fake-test / scope-creep | ✅ |
| B（LLM） | drift | ⬜（暂不做，易误报） |

**语言支持**：
- **Python**：全部检查（内置 AST）。
- **JS/TS**：`hallucinated-import`（package.json + node 内置）、`stub-implementation`（throw-only 桩）、`swallowed-exception`（空 catch）。
- **Go**：`hallucinated-import`（go.mod + std）、`stub-implementation`（panic-only 桩）。

> JS/Go 的 AST 类检查需可选依赖 `[multilang]`（tree-sitter）：`uv sync --extra multilang`。未装时这些检查自动跳过，不影响 Python 与 import 检查。

## 安装

```bash
# 直接用，无需安装（推荐）
uvx slopcheck --help

# 或装进环境
pip install slopcheck

# 启用可选功能：LLM 检查 / JS·Go 多语言检查
pip install 'slopcheck[llm,multilang]'
```

## 用法

```bash
# 审当前 git 改动（working tree）
uv run slopcheck --repo /path/to/repo

# 审某个 diff 文件（CI / PR 场景）
uv run slopcheck --repo /path/to/repo --diff-file pr.diff

# 审到上一个提交的变更
uv run slopcheck --repo /path/to/repo --git-args 'HEAD~1'

# warning 也算失败（默认 hallucinated-import 是 warning，不致 CI 失败）
uv run slopcheck --strict ...

# 启用 B 层 LLM 检查（需 anthropic 包 + ANTHROPIC_API_KEY；默认关闭，不误花钱）
uv run --extra llm slopcheck --enable-llm --pr-description "本 PR 做了 X" --repo /path/to/repo
```

## 用作 GitHub Action

在目标仓库加 `.github/workflows/slopcheck.yml`：

```yaml
name: slopcheck
on: pull_request
permissions:
  contents: read
  pull-requests: write        # 用于在 PR 上发评论
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0       # 需要完整历史才能算 PR diff
      - uses: YuAICode/slopcheck@main
        with:
          strict: "false"      # 设 "true" 则有问题时让 CI 失败
```

会在 PR 上发一条 sticky 评论汇总发现（重复运行只更新同一条）。

> 注：图谱类检查（`hallucinated-symbol` / `reuse-existing`）需要目标仓库存在
> `graphify-out/graph.json`；没有时这两项自动跳过，`hallucinated-import` /
> `stub-implementation` / `swallowed-exception` 三项照常工作。

## 开发

```bash
uv run pytest        # 离线测试，零外部依赖
```

## 架构（M1）

```
diff → parse_unified_diff → checks(A层) → terminal 输出
                              ↑
              deps（依赖清单/本地模块） + graph.json（M2 用）
```

- `diff.py` 解析 unified diff，提取新增行 + 正确行号
- `deps.py` 加载 pyproject/requirements + 本地模块，判定 import 是否已知（含别名表）
- `graph.py` 加载 `graphify-out/graph.json`，符号索引（供 M2 的幻觉调用/复用检查）
- `checks/` 检查项；`output/` 输出适配器
