from typing import Dict
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument, DocumentAttributeVideo
)


class ContentExtractor:
    """
    Отвечает за извлечение контента из сообщений.
    """

    async def extract_content(self, message) -> Dict:
        """
        Извлекает контент (текст, изображения, видео, аудио) из сообщения.

        Args:
            message: Сообщение для извлечения контента.

        Returns:
            Dict: Словарь с извлеченным контентом.
        """
        content = {"text": message.text or ""}
        if message.media:
            if isinstance(message.media, MessageMediaPhoto):
                content["photo"] = await message.download_media(file="downloads/")
            elif isinstance(message.media, MessageMediaDocument):
                document = message.media.document
                for attr in document.attributes:
                    if isinstance(attr, DocumentAttributeVideo) and attr.round_message:
                        content["video"] = await message.download_media(file="downloads/")
                        content["is_round"] = True
                        break
                else:
                    if document.mime_type.startswith("video"):
                        content["video"] = await message.download_media(file="downloads/")
                    elif document.mime_type.startswith("audio"):
                        content["audio"] = await message.download_media(file="downloads/")

        return content
