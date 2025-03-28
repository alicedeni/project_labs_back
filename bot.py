import logging
import asyncio
import csv
import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command

TOKEN = "7752421682:AAFoeD4HCQFX0MT54XWZFHeW5TTKrORkFiQ"
CSV_FILE = "users.csv"

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "ФИО", "Группа", "Почта"])

class Registration(StatesGroup):
    full_name = State()
    mail = State()
    group = State()

def is_registered(user_id: int) -> bool:
    with open(CSV_FILE, mode="r", encoding="utf-8") as file:
        return any(str(user_id) == row[0] for row in csv.reader(file) if row)

def is_valid_full_name(name: str) -> bool:
    return bool(re.match(r"^[А-ЯЁа-яёA-Za-z ]+$", name.strip()))

def is_valid_mail(mail: str) -> bool:
    return re.match(r"^[^@]+@[^@]+\.[^@]+$", mail.strip()) is not None

@dp.message(Command(commands=["start"]))
async def start_command(message: types.Message, state: FSMContext):
    if is_registered(message.from_user.id):
        await message.answer("Вы уже зарегистрированы!")
        return
        
    await message.answer("Привет! Добро пожаловать в бот для проверки лабораторных работ.")
    await message.answer("Введите ваше ФИО (например: Иванов Иван Иванович):")
    await state.set_state(Registration.full_name)

@dp.message(Registration.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    if not is_valid_full_name(message.text):
        await message.answer("Ошибка! ФИО должно содержать только буквы и пробелы!")
        return
        
    await state.update_data(full_name=message.text.strip())
    await message.answer("Теперь введите вашу почту (например: example@edu.hse.ru):")
    await state.set_state(Registration.mail)

@dp.message(Registration.mail)
async def process_mail(message: types.Message, state: FSMContext):
    if not is_valid_mail(message.text):
        await message.answer("Ошибка! Некорректный формат почты!")
        return
        
    await state.update_data(mail=message.text.strip())
    await message.answer("Теперь введите вашу группу (например: БИТ231):")
    await state.set_state(Registration.group)

@dp.message(Registration.group)
async def process_group(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
        csv.writer(file).writerow([user_id, user_data["full_name"], message.text.strip(), user_data["mail"]])
    
    await message.answer(
        f"✅ Регистрация завершена!\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Группа: {message.text.strip()}\n"
        f"Почта: {user_data['mail']}"
    )
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
