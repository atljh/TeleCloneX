import os
import random
from typing import Dict
import piexif
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import subprocess

from PIL import Image, ImageEnhance, ImageFilter
from moviepy.editor import VideoFileClip
from src.logger import console, logger
from src.chatgpt import ChatGPTClient


class UniqueManager:
    """
    A class for content uniqueness management: text, images, and videos.
    """
    def __init__(self, config, account_phone: str):
        self.config = config
        self.account_phone = account_phone
        self.chatgpt_client = ChatGPTClient(config)
        self.replacements = self._load_replacements(config.uniqueness.text.replacements_file)

    def _load_replacements(self, replacements_file: str) -> Dict[str, str]:
        """
        Loads word replacement rules from a file.

        Args:
            replacements_file (str): Path to the file with replacement rules.

        Returns:
            Dict[str, str]: Dictionary with replacement rules.
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

    async def unique_text(self, text: str) -> str:
        """
        Text uniqueness:
        - Replace words according to rules.
        - Mask characters with RU-EN substitutions.
        - Rewrite text using ChatGPT (if enabled).

        Args:
            text (str): Input text.

        Returns:
            str: Unique text.
        """
        for original, replacement in self.replacements.items():
            text = text.replace(original, replacement)

        if self.config.uniqueness.text.symbol_masking:
            text = self._mask_characters(text)

        if self.config.uniqueness.text.rewrite:
            text = await self._rewrite_with_chatgpt(text)

        return text

    def _mask_characters(self, text: str) -> str:
        """
        Masks similar characters using RU-EN substitutions.

        Args:
            text (str): Input text.

        Returns:
            str: Text with substituted characters.
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

    async def _rewrite_with_chatgpt(self, text: str) -> str:
        """
        Rewrites text using ChatGPT.

        Args:
            text (str): Input text.

        Returns:
            str: Rewritten text.
        """
        console.log("Рерайт текста через ChatGPT...", style="cyan")
        if len(text) < 10:
            return text
        response = await self.chatgpt_client.rewrite(text)
        return response

    def unique_image(self, image_path: str) -> str:
        """
        Image uniqueness:
        - Cropping.
        - Adjusting brightness and contrast.
        - Rotation.
        - Removing/replacing metadata.
        - Adding filters.

        Args:
            image_path (str): Path to the input image.

        Returns:
            str: Path to the unique image.
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

        if self.config.uniqueness.image.rotation:
            angle = random.uniform(-0.3, 0.3)
            image = image.rotate(angle)

        if self.config.uniqueness.image.filters:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

        unique_image_path = f"unique_{os.path.basename(image_path)}"
        image.save(unique_image_path)

        if self.config.uniqueness.image.metadata == "replace":
            self._replace_image_metadata(unique_image_path)
        elif self.config.uniqueness.image.metadata == "remove":
            self._remove_image_metadata(unique_image_path)

        return unique_image_path

    def _replace_image_metadata(self, image_path: str) -> None:
        """
        Replaces image metadata with custom data.

        Args:
            image_path (str): Path to the image.
        """
        try:
            exif_dict = piexif.load(image_path)
            exif_dict["0th"][piexif.ImageIFD.Artist] = "UniqueManager"
            exif_dict["0th"][piexif.ImageIFD.Software] = "ContentCloner"
            piexif.insert(piexif.dump(exif_dict), image_path)
            console.print(f"Метаданные изображения {image_path} заменены.", style="green")
        except Exception as e:
            logger.error(f"Ошибка при замене метаданных изображения: {e}")
            console.print(f"Ошибка при замене метаданных изображения: {e}", style="red")

    def _remove_image_metadata(self, image_path: str) -> None:
        """
        Removes metadata from an image.

        Args:
            image_path (str): Path to the image.
        """
        try:
            piexif.remove(image_path)
            console.print(f"Метаданные изображения {image_path} удалены.", style="green")
        except Exception as e:
            logger.error(f"Ошибка при удалении метаданных изображения: {e}")
            console.print(f"Ошибка при удалении метаданных изображения: {e}", style="red")

    def unique_video(self, video_path: str) -> str:
        """
        Video uniqueness:
        - Changing hash.
        - Adding invisible elements.
        - Adjusting FPS.
        - Modifying audio speed.
        - Cropping, brightness, contrast, rotation.
        - Removing/replacing metadata.

        Args:
            video_path (str): Path to the input video.

        Returns:
            str: Path to the unique video.
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

        if self.config.uniqueness.video.metadata == "replace":
            self._replace_video_metadata(unique_video_path)
        elif self.config.uniqueness.video.metadata == "remove":
            self._remove_video_metadata(unique_video_path)

        return unique_video_path

    def _replace_video_metadata(self, video_path: str) -> None:
        """
        Replaces video metadata with custom data.

        Args:
            video_path (str): Path to the video.
        """
        try:
            command = [
                "ffmpeg",
                "-i", video_path,
                "-metadata", "artist=UniqueManager",
                "-metadata", "software=ContentCloner",
                "-c", "copy",
                f"temp_{video_path}"
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
