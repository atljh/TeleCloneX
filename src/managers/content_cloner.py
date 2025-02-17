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
            config: Configuration object.
            client (TelegramClient): The Telegram client instance.
            account_phone (str): The phone number of the account.
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
        self.posts_to_clone = config.cloning.posts_to_clone
        self._running = False

    def get_target_channels(self) -> List[str]:
        target_channels = []
        all_target_channels = FileManager._read_file(
            self.config.cloning.target_channels_file
        )
        for channel in all_target_channels:
            if channel.split(' ')[1] == self.account_phone:
                target_channels.append(channel.split(' ')[0])

        if not target_channels:
            console.print(
                f"{self.account_phone} | Не найдены целевые каналы для аккаунта",
                style="red"
            )
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
            return await self._clone_history(self.client)
        elif self.mode == 'live':
            return await self._monitor_realtime(self.client)

    async def stop(self) -> None:
        self._running = False
        console.print("Клонирование остановлено", style="yellow")

    async def _check_channel_access(self, client: TelegramClient, channel: str) -> bool:
        """
        Checks if the channel is accessible.

        Args:
            client (TelegramClient): The Telegram client instance.
            channel (str): The channel name or link.

        Returns:
            bool: True if the channel is accessible, otherwise False.
        """
        try:
            await client.get_entity(channel)
            return True
        except Exception as e:
            logger.error(f"Канал {channel} недоступен: {e}")
            console.print(f"Канал {channel} недоступен: {e}", style="red")
            return False

    async def _clone_history(self, client: TelegramClient) -> None:
        if not self.posts_to_clone:
            raise ValueError("Для режима работы по истории канала должно быть указано количество постов")

        for channel in self.source_channels:
            if not await self._check_channel_access(client, channel):
                continue
            console.print(f"Клонирование последних {self.posts_to_clone} постов в канале {channel}...", style="blue")
            try:
                async for message in client.iter_messages(channel, limit=self.posts_to_clone):
                    if not self._running:
                        break
                    await self._process_message(client, message)
                    await self._random_delay(self.post_delay)
            except FloodWaitError as e:
                console.print(f"Лимиты превышены. Ожидание {e.seconds} секунд...", style="yellow")
                await asyncio.sleep(e.seconds)

    async def _monitor_realtime(self, client: TelegramClient) -> None:
        """
        Monitors the source channel for new posts and clones them in real-time.
        """
        console.print("Запущено клонирование с каналов в реальном времени...", style="blue")

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
            # unique_content = self.unique_content_manager.make_unique(content)
            for channel in self.target_channels:
                if not await self._check_channel_access(client, channel):
                    continue
                await self._publish_content(client, content, channel)
                console.print(f"Сообщение {message.id} опубликовано в канал {channel}", style="green")
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения {message.id}: {e}")
            console.print(f"Ошибка при обработке сообщения {message.id}: {e}", style="red")

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
        try:
            caption = content.get("text", "")
            if len(caption) > 1024:
                caption = caption[:1021] + "..."

            if content.get("photo"):
                await client.send_file(target_channel, content["photo"], caption=caption)
            elif content.get("video"):
                await client.send_file(target_channel, content["video"], caption=caption)
            elif content.get("audio"):
                await client.send_file(target_channel, content["audio"], caption=caption)
            else:
                await client.send_message(target_channel, caption)
        except Exception as e:
            logger.error(f"Ошибка при публикации контента в канал {target_channel}: {e}")
            console.print(f"Ошибка при публикации контента в канал {target_channel}: {e}", style="red")

    async def _random_delay(self, delay_range: tuple[int, int]) -> None:
        """
        Introduces a random delay between sending messages.

        Args:
            delay_range (tuple[int, int]): The range of delays (in seconds).
        """
        delay = random.randint(*delay_range)
        await asyncio.sleep(delay)
