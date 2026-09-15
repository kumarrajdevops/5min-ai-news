from pydantic_settings import BaseSettings, SettingsConfigDict  # Application settings


class Settings(BaseSettings):
    # Application environment
    app_env: str = "local"

    # PostgreSQL configuration
    postgres_db: str = "ai_news"
    postgres_user: str = "ai_news"
    postgres_password: str = "ai_news_dev"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Redis configuration
    redis_url: str = "redis://redis:6379/0"

    # Daily news collection window
    news_window_hours: int = 22

    # Build the PostgreSQL SQLAlchemy URL.
    # The project uses psycopg (PostgreSQL driver version 3).
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.postgres_user}:"
            f"{self.postgres_password}@"
            f"{self.postgres_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )

    # Load configuration from .env.
    # Environment variables override the defaults above.
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


# Create the application settings object.
settings = Settings()
