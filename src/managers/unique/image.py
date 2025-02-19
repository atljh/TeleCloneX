import os
import string
import random
from datetime import datetime, timedelta
from PIL import Image, ImageEnhance, ImageFilter
import piexif
from src.logger import console, logger


class ImageUniquenessManager:
    """
    Manages image uniqueness: cropping, brightness/contrast adjustment, rotation, filters, and metadata.
    """

    def __init__(self, config):
        self.config = config

    def unique_image(self, image_path: str) -> str:
        """
        Applies uniqueness transformations to an image.

        Args:
            image_path (str): Path to the input image.

        Returns:
            str: Path to the unique image.
        """
        console.log(f"Уникализация изображения: {image_path}", style="cyan")
        image = Image.open(image_path)

        # Кадрирование
        width, height = image.size
        crop_pixels = random.randint(*self.config.uniqueness.image.crop)
        image = image.crop((crop_pixels, crop_pixels, width - crop_pixels, height - crop_pixels))

        # Яркость и контраст
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
            angle = random.uniform(-0.3, 0.3)
            image = image.rotate(angle)

        # Фильтры
        if self.config.uniqueness.image.filters:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

        # Сохранение уникализированного изображения
        unique_image_path = f"unique_{os.path.basename(image_path)}"
        image.save(unique_image_path)

        # Работа с метаданными
        if self.config.uniqueness.image.metadata == "replace":
            unique_image_path = self._replace_image_metadata(unique_image_path)
        elif self.config.uniqueness.image.metadata == "remove":
            self._remove_image_metadata(unique_image_path)

        return unique_image_path

    def _replace_image_metadata(self, image_path: str) -> str:
        """
        Replaces image metadata with random data.

        Args:
            image_path (str): Path to the image.

        Returns:
            str: Path to the new image with replaced metadata.
        """
        try:
            img = Image.open(image_path)
            exif_dict = piexif.load(img.info.get("exif", b""))
            exif_dict["0th"][piexif.ImageIFD.Artist] = self._generate_random_string(10)
            exif_dict["0th"][piexif.ImageIFD.Software] = self._generate_random_string(12)
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = self._generate_random_date().strftime("%Y:%m:%d %H:%M:%S")
            exif_bytes = piexif.dump(exif_dict)

            new_file_name = self._generate_random_string(15) + ".jpg"
            new_file_path = os.path.join(os.path.dirname(image_path), new_file_name)

            img.save(new_file_path, "jpeg", exif=exif_bytes)

            random_date = self._generate_random_date()
            mod_time = random_date.timestamp()
            os.utime(new_file_path, (mod_time, mod_time))

            return new_file_path
        except Exception as e:
            logger.error(f"Ошибка при замене метаданных изображения: {e}")
            return image_path

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

    def _generate_random_string(self, length: int = 8) -> str:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def _generate_random_date(self):
        """Generates a random date within the last year."""
        start_date = datetime.now() - timedelta(days=365)
        random_date = start_date + timedelta(days=random.randint(0, 365))
        return random_date
