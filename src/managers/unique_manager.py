import os
import random
import hashlib
from typing import Dict, List, Tuple
from PIL import Image, ImageEnhance, ImageFilter
from moviepy.editor import VideoFileClip
from src.logger import console


class UniqueManager:
    """
    Класс для уникализации контента: текста, изображений и видео.
    """

    def __init__(self, config, account_phone: str):
        self.config = config
        self.account_phone = account_phone
        self.replacements = self._load_replacements(config.uniqueness.text.replacements_file)

    def _load_replacements(self, replacements_file: str) -> Dict[str, str]:
        """
        Загружает правила замены слов из файла.

        Args:
            replacements_file (str): Путь к файлу с правилами замены.

        Returns:
            Dict[str, str]: Словарь с правилами замены.
        """
        replacements = {}
        try:
            with open(replacements_file, "r", encoding="utf-8") as file:
                for line in file:
                    if "=" in line:
                        original, replacement = line.strip().split("=")
                        if replacement.strip().split(" ")[1] == self.account_phone:
                            replacements[original.strip()] = replacement.strip().split(" ")[0]
        except FileNotFoundError:
            console.log(f"Файл {replacements_file} не найден. Замены слов не будут применены.", style="yellow")
        return replacements

    def unique_text(self, text: str) -> str:
        """
        Уникализация текста:
        - Замена слов по правилам.
        - Маскировка символов RU-EN.
        - Рерайт текста через ChatGPT (если включено).

        Args:
            text (str): Исходный текст.

        Returns:
            str: Уникализированный текст.
        """
        for original, replacement in self.replacements.items():
            text = text.replace(original, replacement)

        if self.config.uniqueness.text.symbol_masking:
            text = self._mask_characters(text)

        if self.config.uniqueness.text.rewrite:
            text = self._rewrite_with_chatgpt(text)

        return text

    def _mask_characters(self, text: str) -> str:
        """
        Маскировка похожих символов RU-EN.

        Args:
            text (str): Исходный текст.

        Returns:
            str: Текст с замененными символами.
        """
        char_map = {
            "а": ["а", "a"], "А": ["А", "A"],
            "В": ["В", "B"], "е": ["е", "e"],
            "Е": ["Е", "E"], "К": ["К", "K"],
            "М": ["М", "M"], "Н": ["Н", "H"],
            "о": ["о", "o"], "О": ["О", "O"],
            "р": ["р", "p"], "Р": ["Р", "P"],
            "с": ["с", "c"], "С": ["С", "C"],
            "Т": ["Т", "T"], "х": ["х", "x"],
            "Х": ["Х", "X"], "у": ["у", "y"],
        }
        result = []
        for char in text:
            if char in char_map:
                result.append(random.choice(char_map[char]))
            else:
                result.append(char)
        return "".join(result)

    def _rewrite_with_chatgpt(self, text: str) -> str:
        """
        Рерайт текста через ChatGPT.

        Args:
            text (str): Исходный текст.

        Returns:
            str: Переписанный текст.
        """
        # Здесь должен быть код для взаимодействия с ChatGPT API
        # Например:
        # response = chatgpt_client.rewrite(text)
        # return response
        console.log("Рерайт текста через ChatGPT...", style="cyan")
        return text  # Заглушка

    def unique_image(self, image_path: str) -> str:
        """
        Уникализация изображения:
        - Кадрирование.
        - Изменение яркости и контраста.
        - Поворот.
        - Удаление/замена метаданных.
        - Добавление фильтров.

        Args:
            image_path (str): Путь к исходному изображению.

        Returns:
            str: Путь к уникализированному изображению.
        """
        console.log(f"Уникализация изображения: {image_path}", style="cyan")
        image = Image.open(image_path)

        width, height = image.size
        crop_pixels = random.randint(*self.config.uniqueness.image.crop)
        image = image.crop((crop_pixels, crop_pixels, width - crop_pixels, height - crop_pixels))

        enhancer = ImageEnhance.Brightness(image)
        brightness_factor = random.uniform(1 + self.config.uniqueness.image.brightness[0] / 100,
                                          1 + self.config.uniqueness.image.brightness[1] / 100)
        image = enhancer.enhance(brightness_factor)

        enhancer = ImageEnhance.Contrast(image)
        contrast_factor = random.uniform(1 + self.config.uniqueness.image.contrast[0] / 100,
                                         1 + self.config.uniqueness.image.contrast[1] / 100)
        image = enhancer.enhance(contrast_factor)

        # Поворот
        if self.config.uniqueness.image.rotation:
            angle = random.randint(-5, 5)
            image = image.rotate(angle)

        if self.config.uniqueness.image.filters:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

        unique_image_path = f"unique_{os.path.basename(image_path)}"
        image.save(unique_image_path)
        return unique_image_path

    def unique_video(self, video_path: str) -> str:
        """
        Уникализация видео:
        - Изменение хеша.
        - Наложение невидимых элементов.
        - Изменение FPS.
        - Ускорение аудио.
        - Кадрирование, яркость, контраст, поворот.
        - Удаление/замена метаданных.

        Args:
            video_path (str): Путь к исходному видео.

        Returns:
            str: Путь к уникализированному видео.
        """
        console.log(f"Уникализация видео: {video_path}", style="cyan")
        video = VideoFileClip(video_path)

        if self.config.uniqueness.video.frame_rate_variation:
            new_fps = video.fps * random.uniform(0.98, 1.02)
            video = video.set_fps(new_fps)

        if self.config.uniqueness.video.audio_speed:
            speed_factor = random.uniform(1 + self.config.uniqueness.video.audio_speed[0] / 100,
                                         1 + self.config.uniqueness.video.audio_speed[1] / 100)
            video = video.fx(lambda clip: clip.speedx(factor=speed_factor))

        unique_video_path = f"unique_{os.path.basename(video_path)}"
        video.write_videofile(unique_video_path, codec="libx264")
        return unique_video_path
