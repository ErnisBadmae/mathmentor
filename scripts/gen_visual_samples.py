"""Generate 3 PNG visual samples for predeploy review."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.infrastructure.figures_render import render_number_line
from app.domain.figures import parse_interval_answer

OUT = Path(r"C:\Users\badmaev_es\AppData\Local\Temp\ege_mentor_visual_samples")
OUT.mkdir(exist_ok=True)


def sample_1():
    """Correct solution only — interval [−2; 3]."""
    intervals = parse_interval_answer("[−2;3]")
    if intervals is None:
        print("SKIP: sample_1 parse failed")
        return
    png = render_number_line(
        intervals=intervals,
        label="Решение",
        student_intervals=None,
        student_label=None,
    )
    (OUT / "01_correct_only.png").write_bytes(png)
    print(f"01_correct_only.png — {len(png)} bytes")


def sample_2():
    """Correct vs wrong — correct=[1;9], student=(2;7)."""
    correct = parse_interval_answer("[1;9]")
    student = parse_interval_answer("(2;7)")
    png = render_number_line(
        intervals=correct,
        label="Решение",
        student_intervals=student,
        student_label="Ответ ученика",
    )
    (OUT / "02_correct_vs_wrong.png").write_bytes(png)
    print(f"02_correct_vs_wrong.png — {len(png)} bytes")


def sample_3():
    """Correct vs overlay — correct=(-∞;−2)∪[1;+∞), student=(-∞;−2]∪(1;+∞)."""
    correct = parse_interval_answer("(-∞;−2)∪[1;+∞)")
    student = parse_interval_answer("(-∞;−2]∪(1;+∞)")
    png = render_number_line(
        intervals=correct,
        label="Решение",
        student_intervals=student,
        student_label="Ответ ученика",
    )
    (OUT / "03_odz_overlay.png").write_bytes(png)
    print(f"03_odz_overlay.png — {len(png)} bytes")


if __name__ == "__main__":
    sample_1()
    sample_2()
    sample_3()
    print(f"\nAll samples in: {OUT}")
