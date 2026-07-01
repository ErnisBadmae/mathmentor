from app.adapters.mcp.sandbox_server import run_student_simulation


def test_sandbox_mcp_run_student_simulation():
    result = run_student_simulation()

    assert result["ok"] is True
    cases = {case["name"]: case for case in result["cases"]}
    assert cases["interval_wrong_overlay"]["visual_kind"] == "number_line"
    assert cases["interval_unparseable_answer"]["visual_kind"] == "number_line"
    assert cases["probability_wrong_answer"]["visual_kind"] == "probability"
