from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Возвращает главную Reply-клавиатуру.
    """
    buttons = [
        [
            KeyboardButton(text="🔍 Поиск"), 
            KeyboardButton(text="🖼 Скачать обложку")
        ],
        [
            KeyboardButton(text="📝 Скачать текст песни"),
            KeyboardButton(text="⚙️ Настройки") 
        ],
        [
            
            KeyboardButton(text="📊 Статистика")
        ]
    ]
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )
    return keyboard