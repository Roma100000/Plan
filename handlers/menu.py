from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards.keyboards import main_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я интеллектуальный планировщик задач.\nИспользуй кнопки меню.",
        reply_markup=main_keyboard()
    )

@router.message(F.text == "⚙️ Помощь")
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Доступные команды:\n"
        "📋 Мои задачи – просмотр задач по матрице\n"
        "➕ Новая задача – добавить задачу\n"
        "📊 Статистика – аналитика продуктивности\n"
        "⚙️ Помощь – эта справка",
        reply_markup=main_keyboard()
    )