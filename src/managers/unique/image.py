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
            unique_image_path = self._replace_image_metadata(unique_image_path)
        elif self.config.uniqueness.image.metadata == "remove":
            self._remove_image_metadata(unique_image_path)

        return unique_image_path

    def _replace_image_metadata(self, image_path: str) -> str:
        """
        Заменяет метаданные изображения на случайные значения и перезаписывает исходное изображение.

        Args:
            image_path (str): Путь к изображению.

        Returns:
            str: Путь к обновленному изображению.
        """
        try:
            metadata = self.generate_random_metadata()

            image = Image.open(image_path)

            exif_dict = {
                "0th": {},
                "Exif": {},
                "GPS": {},
                "1st": {},
                "thumbnail": None,
            }

            exif_dict["0th"][piexif.ImageIFD.Make] = metadata["Make"].encode("utf-8")
            exif_dict["0th"][piexif.ImageIFD.Model] = metadata["Model"].encode("utf-8")
            exif_dict["Exif"][piexif.ExifIFD.BodySerialNumber] = metadata["SerialNumber"].encode("utf-8")

            exif_bytes = piexif.dump(exif_dict)

            image.save(image_path, "jpeg", exif=exif_bytes, quality=95)

            return image_path
        except Exception as e:
            logger.error(f"Ошибка при замене метаданных изображения: {e}")
            raise

    def _remove_image_metadata(self, image_path: str) -> None:
        """
        Removes metadata from an image.

        Args:
            image_path (str): Path to the image.
        """
        try:
            img = Image.open(image_path)

            if "exif" not in img.info:
                return

            piexif.remove(image_path)
            console.print(f"Метаданные изображения {image_path} удалены.", style="green")
        except Exception as e:
            logger.error(f"Ошибка при удалении метаданных изображения: {e}")

    def generate_random_metadata(self):
        """
        Generates random metadata for Make, Model, and SerialNumber.

        Returns:
            dict: A dictionary containing random values for Make, Model, and SerialNumber.
        """
        make = random.choice(["Canon", "Nikon", "Sony", "Fujifilm", "Panasonic", "Olympus", "Leica", "Pentax"])
        model = f"{make} Model-{random.randint(100, 999)}"
        serial_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        return {"Make": make, "Model": model, "SerialNumber": serial_number}

    def _generate_random_string(self, length: int = 8) -> str:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def _generate_random_date(self):
        """Generates a random date within the last year."""
        start_date = datetime.now() - timedelta(days=365)
        random_date = start_date + timedelta(days=random.randint(0, 365))
        return random_date
