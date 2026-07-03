"""Release smoke для живого стека: API health, миграции на head, бот getMe, живой judge.

Только чтение против запущенного деплоя — БЕЗ записи в БД и БЕЗ сообщений ученику. Запускать
сразу после `alembic upgrade head` + рестарта, прежде чем доверять деплою:

    python scripts/release_smoke.py

Сознательно НЕ здесь: реальная доставка заметки ученику в Telegram — это необратимое outward-
действие, оно остаётся ручным one-shot в родительский чат и не прячется в автотест. Глубокая
классификация модели — в scripts/llm_review_gate.py. Логика доставки/грейдинга уже покрыта
обычным pytest (FakeBot + реальный сервис/БД) — здесь только живые границы.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.config import get_settings  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]


def check_health(base_url: str) -> tuple[bool, str]:
    try:
        response = httpx.get(f"{base_url}/api/health", timeout=5)
        body = response.json()
    except Exception as exc:
        return False, f"запрос health не удался: {exc}"
    ok = response.status_code == 200 and body.get("status") == "healthy"
    return ok, f"{base_url}/api/health → {response.status_code} {body}"


def check_migrations(database_url: str) -> tuple[bool, str]:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    heads = set(ScriptDirectory.from_config(cfg).get_heads())
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            current = set(MigrationContext.configure(conn).get_current_heads())
    finally:
        engine.dispose()
    ok = current == heads
    return ok, f"БД={sorted(current)} код_head={sorted(heads)}"


async def check_bot_getme(settings) -> tuple[bool, str]:
    if not settings.telegram_bot_token:
        return True, "SKIP: telegram_bot_token не задан"
    try:
        from aiogram import Bot
        from aiogram.client.session.aiohttp import AiohttpSession
    except ImportError:
        return True, "SKIP: aiogram не установлен (нет [bot] extra)"
    proxy = (
        settings.telegram_proxy_url
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
    )
    bot = Bot(
        token=settings.telegram_bot_token,
        session=AiohttpSession(proxy=proxy) if proxy else None,
    )
    try:
        me = await bot.get_me()  # read-only: подтверждает токен+прокси, НЕ шлёт сообщение
        return True, f"getMe OK: @{me.username}"
    finally:
        await bot.session.close()


async def check_live_judge(settings) -> tuple[bool, str]:
    connection = settings.llm_connection()
    if connection is None:
        return True, "SKIP: llm_provider=disabled"
    from app.infrastructure.llm import LlmShortAnswerJudge

    assessment = await LlmShortAnswerJudge(connection).assess("Сколько будет 2+2?", "4", "ответ 4")
    if assessment is None:
        return False, "живой judge вернул None (модель недоступна/мусор)"
    return True, f"живой judge OK: equivalent={assessment.equivalent}"


async def main() -> None:
    settings = get_settings()
    results = [
        ("API health", check_health(settings.public_api_base_url)),
        ("миграции на head", check_migrations(settings.database_url)),
        ("бот getMe", await check_bot_getme(settings)),
        ("живой short-answer judge", await check_live_judge(settings)),
    ]
    green = True
    for name, (ok, msg) in results:
        print(f"[{'OK  ' if ok else 'FAIL'}] {name}: {msg}")
        green = green and ok
    print(f"\nRelease smoke: {'GREEN' if green else 'RED'}")
    sys.exit(0 if green else 1)


if __name__ == "__main__":
    asyncio.run(main())
