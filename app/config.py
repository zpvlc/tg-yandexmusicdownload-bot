from dataclasses import dataclass
from pydantic_settings import BaseSettings
from pydantic import SecretStr

class EnvConfig(BaseSettings):
    """
    Валидирует переменные окружения из .env
    """
    BOT_TOKEN: SecretStr
    YANDEX_TOKEN: SecretStr
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = 'ignore' 

@dataclass
class BotConfig:
    """Конфиг для Телеграм Бота"""
    token: str

@dataclass
class YandexConfig:
    """Конфиг для API Яндекса"""
    token: str

def load_config() -> tuple[BotConfig, YandexConfig]:
    """
    Загружает, валидирует и возвращает 
    конфигурацию в удобных объектах.
    """
    env = EnvConfig()

    return (
        BotConfig(token=env.BOT_TOKEN.get_secret_value()),
        YandexConfig(token=env.YANDEX_TOKEN.get_secret_value())
    )