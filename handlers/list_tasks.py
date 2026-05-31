from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from services.task_service import get_user_tasks, get_task, get_user_tags
from keyboards.keyboards import quadrants_keyboard, class_selection_keyboard, quadrant_emoji

router = Router()

# Вспомогательная функция рендеринга списка задач по квадранту/классу
async def render_tasks_by_quadrant(
    target: Message | CallbackQuery,
    state: FSMContext,
    quadrant: str,
    class_filter: str | None = None
):
    user_id = target.from_user.id
    all_tasks = get_user_tasks(user_id)
    active = [t for t in all_tasks if not t["is_done"]]

    # Применяем класс
    if class_filter:
        if class_filter == "__notag__":
            active = [t for t in active if not t.get("tags")]
        else:
            active = [t for t in active if class_filter in t.get("tags", [])]

    # Применяем квадрант
    mapping = {
        "quad_urgent_important": lambda t: t["is_urgent"] and t["is_important"],
        "quad_urgent_not_important": lambda t: t["is_urgent"] and not t["is_important"],
        "quad_not_urgent_important": lambda t: not t["is_urgent"] and t["is_important"],
        "quad_not_urgent_not_important": lambda t: not t["is_urgent"] and not t["is_important"],
        "quad_all": lambda t: True
    }
    filt_func = mapping.get(quadrant)
    if filt_func:
        filtered = [t for t in active if filt_func(t)]
    else:
        filtered = []

    if not filtered:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="back_to_quads")]
        ])
        text = "В этой категории нет активных задач."
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=kb)
        else:
            await target.answer(text, reply_markup=kb)
        await target.answer() if isinstance(target, CallbackQuery) else None
        return

    filtered.sort(key=lambda t: t["id"], reverse=True)

    # Сохраняем текущий квадрант в состоянии
    await state.update_data(current_quadrant=quadrant)

    kb_buttons = []
    for t in filtered:
        btn_text = t['title'][:30]
        if t['deadline']:
            btn_text += f" ({t['deadline']})"
        kb_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"task_{t['id']}")])
    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="back_to_quads")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text("Выберите задачу:", reply_markup=keyboard)
    else:
        await target.answer("Выберите задачу:", reply_markup=keyboard)
    if isinstance(target, CallbackQuery):
        await target.answer()

# Вход в просмотр задач
@router.message(F.text == "📋 Мои задачи")
@router.message(Command("list"))
async def show_quadrants_inline(message: Message, state: FSMContext):
    await state.update_data(current_class=None)
    tasks = get_user_tasks(message.from_user.id)
    active = [t for t in tasks if not t["is_done"]]
    text = "Выберите категорию задач:" if active else "У вас нет активных задач."
    await message.answer(text, reply_markup=quadrants_keyboard())

# Выбор класса задач
@router.callback_query(F.data == "choose_class")
async def choose_class(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_tags = get_user_tags(user_id)
    if not user_tags:
        await callback.answer("Нет доступных классов.", show_alert=True)
        return
    await callback.message.edit_text("Выберите класс задач:", reply_markup=class_selection_keyboard(user_tags))

@router.callback_query(F.data.startswith("class_"))
async def class_chosen(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "class_all":
        await state.update_data(current_class=None)
        await callback.message.edit_text("Все задачи (без фильтра класса). Выберите категорию:",
                                         reply_markup=quadrants_keyboard(show_class_button=True, show_back_to_class=False))
    elif data == "class_notag":
        await state.update_data(current_class="__notag__")
        await callback.message.edit_text("Класс: без класса. Выберите категорию:",
                                         reply_markup=quadrants_keyboard(show_class_button=False, show_back_to_class=True))
    else:
        tag = data[len("class_tag_"):]
        await state.update_data(current_class=tag)
        await callback.message.edit_text(f"Класс: {tag}. Выберите категорию:",
                                         reply_markup=quadrants_keyboard(show_class_button=False, show_back_to_class=True))
    await callback.answer()

# Обработчик выбора квадранта
@router.callback_query(F.data.startswith("quad_"))
async def quadrant_chosen(callback: CallbackQuery, state: FSMContext):
    quadrant = callback.data  # чистое quad_... при прямом вызове
    fsm_data = await state.get_data()
    class_filter = fsm_data.get("current_class")
    await render_tasks_by_quadrant(callback, state, quadrant, class_filter)
    await callback.answer()

# Детали задачи
@router.callback_query(F.data.startswith("task_"))
async def show_task_detail(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[1])
    task = get_task(task_id)
    if not task:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    data = await state.get_data()
    current_quadrant = data.get("current_quadrant", "quad_all")

    detail_text = (
        f"📌 *{task['title']}*\n"
        f"📝 {task['description'] or 'нет описания'}\n"
        f"⏰ Дедлайн: {task['deadline'] or 'нет'}\n"
        f"{quadrant_emoji(task['is_urgent'], task['is_important'])} "
        f"{'Срочно' if task['is_urgent'] else 'Не срочно'}, "
        f"{'Важно' if task['is_important'] else 'Не важно'}\n"
    )
    if task.get('tags'):
        detail_text += f"📚 Класс: {', '.join(task['tags'])}\n"
    detail_text += f"Статус: {'✅ Выполнено' if task['is_done'] else '⬜ В процессе'}"

    action_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{task_id}"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_{task_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{task_id}")
        ],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"back_to_list_{current_quadrant}")]
    ])

    await callback.message.edit_text(detail_text, reply_markup=action_kb, parse_mode="Markdown")
    await state.update_data(current_task_id=task_id)
    await callback.answer()