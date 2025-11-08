import logging
import os
import asyncio
import io 

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from yandex_music import Client, Track 

from app.services.yandex import download_track_via_cli, get_lyrics_via_cli, get_cover_via_cli
from app.services.metadata import extract_metadata
from app.keyboards.inline import get_settings_menu 
from app.services.database import Database
from app.states.main import ActionStates


router = Router()
logger = logging.getLogger(__name__)

TRACK_REGEX = r"https?://music\.yandex\.(ru|com)/track/(\d+)"


@router.message(F.text.regexp(TRACK_REGEX))
async def handle_track_link(
    message: types.Message, 
    state: FSMContext, 
    yandex_client: Client,
    yandex_token: str,
    db: Database
):
    """
    Ловит ссылку на трек и решает, что с ней делать.
    """
    try:
        # FSM state (временный)
        current_state = await state.get_state()
        track_id = message.text.split("/")[-1].split("?")[0]

        try:
            track_obj = (await asyncio.to_thread(yandex_client.tracks, track_id))[0]
        except Exception:
            track_obj = None

        if current_state == ActionStates.awaiting_link_for_lyrics.state:
            await process_lyrics(message, yandex_token, track_id, track_obj, db) 
        elif current_state == ActionStates.awaiting_link_for_cover.state:
            await process_cover(message, yandex_token, track_id, track_obj, db) 
        else:
            await process_download(message, yandex_token, track_id, track_obj, db) 
            
    finally:
        await state.set_state(ActionStates.awaiting_link_for_download)


async def process_download(
    message: types.Message, 
    yandex_token: str,
    track_id: str,
    track_obj: Track | None,
    db: Database
):
    """
    Обрабатывает скачивание аудиофайла.
    (Читает настройки из БД)
    """
    # ===>>> ЧИТАЕМ НАСТРОЙКИ ИЗ БД <<<===
    settings = await db.get_user_stats_and_settings(message.from_user.id)
    quality_code = settings.get("quality", 1)
    send_lrc = settings.get("send_lrc", True)

    try:
        await message.delete() 
    except Exception:
        pass 

    status_msg = await message.answer("⏳ <b>Начинаю скачивание...</b>\n<i>(Это может занять время)</i>")
    
    filepath = None
    
    try:
        filepath = await download_track_via_cli(
            yandex_token, track_id, quality_code
        )
        
        await status_msg.edit_text("⚙️ <b>Извлекаю метаданные...</b>")
        
        title_to_send, performer_to_send, duration_to_send, thumb = await asyncio.to_thread(
            extract_metadata, filepath
        )

        if not title_to_send and track_obj:
            title_to_send = track_obj.title
        if not performer_to_send and track_obj:
            performer_to_send = ', '.join(a.name for a in track_obj.artists)
        if not duration_to_send and track_obj:
            duration_to_send = track_obj.duration_ms // 1000

        await status_msg.edit_text("📤 <b>Загружаю аудио в Telegram...</b>")
        
        await message.answer_audio(
            audio=types.FSInputFile(filepath),
            title=title_to_send or "Без названия",
            performer=performer_to_send or "Неизвестный",
            duration=duration_to_send,
            thumbnail=types.BufferedInputFile(thumb.getvalue(), "jpg") if thumb else None
        )
        
        await status_msg.delete()
        
        # ===>>> СЧЕТЧИК <<<===
        await db.increment_track_count(message.from_user.id)

        # ===>>> ЧИТАЕМ НАСТРОЙКУ ИЗ ПЕРЕМЕННОЙ <<<===
        if send_lrc:
            try:
                lrc_text, plain_text = await get_lyrics_via_cli(yandex_token, track_id)
                if lrc_text and track_obj:
                    lrc_file = types.BufferedInputFile(
                        file=lrc_text.encode('utf-8'), 
                        filename=f"{track_obj.artists[0].name if track_obj.artists else 'Unknown'} - {track_obj.title}.lrc"
                    )
                    await message.answer_document(lrc_file)
                    await db.increment_lyrics_count(message.from_user.id)
            except Exception as e:
                logger.warning(f"Failed to auto-send LRC: {e}")

    except Exception as e:
        logger.error(f"Download error: {e}")
        error_text = str(e).replace("<", "&lt;").replace(">", "&gt;")
        await status_msg.edit_text(f"❌ <b>Ошибка при загрузке:</b>\n<code>{error_text}</code>")
    
    finally:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Failed to remove file: {e}")


async def process_lyrics(
    message: types.Message,
    yandex_token: str,
    track_id: str,
    track_obj: Track | None,
    db: Database
):
    """
    Обрабатывает запрос на текст песни (по кнопке).
    """
    try:
        await message.delete()
    except Exception:
        pass

    status_msg = await message.answer("⏳ <b>Ищу текст песни (LRC)...</b>")
    
    try:
        lrc_text, plain_text = await get_lyrics_via_cli(yandex_token, track_id)
        
        if not track_obj:
             await status_msg.edit_text("❌ <b>Ошибка:</b> Не удалось получить информацию о треке.")
             return

        track_title = f"<i>Трек: {track_obj.artists[0].name} - {track_obj.title}</i>" if track_obj.artists else ""

        if not plain_text:
            await status_msg.edit_text(
                f"❌ <b>Текст песни не найден.</b>\n\n{track_title}"
            )
            return

        lrc_file = types.BufferedInputFile(
            file=lrc_text.encode('utf-8'), 
            filename=f"{track_obj.artists[0].name if track_obj.artists else 'Unknown'} - {track_obj.title}.lrc"
        )
        await message.answer_document(lrc_file, caption=f"🎵 Текст песни (LRC) с таймкодами.\n{track_title}")
        
        await status_msg.delete()
        
        # ===>>> СЧЕТЧИК <<<===
        await db.increment_lyrics_count(message.from_user.id)

    except Exception as e:
        logger.error(f"Lyrics error: {e}")
        error_text = str(e).replace("<", "&lt;").replace(">", "&gt;")
        await status_msg.edit_text(f"❌ <b>Ошибка при поиске текста:</b>\n<code>{error_text}</code>")


async def process_cover(
    message: types.Message,
    yandex_token: str,
    track_id: str,
    track_obj: Track | None,
    db: Database
):
    """
    Обрабатывает запрос на обложку трека.
    """
    try:
        await message.delete()
    except Exception:
        pass

    status_msg = await message.answer("⏳ <b>Ищу обложку...</b>")
    filepath = None
    
    try:
        filepath = await get_cover_via_cli(yandex_token, track_id)
        await status_msg.edit_text("⚙️ <b>Извлекаю обложку...</b>")
        
        _, _, _, thumb = await asyncio.to_thread(
            extract_metadata, filepath
        )

        track_title = ""
        if track_obj:
            track_title = f"<i>{track_obj.artists[0].name} - {track_obj.title}</i>" if track_obj.artists else ""

        if thumb:
            await message.answer_photo(
                photo=types.BufferedInputFile(thumb.getvalue(), "cover.jpg"),
                caption=f"🖼 Обложка трека.\n{track_title}"
            )
            await status_msg.delete()
            
            # ===>>> СЧЕТЧИК <<<===
            await db.increment_cover_count(message.from_user.id)
            
        else:
            await status_msg.edit_text(f"❌ <b>Обложка не найдена.</b>\n\n{track_title}")

    except Exception as e:
        logger.error(f"Cover error: {e}")
        error_text = str(e).replace("<", "&lt;").replace(">", "&gt;")
        await status_msg.edit_text(f"❌ <b>Ошибка при поиске обложки:</b>\n<code>{error_text}</code>")
    
    finally:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Failed to remove dummy file: {e}")