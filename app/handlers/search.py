import logging
from aiogram import Router, types
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from yandex_music import Client
from app.services.yandex import search_tracks

router = Router()
logger = logging.getLogger(__name__)

@router.inline_query()
async def handle_inline_search(query: types.InlineQuery, yandex_client: Client):
    """
    Обрабатывает inline-запросы, используя асинхронный поиск.
    """
    try:
        tracks = await search_tracks(yandex_client, query.query)
        results = []
        
        for track in tracks:
            title = track.title
            performer = ', '.join(artist.name for artist in track.artists)
            full_title = f"{performer} — {title}"
            url = f"https://music.yandex.ru/track/{track.id}"
            
            results.append(
                InlineQueryResultArticle(
                    id=str(track.id),
                    title=full_title,
                    description=f"Альбом: {track.albums[0].title}" if track.albums else "Трек",
                    input_message_content=InputTextMessageContent(message_text=url),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="Открыть в Яндекс.Музыке", url=url)
                    ]])
                )
            )
        
        await query.answer(results, cache_time=1)

    except Exception as e:
        logger.error(f"Inline search error: {e}")
        # Не падаем, просто отдаем пустой результат
        await query.answer([], cache_time=1)