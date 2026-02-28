import json

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict
from redis import Redis


class RedisChatMessageHistory(BaseChatMessageHistory):
    def __init__(
        self,
        redis_client: Redis,
        session_key: str,
        key_prefix: str,
        ttl_seconds: int,
        max_messages: int,
    ) -> None:
        self.redis_client = redis_client
        self.session_key = session_key
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages

    @property
    def redis_key(self) -> str:
        return f"{self.key_prefix}:{self.session_key}"

    @property
    def messages(self) -> list[BaseMessage]:
        payload = self.redis_client.lrange(self.redis_key, 0, -1)
        if not payload:
            return []

        records = [json.loads(item) for item in payload]
        return messages_from_dict(records)

    def add_messages(self, messages: list[BaseMessage]) -> None:
        if not messages:
            return

        records = [json.dumps(record, ensure_ascii=False) for record in messages_to_dict(messages)]

        pipe = self.redis_client.pipeline()
        pipe.rpush(self.redis_key, *records)

        if self.max_messages > 0:
            pipe.ltrim(self.redis_key, -self.max_messages, -1)

        if self.ttl_seconds > 0:
            pipe.expire(self.redis_key, self.ttl_seconds)

        pipe.execute()

    def clear(self) -> None:
        self.redis_client.delete(self.redis_key)
