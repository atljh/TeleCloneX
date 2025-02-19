import random
from typing import Dict
from src.chatgpt import ChatGPTClient
from src.logger import console


class TextUniquenessManager:
    """
    Manages text uniqueness: word replacement, character masking, and ChatGPT rewriting.
    """

    def __init__(self, config, account_phone: str):
        self.config = config
        self.account_phone = account_phone
        self.chatgpt_client = ChatGPTClient(config)
        self.replacements = self._load_replacements(config.uniqueness.text.replacements_file)

    def _load_replacements(self, replacements_file: str) -> Dict[str, str]:
        """
        Loads word replacement rules from a file.

        Args:
            replacements_file (str): Path to the file with replacement rules.

        Returns:
            Dict[str, str]: Dictionary with replacement rules.
        """
        replacements = {}
        try:
            with open(replacements_file, "r", encoding="utf-8") as file:
                for line in file:
                    if "=" in line:
                        original, replacement = line.strip().split("=")
                        if replacement.strip().split(" ")[1] == self.account_phone:
                            replacements[original.strip()] = replacement.strip().split(" ")[0]
        except FileNotFoundError:
            console.log(f"Файл {replacements_file} не найден. Замены слов не будут применены.", style="yellow")
        return replacements

    async def unique_text(self, text: str) -> str:
        """
        Applies text uniqueness transformations:
        - Word replacement.
        - Character masking.
        - ChatGPT rewriting.

        Args:
            text (str): Input text.

        Returns:
            str: Unique text.
        """
        if self.config.uniqueness.text.symbol_masking:
            text = self._mask_characters(text)

        if self.config.uniqueness.text.rewrite:
            text = await self._rewrite_with_chatgpt(text)

        for original, replacement in self.replacements.items():
            text = text.replace(original, replacement)

        return text

    def _mask_characters(self, text: str) -> str:
        """
        Masks similar characters using RU-EN substitutions.

        Args:
            text (str): Input text.

        Returns:
            str: Text with substituted characters.
        """
        char_map = {
            "а": ["а", "a"], "А": ["А", "A"],
            "В": ["В", "B"], "е": ["е", "e"],
            "Е": ["Е", "E"], "К": ["К", "K"],
            "М": ["М", "M"], "Н": ["Н", "H"],
            "о": ["о", "o"], "О": ["О", "O"],
            "р": ["р", "p"], "Р": ["Р", "P"],
            "с": ["с", "c"], "С": ["С", "C"],
            "Т": ["Т", "T"], "х": ["х", "x"],
            "Х": ["Х", "X"], "у": ["у", "y"],
        }
        result = []
        for char in text:
            if char in char_map:
                result.append(random.choice(char_map[char]))
            else:
                result.append(char)
        return "".join(result)

    async def _rewrite_with_chatgpt(self, text: str) -> str:
        """
        Rewrites text using ChatGPT.

        Args:
            text (str): Input text.

        Returns:
            str: Rewritten text.
        """
        console.log("Рерайт текста через ChatGPT...", style="cyan")
        if len(text) < 10:
            return text
        response = await self.chatgpt_client.rewrite(text)
        return response
