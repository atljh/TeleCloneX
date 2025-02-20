import os
import random
import string
import subprocess
from src.logger import console, logger


class VideoUniquenessManager:
    """
    Manages video uniqueness: conversion to .mp4, metadata replacement, and metadata removal.
    """

    def __init__(self, config):
        self.config = config

    def unique_video(self, video_path: str) -> str:
        """
        Converts a video to a format compatible with Telegram and applies uniqueness transformations.

        Args:
            video_path (str): Path to the input video.

        Returns:
            str: Path to the unique video.
        """
        output_path = f"converted_{os.path.splitext(os.path.basename(video_path))[0]}.mp4"

        try:
            command = [
                "ffmpeg",
                "-loglevel", "error",
                "-i", video_path,
                "-c:v", "libx264",
                "-profile:v", "baseline",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_path
            ]
            subprocess.run(command, check=True)
            console.print(f"Видео {video_path} успешно преобразовано в {output_path}.", style="green")

            if self.config.uniqueness.video.metadata == "replace":
                self._replace_video_metadata(output_path)
            elif self.config.uniqueness.video.metadata == "remove":
                self._remove_video_metadata(output_path)

            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при преобразовании видео: {e.stderr}")
            return video_path

    def _replace_video_metadata(self, video_path: str) -> None:
        """
        Replaces video metadata with custom random data.

        Args:
            video_path (str): Path to the video.
        """
        try:
            make = self._generate_random_string(10)
            model = self._generate_random_string(8)
            serial_number = self._generate_random_string(12)

            command = [
                "ffmpeg",
                "-loglevel", "error",  # Убираем лишние логи
                "-i", video_path,  # Входной файл
                "-metadata", f"artist=UniqueManager",  # Метаданные
                "-metadata", f"software=ContentCloner",
                "-metadata", f"make={make}",
                "-metadata", f"model={model}",
                "-metadata", f"serial_number={serial_number}",
                "-vf", "fps=30",  # Устанавливаем FPS на 30 (рекомендуется для Telegram)
                "-c:v", "libx264",  # Кодек видео H.264
                "-preset", "fast",  # Баланс между скоростью и качеством
                "-crf", "23",  # Качество видео (меньше значение = лучше качество, 23 — оптимально)
                "-movflags", "+faststart",  # Для быстрого старта воспроизведения
                "-c:a", "aac",  # Кодек аудио AAC
                "-b:a", "128k",  # Битрейт аудио (128 kbps — рекомендуется)
                f"temp_{video_path}"  # Выходной файл
            ]
            subprocess.run(command, check=True)
            os.replace(f"temp_{video_path}", video_path)
            console.print(f"Метаданные видео {video_path} заменены.", style="green")
        except Exception as e:
            logger.error(f"Ошибка при замене метаданных видео: {e}")

    def _remove_video_metadata(self, video_path: str) -> None:
        """
        Removes metadata from a video.

        Args:
            video_path (str): Path to the video.
        """
        try:
            command = [
                "ffmpeg",
                "-loglevel", "error",
                "-i", video_path,
                "-map_metadata", "-1",
                "-c", "copy",
                f"temp_{video_path}"
            ]
            subprocess.run(command, check=True)
            os.replace(f"temp_{video_path}", video_path)
            console.print(f"Метаданные видео {video_path} удалены.", style="green")
        except Exception as e:
            logger.error(f"Ошибка при удалении метаданных видео: {e}")

    def _generate_random_string(self, length: int = 8) -> str:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
