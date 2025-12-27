from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AgentContext:
    request_id: Optional[str] = None
    user: Optional[str] = None
    metadata: Dict[str, Any] = None


class BaseAgent:
    """Minimal agent contract.

    Implement `run_task(context, payload)` in concrete agents.
    """

    def __init__(self, name: str = "base"):
        self.name = name

    def run_task(self, context: AgentContext, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("run_task must be implemented by agents")
