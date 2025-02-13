import sys
import yaml
from typing import Tuple
from rich.text import Text
from rich.panel import Panel
from pydantic import BaseModel, Field
from src.logger import logger, console


class APISettings(BaseModel):
    openai_api_key: str = Field(..., description="Ключ API OpenAI")
    chat_gpt_model: str = Field(default="gpt-3.5-turbo", description="Модель для рерайта текста")


class ProxySettings(BaseModel):
    enabled: bool = Field(default=False, description="Использовать прокси")
    list: str = Field(default="proxies.txt", description="Файл с прокси")


class TelegramSettings(BaseModel):
    session_directory: str = Field(default="accounts/", description="Папка с session-файлами")
    proxy: ProxySettings


class CloningSettings(BaseModel):
    mode: str = Field(default="history", description="Режим работы: history или live")
    post_range: Tuple[int, int] = Field(default=(20, 300), description="Диапазон постов для клонирования")
    source_channels_file: str = Field(default="Источники.txt", description="Файл с каналами-донорами")
    target_channels_file: str = Field(default="Цели.txt", description="Файл с целевыми каналами")


class TextUniquenessSettings(BaseModel):
    rewrite: bool = Field(default=True, description="Использовать рерайт через ChatGPT")
    symbol_masking: bool = Field(default=True, description="Маскировка RU-EN символов")
    replacements_file: str = Field(default="Замены.txt", description="Файл с заменами слов")


class ImageUniquenessSettings(BaseModel):
    crop: Tuple[int, int] = Field(default=(1, 4), description="Кадрирование в пикселях")
    brightness: Tuple[int, int] = Field(default=(1, 7), description="Изменение яркости в %")
    contrast: Tuple[int, int] = Field(default=(1, 7), description="Изменение контраста в %")
    rotation: bool = Field(default=True, description="Изменение градуса поворота")
    metadata: str = Field(default="replace", description="Удаление или замена метаданных")
    filters: bool = Field(default=True, description="Применение скрытых фильтров")


class VideoUniquenessSettings(BaseModel):
    hash_change: bool = Field(default=True, description="Изменение хеша видео")
    watermark: bool = Field(default=True, description="Добавление невидимых элементов")
    frame_rate_variation: bool = Field(default=True, description="Изменение FPS")
    audio_speed: Tuple[int, int] = Field(default=(2, 4), description="Изменение скорости аудио в %")


class UniquenessSettings(BaseModel):
    text: TextUniquenessSettings
    image: ImageUniquenessSettings
    video: VideoUniquenessSettings


class TimeoutSettings(BaseModel):
    post_delay: Tuple[int, int] = Field(default=(5, 15), description="Задержка перед отправкой в сек")
    flood_wait_limit: int = Field(default=300, description="Максимальное время ожидания при флуд-ограничении")


class LoggingSettings(BaseModel):
    log_file: str = Field(default="logs/app.log", description="Основной лог-файл")
    error_log_file: str = Field(default="logs/errors.log", description="Файл логирования ошибок")


class Config(BaseModel):
    api: APISettings
    telegram: TelegramSettings
    cloning: CloningSettings
    uniqueness: UniquenessSettings
    timeouts: TimeoutSettings
    logging: LoggingSettings


class ConfigManager:
    @staticmethod
    def load_config(config_file='config/config.yaml') -> Config:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

                return Config(**config_data)
        except FileNotFoundError:
            console.log(f"Файл {config_file} не найден", style="red")
            sys.exit(1)
        except Exception as e:
            console.log("Ошибка в конфиге", style="red")
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            sys.exit(1)


def print_config(config: Config) -> None:
    config_text = Text()

    config_text.append("API Настройки:\n", style="bold cyan")
    config_text.append("  OpenAI API Key: ", style="cyan")
    config_text.append(f"{config.api.openai_api_key}\n", style="green")
    config_text.append("  ChatGPT Model: ", style="cyan")
    config_text.append(f"{config.api.chat_gpt_model}\n\n", style="green")

    config_text.append("Telegram Настройки:\n", style="bold cyan")
    config_text.append("  Папка с сессиями: ", style="cyan")
    config_text.append(f"{config.telegram.session_directory}\n", style="green")
    config_text.append("  Использовать прокси: ", style="cyan")
    config_text.append(f"{'Да' if config.telegram.proxy.enabled else 'Нет'}\n", style="green")
    config_text.append("  Файл с прокси: ", style="cyan")
    config_text.append(f"{config.telegram.proxy.list}\n\n", style="green")

    config_text.append("Настройки клонирования:\n", style="bold cyan")
    config_text.append("  Режим работы: ", style="cyan")
    config_text.append(f"{config.cloning.mode}\n", style="green")
    config_text.append("  Диапазон постов: ", style="cyan")
    config_text.append(f"{config.cloning.post_range[0]} - {config.cloning.post_range[1]}\n", style="green")
    config_text.append("  Источники каналов: ", style="cyan")
    config_text.append(f"{config.cloning.source_channels_file}\n", style="green")
    config_text.append("  Целевые каналы: ", style="cyan")
    config_text.append(f"{config.cloning.target_channels_file}\n\n", style="green")

    config_text.append("Уникализация текста:\n", style="bold cyan")
    config_text.append("  Использовать рерайт: ", style="cyan")
    config_text.append(f"{'Да' if config.uniqueness.text.rewrite else 'Нет'}\n", style="green")
    config_text.append("  Маскировка символов: ", style="cyan")
    config_text.append(f"{'Да' if config.uniqueness.text.symbol_masking else 'Нет'}\n", style="green")
    config_text.append("  Файл замен: ", style="cyan")
    config_text.append(f"{config.uniqueness.text.replacements_file}\n\n", style="green")

    config_text.append("Уникализация изображений:\n", style="bold cyan")
    config_text.append("  Кадрирование: ", style="cyan")
    config_text.append(f"{config.uniqueness.image.crop[0]} - {config.uniqueness.image.crop[1]} пикселей\n", style="green")
    config_text.append("  Яркость: ", style="cyan")
    config_text.append(f"{config.uniqueness.image.brightness[0]} - {config.uniqueness.image.brightness[1]}%\n", style="green")
    config_text.append("  Контраст: ", style="cyan")
    config_text.append(f"{config.uniqueness.image.contrast[0]} - {config.uniqueness.image.contrast[1]}%\n", style="green")
    config_text.append("  Изменение метаданных: ", style="cyan")
    config_text.append(f"{config.uniqueness.image.metadata}\n", style="green")

    config_text.append("\nНастройки логирования:\n", style="bold cyan")
    config_text.append("  Основной лог-файл: ", style="cyan")
    config_text.append(f"{config.logging.log_file}\n", style="green")
    config_text.append("  Файл ошибок: ", style="cyan")
    config_text.append(f"{config.logging.error_log_file}\n", style="green")

    console.print(Panel(config_text, title="[bold magenta]Конфигурация[/]", border_style="cyan"))
