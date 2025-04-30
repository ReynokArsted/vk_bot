from bot.bot import Bot
from example.utils import create_inline_keyboard

def show_main_menu(bot: Bot, chat_id: str, is_private_chat: bool) -> None:
    if is_private_chat:
        text = "Привет! Создадим запрос на апрув?"
        buttons = [
            [{"text": "Создать запрос на апрув", "callbackData": "create_approval_request"}],
            [{"text": "Посмотреть статус запросов", "callbackData": "to_requests_menu"}],
            [{"text": "Настройки напоминаний", "callbackData": "settings_reminder_frequency"}]
        ]
        bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))

    
