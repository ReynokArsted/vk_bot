from typing import List, Dict
from example.logger import logging
import json
import urllib.parse
import datetime
import os
from dotenv import load_dotenv
from contextlib import closing
from example.storage.database import get_db
from example.storage.models import UserSettings

def load_env():
    load_dotenv()
    if 'DATABASE_URL' not in os.environ:
        raise RuntimeError("Переменная окружения DATABASE_URL не задана")

# Функции для кодировки названия групп и збежания ошибок в формата callback_data
def encode_for_callback(group_id: str, group_name: str) -> str:
    encoded_name = urllib.parse.quote(group_name)
    return f"choose_group_{group_id}|{encoded_name}"

def decode_from_callback(callback_data: str) -> tuple[str, str]:
    raw = callback_data.replace("choose_group_", "")
    if "|" in raw:
        group_id, encoded_name = raw.split("|", 1)
        group_name = urllib.parse.unquote(encoded_name)
    else:
        group_id = raw
        group_name = ""
    return group_id, group_name

def create_inline_keyboard(buttons_list: List[List[Dict[str, str]]]) -> str:
    return json.dumps(buttons_list)

def parse_expiry_time(input_text: str) -> datetime.datetime:
    """
    Разбирает ввод пользователя для определения времени окончания голосования.
    Допустимые форматы:
    • "N мин" — через N минут;
    • "HH:MM" — сегодня в указанное время (если время уже прошло, то следующий день);
    • "DD.MM HH:MM" — указанная дата и время (текущий год);
    • "DD.MM.YYYY HH:MM" — полная дата и время.
    """
    now = datetime.datetime.now()
    try:
        if "мин" in input_text:
            minutes = int(input_text.split()[0])
            return now + datetime.timedelta(minutes=minutes)
        elif ":" in input_text and len(input_text.split()) == 1:
            hour, minute = map(int, input_text.split(":"))
            expiry_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return expiry_time if expiry_time > now else expiry_time + datetime.timedelta(days=1)
        elif len(input_text.split()) == 2:
            date_part, time_part = input_text.split()
            day, month = map(int, date_part.split("."))
            hour, minute = map(int, time_part.split(":"))
            year = now.year
            expiry_time = datetime.datetime(year, month, day, hour, minute)
            return expiry_time if expiry_time > now else expiry_time.replace(year=year + 1)
        elif len(input_text.split(".")) == 3:
            parts = input_text.split()
            if len(parts) != 2:
                return None
            date_part, time_part = parts
            day, month, year = map(int, date_part.split("."))
            hour, minute = map(int, time_part.split(":"))
            return datetime.datetime(year, month, day, hour, minute)
    except Exception as e:
        logging.error(f"Ошибка парсинга времени: {e}")
    return None

def get_user_reminder_frequency(user_id: str) -> int:
    """Получить частоту напоминаний для пользователя (в минутах)."""
    with closing(next(get_db())) as db:
        user_settings = db.query(UserSettings).filter_by(user_id=user_id).first()
        return user_settings.reminder_frequency if user_settings else 60  # Возвращаем 60 минут по умолчанию, если настройки нет


