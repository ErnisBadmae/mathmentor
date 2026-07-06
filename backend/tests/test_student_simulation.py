import json
import subprocess
import sys
from pathlib import Path


def test_student_flow_simulator_script():
    root = Path(__file__).resolve().parents[2]
    script = root / "backend" / "scripts" / "simulate_student_flow.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        text=True,
        capture_output=True,
        # 30s флейкнул в первую ночь флота (2026-07-05): subprocess завершился rc=0,
        # но позже лимита — машина была прогрета очередями соседних репо.
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    start = result.stdout.find("{")
    assert start >= 0, result.stdout
    payload = json.loads(result.stdout[start:])

    assert payload["ok"] is True
    cases = {case["name"]: case for case in payload["cases"]}
    assert cases["interval_wrong_overlay"]["visual_kind"] == "number_line"
    assert cases["interval_correct_answer"]["status"] == "passed"
    assert cases["interval_correct_answer"]["mission_status"] == "done"
    assert cases["interval_correct_answer"]["visual_kind"] == "number_line"
    assert cases["interval_unparseable_answer"]["visual_kind"] == "number_line"
    assert "не удалось распознать" in cases["interval_unparseable_answer"]["visual_caption"]
    assert cases["probability_bar_chart_wrong_answer"]["visual_kind"] == "probability"
    assert cases["probability_table_neither_wrong_answer"]["visual_kind"] == "probability"
    assert cases["probability_table_neither_correct_answer"]["status"] == "passed"
    assert cases["probability_table_neither_correct_answer"]["mission_status"] == "done"
    assert cases["probability_table_neither_correct_answer"]["visual_kind"] == "probability"
    assert cases["probability_table_only_a_wrong_answer"]["visual_kind"] == "probability"
    assert cases["manual_gate_text_solution"]["status"] == "needs_manual_review"
    assert cases["manual_gate_text_solution"]["score_percent"] == 0.0
    assert cases["manual_gate_text_solution"]["mission_status"] == "active"
    assert cases["manual_gate_text_solution"]["manual_review_present"] is True
