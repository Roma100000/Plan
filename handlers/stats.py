import io
import numpy as np
import matplotlib.pyplot as plt
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from services.stats_service import get_completed_by_class, get_total_stats
from keyboards.keyboards import main_keyboard

router = Router()
plt.rcParams['font.family'] = 'Arial'


@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def show_stats(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    total = get_total_stats(user_id)
    
    # ---------- Текстовая сводка ----------
    text = (
        "📊 *Статистика продуктивности*\n\n"
        f"📌 Всего задач: {total['total']}\n"
        f"✅ Выполнено: {total['done']}\n"
        f"🔄 В процессе: {total['active']}\n"
        f"⚠️ Просрочено: {total['overdue']}\n"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard())
    
    if total['total'] == 0:
        await message.answer("У вас пока нет задач для статистики.")
        return
    
    # ========== График 1: Всего / Выполнено / Просрочено ==========
    categories = ['Всего задач', 'Выполнено', 'Просрочено']
    values = [total['total'], total['done'], total['overdue']]
    colors = ['#2196F3', '#4CAF50', '#F44336']
    
    fig1, ax1 = plt.subplots(figsize=(7, 4))
    bars = ax1.bar(categories, values, color=colors, edgecolor='white', width=0.5)
    
    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 str(val), ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    ax1.set_title("Статус задач", fontsize=14, fontweight='bold', pad=15)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.set_ylim(0, max(values) + 2 if max(values) > 0 else 5)
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.tight_layout()
    
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png', dpi=100, bbox_inches='tight')
    buf1.seek(0)
    plt.close(fig1)
    
    await message.answer_photo(
        BufferedInputFile(buf1.read(), filename="status.png"),
        caption="📊 Статус задач"
    )
    
    # ========== График 2: Прогресс по классам ==========
    class_data = get_completed_by_class(user_id)  # {класс: выполнено}
    
    if not class_data:
        await message.answer("Нет задач с классами для статистики.")
        return
    
    # Для каждого класса считаем общее количество и процент выполнения
    from database.db import get_connection
    conn = get_connection()
    
    classes = []
    done_counts = []
    total_counts = []
    percentages = []
    
    for class_name in class_data.keys():
        # Считаем общее количество задач этого класса
        total_for_class = conn.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE user_id = ? AND tags LIKE ?
        """, (user_id, f"%{class_name}%")).fetchone()[0]
        
        done_for_class = class_data[class_name]
        
        classes.append(class_name.capitalize())
        done_counts.append(done_for_class)
        total_counts.append(total_for_class)
        percentages.append(round(done_for_class / total_for_class * 100) if total_for_class > 0 else 0)
    
    # Считаем задачи без класса
    no_class_total = conn.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE user_id = ? AND (tags = '' OR tags IS NULL)
    """, (user_id,)).fetchone()[0]
    
    no_class_done = conn.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE user_id = ? AND is_done = 1 AND (tags = '' OR tags IS NULL)
    """, (user_id,)).fetchone()[0]
    
    conn.close()
    
    if no_class_total > 0:
        classes.append("Без класса")
        done_counts.append(no_class_done)
        total_counts.append(no_class_total)
        percentages.append(round(no_class_done / no_class_total * 100))
    
    # Строим сгруппированную диаграмму
    x = np.arange(len(classes))
    width = 0.35
    
    fig2, ax2 = plt.subplots(figsize=(max(8, len(classes) * 1.5), 5))
    
    bars_done = ax2.bar(x - width/2, done_counts, width, label='Выполнено', color='#4CAF50', edgecolor='white')
    bars_total = ax2.bar(x + width/2, total_counts, width, label='Всего', color='#2196F3', edgecolor='white')
    
    # Подписи — процент выполнения над столбцами "Всего"
    for i, (bar, pct) in enumerate(zip(bars_total, percentages)):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                 f'{pct}%', ha='center', va='bottom', fontsize=11, fontweight='bold', color='#333')
    
    ax2.set_title("Прогресс выполнения по классам", fontsize=14, fontweight='bold', pad=15)
    ax2.set_xticks(x)
    ax2.set_xticklabels(classes, fontsize=11)
    ax2.legend(fontsize=11)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.set_ylim(0, max(total_counts) + 2 if total_counts else 5)
    ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.tight_layout()
    
    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png', dpi=100, bbox_inches='tight')
    buf2.seek(0)
    plt.close(fig2)
    
    await message.answer_photo(
        BufferedInputFile(buf2.read(), filename="classes.png"),
        caption="📚 Прогресс выполнения по классам (процент выполнения над столбцами)"
    )