import sys
import yaml
from typing import Tuple, List, Dict
from rich.text import Text
from rich.panel import Panel
from pydantic import BaseModel, Field
from src.logger import logger, console



class ProxyConfig(BaseModel):
    proxy: str = Field(
        default="",
        description="Прокси-сервер в формате IP:Port:Username:Password"
    )


class ChannelConfig(BaseModel):
    source_channels: List[str] = Field(default=[], description="Список источников")
    target_channels: Dict[str, str] = Field(
        default={},
        description="Список целевых каналов в формате {source: target}"
    )


class ModeConfig(BaseModel):
    mode: str = Field(
        default="history",
        description="Режим работы: history или realtime"
    )
    history_range: Tuple[int, int] = Field(
        default=(20, 300),
        description="Диапазон постов для клонирования"
    )


class DelayConfig(BaseModel):
    delay_range: Tuple[int, int] = Field(
        default=(5, 15),
        description="Диапазон задержек перед отправкой постов"
    )
    flood_wait_limit: int = Field(
        default=600,
        description="Максимальное время ожидания при флуд-лимите"
    )


class UniqueConfig(BaseModel):
    text_replacement: Dict[str, str] = Field(default={}, description="Замена текста")
    image_unique_params: Dict[str, int] = Field(
        default={}, description="Параметры уникализации изображений"
    )
    video_unique_params: Dict[str, int] = Field(
        default={}, description="Параметры уникализации видео"
    )
    text_unique_mode: str = Field(
        default="chatgpt",
        description="Метод уникализации текста: chatgpt или символы"
    )


class LoggingConfig(BaseModel):
    log_file: str = Field(
        default="logs/bot.log",
        description="Файл для записи логов"
    )


class Config(BaseModel):
    proxy: ProxyConfig = ProxyConfig()
    channels: ChannelConfig = ChannelConfig()
    mode: ModeConfig = ModeConfig()
    delay: DelayConfig = DelayConfig()
    unique: UniqueConfig = UniqueConfig()
    logging: LoggingConfig = LoggingConfig()


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

    config_text.append("  Режим работы: ", style="cyan")
    config_text.append(f"{config.mode}\n", style="green")
    config_text.append("  Источники: ", style="cyan")
    config_text.append(f"{', '.join(config.source_channels)}\n", style="green")
    config_text.append("  Целевые каналы: ", style="cyan")
    config_text.append(f"{config.target_channels}\n", style="green")
    config_text.append("  Задержка перед отправкой: ", style="cyan")
    config_text.append(f"{config.delay_range[0]} - {config.delay_range[1]} сек\n", style="green")
    config_text.append("  Лог-файл: ", style="cyan")
    config_text.append(f"{config.log_file}\n", style="green")

    console.print(Panel(config_text, title="[bold magenta]Конфигурация[/]", border_style="cyan"))
