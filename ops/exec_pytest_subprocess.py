import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
LOG = LOGS / "pytest.log"

PY = sys.executable
cmd = [PY, "-m", "pytest", "-q", "tests"]
print("Running:", " ".join(cmd))
with open(LOG, "wb") as f:
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT)
    ret = p.wait()
    print("exit", ret)
    f.flush()

print("Tail of log:")
print(LOG.read_text()[-4000:])
sys.exit(ret)
