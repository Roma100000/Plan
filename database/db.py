import sqlite3

DB_PATH = "bot.db"

def get_connection():
    """Создаёт подключение к SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # чтобы можно было обращаться к полям по имени
    conn.execute("PRAGMA journal_mode=WAL")  # ускоряет запись
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """Создаёт таблицы, если их ещё нет."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            is_urgent INTEGER DEFAULT 0,
            is_important INTEGER DEFAULT 0,
            is_done INTEGER DEFAULT 0,
            tags TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()