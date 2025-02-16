import asyncio
from pathlib import Path
from asyncio import Semaphore
from typing import Generator

from tooler import move_item
from src.thon import BaseSession
from src.cloner import Cloner
from src.logger import logger
from src.logger import console


class Starter(BaseSession):
    def __init__(
        self,
        threads: int,
        config
    ):
        self.semaphore = Semaphore(threads)
        self.config = config
        super().__init__()

    async def _main(
        self,
        item: Path,
        json_file: Path,
        json_data: dict,
        config
    ):
        try:
            cloner = Cloner(item, json_file, json_data, config)
            async with self.semaphore:
                try:
                    r = await cloner.main()
                except Exception as e:
                    console.log(f"Ошибка при работе аккаунта {item}: {e}", style="red")
                    r = "ERROR_UNKNOWN"
            if "ERROR_AUTH" in r:
                console.log(f"Аккаунт {item.name} разлогинен или забанен", style="red")
                move_item(item, self.banned_dir, True, True)
                move_item(json_file, self.banned_dir, True, True)
                return
            if "ERROR_STORY" in r:
                console.log(f"Ошибка при работе аккаунта {item.name}", style="red")
                move_item(item, self.errors_dir, True, True)
                move_item(json_file, self.errors_dir, True, True)
                return
            if "OK" in r:
                console.log(f"Аккаунт {item.name} закончил работу", style="green")
        except Exception as e:
            logger.error(f"Ошибка при работе акканута {item}: {e}")
            console.log(f"Ошибка при работе аккаунта {item}: {e}", style="red")

    def __get_sessions_and_users(self) -> Generator:
        for item, json_file, json_data in self.find_sessions():
            yield item, json_file, json_data

    async def main(self) -> bool:
        sessions = list(self.__get_sessions_and_users())
        if not sessions:
            console.log("Нет активных сессий. Прекращение работы.", style="yellow")
            return False
        tasks = set()
        for item, json_file, json_data in self.__get_sessions_and_users():
            tasks.add(self._main(item, json_file, json_data, self.config))
        if not tasks:
            return False
        await asyncio.gather(*tasks, return_exceptions=True)
        return True
