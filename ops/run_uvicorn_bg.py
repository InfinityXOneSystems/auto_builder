"""Start uvicorn in background, capture logs to logs/gateway_bg.log, and write PID file.

Usage: python ops/run_uvicorn_bg.py start|stop|status
"""
import sys
import subprocess
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'gateway_bg.log'
PID_FILE = LOG_DIR / 'gateway_bg.pid'

PYTHON = sys.executable

def start():
    if PID_FILE.exists():
        print('PID file exists, gateway may already be running')
        return 1
    cmd = [PYTHON, '-m', 'uvicorn', 'omni_gateway:app', '--host', '127.0.0.1', '--port', '8000']
    print('Starting:', ' '.join(cmd))
    f = open(LOG_FILE, 'ab')
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT, env={**dict(**{**dict()}), **dict(PYTHONPATH=str(ROOT))})
    # write pid
    PID_FILE.write_text(str(proc.pid))
    # give it a moment
    time.sleep(1)
    print('Started PID', proc.pid)
    return 0

def stop():
    if not PID_FILE.exists():
        print('PID file not found')
        return 1
    pid = int(PID_FILE.read_text())
    try:
        import psutil
        p = psutil.Process(pid)
        p.terminate()
        p.wait(timeout=5)
    except Exception:
        try:
            import os
            os.kill(pid, 9)
        except Exception as e:
            print('Failed to kill process', e)
    PID_FILE.unlink(missing_ok=True)
    print('Stopped', pid)
    return 0

def status():
    if PID_FILE.exists():
        print('PID file exists:', PID_FILE.read_text())
    else:
        print('No PID file')
    if LOG_FILE.exists():
        print('Log tail:')
        print(LOG_FILE.read_text()[-2000:])

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: start|stop|status')
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == 'start':
        sys.exit(start())
    if cmd == 'stop':
        sys.exit(stop())
    if cmd == 'status':
        status(); sys.exit(0)
    print('Unknown command')
    sys.exit(2)
