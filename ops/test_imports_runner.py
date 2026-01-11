import importlib
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path (repo root is parent of ops/)
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

mods = [
    "vision_cortex",
    "vision_cortex.integration.headless_team",
    "vision_cortex.agents.headless_crawler",
]

out = {}
for m in mods:
    try:
        importlib.import_module(m)
        out[m] = {"ok": True}
    except Exception as e:
        out[m] = {"ok": False, "error": str(e)}

print(json.dumps(out, indent=2))
