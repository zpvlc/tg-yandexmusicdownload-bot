from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime 

from app.keyboards.reply import get_main_keyboard
from app.keyboards.inline import get_search_keyboard, get_settings_menu
from app.states.main import ActionStates 
from app.services.database import Database

router = Router()

QUALITY_NAMES = {
    0: "Низкое (MP3 128)",
    1: "Оптимальное (MP3 192)",
    2: "Лучшее (FLAC)"
}

@router.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext, db: Database):
    """
    Обработчик команды /start
    1. Создает юзера в БД (если нет)
    2. Устанавливает FSM state (временный)
    """
    # 1. Создаем пользователя в SQLite (он установит first_seen и настройки)
    await db.get_or_create_user(message.from_user.id)
    
    # 2. Устанавливаем ВРЕМЕННЫЙ state (FSM)
    await state.set_state(ActionStates.awaiting_link_for_download)
    
    await message.answer(
        "<b>🎵 Добро пожаловать в Яндекс Музыка!</b>\n\n"
        "<b>📌 Как скачать музыку:</b>\n"
        "1. Зайдите в '⚙️ Настройки', чтобы выбрать качество\n"
        "2. Нажмите <i> '🔍 Поиск' </i> или отправьте ссылку\n"            
        "3. Получите трек и наслаждайтесь!\n\n",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "🔍 Поиск")
async def handle_search_button(message: types.Message, state: FSMContext, bot_username: str):
    await state.set_state(ActionStates.awaiting_link_for_download)
    await message.answer(
        "<b>🔍 Как найти трек:</b>\n"
        "1. Нажмите кнопку ниже и введите запрос\n"
        "2. Выберите трек из результатов\n\n"
        f"<i>Альтернатива:</i> <code>@{bot_username} название</code>",
        reply_markup=get_search_keyboard()
    )

@router.message(F.text == "📝 Скачать текст песни")
async def handle_lyrics_button(message: types.Message, state: FSMContext, bot_username: str):
    await state.set_state(ActionStates.awaiting_link_for_lyrics)
    await message.answer(
        "<b>📝 Как получить текст:</b>\n"
        "1. Нажмите кнопку 'Начать поиск' ниже\n"
        "2. Выберите трек, и я пришлю его текст.\n\n"
        f"<i>Альтернатива:</i> <code>@{bot_username} название</code>",
        reply_markup=get_search_keyboard()
    )

@router.message(F.text == "🖼 Скачать обложку")
async def handle_cover_button(message: types.Message, state: FSMContext, bot_username: str):
    await state.set_state(ActionStates.awaiting_link_for_cover)
    await message.answer(
        "<b>🖼 Как получить обложку:</b>\n"
        "1. Нажмите кнопку 'Начать поиск' ниже\n"
        "2. Выберите трек, и я пришлю его обложку.\n\n"
        f"<i>Альтернатива:</i> <code>@{bot_username} название</code>",
        reply_markup=get_search_keyboard()
    )

@router.message(F.text == "⚙️ Настройки")
async def handle_settings_button(message: types.Message, db: Database):
    """
    Показывает инлайн-меню настроек (читает из SQLite).
    """
    # ===>>> ЧИТАЕМ ИЗ БД <<<===
    settings = await db.get_user_stats_and_settings(message.from_user.id)
    
    quality_code = settings.get("quality", 1)
    send_lrc = settings.get("send_lrc", True)
    
    quality_name = QUALITY_NAMES.get(quality_code, "Оптимальное")
    
    await message.answer(
        "<b>⚙️ Настройки бота</b>\n\n"
        "Здесь вы можете управлять качеством треков и автоматической отправкой текстов (LRC).",
        reply_markup=get_settings_menu(quality_name, send_lrc)
    )

@router.message(F.text == "📊 Статистика")
async def handle_stats_button(message: types.Message, db: Database):
    """
    Показывает статистику пользователя из БД.
    """
    # ===>>> ЧИТАЕМ ИЗ БД <<<===
    stats = await db.get_user_stats_and_settings(message.from_user.id)
    
    if not stats:
        await message.answer("Ошибка: не удалось получить вашу статистику.")
        return
        
    try:
        first_seen_date = datetime.fromisoformat(stats["first_seen"])
        date_str = first_seen_date.strftime("%d.%m.%Y в %H:%M")
    except Exception:
        date_str = "Неизвестно"
    
    text = (
        f"<b>📊 Ваша статистика</b>\n\n"
        f" • <b>Первый запуск:</b> {date_str}\n\n"
        f" • <b>Скачано треков:</b> {stats['tracks']}\n"
        f" • <b>Скачано текстов:</b> {stats['lyrics']}\n"
        f" • <b>Скачано обложек:</b> {stats['covers']}\n"
    )
    
    await message.answer(text)