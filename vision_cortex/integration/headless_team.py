from typing import List, Dict


def init_headless_team() -> List[Dict[str, str]]:
    """Return a list of available headless agents descriptors.

    Each descriptor is a dict with `id`, `name`, and `description`.
    """
    return [
        {"id": "headless-crawler", "name": "Headless Crawler", "description": "Fetch pages via HTTP"}
    ]
