from app.adapters.mcp.sandbox_server import run_student_simulation


def test_sandbox_mcp_run_student_simulation():
    result = run_student_simulation()

    assert result["ok"] is True
    cases = {case["name"]: case for case in result["cases"]}
    assert cases["interval_wrong_overlay"]["visual_kind"] == "number_line"
    assert cases["interval_unparseable_answer"]["visual_kind"] == "number_line"
    assert cases["probability_bar_chart_wrong_answer"]["visual_kind"] == "probability"
    assert cases["probability_table_neither_wrong_answer"]["visual_kind"] == "probability"
    assert cases["probability_table_only_a_wrong_answer"]["visual_kind"] == "probability"
