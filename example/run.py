from example.logger import logging
from bot.handler import MessageHandler, BotButtonCommandHandler, CommandHandler, NewChatMembersHandler, LeftChatMembersHandler
from example.handlers.message_handler import handle_message
from example.handlers.button_handler import handle_buttons
from example.features.groups import update_members, handle_member_added, handle_member_removed
from example.bot_instance import bot 

bot.dispatcher.add_handler(MessageHandler(callback = handle_message))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback = handle_buttons))
bot.dispatcher.add_handler(CommandHandler(command = "/update_members", callback = update_members))
bot.dispatcher.add_handler(NewChatMembersHandler(callback=handle_member_added))
bot.dispatcher.add_handler(LeftChatMembersHandler(callback=handle_member_removed))


logging.info("Бот запущен и ожидает сообщений...")
bot.start_polling()
bot.idle()
