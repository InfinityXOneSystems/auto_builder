import importlib
import json
import traceback

modules = [
    "main_extended",
    "vision_cortex",
    "vision_cortex.integration.headless_team",
    "vision_cortex.agents.headless_crawler",
    "vision_cortex.instrumentation.observability",
    "vision_cortex.integration.agent_integration",
    "intelligence_endpoints",
    "mcp_http_adapter_ascii",
    "mcp_http_adapter",
    "credential_gateway",
    "autonomous_orchestrator",
    "langchain_integration",
    "api_dashboard",
]

report = {}
for m in modules:
    try:
        mod = importlib.import_module(m)
        report[m] = {"ok": True, "path": getattr(mod, "__file__", None)}
    except Exception as e:
        report[m] = {"ok": False, "error": repr(e), "traceback": traceback.format_exc()}

print(json.dumps(report, indent=2))
