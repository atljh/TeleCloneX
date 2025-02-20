import os
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from config import Config
from src.thon import BaseThon
from src.managers import (
    ChatJoiner, FileManager,
    JoinStatus, BlackList
)
from src.managers import ContentCloner
from src.logger import logger, console


class Cloner(BaseThon):
    """
    A class responsible for managing the joining and monitoring of Telegram chats for a specific account.

    Attributes:
        item (Path): The path to the session file for the account.
        config (Config): Configuration settings for the application.
        json_file (Path): The path to the JSON file containing account data.
        blacklist (BlackList): An instance of the BlackList class to manage blacklisted chats.
        file_manager (FileManager): An instance of the FileManager class to handle file operations.
        chat_joiner (ChatJoiner): An instance of the ChatJoiner class to manage joining chats.
        chat_manager (ChatManager): An instance of the ChatManager class to monitor chats.
        account_phone (str): The phone number of the account derived from the session file name.
        chats (list): A list of chats the account has joined or is monitoring.
    """

    def __init__(
        self,
        item: Path,
        json_file: Path,
        json_data: dict,
        config: Config,
    ):
        """
        Initializes the Chatter class with the necessary configurations and instances.

        Args:
            item (Path): The path to the session file for the account.
            json_file (Path): The path to the JSON file containing account data.
            json_data (dict): The data loaded from the JSON file.
            config (Config): Configuration settings for the application.
        """
        super().__init__(
            item=item,
            json_data=json_data
        )
        self.item = item
        self.config = config
        self.json_file = json_file
        self.blacklist = BlackList()
        self.file_manager = FileManager()
        self.chat_joiner = ChatJoiner(config)
        self.account_phone = os.path.basename(self.item).split('.')[0]
        self.content_cloner = ContentCloner(
            config, self.client, self.account_phone
        )
        self.source_channels = config.cloning.source_channels_file
        self.target_channels = config.cloning.target_channels_file
        self.channels = []

    async def _start(self):
        """
        Starts the process of joining and monitoring chats for the account.

        Returns:
            bool: The status of the chat handler after starting.
        """
        console.log(
            f"Аккаунт {self.account_phone} начал работу",
        )
        result = await self._join_channels()
        if not result:
            return
        handler_status = await self._start_chat_handler()
        return handler_status

    async def _join_channels(self) -> None:
        """
        Joins the chats listed in the chats file, skipping blacklisted chats.
        """
        channels = self.file_manager.read_chats(file='Источники.txt')
        for chat in channels:
            if self.blacklist.is_chat_blacklisted(
                self.account_phone, chat
            ):
                console.log(f"Чат {chat} в черном списке, пропускаем")
                continue
            join_status = await self.chat_joiner.join(
                self.client, self.account_phone, chat
            )
            result = await self._handle_join_status(
                join_status, self.client, self.account_phone, chat
            )
            if not result:
                return result
        return result

    async def _handle_join_status(
        self,
        join_status: JoinStatus,
        client: TelegramClient,
        account_phone: str,
        chat: str
    ) -> bool:
        """
        Handles the status after attempting to join a chat.

        Args:
            status (JoinStatus): The status of the join attempt.
            account_phone (str): The phone number of the account.
            chat (str): The name or identifier of the chat.
        """
        match join_status:
            case JoinStatus.OK:
                console.log(
                    f"Аккаунт {account_phone} успешно вступил в {chat}",
                    style="green"
                )
                self.channels.append(chat)
            case JoinStatus.SKIP:
                console.log(
                    f"Ссылка на чат {chat} не рабочая или такого чата не существует",
                    style="yellow"
                )
            case JoinStatus.BANNED:
                console.log(
                    f"Аккаунт {account_phone} забанен в чате {chat}, или ссылка не действительная",
                    style="yellow"
                )
                self.blacklist.add_to_blacklist(account_phone, chat)
            case JoinStatus.FLOOD:
                # mute_seconds = await self.check_flood_wait(client)
                console.print(
                    f"{account_phone} | Флуд, приостанавливаем работу",
                    style="yellow"
                )
                return False
                # if not mute_seconds:
                #     return True
                # flood_limit = self.config.timeouts.flood_wait_limit
                # if mute_seconds:
                #     if mute_seconds <= flood_limit:
                #         console.print(
                #             f"{account_phone} | Флуд {mute_seconds} секунд, делаем паузу...",
                #             style="yellow"
                #         )
                #         await asyncio.sleep(mute_seconds)
                #     else:
                #         console.print(
                #             f"{account_phone} | Флуд {mute_seconds} секунд, приостанавливаем работу",
                #             style="yellow"
                #         )
                #         return False
            case JoinStatus.ALREADY_JOINED:
                console.log(
                    f"Аккаунт {account_phone} уже состоит в чате {chat}",
                    style="green"
                )
                self.channels.append(chat)
            case JoinStatus.REQUEST_SEND:
                console.log(
                    f"Заявка на подписку в чат {chat} уже отправлена",
                    style="yellow"
                )
            case JoinStatus.ERROR:
                console.log(
                    f"Произошла ошибка при вступлении в чат {chat}, {account_phone}",
                    style="red"
                )
            case JoinStatus.OPEN_CHANNEL:
                self.channels.append(chat)
            case _:
                logger.error(f"Unknown JoinStatus: {join_status}")
                console.log(f"Неизвестный статус: {join_status}")
        return True

    async def _start_chat_handler(self) -> bool:
        """
        Starts monitoring the chats the account has joined.

        Returns:
            bool: True if monitoring started successfully, False otherwise.
        """
        if not len(self.channels):
            console.log("Нет каналов для обработки", style="red")
            return False
        console.log(
            f"Мониторинг каналов начат для аккаунта {self.account_phone}",
        )
        await self.content_cloner.start()

    async def check_flood_wait(self, client: TelegramClient):
        try:
            me = await client.get_me()
        except FloodWaitError as e:
            print(f"Flood wait detected: {e.seconds} seconds remaining")
            return e.seconds
        except Exception as e:
            print(e)
            return None
        return None

    async def _main(self) -> str:
        """
        Main method to check the account status and start the chat joining and monitoring process.

        Returns:
            str: The result of the account status check.
        """
        r = await self.check()
        if "OK" not in r:
            return r
        await self._start()
        return r

    async def main(self) -> str:
        """
        Public method to execute the main functionality of the Chatter class.

        Returns:
            str: The result of the account status check.
        """
        r = await self._main()
        return r
