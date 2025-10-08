from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from functools import lru_cache

class Config(BaseSettings):
    #Telegram Bot Token
    telegram_bot_token: SecretStr = Field(..., alias="TELEGRAM_BOT_TOKEN", description="Telegram Bot Token")
    webhook_url: str = Field(default="https://supercat.onrender.com/webhook", alias="WEBHOOK_URL", description="Webhook URL")
    allowed_chat_ids: list[int] = Field(default=[6779771948], alias="ALLOWED_CHAT_IDS", description="Allowed Chat IDs")

    #Database
    database_url: str | None = Field(None, alias="DATABASE_URL", description="Database URL")

    #Redis
    redis_url: str | None = Field(None, alias="REDIS_URL", description="Redis URL")

    #LLM API Key
    gemini_api_key: SecretStr = Field(..., alias="GEMINI_API_KEY", description="Gemini API Key")
    deepseek_api_key: SecretStr = Field(..., alias="DEEPSEEK_API_KEY", description="DeepSeek API Key")

    #Tavily API Key
    tavily_search_key: SecretStr = Field(..., alias="TAVILY_SEARCH_KEY", description="Tavily Search Key")

    # App settings
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings():
    return Config()