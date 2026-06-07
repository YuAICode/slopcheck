from slopcheck.llm import LLMJudge, parse_verdict


def test_parse_verdict_valid():
    v = parse_verdict('前缀 {"is_issue": true, "reason": "x"} 后缀')
    assert v["is_issue"] is True
    assert v["reason"] == "x"


def test_parse_verdict_garbage():
    assert parse_verdict("no json here") == {"is_issue": False, "reason": ""}


def test_parse_verdict_false():
    assert parse_verdict('{"is_issue": false}')["is_issue"] is False


class _FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeResp:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]


class _FakeMessages:
    def __init__(self, text):
        self._text = text
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return _FakeResp(self._text)


class _FakeClient:
    def __init__(self, text):
        self.messages = _FakeMessages(text)


def test_judge_parses_response_and_caches_system():
    client = _FakeClient('{"is_issue": true, "reason": "断言恒真"}')
    judge = LLMJudge(client=client)
    v = judge.judge("检查假测试", "def test_x(): assert True")
    assert v["is_issue"] is True
    assert "断言" in v["reason"]
    # system 必须带 cache_control，否则 prompt caching 被静默破坏
    assert client.messages.kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert client.messages.kwargs["model"] == "claude-opus-4-8"
