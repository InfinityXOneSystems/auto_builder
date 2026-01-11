import json
import os
import sys
from pathlib import Path

import requests

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

gateway = os.environ.get("HEADLESS_GATEWAY", "http://127.0.0.1:8000")
out = {"gateway": gateway, "results": []}


def safe_get(path):
    try:
        r = requests.get(gateway + path, timeout=10)
        return r.status_code, r
    except Exception as e:
        return None, e


def safe_post(path, json_payload):
    try:
        r = requests.post(gateway + path, json=json_payload, timeout=30)
        return r.status_code, r
    except Exception as e:
        return None, e


code, r = safe_get("/api/agents/headless_team")
if code != 200:
    out["error"] = f"failed to list headless team: {r}"
else:
    team = r.json().get("team", [])
    for a in team:
        # agent may be dict or object representation
        if isinstance(a, dict):
            name = a.get("name") or a.get("id")
        else:
            name = getattr(a, "name", None)
        if not name:
            continue
        payload = {"agent_name": name, "url": "https://example.com", "render": False}
        code2, r2 = safe_post("/api/agents/headless_team/execute", payload)
        if code2 == 200:
            try:
                body = r2.json()
            except Exception:
                body = r2.text
            out["results"].append({"agent": name, "status": code2, "body": body})
        else:
            out["results"].append({"agent": name, "status": code2, "error": str(r2)})

out_path = repo_root / "tools" / "headless_test_results.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print("WROTE", str(out_path))
print(json.dumps(out, indent=2))
