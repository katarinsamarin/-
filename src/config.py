from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    url: str = os.getenv(
        "SCHEDULE_URL",
        "https://timetable.spbu.ru/MCSC/StudyProgram/17476",
    )
    groups: tuple[str, ...] = (
        "25.Б02-мкн",
        "25.Б03-мкн",
    )
    section_title: str = (
        "Intermediary attestation for the previous academic year 2025-2026"
    )
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    state_file: str = os.getenv("STATE_FILE", "state/last_schedule.json")
