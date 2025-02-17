import asyncio
from src.starter import Starter
from config import ConfigManager, print_config
from src.thon.json_converter import JsonConverter
# from src.managers.file_manager import FileManager, groups


async def run_starter(sessions_count, config):
    starter = Starter(sessions_count, config)
    await starter.main()


def main():
    config = ConfigManager.load_config()
    print_config(config)
    sessions_count = JsonConverter(config).main()
    asyncio.run(run_starter(sessions_count, config))


if __name__ == "__main__":
    main()
