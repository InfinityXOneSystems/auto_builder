"""
Omni Gateway - FastAPI wrapper for main_extended.py MCP server
Exposes 59 Omni Hub tools via HTTP + serves Intelligence Cockpit UI
"""
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import sys
import json
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from google.api_core.exceptions import GoogleAPIError
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from pathlib import Path as _Path

# Ensure the repository root is on sys.path so subpackages import correctly
_ROOT = _Path(__file__).resolve().parent
_ROOT_STR = str(_ROOT)
if _ROOT_STR not in sys.path:
    sys.path.insert(0, _ROOT_STR)
from pydantic import BaseModel as _BaseModel  # alias to avoid shadowing later
from typing import Optional as _Optional

# AgentContext import for headless agent endpoint
try:
    from vision_cortex.agents.base_agent import AgentContext
except Exception:
    AgentContext = None

# Optional Google client imports (fail gracefully if libs missing)
try:
    from google.cloud import secretmanager  # type: ignore
    from google.cloud import firestore      # type: ignore
    _HAS_GCP = True
except Exception:
    _HAS_GCP = False

LOG_DIR = Path(__file__).resolve().parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger('omni_gateway')
logger.setLevel(logging.INFO)
from logging.handlers import RotatingFileHandler
log_file = LOG_DIR / 'gateway.log'
handler = RotatingFileHandler(str(log_file), maxBytes=5 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logging.getLogger().addHandler(handler)

# Initialize OpenTelemetry tracing if OTLP endpoint provided
try:
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        span_processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(span_processor)
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry initialized with OTLP endpoint %s", otlp_endpoint)
except Exception:
    logger.debug("OpenTelemetry initialization skipped or failed")

# Initialize gateway environment early (centralized env loader)
try:
    # local import; gateway_env is added to the repo to centralize env handling
    from gateway_env import init_gateway_env
    init_gateway_env()
except Exception:
    # If the loader is not present or fails, continue with existing envs
    logger.debug("gateway_env not loaded or init failed; continuing with existing environment variables")

# Import Omni Hub MCP server (optional - graceful degradation)
sys.path.insert(0, os.path.dirname(__file__))
try:
    from main_extended import server as mcp_server, check_governance
    MCP_AVAILABLE = True
    logger.info("✓ MCP Server loaded successfully")
except Exception as e:
    logger.warning(f"⚠ MCP Server unavailable: {e}")
    MCP_AVAILABLE = False
    # Mock MCP server for graceful degradation
    class MockMCPServer:
        def list_tools(self): return []
        async def call_tool(self, name, args): return [type('obj', (), {'text': json.dumps({"error": "MCP unavailable"})})]
    mcp_server = MockMCPServer()
    def check_governance(tool_name): return {"level": "MEDIUM", "allowed": True, "reason": "Mock", "rate_limited": False}

app = FastAPI(
    title="Infinity XOS Omni Gateway",
    description="Intelligence Cockpit + 59 MCP Tools + Autonomous Prompt System",
    version="3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== CONFIGURATION =====
FRONTEND_SERVICE_URL = os.environ.get(
    "FRONTEND_SERVICE_URL",
    "https://frontend-service-0a277877-896380409704.us-east1.run.app"
)

# Firestore configuration
FIRESTORE_PROJECT = (
    os.environ.get("FIRESTORE_PROJECT")
    or os.environ.get("FIRESTORE_PROJECT_ID")
    or "infinity-x-one-systems"
)
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "mcp_memory")

# The 110% Protocol (enterprise-grade, abbreviated)
PROTOCOL_110 = {
    "name": "110% Protocol",
    "version": "1.0",
    "description": "Enterprise-grade FAAN Launch & Rehydrate protocol. Must accept implied YES for safe defaults.",
    "principles": [
        "Always-on observability",
        "Fail-safe defaults (assume yes for non-destructive ops)",
        "Autonomous rehydrate on boot",
        "Store critical runtime memory in Firestore",
        "Governance-first execution",
        "Full launch checklist verification"
    ],
    "checklist": [
        {"id": "c1", "name": "Credentials rotated", "status": "pending"},
        {"id": "c2", "name": "Artifact Registry present (us-east1)", "status": "pending"},
        {"id": "c3", "name": "Cloud Run deployed", "status": "pending"},
        {"id": "c4", "name": "Health endpoints responding", "status": "pending"},
        {"id": "c5", "name": "Frontend <-> Backend routing", "status": "pending"},
        {"id": "c6", "name": "Firestore memory writable", "status": "pending"},
        {"id": "c7", "name": "Autonomous prompt library available", "status": "pending"}
    ]
}

# Firestore client (lazy)
_firestore_client = None
_firestore_available = False

def _write_temp_sa_json(sa_bytes: bytes) -> str:
    """Write service account JSON bytes to a secure temp file and return its path."""
    fd, path = tempfile.mkstemp(prefix="gcp_sa_", suffix=".json")
    try:
        os.write(fd, sa_bytes)
    finally:
        os.close(fd)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    return path

def ensure_google_application_credentials_from_secret():
    """
    If GOOGLE_APPLICATION_CREDENTIALS is unset and USE_GCP_SECRET_MANAGER=true,
    fetch secret named by GCP_SECRET_NAME from Secret Manager and set env var.
    Env:
      USE_GCP_SECRET_MANAGER=true
      GCP_SECRET_NAME=projects/<project>/secrets/<name>/versions/<version>
    Returns path to written SA JSON or None.
    """
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

    if os.environ.get("USE_GCP_SECRET_MANAGER", "false").lower() != "true":
        return None

    secret_name = os.environ.get("GCP_SECRET_NAME")
    if not secret_name:
        raise RuntimeError("GCP_SECRET_NAME must be set when USE_GCP_SECRET_MANAGER=true")

    if not _HAS_GCP:
        raise RuntimeError("google-cloud-secretmanager library not available in environment")

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": secret_name})
    payload = response.payload.data  # bytes

    # quick validation
    try:
        json.loads(payload.decode("utf-8"))
    except Exception as e:
        raise RuntimeError("Secret payload is not valid JSON service account content") from e

    sa_path = _write_temp_sa_json(payload)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path
    return sa_path

def init_firestore():
    """
    Initialize and return a Firestore client.
    Attempts to load service account JSON from Secret Manager if requested
    and GOOGLE_APPLICATION_CREDENTIALS not already set.
    """
    # Try to populate GOOGLE_APPLICATION_CREDENTIALS from Secret Manager if needed
    try:
        ensure_google_application_credentials_from_secret()
    except Exception as e:
        # non-fatal here; log and continue (applying ADC if available)
        print(f"[omni_gateway] secret-manager warning: {e}")

    if not _HAS_GCP:
        raise RuntimeError("google-cloud-firestore not available; install google-cloud-firestore")

    # Create and return Firestore client (uses ADC or the SA file we wrote)
    return firestore.Client()

async def load_110_protocol():
    """Write the 110% protocol into Firestore (rehydrate on boot)."""
    client = init_firestore()
    if not client:
        logger.warning("Skipping protocol load; Firestore not available")
        return False
    try:
        doc_ref = client.collection(FIRESTORE_COLLECTION).document("protocol_110")
        doc_ref.set(PROTOCOL_110)
        logger.info(f"110% Protocol written to Firestore/{FIRESTORE_COLLECTION}/protocol_110")
        return True
    except Exception as e:
        logger.error(f"Failed to write protocol to Firestore: {e}")
        return False


# Startup event: rehydrate protocol
@app.on_event("startup")
async def on_startup_rehydrate():
    # Initialize Firestore and write protocol document (non-blocking)
    try:
        init_firestore()
        # Fire-and-forget: ensure we don't block startup for long network ops
        asyncio.create_task(load_110_protocol())
    except Exception as e:
        logger.error(f"Startup rehydrate error: {e}")


# Initialize default agents router (vision_cortex integration)
try:
    from vision_cortex.integration.agent_integration import init_agents
    app.state.agent_router = init_agents()
    logger.info("Agent router initialized and attached to app.state.agent_router")
except Exception as e:
    logger.warning(f"Failed to initialize default agent router: {e}")

# Initialize headless team registry (lightweight on-demand agents)
try:
    from vision_cortex.integration.headless_team import init_headless_team
    app.state.headless_team = init_headless_team()
    logger.info("Headless team initialized and attached to app.state.headless_team")
except Exception as e:
    logger.warning(f"Failed to initialize headless team: {e}")

# Initialize Hybrid Orchestrator (router + factory)
try:
    from vision_cortex.integration.hybrid_orchestrator import HybridOrchestrator
    app.state.hybrid_orch = HybridOrchestrator(use_celery=False)
    logger.info("HybridOrchestrator attached to app.state.hybrid_orch")
except Exception as e:
    logger.warning(f"Failed to initialize HybridOrchestrator: {e}")

# Metrics endpoint (Prometheus) - optional
try:
    from vision_cortex.instrumentation.observability import PROM_REGISTRY
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    @app.get('/metrics')
    async def metrics_endpoint():
        if not PROM_REGISTRY:
            return PlainTextResponse('')
        data = generate_latest(PROM_REGISTRY)
        return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)
except Exception:
    logger.debug('Prometheus client not available; /metrics endpoint disabled')

# ===== COCKPIT UI =====
@app.get("/", response_class=HTMLResponse)
async def serve_cockpit():
    """Serve Intelligence Cockpit UI"""
    try:
        cockpit_path = os.path.join(os.path.dirname(__file__), "cockpit.html")
        with open(cockpit_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        logger.error(f"Failed to load cockpit: {e}")
        return HTMLResponse(
            content=f"<h1>Cockpit Unavailable</h1><p>{str(e)}</p>",
            status_code=500
        )

# ===== AUTONOMOUS PROMPTS API =====
@app.get("/api/prompts")
async def get_autonomous_prompts():
    """Get autonomous prompt library (L1-L10)"""
    try:
        prompts_path = os.path.join(os.path.dirname(__file__), "AUTONOMOUS_PROMPTS.md")
        with open(prompts_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parse prompts (simple parsing - can be enhanced)
        prompts = []
        lines = content.split("\n")
        current_prompt = None
        
        for line in lines:
            if line.startswith("### "):
                if current_prompt:
                    prompts.append(current_prompt)
                current_prompt = {
                    "name": line.replace("### ", "").strip(),
                    "content": ""
                }
            elif current_prompt and line.strip():
                current_prompt["content"] += line + "\n"
        
        if current_prompt:
            prompts.append(current_prompt)
        
        return JSONResponse(content={
            "success": True,
            "count": len(prompts),
            "prompts": prompts
        })
    except Exception as e:
        logger.error(f"Failed to load prompts: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/prompts/execute")
async def execute_prompt(request: Request):
    """Execute an autonomous prompt"""
    try:
        data = await request.json()
        prompt_name = data.get("prompt_name")
        context = data.get("context", {})
        
        # Log execution
        logger.info(f"Executing autonomous prompt: {prompt_name}")
        
        # This would integrate with ChatGPT MCP or other execution engine
        return JSONResponse(content={
            "success": True,
            "prompt_name": prompt_name,
            "status": "queued",
            "message": f"Prompt '{prompt_name}' queued for execution"
        })
    except Exception as e:
        logger.error(f"Prompt execution failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ===== MCP TOOLS API =====
@app.get("/api/tools")
async def list_tools():
    """List all available MCP tools"""
    try:
        if not MCP_AVAILABLE:
            return JSONResponse(content={
                "success": False,
                "error": "MCP Server not available",
                "count": 0,
                "tools": []
            })
        
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "governance": check_governance(tool.name)
            }
            for tool in mcp_server.list_tools()
        ]
        
        return JSONResponse(content={
            "success": True,
            "count": len(tools),
            "tools": tools
        })
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

@app.post("/api/tools/execute")
async def execute_tool(tool_req: ToolRequest):
    """Execute an MCP tool"""
    try:
        # Check governance
        gov_check = check_governance(tool_req.tool_name)
        if not gov_check["allowed"]:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded or operation blocked",
                    "governance": gov_check
                }
            )
        
        # Execute tool via MCP server
        result = await mcp_server.call_tool(tool_req.tool_name, tool_req.arguments)
        
        return JSONResponse(content={
            "success": True,
            "tool": tool_req.tool_name,
            "result": str(result[0].text) if result else None
        })
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ===== CLI INTEGRATION =====
@app.post("/api/cli/execute")
async def execute_cli_command(request: Request):
    """Execute CLI commands (with governance)"""
    try:
        data = await request.json()
        command = data.get("command")
        
        # Check governance for critical commands
        if any(dangerous in command.lower() for dangerous in ["rm -rf", "del /f", "format", "shutdown"]):
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": "Command blocked by governance - critical operation"
                }
            )
        
        # Execute via orchestrator tool
        result = await mcp_server.call_tool("execute", {"command": command})
        
        return JSONResponse(content={
            "success": True,
            "command": command,
            "output": str(result[0].text) if result else None
        })
    except Exception as e:
        logger.error(f"CLI execution failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ===== SYSTEM STATUS =====
@app.get("/api/status")
async def get_system_status():
    """Get system status and metrics"""
    try:
        tools_count = len(mcp_server.list_tools()) if MCP_AVAILABLE else 0
        
        return JSONResponse(content={
            "success": True,
            "status": "operational",
            "components": {
                "omni_hub": "active" if MCP_AVAILABLE else "degraded",
                "mcp_tools": tools_count,
                "cockpit": "online",
                "frontend_service": FRONTEND_SERVICE_URL,
                "autonomous_prompts": "loaded",
                "cli_integration": "enabled"
            },
            "governance": "enforced",
            "agents_initialized": bool(getattr(app.state, "agent_router", None))
        })
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ===== FRONTEND SERVICE PROXY =====
@app.get("/frontend")
async def frontend_proxy():
    """Proxy Cloud Run frontend service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(FRONTEND_SERVICE_URL, timeout=30.0)
            return HTMLResponse(content=response.text)
    except Exception as e:
        logger.error(f"Frontend proxy failed: {e}")
        return HTMLResponse(
            content=f"<h1>Frontend Service Unavailable</h1><p>{str(e)}</p>",
            status_code=503
        )

@app.get("/frontend/api/{path:path}")
async def frontend_api_proxy(path: str, request: Request):
    """Proxy API requests to frontend service"""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{FRONTEND_SERVICE_URL}/api/{path}"
            response = await client.request(
                method=request.method,
                url=url,
                headers=dict(request.headers),
                timeout=30.0
            )
            return JSONResponse(content=response.json())
    except Exception as e:
        logger.error(f"Frontend API proxy failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Frontend service error: {str(e)}"}
        )

    @app.post("/api/chat")
    async def chat_dispatch(request: Request):
        """Minimal chat endpoint that dispatches to premade agents by intent.

        Expected JSON body:
          { "intent": "discover", "session_id": "s1", "data": {...} }
        """
        try:
            body = await request.json()
            intent = body.get("intent")
            if not intent:
                return JSONResponse(status_code=400, content={"success": False, "error": "Missing 'intent' in request body"})

            session_id = body.get("session_id") or str(int(time.time() * 1000))
            ctx = AgentContext(session_id=session_id, task_id=f"chat_{session_id}", governance_level=body.get("governance", "LOW"))

            router = getattr(app.state, "agent_router", None)
            if not router:
                return JSONResponse(status_code=503, content={"success": False, "error": "Agent router not initialized"})

            payload = {"context": ctx, "data": body.get("data", {})}

            # dispatch may be sync or async depending on agent implementations
            result = router.dispatch(intent, payload)

            return JSONResponse(content={"success": True, "intent": intent, "result": result})

        except Exception as e:
            logger.exception("Chat dispatch failed")
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


    @app.post("/api/agents/enqueue")
    async def enqueue_agent_task(request: Request):
        """Enqueue a long-running agent task via the HybridOrchestrator.

        Body JSON: { "role": "visionary", "objective": "Analyze X", "context": { ... } }
        """
        try:
            body = await request.json()
            role = body.get("role")
            objective = body.get("objective")
            context = body.get("context")
            if not role or not objective:
                return JSONResponse(status_code=400, content={"success": False, "error": "Missing role or objective"})

            orch = getattr(app.state, "hybrid_orch", None)
            if not orch:
                return JSONResponse(status_code=503, content={"success": False, "error": "HybridOrchestrator not available"})

            # Governance check for high-sensitivity operations
            gov = check_governance(role)
            if not gov.get("allowed", True):
                return JSONResponse(status_code=403, content={"success": False, "error": "Operation blocked by governance", "governance": gov})

            # API key simple auth for enqueueing (for higher trust operations)
            required_key = os.environ.get("ADMIN_API_KEY")
            if required_key:
                provided = request.headers.get("X-API-KEY")
                if provided != required_key:
                    # allow JWT bearer as alternative
                    auth = request.headers.get("Authorization", "")
                    token = None
                    if auth.lower().startswith("bearer "):
                        token = auth.split(" ", 1)[1].strip()
                    if token:
                        try:
                            from vision_cortex.auth.jwt_auth import verify_jwt
                            payload = verify_jwt(token)
                            if not payload:
                                return JSONResponse(status_code=401, content={"success": False, "error": "Invalid JWT token"})
                        except Exception:
                            return JSONResponse(status_code=401, content={"success": False, "error": "Invalid JWT token"})
                    else:
                        return JSONResponse(status_code=401, content={"success": False, "error": "Invalid API key"})

            # enqueue (runs in-process unless USE_CELERY=true)
            result = await orch.enqueue_long(role, objective, context)
            return JSONResponse(content={"success": True, "task": result})
        except Exception as e:
            logger.exception("Enqueue failed")
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


    @app.get('/api/agents/status/{task_id}')
    async def get_agent_task_status(task_id: str):
        """Return status for in-process or Celery task.

        - For in-process tasks we read the inproc store.
        - For Celery tasks users can query Celery backend directly (not implemented here).
        """
        try:
            from vision_cortex.instrumentation.observability import get_inproc_task

            entry = get_inproc_task(task_id)
            if entry:
                return JSONResponse(content={"success": True, "task": entry})
            # Celery lookup can be added here if needed
            # If Celery is used, try to read backend
            try:
                from vision_cortex.integration.celery_app import celery_app
                async_result = celery_app.AsyncResult(task_id)
                if async_result:
                    state = async_result.state
                    info = async_result.result
                    return JSONResponse(content={"success": True, "task": {"celery_state": state, "result": info}})
            except Exception:
                pass
            return JSONResponse(status_code=404, content={"success": False, "error": "task not found"})
        except Exception as e:
            logger.exception('Task status lookup failed')
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get('/api/agents/headless_team')
async def list_headless_team():
    try:
        team = getattr(app.state, "headless_team", [])
        data = [t.__dict__ for t in team]
        return JSONResponse(content={"success": True, "team": data})
    except Exception as e:
        logger.exception('List headless team failed')
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


class HeadlessRequest(_BaseModel):
    agent_name: str
    url: str
    render: _Optional[bool] = False
    timeout: _Optional[int] = 15
    no_robots: _Optional[bool] = False
    enqueue: _Optional[bool] = False


@app.post('/api/agents/headless_team/execute')
async def execute_headless_agent(req: HeadlessRequest, request: Request):
    try:
        team = getattr(app.state, "headless_team", [])
        names = [t.name for t in team]
        if req.agent_name not in names:
            return JSONResponse(status_code=404, content={"success": False, "error": "agent not found"})

        ctx = AgentContext(session_id=str(int(time.time() * 1000)), task_id=f"headless_{req.agent_name}", governance_level="LOW") if AgentContext else None
        dev_ok = request.headers.get("X-DEV-OK", "").lower() in ("1", "true", "yes") or os.environ.get("ALLOW_NO_ROBOTS", "") == "1"
        if ctx:
            ctx.tags["dev_ok"] = dev_ok

        payload = {"url": req.url, "timeout": req.timeout, "no_robots": req.no_robots}

        if req.enqueue:
            orch = getattr(app.state, "hybrid_orch", None)
            if not orch:
                return JSONResponse(status_code=503, content={"success": False, "error": "HybridOrchestrator not available"})
            result = await orch.enqueue_long("headless", f"fetch {req.url}", {"agent_name": req.agent_name, "payload": payload, "context": ctx.__dict__ if ctx else {}})
            return JSONResponse(content={"success": True, "task": result})

        try:
            from vision_cortex.agents.headless_crawler import HeadlessCrawlerAgent
            class _Bus:
                def publish(self, topic, payload):
                    pass
                def subscribe(self, topic, handler):
                    pass
            agent = HeadlessCrawlerAgent(name=req.agent_name, role="headless", bus=_Bus())
            out = agent.run_task(ctx, payload) if ctx else agent.run_task(AgentContext(session_id='local', task_id='local'), payload)
            return JSONResponse(content={"success": True, "result": out})
        except Exception as e:
            logger.exception('Headless agent run failed')
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

    except Exception as e:
        logger.exception('Execute headless agent failed')
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# Mount MCP HTTP Adapter (OpenAPI/Custom GPT compatible)
try:
    # Prefer clean ASCII adapter to avoid non-ASCII import issues
    from mcp_http_adapter_ascii import router as mcp_router
    app.include_router(mcp_router)
    logger.info("✓ MCP HTTP Adapter (ASCII) mounted: /mcp/* endpoints available")
except Exception as e:
    logger.warning(f"⚠ ASCII MCP Adapter failed: {e}; trying fallback")
    try:
        from mcp_http_adapter import router as mcp_router
        app.include_router(mcp_router)
        logger.info("✓ MCP HTTP Adapter mounted: /mcp/* endpoints available")
    except Exception as e2:
        logger.warning(f"⚠ Failed to mount MCP HTTP Adapter: {e2}")

# Alias endpoints for Custom GPT compatibility
# Some clients expect /mcp/listMCPTools and /mcp/executeMCPTool.
# Provide thin wrappers that map to the Omni Hub server directly.
@app.get("/mcp/listMCPTools")
async def mcp_list_tools_alias():
    try:
        # Read tools directly from main_extended to avoid server method quirks
        from main_extended import TOOLS as MCP_TOOLS
        tools = [
            {
                "name": getattr(tool, "name", None),
                "description": getattr(tool, "description", ""),
                "governance": check_governance(getattr(tool, "name", "")),
            }
            for tool in MCP_TOOLS
        ]
        return JSONResponse(content={"success": True, "count": len(tools), "tools": tools})
    except Exception as e:
        logger.error(f"Alias listMCPTools failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

class MCPExecuteAlias(BaseModel):
    toolName: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = {}
    dryRun: Optional[bool] = False

@app.post("/mcp/executeMCPTool")
async def mcp_execute_tool_alias(req: MCPExecuteAlias, x_mcp_key: Optional[str] = Header(None)):
    try:
        name = req.toolName or req.tool_name
        if not name:
            return JSONResponse(status_code=400, content={"success": False, "error": "Missing toolName"})

        # Allow dry-run without authentication to inspect parameters safely
        if req.dryRun:
            # Provide minimal parameter hint via governance and available registry if possible
            try:
                schema = next((t.inputSchema for t in mcp_server.list_tools() if t.name == name), {})
                params = list((schema.get("properties") or {}).keys())
            except Exception:
                params = []
            return JSONResponse(content={"success": True, "tool": name, "dry_run": True, "parameters": params})

        # Enforce SAFE_MODE for actual execution
        safe_mode = os.environ.get("SAFE_MODE", "true").lower() in ("1", "true", "yes")
        if safe_mode:
            api_key = os.environ.get("MCP_API_KEY")
            if not x_mcp_key or x_mcp_key != api_key:
                return JSONResponse(status_code=401, content={"success": False, "error": "Missing or invalid X-MCP-KEY"})

        result = await mcp_server.call_tool(name, req.arguments or {})
        payload = None
        try:
            if isinstance(result, list) and len(result) > 0 and hasattr(result[0], "text"):
                payload = json.loads(result[0].text)
            else:
                payload = result
        except Exception:
            payload = result
        return JSONResponse(content={"success": True, "tool": name, "result": payload})
    except Exception as e:
        logger.error(f"Alias executeMCPTool failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# Mount intelligence endpoints (arrival, mirror-business, pipeline-shadow)
try:
    from intelligence_endpoints import router as intelligence_router
    app.include_router(intelligence_router, prefix="/v1/intelligence")
    logger.info("Intelligence endpoints mounted: /v1/intelligence")
except Exception as e:
    logger.warning(f"Failed to mount intelligence endpoints: {e}")

# Mount credential gateway
try:
    from credential_gateway import router as credential_router
    app.include_router(credential_router)
    logger.info("✓ Credential gateway mounted: /credentials/* endpoints")
except Exception as e:
    logger.warning(f"⚠ Failed to mount credential gateway: {e}")

# Mount autonomous orchestrator
try:
    from autonomous_orchestrator import router as autonomy_router
    app.include_router(autonomy_router)
    logger.info("✓ Autonomous orchestrator mounted: /autonomy/* endpoints")
except Exception as e:
    logger.warning(f"⚠ Failed to mount autonomous orchestrator: {e}")

# Mount LangChain integration (RAG + Memory Sync + Autonomous)
try:
    from langchain_integration import router as langchain_router
    app.include_router(langchain_router)
    logger.info("✓ LangChain integration mounted: /langchain/* endpoints")
except Exception as e:
    logger.warning(f"⚠ Failed to mount LangChain integration: {e}")

# add: mount static webview folder and include dashboard router if available
BASE_DIR = Path(__file__).resolve().parent
WEBVIEW_DIR = BASE_DIR / "webview"

# Web shell static/UI
WEB_SHELL_DIR = BASE_DIR / "web_shell" / "static"

try:
    # 'app' should be the FastAPI instance created earlier in this file
    # If your app variable name differs, merge these two lines into your app init section.
    from api_dashboard import router as dashboard_router  # ensure api_dashboard.py exists in repo

    if WEBVIEW_DIR.is_dir():
        app.mount("/webview", StaticFiles(directory=str(WEBVIEW_DIR)), name="webview")

    # mount the lightweight web shell UI
    if WEB_SHELL_DIR.is_dir():
        app.mount("/web_shell", StaticFiles(directory=str(WEB_SHELL_DIR)), name="web_shell")

    # include the dashboard router to expose /api/dashboard/data
    app.include_router(dashboard_router)
    try:
        from web_shell import router as web_shell_router
        app.include_router(web_shell_router)
        print('[omni_gateway] web_shell router mounted')
    except Exception as e:
        print(f'[omni_gateway] web_shell mount skipped: {e}')
except Exception as e:
    # avoid breaking startup if dashboard module missing; log and continue
    print(f"[omni_gateway] dashboard mount/include skipped: {e}")

# ===== HEALTH CHECK =====
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={"status": "healthy", "service": "omni-gateway"})


# ===== 110% Protocol & Launch Checklist Endpoints =====
@app.get("/api/protocol")
async def get_protocol():
    """Return the in-memory 110% protocol and indicate Firestore availability"""
    return JSONResponse(content={
        "success": True,
        "protocol": PROTOCOL_110,
        "firestore": _firestore_available
    })


@app.get("/api/firestore/diagnose")
async def firestore_diagnose():
    """Run a quick Firestore diagnostic: env, credential file check, and test read/write."""
    report = {
        "firestore_project": FIRESTORE_PROJECT,
        "firestore_collection": FIRESTORE_COLLECTION,
        "firestore_available": _firestore_available,
        "google_app_creds": None,
        "credential_file_exists": False,
        "credential_file_sha256": None,
        "client_init": None,
        "test_write": None,
        "errors": []
    }

    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    report["google_app_creds"] = gac
    try:
        if gac and os.path.exists(gac):
            report["credential_file_exists"] = True
            import hashlib
            try:
                with open(gac, "rb") as f:
                    data = f.read()
                report["credential_file_sha256"] = hashlib.sha256(data).hexdigest()
            except Exception as e:
                report["errors"].append(f"Failed to hash credential file: {e}")
        else:
            report["credential_file_exists"] = False
    except Exception as e:
        report["errors"].append(f"Credential file check error: {e}")

    # Try to init client and perform a safe write-read-delete on a test doc
    try:
        client = init_firestore()
        report["client_init"] = bool(client)
        if client:
            try:
                test_doc_id = "diagnostic_test_doc"
                doc_ref = client.collection(FIRESTORE_COLLECTION).document(test_doc_id)
                test_payload = {"diagnostic": True, "ts": int(time.time())}
                doc_ref.set(test_payload)
                got = doc_ref.get()
                report["test_write"] = got.to_dict()
                # cleanup
                doc_ref.delete()
            except Exception as e:
                report["errors"].append(f"Firestore test write/read/delete failed: {e}")
    except Exception as e:
        report["errors"].append(f"Firestore init in diagnose failed: {e}")

    status_code = 200 if not report["errors"] else 500
    return JSONResponse(status_code=status_code, content={"success": len(report["errors"])==0, "report": report})


@app.post("/api/protocol/rehydrate")
async def rehydrate_protocol():
    """Force rehydrate/write protocol to Firestore now"""
    ok = await load_110_protocol()
    if ok:
        return JSONResponse(content={"success": True, "message": "Protocol rehydrated to Firestore"})
    else:
        return JSONResponse(status_code=500, content={"success": False, "error": "Failed to rehydrate protocol"})


@app.get("/api/checklist")
async def get_checklist():
    """Return the launch checklist (from Firestore if available, otherwise in-memory)"""
    client = init_firestore()
    if client:
        try:
            doc = client.collection(FIRESTORE_COLLECTION).document("protocol_110").get()
            if doc.exists:
                data = doc.to_dict()
                checklist = data.get("checklist", PROTOCOL_110["checklist"])
                return JSONResponse(content={"success": True, "checklist": checklist})
        except Exception as e:
            logger.error(f"Failed to read checklist from Firestore: {e}")

    # Fallback to in-memory
    return JSONResponse(content={"success": True, "checklist": PROTOCOL_110["checklist"]})


class ChecklistUpdate(BaseModel):
    id: str
    status: str


@app.post("/api/checklist/update")
async def update_checklist(item: ChecklistUpdate):
    """Update a checklist item status and persist to Firestore if available"""
    # Update in-memory
    found = False
    for it in PROTOCOL_110["checklist"]:
        if it["id"] == item.id:
            it["status"] = item.status
            found = True
            break

    if not found:
        return JSONResponse(status_code=404, content={"success": False, "error": "Checklist item not found"})

    client = init_firestore()
    if client:
        try:
            doc_ref = client.collection(FIRESTORE_COLLECTION).document("protocol_110")
            doc_ref.set(PROTOCOL_110, merge=True)
            return JSONResponse(content={"success": True, "message": "Checklist updated and persisted"})
        except Exception as e:
            logger.error(f"Failed to persist checklist update: {e}")
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

    return JSONResponse(content={"success": True, "message": "Checklist updated (in-memory only)"})

# Set up OpenTelemetry tracing
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)

@app.middleware("http")
async def add_tracing(request, call_next):
    with tracer.start_as_current_span("request"):
        response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
