import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from config import BOT_TOKEN
from database.db import init_db
from handlers.menu import router as menu_router
from handlers.add_task import router as add_task_router
from handlers.list_tasks import router as list_tasks_router
from handlers.task_actions import router as task_actions_router
from handlers.edit_task import router as edit_task_router
from handlers.stats import router as stats_router

async def main():
    # Инициализируем БД перед стартом
    init_db()

    session = AiohttpSession(proxy="socks5://127.0.0.1:12334")
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.include_router(menu_router)
    dp.include_router(add_task_router)
    dp.include_router(list_tasks_router)
    dp.include_router(task_actions_router)
    dp.include_router(edit_task_router)
    dp.include_router(stats_router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())