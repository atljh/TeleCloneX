from typing import Dict
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
            unique_content["audio"] = content["audio"]

        unique_content['is_round'] = content.get('is_round')

        return unique_content
