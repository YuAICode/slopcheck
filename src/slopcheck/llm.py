"""B 层 LLM judge：用 Claude 做语义判定（fake-test / scope-creep 等）。

设计：
- 依赖注入——检查通过 CheckContext.llm 拿到一个有 .judge() 的对象，测试可注入 FakeLLM。
- prompt caching：judge 指令 + 项目上下文放 system 并打 cache_control，跨多次判定命中缓存。
- 结构化裁决：约束模型只输出 {"is_issue": bool, "reason": str}，容错解析。
- 默认 Opus（claude-opus-4-8）；真跑需 ANTHROPIC_API_KEY，CLI 默认不启用（不误花钱）。
"""

from __future__ import annotations

import json
import re

_JUDGE_SYSTEM = (
    "你是严格的代码审查助手。针对给定的检查任务和代码片段，判断是否存在该问题。"
    '只输出一个 JSON 对象，格式：{"is_issue": true|false, "reason": "简短中文理由"}。'
    "不要输出 JSON 以外的任何内容。保守判定：证据不足时 is_issue=false。"
)

_VERDICT_RE = re.compile(r"\{.*\}", re.S)


def parse_verdict(text: str) -> dict:
    """从模型输出里抽出裁决 JSON，容错返回 {is_issue, reason}。"""
    m = _VERDICT_RE.search(text or "")
    if not m:
        return {"is_issue": False, "reason": ""}
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return {"is_issue": False, "reason": ""}
    return {"is_issue": bool(data.get("is_issue")), "reason": str(data.get("reason", ""))}


class LLMJudge:
    def __init__(self, model: str = "claude-opus-4-8", context: str = "", client=None):
        self.model = model
        self.context = context
        self._client = client

    def _get_client(self):
        if self._client is None:
            import anthropic  # 延迟导入：未装 anthropic 也能 import 本模块

            self._client = anthropic.Anthropic()
        return self._client

    def judge(self, instruction: str, payload: str) -> dict:
        system_text = _JUDGE_SYSTEM
        if self.context:
            system_text += "\n\n项目上下文：\n" + self.context
        resp = self._get_client().messages.create(
            model=self.model,
            max_tokens=1024,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
            system=[
                {
                    "type": "text",
                    "text": system_text,  # 稳定前缀，命中缓存
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": f"检查任务：{instruction}\n\n--- 代码 ---\n{payload}"}
            ],
        )
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return parse_verdict(text)
