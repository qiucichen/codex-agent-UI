from mcp_server import build_fastmcp_server, call_mcp_tool, list_supported_business_queries


def test_query_fire_alarm_count():
    result = call_mcp_tool("query_fire_alarm_count", "第一中学")
    assert result.data["count"] == 3


def test_supported_queries_size():
    assert len(list_supported_business_queries()) == 4


def test_fastmcp_server_build_does_not_crash():
    server = build_fastmcp_server()
    assert server is None or hasattr(server, "tool")
