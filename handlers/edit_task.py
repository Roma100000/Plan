from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.task_service import get_task, update_task
from services.validators import is_valid_deadline
from keyboards.keyboards import main_keyboard

router = Router()

# Состояние: ожидание нового текстового значения (для полей Название, Описание, Дедлайн)
class EditTask(StatesGroup):
    new_value = State()


# Начало редактирования — показываем меню выбора поля
@router.callback_query(F.data.startswith("edit_"))
async def start_edit_task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[1])
    task = get_task(task_id)
    if not task:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    await state.update_data(edit_task_id=task_id)

    edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data="field_title")],
        [InlineKeyboardButton(text="Описание", callback_data="field_desc")],
        [InlineKeyboardButton(text="Дедлайн", callback_data="field_deadline")],
        [InlineKeyboardButton(text="Срочность", callback_data="field_urgent")],
        [InlineKeyboardButton(text="Важность", callback_data="field_important")],
        [InlineKeyboardButton(text="🔙 Назад к задаче", callback_data=f"task_{task_id}")]
    ])
    await callback.message.edit_text("Выберите поле для редактирования:", reply_markup=edit_kb)
    await callback.answer()


# После выбора поля: либо запрашиваем новое значение, либо показываем Да/Нет
@router.callback_query(F.data.startswith("field_"))
async def edit_field_selected(callback: CallbackQuery, state: FSMContext):
    field_map = {
        "field_title": ("title", "название"),
        "field_desc": ("description", "описание"),
        "field_deadline": ("deadline", "дедлайн"),
        "field_urgent": ("is_urgent", "срочность"),
        "field_important": ("is_important", "важность")
    }
    if callback.data not in field_map:
        await callback.answer("Неизвестное поле", show_alert=True)
        return

    field_key, field_label = field_map[callback.data]
    await state.update_data(edit_field=field_key)

    # Для булевых полей показываем инлайн-кнопки Да/Нет
    if field_key in ("is_urgent", "is_important"):
        data = await state.get_data()
        task = get_task(data["edit_task_id"])
        current_val = "да" if task[field_key] else "нет"
        yes_no_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="bool_yes"),
             InlineKeyboardButton(text="Нет", callback_data="bool_no")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_{data['edit_task_id']}")]
        ])
        await callback.message.edit_text(
            f"Новое значение «{field_label}» (сейчас: {current_val})?",
            reply_markup=yes_no_kb
        )
    else:
        # Для текстовых полей — просим ввести новое значение
        prompts = {
            "title": "Введите новое название задачи:",
            "description": "Введите новое описание задачи:",
            "deadline": "Введите новый дедлайн в формате ДД.ММ.ГГГГ (или '-' для удаления):"
        }
        prompt = prompts.get(field_key, f"Введите новое значение для «{field_label}»:")
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_{ (await state.get_data())['edit_task_id'] }")]
        ])
        await callback.message.edit_text(prompt, reply_markup=back_kb)
        await state.set_state(EditTask.new_value)  # переходим в состояние ожидания ввода

    await callback.answer()


# Обработка ответа Да/Нет для булевых полей
@router.callback_query(F.data.startswith("bool_"))
async def set_bool_value(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data["edit_task_id"]
    field = data["edit_field"]
    value = (callback.data == "bool_yes")
    update_task(task_id, **{field: value})
    await callback.answer("Значение обновлено")

    # Возвращаемся к просмотру задачи (функция из task_actions)
    from handlers.task_actions import show_task_detail_after_edit
    await show_task_detail_after_edit(callback, task_id, state)


# Обработка ввода нового значения для текстовых полей
@router.message(EditTask.new_value)
async def edit_text_new_value(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["edit_task_id"]
    field = data["edit_field"]
    new_value = message.text.strip()

    # Для дедлайна проверяем формат (или разрешаем '-' как пустое значение)
    if field == "deadline":
        if new_value == "-":
            new_value = ""
        elif not is_valid_deadline(new_value):
            await message.answer("❌ Неверный формат или дата уже прошла. Введите дату ДД.ММ.ГГГГ (или '-' пропустить):")
            return  # ждём корректный ввод

    update_task(task_id, **{field: new_value})
    await message.answer("✅ Изменение сохранено.", reply_markup=main_keyboard())
    await state.clear()

    # Показываем обновлённую задачу
    task = get_task(task_id)
    if task:
        from keyboards.keyboards import quadrant_emoji
        detail = (
            f"📌 *{task['title']}*\n"
            f"📝 {task['description'] or 'нет описания'}\n"
            f"⏰ Дедлайн: {task['deadline'] or 'нет'}\n"
            f"{quadrant_emoji(task['is_urgent'], task['is_important'])} "
            f"{'Срочно' if task['is_urgent'] else 'Не срочно'}, "
            f"{'Важно' if task['is_important'] else 'Не важно'}\n"
        )
        if task.get('tags'):
            detail += f"📚 Класс: {', '.join(task['tags'])}\n"
        detail += f"Статус: {'✅ Выполнено' if task['is_done'] else '⬜ В процессе'}"
        await message.answer(detail, parse_mode="Markdown")


# Кнопка "Отмена" в редактировании
@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Редактирование отменено.")
    from handlers.task_actions import back_to_quadrants
    await back_to_quadrants(callback, state)