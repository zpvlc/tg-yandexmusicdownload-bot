from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

QUALITY_NAMES = {
    0: "Низкое (MP3 128)",
    1: "Оптимальное (MP3 192)",
    2: "Лучшее (FLAC)"
}

def get_settings_menu(current_quality_name: str, lrc_enabled: bool) -> InlineKeyboardMarkup:
    """
    Создает ГЛАВНОЕ меню настроек.
    Оно показывает текущие выборы.
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"Качество: {current_quality_name}",
            callback_data="settings:quality_menu" 
        )
    )
    
    lrc_status = "✅ Вкл" if lrc_enabled else "❌ Выкл"
    builder.row(
        InlineKeyboardButton(
            text=f"Авто-LRC: {lrc_status}",
            callback_data="settings:toggle_lrc" 
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="Готово",
            callback_data="settings:close" 
        )
    )
    
    return builder.as_markup()


def get_quality_submenu() -> InlineKeyboardMarkup:
    """
    Создает ПОДМЕНЮ выбора качества.
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки выбора качества
    for code, name in QUALITY_NAMES.items():
        builder.row(
            InlineKeyboardButton(text=name, callback_data=f"quality:{code}")
        )
    
    # Кнопка "Назад"
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="settings:main" 
        )
    )
    return builder.as_markup()


def get_search_keyboard() -> InlineKeyboardMarkup:
    """
    Возвращает Inline-клавиатуру для старта inline-поиска.
    (Эта функция без изменений)
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔍 Начать поиск", 
                switch_inline_query_current_chat=""
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard