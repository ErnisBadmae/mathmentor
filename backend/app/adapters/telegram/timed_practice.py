"""Timed CISIA delivery. PostgreSQL owns answers/deadlines; tasks only notify."""

import asyncio
import logging
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from app.application.use_cases import LearningService, RuleBasedReviewer
from app.config import get_settings
from app.infrastructure.db import SessionLocal
from app.infrastructure.repositories import SqlAlchemyUnitOfWork

STUDENT = UUID("00000000-0000-0000-0000-000000000000")
_timers: dict[UUID, asyncio.Task] = {}
logger = logging.getLogger(__name__)


def _service(session):
    return LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())


def result_text(block):
    lines = [
        "⏱ Тренировка CISIA завершена",
        "Время вышло." if block["finish_reason"] == "deadline" else "Завершено тобой.",
        f"Верно: {block['correct']}/{block['total']}. Пропуски: {block['skipped']}.",
        f"Время: {block['elapsed_seconds'] // 60}:{block['elapsed_seconds'] % 60:02d}.",
        f"Незнакомые: {block['independent']}/{block['total']}; "
        f"верно среди них: {block['independent_correct']}.",
        "Это тренировка темпа, не официальный экзаменационный балл.",
    ]
    for index, task in enumerate(block["tasks"], 1):
        mark = "✓" if task["answer"] == task["correct_answer"] else "✗"
        lines.append(
            f"{index}. CISIA №{task['number']}: {task['answer'] or '—'} "
            f"{mark}; ключ: {task['correct_answer']}."
        )
    return "\n".join(lines)


async def guard(message):
    with SessionLocal() as session:
        block = _service(session).active_timed_block(STUDENT)
    if block and not block["finished"]:
        await message.answer(
            "Идёт тренировка с таймером. Продолжить: /timed. "
            "Сначала заверши её; /cancel не останавливает часы."
        )
        return True
    if block and block["newly_finished"]:
        await message.answer(result_text(block))
    return False


async def on_timed(message):
    with SessionLocal() as session:
        service = _service(session)
        block = service.active_timed_block(STUDENT)
        last = service.last_timed_block(STUDENT) if block is None else None
    if block:
        await show(message, block)
        return
    await message.answer(
        "⏱ CISIA: 5 вопросов по математике / 10 минут\n\n"
        "Общий таймер начнётся после кнопки «Начать». Отвечай кнопками A–E; "
        "можно менять ответы и возвращаться по номерам. Ключ — после завершения. "
        "Остаток времени обновляется при действиях; в конце придёт уведомление. "
        "Пропуск — вопрос без ответа. Баллы: верно 1, неверно/пропуск 0.\n\n"
        "Ответ принимается, когда его сохранит сервер строго до дедлайна. "
        "При задержке сети нажатие может прийти поздно. Перезапуск и /cancel "
        "не продлевают время.\n\n"
        "Это учебная настройка, не правила конкретного экзамена. Ранее назначенные "
        "вопросы считаем знакомыми, даже если неизвестно, открывала ли ты их.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Начать · 10 минут", callback_data="tb:start")]
            ]
            + (
                [
                    [
                        InlineKeyboardButton(
                            text="Результат прошлого блока", callback_data=f"tb:{last['id']}:0:go"
                        )
                    ]
                ]
                if last
                else []
            )
        ),
    )


async def on_callback(callback):
    if str(callback.message.chat.id) not in get_settings().authorized_chat_ids:
        await callback.answer("Не авторизовано", show_alert=True)
        return
    try:
        parts = callback.data.split(":")
        with SessionLocal() as session:
            service = _service(session)
            if callback.data == "tb:start":
                block = service.start_timed_block(STUDENT)
                index = 0
            else:
                if len(parts) != 4:
                    raise ValueError("Некорректная кнопка")
                block_id, index, action = UUID(parts[1]), int(parts[2]), parts[3]
                if action == "end":
                    block = service.finish_timed_block(STUDENT, block_id)
                elif action in "ABCDE" and len(action) == 1:
                    block = service.answer_timed_block(STUDENT, block_id, index, action)
                elif action == "go":
                    block = service.active_timed_block(STUDENT, block_id)
                else:
                    raise ValueError("Некорректная кнопка")
        await callback.answer(
            "Ответ сохранён" if parts[-1] in list("ABCDE") and not block["finished"] else ""
        )
        await show(callback.message, block, index)
    except (ValueError, LookupError):
        await callback.answer("Эта кнопка недоступна. Открой /timed.", show_alert=True)


async def show(message, block, index=0):
    block_id = block["id"]
    if block["finished"]:
        await message.answer(result_text(block))
        return
    if not 0 <= index < len(block["tasks"]):
        index = 0
    task = block["tasks"][index]
    remaining = block["remaining_seconds"]
    deadline = block["deadline_at"].astimezone(ZoneInfo(get_settings().local_timezone))
    caption = (
        f"⏱ CISIA · {index + 1}/{block['total']} · осталось "
        f"{remaining // 60}:{remaining % 60:02d} · до {deadline:%H:%M:%S}\n"
        f"{task['statement']}\n"
        f"{'Ранее доступный вопрос' if task['familiar'] else 'Новый вопрос'}. "
        f"Твой ответ: {task['answer'] or 'не выбран'}.\n"
        "Можно изменить ответ или выбрать другой номер. Проверка — в конце."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=letter, callback_data=f"tb:{block_id}:{index}:{letter}")
                for letter in "ABCDE"
            ],
            [
                InlineKeyboardButton(
                text=f"{i + 1}{' •' if item['answer'] else ''}",
                    callback_data=f"tb:{block_id}:{i}:go",
                )
                for i, item in enumerate(block["tasks"])
            ],
            [
                InlineKeyboardButton(
                    text="Завершить и проверить", callback_data=f"tb:{block_id}:0:end"
                )
            ],
        ]
    )
    path = Path(__file__).resolve().parents[3] / "data/cisia" / f"q{task['number']:02d}.png"
    await message.answer_photo(FSInputFile(path), caption=caption, reply_markup=keyboard)
    schedule(message.bot, message.chat.id, block)


def schedule(bot, chat_id, block):
    if block["id"] not in _timers:
        _timers[block["id"]] = asyncio.create_task(_notify_deadline(bot, chat_id, block["id"]))


async def _notify_deadline(bot, chat_id, block_id):
    try:
        while True:
            with SessionLocal() as session:
                block = _service(session).active_timed_block(STUDENT, block_id)
            if block["finished"]:
                if block["newly_finished"]:
                    await bot.send_message(chat_id, result_text(block))
                return
            await asyncio.sleep(max(1, block["remaining_seconds"]))
    except Exception:
        # shortcut: no durable Telegram outbox; /timed/old block buttons recover DB results.
        logger.exception("Timed block notification failed; result remains recoverable")
    finally:
        _timers.pop(block_id, None)


async def restore_timer(bot):
    chat = get_settings().telegram_student_chat_id
    if not chat:
        return
    with SessionLocal() as session:
        block = _service(session).active_timed_block(STUDENT)
    if block and block["newly_finished"]:
        await bot.send_message(int(chat), result_text(block))
    elif block:
        schedule(bot, int(chat), block)
