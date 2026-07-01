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
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    start = result.stdout.find("{")
    assert start >= 0, result.stdout
    payload = json.loads(result.stdout[start:])

    assert payload["ok"] is True
    cases = {case["name"]: case for case in payload["cases"]}
    assert cases["interval_wrong_overlay"]["visual_kind"] == "number_line"
    assert cases["interval_unparseable_answer"]["visual_kind"] == "number_line"
    assert cases["probability_wrong_answer"]["visual_kind"] == "probability"
