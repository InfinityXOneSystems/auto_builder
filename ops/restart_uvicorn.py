import subprocess
import sys
import re
import time
import os

def kill_port(port=8000):
    try:
        out = subprocess.check_output(["netstat", "-ano"], stderr=subprocess.DEVNULL).decode(errors='ignore')
    except Exception as e:
        print("netstat failed:", e)
        return
    pids = set()
    for line in out.splitlines():
        if f":{port} " in line or line.strip().endswith(f":{port}"):
            parts = re.split(r"\s+", line.strip())
            if parts:
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(pid)
    for pid in pids:
        try:
            print(f"Killing PID {pid}")
            subprocess.run(["taskkill", "/F", "/PID", pid], check=False)
        except Exception as e:
            print(f"Failed to kill {pid}: {e}")

def start_uvicorn():
    cmd = [sys.executable, "-m", "uvicorn", "omni_gateway:app", "--host", "127.0.0.1", "--port", "8000"]
    print("Starting uvicorn:", cmd)
    proc = subprocess.Popen(cmd, cwd=os.getcwd())
    time.sleep(1)
    print("uvicorn started with pid", proc.pid)
    return proc

if __name__ == '__main__':
    kill_port(8000)
    p = start_uvicorn()
    # quick health check
    try:
        import httpx
        r = httpx.get('http://127.0.0.1:8000/health', timeout=5.0)
        print('health', r.status_code, r.text)
    except Exception as e:
        print('health check failed:', e)
