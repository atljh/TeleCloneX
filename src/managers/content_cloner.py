import asyncio
import random
from typing import Dict, Optional
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import FloodWaitError
from src.logger import console, logger
from src.managers import ProxyManager, UniqueContentManager


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
        source_channel: str,
        target_channel: str,
        history_range: Optional[tuple[int, int]] = None,
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
        self.source_channel = source_channel
        self.target_channel = target_channel
        self.mode = config.cloning.mode
        self.history_range = history_range
        self.proxy_manager = ProxyManager()
        self.unique_content_manager = UniqueContentManager()
        self._running = False

    async def start(self) -> None:
        """
        Starts the cloning process based on the selected mode.
        - If mode is HISTORY, clones posts from the specified range.
        - If mode is REALTIME, monitors the source channel for new posts.
        """
        self._running = True
        if self.mode == 'history':
            await self._clone_history()
        elif self.mode == 'live':
            await self._monitor_realtime()

    async def stop(self) -> None:
        """
        Stops the cloning process.
        """
        self._running = False
        console.log("Cloning stopped.", style="yellow")

    async def _clone_history(self) -> None:
        """
        Clones content from the channel's history within the specified range.
        """
        if not self.history_range:
            raise ValueError("For HISTORY mode, a post range must be specified.")

        start, end = self.history_range
        console.log(f"Cloning posts from {start} to {end}...", style="blue")

        for account in self.accounts:
            client = TelegramClient(
                f"sessions/{account.phone}",
                account.api_id,
                account.api_hash,
                proxy=account.proxy,
            )
            await client.start(account.phone)

            try:
                async for message in client.iter_messages(self.source_channel, min_id=start, max_id=end):
                    if not self._running:
                        break
                    await self._process_message(client, message)
                    await self._random_delay(account.delay_range)
            except FloodWaitError as e:
                console.log(f"Waiting {e.seconds} seconds due to Telegram limits...", style="yellow")
                await asyncio.sleep(e.seconds)
            finally:
                await client.disconnect()

    async def _monitor_realtime(self) -> None:
        """
        Monitors the source channel for new posts and clones them in real-time.
        """
        console.log("Starting real-time monitoring...", style="blue")

        for account in self.accounts:
            client = TelegramClient(
                f"sessions/{account.phone}",
                account.api_id,
                account.api_hash,
                proxy=account.proxy,
            )
            await client.start(account.phone)

            @client.on(events.NewMessage(chats=self.source_channel))
            async def handler(event):
                if not self._running:
                    return
                await self._process_message(client, event.message)
                await self._random_delay(account.delay_range)

            console.log(f"Account {account.phone} started monitoring.", style="green")

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
            unique_content = self.unique_content_manager.make_unique(content)
            await self._publish_content(client, unique_content)
            console.log(f"Message published successfully: {message.id}", style="green")
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            console.log(f"Error processing message {message.id}: {e}", style="red")

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

    async def _publish_content(self, client: TelegramClient, content: Dict) -> None:
        """
        Publishes unique content to the target channel.

        Args:
            client (TelegramClient): The Telegram client instance.
            content (Dict): The unique content to publish.
        """
        if content.get("photo"):
            await client.send_file(self.target_channel, content["photo"], caption=content["text"])
        elif content.get("video"):
            await client.send_file(self.target_channel, content["video"], caption=content["text"])
        elif content.get("audio"):
            await client.send_file(self.target_channel, content["audio"], caption=content["text"])
        else:
            await client.send_message(self.target_channel, content["text"])

    async def _random_delay(self, delay_range: tuple[int, int]) -> None:
        """
        Introduces a random delay between sending messages.

        Args:
            delay_range (tuple[int, int]): The range of delays (in seconds).
        """
        delay = random.randint(*delay_range)
        await asyncio.sleep(delay)
