import os
from typing import Dict, List
from telethon import TelegramClient
from src.logger import console, logger


class ContentPublisher:
    """
    Отвечает за публикацию контента в целевые каналы.
    """

    def __init__(self, client: TelegramClient):
        self.client = client

    async def publish_content(self, content: Dict, target_channel: str) -> bool:
        """
        Публикует уникальный контент в целевой канал.

        Args:
            content (Dict): Уникальный контент для публикации.
            target_channel (str): Целевой канал.

        Returns:
            bool: True, если публикация прошла успешно, иначе False.
        """
        try:
            if not content.get("text") and not any(key in content for key in ["photo", "video", "audio", "video_note"]):
                console.print(f"Пустой контент. Пропускаем публикацию в канал {target_channel}", style="yellow")
                return False
            caption = content.get("text", "")
            if len(caption) > 1024:
                caption = caption[:1021] + "..."

            if content.get("photo"):
                await self.client.send_file(
                    target_channel,
                    content["photo"],
                    caption=caption
                )
                self._delete_file(content["photo"])
            elif content.get("video"):
                if content.get("is_round"):
                    await self.client.send_file(target_channel, content["video"], video_note=True)
                    self._delete_file(content["video"])
                else:
                    await self.client.send_file(target_channel, content["video"], caption=caption)
                    self._delete_file(content["video"])
            elif content.get("audio"):
                await self.client.send_file(target_channel, content["audio"], caption=caption)
                self._delete_file(content["audio"])
            elif content.get("video_note"):
                await self.client.send_file(target_channel, content["video_note"], video_note=True)
                self._delete_file(content["video_note"])
            else:
                await self.client.send_message(target_channel, caption)
            return True
        except Exception as e:
            if "You can't write" in str(e):
                logger.error(f"Не может публиковать в канал {target_channel}")
                return False
            logger.error(f"Ошибка при публикации контента в канал {target_channel}: {e}")
            return False

    async def publish_album(self, album_contents: List[Dict], channel: str) -> None:
        """
        Публикует альбом медиафайлов в целевой канал.

        Args:
            album_contents (List[Dict]): Список уникализированных контентов.
            channel (str): Целевой канал.
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
            await self.client.send_file(channel, files, caption=caption)
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
                pass
                # console.print(f"Файл {original_file} не найден.", style="yellow")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {file_path}: {e}")
