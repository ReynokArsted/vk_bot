from bot.bot import Bot
from bot.handler import MessageHandler

TOKEN = "001.0552989608.2853020515:1011883647"  # your token here

bot = Bot(token=TOKEN)


def message_cb(bot, event):
    bot.send_text(chat_id=event.from_chat, text=event.text)


bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
bot.start_polling()
bot.idle()
