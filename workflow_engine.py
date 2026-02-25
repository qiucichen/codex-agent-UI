from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import uuid4

from agent_core import UserState, llm_compose_answer, llm_decide, mock_units_for_user, validate_login
from mcp_server import call_mcp_tool


@dataclass
class SessionContext:
    session_id: str
    state: UserState = field(default_factory=UserState)
    pending_question: Optional[str] = None
    flow_stage: str = "idle"  # idle|await_login|await_unit|auto_resume
    messages: List[Dict[str, str]] = field(default_factory=list)


class WorkflowEngine:
    def __init__(self) -> None:
        self.sessions: Dict[str, SessionContext] = {}

    def create_session(self, session_id: Optional[str] = None) -> SessionContext:
        sid = session_id or str(uuid4())
        ctx = SessionContext(session_id=sid)
        self.sessions[sid] = ctx
        return ctx

    def get_session(self, session_id: str) -> SessionContext:
        if session_id not in self.sessions:
            return self.create_session(session_id=session_id)
        return self.sessions[session_id]

    def _assistant(self, ctx: SessionContext, text: str) -> None:
        ctx.messages.append({"role": "assistant", "content": text})

    def _user(self, ctx: SessionContext, text: str) -> None:
        ctx.messages.append({"role": "user", "content": text})

    def process_chat(self, session_id: str, question: str) -> Dict:
        ctx = self.get_session(session_id)
        self._user(ctx, question)
        return self._run_question(ctx, question)

    def _run_question(self, ctx: SessionContext, question: str) -> Dict:
        decision = llm_decide(question, ctx.state)

        if decision.intent == "normal_chat":
            text = f"普通对话回复：你说“{question}”，我已理解。若你要查消防业务，也可以直接问我。"
            self._assistant(ctx, text)
            return self._response(ctx, ui_action="none", content=text)

        if decision.need_login:
            ctx.pending_question = question
            ctx.flow_stage = "await_login"
            text = "我判断这是业务查询，请先登录。登录成功后我会自动继续回答原问题。"
            self._assistant(ctx, text)
            return self._response(ctx, ui_action="show_login", content=text, extra={"ui": {"type": "login_form", "fields": ["username", "password"], "submit_label": "登录"}})

        if decision.need_unit_selection:
            ctx.pending_question = question
            ctx.flow_stage = "await_unit"
            text = "检测到你有多个单位，请先选择单位，随后自动继续回答原问题。"
            self._assistant(ctx, text)
            return self._response(ctx, ui_action="show_unit", content=text, extra={"units": ctx.state.units, "ui": {"type": "unit_select", "submit_label": "确认单位"}})

        unit = ctx.state.selected_unit or (ctx.state.units[0] if ctx.state.units else "默认单位")
        mcp = call_mcp_tool(decision.mcp_tool or "query_fire_alarm_count", unit)
        answer = llm_compose_answer(question, mcp.title, mcp.summary, mcp.data)
        self._assistant(ctx, answer.narrative)
        return self._response(
            ctx,
            ui_action="render_result",
            content=answer.narrative,
            extra={
                "chart_type": answer.chart_type,
                "chart_payload": answer.chart_payload,
                "mcp_title": mcp.title,
                "mcp_data": mcp.data,
            },
        )

    def login(self, session_id: str, username: str, password: str) -> Dict:
        ctx = self.get_session(session_id)
        if not validate_login(username, password):
            text = "登录失败：用户名或密码不能为空。"
            self._assistant(ctx, text)
            return self._response(ctx, ui_action="show_login", content=text, extra={"ui": {"type": "login_form", "fields": ["username", "password"], "submit_label": "登录"}})

        ctx.state.username = username
        ctx.state.logged_in = True
        ctx.state.units = mock_units_for_user(username)
        if len(ctx.state.units) == 1:
            ctx.state.selected_unit = ctx.state.units[0]

        text = "登录成功，正在自动继续回答原问题。"
        self._assistant(ctx, text)

        if ctx.pending_question:
            return self._run_question(ctx, ctx.pending_question)
        return self._response(ctx, ui_action="none", content=text)

    def select_unit(self, session_id: str, unit: str) -> Dict:
        ctx = self.get_session(session_id)
        if unit not in ctx.state.units:
            text = "单位选择无效，请重新选择。"
            self._assistant(ctx, text)
            return self._response(ctx, ui_action="show_unit", content=text, extra={"units": ctx.state.units, "ui": {"type": "unit_select", "submit_label": "确认单位"}})

        ctx.state.selected_unit = unit
        text = f"已选择单位：{unit}，正在自动继续回答原问题。"
        self._assistant(ctx, text)

        if ctx.pending_question:
            return self._run_question(ctx, ctx.pending_question)
        return self._response(ctx, ui_action="none", content=text)

    def get_state(self, session_id: str) -> Dict:
        ctx = self.get_session(session_id)
        return {
            "session_id": ctx.session_id,
            "logged_in": ctx.state.logged_in,
            "username": ctx.state.username,
            "units": ctx.state.units,
            "selected_unit": ctx.state.selected_unit,
            "pending_question": ctx.pending_question,
            "messages": ctx.messages,
        }

    def _response(self, ctx: SessionContext, ui_action: str, content: str, extra: Optional[Dict] = None) -> Dict:
        return {
            "session_id": ctx.session_id,
            "ui_action": ui_action,
            "content": content,
            "extra": extra or {},
            "state": {
                "logged_in": ctx.state.logged_in,
                "username": ctx.state.username,
                "units": ctx.state.units,
                "selected_unit": ctx.state.selected_unit,
                "pending_question": ctx.pending_question,
            },
            "messages": ctx.messages,
        }


def build_engine() -> WorkflowEngine:
    return WorkflowEngine()
