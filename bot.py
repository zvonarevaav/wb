import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import timedelta, datetime
import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')

# Логирование
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Планировщик для напоминаний
scheduler = AsyncIOScheduler()


class ReminderBot:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def set_reminder(self, message: Message, task: str, amount: int, unit: str):
        # Определяем правильный интервал на основе выбранной единицы времени
        if unit == 'min':
            delta = timedelta(minutes=amount)
        elif unit == 'h':
            delta = timedelta(hours=amount)
        elif unit == 'd':
            delta = timedelta(days=amount)
        elif unit == 'w':
            delta = timedelta(weeks=amount)
        elif unit == 'mo':
            delta = timedelta(days=amount * 30)  # Условный месяц = 30 дней
        else:
            delta = timedelta(minutes=amount)  # По умолчанию используем минуты

        reminder_time = datetime.now() + delta
        logging.info(f"Устанавливаем напоминание на: {reminder_time}")

        await message.answer(f"Задача принята: '{task}'. Напомню через {amount} {unit}.")

        try:
            scheduler.add_job(self.send_reminder_async, DateTrigger(run_date=reminder_time),
                              args=(message.chat.id, task), id=f"reminder_{message.chat.id}_{task}")
            logging.info(f"Напоминание установлено на задачу: {task}, время: {reminder_time}")
        except Exception as e:
            logging.error(f"Ошибка при добавлении задачи в планировщик: {e}")

    async def send_reminder_async(self, chat_id: int, task: str):
        try:
            logging.info(f"Отправка напоминания. Задача: {task}, чат: {chat_id}")
            await bot.send_message(chat_id, f"Напоминание о задаче: '{task}'")
        except Exception as e:
            logging.error(f"Ошибка при отправке напоминания: {e}")


# Инициализация бота
reminder_bot = ReminderBot(bot)


# Приветственное сообщение с инструкцией
@dp.message(Command("start"))
async def send_welcome(message: Message):
    welcome_text = (
        "Привет! Я бот-напоминатель. 📝\n\n"
        "Как я работаю:\n"
        "1. Напишите команду в формате: @bot_name ctrl N{unit}\n"
        "   Где N — это количество, а {unit} — единица времени:\n"
        "   - min (минуты)\n"
        "   - h (часы)\n"
        "   - d (дни)\n"
        "   - w (недели)\n"
        "   - mo (месяцы)\n\n"
        "2. Ответьте на сообщение с задачей, к которому нужно установить напоминание.\n"
        "Пример команды: @bot_name ctrl 5d — напомнит через 5 дней.\n"
    )
    await message.answer(welcome_text)


# Обработка команды вида "@bot_name ctrl 5min" или "@bot_name ctrl 5d"
@dp.message(lambda message: re.match(r"@bot_name ctrl (\d+)(min|h|d|w|mo)", message.text))
async def handle_ctrl_command(message: Message):
    match = re.match(r"@bot_name ctrl (\d+)(min|h|d|w|mo)", message.text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        # Проверка, есть ли последнее сообщение как задача (через ответ)
        if message.reply_to_message:
            task = message.reply_to_message.text
        else:
            await message.answer("Ошибка: Используйте команду как ответ на сообщение с задачей.")
            return

        # Устанавливаем напоминание
        await reminder_bot.set_reminder(message, task, amount, unit)
    else:
        await message.answer(
            "Неверный формат команды. Используйте: @bot_name ctrl 5min, @bot_name ctrl 5h, @bot_name ctrl 5d (например)")


async def main():
    scheduler.start()  # Запускаем планировщик
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
