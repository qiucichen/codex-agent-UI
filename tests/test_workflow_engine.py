from workflow_engine import build_engine


def test_business_requires_login_then_auto_resume():
    engine = build_engine()
    sid = engine.create_session().session_id

    first = engine.process_chat(sid, "查询单位的火警数量")
    assert first["ui_action"] == "show_login"
    assert first["state"]["pending_question"] == "查询单位的火警数量"
    assert first["extra"]["ui"]["type"] == "login_form"

    second = engine.login(sid, "user1", "pwd")
    assert second["ui_action"] == "render_result"
    assert "火警" in second["content"]


def test_multi_unit_requires_selection():
    engine = build_engine()
    sid = engine.create_session().session_id

    engine.process_chat(sid, "查询单位的平面图")
    second = engine.login(sid, "admin", "pwd")
    assert second["ui_action"] == "show_unit"
    assert len(second["extra"]["units"]) > 1
    assert second["extra"]["ui"]["type"] == "unit_select"

    third = engine.select_unit(sid, second["extra"]["units"][0])
    assert third["ui_action"] == "render_result"
    assert third["extra"]["chart_type"] in {"floor_plan", "bar", "gauge_like"}
