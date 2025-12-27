from .base_agent import BaseAgent, AgentContext
from typing import Dict, Any
import httpx


class HeadlessCrawlerAgent(BaseAgent):
    def __init__(self, name: str = "headless-crawler", role: str = None, bus=None):
        super().__init__(name=name)
        self.role = role
        self.bus = bus

    def run_task(self, context: AgentContext, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = payload.get("url")
        if not url:
            return {"error": "missing url in payload"}

        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
                return {
                    "status_code": r.status_code,
                    "content_snippet": r.text[:200],
                    "headers": dict(r.headers),
                }
        except Exception as e:
            return {"error": str(e)}
