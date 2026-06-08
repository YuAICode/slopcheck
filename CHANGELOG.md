# Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## v0.1.0 — 2026-06-08

首个发布。专审 **AI 生成代码**的特有失败模式，用知识图谱做确定性事实校验。

### 检查项
- **A 层（确定性）**：`hallucinated-import`、`stub-implementation`、`swallowed-exception`
- **A 层（图谱）**：`hallucinated-symbol`、`reuse-existing`、`missing-test`
- **B 层（LLM，可选 `--enable-llm`）**：`fake-test`、`scope-creep`

### 多语言
- **Python**：全部检查（内置 AST）
- **JS/TS**：`hallucinated-import` + `stub-implementation`（throw-only 桩）+ `swallowed-exception`（空 catch）
- **Go**：`hallucinated-import` + `stub-implementation`（panic-only 桩）

### 集成
- CLI：`terminal` / `json` / `github` 三种输出
- GitHub Action：PR sticky 汇总评论 + 行级 inline 评论

### 设计
- 与通用 LLM review 的区别：用 graphify 知识图谱做**确定性**事实校验（幻觉调用、复用、测试覆盖），不靠 LLM 猜
- 核心零运行时依赖；LLM 与多语言为可选依赖（`[llm]` / `[multilang]`）
