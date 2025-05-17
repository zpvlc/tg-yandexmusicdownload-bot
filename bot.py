import os
import subprocess
import glob
import logging
import traceback
import io
from collections import defaultdict
from urllib.parse import urlparse

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent,
    ReplyKeyboardMarkup, KeyboardButton
)

from dotenv import load_dotenv
from yandex_music import Client as YandexClient
from mutagen import File as AudioFile
from PIL import Image
from mutagen.mp4 import MP4, MP4Cover

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Client(
    "music_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

DOWNLOAD_DIR = "downloads"
LYRICS_FORMAT = "none"
COVER_RESOLUTION = "original"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

import json

USER_DATA_FILE = "users.json"

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                return {int(k): v for k, v in raw.items()}
        except Exception as e:
            logger.warning(f"Не удалось загрузить user_data: {e}")
    return {}

def save_user_data():
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Не удалось сохранить user_data: {e}")

user_data_raw = load_user_data()
default_user = {"quality": None, "messages_to_delete": [], "awaiting_cover": False}
user_data = defaultdict(lambda: default_user.copy(), user_data_raw)

def quality_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Лучшее", callback_data="quality_2"),
        InlineKeyboardButton("Оптимальное", callback_data="quality_1"),
        InlineKeyboardButton("Низкое", callback_data="quality_0")
    ]])

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🗣 Качество звучания"), KeyboardButton("🔍 Поиск")],
        [KeyboardButton("🖼 Скачать обложку")]
    ], resize_keyboard=True)

def search_inline_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔍 Начать поиск", switch_inline_query_current_chat="")
    ]])

async def cleanup_user_messages(client, user_id):
    user = user_data[user_id]
    msg_ids = user.get("messages_to_delete", [])

    if msg_ids:
        try:
            await client.delete_messages(user_id, msg_ids)
        except Exception as e:
            logger.warning(f"Batch delete failed: {e}")
        user["messages_to_delete"] = []

def is_valid_yandex_music_url(url):
    try:
        parsed = urlparse(url)
        return parsed.netloc in ["music.yandex.ru", "music.yandex.com"]
    except:
        return False

def extract_metadata(path):
    try:
        audio = AudioFile(path)
        title = performer = duration = None
        cover_bytes = None

        duration = int(audio.info.length) if audio and audio.info else None

        if isinstance(audio, MP4):
            tags = audio.tags
            title = tags.get('\xa9nam', [None])[0]
            performer = tags.get('\xa9ART', [None])[0]

            # Обложка
            if 'covr' in tags:
                cover_data = tags['covr'][0]
                if isinstance(cover_data, MP4Cover):
                    img_format = 'PNG' if cover_data.imageformat == MP4Cover.FORMAT_PNG else 'JPEG'
                    with io.BytesIO(cover_data) as stream:
                        with Image.open(stream) as img:
                            cover_bytes = io.BytesIO()
                            img.save(cover_bytes, format=img_format)
                            cover_bytes.seek(0)

        elif audio.tags:
            title = audio.tags.get("TIT2", [None])[0]
            performer = audio.tags.get("TPE1", [None])[0]

        return title, performer, duration, cover_bytes

    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return None, None, None, None

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    user = user_data[user_id]

    await cleanup_user_messages(client, user_id)

    try:
        welcome_msg = await message.reply(
            "<b>🎵 Добро пожаловать в Яндекс Музыка!</b>\n\n"
            "<b>📌 Как скачать музыку:</b>\n"
            "1. Выберите качество скачивания\n"
            "2. Нажмите <i> '🔍 Поиск' </i> или отправьте ссылку\n"            
            "3. Получите трек и наслаждайтесь!\n\n",
            reply_markup=main_keyboard()
        )
        quality_msg = await message.reply(
            "<b>Выбор качества звучания</b>\n\n"
            "⚠️ <i>Важно:</i> Высокое качество — это большие файлы, будьте готовы к загрузке.",
            reply_markup=quality_keyboard()
        )

        user["messages_to_delete"].extend([welcome_msg.id, quality_msg.id])

    except Exception as e:
        logger.error(f"/start error: {e}")
        traceback.print_exc()


@app.on_message(filters.regex("^🗣 Качество звучания$"))
async def settings_command(client, message):
    user_id = message.from_user.id
    user = user_data[user_id]

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete settings message: {e}")

    try:
        msg = await message.reply(
            "<b>Выбор качества звучания</b>\n\n"
            "⚠️ <i>Важно:</i> Высокое качество — это большие файлы, будьте готовы к загрузке.",
            reply_markup=quality_keyboard()
        )
        user["messages_to_delete"].append(msg.id)
    except Exception as e:
        logger.error(f"Settings command error: {e}")
        traceback.print_exc()

@app.on_message(filters.regex("^🖼 Скачать обложку$"))
async def prompt_cover_download(client, message):
    user_id = message.from_user.id
    user = user_data[user_id]

    await message.delete()
    user["awaiting_cover"] = True

    msg = await message.reply(
        "🎯 <b>Скачивание обложки</b>\n\n"
        "Отправь ссылку на трек Яндекс Музыки.\n"
        "После этого я пришлю тебе только обложку (без трека).",
        reply_markup=main_keyboard()
    )
    user["messages_to_delete"].append(msg.id)
  
@app.on_message(filters.regex("^🔍 Поиск$"))
async def search_command(client, message):
    user_id = message.from_user.id
    user = user_data[user_id]

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete search message: {e}")

    try:
        msg = await message.reply(
            "<b>🔍 Как найти трек:</b>\n"
            "1. Нажмите кнопку ниже и введите запрос\n"
            "2. Выберите трек из результатов\n\n"
            f"<i>Альтернатива:</i> <code>@{app.me.username} название</code>",
            reply_markup=search_inline_keyboard()
        )
        user["messages_to_delete"].append(msg.id)
    except Exception as e:
        logger.error(f"Search command error: {e}")
        traceback.print_exc()

@app.on_callback_query(filters.regex("^quality_"))
async def handle_quality_choice(client, callback_query):
    user_id = callback_query.from_user.id
    user = user_data[user_id]

    try:
        quality = int(callback_query.data.split("_")[1])
        user["quality"] = quality
        save_user_data()
        quality_names = ["Низкое", " Оптимальное", "Лучшее"]
        save_user_data()

        await cleanup_user_messages(client, user_id)

        msg = await callback_query.message.reply(
            f"<i>Качество выбрано и успешно сохранено:</i> <b>{quality_names[quality]}</b>",
            reply_markup=main_keyboard()
        )
        user["messages_to_delete"].append(msg.id)
        await callback_query.answer()

    except Exception as e:
        logger.error(f"Quality choice error: {e}")
        traceback.print_exc()
        await callback_query.answer("Произошла ошибка", show_alert=True)


@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def handle_message(client, message):
    user_id = message.from_user.id
    user = user_data[user_id]
    text = message.text.strip()

    if text in ["🗣 Качество звучания", "🔍 Поиск", "🖼 Скачать обложку"]:
        return

    if user.get("awaiting_cover"):
        user["awaiting_cover"] = False

        if not is_valid_yandex_music_url(text):
            msg = await message.reply(
                "❌ Это не похоже на ссылку с Яндекс Музыки.\nПопробуй ещё раз.",
                reply_markup=main_keyboard()
            )
            user["messages_to_delete"].append(msg.id)
            return

        await message.delete()

        status_msg = await message.reply("⏳ Скачиваю обложку...", reply_markup=main_keyboard())
        user["messages_to_delete"].append(status_msg.id)

        for file in glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.*"), recursive=True):
            try:
                os.remove(file)
            except Exception as e:
                logger.warning(f"Не удалось удалить файл: {file} - {e}")

        result = subprocess.run([
            "yandex-music-downloader",
            "--token", YANDEX_TOKEN,
            "--quality", "0",  # минимальное
            "--embed-cover",
            "--cover-resolution", COVER_RESOLUTION,
            "--url", text,
            "--dir", DOWNLOAD_DIR
        ], capture_output=True, text=True)

        if result.returncode != 0:
            await status_msg.edit_text(f"❌ Ошибка:\n<pre>{result.stderr[:4000]}</pre>", parse_mode=ParseMode.HTML)
            return

        audio_files = sorted(
            glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.*"), recursive=True),
            key=lambda x: os.path.getmtime(x),
            reverse=True
        )

        if not audio_files:
            await status_msg.edit_text("❌ Не удалось найти файл.")
            return

        audio_path = audio_files[0]
        _, _, _, cover_bytes = extract_metadata(audio_path)

        await status_msg.delete()
        user["messages_to_delete"].remove(status_msg.id)

        if cover_bytes:
            cover_bytes.name = "cover.jpg"
            await message.reply_document(
                document=cover_bytes,
                caption="",
                reply_markup=main_keyboard()
            )
        else:
            await message.reply("❌ Обложка не найдена.", reply_markup=main_keyboard())
        await cleanup_user_messages(client, user_id)
        try:
            os.remove(audio_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить файл: {audio_path} - {e}")
        return

    if user.get("quality") is None:
        warning = await message.reply(
            "⚠️ *Выберите качество звучания!*\nПерейдите в меню «🗣 Качество звучания» и задайте желаемый уровень, иначе бот не знает, что отдавать.",
            reply_markup=main_keyboard()
        )
        user["messages_to_delete"].append(warning.id)
        return

    if not is_valid_yandex_music_url(text):
        fallback = await message.reply(
            "❌ <b>Неверная ссылка.</b>\nПожалуйста, пришлите корректный URL на трек Яндекс Музыки.",
            reply_markup=main_keyboard()
        )
        user["messages_to_delete"].append(fallback.id)
        return

    try:
        await message.delete()
    except Exception:
        pass

    try:
        status_msg = await message.reply(
            "⏳ <b>Скачиваю трек...</b><br>Пожалуйста, подождите. Это может занять несколько минут.",
            reply_markup=main_keyboard()
        )
        user["messages_to_delete"].append(status_msg.id)

        for file in glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.*"), recursive=True):
            try:
                os.remove(file)
            except Exception as e:
                logger.warning(f"Failed to remove file: {file} - {e}")

        result = subprocess.run([
            "yandex-music-downloader",
            "--token", YANDEX_TOKEN,
            "--quality", str(user["quality"]),
            "--lyrics-format", LYRICS_FORMAT,
            "--embed-cover",
            "--cover-resolution", COVER_RESOLUTION,
            "--url", text,
            "--dir", DOWNLOAD_DIR
        ], capture_output=True, text=True)

        if result.returncode != 0:
            error_text = result.stderr or "Неизвестная ошибка загрузчика"
            logger.error(f"Downloader error: {error_text}")
            await status_msg.edit_text(
                f"❌ Ошибка при загрузке:\n```{error_text[:4000]}```",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        audio_files = sorted(
            glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.*"), recursive=True),
            key=lambda x: os.path.getmtime(x),
            reverse=True
        )

        if not audio_files:
            await status_msg.edit_text("❌ Файл не найден.")
            return

        await status_msg.delete()
        user["messages_to_delete"].remove(status_msg.id)

        for audio_path in audio_files:
            title, performer, duration, thumb = extract_metadata(audio_path)

            await message.reply_audio(
                audio_path,
                title=title or "Без названия",
                performer=performer or "Неизвестный исполнитель",
                duration=duration,
                thumb=thumb,
                reply_markup=main_keyboard()
            )

            try:
                os.remove(audio_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить файл: {audio_path} - {e}")

    except Exception as e:
        logger.error(f"Ошибка при обработке ссылки: {e}")
        traceback.print_exc()
        await message.reply(
            f"❌ Ошибка:\n`{str(e)[:4000]}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard()
        )

@app.on_inline_query()
async def inline_search_handler(client, inline_query):
    query = inline_query.query.strip()
    results = []

    if not query:
        await inline_query.answer([], cache_time=1)
        return

    try:
        yandex = YandexClient(YANDEX_TOKEN)
        yandex.init()
    except Exception as e:
        logger.error(f"Ошибка инициализации YandexClient: {e}")
        await inline_query.answer([], cache_time=1)
        return

    try:
        search_result = yandex.search(query)
        tracks = search_result.tracks.results[:10] if search_result.tracks else []

        for track in tracks:
            title = f"{track.title} — {', '.join(artist.name for artist in track.artists)}"
            url = f"https://music.yandex.ru/track/{track.id}"

            results.append(
                InlineQueryResultArticle(
                    title=title,
                    description="Нажмите, чтобы отправить ссылку",
                    input_message_content=InputTextMessageContent(url),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Открыть в Яндекс.Музыке", url=url)
                    ]])
                )
            )

        await inline_query.answer(results, cache_time=1)

    except Exception as e:
        logger.error(f"Ошибка поиска треков: {e}")
        await inline_query.answer([], cache_time=1)


if __name__ == "__main__":
    logger.info("Запуск бота...")
    app.run()

