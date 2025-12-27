# RUNBOOK: Omni Gateway

Run and manage the gateway locally (dev):

Start:
```
python ops/run_uvicorn_bg.py start
```

Stop:
```
python ops/run_uvicorn_bg.py stop
```

Status & logs:
```
python ops/run_uvicorn_bg.py status
tail -n 200 logs/gateway_bg.log
```

Testing headless agents:
```
python ops/run_headless_test_now.py
cat tools/headless_test_results.json
```
