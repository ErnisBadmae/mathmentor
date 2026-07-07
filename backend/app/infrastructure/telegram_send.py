"""Единственная точка доставки наставнических заметок в Telegram.

Заметки публикуются из трёх мест (MCP-агент, веб-форма оператора, команда /send в боте),
а доставку в Telegram делает одна функция — ``deliver_pending_notes``. Отправка синхронная
через urllib + прокси (тот же паттерн, что healthcheck ``telegram_getme_health``), поэтому
работает из любого процесса: и из MCP/API на хосте, и из aiogram-бота в контейнере — не
требуя запущенного бота.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import TYPE_CHECKING
from uuid import UUID

from app.infrastructure.db import SessionLocal
from app.infrastructure.repositories import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

# Один ученик в семейном пилоте (all-zero UUID, который используют фронт/seed/MCP).
PILOT_STUDENT_ID = UUID("00000000-0000-0000-0000-000000000000")
TELEGRAM_LIMIT = 4096
SEND_TIMEOUT_SECONDS = 15.0


def _proxy(settings: Settings) -> str | None:
    """Telegram бывает доступен только через прокси (напр. в RU): из настройки или env."""
    return (
        settings.telegram_proxy_url
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or None
    )


def _split(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Telegram отклоняет сообщения длиннее 4096 символов — режем длинную заметку на части."""
    return [text[i : i + limit] for i in range(0, len(text), limit)] or [""]


def send_telegram_message(settings: Settings, chat_id: int, text: str) -> None:
    """Отправить одно сообщение. Бросает исключение при сетевой ошибке или ok=false."""
    proxy = _proxy(settings)
    opener = (
        urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        if proxy
        else urllib.request.build_opener()
    )
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with opener.open(request, timeout=SEND_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read())
    if not body.get("ok"):
        raise RuntimeError(f"Telegram sendMessage failed: {body.get('description')}")


def deliver_pending_notes(settings: Settings, student_id: UUID = PILOT_STUDENT_ID) -> int:
    """Доставить ученику все ещё не доставленные заметки. Возвращает число доставленных.

    At-least-once: шлём → помечаем delivered. Повтор после успешной доставки заметку не
    дублирует; редкий дубль возможен только при краше между отправкой и commit — для пилота
    допустимо. При успешной доставке родитель-контролёр получает пинг (best-effort)."""
    student_chat = settings.telegram_student_chat_id.strip()
    if not student_chat:
        raise RuntimeError("telegram_student_chat_id не задан — некому доставлять заметку")
    student_chat_id = int(student_chat)
    parent_chat = settings.telegram_parent_chat_id.strip()

    with SessionLocal() as session:
        notes = SqlAlchemyUnitOfWork(session).mentor_notes.list_undelivered(student_id)
    for note in notes:
        for chunk in _split(f"💬 От наставника:\n\n{note['body']}"):
            send_telegram_message(settings, student_chat_id, chunk)
        with SessionLocal() as session:
            uow = SqlAlchemyUnitOfWork(session)
            uow.mentor_notes.mark_delivered([note["id"]])
            uow.commit()
        if parent_chat:
            _notify_parent(settings, parent_chat, str(note["body"]))
    return len(notes)


def _notify_parent(settings: Settings, parent_chat: str, body: str) -> None:
    """Пинг родителю-контролёру о доставке. Best-effort: сбой пинга не рушит доставку ученику."""
    preview = body if len(body) <= 200 else body[:200] + "…"
    try:
        send_telegram_message(
            settings,
            int(parent_chat),
            f"📨 Заметка наставника доставлена ученику:\n\n{preview}",
        )
    except Exception:
        logger.exception("Failed to notify parent about mentor note delivery")
