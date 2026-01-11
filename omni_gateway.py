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
        # Fire-and-forget: ensure we don\'t block startup for long network ops
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


# Static files for the Intelligence Cockpit UI
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def serve_cockpit():
    """Serve the Intelligence Cockpit UI."""
    cockpit_path = Path(__file__).parent / "static" / "cockpit.html"
    if not cockpit_path.exists():
        return PlainTextResponse("Intelligence Cockpit UI not found", status_code=404)
    return HTMLResponse(content=cockpit_path.read_text(), status_code=200)


# Endpoint to get the list of available tools
@app.get("/mcp/tools", response_model=List[str])
async def mcp_list_tools_alias():
    """List all available tools from the MCP server."""
    return mcp_server.list_tools()


# Endpoint to execute a tool
class ToolExecutionRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any]


@app.post("/mcp/execute")
async def mcp_execute_tool_alias(request: ToolExecutionRequest):
    """Execute a specified tool with given arguments."""
    governance = check_governance(request.tool_name)
    if not governance["allowed"]:
        return JSONResponse(
            {
                "error": "Tool execution not allowed by governance policy",
                "reason": governance["reason"],
            },
            status_code=403,
        )
    if governance["rate_limited"]:
        return JSONResponse(
            {"error": "Tool execution rate-limited", "reason": governance["reason"]},
            status_code=429,
        )

    try:
        # MCP server returns a list of objects with a \'text\' attribute
        results = await mcp_server.call_tool(request.tool_name, request.args)
        # Assuming each result object has a \'text\' attribute that is a JSON string
        parsed_results = []
        for res in results:
            try:
                parsed_results.append(json.loads(res.text))
            except json.JSONDecodeError:
                parsed_results.append(res.text)  # Append as is if not JSON
        return JSONResponse(parsed_results)
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Headless Agent endpoint
@app.post("/headless/agent")
async def execute_headless_agent(agent_context: AgentContext):
    """Execute a headless agent with the given context."""
    if not app.state.headless_team:
        return JSONResponse({"error": "Headless team not initialized"}, status_code=500)
    try:
        result = await app.state.headless_team.run_agent(agent_context)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error executing headless agent: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Endpoint to enqueue an agent task
class AgentTaskRequest(BaseModel):
    agent_context: AgentContext
    team_id: str
    task_id: str


@app.post("/headless/enqueue_task")
async def enqueue_agent_task(request: AgentTaskRequest):
    """Enqueue an agent task for asynchronous execution."""
    if not app.state.hybrid_orch:
        return JSONResponse({"error": "Hybrid Orchestrator not initialized"}, status_code=500)
    try:
        task_info = await app.state.hybrid_orch.enqueue_agent_task(
            request.team_id, request.task_id, request.agent_context
        )
        return JSONResponse(task_info)
    except Exception as e:
        logger.error(f"Error enqueuing agent task: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Endpoint to get agent task status
@app.get("/headless/task_status/{team_id}/{task_id}")
async def get_agent_task_status(team_id: str, task_id: str):
    """Get the status of an enqueued agent task."""
    if not app.state.hybrid_orch:
        return JSONResponse({"error": "Hybrid Orchestrator not initialized"}, status_code=500)
    try:
        status = await app.state.hybrid_orch.get_agent_task_status(team_id, task_id)
        return JSONResponse(status)
    except Exception as e:
        logger.error(f"Error getting agent task status: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Endpoint to list headless team members
@app.get("/headless/team")
async def list_headless_team():
    """List all members of the headless team."""
    if not app.state.headless_team:
        return JSONResponse({"error": "Headless team not initialized"}, status_code=500)
    try:
        team_members = app.state.headless_team.list_members()
        return JSONResponse(team_members)
    except Exception as e:
        logger.error(f"Error listing headless team: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "mcp_available": MCP_AVAILABLE}


# Protocol 110 endpoints
@app.get("/protocol110")
async def get_protocol():
    if not _firestore_available:
        return JSONResponse({"error": "Firestore not available"}, status_code=500)
    try:
        doc_ref = _firestore_client.collection(FIRESTORE_COLLECTION).document("protocol_110")
        doc = doc_ref.get()
        if doc.exists:
            return JSONResponse(doc.to_dict())
        return JSONResponse({"error": "Protocol 110 not found"}, status_code=404)
    except Exception as e:
        logger.error(f"Error getting Protocol 110: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/protocol110/rehydrate")
async def rehydrate_protocol():
    success = await load_110_protocol()
    if success:
        return JSONResponse({"status": "Protocol 110 rehydrated"})
    return JSONResponse({"error": "Failed to rehydrate Protocol 110"}, status_code=500)


@app.get("/protocol110/checklist")
async def get_checklist():
    if not _firestore_available:
        return JSONResponse({"error": "Firestore not available"}, status_code=500)
    try:
        doc_ref = _firestore_client.collection(FIRESTORE_COLLECTION).document("protocol_110")
        doc = doc_ref.get()
        if doc.exists and "checklist" in doc.to_dict():
            return JSONResponse(doc.to_dict()["checklist"])
        return JSONResponse({"error": "Checklist not found"}, status_code=404)
    except Exception as e:
        logger.error(f"Error getting checklist: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/protocol110/checklist/{item_id}")
async def update_checklist(item_id: str, status: str):
    if not _firestore_available:
        return JSONResponse({"error": "Firestore not available"}, status_code=500)
    try:
        doc_ref = _firestore_client.collection(FIRESTORE_COLLECTION).document("protocol_110")
        doc = doc_ref.get()
        if not doc.exists:
            return JSONResponse({"error": "Protocol 110 not found"}, status_code=404)

        protocol_data = doc.to_dict()
        checklist = protocol_data.get("checklist", [])
        updated = False
        for item in checklist:
            if item.get("id") == item_id:
                item["status"] = status
                updated = True
                break

        if updated:
            doc_ref.update({"checklist": checklist})
            return JSONResponse({"status": "Checklist updated"})
        return JSONResponse({"error": "Checklist item not found"}, status_code=404)
    except Exception as e:
        logger.error(f"Error updating checklist: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Diagnostics endpoint for Firestore
@app.get("/diagnose/firestore")
async def firestore_diagnose():
    if not _HAS_GCP:
        return JSONResponse({"error": "GCP libraries not available"}, status_code=500)
    try:
        client = init_firestore()
        # Attempt to write a test document
        test_doc_ref = client.collection(FIRESTORE_COLLECTION).document("diagnostic_test")
        test_doc_ref.set({"timestamp": time.time(), "test": "ok"})
        test_doc = test_doc_ref.get()
        if test_doc.exists and test_doc.to_dict().get("test") == "ok":
            test_doc_ref.delete()
            return JSONResponse({"status": "Firestore read/write successful"})
        return JSONResponse({"error": "Firestore write verification failed"}, status_code=500)
    except Exception as e:
        logger.error(f"Firestore diagnostic failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Tracing middleware
@app.middleware("http")
async def add_tracing(request: Request, call_next):
    with trace.get_tracer(__name__).start_as_current_span(request.url.path):
        response = await call_next(request)
        return response


# Web shell endpoints
@app.get("/shell/list")
async def list_files(path: str = "."):
    try:
        files = os.listdir(path)
        return JSONResponse({"files": files})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/shell/read")
async def read_file(path: str):
    try:
        with open(path, "r") as f:
            content = f.read()
        return JSONResponse({"content": content})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/shell/save")
async def save_file(path: str, content: str):
    try:
        with open(path, "w") as f:
            f.write(content)
        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
