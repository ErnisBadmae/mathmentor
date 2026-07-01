#!/usr/bin/env python3
"""Minimal overnight task runner — proving harness, NOT a framework.

Ключевая идея против переполнения контекста: СВЕЖИЙ контекст на каждую задачу.
Runner — тупой цикл. Состояние живёт в git + отчёте, не в окне модели.
Каждая задача гоняется в одноразовом git worktree — executor НИКОГДА не трогает
основную рабочую копию. На красном — revert + удаление worktree, переход к следующей.

Сегодня = ПРОВЕРОЧНЫЙ прогон на крошечной очереди, не 8-часовой grind.
Morning-review архитектором обязателен (отчёт содержит сырой вывод).

Запуск:
  python scripts/night_runner.py --dry-run   # проверить плумбинг без executor (безопасно)
  python scripts/night_runner.py             # реальный прогон

Ограничения (честно):
- Сервисы (локальный Qwen + API) должны быть подняты всю ночь — acceptance гоняет gate.
- Подходят только задачи, чей acceptance читает файлы worktree В ПРОЦЕССЕ (gate/pytest/YAML/config).
  Задачи, требующие, чтобы API отдавал НОВЫЙ код, сюда не годятся (нужен рестарт против worktree).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
WORKTREE_ROOT = pathlib.Path(
    os.environ.get("NIGHT_RUNNER_WORKTREE_ROOT", "C:/tmp/egeMentor-qwen-runs")
)
QUEUE = REPO / "scripts" / "night_queue.json"
BASE_REF = "HEAD"
# venv-python (auto-detect любого venv*/.venv); подставляется вместо токена "{PY}" в acceptance.
_VENV_PY = next(
    (
        p
        for p in REPO.glob("*venv*/Scripts/python.exe")
        if (p.parents[1] / "pyvenv.cfg").exists()
    ),
    None,
)
PY = str(_VENV_PY) if _VENV_PY else "python"

# opencode-CLI (переиспользует ~/.config/opencode с провайдером Qwen). Полный путь к .CMD —
# Python subprocess на Windows не находит bare-имя .cmd-шима.
OPENCODE = shutil.which("opencode") or "opencode"
# headless: --format json (без TUI-рендера, иначе виснет без TTY), --dir <worktree>.
# AUTO_APPROVE_EDITS=True добавляет --dangerously-skip-permissions (авто-approve правок).
# Безопасно ТОЛЬКО из-за worktree-изоляции + no-auto-merge + morning-review. Запуск раннера
# с этим флагом = твоя явная авторизация автономных правок. Альтернатива безопаснее:
# настроить точечные permission-правила в ~/.config/opencode/opencode.jsonc и выключить флаг.
AUTO_APPROVE_EDITS = True
# Self-check preamble: python НЕ на PATH в окружении opencode → Qwen отгружал непроверенный код.
# Даём полный путь к venv-python (forward slashes для bash), чтобы модель сама прогнала тесты.
_PY_POSIX = _VENV_PY.as_posix() if _VENV_PY else "python"
# Вешается ПОСЛЕ задачи (append). Иначе слабая модель принимает preamble за саму задачу и не работает.
SELF_VERIFY = (
    f"\n\n---\nСначала ВЫПОЛНИ задачу выше (внеси правки в файлы). ПОТОМ, перед финишем, self-check "
    f"(python НЕ на PATH — только полный путь к venv):\n"
    f"1) тесты: `{_PY_POSIX} -m pytest <нужные_файлы> -q` → rc=0;\n"
    f"2) lint изменённых .py: `{_PY_POSIX} -m flake8 <files>` и `{_PY_POSIX} -m black <files>`.\n"
    f"Исправь всё красное. НЕ финишируй, пока правки НЕ внесены и тесты/lint НЕ зелёные."
)


def sh(cmd: list[str], cwd: pathlib.Path, timeout: int = 1800) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,  # иначе cp1251 давится выводом opencode
        )
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    tail = (p.stdout or "")[-1500:] + (p.stderr or "")[-1500:]
    return p.returncode, tail


def changed_files(wt: pathlib.Path) -> tuple[int, set[str]]:
    rc, out = sh(["git", "status", "--porcelain"], wt, 60)
    if rc != 0:
        return rc, set()
    files = set()
    for line in out.splitlines():
        path = line[3:].strip()
        if path:
            files.add(path)
    return 0, files


def status_snapshot(path: pathlib.Path) -> tuple[int, set[str]]:
    rc, out = sh(["git", "status", "--porcelain"], path, 60)
    if rc != 0:
        return rc, set()
    # ``sh`` returns stderr too; local Git can emit warnings such as a denied
    # global ignore file. Keep only porcelain status records.
    lines = set()
    for raw in out.splitlines():
        line = raw.rstrip()
        if len(line) >= 4 and line[:2] != "wa" and line[2] == " ":
            lines.add(line)
    return 0, lines


def run_task(t: dict, wt: pathlib.Path, dry: bool) -> tuple[str, str]:
    detail = ""
    has_prompt = bool(t.get("prompt"))
    kind = t.get("kind") or ("edit" if has_prompt else "run")
    if kind not in {"run", "edit", "report"}:
        return "BLOCKED", f"unsupported task kind: {kind}\n"
    if dry and has_prompt:
        detail += "dry-run: executor and prompt-dependent acceptance skipped\n"
        return "GREEN", detail

    if not dry and has_prompt:
        main_rc, main_before = status_snapshot(REPO)
        if main_rc != 0:
            return "BLOCKED", detail + "could not inspect main worktree before executor\n"
        if main_before:
            return (
                "BLOCKED",
                detail
                + "main worktree must be clean before live executor run:\n"
                + "\n".join(f"- {line}" for line in sorted(main_before))
                + "\n",
            )
        prompt_preview = t["prompt"].replace("\n", "\\n")
        detail += f"prompt preview: {prompt_preview[:500]}\n"
        cmd = [OPENCODE, "run", "--format", "json", "--dir", str(wt)]
        if AUTO_APPROVE_EDITS:
            cmd.append("--dangerously-skip-permissions")
        cmd.append(t["prompt"] + SELF_VERIFY)
        erc, eout = sh(cmd, wt, t.get("timeout", 1800))
        detail += f"executor rc={erc}\n```\n{eout[-1500:]}\n```\n"
        main_rc, main_after = status_snapshot(REPO)
        if main_rc != 0:
            return "BLOCKED", detail + "could not inspect main worktree after executor\n"
        contamination = sorted(main_after - main_before)
        if contamination:
            return (
                "BLOCKED",
                detail
                + "main worktree changed during isolated executor run:\n"
                + "\n".join(f"- {line}" for line in contamination)
                + "\n",
            )
        if erc != 0:
            return "RED", detail
        rc, files = changed_files(wt)
        if rc != 0:
            return "BLOCKED", detail + "could not inspect changed files\n"
        if kind == "report" and files:
            return (
                "RED",
                detail
                + "report task changed files:\n"
                + "\n".join(f"- {path}" for path in sorted(files))
                + "\n",
            )
        allowed = set(t.get("files_allowed") or [])
        if allowed:
            unexpected = sorted(files - allowed)
            if unexpected:
                return (
                    "RED",
                    detail
                    + "files_allowed violation:\n"
                    + "\n".join(f"- {path}" for path in unexpected)
                    + "\n",
                )
        if kind != "report" and not files:
            return "RED", detail + "executor made no file changes\n"

    # acceptance = список команд (каждая — список аргументов), БЕЗ shell; "{PY}" → venv-python.
    status = "GREEN"
    for cmd in t["acceptance"]:
        argv = [PY if a == "{PY}" else a for a in cmd]
        rc, out = sh(argv, wt, t.get("timeout", 1800))
        detail += f"$ {' '.join(cmd)}\nrc={rc}\n```\n{out}\n```\n"
        if rc == 124:
            return "BLOCKED", detail
        if rc != 0:
            status = "RED"
            break
    return status, detail


def main() -> None:
    try:  # Windows-консоль может быть cp1251 — печатаем безопасно
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="skip executor, test plumbing")
    args = ap.parse_args()

    tasks = json.loads(QUEUE.read_text(encoding="utf-8"))
    date = datetime.date.today().isoformat()
    run_id = datetime.datetime.now().strftime("%H%M%S")  # уникальность ветки/worktree на прогон
    out_dir = WORKTREE_ROOT / date
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# night_runner {date}-{run_id} ({'DRY' if args.dry_run else 'LIVE'})\n"]
    sh(["git", "worktree", "prune"], REPO, 60)

    for t in tasks:
        tid = t["id"]
        branch = f"auto/{date}-{run_id}/{tid}"
        wt = out_dir / f"{tid}-{run_id}"
        rc, wout = sh(["git", "worktree", "add", "-b", branch, str(wt), BASE_REF], REPO, 120)
        if rc != 0:
            lines.append(f"## {tid} — BLOCKED (worktree add)\n```\n{wout}\n```\n")
            continue
        status, detail = run_task(t, wt, args.dry_run)
        if status == "GREEN" and not args.dry_run and t.get("prompt") and t.get("kind") != "report":
            sh(["git", "add", "-A"], wt)
            # --no-verify: гейт уже прогнал black/flake8/pytest; иначе pre-commit отбивает commit.
            crc, cout = sh(["git", "commit", "-m", f"auto: {tid}", "--no-verify"], wt)
            detail += f"$ git commit -m auto: {tid} --no-verify\nrc={crc}\n```\n{cout}\n```\n"
            if crc != 0:
                status = "RED"
        if status != "GREEN" or args.dry_run or not t.get("prompt") or t.get("kind") == "report":
            sh(["git", "worktree", "remove", "--force", str(wt)], REPO)
            sh(["git", "branch", "-D", branch], REPO)  # не-green: чистим и ветку
        lines.append(f"## {tid} — {status} (branch {branch})\n{detail}\n")

    report = out_dir / f"report-{run_id}.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"[night_runner] done -> {report}")
    for ln in lines:
        if ln.startswith("## "):
            print(ln.strip())


if __name__ == "__main__":
    main()
