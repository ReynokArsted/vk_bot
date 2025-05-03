from example.utils import create_inline_keyboard, get_user_reminder_frequency
from contextlib import closing
from example.storage.database import get_db
from example.storage.models import UserSettings, User

def handle_reminder_settings(bot, user_id):
    """Обрабатываем нажатие кнопки настройки напоминаний."""
    reminder_frequency = get_user_reminder_frequency(user_id)
    bot.send_text(
        chat_id=user_id,
        text=f"Текущая частота напоминаний:\n{reminder_frequency} минут\nВыберем новую частоту?",
        inline_keyboard_markup=create_inline_keyboard([
            [
                {"text": "15 минут", "callbackData": "set_reminder_15"},
                {"text": "25 минут", "callbackData": "set_reminder_25"}
            ],
            [
                {"text": "30 минут", "callbackData": "set_reminder_30"},
                {"text": "60 минут", "callbackData": "set_reminder_60"}
            ],
            [ {"text": "Назад в главное меню", "callbackData": "to_main_menu"}]
        ])
    )

def handle_set_reminder_frequency(bot, user_id, frequency):
    """Обновляем частоту напоминаний для пользователя."""
    with closing(next(get_db())) as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            db.add(User(id=user_id))
            db.commit()

        user_settings = db.query(UserSettings).filter_by(user_id=user_id).first()
        if user_settings:
            user_settings.reminder_frequency = frequency
        else:
            user_settings = UserSettings(user_id=user_id, reminder_frequency=frequency)
            db.add(user_settings)

        db.commit()

    bot.send_text(
        chat_id=user_id,
        text=f"Частота напоминаний была изменена на {frequency} минут"
    )