from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # API
    api_key: str = "change_me"

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/payments"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # Webhook
    webhook_timeout: int = 5  # seconds

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Singleton instance
settings = Settings()
