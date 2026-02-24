from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None


@dataclass
class MCPResult:
    title: str
    summary: str
    data: Dict[str, Any]


def query_fire_alarm_count(unit_name: str) -> MCPResult:
    values = {"第一中学": 3, "人民医院": 7, "城市综合体": 12, "默认单位": 2}
    count = values.get(unit_name, 1)
    return MCPResult(
        title="单位火警数量",
        summary=f"{unit_name} 近30天火警数量为 {count} 起，周末波动明显。",
        data={"unit": unit_name, "count": count, "period": "近30天"},
    )


def query_floor_plan(unit_name: str) -> MCPResult:
    return MCPResult(
        title="单位平面图",
        summary=f"已为 {unit_name} 生成消防重点区域平面图示意。",
        data={"unit": unit_name, "image_type": "floor_plan"},
    )


def query_hidden_risk_count(unit_name: str) -> MCPResult:
    values = {"第一中学": 5, "人民医院": 4, "城市综合体": 10, "默认单位": 1}
    count = values.get(unit_name, 2)
    return MCPResult(
        title="未闭环隐患数量",
        summary=f"{unit_name} 当前未闭环隐患共 {count} 条，建议按高风险优先处置。",
        data={"unit": unit_name, "count": count, "category": "隐患"},
    )


def query_device_online_rate(unit_name: str) -> MCPResult:
    rates = {"第一中学": 98.2, "人民医院": 96.5, "城市综合体": 94.1, "默认单位": 99.0}
    rate = rates.get(unit_name, 95.0)
    return MCPResult(
        title="消防设备在线率",
        summary=f"{unit_name} 当前设备在线率 {rate}%，离线设备集中在辅助楼层。",
        data={"unit": unit_name, "rate": rate, "metric": "online_rate"},
    )


def list_supported_business_queries() -> List[str]:
    return [
        "查询单位的火警数量",
        "查询单位的平面图",
        "查询单位未闭环隐患数量",
        "查询单位消防设备在线率",
    ]


def call_mcp_tool(tool_name: str, unit_name: str) -> MCPResult:
    mapping = {
        "query_fire_alarm_count": query_fire_alarm_count,
        "query_floor_plan": query_floor_plan,
        "query_hidden_risk_count": query_hidden_risk_count,
        "query_device_online_rate": query_device_online_rate,
    }
    if tool_name not in mapping:
        raise ValueError(f"unknown tool: {tool_name}")
    return mapping[tool_name](unit_name)


def build_fastmcp_server() -> Any:
    if FastMCP is None:
        return None

    server = FastMCP("fire-business-mcp")

    @server.tool()
    def get_fire_alarm_count(unit_name: str) -> Dict[str, Any]:
        return asdict(query_fire_alarm_count(unit_name))

    @server.tool()
    def get_floor_plan(unit_name: str) -> Dict[str, Any]:
        return asdict(query_floor_plan(unit_name))

    @server.tool()
    def get_hidden_risk_count(unit_name: str) -> Dict[str, Any]:
        return asdict(query_hidden_risk_count(unit_name))

    @server.tool()
    def get_device_online_rate(unit_name: str) -> Dict[str, Any]:
        return asdict(query_device_online_rate(unit_name))

    return server
