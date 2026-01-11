import json
import os
import sys
from pathlib import Path

import requests

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

gateway = os.environ.get("HEADLESS_GATEWAY", "http://127.0.0.1:8000")

out = {"gateway": gateway, "results": []}

try:
    r = requests.get(gateway + "/api/agents/headless_team", timeout=5)
    print("list:", r.status_code, r.text[:1000])
    if r.status_code != 200:
        print("Headless team endpoint not available")
    else:
        j = r.json()
        team = j.get("team", [])
        for agent in team:
            name = (
                agent.get("name")
                if isinstance(agent, dict)
                else getattr(agent, "name", None)
            )
            if not name:
                continue
            print("Testing agent", name)
            try:
                payload = {
                    "agent_name": name,
                    "url": "https://example.com",
                    "render": False,
                }
                r2 = requests.post(
                    gateway + "/api/agents/headless_team/execute",
                    json=payload,
                    timeout=15,
                )
                print("->", r2.status_code, r2.text[:1000])
                out["results"].append(
                    {
                        "agent": name,
                        "status": r2.status_code,
                        "body": r2.json() if r2.status_code == 200 else r2.text,
                    }
                )
            except Exception as e:
                out["results"].append({"agent": name, "error": str(e)})
except Exception as e:
    out["error"] = str(e)

with open("tools/headless_test_results.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("WROTE tools/headless_test_results.json")
print(json.dumps(out, indent=2))
