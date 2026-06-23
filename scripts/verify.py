#!/usr/bin/env python
"""Детерминированная пост-проверка для Stop-хука Claude Code.

Если в ``backend`` есть изменения — гоняет pytest и печатает короткий вердикт (OK/FAIL). Без
облачных токенов и без LLM: исполнение детерминированное, поэтому надёжное (локальный qwen тут
не нужен — он только генерит текст, а проверка должна реально запускаться). ruff в гейт НЕ берём:
в репо много pre-existing замечаний (B008 от FastAPI-Depends), он давал бы ложный FAIL — линт
гоняем точечно на изменённых строках вручную.

Запуск (как в хуке): ``backend/.venv312/Scripts/python.exe scripts/verify.py``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PY = BACKEND / ".venv312" / "Scripts" / "python.exe"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=240)


def _last(text: str, default: str) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else default


def main(hook_mode: bool) -> int:
    changed = _run(["git", "status", "--porcelain", "backend"], ROOT).stdout.strip()
    if not changed:
        # В режиме хука молчим (нет изменений — нечего проверять), чтобы не шуметь каждый ход.
        print(json.dumps({"suppressOutput": True}) if hook_mode else "verify: backend без изменений — пропуск")
        return 0
    tests = _run([str(PY), "-m", "pytest", "-q"], BACKEND)
    ok = tests.returncode == 0
    summary = f"verify: {'OK' if ok else 'FAIL'} - pytest: {_last(tests.stdout, 'нет вывода')}"
    if hook_mode:
        # systemMessage виден пользователю; exit 0 → не блокирует завершение.
        print(json.dumps({"systemMessage": summary, "suppressOutput": True}, ensure_ascii=False))
    else:
        print(summary)
    return 0


if __name__ == "__main__":
    # Windows-консоль по умолчанию cp1251 — форсируем utf-8, чтобы кириллица/символы не падали.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
    is_hook = "--hook" in sys.argv
    try:
        sys.exit(main(is_hook))
    except Exception as exc:  # хук не должен падать жёстко — сообщаем и выходим мягко
        print(json.dumps({"suppressOutput": True}) if is_hook else f"verify: ошибка запуска: {exc}")
        sys.exit(0)
