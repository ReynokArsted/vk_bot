from example.bot_instance import bot
from example.logger import logging
from bot.handler import (
    MessageHandler,
    BotButtonCommandHandler,
    CommandHandler,
    NewChatMembersHandler,
    LeftChatMembersHandler
)
from example.handlers.button_handler import handle_buttons
from example.handlers.message_handler import handle_message
from example.handlers.chat_member_handler import update_members_handler
from example.features.groups import (
    handle_member_added,
    handle_member_removed
)
from example.utils import load_env
from example.features.reminders import start_reminder_loop

load_env()

bot.dispatcher.add_handler(MessageHandler(callback = handle_message))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback = handle_buttons))
bot.dispatcher.add_handler(CommandHandler(callback=update_members_handler))
bot.dispatcher.add_handler(NewChatMembersHandler(callback=handle_member_added))
bot.dispatcher.add_handler(LeftChatMembersHandler(callback=handle_member_removed))

start_reminder_loop(bot)  # Запуск цикла напоминаний

logging.info("Бот запущен и ожидает сообщений...")
bot.start_polling()
bot.idle()
