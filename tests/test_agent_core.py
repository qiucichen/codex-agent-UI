from agent_core import UserState, llm_compose_answer, llm_decide, validate_login


def test_llm_decide_normal_chat():
    decision = llm_decide("你好", UserState())
    assert decision.intent == "normal_chat"
    assert not decision.need_login


def test_llm_decide_need_login_and_unit_selection():
    decision = llm_decide("查询单位火警数量", UserState(logged_in=False))
    assert decision.need_login

    state = UserState(logged_in=True, units=["A", "B"], selected_unit=None)
    decision2 = llm_decide("查询单位火警数量", state)
    assert decision2.need_unit_selection


def test_validate_login():
    assert validate_login("u", "p")
    assert not validate_login("", "p")


def test_llm_compose_answer_text_and_chart():
    answer = llm_compose_answer(
        "查询单位火警数量",
        "单位火警数量",
        "默认单位近30天火警数量为2起",
        {"unit": "默认单位", "count": 2, "period": "近30天"},
    )
    assert "查询单位火警数量" in answer.narrative
    assert answer.chart_type == "bar"
