import sys
import asyncio
import requests
from random import choice
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

from jsoner import json_write_sync
from tooler import ProxyParser
from src.logger import console
from src.thon.base_session import BaseSession
from src.managers import FileManager


class JsonConverter(BaseSession):
    def __init__(self, config):
        super().__init__()
        self.__api_id, self.__api_hash = 2040, "b18441a1ff607e10a989891a5462e627"
        self.config = config
        proxy_enabled = self.config.telegram.proxy.enabled
        proxy_file = self.config.telegram.proxy.file
        if proxy_enabled == 'Без прокси':
            self.__proxy = None
            return
        try:
            proxy_list = FileManager._read_file(proxy_file)
            random_proxy = "http:" + choice(proxy_list)
            proxy_parts = random_proxy.strip().split(':')
            self.__proxy = None
            if len(proxy_parts) == 5:
                self.__proxy = ProxyParser(random_proxy).asdict_thon
            else:
                raise ValueError("Неправильный формат прокси, продолжаем без него")
        except Exception as e:
            console.log(e, style="red")
            self.__proxy = None
            return

    def check_proxy(self, ip, port, username, password):
        proxies = {
            'http': f"socks5://{username}:{password}@{ip}:{port}",
            'https': f"socks5://{username}:{password}@{ip}:{port}"
        }
        try:
            response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
            if response.status_code == 200:
                print("Прокси работает. Видимый IP:", response.json()['origin'])
                return True
            else:
                print("Прокси не отвечает, код состояния:", response.status_code)
                return False
        except requests.exceptions.RequestException as e:
            console.log(f"Ошибка при проверке прокси {e}")
            return False

    def _main(self, item: Path, json_file: Path, json_data: dict):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = TelegramClient(str(item), self.__api_id, self.__api_hash)
        ss = StringSession()
        ss._server_address = client.session.server_address  # type: ignore
        ss._takeout_id = client.session.takeout_id  # type: ignore
        ss._auth_key = client.session.auth_key  # type: ignore
        ss._dc_id = client.session.dc_id  # type: ignore
        ss._port = client.session.port  # type: ignore
        string_session = ss.save()
        del ss, client
        json_data["proxy"] = self.__proxy
        json_data["string_session"] = string_session
        json_write_sync(json_file, json_data)

    def main(self) -> int:
        count = 0
        for item, json_file, json_data in self.find_sessions():
            self._main(item, json_file, json_data)
            count += 1
        if not count:
            console.log("Нет аккаунтов в папке с сессиями!", style="yellow")
            sys.exit(1)
        return count
