import os
import asyncio
import random
from collections import deque
from typing import Dict, List
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument, DocumentAttributeVideo
)
from telethon.errors import FloodWaitError
from src.logger import console, logger
from src.managers import FileManager
from src.managers.unique_manager import UniqueManager


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
        self.unique_manager = UniqueManager(config, self.account_phone)
        self.processed_albums = deque(maxlen=500)
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
            await self._clone_history(self.client)
        elif self.mode == 'live':
            await self._monitor_realtime(self.client)
        else:
            console.print(f"Неизвестный режим работы: {self.mode}", style="red")

    async def stop(self) -> None:
        self._running = False
        console.print("Клонирование остановлено", style="yellow")

    async def _check_channel_access(self, client: TelegramClient, channel: str) -> bool:
        """
        Checks if the channel is accessible.

        Args:
            client (TelethonClient): The Telegram client instance.
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
                console.print(f"Канал {channel} недоступен. Пропускаем.", style="yellow")
                continue

            console.print(f"Клонирование последних {self.posts_to_clone} постов (от старых к новым) в канале {channel}", style="blue")
            try:
                messages = []
                async for message in client.iter_messages(channel, limit=self.posts_to_clone):
                    messages.append(message)

                messages.reverse()

                for message in messages:
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
        console.print(f"{self.account_phone} | Запущено клонирование с каналов в реальном времени", style="blue")

        @client.on(events.NewMessage(chats=self.source_channels))
        async def handler(event):
            if not self._running:
                return
            if event.grouped_id:
                if event.grouped_id in self.processed_albums:
                    return
                self.processed_albums.append(event.grouped_id)
                await self._process_album(client, event.message)
                await self._random_delay(self.post_delay)
            else:
                await self._process_message(client, event.message)
                await self._random_delay(self.post_delay)

        while self._running:
            await asyncio.sleep(1)

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

    async def _make_content_unique(self, content: Dict) -> Dict:
        """
        Unuqie message content

        Args:
            content (Dict): Original content.

        Returns:
            Dict: Uniquiezed content.
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

    async def _process_message(self, client: TelegramClient, message) -> None:
        """
        Processes a message: extracts content, makes it unique, and publishes it to the target channel.
        Supports albums (groups of media files).

        Args:
            client (TelegramClient): The Telegram client instance.
            message: The message to process.
        """
        try:
            if message.grouped_id:
                console.print(
                    style="blue"
                )
                await self._process_album(client, message)
            else:
                await self._process_single_message(client, message)
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            console.print(f"Ошибка при обработке сообщения: {e}", style="red")

    async def _process_single_message(self, client: TelegramClient, message):
        content = await self._extract_content(message)
        if not content.get("text") and not any(key in content for key in ["photo", "video", "audio"]):
            console.print("Сообщение пустое. Пропускаем.", style="yellow")
            return

        for channel in self.target_channels:
            if not await self._check_channel_access(client, channel):
                console.print(f"Канал {channel} недоступен. Пропускаем.", style="yellow")
                continue

            unique_content = await self._make_content_unique(content)

            result = await self._publish_content(client, unique_content, channel)
            if result:
                console.print(f"Сообщение опубликовано в канал {channel}", style="green")

    async def _process_album(self, client: TelegramClient, message) -> None:
        """
        Processes an album of messages (grouped media files).
        """
        try:
            all_messages = []
            async for msg in client.iter_messages(
                message.chat_id,
                limit=20
            ):
                all_messages.append(msg)

            album_messages = [msg for msg in all_messages if msg.grouped_id == message.grouped_id]
            album_messages.reverse()
            if not album_messages:
                console.print(f"Не удалось найти сообщения альбома с grouped_id: {message.grouped_id}", style="yellow")
                return
            console.print(f"Найден альбом из {len(album_messages)} сообщений.", style="blue")

            unique_contents = []
            for msg in album_messages:
                content = await self._extract_content(msg)
                unique_content = await self._make_content_unique(content)
                unique_contents.append(unique_content)
            for channel in self.target_channels:
                if not await self._check_channel_access(client, channel):
                    console.print(f"Канал {channel} недоступен. Пропускаем.", style="yellow")
                    continue

                await self._publish_album(client, unique_contents, channel)
                console.print(f"Альбом опубликован в канал {channel}", style="green")
        except Exception as e:
            logger.error(f"Ошибка при обработке альбома: {e}")

    async def _publish_content(
        self,
        client: TelegramClient,
        content: Dict,
        target_channel: str
    ) -> bool:
        """
        Publishes unique content to the target channel.

        Args:
            client (TelethonClient): The Telegram client instance.
            content (Dict): The unique content to publish.
        """
        try:
            if not content.get("text") and not any(key in content for key in ["photo", "video", "audio", "video_note"]):
                console.print(f"Пустой контент. Пропускаем публикацию в канал {target_channel}", style="yellow")
                return
            caption = content.get("text", "")
            if len(caption) > 1024:
                caption = caption[:1021] + "..."

            if content.get("photo"):
                await client.send_file(target_channel, content["photo"], caption=caption)
                self._delete_file(content["photo"])
            elif content.get("video"):
                if content.get("is_round"):
                    await client.send_file(target_channel, content["video"], video_note=True)
                    self._delete_file(content["video"])
                else:
                    await client.send_file(target_channel, content["video"], caption=caption)
                    self._delete_file(content["video"])
            elif content.get("audio"):
                await client.send_file(target_channel, content["audio"], caption=caption)
                self._delete_file(content["audio"])
            elif content.get("video_note"):
                await client.send_file(target_channel, content["video_note"], video_note=True)
                self._delete_file(content["video_note"])
            else:
                await client.send_message(target_channel, caption)
            return True
        except Exception as e:
            if "You can't write" in str(e):
                logger.error(f"{self.account_phone} | Не может публиковать в канал {target_channel}")
                return False
            logger.error(f"Ошибка при публикации контента в канал {target_channel}: {e}")
            return False

    async def _publish_album(self, client: TelegramClient, album_contents: List[Dict], channel: str) -> None:
        """
        Publishes an album of media files to the target channel.

        Args:
            client (TelegramClient): The Telegram client instance.
            album_contents (List[Dict]): List of unique content dictionaries.
            channel (str): The target channel.
        """
        try:
            files = []
            captions = []
            for content in album_contents:

                if content.get("photo"):
                    files.append(content["photo"])
                    captions.append(content.get("text", ""))
                elif content.get("video"):
                    files.append(content["video"])
                    captions.append(content.get("text", ""))
                elif content.get("audio"):
                    files.append(content["audio"])
                    captions.append(content.get("text", ""))
            caption = ''.join(captions)
            await client.send_file(channel, files, caption=caption)
            console.print(f"Альбом из {len(files)} файлов опубликован в канал {channel}.", style="green")

            for file in files:
                self._delete_file(file)
        except Exception as e:
            logger.error(f"Ошибка при публикации альбома: {e}")

    def _delete_file(self, file_path: str) -> None:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                console.print(f"Файл {file_path} удален.", style="green")
            else:
                console.print(f"Файл {file_path} не найден.", style="yellow")
            original_file = f'downloads/{file_path.replace("unique_", "")}'
            if os.path.exists(original_file):
                os.remove(original_file)
                console.print(f"Файл {original_file} удален.", style="green")
            else:
                console.print(f"Файл {original_file} не найден.", style="yellow")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {file_path}: {e}")

    async def _random_delay(self, delay_range: tuple[int, int]) -> None:
        delay = random.randint(*delay_range)
        console.print(f"Задержка {delay} секунд", style="yellow")
        await asyncio.sleep(delay)
