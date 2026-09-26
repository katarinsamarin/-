from __future__ import annotations

import argparse
import os
import requests


API = "https://api.telegram.org/bot8913966807:AAFz--QoO5bdMz_LY0JKM2UmV3hA_xl2ik0/{method}"


def _call(token: str, method: str, payload: dict | None = None) -> dict:
    response = requests.post(
        API.format(token=token, method=method),
        json=payload or {},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Telegram API error"))
    return data


def send_message(token: str, chat_id: str, text: str) -> None:
    _call(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
    )


def get_updates(token: str) -> list[dict]:
    return _call(token, "getUpdates").get("result", [])


def format_exam(exam: dict) -> str:
    parts = [
        f"📚 {exam.get('subject') or 'Экзамен'}",
        f"👥 Группа: {exam.get('group', '—')}",
        f"📅 Дата: {exam.get('date', '—')}",
        f"🕐 Время: {exam.get('time', '—')}",
        f"👨‍🏫 Преподаватель: {exam.get('teacher', '—')}",
        f"🏫 Аудитория: {exam.get('room', '—')}",
    ]
    if exam.get("type"):
        parts.append(f"📝 Тип: {exam['type']}")
    if exam.get("extra"):
        parts.append(f"ℹ️ {exam['extra']}")
    parts.append(
        "🔗 https://timetable.spbu.ru/MCSC/StudyProgram/17476"
    )
    return "\n".join(parts)


def format_changes(added: list[dict], changed: list[dict], removed: list[dict]) -> str:
    blocks = []

    for exam in added:
        blocks.append("🆕 НОВАЯ ЗАПИСЬ\n" + format_exam(exam))

    for item in changed:
        blocks.append(
            "✏️ ИЗМЕНЕНИЕ В РАСПИСАНИИ\n"
            "Было:\n"
            + format_exam(item["before"])
            + "\n\nСтало:\n"
            + format_exam(item["after"])
        )

    for exam in removed:
        blocks.append("❌ ЗАПИСЬ ИСЧЕЗЛА\n" + format_exam(exam))

    return "\n\n────────────\n\n".join(blocks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--get-chat-id", action="store_true")
    args = parser.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")

    if args.get_chat_id:
        updates = get_updates(token)
        if not updates:
            print("Нет updates. Напиши боту /start и запусти команду ещё раз.")
            return

        seen = set()
        for update in updates:
            message = update.get("message") or update.get("channel_post")
            if not message:
                continue
            chat = message.get("chat", {})
            chat_id = chat.get("id")
            if chat_id in seen:
                continue
            seen.add(chat_id)
            print(
                f"chat_id={chat_id} | "
                f"type={chat.get('type')} | "
                f"title={chat.get('title') or chat.get('first_name', '')}"
            )


if __name__ == "__main__":
    main()
