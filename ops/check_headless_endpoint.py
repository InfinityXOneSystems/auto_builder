import os
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo))
import requests

url = (
    os.environ.get("HEADLESS_GATEWAY", "http://127.0.0.1:8000")
    + "/api/agents/headless_team"
)
try:
    r = requests.get(url, timeout=5)
    print(r.status_code)
    print(r.text[:1000])
except Exception as e:
    print("ERROR", e)
