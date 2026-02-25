from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class UserState:
    username: Optional[str] = None
    logged_in: bool = False
    units: List[str] = field(default_factory=list)
    selected_unit: Optional[str] = None


@dataclass
class AgentDecision:
    intent: str
    need_login: bool
    need_unit_selection: bool
    mcp_tool: Optional[str]
    reason: str


@dataclass
class AgentAnswer:
    narrative: str
    chart_type: Optional[str]
    chart_payload: dict


def validate_login(username: str, password: str) -> bool:
    return bool(username.strip()) and bool(password.strip())


def mock_units_for_user(username: str) -> List[str]:
    if username.lower() in {"admin", "multi", "manager"}:
        return ["第一中学", "人民医院", "城市综合体"]
    return ["默认单位"]


def llm_decide(question: str, state: UserState) -> AgentDecision:
    """模拟 LLM 的决策输出。实际接入时可替换为真实模型调用。"""
    business = any(k in question for k in ["消防", "火警", "平面图", "隐患", "在线率", "单位", "设备"])
    if not business:
        return AgentDecision(
            intent="normal_chat",
            need_login=False,
            need_unit_selection=False,
            mcp_tool=None,
            reason="模型判断为普通对话",
        )

    if not state.logged_in:
        return AgentDecision(
            intent="business_query",
            need_login=True,
            need_unit_selection=False,
            mcp_tool=None,
            reason="模型判断是业务问题，但用户未登录",
        )

    if len(state.units) > 1 and not state.selected_unit:
        return AgentDecision(
            intent="business_query",
            need_login=False,
            need_unit_selection=True,
            mcp_tool=None,
            reason="模型判断需先选择单位",
        )

    if "平面图" in question:
        tool = "query_floor_plan"
    elif "隐患" in question:
        tool = "query_hidden_risk_count"
    elif "在线率" in question or "设备" in question:
        tool = "query_device_online_rate"
    else:
        tool = "query_fire_alarm_count"

    return AgentDecision(
        intent="business_query",
        need_login=False,
        need_unit_selection=False,
        mcp_tool=tool,
        reason="模型完成前置条件判断并给出MCP调用建议",
    )


def llm_compose_answer(question: str, mcp_title: str, mcp_summary: str, mcp_data: dict) -> AgentAnswer:
    """模型将业务结果组织成自然语言+图像指令，而不是模板字段填充。"""
    if "count" in mcp_data and "period" in mcp_data:
        narrative = (
            f"你提到“{question}”，我基于业务数据整理如下：{mcp_summary} "
            "从趋势上看，近期有波动，建议关注重点时段与重点区域并做复盘。"
        )
        return AgentAnswer(narrative=narrative, chart_type="bar", chart_payload={"label": mcp_data["unit"], "value": mcp_data["count"], "title": mcp_title})

    if mcp_data.get("image_type") == "floor_plan":
        narrative = f"关于“{question}”，我已调取平面示意信息：{mcp_summary} 可结合疏散路线和重点设备位进行巡检。"
        return AgentAnswer(narrative=narrative, chart_type="floor_plan", chart_payload={"unit": mcp_data["unit"], "title": mcp_title})

    if "rate" in mcp_data:
        narrative = f"针对“{question}”，当前状态是：{mcp_summary} 建议优先排查离线设备集中区域。"
        return AgentAnswer(narrative=narrative, chart_type="gauge_like", chart_payload={"value": mcp_data["rate"], "title": mcp_title})

    narrative = f"关于“{question}”，结果如下：{mcp_summary}"
    return AgentAnswer(narrative=narrative, chart_type=None, chart_payload={})
