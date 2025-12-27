class HybridOrchestrator:
    def __init__(self, app=None):
        self.app = app

    def enqueue(self, agent_id: str, payload: dict) -> dict:
        return {"enqueued": True, "agent_id": agent_id}
