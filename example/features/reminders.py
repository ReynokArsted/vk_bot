import time
from threading import Thread
from example.storage.requests import get_all_active_requests
from example.storage.group_members import get_group_members
from example.storage.votes import get_votes
from example.utils import create_inline_keyboard, get_user_reminder_frequency

def start_reminder_loop(bot):
    def loop():
        while True:
            check_pending_votes(bot)
            time.sleep(60)  # Каждый 1 минуту проверяем

    Thread(target=loop, daemon=True).start()


def check_pending_votes(bot):
    requests = get_all_active_requests()  # Получаем все запросы со статусом "in_progress"
    print(f"\n[ReminderLoop] Проверка запросов: найдено {len(requests)} активных запросов\n")
    
    for req in requests:
        group_id = req.group_id
        members = get_group_members(group_id)
        votes = get_votes(req.id)  # Получаем все голоса для текущего запроса
        
        # Получаем список пользователей, которые проголосовали
        voted_user_ids = {vote.user_id for vote in votes}

        # Исключаем создателя запроса и тех, кто уже проголосовал
        non_voters = [user_id for user_id in members if user_id not in voted_user_ids and user_id != req.requester_id]

        for user_id in non_voters:
            try:
                # Получаем частоту напоминаний для этого пользователя
                reminder_frequency = get_user_reminder_frequency(user_id)

                # Отправляем напоминание
                bot.send_text(
                    chat_id=user_id,
                    text=f"🔔 Напоминание: ты ещё не проголосовал по запросу \"{req.name or 'Без названия'}\" в группе \"{req.group_name or group_id}\"",
                    inline_keyboard_markup=create_inline_keyboard([
                        [
                            {"text": "👍 Одобрить", "callbackData": f"approve_{req.id}"},
                            {"text": "👎 Отклонить", "callbackData": f"reject_{req.id}"}
                        ]
                    ])
                )

                # Засыпаем на время, равное частоте напоминаний пользователя (в секундах)
                time.sleep(reminder_frequency * 60)  # Частота напоминаний в минутах

            except Exception as e:
                print(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
