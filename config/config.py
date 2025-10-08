from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

class Config(BaseSettings):
    #Telegram Bot Token
    telegram_bot_token: SecretStr = Field(..., alias="TELEGRAM_BOT_TOKEN", description="Telegram Bot Token")
    webhook_url: str = Field(..., alias="WEBHOOK_URL", description="Webhook URL")

    #Database
    database_url: str | None = Field(None, alias="DATABASE_URL", description="Database URL")

    #Redis
    redis_url: str | None = Field(None, alias="REDIS_URL", description="Redis URL")

    #LLM API Key
    gemini_api_key: SecretStr = Field(..., alias="GEMINI_API_KEY", description="Gemini API Key")
    deepseek_api_key: SecretStr = Field(..., alias="DEEPSEEK_API_KEY", description="DeepSeek API Key")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

config = Config()