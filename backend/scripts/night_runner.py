#!/usr/bin/env python3
"""Minimal overnight task runner — proving harness, NOT a framework.

Ключевая идея против переполнения контекста: СВЕЖИЙ контекст на каждую задачу.
Runner — тупой цикл. Состояние живёт в git + отчёте, не в окне модели.
Каждая задача гоняется в одноразовом git worktree — executor НИКОГДА не трогает
основную рабочую копию. На красном — revert + удаление worktree, переход к следующей.

Сегодня = ПРОВЕРОЧНЫЙ прогон на крошечной очереди, не 8-часовой grind.
Morning-review архитектором обязателен (отчёт содержит сырой вывод).

Канонический источник — репозиторий expert-agent; в другие репозитории копируется
как есть, сверка версий по VERSION ниже. В egeMentor разрешено сохранять
репо-специфику путей: REPO / WORKTREE_ROOT / DEFAULT_QUEUE / OPENCODE /
AUTO_APPROVE_EDITS.
Changelog:
  1.0 — базовый runner.
  1.1 — копирование .env в worktree + sh_logged full-log + LOG_TAIL_CHARS.

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

VERSION = "1.1"

REPO = pathlib.Path(__file__).resolve().parents[1]
WORKTREE_ROOT = pathlib.Path(
    os.environ.get("NIGHT_RUNNER_WORKTREE_ROOT", "C:/tmp/egeMentor-qwen-runs")
)
DEFAULT_QUEUE = REPO / "scripts" / "night_queue.json"
BASE_REF = "HEAD"
LOG_TAIL_CHARS = 3000
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


def sh_full(cmd: list[str], cwd: pathlib.Path, timeout: int = 1800) -> tuple[int, str]:
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
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sh(cmd: list[str], cwd: pathlib.Path, timeout: int = 1800) -> tuple[int, str]:
    rc, out = sh_full(cmd, cwd, timeout)
    return rc, out[-LOG_TAIL_CHARS:]


def _write_full_log(log_dir: pathlib.Path, name: str, content: str) -> str:
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"{name}.log"
        path.write_text(content, encoding="utf-8")
        return str(path)
    except OSError as exc:
        return f"<full log unavailable: {exc}>"


def sh_logged(
    cmd: list[str],
    cwd: pathlib.Path,
    timeout: int,
    log_dir: pathlib.Path,
    name: str,
) -> tuple[int, str, str]:
    rc, out = sh_full(cmd, cwd, timeout)
    log_path = _write_full_log(log_dir, name, out)
    return rc, out[-LOG_TAIL_CHARS:], log_path


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


def run_task(t: dict, wt: pathlib.Path, dry: bool, log_dir: pathlib.Path) -> tuple[str, str]:
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
        erc, eout, log_path = sh_logged(
            cmd,
            wt,
            t.get("timeout", 1800),
            log_dir,
            "executor",
        )
        detail += f"executor rc={erc}\nFull log: {log_path}\n```\n{eout}\n```\n"
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
    for idx, cmd in enumerate(t["acceptance"], start=1):
        argv = [PY if a == "{PY}" else a for a in cmd]
        rc, out, log_path = sh_logged(
            argv,
            wt,
            t.get("timeout", 1800),
            log_dir,
            f"acceptance-{idx:02d}",
        )
        detail += f"$ {' '.join(cmd)}\nrc={rc}\nFull log: {log_path}\n```\n{out}\n```\n"
        if rc == 124:
            return "BLOCKED", detail
        if rc != 0:
            status = "RED"
            break
    allowed = set(t.get("files_allowed") or [])
    if status == "GREEN" and allowed:
        rc, files = changed_files(wt)
        if rc != 0:
            return "BLOCKED", detail + "could not inspect changed files after acceptance\n"
        unexpected = sorted(files - allowed)
        if unexpected:
            return (
                "RED",
                detail
                + "files_allowed violation after acceptance:\n"
                + "\n".join(f"- {path}" for path in unexpected)
                + "\n",
            )
    return status, detail


def main() -> None:
    try:  # Windows-консоль может быть cp1251 — печатаем безопасно
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="skip executor, test plumbing")
    ap.add_argument(
        "--queue",
        default=str(DEFAULT_QUEUE),
        help="queue JSON path; defaults to backend/scripts/night_queue.json",
    )
    args = ap.parse_args()

    queue_path = pathlib.Path(args.queue)
    if not queue_path.is_absolute():
        queue_path = (REPO.parent / queue_path).resolve()
    tasks = json.loads(queue_path.read_text(encoding="utf-8"))
    date = datetime.date.today().isoformat()
    run_id = datetime.datetime.now().strftime("%H%M%S")  # уникальность ветки/worktree на прогон
    out_dir = WORKTREE_ROOT / date
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# night_runner {date}-{run_id} ({'DRY' if args.dry_run else 'LIVE'})\n",
        f"queue: {queue_path}\n",
    ]
    sh(["git", "worktree", "prune"], REPO, 60)

    for t in tasks:
        tid = t["id"]
        branch = f"auto/{date}-{run_id}/{tid}"
        wt = out_dir / f"{tid}-{run_id}"
        rc, wout = sh(["git", "worktree", "add", "-b", branch, str(wt), BASE_REF], REPO, 120)
        if rc != 0:
            lines.append(f"## {tid} — BLOCKED (worktree add)\n```\n{wout}\n```\n")
            continue
        env_file = REPO.parent / ".env"
        if env_file.exists():
            shutil.copy2(env_file, wt / ".env")
        log_dir = out_dir / "logs" / f"{tid}-{run_id}"
        status, detail = run_task(t, wt, args.dry_run, log_dir)
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
