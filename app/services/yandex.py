import asyncio
import os
import glob
import subprocess 
import logging
import re
from yandex_music import Client, Track

logger = logging.getLogger(__name__)

# Куда будем временно сохранять треки
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def setup_yandex_client(token: str) -> Client:
    """
    Асинхронно инициализирует клиент Яндекс.Музыки.
    (Используется только для поиска)
    """
    client = Client(token)
    await asyncio.to_thread(client.init)
    return client

async def search_tracks(client: Client, query: str) -> list:
    """
    Асинхронно ищет треки.
    (Остается без изменений)
    """
    if not query:
        return []
    
    search_result = await asyncio.to_thread(client.search, query)
    
    if search_result.tracks:
        return search_result.tracks.results[:10]
    return []

def _clear_download_dir():
    """Очищает папку загрузок перед новой операцией."""
    try:
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.*"), recursive=True)
        for f in files:
            os.remove(f)
    except Exception as e:
        logger.warning(f"Failed to clear download dir: {e}")

async def download_track_via_cli(
    token: str, 
    track_id: str, 
    quality_code: int
) -> str:
    """
    Скачивает трек с помощью yandex-music-downloader в отдельном потоке.
    Возвращает путь к скачанному файлу.
    """
    _clear_download_dir()
    
    quality_str = str(quality_code)
    url = f"https://music.yandex.ru/track/{track_id}"
    
    cmd = [
        "yandex-music-downloader",
        "--token", token,
        "--quality", quality_str,
        "--embed-cover",
        "--cover-resolution", "400",
        "--url", url,
        "--dir", DOWNLOAD_DIR,
        # ===>>> ИСПРАВЛЕНИЕ ЗДЕСЬ: Задаем чистый паттерн <<<===
        "--path-pattern", "#track-artist - #title"
    ]

    # Запускаем блокирующий subprocess в потоке
    result = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, encoding='utf-8'
    )

    if result.returncode != 0:
        logger.error(f"Downloader failed: {result.stderr}")
        raise Exception(f"Ошибка загрузчика: {result.stderr[:1000]}")

    # Ищем скачанный файл
    audio_files = sorted(
        glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.*"), recursive=True),
        key=os.path.getmtime,
        reverse=True
    )
    
    if not audio_files:
        raise Exception("Файл был скачан, но не найден в папке.")
        
    return audio_files[0]

def _parse_lrc_to_plain(lrc_text: str) -> str:
    """Убирает [xx:xx.xx] таймкоды из LRC."""
    return re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', lrc_text).strip()

async def get_lyrics_via_cli(token: str, track_id: str) -> (str, str):
    """
    Скачивает LRC и Plain text с помощью yandex-music-downloader.
    Возвращает (lrc_text, plain_text)
    """
    _clear_download_dir()
    
    url = f"https://music.yandex.ru/track/{track_id}"
    
    cmd = [
        "yandex-music-downloader",
        "--token", token,
        "--lyrics-format", "lrc",
        "--quality", "0",
        "--skip-existing",
        "--url", url,
        "--dir", DOWNLOAD_DIR,
        # ===>>> ИСПРАВЛЕНИЕ ЗДЕСЬ: Задаем чистый паттерн <<<===
        "--path-pattern", "#track-artist - #title"
    ]
    
    result = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, encoding='utf-8'
    )

    if result.returncode != 0:
        logger.error(f"Lyrics Downloader failed: {result.stderr}")
        raise Exception(f"Ошибка загрузчика текста: {result.stderr[:1000]}")
    
    lrc_files = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.lrc"), recursive=True)
    
    if not lrc_files:
        return None, None
        
    lrc_filepath = lrc_files[0]
    
    try:
        with open(lrc_filepath, 'r', encoding='utf-8') as f:
            lrc_text = f.read()
            
        plain_text = _parse_lrc_to_plain(lrc_text)
        
        return lrc_text, plain_text
        
    except Exception as e:
        logger.error(f"Failed to read LRC file: {e}")
        return None, None
    finally:
        _clear_download_dir() 

async def get_cover_via_cli(token: str, track_id: str) -> str:
    """
    Скачивает трек с обложкой в макс. разрешении ("original").
    Возвращает путь к скачанному файлу (для извлечения обложки).
    """
    _clear_download_dir()
    
    url = f"https://music.yandex.ru/track/{track_id}"
    
    cmd = [
        "yandex-music-downloader",
        "--token", token,
        "--quality", "0",
        "--embed-cover",
        "--cover-resolution", "original",
        "--url", url,
        "--dir", DOWNLOAD_DIR,
        # ===>>> ИСПРАВЛЕНИЕ ЗДЕСЬ: Задаем чистый паттерн <<<===
        "--path-pattern", "#track-artist - #title"
    ]

    result = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, encoding='utf-8'
    )

    if result.returncode != 0:
        logger.error(f"Downloader failed (for cover): {result.stderr}")
        raise Exception(f"Ошибка загрузчика: {result.stderr[:1000]}")

    audio_files = sorted(
        glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.*"), recursive=True),
        key=os.path.getmtime,
        reverse=True
    )
    
    if not audio_files:
        raise Exception("Файл для обложки был скачан, но не найден.")
        
    audio_file = next((f for f in audio_files if not f.endswith('.lrc')), None)
    
    if not audio_file:
         raise Exception("Файл для обложки не найден (только .lrc).")
         
    return audio_file