from src.managers.unique import (
    TextUniquenessManager, ImageUniquenessManager, VideoUniquenessManager
)


class UniqueManager:
    """
    Manages content uniqueness: text, images, and videos.
    """

    def __init__(self, config, account_phone: str):
        self.config = config
        self.account_phone = account_phone
        self.text_manager = TextUniquenessManager(config, account_phone)
        self.image_manager = ImageUniquenessManager(config)
        self.video_manager = VideoUniquenessManager(config)

    async def unique_text(self, text: str) -> str:
        """
        Applies text uniqueness transformations.

        Args:
            text (str): Input text.

        Returns:
            str: Unique text.
        """
        return await self.text_manager.unique_text(text)

    def unique_image(self, image_path: str) -> str:
        """
        Applies image uniqueness transformations.

        Args:
            image_path (str): Path to the input image.

        Returns:
            str: Path to the unique image.
        """
        return self.image_manager.unique_image(image_path)

    def unique_video(self, video_path: str) -> str:
        """
        Applies video uniqueness transformations.

        Args:
            video_path (str): Path to the input video.

        Returns:
            str: Path to the unique video.
        """
        return self.video_manager.unique_video(video_path)
