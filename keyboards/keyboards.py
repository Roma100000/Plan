from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню (reply)
def main_keyboard():
    buttons = [
        [KeyboardButton(text="📋 Мои задачи")],
        [KeyboardButton(text="➕ Новая задача")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Эмодзи квадрантов
def quadrant_emoji(urgent: bool, important: bool) -> str:
    if urgent and important:
        return "🔴"
    elif urgent and not important:
        return "🟡"
    elif not urgent and important:
        return "🔵"
    else:
        return "⚪"

# Клавиатура выбора квадрантов (инлайн)
def quadrants_keyboard(show_class_button=True, show_back_to_class=False):
    buttons = [
        [InlineKeyboardButton(text="🔴 Срочно и важно", callback_data="quad_urgent_important")],
        [InlineKeyboardButton(text="🟡 Срочно, не важно", callback_data="quad_urgent_not_important")],
        [InlineKeyboardButton(text="🔵 Не срочно, важно", callback_data="quad_not_urgent_important")],
        [InlineKeyboardButton(text="⚪ Не срочно и не важно", callback_data="quad_not_urgent_not_important")],
        [InlineKeyboardButton(text="📊 Все активные", callback_data="quad_all")],
    ]
    if show_class_button:
        buttons.append([InlineKeyboardButton(text="📚 По классам задач", callback_data="choose_class")])
    if show_back_to_class:
        buttons.append([InlineKeyboardButton(text="🔙 Назад к классам", callback_data="choose_class")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура выбора классов
def class_selection_keyboard(user_tags: list[str]):
    buttons = []
    for tag in user_tags:
        buttons.append([InlineKeyboardButton(text=tag.capitalize(), callback_data=f"class_tag_{tag}")])
    buttons.append([InlineKeyboardButton(text="Без класса", callback_data="class_notag")])
    buttons.append([InlineKeyboardButton(text="Все задачи", callback_data="class_all")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="back_to_quads")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)