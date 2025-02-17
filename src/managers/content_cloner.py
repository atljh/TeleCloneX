import asyncio
import random
from typing import Dict, List
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import FloodWaitError
from src.logger import console, logger
from src.managers import FileManager


class ContentCloner:
    """
    A class for cloning content from Telegram channels, including text, images, videos, and audio.
    The content is then made unique and published to target channels. The program supports two modes:
    - Cloning from channel history.
    - Real-time monitoring and cloning.

    The program operates in a multi-threaded manner, with configurable delays and proxy settings for each account.
    """

    def __init__(
        self,
        config,
        client: TelegramClient,
        account_phone: str,
    ):
        """
        Initializes the ContentCloner.

        Args:
            source_channel (str): The source channel link (donor channel).
            target_channel (str): The target channel link where content will be published.
            accounts (List[AccountConfig]): List of accounts to use for cloning.
            mode (CloneMode): The cloning mode (HISTORY or REALTIME).
            history_range (Optional[tuple[int, int]]): The range of posts to clone (only for HISTORY mode).
        """
        self.config = config
        self.client = client
        self.account_phone = account_phone
        self.source_channels = FileManager._read_file(
            config.cloning.source_channels_file
        )
        self.target_channels = self.get_target_channels()
        self.mode = config.cloning.mode
        self.post_delay = config.timeouts.post_delay
        self.history_range = config.cloning.post_range
        # self.unique_content_manager = UniqueContentManager()
        self._running = False

    def get_target_channels(self) -> List[str]:
        target_channels = []
        all_target_channels = FileManager._read_file(
            self.config.cloning.target_channels_file
        )
        for channel in all_target_channels:
            if channel.split(' ')[1] == self.account_phone:
                target_channels.append(channel.split(' ')[0])
        return target_channels

    async def start(self) -> None:
        if not self.target_channels or not self.source_channels:
            console.print(
                f"{self.account_phone} | Не найдены целевые каналы для аккаунта",
                style="red"
            )
            return
        self._running = True
        if self.mode == 'history':
            await self._clone_history(self.client)
        elif self.mode == 'live':
            await self._monitor_realtime(self.client)

    async def stop(self) -> None:
        self._running = False
        console.log("Клонирование остановлено", style="yellow")

    async def _clone_history(self, client: TelegramClient) -> None:
        if not self.history_range:
            raise ValueError("Для режима работы по истории канала должнен быть указан диапазон постов")

        start, end = self.history_range
        console.log(f"Клонирование постов от {start} до {end}...", style="blue")
        for channel in self.source_channels:
            try:
                async for message in client.iter_messages(channel, min_id=start, max_id=end):
                    if not self._running:
                        break
                    await self._process_message(client, message)
                    await self._random_delay(self.post_delay)
            except FloodWaitError as e:
                console.log(f"Waiting {e.seconds} seconds due to Telegram limits...", style="yellow")
                await asyncio.sleep(e.seconds)

    async def _monitor_realtime(self, client: TelegramClient) -> None:
        """
        Monitors the source channel for new posts and clones them in real-time.
        """
        console.log("Starting real-time monitoring...", style="blue")

        @client.on(events.NewMessage(chats=self.source_channels))
        async def handler(event):
            if not self._running:
                return
            await self._process_message(client, event.message)
            await self._random_delay(self.post_delay)

        while self._running:
            await asyncio.sleep(1)

    async def _process_message(self, client: TelegramClient, message) -> None:
        """
        Processes a message: extracts content, makes it unique, and publishes it to the target channel.

        Args:
            client (TelegramClient): The Telegram client instance.
            message: The message to process.
        """
        try:
            content = await self._extract_content(message)
            console.log(content)
            # unique_content = self.unique_content_manager.make_unique(content)
            for channel in self.target_channels:
                await self._publish_content(client, content, channel)
            console.log(f"Сообщение опубликовано: {message.id}", style="green")
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")

    async def _extract_content(self, message) -> Dict:
        """
        Extracts content (text, images, videos, audio) from a message.

        Args:
            message: The message to extract content from.

        Returns:
            Dict: A dictionary containing the extracted content.
        """
        content = {"text": message.text or ""}

        if message.media:
            if isinstance(message.media, MessageMediaPhoto):
                content["photo"] = await message.download_media(file="downloads/")
            elif isinstance(message.media, MessageMediaDocument):
                if message.document.mime_type.startswith("video"):
                    content["video"] = await message.download_media(file="downloads/")
                elif message.document.mime_type.startswith("audio"):
                    content["audio"] = await message.download_media(file="downloads/")

        return content

    async def _publish_content(
        self,
        client: TelegramClient,
        content: Dict,
        target_channel: str
    ) -> None:
        """
        Publishes unique content to the target channel.

        Args:
            client (TelegramClient): The Telegram client instance.
            content (Dict): The unique content to publish.
        """
        if content.get("photo"):
            await client.send_file(target_channel, content["photo"], caption=content["text"])
        elif content.get("video"):
            await client.send_file(target_channel, content["video"], caption=content["text"])
        elif content.get("audio"):
            await client.send_file(target_channel, content["audio"], caption=content["text"])
        else:
            await client.send_message(target_channel, content["text"])

    async def _random_delay(self, delay_range: tuple[int, int]) -> None:
        """
        Introduces a random delay between sending messages.

        Args:
            delay_range (tuple[int, int]): The range of delays (in seconds).
        """
        delay = random.randint(*delay_range)
        await asyncio.sleep(delay)
