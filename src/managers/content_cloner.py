import asyncio
import random
from collections import deque
from typing import List
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from src.logger import console, logger
from src.managers import FileManager
from src.managers.unique_manager import UniqueManager
from src.managers.clone import (
    ContentExtractor, ContentPublisher, ContentUniquifier
)

class ContentCloner:
    """
    Основной класс, управляющий процессом клонирования.
    """

    def __init__(
        self,
        config,
        client: TelegramClient,
        account_phone: str,
    ):
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

        self.content_extractor = ContentExtractor()
        self.content_uniquifier = ContentUniquifier(self.unique_manager)
        self.content_publisher = ContentPublisher(self.client)

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
            await self._clone_history()
        elif self.mode == 'live':
            await self._monitor_realtime()
        else:
            console.print(f"Неизвестный режим работы: {self.mode}", style="red")

    async def stop(self) -> None:
        self._running = False
        console.print("Клонирование остановлено", style="yellow")

    async def _check_channel_access(self, channel: str) -> bool:
        """
        Проверяет доступность канала.

        Args:
            channel (str): Имя или ссылка на канал.

        Returns:
            bool: True, если канал доступен, иначе False.
        """
        try:
            await self.client.get_entity(channel)
            return True
        except Exception as e:
            logger.error(f"Канал {channel} недоступен: {e}")
            console.print(f"Канал {channel} недоступен: {e}", style="red")
            return False

    async def _clone_history(self) -> None:
        if not self.posts_to_clone:
            raise ValueError("Для режима работы по истории канала должно быть указано количество постов")

        for channel in self.source_channels:
            if not await self._check_channel_access(channel):
                console.print(f"Канал {channel} недоступен. Пропускаем.", style="yellow")
                continue

            console.print(f"Клонирование последних {self.posts_to_clone} постов (от старых к новым) в канале {channel}", style="blue")
            try:
                messages = []
                async for message in self.client.iter_messages(channel, limit=self.posts_to_clone):
                    messages.append(message)

                messages.reverse()

                for message in messages:
                    if not self._running:
                        break
                    if message.grouped_id and message.grouped_id in self.processed_albums:
                        continue

                    await self._process_message(message)

                    if message.grouped_id:
                        self.processed_albums.append(message.grouped_id)

                    await self._random_delay(self.post_delay)
            except FloodWaitError as e:
                console.print(f"Лимиты превышены. Ожидание {e.seconds} секунд...", style="yellow")
                await asyncio.sleep(e.seconds)

    async def _monitor_realtime(self) -> None:
        """
        Мониторит исходный канал на новые посты и клонирует их в реальном времени.
        """
        console.print(f"{self.account_phone} | Запущено клонирование с каналов в реальном времени", style="blue")

        self.message_queue = asyncio.Queue()

        @self.client.on(events.NewMessage(chats=self.source_channels))
        async def handler(event):
            if not self._running:
                return
            await self.message_queue.put(event)

        asyncio.create_task(self._process_message_queue())

        while self._running:
            await asyncio.sleep(1)

    async def _process_message_queue(self) -> None:
        """
        Обрабатывает сообщения из очереди с задержкой между ними.
        """
        while self._running:
            event = await self.message_queue.get()

            if event.grouped_id:
                if event.grouped_id in self.processed_albums:
                    continue
                self.processed_albums.append(event.grouped_id)
                await self._process_album(event.message)
            else:
                await self._process_message(event.message)

            await self._random_delay(self.post_delay)

            self.message_queue.task_done()

    async def _process_message(self, message) -> None:
        """
        Обрабатывает сообщение: извлекает контент, уникализирует его и публикует в целевой канал.
        Поддерживает альбомы (группы медиафайлов).

        Args:
            message: Сообщение для обработки.
        """
        try:
            if message.grouped_id:
                await self._process_album(message)
            else:
                await self._process_single_message(message)
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            console.print(f"Ошибка при обработке сообщения: {e}", style="red")

    async def _process_single_message(self, message):
        content = await self.content_extractor.extract_content(message)
        if not content.get("text") and not any(key in content for key in ["photo", "video", "audio"]):
            console.print("Сообщение пустое. Пропускаем.", style="yellow")
            return

        for channel in self.target_channels:
            if not await self._check_channel_access(channel):
                console.print(f"Канал {channel} недоступен. Пропускаем.", style="yellow")
                continue

            unique_content = await self.content_uniquifier.make_content_unique(content)

            result = await self.content_publisher.publish_content(unique_content, channel)
            if result:
                console.print(f"Сообщение опубликовано в канал {channel}", style="green")

    async def _process_album(self, message) -> None:
        """
        Обрабатывает альбом сообщений (группу медиафайлов).
        """
        try:
            all_messages = []
            async for msg in self.client.iter_messages(
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
                content = await self.content_extractor.extract_content(msg)
                unique_content = await self.content_uniquifier.make_content_unique(content)
                unique_contents.append(unique_content)
            for channel in self.target_channels:
                if not await self._check_channel_access(channel):
                    console.print(f"Канал {channel} недоступен. Пропускаем.", style="yellow")
                    continue

                await self.content_publisher.publish_album(unique_contents, channel)
                console.print(f"Альбом опубликован в канал {channel}", style="green")
        except Exception as e:
            logger.error(f"Ошибка при обработке альбома: {e}")

    async def _random_delay(self, delay_range: tuple[int, int]) -> None:
        delay = random.randint(*delay_range)
        console.print(f"Задержка {delay} секунд", style="yellow")
        await asyncio.sleep(delay)