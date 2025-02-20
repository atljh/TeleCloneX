import os
import subprocess
from typing import Dict
from src.logger import logger
from src.managers.unique_manager import UniqueManager


class ContentUniquifier:
    """
    Отвечает за уникализацию контента.
    """

    def __init__(self, unique_manager: UniqueManager):
        self.unique_manager = unique_manager

    async def make_content_unique(self, content: Dict) -> Dict:
        """
        Уникализирует контент сообщения.

        Args:
            content (Dict): Оригинальный контент.

        Returns:
            Dict: Уникализированный контент.
        """
        unique_content = {}

        if content.get("text"):
            unique_content["text"] = await self.unique_manager.unique_text(content["text"])

        if content.get("photo"):
            unique_content["photo"] = self.unique_manager.unique_image(content["photo"])

        if content.get("video"):
            unique_content["video"] = self.unique_manager.unique_video(content["video"])

        if content.get("audio"):
            audio_path = content["audio"]
            ogg_path = self._convert_to_ogg(audio_path)
            unique_content["audio"] = ogg_path

        unique_content['is_round'] = content.get('is_round')

        return unique_content

    def _convert_to_ogg(self, audio_path: str) -> str:
        """
        Конвертирует аудиофайл в формат OGG (Opus) с использованием ffmpeg.

        Args:
            audio_path (str): Путь к исходному аудиофайлу.

        Returns:
            str: Путь к сконвертированному файлу в формате OGG.
        """
        try:
            ogg_path = os.path.splitext(audio_path)[0] + ".ogg"

            command = [
                "ffmpeg",
                "-loglevel", "error",
                "-y",
                "-i", audio_path,
                "-c:a", "libopus",
                ogg_path
            ]

            subprocess.run(command, check=True)

            os.remove(audio_path)

            return ogg_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при конвертации аудио в OGG: {e}")
            raise
        except Exception as e:
            logger.error(f"Неизвестная ошибка: {e}")
