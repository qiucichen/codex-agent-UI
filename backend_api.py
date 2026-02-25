from __future__ import annotations

from typing import Optional

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI 未安装，请先安装 requirements.txt 依赖") from exc

from workflow_engine import build_engine

app = FastAPI(title="Fire Agent Workflow API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = build_engine()


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    question: str


class LoginRequest(BaseModel):
    session_id: str
    username: str
    password: str


class UnitRequest(BaseModel):
    session_id: str
    unit: str


@app.post("/api/session")
def create_session() -> dict:
    ctx = engine.create_session()
    return {"session_id": ctx.session_id}


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    session_id = req.session_id or engine.create_session().session_id
    return engine.process_chat(session_id, req.question)


@app.post("/api/login")
def login(req: LoginRequest) -> dict:
    return engine.login(req.session_id, req.username, req.password)


@app.post("/api/select-unit")
def select_unit(req: UnitRequest) -> dict:
    return engine.select_unit(req.session_id, req.unit)


@app.get("/api/state/{session_id}")
def state(session_id: str) -> dict:
    return engine.get_state(session_id)
