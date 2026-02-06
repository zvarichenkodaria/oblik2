import time
import threading
import json
import os
from datetime import date, datetime
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telebot import apihelper
import pytz

# 1. Настройки и инициализация
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = "users.json"
last_sent_date = None 

# Увеличиваем глобальный тайм-аут для запросов
apihelper.READ_TIMEOUT = 60 

# --- (Список BIRTHDAYS и функции загрузки/сохранения JSON без изменений) ---
BIRTHDAYS = [
    (7, 1, "Владимир Бурмистров"),
    (26, 1, "Василий Попов"), 
    (29, 1, "Татьяна Шабалина"),
    (1, 2, "Алеся Сантеева"),
    (16, 2, "Евгений Анатольевич Крылатков"), 
    (26, 4, "Алена Воронкова"),
    (6, 8, "Дарья Звариченко"), 
    (8, 9, "Игорь Черепанов"),
    (25, 9, "Татьяна Коваленко"), 
    (29, 9, "Алексей Варзегов"),
    (11, 10, "Петр Захаров"), 
    (21, 10, "Регина Бурмистрова"),
    (2, 11, "Светлана Шонорова"), 
]

def load_users():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

user_notifications = load_users()

def get_keyboard(chat_id):
    cid = str(chat_id)
    if user_notifications.get(cid, False):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Полный список дней рождений"))
        markup.add(KeyboardButton("Выкл уведомления"))
        return markup
    return ReplyKeyboardRemove()

def days_until(day: int, month: int, today: date) -> int:
    year = today.year
    try:
        target = date(year, month, day)
    except ValueError:
        target = date(year, month, day - 1)
    if target < today:
        target = target.replace(year=year + 1)
    return (target - today).days

# 5. Обработка сообщений (Добавлена обработка ошибок внутри)
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        text = message.text.strip().lower()
        chat_id = str(message.chat.id)
        user_first_name = message.from_user.first_name or "коллега"

        if text == "уведомление":
            user_notifications[chat_id] = True
            save_users(user_notifications)
            msg = (f"Добрый день, {user_first_name}! Уведомления включены.\n"
                   "Напоминание будет приходить за 5 дней и за 1 день до праздника в 08:00 по Екатеринбургу.")
            bot.reply_to(message, msg, reply_markup=get_keyboard(chat_id))
        
        elif text == "полный список дней рождений":
            if user_notifications.get(chat_id, False):
                lines = [f"{d:02d}.{m:02d} – {name}" for d, m, name in BIRTHDAYS]
                bot.reply_to(message, "Полный список:\n" + "\n".join(lines), 
                            reply_markup=get_keyboard(chat_id))
        
        elif text == "выкл уведомления":
            user_notifications[chat_id] = False
            save_users(user_notifications)
            bot.reply_to(message, 
                         "Вы выключили уведомления. Напишите «Уведомление» для включения.",
                         reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        print(f"Ошибка в обработчике сообщений: {e}")

# 6. Фоновая проверка дат (Добавлен try-except для стабильности)
def check_birthdays():
    global last_sent_date
    # Явно задаем московский часовой пояс
    moscow_tz = pytz.timezone('Europe/Moscow')
    
    while True:
        try:
            # Получаем время сервера и переводим его в МСК
            now_moscow = datetime.now(moscow_tz)
            today = now_moscow.date()
            
            # Для отладки: выводит в логи хостинга точное время, которое видит бот
            # print(f"DEBUG: Текущее время МСК: {now_moscow.strftime('%H:%M:%S')}")

            # Проверяем часы и минуты по Москве
            if now_moscow.hour == 6 and now_moscow.minute == 0 and last_sent_date != str(today):
                print(f"[{now_moscow.strftime('%H:%M:%S')}] Запуск рассылки...")
                
                # Копия списка пользователей для безопасного обхода
                current_users = list(user_notifications.items())
                
                for d, m, name in BIRTHDAYS:
                    diff = days_until(d, m, today)
                    text = None
                    if diff == 5:
                        text = f"📅 Через 5 дней ({d:02d}.{m:02d}) {name} празднует день рождения. Пора планировать подарок! 🎁"
                    elif diff == 1:
                        text = f"⏰ Внимание! ЗАВТРА ({d:02d}.{m:02d}) {name} празднует день рождения. Не забудьте поздравить! 🎉"

                    if text:
                        for chat_id, enabled in current_users:
                            if enabled:
                                try:
                                    bot.send_message(chat_id, text)
                                    time.sleep(0.1)
                                except Exception as send_error:
                                    print(f"Ошибка отправки для {chat_id}: {send_error}")
                
                last_sent_date = str(today)
                
        except Exception as e:
            print(f"Ошибка в цикле проверки: {e}")
            
        time.sleep(30) # Проверка каждые 30 секунд

# 7. Запуск с защитой от вылета
if __name__ == "__main__":
    checker_thread = threading.Thread(target=check_birthdays, daemon=True)
    checker_thread.start()
    
    print(f"✅ Бот запущен! Пользователей в базе: {len(user_notifications)}")

    # Параметры для предотвращения ReadTimeout
    bot.infinity_polling(
        timeout=90, 
        long_polling_timeout=5,
        logger_level=None # Можно поставить logging.DEBUG для отладки
    )

