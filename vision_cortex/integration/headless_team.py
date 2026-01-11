from dataclasses import dataclass
from typing import List


@dataclass
class HeadlessAgentDesc:
    id: str
    name: str
    description: str


def init_headless_team() -> List[HeadlessAgentDesc]:
    """Return a list of available headless agents as objects with attributes.

    This matches what `omni_gateway.list_headless_team` expects (objects with
    `.name` and a `__dict__` representation).
    """
    return [
        HeadlessAgentDesc(
            id="headless-crawler",
            name="headless-crawler",
            description="Fetch pages via HTTP",
        ),
    ]
