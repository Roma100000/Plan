from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from services.task_service import create_task, get_user_tags
from services.validators import is_valid_deadline
from keyboards.keyboards import main_keyboard

router = Router()

# Группа состояний для пошагового диалога добавления задачи
class AddTask(StatesGroup):
    title = State()       # ожидание названия
    description = State() # ожидание описания
    deadline = State()    # ожидание дедлайна
    urgent = State()      # срочно? (Да/Нет)
    important = State()   # важно? (Да/Нет)
    tags = State()        # выбор класса (тега)


# Вход в процесс: кнопка «➕ Новая задача» или команда /add
@router.message(F.text == "➕ Новая задача")
@router.message(Command("add"))
async def start_add_task(message: Message, state: FSMContext):
    await state.clear()  # сбрасываем предыдущие незавершённые попытки
    await message.answer("Введите название задачи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddTask.title)


@router.message(AddTask.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание (или отправьте '-', если нет):")
    await state.set_state(AddTask.description)


@router.message(AddTask.description)
async def process_description(message: Message, state: FSMContext):
    desc = message.text if message.text != '-' else ""
    await state.update_data(description=desc)
    await message.answer("Введите дедлайн в формате ДД.ММ.ГГГГ (или '-', если без дедлайна):")
    await state.set_state(AddTask.deadline)


@router.message(AddTask.deadline)
async def process_deadline(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == '-':
        deadline = ""
    else:
        # Проверяем, что дата корректная и не в прошлом
        if not is_valid_deadline(text):
            await message.answer("❌ Неверный формат или дата уже прошла. Введите дату в формате ДД.ММ.ГГГГ (или '-' пропустить):")
            return  # остаёмся в том же состоянии, ждём правильный ввод
        deadline = text

    await state.update_data(deadline=deadline)

    # Клавиатура с Да/Нет для срочности
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Задача срочная?", reply_markup=kb)
    await state.set_state(AddTask.urgent)


@router.message(AddTask.urgent, F.text.in_(["Да", "Нет"]))
async def process_urgent(message: Message, state: FSMContext):
    await state.update_data(is_urgent=(message.text == "Да"))  # True/False
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Задача важная?", reply_markup=kb)
    await state.set_state(AddTask.important)


@router.message(AddTask.important, F.text.in_(["Да", "Нет"]))
async def process_important(message: Message, state: FSMContext):
    await state.update_data(is_important=(message.text == "Да"))

    # Предлагаем выбор из уже существующих классов пользователя
    user_id = message.from_user.id
    existing_tags = get_user_tags(user_id)
    kb_buttons = [[KeyboardButton(text=tag)] for tag in existing_tags]
    kb_buttons.append([KeyboardButton(text="Без категории")])
    keyboard = ReplyKeyboardMarkup(keyboard=kb_buttons, resize_keyboard=True, one_time_keyboard=True)

    await message.answer(
        "Выберите категорию (класс) или введите свой (можно несколько через запятую):",
        reply_markup=keyboard
    )
    await state.set_state(AddTask.tags)


@router.message(AddTask.tags)
async def process_tags(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text == "без категории":
        tags = []
    else:
        # Разбиваем по запятой, убираем пробелы и пустые значения
        tags = [tag.strip() for tag in text.split(",") if tag.strip()]

    # Собираем все сохранённые данные и создаём задачу в БД
    data = await state.get_data()
    create_task(
        message.from_user.id,
        data["title"],
        data["description"],
        data["deadline"],
        data["is_urgent"],
        data["is_important"],
        tags
    )

    await message.answer(f"✅ Задача «{data['title']}» добавлена.", reply_markup=main_keyboard())
    await state.clear()  # сбрасываем состояния — диалог завершён