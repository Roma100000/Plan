from database.db import get_connection


def create_task(user_id: int, title: str, description: str, deadline: str,
                is_urgent: bool, is_important: bool, tags: list[str] = None) -> int:
    """Добавляет новую задачу в базу и возвращает её ID."""
    if tags is None:
        tags = []
    
    # Превращаем список тегов в строку через запятую для хранения в БД
    tags_str = ",".join(tags)
    
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (user_id, title, description, deadline, is_urgent, is_important, tags) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, title, description, deadline, int(is_urgent), int(is_important), tags_str)
    )
    task_id = cursor.lastrowid  # ID, который база присвоила автоматически
    conn.commit()
    conn.close()
    return task_id


def get_user_tasks(user_id: int) -> list[dict]:
    """Возвращает список всех задач пользователя, отсортированных по дате создания (новые сверху)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    
    tasks = []
    for row in rows:
        task = dict(row)
        # Приводим целочисленные поля обратно к bool и список тегов к list
        task["is_urgent"] = bool(task["is_urgent"])
        task["is_important"] = bool(task["is_important"])
        task["is_done"] = bool(task["is_done"])
        task["tags"] = [t.strip() for t in task["tags"].split(",") if t.strip()]
        tasks.append(task)
    
    return tasks


def get_task(task_id: int) -> dict | None:
    """Ищет задачу по ID. Возвращает словарь с данными или None, если задача не найдена."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    
    if row is None:
        return None
    
    task = dict(row)
    task["is_urgent"] = bool(task["is_urgent"])
    task["is_important"] = bool(task["is_important"])
    task["is_done"] = bool(task["is_done"])
    task["tags"] = [t.strip() for t in task["tags"].split(",") if t.strip()]
    return task


def update_task(task_id: int, **kwargs):
    """
    Обновляет одно или несколько полей задачи.
    Принимает только разрешённые поля: title, description, deadline,
    is_urgent, is_important, is_done, tags.
    """
    allowed = ["title", "description", "deadline", "is_urgent", "is_important", "is_done", "tags"]
    updates = {}
    
    for k, v in kwargs.items():
        if k in allowed:
            # Булевы поля храним как INTEGER (0/1)
            if k in ("is_urgent", "is_important", "is_done"):
                updates[k] = int(v)
            # Теги приходят списком, склеиваем обратно в строку
            elif k == "tags" and isinstance(v, list):
                updates[k] = ",".join(v)
            else:
                updates[k] = v
    
    if not updates:
        return  # нечего обновлять
    
    # Динамически строим SET часть запроса: "title = ?, deadline = ?"
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]
    
    conn = get_connection()
    conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_task(task_id: int):
    """Удаляет задачу по ID."""
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def mark_done(task_id: int):
    """Отмечает задачу как выполненную (короткая запись для update_task)."""
    update_task(task_id, is_done=True)


def get_user_tags(user_id: int) -> list[str]:
    """
    Собирает все уникальные теги из задач пользователя.
    Используется для подсказок при добавлении новой задачи.
    """
    conn = get_connection()
    # Берём только непустые строки с тегами
    rows = conn.execute(
        "SELECT tags FROM tasks WHERE user_id = ? AND tags != ''",
        (user_id,)
    ).fetchall()
    conn.close()
    
    tags_set = set()
    for row in rows:
        for tag in row["tags"].split(","):
            tag = tag.strip()
            if tag:
                tags_set.add(tag.lower())  # приводим к нижнему регистру
    
    return sorted(list(tags_set))