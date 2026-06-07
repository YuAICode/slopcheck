# Spec：`slopcheck` —— 专审 AI 生成代码的验证工具（代号待定）

> 起草日期：2026-06-08
> 来源：项目选型梳理「方向 E1 —— AI 代码验证」
> 形态：**独立产品**（CLI + GitHub Action），不绑 Claude 生态，受众=所有用 GitHub 的开发者。
> 一句话：通用 review 工具审"所有代码"，`slopcheck` 只盯**AI 写的代码的特有失败模式**，并用**代码知识图谱做确定性事实校验**——抓纯 LLM review 抓不住的幻觉。

---

## 1. 问题与动机

- AI 生成的 PR 已从一年前的 1% 涨到 **27.6%**，瓶颈从"写代码"转到"**没人审得过来**"。
- AI 代码有**区别于人类 bug 的特有失败模式**：幻觉 API、幻觉依赖、架构漂移、假测试、占位实现、scope creep。
- 现有通用 AI review（Greptile / CodeRabbit / Sourcegraph）**主要靠 LLM 读 diff**——但 LLM **自己也会幻觉**，对"这个调用在项目里到底存不存在"这类事实问题不可靠。

**切入点**：不做"又一个通用 review"，专攻 **AI-aware review**，且把"事实校验"交给**确定性的知识图谱**而非 LLM。

---

## 2. 差异化（护城河）

| | 通用 AI review | **slopcheck（E1）** |
| --- | --- | --- |
| 审什么 | 所有代码、通用 bug/风格 | **专盯 AI 代码的特有失败模式** |
| 怎么判 | 主要靠 LLM 读 diff | **图谱做确定性事实校验** + LLM 语义层 |
| 幻觉调用/import | LLM 自己也可能看不出 | **图谱查符号是否真实存在 → 确定性命中、零误报** |
| 复用缺失 | 弱 | 图谱找已有等价实现 → 提示"别重造，用 X" |
| 成本 | 常全量喂 LLM | **只审 diff + 图谱拉的 blast radius**，省 token |

**核心武器 = 你的 `code-review-graph` / graphify**。图谱不是附属，是确定性校验和上下文裁剪的引擎。

---

## 3. 检查项清单（按置信度分两层）

### A 层 — 确定性（图谱/AST，不靠 LLM，**目标零误报**）
1. **幻觉调用**：diff 中调用的函数/方法/符号在项目+依赖里**不存在**。
2. **幻觉 import / 包**：import 的模块/包不在依赖清单（`package.json`/`go.mod`/`requirements`）→ 顺带防 **slopsquatting**（AI 编造的包名被恶意抢注的供应链风险）。
3. **签名不符**：调用的参数个数/名与定义不一致。
4. **复用缺失**：新增函数与图谱中已有函数高度相似 → 建议复用。
5. **占位/未实现**：`TODO`/空函数体/`raise NotImplementedError`/`throw new Error("not implemented")`。
6. **吞异常**：空 `catch` / `except: pass`。

### B 层 — LLM 语义（带图谱上下文，**每条必须给证据**，靠规则降误报）
7. **假测试**：新增测试断言恒真、或没真正覆盖新增逻辑。
8. **漏测**：新增公共函数在图谱里 `tests_for` 为空。
9. **scope creep**：改了 PR 描述/范围之外的东西。
10. **架构漂移**：违反项目分层/约定（把图谱社区结构当上下文喂给 LLM）。
11. **风格/命名不一致**：与周边代码不一致。

> A 层是卖点和信任锚（确定性、可解释）；B 层提供深度但严格控误报。

---

## 4. 范围与里程碑

| 里程碑 | 内容 | 验收锚点 |
| --- | --- | --- |
| **M1（CLI MVP）** | 取 diff → 解析 → **A 层全部**（幻觉调用/import/签名/复用/占位/吞异常）→ 终端输出。单语言起步 | 在一个真实仓库的 AI 生成 PR 上，能确定性抓出幻觉调用/import，零误报 |
| **M2** | **GitHub Action**（PR inline 评论）+ **B 层**（假测试/漏测/scope creep）+ 误报抑制 | PR 上自动评论；B 层每条带证据行号；可配严格度 |
| **M3** | 多语言 + **SARIF 输出**（进 GitHub Code Scanning）+ 规则配置化 + 可选 SaaS/webhook | 多语言可用；SARIF 被 GitHub 安全面板识别 |

### 非目标
- 不做通用 linter / 格式化（交给 eslint/gofmt）。
- 不做"自动改"（首版只报，不动用户代码）。
- 不做 IDE 实时插件（首版聚焦 PR/CI 这个真痛点环节）。

---

## 5. 架构

```
        ┌─────────┐   ┌──────────────┐   ┌───────────────────┐   ┌──────────────┐
 diff → │ 解析/AST │ → │ 图谱锚定校验   │ → │ LLM 语义层(带上下文) │ → │ 聚合裁决/输出  │
        └─────────┘   │ (A 层,确定性) │   │ (B 层,需证据)       │   └──────────────┘
                      └──────────────┘   └───────────────────┘
                            ↑                      ↑
                      code-review-graph      图谱拉 blast radius 做上下文裁剪
```

- **输入**：`git diff`（本地）或 PR diff（Action）。
- **图谱锚定**：对 diff 里每个新增的调用/import/符号，查图谱+依赖清单是否存在 → A 层 findings。
- **上下文裁剪**：用图谱 `get_impact_radius` 只取相关节点喂 LLM，控成本。
- **聚合裁决**：A 层高置信直接报；B 层带证据、按阈值过滤。
- **输出适配器**：终端 / PR 评论 / SARIF。

---

## 6. 技术选型（待你拍板）

- **引擎复用**：优先**复用现有 `code-review-graph` / graphify**（Python + tree-sitter + 图）当核心，E1 作为它上面的 "AI-review" 层 —— **最大化吃老本，少从零**。
  - 前置调研项：确认 graphify 能否作为**库/本地服务**被调用（而非只在 MCP 里）。
- **语言**：
  - 若复用 graphify → **Python**；CLI 用 `uvx` 分发，Action 用 Docker container action。
  - **备选 Go**：tree-sitter Go binding 重写精简图，**单二进制分发最爽**，但放弃 graphify 老本。
  - 推荐：**先 Python 复用老本跑通 MVP**，分发摩擦用 Docker Action 解决；除非你更看重 Go 单二进制。
- **LLM（B 层）**：调 Claude API（`claude-haiku` 跑量、`claude-sonnet` 跑难判定），**用 prompt caching 缓存项目规则/上下文**降成本。模型可配置（也支持其他 provider）。

---

## 7. 误报控制（review 工具的生死线）

- **A 层**：确定性命中，附"图谱里查无此符号 + 行号"作证据 → 不吵。
- **B 层**：① 每条 finding 必须带证据（行号 + 一句理由）；② 可配 `--strict` 级别；③ 高风险条目可走对抗式二次确认（让 LLM 尝试反驳自己，反驳不掉才报）。
- **基线模式**：`--baseline` 只报本次 diff 引入的新问题，不翻旧账。

---

## 8. 成本与性能

- 只处理 diff + 图谱裁剪后的上下文，不全量喂仓库。
- A 层纯本地计算，零 LLM 成本；B 层才调模型。
- prompt caching 缓存"项目约定/规则"前缀，多文件审查命中缓存。

---

## 9. 项目结构（以 Python 复用方案为例）

```
slopcheck/
├── pyproject.toml          # 入口 bin: slopcheck
├── src/slopcheck/
│   ├── cli.py              # 取 diff、跑 pipeline、选输出
│   ├── diff.py             # 解析 git/PR diff → 变更符号
│   ├── graph.py            # 对接 code-review-graph（查符号/依赖/复用/影响半径）
│   ├── checks/
│   │   ├── deterministic/  # A 层：hallucinated_call / import / signature / reuse / stub / swallow
│   │   └── semantic/       # B 层：fake_test / missing_test / scope_creep / drift
│   ├── llm.py              # LLM 调用 + prompt caching + 证据约束
│   ├── verdict.py          # 聚合 + 误报过滤
│   └── output/             # terminal / pr_comment / sarif
├── action/                 # GitHub Action（Dockerfile + action.yml）
├── tests/                  # 离线测试：喂构造的 AI-slop diff，断言命中（沿用 ai-skills 测试哲学）
└── README.md
```

---

## 10. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 误报多 → 开发者关掉它 | A 层确定性优先、B 层带证据+严格度可调+baseline 模式 |
| graphify 不易作库复用 | M1 前先做 1 天调研；不行则 fallback 到独立 tree-sitter 解析 |
| 红海（Greptile/CodeRabbit） | 不正面竞通用 review，**专打"审 AI 代码 + 确定性事实校验"细分** |
| LLM 成本 | A 层免费、diff+裁剪上下文、prompt caching、可选小模型 |
| 多语言工作量 | MVP 单语言，按图谱已支持的语言逐步加 |

---

## 11. 验收标准（M1）

- [ ] `slopcheck <repo>` 能对当前 `git diff` 跑 A 层全部检查。
- [ ] 在构造的"AI-slop" diff（含幻觉调用 + 幻觉 import）上，**确定性命中、零误报**，每条带行号证据。
- [ ] 复用检测：新增与已有重复的函数能提示复用目标。
- [ ] 离线测试覆盖每个 A 层检查的命中 + 不命中两路。
- [ ] 终端输出清晰（文件:行 + 类型 + 证据 + 建议）。

---

## 12. 分发与商业

- **CLI**：`uvx slopcheck`（或 Go 二进制）。
- **GitHub Action**：marketplace 上架，README 给 workflow 示例（PR 上自动评论）。
- **商业路径**：开源 CLI 引流 + 团队版 SaaS（webhook、面板、规则托管），对标 CodeRabbit 的"细分专精"打法。
- 差异化标语候选：*"AI writes it, slopcheck proves it's real."*

---

## 13. 下一步

1. 你拍板：**复用 graphify(Python) / 还是 Go 单二进制**。
2. 先花 ~1 天确认 code-review-graph 能否作库/服务调用（决定走复用还是 fallback）。
3. 我起 **M1 脚手架**：diff 解析 + 图谱对接 + A 层第一个检查（幻觉 import，最易出彩、最能防供应链风险）+ 测试骨架。
