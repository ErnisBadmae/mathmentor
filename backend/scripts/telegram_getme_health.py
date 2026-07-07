"""Container healthcheck for Telegram reachability.

Read-only: validates bot token + configured proxy by calling Telegram getMe. It does
not send messages and does not touch the product database.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request


def _proxy_url() -> str | None:
    return (
        os.environ.get("TELEGRAM_PROXY_URL")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
    )


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("telegram_getme_health: FAIL missing TELEGRAM_BOT_TOKEN")
        return 1
    timeout = float(os.environ.get("TELEGRAM_HEALTH_TIMEOUT_SECONDS", "15"))
    proxy = _proxy_url()
    opener = (
        urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        if proxy
        else urllib.request.build_opener()
    )
    try:
        response = opener.open(f"https://api.telegram.org/bot{token}/getMe", timeout=timeout)
        payload = json.loads(response.read())
    except Exception as exc:
        print(f"telegram_getme_health: FAIL {type(exc).__name__}")
        return 1
    if not payload.get("ok"):
        print("telegram_getme_health: FAIL getMe returned ok=false")
        return 1
    username = payload.get("result", {}).get("username") or "unknown"
    print(f"telegram_getme_health: OK @{username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
