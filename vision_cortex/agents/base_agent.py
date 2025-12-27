from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AgentContext:
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    governance_level: Optional[str] = None
    tags: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class BaseAgent:
    """Minimal agent contract.

    Implement `run_task(context, payload)` in concrete agents.
    """

    def __init__(self, name: str = "base"):
        self.name = name

    def run_task(self, context: AgentContext, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("run_task must be implemented by agents")
