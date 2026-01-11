import requests


def q(path):
    url = f"http://127.0.0.1:8000{path}"
    try:
        r = requests.get(url, timeout=5)
        print(path, r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text[:1000])
    except Exception as e:
        print(path, "ERROR", e)


q("/health")
q("/api/agents/headless_team")
