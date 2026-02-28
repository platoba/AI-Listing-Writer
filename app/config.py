"""Configuration management."""
import os


class Config:
    def __init__(self):
        self.BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
        self.OPENAI_KEY: str = os.environ.get("OPENAI_API_KEY", "")
        self.OPENAI_BASE: str = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.MAX_HISTORY: int = int(os.environ.get("MAX_HISTORY", "50"))
        self.RATE_LIMIT_PER_MIN: int = int(os.environ.get("RATE_LIMIT_PER_MIN", "10"))
        self.AI_TEMPERATURE: float = float(os.environ.get("AI_TEMPERATURE", "0.7"))
        self.AI_MAX_TOKENS: int = int(os.environ.get("AI_MAX_TOKENS", "2000"))

    def validate(self):
        if not self.BOT_TOKEN:
            raise ValueError("未设置 BOT_TOKEN!")
        if not self.OPENAI_KEY:
            raise ValueError("未设置 OPENAI_API_KEY!")


config = Config()
