from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from services.task_service import update_task, delete_task, mark_done, get_task, get_user_tasks
from keyboards.keyboards import quadrant_emoji, quadrants_keyboard

router = Router()

# Выполнено
@router.callback_query(F.data.startswith("done_"))
async def task_done(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[1])
    mark_done(task_id)
    data = await state.get_data()
    current_quadrant = data.get("current_quadrant", "quad_all")
    await callback.message.edit_text(
        "✅ Задача выполнена.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"back_to_list_{current_quadrant}")],
            [InlineKeyboardButton(text="↩️ Отменить", callback_data=f"undo_{task_id}")]
        ])
    )
    await callback.answer("Статус обновлён")

# Отменить выполнение
@router.callback_query(F.data.startswith("undo_"))
async def undo_done(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[1])
    update_task(task_id, is_done=False)
    await callback.answer("Выполнение отменено")
    await show_task_detail_after_edit(callback, task_id, state)

# 🗑 Удаление
@router.callback_query(F.data.startswith("delete_"))
async def task_delete(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[1])
    delete_task(task_id)
    data = await state.get_data()
    current_quadrant = data.get("current_quadrant", "quad_all")
    await callback.message.edit_text(
        "🗑 Задача удалена.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"back_to_list_{current_quadrant}")]
        ])
    )
    await callback.answer()

# Назад к списку (из деталей или выполнено/удалено)
@router.callback_query(F.data.startswith("back_to_list_"))
async def back_to_list(callback: CallbackQuery, state: FSMContext):
    quadrant = callback.data.replace("back_to_list_", "")
    await state.update_data(current_quadrant=quadrant)
    fsm_data = await state.get_data()
    class_filter = fsm_data.get("current_class")
    from handlers.list_tasks import render_tasks_by_quadrant
    await render_tasks_by_quadrant(callback, state, quadrant, class_filter)
    await callback.answer()

#  Назад к категориям (матрице)
@router.callback_query(F.data == "back_to_quads")
async def back_to_quadrants(callback: CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    current_class = fsm_data.get("current_class")
    user_id = callback.from_user.id
    all_tasks = get_user_tasks(user_id)
    active = [t for t in all_tasks if not t["is_done"]]

    if current_class:
        if current_class == "__notag__":
            active = [t for t in active if not t.get("tags")]
        else:
            active = [t for t in active if current_class in t.get("tags", [])]
        class_text = f"Класс: {current_class}. " if current_class != "__notag__" else "Класс: без класса. "
        text = f"{class_text}Выберите категорию:"
        await callback.message.edit_text(text, reply_markup=quadrants_keyboard(show_class_button=False, show_back_to_class=True))
    else:
        text = "Выберите категорию задач:" if active else "У вас нет активных задач."
        await callback.message.edit_text(text, reply_markup=quadrants_keyboard(show_class_button=True, show_back_to_class=False))
    await callback.answer()

#  Вспомогательная: показать детали после редактирования/отмены
async def show_task_detail_after_edit(callback: CallbackQuery, task_id: int, state: FSMContext):
    task = get_task(task_id)
    if not task:
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