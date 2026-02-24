from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from agent_core import AgentDecision, UserState, llm_compose_answer, llm_decide, mock_units_for_user, validate_login
from mcp_server import call_mcp_tool, list_supported_business_queries

st.set_page_config(page_title="消防业务对话 Agent", page_icon="🚒", layout="wide")

if "user_state" not in st.session_state:
    st.session_state.user_state = UserState()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

state: UserState = st.session_state.user_state


def draw_chart(chart_type: str, payload: dict) -> None:
    if chart_type == "bar":
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.bar([payload["label"]], [payload["value"]], color="#ff6b6b")
        ax.set_ylabel("数量")
        ax.set_title(payload["title"])
        st.pyplot(fig)
    elif chart_type == "floor_plan":
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.set_title(f"{payload['unit']} 平面图（示意）")
        ax.add_patch(plt.Rectangle((0.1, 0.1), 0.8, 0.7, fill=False, edgecolor="black", linewidth=2))
        ax.add_patch(plt.Rectangle((0.15, 0.55), 0.25, 0.2, fill=False, edgecolor="blue"))
        ax.add_patch(plt.Rectangle((0.45, 0.55), 0.4, 0.2, fill=False, edgecolor="green"))
        ax.add_patch(plt.Rectangle((0.15, 0.2), 0.7, 0.25, fill=False, edgecolor="orange"))
        ax.text(0.2, 0.63, "控制室", fontsize=10)
        ax.text(0.58, 0.63, "办公区", fontsize=10)
        ax.text(0.45, 0.3, "仓储区", fontsize=10)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        st.pyplot(fig)
    elif chart_type == "gauge_like":
        fig, ax = plt.subplots(figsize=(5, 1.6))
        ax.barh(["在线率"], [payload["value"]], color="#4dabf7")
        ax.set_xlim(0, 100)
        ax.set_title(payload["title"])
        st.pyplot(fig)


def handle_question(question: str) -> None:
    decision: AgentDecision = llm_decide(question, state)

    with st.chat_message("assistant"):
        if decision.intent == "normal_chat":
            answer = f"普通对话回复：你说“{question}”，我已理解。若你要查消防业务，也可以直接问我。"
            st.markdown(answer)
            st.session_state.chat_history.append(("assistant", answer))
            return

        if decision.need_login:
            st.info("我判断这是业务查询，请先登录后我会自动继续处理你刚才的问题。")
            st.session_state.pending_question = question
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("登录用户名")
                password = st.text_input("用户密码", type="password")
                login_submit = st.form_submit_button("登录")
            if login_submit:
                if validate_login(username, password):
                    state.username = username
                    state.logged_in = True
                    state.units = mock_units_for_user(username)
                    if len(state.units) == 1:
                        state.selected_unit = state.units[0]
                    msg = "登录成功，正在自动继续回答原问题。"
                    st.success(msg)
                    st.session_state.chat_history.append(("assistant", msg))
                    st.rerun()
                else:
                    msg = "登录失败：用户名或密码不能为空。"
                    st.error(msg)
                    st.session_state.chat_history.append(("assistant", msg))
            return

        if decision.need_unit_selection:
            st.warning("我判断你有多个单位，请先选择单位，随后会自动继续回答原问题。")
            st.session_state.pending_question = question
            with st.form("unit_select_form", clear_on_submit=False):
                selected = st.selectbox("请选择单位", options=state.units)
                unit_submit = st.form_submit_button("确认单位")
            if unit_submit:
                state.selected_unit = selected
                msg = f"已选择单位：{selected}，正在自动继续回答原问题。"
                st.success(msg)
                st.session_state.chat_history.append(("assistant", msg))
                st.rerun()
            return

        unit = state.selected_unit or (state.units[0] if state.units else "默认单位")
        mcp = call_mcp_tool(decision.mcp_tool or "query_fire_alarm_count", unit)
        answer = llm_compose_answer(question, mcp.title, mcp.summary, mcp.data)
        st.markdown(answer.narrative)
        if answer.chart_type:
            draw_chart(answer.chart_type, answer.chart_payload)
        st.session_state.chat_history.append(("assistant", answer.narrative))


st.title("🚒 消防业务对话 Agent（LLM编排 + FastMCP）")
st.caption("支持多轮对话；业务问题由模型判断是否触发登录/单位选择，并自动续答原问题")

with st.expander("示例测试问题列表", expanded=True):
    for q in [
        "你好，帮我总结今天工作",
        "查询单位的火警数量",
        "查询单位的平面图",
        "查询单位未闭环隐患数量",
        "查询单位消防设备在线率",
        "刚才的结果还有什么风险建议？",
    ]:
        st.markdown(f"- {q}")

with st.sidebar:
    st.subheader("会话状态")
    st.write(f"登录状态：{'✅ 已登录' if state.logged_in else '❌ 未登录'}")
    st.write(f"用户：{state.username or '无'}")
    st.write(f"可选单位：{', '.join(state.units) if state.units else '无'}")
    st.write(f"已选单位：{state.selected_unit or '无'}")
    st.write(f"待续答问题：{st.session_state.pending_question or '无'}")
    st.divider()
    st.markdown("**支持业务查询（FastMCP 模拟值）**")
    for item in list_supported_business_queries():
        st.markdown(f"- {item}")

for role, content in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(content)

if st.session_state.pending_question and state.logged_in and (len(state.units) <= 1 or state.selected_unit):
    pending = st.session_state.pending_question
    st.session_state.pending_question = None
    handle_question(pending)

question = st.chat_input("请输入问题")
if question:
    st.session_state.chat_history.append(("user", question))
    with st.chat_message("user"):
        st.markdown(question)
    handle_question(question)
