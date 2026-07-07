"""Read-only runtime smoke for the Telegram bot Compose service.

Checks the failure mode that can silently break the daily loop:
- bot service is running and not unhealthy;
- recent bot logs do not contain Telegram polling/proxy/network failures;
- Telegram getMe works from inside the bot container with its active environment.

No messages are sent to the student and the product database is not modified.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


POLLING_ERROR_PATTERNS = (
    "Failed to fetch updates",
    "ProxyConnectionError",
    "TelegramNetworkError",
    "Traceback",
)

GETME_INLINE = r"""
import json
import os
import sys
import urllib.request

token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    print("missing TELEGRAM_BOT_TOKEN")
    raise SystemExit(1)
proxy = (
    os.environ.get("TELEGRAM_PROXY_URL")
    or os.environ.get("HTTPS_PROXY")
    or os.environ.get("https_proxy")
)
handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy}) if proxy else None
opener = urllib.request.build_opener(handler) if handler else urllib.request.build_opener()
try:
    data = opener.open(
        "https://api.telegram.org/bot" + token + "/getMe",
        timeout=15,
    ).read()
    payload = json.loads(data)
except Exception as exc:
    print(type(exc).__name__)
    raise SystemExit(1)
if not payload.get("ok"):
    print("getMe returned ok=false")
    raise SystemExit(1)
print("@" + (payload.get("result", {}).get("username") or "unknown"))
"""


def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _has_polling_errors(log_text: str) -> list[str]:
    return [
        line
        for line in log_text.splitlines()
        if any(pattern in line for pattern in POLLING_ERROR_PATTERNS)
    ]


def check_service_running() -> tuple[bool, str]:
    result = _run(["docker", "compose", "ps", "bot"], timeout=20)
    if result.returncode != 0:
        return False, result.stderr.strip() or "docker compose ps failed"
    output = result.stdout.strip()
    if "unhealthy" in output.lower():
        return False, "bot service is unhealthy"
    if "Up" not in output:
        return False, output or "bot service is not Up"
    return True, "bot service is Up"


def check_recent_logs(since: str, tail: int) -> tuple[bool, str]:
    result = _run(
        ["docker", "compose", "logs", "bot", "--since", since, "--tail", str(tail)],
        timeout=30,
    )
    if result.returncode != 0:
        return False, result.stderr.strip() or "docker compose logs failed"
    matches = _has_polling_errors(result.stdout)
    if matches:
        preview = " | ".join(matches[-3:])
        return False, f"{len(matches)} polling error log line(s): {preview}"
    return True, f"no polling errors in last {since}"


def check_getme_from_container() -> tuple[bool, str]:
    result = _run(
        ["docker", "compose", "exec", "-T", "bot", "python", "-c", GETME_INLINE],
        timeout=30,
    )
    output = (result.stdout.strip() or result.stderr.strip()).strip()
    if result.returncode != 0:
        return False, f"container getMe failed: {output}"
    return True, f"container getMe OK: {output}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="10m", help="Fresh log window, e.g. 10m or 1h.")
    parser.add_argument("--tail", type=int, default=300)
    args = parser.parse_args()

    checks = [
        ("compose bot", check_service_running()),
        ("bot logs", check_recent_logs(args.since, args.tail)),
        ("bot getMe", check_getme_from_container()),
    ]
    green = True
    for name, (ok, message) in checks:
        print(f"[{'OK  ' if ok else 'FAIL'}] {name}: {message}")
        green = green and ok
    print(f"\nTelegram bot runtime smoke: {'GREEN' if green else 'RED'}")
    return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main())
