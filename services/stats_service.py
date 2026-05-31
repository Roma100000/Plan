from datetime import datetime, timedelta
from collections import Counter
from database.db import get_connection


def get_completed_stats(user_id: int, days: int = 7) -> dict:
    """
    Собирает статистику выполненных задач за последние N дней.
    Возвращает словарь: {дата (str): количество}
    """
    conn = get_connection()
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    rows = conn.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM tasks
        WHERE user_id = ? AND is_done = 1 AND DATE(created_at) >= ?
        GROUP BY DATE(created_at)
        ORDER BY date
    """, (user_id, since_date)).fetchall()
    conn.close()
    
    stats = {}
    for row in rows:
        stats[row["date"]] = row["count"]
    
    return stats


def get_completed_by_class(user_id: int) -> dict:
    """
    Собирает статистику выполненных задач по классам (тегам).
    Возвращает словарь: {тег: количество}
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT tags FROM tasks
        WHERE user_id = ? AND is_done = 1 AND tags != ''
    """, (user_id,)).fetchall()
    conn.close()
    
    counter = Counter()
    for row in rows:
        for tag in row["tags"].split(","):
            tag = tag.strip().lower()
            if tag:
                counter[tag] += 1
    
    return dict(counter.most_common())  # по убыванию


def get_total_stats(user_id: int) -> dict:
    """Общая статистика: всего задач, выполнено, просрочено."""
    conn = get_connection()
    
    total = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    
    done = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_done = 1", (user_id,)
    ).fetchone()[0]
    
    # Просроченные: не выполнены, есть дедлайн, и дата прошла
    today = datetime.now().strftime("%d.%m.%Y")
    overdue = conn.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE user_id = ? AND is_done = 0 AND deadline != '' AND deadline < ?
    """, (user_id, today)).fetchone()[0]
    
    conn.close()
    
    return {
        "total": total,
        "done": done,
        "active": total - done,
        "overdue": overdue
    }