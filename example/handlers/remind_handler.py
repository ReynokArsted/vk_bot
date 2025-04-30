from example.utils import create_inline_keyboard, get_user_reminder_frequency
from contextlib import closing
from example.storage.database import get_db
from example.storage.models import UserSettings, User

def handle_reminder_settings(bot, user_id):
    """Обрабатываем нажатие кнопки настройки напоминаний."""
    reminder_frequency = get_user_reminder_frequency(user_id)
    bot.send_text(
        chat_id=user_id,
        text=f"Текущая частота напоминаний: {reminder_frequency} минут.\nВыберем новую частоту?",
        inline_keyboard_markup=create_inline_keyboard([
            [
                {"text": "15 минут", "callbackData": "set_reminder_15"},
                {"text": "25 минут", "callbackData": "set_reminder_25"}
            ],
            [
                {"text": "30 минут", "callbackData": "set_reminder_30"},
                {"text": "60 минут", "callbackData": "set_reminder_60"}
            ]
        ])
    )

def handle_set_reminder_frequency(bot, user_id, frequency):
    """Обновляем частоту напоминаний для пользователя."""
    valid_frequencies = [15, 25, 30, 60]  # допустимые значения

    try:
        # Проверка на допустимые значения
        if frequency not in valid_frequencies:
            raise ValueError(f"Недопустимая частота напоминаний. Допустимые значения: {', '.join(map(str, valid_frequencies))} минут.")

        # Обновляем настройку частоты напоминаний в базе данных
        with closing(next(get_db())) as db:
            user_settings = db.query(UserSettings).filter_by(user_id=user_id).first()
            if user_settings:
                user_settings.reminder_frequency = frequency
            else:
                user_settings = UserSettings(user_id=user_id, reminder_frequency=frequency)
                db.add(user_settings)
            db.commit()

        # Отправляем пользователю подтверждение
        bot.send_text(
            chat_id=user_id,
            text=f"Частота напоминаний была изменена на {frequency} минут"
        )
    except Exception as e:
        bot.send_text(
            chat_id=user_id,
            text=f"Произошла ошибка при изменении частоты напоминаний: {e}"
        )
