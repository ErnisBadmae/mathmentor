from argparse import ArgumentParser
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.infrastructure.db import SessionLocal
from app.infrastructure.importers.tracker_importer import default_tracker_path, import_tracker
from app.infrastructure.importers.xlsx_reader import read_xlsx_preview


def main() -> None:
    parser = ArgumentParser(description="Preview or import the EGE tracker workbook.")
    parser.add_argument("--path", type=Path, default=default_tracker_path())
    parser.add_argument("--write", action="store_true", help="Write canonical records to the configured DB.")
    args = parser.parse_args()

    if args.write:
        session = SessionLocal()
        try:
            summary = import_tracker(session, args.path)
        finally:
            session.close()
        print(summary)
        return

    for sheet in read_xlsx_preview(args.path):
        print(f"\n## {sheet.name}")
        for row in sheet.rows[:10]:
            print(" | ".join(row[:10]))


if __name__ == "__main__":
    main()
