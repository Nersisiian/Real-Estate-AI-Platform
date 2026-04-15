import tiktoken
from typing import List, Dict


class TokenCounter:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def count_message_tokens(self, message: Dict[str, str]) -> int:
        tokens_per_message = 3
        tokens = tokens_per_message
        for key, value in message.items():
            tokens += self.count_tokens(value)
            if key == "name":
                tokens -= 1
        return tokens

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        total = 0
        for message in messages:
            total += self.count_message_tokens(message)
        total += 3
        return total