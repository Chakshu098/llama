from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Action, ActionType, AgentThought, AgentRole, Observation
from environment import IncidentResponseEnv
from server.session import session_manager
from server.middleware import RequestLoggingMiddleware, RateLimitMiddleware

load_dotenv()

app = FastAPI(
    title="Llama-IR Autonomous SRE Command Center",
    description="High-fidelity incident response environment for the Meta Hackathon.",
    version="1.0.0",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_env: Optional[IncidentResponseEnv] = None

def _require_env() -> IncidentResponseEnv:
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")
    return _env

class ResetRequest(BaseModel):
    task_id: str = "alert-classification"
    scenario_id: Optional[str] = None

class StepRequest(BaseModel):
    action_type: str
    payload: Dict[str, Any] = {}

class ThoughtRequest(BaseModel):
    role: str
    thought: str
    timestamp: float

# --- API Endpoints ---

@app.get("/health")
def health():
    return {"status": "ok", "env": _env is not None}

@app.get("/tasks")
def list_tasks():
    return {"tasks": [
        {"id": "alert-classification", "name": "Alert Triage"},
        {"id": "root-cause-analysis", "name": "Incident Investigation"},
        {"id": "postmortem-writing", "name": "Incident Reporting"},
    ]}

@app.post("/reset")
def reset(req: Optional[ResetRequest] = Body(None)):
    global _env
    if req is None:
        req = ResetRequest()
    try:
        _env = IncidentResponseEnv(task_id=req.task_id, scenario_id=req.scenario_id)
        obs = _env.reset()
        return {"observation": obs.model_dump(), "task_id": req.task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
def step(req: Optional[StepRequest] = Body(None)):
    env = _require_env()
    if req is None:
        raise HTTPException(status_code=422, detail="Step request body is required for parameters.")
    
    try:
        action_type = ActionType(req.action_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid action: {req.action_type}")
    
    action = Action(action_type=action_type, payload=req.payload)
    result = env.step(action)
    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward,
        "done": result.done,
        "info": result.info
    }

@app.get("/state")
def state():
    global _env
    if _env is None: 
        # Auto-initialize for demo/visibility purposes
        try:
            _env = IncidentResponseEnv(task_id="alert-classification")
            _env.reset()
        except Exception:
            return {"error": "not initialized and auto-reset failed"}
    return _env.state()

@app.post("/thought")
def record_thought(thought: ThoughtRequest):
    env = _require_env()
    env.record_thought(role=thought.role, thought=thought.thought)
    return {"status": "ok"}

# --- Dashboard Serving ---

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "dashboard-v3", "dist")

print(f"[*] Command Center Launching...")
print(f"[*] Root Directory: {BASE_DIR}")
print(f"[*] Checking for Dashboard at: {DIST_DIR}")

if os.path.exists(DIST_DIR):
    print(f"[+] Dashboard found! Serving from: {DIST_DIR}")
    
    # Route for assets specifically
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        print(f"[*] Assets directory found at: {assets_dir}")
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # API routes are already defined above. 
    # Everything else should serve index.html or the static file.

    @app.get("/")
    async def get_index():
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

    # Fallback for React routing
    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        # Don't fallback for API calls
        if any(request.url.path.startswith(p) for p in ["/state", "/step", "/reset", "/thought", "/health", "/tasks"]):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        
        index_path = os.path.join(DIST_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse({"detail": "Dashboard index.html not found"}, status_code=404)

    # Mount remaining root files (must be last)
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="root")
else:
    print(f"[!] WARNING: Dashboard directory NOT FOUND at {DIST_DIR}")
    print(f"[!] Dashboard UI will not be available.")

if __name__ == "__main__":
    import uvicorn
    # Hugging Face Spaces require port 7860
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
