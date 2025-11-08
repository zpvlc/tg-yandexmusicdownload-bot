import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage 
from aiogram.client.default import DefaultBotProperties 

from app.config import load_config
from app.services.yandex import setup_yandex_client
from app.services.database import Database, DB_FILE

from app.handlers import common, settings, search, download

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting bot...")

    bot_config, yandex_config = load_config()

    storage = MemoryStorage()
    logger.info("Using MemoryStorage (persistent settings are in SQLite).")
    
    db = Database(db_path=DB_FILE)
    await db.init_db()
    
    bot = Bot(
        token=bot_config.token,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=storage)

    yandex_client = await setup_yandex_client(yandex_config.token)
    logger.info("Yandex.Music client (for Search) initialized!")
        
    dp["bot_username"] = (await bot.get_me()).username
    dp["yandex_client"] = yandex_client
    dp["yandex_token"] = yandex_config.token
    dp["db"] = db 
    
    dp.include_router(common.router) 
    dp.include_router(settings.router)
    dp.include_router(search.router)
    dp.include_router(download.router)
    
    logger.info("All routers registered!")

    logger.info("Starting polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await db.connection.close() 
        logger.info("Bot stopped!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot execution manually interrupted!")