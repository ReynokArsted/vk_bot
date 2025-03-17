import json
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler

TOKEN = "001.0552989608.2853020515:1011883647"  # your token here

bot = Bot(token=TOKEN)

def buttons_answer_cb(bot, event):
    if event.data['callbackData'] == "call_back_id_1":
        bot.send_text(
        chat_id=event.from_chat,
        text=
        "Запрос на апрув может состоять из текста, ссылок на внешние ресурсы \
        и прикреплённых картинок. Ещё можно задать время, в течение которого \
        будут ожидаться апрувы, а после ты получишь напоминание от меня о запросе\
        Начнём с описания предложения. Давай, опишем его:",
        inline_keyboard_markup="{}".format(json.dumps([
            [{"text": "Назад", "callbackData": "back_to_main_menu"}]
            ]))
    )

    elif event.data['callbackData'] == "call_back_id_2":
        bot.send_text(
            chat_id=event.from_chat,
            text="Список предложений",
            inline_keyboard_markup="{}".format(json.dumps([
                [{"text": "Назад", "callbackData": "back_to_main_menu"}],
                [{"text": "Предложение 1", "callbackData": ""}],
                [{"text": "Предложение 2", "callbackData": ""}],
                [{"text": "Предложение 3", "callbackData": ""}]
            ]))
        )

    elif event.data['callbackData'] == "back_to_main_menu":
        show_main_menu(bot, event.from_chat)

def show_main_menu(bot, chat_id):
    bot.send_text(
        chat_id=chat_id,
        text="Привет! У тебя появилась идея? Давай, покажем её",
        inline_keyboard_markup=json.dumps([
            [{"text": "Создать предложение по задаче", "callbackData": "call_back_id_1"}],
            [{"text": "Посмотреть статус твоих предложений для задач", "callbackData": "call_back_id_2"}]
        ])
    )

def message_cb(bot, event):
    show_main_menu(bot, event.from_chat)

bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))

bot.start_polling()
bot.idle()