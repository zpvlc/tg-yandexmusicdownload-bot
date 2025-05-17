# 🎵 Telegram Music Downloader Bot (Yandex Music)

Бот для Telegram, позволяющий скачивать треки с Яндекс.Музыки по ссылке или через inline-поиск.  
Поддерживает выбор качества, загрузку обложек и простое управление.



## ⚙️ Возможности

- 🎧 Скачивание треков с Яндекс.Музыки
- 🖼 Получение только обложки трека
- 🔍 Inline-поиск по названию
- 🗣 Выбор качества звучания (низкое / оптимальное / лучшее)
- 🧹 Очистка временных файлов после отправки
- 🤖 Простой Telegram-интерфейс на Pyrogram



## 🛠 Используемые технологии

Бот основан на следующих библиотеках и проектах:

- [Pyrogram](https://github.com/pyrogram/pyrogram) — Telegram API клиент
- [yandex-music](https://github.com/MarshalX/yandex-music-api) от **MarshalX** — неофициальный Python-клиент для Яндекс.Музыки
- [yandex-music-downloader](https://github.com/listochek/yandex-music-downloader) от **listochek** — CLI-инструмент для скачивания треков с Яндекс.Музыки
- [mutagen](https://mutagen.readthedocs.io/) — библиотека для работы с метаданными аудиофайлов
- [Pillow (PIL)](https://python-pillow.org/) — обработка обложек



## 🚀 Быстрый старт

### 1. Клонируй репозиторий

```bash
git clone https://github.com/yourusername/music-bot.git
cd music-bot
```
### 2. Установи зависимости
```bash
pip install -r requirements.txt
```
### 3. Создай файл .env
```bash
BOT_TOKEN=your_telegram_bot_token
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
YANDEX_TOKEN=your_yandex_music_token
```
### 4. Запуск бота
```bash
python bot.py
```
## Лицензия
Этот проект распространяется под лицензией MIT.
Ты можешь свободно использовать, изменять и распространять его.
## Автор
Создан @zpvlc с использованием открытых проектов от
MarshalX и listochek.

Если бот оказался полезен — ⭐ поставь звезду на GitHub :)






