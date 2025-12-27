from vision_cortex.agents.headless_crawler import HeadlessCrawlerAgent
from vision_cortex.agents.base_agent import AgentContext
import pytest


class DummyResponse:
    def __init__(self, text, status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}


def test_headless_crawler_fetch(monkeypatch):
    called = {}

    def fake_get(url, timeout=10.0):
        called['url'] = url
        return DummyResponse('<html><body>ok</body></html>', 200, {'content-type': 'text/html'})

    import httpx
    class FakeClient:
        def __init__(self, *a, **k):
            pass
        def get(self, url):
            return fake_get(url)
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr('vision_cortex.agents.headless_crawler.httpx.Client', FakeClient)

    agent = HeadlessCrawlerAgent(name='headless-crawler')
    ctx = AgentContext(session_id='s1', task_id='t1')
    out = agent.run_task(ctx, {'url': 'https://example.com'})
    assert out['status_code'] == 200
    assert 'content_snippet' in out
