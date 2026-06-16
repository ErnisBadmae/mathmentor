from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.infrastructure.importers.xlsx_reader import read_xlsx_preview


def default_tracker_path() -> Path:
    return (
        Path.home()
        / "Desktop"
        / "\u0415\u0413\u042d"
        / "\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c"
        / "\u0442\u0440\u0435\u043a\u0435\u0440_\u0415\u0413\u042d-\u0444\u0438\u043d\u0430\u043b.xlsx"
    )


def main() -> None:
    for sheet in read_xlsx_preview(default_tracker_path()):
        print(f"\n## {sheet.name}")
        for row in sheet.rows[:10]:
            print(" | ".join(row[:10]))


if __name__ == "__main__":
    main()
