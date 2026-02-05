import time
import threading
import json
import os
from datetime import date, datetime
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# 1. Настройки и инициализация
BOT_TOKEN = "API_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = "users.json"
last_sent_date = None 

# 2. Список именинников
BIRTHDAYS = [
    (6, 2, "Иван Иванов"),
    (15, 3, "Анна Петрова"), 
    (1, 7, "Сергей Сергеев"),
]

# 3. Функции работы с базой данных (JSON)
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

# Загружаем пользователей сразу при старте
user_notifications = load_users()

# 4. Вспомогательные функции для интерфейса
def get_keyboard(chat_id):
    # Превращаем chat_id в строку, так как в JSON ключи всегда строки
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

# 5. Обработка сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip().lower() # Здесь всё превращается в мелкий шрифт
    chat_id = str(message.chat.id)
    user_first_name = message.from_user.first_name or "коллега"

    if text == "уведомление":
        user_notifications[chat_id] = True
        save_users(user_notifications)
        msg = (f"Добрый день, {user_first_name}! Уведомления включены.\n"
               "Рассылка работает ежедневно в 08:00.")
        bot.reply_to(message, msg, reply_markup=get_keyboard(chat_id))
    
    # Сравниваем с маленькой буквой!
    elif text == "полный список дней рождений":
        if user_notifications.get(chat_id, False):
            lines = [f"{d:02d}.{m:02d} – {name}" for d, m, name in BIRTHDAYS]
            bot.reply_to(message, "Полный список:\n" + "\n".join(lines), 
                        reply_markup=get_keyboard(chat_id))
    
    # Сравниваем с маленькой буквой!
    elif text == "выкл уведомления":
        user_notifications[chat_id] = False
        save_users(user_notifications)
        bot.reply_to(message, 
                     "Вы выключили уведомления. Напишите «Уведомление» для включения.",
                     reply_markup=ReplyKeyboardRemove())

# 6. Фоновая проверка дат (каждые 30 секунд)
def check_birthdays():
    global last_sent_date
    while True:
        now = datetime.now() # Если на компе ЕКБ, то это время ЕКБ
        today = date.today()
        
        # Проверка времени (здесь твои тестовые 18:19 или боевые 08:00)
        if now.hour == 8 and now.minute == 0 and last_sent_date != str(today):
            print(f"[{now.strftime('%H:%M:%S')}] Старт рассылки...")
            
            for d, m, name in BIRTHDAYS:
                diff = days_until(d, m, today)
                
                text = None
                if diff == 5:
                    text = f"📅 Через 5 дней (то есть {d:02d}.{m:02d}) {name} празднует день рождения. Пора планировать подарок! 🎁"
                elif diff == 1:
                    text = f"⏰ Внимание! Уже ЗАВТРА ({d:02d}.{m:02d}) {name} празднует день рождения. Не забудьте поздравить! 🎉"

                # Если текст сформирован (т.е. выпало 1 или 5 дней), отправляем
                if text:
                    for chat_id, enabled in user_notifications.items():
                        if enabled:
                            try:
                                bot.send_message(chat_id, text)
                                print(f"📤 Отправлено для {chat_id} ({name})")
                            except Exception as e:
                                print(f"❌ Ошибка отправки {chat_id}: {e}")
            
            last_sent_date = str(today)
            
        time.sleep(30)

# 7. Запуск
if __name__ == "__main__":
    # Запускаем поток-чекер
    checker_thread = threading.Thread(target=check_birthdays, daemon=True)
    checker_thread.start()
    
    print(f"✅ Бот запущен! База загружена. Пользователей: {len(user_notifications)}")

    bot.infinity_polling()

