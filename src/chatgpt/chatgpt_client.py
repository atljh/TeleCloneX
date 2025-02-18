from typing import Optional
import openai
from openai import OpenAI
from config import Config
from src.logger import logger, console
from src.managers import FileManager


class ChatGPTClient:
    """
    Handles interactions with the OpenAI ChatGPT API.
    """

    def __init__(self, config: Config):
        """
        Initializes the ChatGPTClient.

        Args:
            config (Config): Configuration object with settings like OpenAI API key.
        """
        self.config = config
        self.prompt = self.get_prompt()
        self.openai_client = OpenAI(api_key=self.config.api.openai_api_key)

    def get_prompt(self) -> str:
        prompt = FileManager._read_file("prompt.txt")
        return prompt.pop()

    async def rewrite(self, text: str) -> None:
        prompt_with_text = self.prompt.format(text=text)
        answer = await self.generate_answer(prompt_with_text)
        return answer

    async def generate_answer(self, prompt: str) -> Optional[str]:
        """
        Generates a response using the OpenAI ChatGPT model.

        Args:
            prompt (str): Prompt to send to the API.

        Returns:
            Optional[str]: Generated response or None if an error occurs.
        """
        if not prompt:
            return None

        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.api.chat_gpt_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant and interesting chatter."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                n=1,
                temperature=0.7
            )
            answer = response.choices[0].message.content
            return answer
        except openai.AuthenticationError:
            console.log("Ошибка авторизации: неверный API ключ", style="red")
        except openai.RateLimitError:
            console.log("Не хватает денег на балансе ChatGPT", style="red")
        except openai.PermissionDeniedError:
            console.log("В вашей стране не работает ChatGPT, включите VPN", style="red")
        except Exception as e:
            logger.error(f"Error while generating message with prompt: {e}")
            console.log("Ошибка генерации комментария", style="red")
            return None
