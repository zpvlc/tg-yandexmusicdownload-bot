from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from app.keyboards.inline import get_settings_menu, get_quality_submenu
# ===>>> ИМПОРТИРУЕМ БАЗУ ДАННЫХ <<<===
from app.services.database import Database

router = Router()

QUALITY_NAMES = {
    0: "Низкое (MP3 128)",
    1: "Оптимальное (MP3 192)",
    2: "Лучшее (FLAC)"
}

async def _update_settings_menu(message: types.Message, db: Database, user_id: int, text: str = None):
    """
    Вспомогательная функция для обновления меню настроек
    (читает настройки из БД).
    """
    settings = await db.get_user_stats_and_settings(user_id)
    
    quality_code = settings.get("quality", 1)
    send_lrc = settings.get("send_lrc", True)
    
    quality_name = QUALITY_NAMES.get(quality_code, "Оптимальное")
    
    text_to_send = text or "<b>⚙️ Настройки бота</b>\n\nВыберите опцию:"
    
    try:
        await message.edit_text(
            text_to_send,
            reply_markup=get_settings_menu(quality_name, send_lrc)
        )
    except Exception:
        await message.answer(
            text_to_send,
            reply_markup=get_settings_menu(quality_name, send_lrc)
        )

@router.callback_query(F.data == "settings:quality_menu")
async def handle_quality_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "<b>Выберите желаемое качество:</b>\n\n"
        "<i>(FLAC - лучший, но тяжелый и может долго загружаться)</i>",
        reply_markup=get_quality_submenu()
    )
    await callback.answer()

@router.callback_query(F.data == "settings:main")
async def handle_back_to_settings(callback: types.CallbackQuery, db: Database):
    await _update_settings_menu(callback.message, db, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "settings:close")
async def handle_close_settings(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("Настройки сохранены.")

@router.callback_query(F.data.startswith("quality:"))
async def handle_quality_select(callback: types.CallbackQuery, db: Database):
    try:
        quality_code = int(callback.data.split(":")[-1])
        await db.set_user_quality(callback.from_user.id, quality_code)
        
        quality_name = QUALITY_NAMES.get(quality_code, "Неизвестное")
        
        await _update_settings_menu(
            callback.message, 
            db,
            callback.from_user.id,
            text=f"✅ <b>Качество сохранено:</b> {quality_name}\n\n"
                 "<b>⚙️ Настройки бота</b>\nВыберите опцию:"
        )
        await callback.answer(f"Выбрано: {quality_name}")

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "settings:toggle_lrc")
async def handle_lrc_toggle(callback: types.CallbackQuery, db: Database):
    new_lrc_mode = await db.toggle_user_lrc(callback.from_user.id)
    
    status = "ВКЛЮЧЕНО" if new_lrc_mode else "ВЫКЛЮЧЕНО"
    
    await _update_settings_menu(
        callback.message,
        db,
        callback.from_user.id,
        text=f"✅ <b>Авто-LRC: {status}</b>\n\n"
             "<b>⚙️ Настройки бота</b>\nВыберите опцию:"
    )
    await callback.answer(f"Авто-LRC: {status}")