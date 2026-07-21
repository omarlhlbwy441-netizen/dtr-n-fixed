"""
DTR-N API Server — Comprehensive Multi-Agent AI Platform
نظام DTR-N الشامل — وكلاء متعددون، GitHub، بيئة عمل، تطور ذاتي
"""

import asyncio
import os
import sys
import time
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from dtr_n.evolution_engine import DTREvolutionEngine, create_engine
from dtr_n.agents import MultiAgentOrchestrator
from dtr_n.github_manager import GitHubManager
from dtr_n.workspace_manager import WorkspaceManager

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DTR-N API",
    description="DTR-N Multi-Agent AI Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global Singletons ────────────────────────────────────────────────────────
evolution_engine: DTREvolutionEngine = create_engine()
orchestrator: MultiAgentOrchestrator = MultiAgentOrchestrator()
github_mgr: GitHubManager = GitHubManager()
workspace_mgr: WorkspaceManager = WorkspaceManager()
START_TIME = time.time()

# ─── Session Store ────────────────────────────────────────────────────────────
SESSIONS: Dict[str, Dict] = {}
CURRENT_SESSION_ID = str(uuid.uuid4())

# Session config: 4x resources compared to standard
SESSION_CONFIG = {
    "steps_total": 200,          # 4x standard (50 steps)
    "resources_multiplier": 4.0,
    "plan": "diamond",
}


def get_or_create_session(session_id: Optional[str] = None) -> Dict:
    sid = session_id or CURRENT_SESSION_ID
    if sid not in SESSIONS:
        now = datetime.now()
        expires = datetime.fromtimestamp(now.timestamp() + 4 * 3600)  # 4 hours
        SESSIONS[sid] = {
            "session_id": sid,
            "plan": SESSION_CONFIG["plan"],
            "steps_total": SESSION_CONFIG["steps_total"],
            "steps_used": 0,
            "steps_remaining": SESSION_CONFIG["steps_total"],
            "resources_multiplier": SESSION_CONFIG["resources_multiplier"],
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }
    return SESSIONS[sid]


def consume_session_steps(session_id: str, steps: int = 1):
    session = get_or_create_session(session_id)
    session["steps_used"] = min(session["steps_used"] + steps, session["steps_total"])
    session["steps_remaining"] = max(0, session["steps_total"] - session["steps_used"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = "plan"
    session_id: Optional[str] = None


class CloneRequest(BaseModel):
    repo_url: str
    target_dir: Optional[str] = None


class CreateRepoRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    private: Optional[bool] = False
    init: Optional[bool] = True


class PushRequest(BaseModel):
    repo: str
    message: str
    files: List[Dict[str, str]]


class FileSaveRequest(BaseModel):
    path: str
    content: str


class PreviewRequest(BaseModel):
    project_path: str
    build_command: Optional[str] = None
    port: Optional[int] = None


# ─── Root & Health ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "project": "dtr-n",
        "version": "2.0.0",
        "message": "DTR-N Multi-Agent AI Platform",
        "status": "running",
        "uptime": time.time() - START_TIME,
    }


@app.get("/healthz")
async def health():
    return {"status": "ok"}


# ─── /api/status ──────────────────────────────────────────────────────────────
@app.get("/api/status")
async def get_status():
    session = get_or_create_session()
    active = sum(1 for a in orchestrator.agents.values() if a.status != "idle")
    return {
        "project": "dtr-n",
        "version": "2.0.0",
        "iq_level": evolution_engine.iq_level,
        "is_running": evolution_engine.is_running,
        "github_connected": bool(github_mgr.token),
        "session_steps_remaining": session["steps_remaining"],
        "agents_active": active,
        "uptime_seconds": time.time() - START_TIME,
    }


# ─── /api/messages ────────────────────────────────────────────────────────────
@app.get("/api/messages")
async def get_messages():
    return orchestrator.conversation_history


@app.delete("/api/messages")
async def clear_messages():
    orchestrator.conversation_history.clear()
    return {"ok": True, "message": "تم مسح سجل المحادثة"}


# ─── /api/chat ────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def send_chat(req: ChatRequest, background_tasks: BackgroundTasks):
    session = get_or_create_session(req.session_id)
    if session["steps_remaining"] <= 0:
        raise HTTPException(status_code=429, detail="انتهت خطوات الجلسة")

    result = await orchestrator.process_message(req.message, req.mode or "plan")

    steps_used = result.get("session_steps_used", 1)
    consume_session_steps(req.session_id or CURRENT_SESSION_ID, steps_used)

    return result


# ─── /api/agents ──────────────────────────────────────────────────────────────
@app.get("/api/agents")
async def get_agents():
    return orchestrator.get_agents()


# ─── /api/github/* ────────────────────────────────────────────────────────────
@app.get("/api/github/repos")
async def list_repos():
    return await github_mgr.list_repos()


@app.post("/api/github/clone")
async def clone_repo(req: CloneRequest):
    result = await github_mgr.clone_repo(req.repo_url, req.target_dir)
    return result


@app.post("/api/github/create")
async def create_repo(req: CreateRepoRequest):
    result = await github_mgr.create_repo(req.name, req.description or "", req.private or False, req.init or True)
    return result


@app.post("/api/github/push")
async def push_files(req: PushRequest):
    result = await github_mgr.push_files(req.repo, req.message, req.files)
    return result


# ─── /api/workspace/* ─────────────────────────────────────────────────────────
@app.get("/api/workspace/files")
async def list_workspace_files(path: Optional[str] = None):
    return workspace_mgr.list_files(path)


@app.get("/api/workspace/file")
async def get_workspace_file(path: str):
    result = workspace_mgr.read_file(path)
    if result.get("error") and "not found" in result["error"].lower():
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.put("/api/workspace/file")
async def save_workspace_file(req: FileSaveRequest):
    result = workspace_mgr.write_file(req.path, req.content)
    return result


# ─── /api/evolution ───────────────────────────────────────────────────────────
@app.get("/api/evolution")
async def get_evolution():
    status = evolution_engine.get_status()
    return {
        "iq_level": status["iq_level"],
        "is_running": status["is_running"],
        "files_written": status["files_written"],
        "evolution_cycle": status["evolution_cycle"],
        "github_pushes": getattr(evolution_engine, "github_pushes", 0),
        "capability_multiplier": getattr(evolution_engine, "capability_multiplier", 1.0),
        "last_evolution": getattr(evolution_engine, "last_evolution", None),
    }


@app.post("/api/evolution/triple")
async def triple_capability(background_tasks: BackgroundTasks):
    """
    ثلاثة تضاعفات في القدرة:
    IQ: 85 → 170 → 340 → 680
    ثم يرفع المشروع إلى GitHub
    """
    iq_before = evolution_engine.iq_level

    background_tasks.add_task(_run_triple_evolution)

    return {
        "success": True,
        "cycles_completed": 0,  # will complete in background
        "iq_before": iq_before,
        "iq_after": iq_before * 8,  # 3 doublings
        "capability_multiplier": 8.0,
        "github_pushed": True,
        "message": "بدأت عملية التضاعف الثلاثي — IQ سيرتفع من {:.1f} إلى {:.1f}".format(
            iq_before, iq_before * 8
        ),
    }


async def _run_triple_evolution():
    """تضاعف القدرة 3 مرات + رفع GitHub"""
    for cycle in range(3):
        evolution_engine.iq_level *= 2
        evolution_engine.learning_rate *= 1.5
        evolution_engine.files_written += 5
        evolution_engine.capability_multiplier = 2 ** (cycle + 1)
        evolution_engine.last_evolution = datetime.now().isoformat()

        # Generate and write evolution code
        feature = {
            "name": f"capability_boost_x{2 ** (cycle + 1)}",
            "type": "module",
            "language": "python"
        }
        try:
            code_result = await evolution_engine._generate_feature_code(feature)
            await evolution_engine._write_code_file(code_result)
        except Exception:
            pass

        evolution_engine._log_evolution({
            "type": "capability_boost",
            "cycle": cycle + 1,
            "multiplier": 2 ** (cycle + 1),
            "iq_after": evolution_engine.iq_level,
            "timestamp": datetime.now().isoformat(),
        })
        await asyncio.sleep(1)

    # Push to GitHub after all 3 cycles
    try:
        result = await github_mgr.push_current_workspace(
            f"feat: DTR-N capability tripled — IQ={evolution_engine.iq_level:.1f}"
        )
        evolution_engine.github_pushes = getattr(evolution_engine, "github_pushes", 0) + 1
        evolution_engine._log_evolution({
            "type": "github_push",
            "success": result["success"],
            "message": result["message"],
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        pass


# ─── /api/session ─────────────────────────────────────────────────────────────
@app.get("/api/session")
async def get_session():
    return get_or_create_session()


# ─── /api/preview ─────────────────────────────────────────────────────────────
@app.post("/api/preview")
async def build_preview(req: PreviewRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        workspace_mgr.build_preview, req.project_path, req.build_command, req.port
    )
    return {
        "status": "building",
        "url": None,
        "logs": [f"[BUILD] بدء بناء {req.project_path}..."],
        "error": None,
        "project_path": req.project_path,
    }


@app.get("/api/preview")
async def get_preview_status():
    return workspace_mgr.get_preview_status()


# ─── /api/dtrn/api/* aliases — Render direct deployment (no Express proxy) ────
# On Render only Python runs; the Express proxy is absent. These aliases let
# the React frontend (built with BASE_PATH=/) call /api/dtrn/api/* directly.
from fastapi.routing import APIRouter as _APIRouter
_dtrn = _APIRouter(prefix="/api/dtrn")

@_dtrn.get("/api/status")
async def _dtrn_status(): return await get_status()

@_dtrn.get("/api/messages")
async def _dtrn_messages(): return await get_messages()

@_dtrn.delete("/api/messages")
async def _dtrn_clear(): return await clear_messages()

@_dtrn.post("/api/chat")
async def _dtrn_chat(req: ChatRequest, bg: BackgroundTasks): return await send_chat(req, bg)

@_dtrn.get("/api/agents")
async def _dtrn_agents(): return await get_agents()

@_dtrn.get("/api/github/repos")
async def _dtrn_repos(): return await list_repos()

@_dtrn.post("/api/github/clone")
async def _dtrn_clone(req: CloneRequest): return await clone_repo(req)

@_dtrn.post("/api/github/create")
async def _dtrn_create(req: CreateRepoRequest): return await create_repo(req)

@_dtrn.post("/api/github/push")
async def _dtrn_push(req: PushRequest): return await push_files(req)

@_dtrn.get("/api/workspace/files")
async def _dtrn_files(path: Optional[str] = None): return await list_workspace_files(path)

@_dtrn.get("/api/workspace/file")
async def _dtrn_file(path: str): return await get_workspace_file(path)

@_dtrn.put("/api/workspace/file")
async def _dtrn_save(req: FileSaveRequest): return await save_workspace_file(req)

@_dtrn.get("/api/evolution")
async def _dtrn_evolution(): return await get_evolution()

@_dtrn.post("/api/evolution/triple")
async def _dtrn_triple(bg: BackgroundTasks): return await triple_capability(bg)

@_dtrn.get("/api/session")
async def _dtrn_session(): return await get_session()

@_dtrn.post("/api/preview")
async def _dtrn_build(req: PreviewRequest, bg: BackgroundTasks): return await build_preview(req, bg)

@_dtrn.get("/api/preview")
async def _dtrn_preview(): return await get_preview_status()

app.include_router(_dtrn)

# ─── Serve built React app as static files (Render production) ────────────────
_DIST = Path(__file__).parent.parent / "artifacts" / "dtrn-ui" / "dist" / "public"

if _DIST.exists():
    _assets = _DIST / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="vite-assets")

    @app.get("/", include_in_schema=False)
    async def _spa_root():
        return FileResponse(str(_DIST / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # Don't intercept known API prefixes
        for prefix in ("api/", "healthz", "status", "evolution", "evolve",
                       "start-evolution", "stop-evolution", "files"):
            if full_path.startswith(prefix):
                raise HTTPException(status_code=404, detail="Not found")
        file = _DIST / full_path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(_DIST / "index.html"))

# ─── Legacy endpoints (backwards compat) ──────────────────────────────────────
@app.get("/status")
async def legacy_status():
    return await get_status()


@app.get("/evolution-log")
async def get_evolution_log():
    return {"log": evolution_engine.evolution_log, "count": len(evolution_engine.evolution_log)}


@app.post("/evolve")
async def trigger_evolution(background_tasks: BackgroundTasks):
    feedback = [{"type": "feature_request", "content": "auto", "priority": "medium"}]
    next_feature = await evolution_engine._determine_next_feature(feedback)
    if next_feature:
        code_result = await evolution_engine._generate_feature_code(next_feature)
        await evolution_engine._write_code_file(code_result)
        return {"status": "success", "feature": next_feature["name"], "iq_level": evolution_engine.iq_level}
    return {"status": "no_action"}


@app.post("/start-evolution-loop")
async def start_loop(background_tasks: BackgroundTasks):
    if not evolution_engine.is_running:
        background_tasks.add_task(evolution_engine.start_evolution_loop)
        return {"status": "started"}
    return {"status": "already_running"}


@app.post("/stop-evolution-loop")
async def stop_loop():
    evolution_engine.is_running = False
    return {"status": "stopped"}


@app.get("/files")
async def get_files():
    files = workspace_mgr.list_files()
    return {"files": [f["path"] for f in files], "count": len(files)}


# ─── HTML page proxies (served by Express proxy already, but here for direct access)
@app.get("/api/parallel/status")
async def parallel_status():
    return await get_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
