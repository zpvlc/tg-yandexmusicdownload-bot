import aiosqlite
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_FILE = "bot_data.db" 

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    async def init_db(self):
        """Инициализирует базу данных и создает таблицы."""
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    tracks_downloaded INTEGER DEFAULT 0,
                    lyrics_downloaded INTEGER DEFAULT 0,
                    covers_downloaded INTEGER DEFAULT 0,
                    
                    quality INTEGER DEFAULT 1,
                    send_lrc INTEGER DEFAULT 1 
                )
            """)
            try:
                await self.connection.execute("ALTER TABLE users ADD COLUMN quality INTEGER DEFAULT 1")
            except aiosqlite.OperationalError:
                pass 
            try:
                await self.connection.execute("ALTER TABLE users ADD COLUMN send_lrc INTEGER DEFAULT 1")
            except aiosqlite.OperationalError:
                pass 
                
            await self.connection.commit()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize database: {e}")
            raise

    async def get_or_create_user(self, user_id: int):
        """
        Проверяет, есть ли юзер. Если нет - создает
        с настройками по умолчанию (quality=1, send_lrc=1).
        """
        async with self.connection.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
        
        if not user:
            now = datetime.now().isoformat()
            await self.connection.execute(
                "INSERT INTO users (user_id, first_seen) VALUES (?, ?)", (user_id, now)
            )
            await self.connection.commit()
            logger.info(f"New user created: {user_id}")
    
    async def _increment_counter(self, user_id: int, column: str):
        """Внутренняя функция для увеличения счетчика."""
        await self.get_or_create_user(user_id) 
        await self.connection.execute(
            f"UPDATE users SET {column} = {column} + 1 WHERE user_id = ?", (user_id,)
        )
        await self.connection.commit()

    async def increment_track_count(self, user_id: int):
        await self._increment_counter(user_id, "tracks_downloaded")

    async def increment_lyrics_count(self, user_id: int):
        await self._increment_counter(user_id, "lyrics_downloaded")
    
    async def increment_cover_count(self, user_id: int):
        await self._increment_counter(user_id, "covers_downloaded")

    async def get_user_stats_and_settings(self, user_id: int) -> dict | None:
        """Получает ВСЮ информацию о пользователе (статистику И настройки)."""
        await self.get_or_create_user(user_id)
        async with self.connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "first_seen": row[1],
                    "tracks": row[2],
                    "lyrics": row[3],
                    "covers": row[4],
                    "quality": row[5],
                    "send_lrc": bool(row[6]) 
                }
        return None
        
    
    async def set_user_quality(self, user_id: int, quality_code: int):
        await self.get_or_create_user(user_id)
        await self.connection.execute(
            "UPDATE users SET quality = ? WHERE user_id = ?", (quality_code, user_id)
        )
        await self.connection.commit()

    async def toggle_user_lrc(self, user_id: int) -> bool:
        """Переключает LRC и возвращает НОВОЕ значение."""
        await self.get_or_create_user(user_id)
        await self.connection.execute(
            "UPDATE users SET send_lrc = (1 - send_lrc) WHERE user_id = ?", (user_id,)
        )
        await self.connection.commit()
        
        async with self.connection.execute(
            "SELECT send_lrc FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            new_val = await cursor.fetchone()
            return bool(new_val[0])