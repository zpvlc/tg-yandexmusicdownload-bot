import io
import logging
from mutagen import File as AudioFile
from PIL import Image
from mutagen.mp4 import MP4, MP4Cover

logger = logging.getLogger(__name__)

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
            if 'covr' in tags:
                cover_data = tags['covr'][0]
                if isinstance(cover_data, MP4Cover):
                    img_format = 'PNG' if cover_data.imageformat == MP4Cover.FORMAT_PNG else 'JPEG'
                    with io.BytesIO(cover_data) as stream:
                        with Image.open(stream) as img:
                            # Обложку нужно ресайзить, иначе Telegram не примет
                            img.thumbnail((320, 320)) 
                            cover_bytes = io.BytesIO()
                            img.save(cover_bytes, format=img_format)
                            cover_bytes.seek(0)
        elif audio.tags:
            title = audio.tags.get("TIT2", [None])[0]
            performer = audio.tags.get("TPE1", [None])[0]
            # (Логика для обложек MP3, если нужна, но yandex-music-downloader
            #  кажется, всегда качает в M4A (MP4), так что пока опустим)

        return title, performer, duration, cover_bytes

    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return None, None, None, None